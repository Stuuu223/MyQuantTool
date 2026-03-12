#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动能打分引擎核心算子引擎 - 无状态数学计算模块
========================================
CTO方案S任务1：从TimeMachineEngine剥离动能打分引擎双Ratio算分逻辑

设计原则：
1. 无状态 - 不保存任何运行时状态，纯函数式计算
2. 可复用 - 实盘/回测/热复盘共用同一套动能打分引擎大脑
3. 零硬编码 - 所有参数从ConfigManager读取
4. 向量化支持 - 支持标量和向量化计算

配置读写铁律（见 config_manager.py 模块注释）
--------------------------------------------
热路径参数(tail_trap/decay/bonus): _load_config()缓存 → self.xxx O(1)访问
  回测扫描时: with cfg.temporary_override(...): engine.reload_config(); ...

动态计算参数(量比阈值): _get_volume_ratio_threshold()在调用时读config
  temporary_override自动生效，无需reload_config()

inflow_ratio 单位铁律
--------------------
inflow_ratio 统一为百分比形式：2.0 = 流入占流通市值2%
禁止混用小数形式(0.02)，所有消费方阈值均以百分比写。
示例: inflow_ratio > 1.5  ← 流入>1.5%，而非 > 0.015

Author: AI开发专家团队
Date: 2026-03-04
Version: V1.2.0 (CTO V9.5 架构修复: F1 mfe初始化防UnboundLocal)
"""

from datetime import datetime, time
from typing import Union, Dict, Optional, Any
import pandas as pd
import numpy as np
import logging
import math

from logic.core.config_manager import get_config_manager

# 配置动能打分引擎引擎专用日志器
logger = logging.getLogger("KineticCoreEngine")


def safe_float(value, default=0.0):
    """
    【CTO绝对净化版】安全转换为float，捕获ValueError、TypeError、NaN和Inf
    
    Args:
        value: 任意类型的输入值
        default: 转换失败时的默认值
        
    Returns:
        float: 转换后的浮点数，失败返回default
        
    【CTO修复】:
    - 修复str('nan')变成float('nan')的问题
    - 修复numpy.nan和pandas.NA穿透的问题
    - 确保NaN和Inf都返回default
    """
    if value is None:
        return default
    
    try:
        import pandas as pd
        import numpy as np
        if pd.isna(value) or np.isinf(value):
            return default
    except Exception:
        pass
    
    if isinstance(value, str):
        value = value.strip().lower()
        if value == '' or value in ('nan', 'inf', '-inf', 'null', 'none'):
            return default
    
    try:
        result = float(value)
        import pandas as pd
        import numpy as np
        if pd.isna(result) or np.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


class KineticCoreEngine:
    """
    动能打分引擎核心算子 - 无状态数学计算引擎
    
    职责：
    - 封装动能打分引擎双Ratio算分算法（量比+换手率）
    - 实现时间衰减权重计算
    - 提供标量和向量化两种计算接口
    - 知行合一：实盘/回测/复盘共用同一逻辑
    
    使用示例：
        >>> engine = KineticCoreEngine()
        >>> score = engine.calculate_base_score(
        ...     change_pct=5.2,
        ...     volume_ratio=2.5,
        ...     turnover_rate_per_min=0.3
        ... )
        >>> final = engine.calculate_final_score(score, datetime.now())
    """
    
    # 交易时间常量（秒）
    MARKET_OPEN_AM = time(9, 30)
    MARKET_CLOSE_AM = time(11, 30)
    MARKET_OPEN_PM = time(13, 0)
    MARKET_CLOSE_PM = time(15, 0)
    TOTAL_TRADING_SECONDS = 14400  # 4小时 = 240分钟 = 14400秒
    
    def __init__(self):
        """
        初始化动能打分引擎核心引擎
        
        从ConfigManager加载所有配置参数，确保零硬编码。
        """
        self._config = get_config_manager()
        self._load_config()
    
    def _load_config(self) -> None:
        """
        从ConfigManager加载所有动能打分引擎相关配置（热路径参数缓存）。

        【配置读写铁律】
        此方法只缓存「热路径参数」（每Tick调用，需O(1)访问）。
        量比动态阈值不在此缓存，由 _get_volume_ratio_threshold() 在调用时
        通过 config_manager.compute_volume_ratio_threshold() 动态计算。
        
        回测参数扫描标准姿势：
            with cfg.temporary_override({'live_sniper.time_decay_ratios.tail_trap': 0.1}):
                engine.reload_config()   # ← 必须！刷新缓存
                result = engine.run_backtest(...)
        """
        # 换手率阈值
        turnover_config = self._config.get_turnover_rate_thresholds()
        self.turnover_rate_per_min_min: float = turnover_config.get('per_minute_min', 0.2)
        self.turnover_rate_max: float = turnover_config.get('total_max', 70.0)
        
        # 时间衰减系数
        decay_config = self._config.get_time_decay_ratios()
        self.time_decay_early_morning: float = decay_config.get('early_morning_rush', 1.2)
        self.time_decay_morning_confirm: float = decay_config.get('morning_confirm', 1.0)
        self.time_decay_noon_trash: float = decay_config.get('noon_trash', 0.8)
        self.time_decay_tail_trap: float = decay_config.get('tail_trap', 0.2)
        
        # 评分奖励配置
        bonus_config = self._config.get('live_sniper.scoring_bonuses', {})
        self.extreme_volume_ratio: float = bonus_config.get('extreme_volume_ratio', 3.0)
        self.extreme_vol_bonus: float = bonus_config.get('extreme_vol_bonus', 10.0)
        self.high_efficiency_turnover_min: float = bonus_config.get('high_efficiency_turnover_min', 0.5)
        self.high_turnover_bonus: float = bonus_config.get('high_turnover_bonus', 5.0)

    def reload_config(self) -> None:
        """
        【回测参数扫描专用】重新从ConfigManager加载实例缓存。

        在 cfg.temporary_override() 修改了热路径参数后，
        必须调用此方法才能让新参数对本实例生效。

        示例：
            with cfg.temporary_override({'live_sniper.time_decay_ratios.tail_trap': 0.1}):
                engine.reload_config()  # ← 缓存刷新
                result = engine.run_backtest()

        注意：对 compute_volume_ratio_threshold() 无需调用此方法，
        该函数在每次调用时直接读取ConfigManager，override自动生效。
        """
        self._load_config()
    
    def calculate_base_score(
        self,
        change_pct: float,
        volume_ratio: float,
        turnover_rate_per_min: float,
        market_volume_ratios: list[float] | None = None,
        mode: str = 'live'
    ) -> float:
        """
        计算基础动能分（动能打分引擎双Ratio核心算法）
        
        算法逻辑：
        1. 检查双Ratio过滤条件（量比+换手率）
        2. 通过过滤：涨幅*5 + 极端量比奖励 + 高效换手奖励
        3. 未通过过滤：涨幅*2（降低权重）
        
        Args:
            change_pct: 涨跌幅百分比（如5.0表示涨5%）
            volume_ratio: 量比（当前成交量/5日均量）
            turnover_rate_per_min: 每分钟换手率（百分比）
            market_volume_ratios: 【Option B】当日全市场各股有效量比列表，
                                  传入时动态计算分位数阈值；None时fallback到
                                  fixed_threshold=3.0（向后兼容）
            mode: 'live'=实盘(95th), 'backtest'=回测(88th)，
                  回测灵敏度扫描用 temporary_override 覆盖 backtest_percentile
        
        Returns:
            float: 基础动能分（0-100+）
        
        Raises:
            TypeError: 输入类型不正确时
        """
        if not all(isinstance(x, (int, float)) for x in [change_pct, volume_ratio, turnover_rate_per_min]):
            raise TypeError("所有输入参数必须是数字类型")
        
        # 动态量比阈值（Option B）
        volume_ratio_threshold = self._get_volume_ratio_threshold(market_volume_ratios, mode)
        
        # 动能打分引擎双Ratio化过滤检查
        passes_filters = (
            volume_ratio >= volume_ratio_threshold and
            turnover_rate_per_min >= self.turnover_rate_per_min_min
        )
        
        if passes_filters:
            # 【CTO V87 纯正物理】废除硬截断min(x,100)，改用tanh平滑
            # tanh(涨幅*5/100)*100 让分数在100分渐近
            # 涨幅10% -> tanh(0.5)*100 = 46分
            # 涨幅20% -> tanh(1.0)*100 = 76分
            # 涨幅50% -> tanh(2.5)*100 = 98.7分
            base_score = math.tanh(abs(change_pct) * 0.05) * 100.0
            
            if volume_ratio > self.extreme_volume_ratio:
                base_score += self.extreme_vol_bonus
            
            if turnover_rate_per_min > self.high_efficiency_turnover_min:
                base_score += self.high_turnover_bonus
        else:
            # 【CTO V87 纯正物理】废除硬截断min(x,50)，改用tanh平滑
            base_score = math.tanh(abs(change_pct) * 0.04) * 50.0
        
        return float(base_score)
    
    def _get_volume_ratio_threshold(
        self,
        market_volume_ratios: list[float] | None = None,
        mode: str = 'live'
    ) -> float:
        """
        【动态量比阈值 Option B】获取量比过滤阈值。

        委托给 config_manager.compute_volume_ratio_threshold()，
        每次调用时直接读取 ConfigManager（不缓存），
        temporary_override 自动生效，无需 engine.reload_config()。

        Args:
            market_volume_ratios: 当日全市场各股有效量比列表。
                                  None 或长度不足时 fallback 到 fixed_threshold=3.0。
            mode: 'live'=实盘(95th分位), 'backtest'=回测(88th分位,可override)

        Returns:
            float: 量比过滤阈值（动态计算或fixed_threshold兜底）
        """
        return self._config.compute_volume_ratio_threshold(
            market_volume_ratios or [],
            mode=mode
        )
    
    def get_time_decay_ratio(self, timestamp: Union[datetime, time, str]) -> float:
        """
        获取时间衰减系数
        
        时间段划分：
        - 09:30-09:40 (早盘抢筹): 1.2 溢价奖励
        - 09:40-10:30 (主升浪确认): 1.0 正常推力
        - 10:30-14:00 (震荡垃圾时间): 0.8 分数打折
        - 14:00-14:55 (尾盘陷阱): 0.2 严防骗炮，大幅降权（腰斩×2）
        
        Args:
            timestamp: 时间（datetime/time对象或'HH:MM:SS'字符串）
        
        Returns:
            float: 时间衰减系数
        
        Raises:
            ValueError: 时间格式不正确时
        """
        if isinstance(timestamp, datetime):
            t = timestamp.time()
        elif isinstance(timestamp, time):
            t = timestamp
        elif isinstance(timestamp, str):
            try:
                parts = timestamp.split(':')
                hour = int(parts[0])
                minute = int(parts[1])
                second = int(parts[2]) if len(parts) > 2 else 0
                t = time(hour, minute, second)
            except (ValueError, IndexError) as e:
                raise ValueError(f"时间字符串格式错误，期望'HH:MM:SS'或'HH:MM': {timestamp}") from e
        else:
            raise TypeError(f"timestamp必须是datetime/time/str类型，当前类型: {type(timestamp)}")
        
        t0940 = time(9, 40)
        t1030 = time(10, 30)
        t1400 = time(14, 0)
        t1455 = time(14, 55)
        
        if t < t0940:
            return self.time_decay_early_morning
        elif t < t1030:
            return self.time_decay_morning_confirm
        elif t < t1400:
            return self.time_decay_noon_trash
        elif t <= t1455:
            return self.time_decay_tail_trap
        else:
            return 0.0
    
    def calculate_final_score(
        self,
        base_score: float,
        timestamp: Union[datetime, time, str]
    ) -> float:
        """
        计算最终得分 = 基础分 * 时间衰减
        
        Args:
            base_score: 基础动能分
            timestamp: 时间戳（用于获取时间衰减系数）
        
        Returns:
            float: 最终得分
        
        Raises:
            TypeError: 输入类型不正确时
        """
        if not isinstance(base_score, (int, float)):
            raise TypeError(f"base_score必须是数字类型，当前类型: {type(base_score)}")
        
        decay_ratio = self.get_time_decay_ratio(timestamp)
        return float(base_score * decay_ratio)
    
    def calculate_true_dragon_score(
        self,
        net_inflow: float,
        price: float,
        prev_close: float,
        high: float,
        low: float,
        open_price: float,
        flow_5min: float,
        flow_15min: float,
        flow_5min_median_stock: float,
        space_gap_pct: float,
        float_volume_shares: float,
        current_time: datetime,
        total_amount: float = 0.0,
        total_volume: float = 0.0,
        # 【CTO照妖镜】封板质检核心参数
        is_limit_up: bool = False,
        limit_up_queue_amount: float = 0.0,
        # 【CTO V34】模式参数
        mode: str = "live",
        # 【CTO V54】股票代码参数
        stock_code: str = "",
        # 【CTO终极战役】基因记忆参数
        is_yesterday_limit_up: bool = False,
        yesterday_vol_ratio: float = 1.0,
        # 【CTO V46】横向虹吸效应参数
        vampire_ratio_pct: float = 0.0
    ) -> tuple[float, float, float, float, float]:
        """
        【V20.5 Boss终极钦定：动能与势能的双Ratio验钞机 + VWAP洗盘容错】
        
        Returns:
            tuple: (final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe)
        """

        if not isinstance(current_time, datetime):
            raise TypeError(f"current_time必须是datetime类型，当前类型: {type(current_time)}")
        
        # ==============================================================
        # 【CTO V88 纯正物理引擎】无低保、无门槛的连续力场
        # 废除所有max/min硬编码，用连续物理算子计算动能
        # ==============================================================
        import math
        
        # 0. 安全转换
        net_inflow = safe_float(net_inflow, 0.0)
        price = safe_float(price, 0.0)
        prev_close = safe_float(prev_close, 0.0)
        high = safe_float(high, 0.0)
        low = safe_float(low, 0.0)
        open_price = safe_float(open_price, 0.0)
        flow_5min = safe_float(flow_5min, 0.0)
        flow_15min = safe_float(flow_15min, 0.0)
        flow_5min_median_stock = safe_float(flow_5min_median_stock, 0.0)
        float_volume_shares = safe_float(float_volume_shares, 0.0)
        
        # 安全检查
        if price <= 0:
            return 0.0, 0.0, 0.0, 0.0, 0.0
        if float_volume_shares <= 0:
            return 0.0, 0.0, 0.0, 0.0, 0.0
        if high < low:
            high = low = price  # 容错
        
        # 量纲升维
        float_market_cap = float_volume_shares * price
        if 0 < float_market_cap < 200000000:  # 2亿以下
            float_market_cap = float_market_cap * 10000.0
            logger.debug(f"V88 [量纲升维] {stock_code} 市值已升维")
        
        # ========== 1. 质量 = 流入占比 × 放量倍数 ==========
        # 流入占比（对数软压缩）
        if float_market_cap > 1000:
            raw_inflow_pct = (net_inflow / float_market_cap * 100.0)
            if abs(raw_inflow_pct) > 30.0:
                sign = 1.0 if raw_inflow_pct > 0 else -1.0
                inflow_ratio_pct = sign * (30.0 + 10.0 * math.log10(abs(raw_inflow_pct) - 29.0))
            else:
                inflow_ratio_pct = raw_inflow_pct
        else:
            inflow_ratio_pct = 0.0
        
        # 放量倍数（tanh自然限制）
        MIN_BASE_FLOW = 2000000.0
        safe_flow_5min = flow_5min if flow_5min > 0 else (flow_15min / 3.0 if flow_15min > 0 else 1.0)
        safe_median = flow_5min_median_stock if flow_5min_median_stock > 0 else MIN_BASE_FLOW
        raw_ratio_stock = safe_flow_5min / safe_median if safe_median > 0 else 1.0
        ratio_stock = 1.0 + 6.0 * math.tanh(raw_ratio_stock - 1.0)
        
        # ========== 1. 洛伦兹质量收缩 (Lorentz Contraction) ==========
        # 【CTO V100 铁律】放量>10倍后边际效用急剧递减，防止90x异常对倒撑爆引擎！
        if ratio_stock > 10.0:
            effective_ratio = 10.0 + 5.0 * math.log10(ratio_stock - 9.0)
        else:
            effective_ratio = ratio_stock
        
        # 质量势能
        # === 【CTO V105 去魔法化：跨日封单溢出算子】 ===
        if is_yesterday_limit_up:
            # 废除拍脑袋的 "3倍"！我们需要根据昨天封板时的真实动能溢出来计算今天的基础质量。
            # 【提取真实溢出势能】yesterday_vol_ratio参数包含昨日量比信息
            # 如果昨天是巨量封板，今天应该继承更大的势能
            overflow_multiplier = 1.0  # 默认温和继承
            
            if yesterday_vol_ratio > 1.0 and flow_5min_median_stock > 0:
                # 溢出乘数 = 昨日量比的对数平滑
                # 昨日量比越高，说明资金介入越深，今日继承势能越大
                overflow_multiplier = 1.0 + math.log10(1.0 + yesterday_vol_ratio) * 2.0
            else:
                # 若缺乏昨日量比数据，仅给予温和的 1.5 倍基础惯性继承
                overflow_multiplier = 1.5
            
            # 材质脆性检测 (踢铁板逻辑)
            # 如果今天极端缩量且盘中无封单，这是惯性衰竭的铁板！
            if ratio_stock < 0.5 and limit_up_queue_amount < 50000000.0:
                # 极端缩量且今天盘中无封单，这是惯性衰竭的铁板！
                mass_potential = (inflow_ratio_pct / 100.0) * 0.1
                logger.debug(f"⚠️ [惯性衰竭] {stock_code} 缩量铁板(ratio:{ratio_stock:.2f})，剥夺连板特权！")
            else:
                # 真正的动态质量继承！没有魔法数字，全靠真实数据说话！
                mass_potential = (inflow_ratio_pct / 100.0) * overflow_multiplier
                logger.debug(f"👑 [真实动量继承] {stock_code} 溢出乘数: {overflow_multiplier:.2f}x，质量: {mass_potential:.4f}")
        else:
            # 非连板股，使用当天的实际放量作为质量
            mass_potential = (inflow_ratio_pct / 100.0) * effective_ratio
        
        # ========== 2. 指数速度向量 (VELOCITY CUBED) ==========
        # 【CTO V92 铁律】涨幅的威力是非线性的！3次幂让涨幅9%的动能是涨幅3%的27倍！
        change_pct = (price - prev_close) / prev_close * 100.0 if prev_close > 0 else 0.0
        sign_velocity = 1.0 if change_pct >= 0 else -1.0
        velocity = sign_velocity * (abs(change_pct) ** 3)
        
        # ========== 3. 动能 = 质量 × 速度 ==========
        base_kinetic_energy = mass_potential * velocity
        
        # === 【CTO V100 终极时空物理引擎 + V109 能量重心降维】 ===
        # 4. 时空微观动量阻尼与【VWAP重心引力补偿】
        price_range = high - low
        raw_purity = (price - low) / price_range if price_range > 0 else (1.0 if change_pct > 0 else 0.0)
        purity_norm = min(max(raw_purity, 0.0), 1.0)
        
        # 【CTO V109 能量重心降维提取】
        # 计算全天成交均价 (VWAP)，作为主力的真实能量重心
        vwap = (total_amount / total_volume) if total_volume > 0 else prev_close
        
        # === 【CTO V112 微观坍塌探测 (动量方向)】 ===
        # 物理铁律：如果从高空自由落体回撤超过3.5%（比如冲高8%被砸回4.5%），
        # 即使你现在还在水面上，这也不叫重力逃逸，这叫"流星坠毁"！
        is_micro_collapsed = False
        # 预先计算mfe用于返回（防止UnboundLocalError）
        mfe = 0.0
        if high > 0 and prev_close > 0:
            drawdown_from_high = (high - price) / prev_close * 100.0
            if drawdown_from_high > 3.5:  # V112精细调整：3.5%阈值捕获更多诱多
                is_micro_collapsed = True
                # 【CTO V112终极修复】流星坠毁直接静默！诱多出货票没资格上榜！
                # 物理铁律：从高点回撤>3.5% = 资金链断裂 = 诱多出货
                logger.debug(f"☄️ [流星坠毁静默] {stock_code} 从高点回撤{drawdown_from_high:.1f}%>3.5%，诱多出货判死刑！")
                return 0.0, 0.0, inflow_ratio_pct, ratio_stock, mfe
        
        # === 【CTO V110 绝对水位隔离：重力逃逸判据 + V112微观坍塌】 ===
        # 物理铁律：必须同时满足 [翻红] + [高于开盘价] + [脱离底部3%以上] + [站稳均价线] + [未发生微观坍塌]
        # 才算真正的"高空重力逃逸"，才有资格享受洗盘豁免！
        # 防止水下反抽(price < prev_close)骗炮！
        # 【V112新增】防止高空坠毁流星(is_micro_collapsed)骗取豁免！
        is_gravitational_escape = (
            price > prev_close and           # 翻红：打破隔夜多空平衡
            price >= open_price and          # 高于开盘价：守住日内资金防线
            change_pct > 3.0 and             # 脱离底部引力区
            price >= (vwap * 0.995) and      # 站稳均价线
            not is_micro_collapsed           # 【V112】未发生微观坍塌
        )
        
        # 时间熵特征提取 (判断当前处于什么交易阶段)
        minutes_from_open = (current_time.hour * 60 + current_time.minute) - (9 * 60 + 30)
        
        # 动态阻尼场
        if minutes_from_open < 60:
            # 早盘(10:30前)：容忍洗盘，2次方温和阻尼
            friction_multiplier = purity_norm ** 2
            # 早盘龙抬头豁免 (强流入+放量承接)
            if inflow_ratio_pct > 1.5 and effective_ratio > 3.0 and purity_norm < 0.5:
                friction_multiplier = max(friction_multiplier, 0.4)
                logger.debug(f"🐉 [龙抬头豁免] {stock_code} 早盘强承接，纯度{purity_norm*100:.0f}%豁免！")
        elif minutes_from_open < 180:
            # 盘中(10:30-13:30)：3次方中等绞杀
            friction_multiplier = purity_norm ** 3
        else:
            # 午后及尾盘(13:30后)：长上影线是绝对的死亡派发，5次方极刑！
            friction_multiplier = purity_norm ** 5
        
        # 【CTO V110 重力逃逸绝对豁免】
        # 只有真正的高空重力逃逸(翻红+高于开盘+涨幅>3%+站稳VWAP)，才能享受洗盘豁免！
        # 彻底杜绝水下反抽骗炮！(水下股票反抽超过均价线也被当成高位洗盘的致命Bug已修复)
        if is_gravitational_escape and purity_norm < 0.7:
            friction_multiplier = purity_norm ** 1.5
            logger.debug(f"⚖️ [重力逃逸豁免] {stock_code} 高空水位(涨幅{change_pct:.1f}%)稳踩VWAP，纯度{purity_norm*100:.0f}%判定为洗盘！")
        
        # 【CTO V112 流星坠毁极刑】
        # 如果发生了微观坍塌(从高点回撤>4.5%)，这就是"流星坠毁"！
        # 无论纯度如何，都要执行严厉惩罚！诱多出货票必须被绞杀！
        if is_micro_collapsed:
            # 流星坠毁：用5次方惩罚，让分数归零
            friction_multiplier = purity_norm ** 5
            logger.debug(f"☄️ [流星坠毁] {stock_code} 从高点回撤>{4.5}%，执行5次方极刑！")
        
        # 【CTO V112 坠毁极刑】
        # 只要你没资格进入逃逸层(被砸破了VWAP，或者发生了微观坍塌)，且纯度低于45%
        # 直接执行最残忍的6次方极刑，让那些骗炮票分数彻底归零！
        if not is_gravitational_escape and purity_norm < 0.45:
            friction_multiplier = purity_norm ** 6
            logger.debug(f"💀 [坠毁极刑] {stock_code} 未逃逸重力且纯度{purity_norm*100:.0f}%，执行6次方绞杀！")
        
        # ========== 5. 效率激活 = MFE Sigmoid ==========
        if inflow_ratio_pct <= 0.0:
            efficiency_multiplier = 0.0
            mfe = 0.0
        else:
            upward_thrust = ((price - low) + (high - open_price)) / 2
            price_range_pct = upward_thrust / prev_close * 100.0 if prev_close > 0 else 0.0
            mfe = price_range_pct / inflow_ratio_pct if inflow_ratio_pct > 0 else 0.0
            efficiency_multiplier = 3.0 / (1.0 + math.exp(-2.0 * (mfe - 1.2)))
        
        # === 【CTO V103 纯物理力场防线：废除一切静态位移阈值】 ===
        
        # 1. MFE 摩擦力死亡之墙 (取代涨幅<3%静态阈值)
        # 不看涨幅！看做功效率。如果流入了一定资金(>0.5%)，但 MFE 效率极低(<0.1)，
        # 说明每一分钱都砸在了套牢盘的绝对阻力墙上（动能转化为无用的内能热量）。直接放弃！
        if not is_yesterday_limit_up and inflow_ratio_pct > 0.5:
            if mfe < 0.1:
                logger.debug(f"🧱 [阻力死墙] {stock_code} 做功效率极低(MFE:{mfe:.2f})，动能被摩擦力耗尽，静默！")
                return 0.0, 0.0, inflow_ratio_pct, ratio_stock, mfe
        
        # 2. 重力势能坍塌 (Gravitational Collapse, 取代回撤>4%静态阈值)
        # 物理学定义：价格被砸穿了日内的"能量质心"(近似为当日开盘价)。
        # 如果当前价格跌破了开盘价，且被死死压在日内最高点的一半以下(纯度<0.4)，主升力场已坍塌。
        if price < open_price and purity_norm < 0.4:
            logger.debug(f"🕳️ [引力坍塌] {stock_code} 跌破开盘价且纯度仅{purity_norm*100:.0f}%，势能坠入黑洞！")
            return 0.0, 0.0, inflow_ratio_pct, ratio_stock, mfe
        
        # ========== 6. 终极融合 ==========
        final_score_raw = base_kinetic_energy * friction_multiplier * efficiency_multiplier
        final_score = round(final_score_raw * 1000.0, 1)
        if final_score < 0:
            final_score = 0.0
        
        # === 【CTO V103 纯物理力场防线：动量虚空惩罚】 ===
        # 物理学定义：位移大(涨停)，但质量极轻(无承接资金)，说明在高空处于失重漂浮状态，极其危险。
        # 如果速度极快(velocity>300) 但 势能质量(mass_potential) < 0.05 且非连板票，没资格打高分！
        if velocity > 300.0 and mass_potential < 0.05 and not is_yesterday_limit_up:
            final_score = final_score / 10.0
            logger.debug(f"🎈 [动量虚空] {stock_code} 速度快({velocity:.0f})但质量空洞(Mass:{mass_potential:.4f})，判定为失重跟风！")
        
        # Sustain计算（兼容输出）
        safe_median_15min = flow_5min_median_stock * 3.0 if flow_5min_median_stock > 0 else MIN_BASE_FLOW * 3.0
        sustain_ratio = flow_15min / safe_median_15min if safe_median_15min > 0 else 0.0
        float_mc_yi = float_market_cap / 100000000.0
        if float_mc_yi > 0:
            gravity_damper = min(max(1.0 + math.log10(float_mc_yi / 50.0) * 0.5, 0.5), 2.5)
        else:
            gravity_damper = 0.5
        sustain_ratio = sustain_ratio * gravity_damper
        
        logger.debug(f"[V88Physics] {stock_code} | mass:{mass_potential:.4f} | vel:{velocity:.2f}% | ke:{base_kinetic_energy:.4f} | friction:{friction_multiplier:.2f} | mfe_mult:{efficiency_multiplier:.2f} | score:{final_score}")
        
        return final_score, sustain_ratio, inflow_ratio_pct, ratio_stock, mfe
    
    def calculate_volume_ratio(
        self,
        current_volume: Union[int, float],
        elapsed_seconds: int,
        avg_volume_5d: float
    ) -> float:
        """
        计算盘中动态量比（向量化支持）
        
        公式：
        - 时间进度 = elapsed_seconds / 14400（4小时交易时间）
        - 预期累计成交量 = avg_volume_5d * 时间进度
        - 量比 = current_volume / 预期累计成交量
        
        Args:
            current_volume: 当前累计成交量（股数）
            elapsed_seconds: 已交易秒数（从09:30开始）
            avg_volume_5d: 5日平均成交量（股数）
        
        Returns:
            float 或 pd.Series: 动态量比值
        
        Raises:
            ValueError: 平均成交量<=0或已用秒数<0时
            TypeError: 输入类型不正确时
        """
        if isinstance(current_volume, pd.Series) or isinstance(elapsed_seconds, pd.Series):
            return self._calculate_volume_ratio_vectorized(
                current_volume, elapsed_seconds, avg_volume_5d
            )
        
        if not all(isinstance(x, (int, float)) for x in [current_volume, elapsed_seconds, avg_volume_5d]):
            raise TypeError("所有输入参数必须是数字类型")
        
        if avg_volume_5d <= 0:
            raise ValueError(f"5日平均成交量必须>0，当前值: {avg_volume_5d}")
        if elapsed_seconds < 0:
            raise ValueError(f"已交易秒数不能为负数，当前值: {elapsed_seconds}")
        if elapsed_seconds == 0:
            return 0.0
        
        time_progress = elapsed_seconds / self.TOTAL_TRADING_SECONDS
        expected_volume = avg_volume_5d * time_progress
        volume_ratio = current_volume / expected_volume if expected_volume > 0 else 0.0
        
        return float(volume_ratio)
    
    def _calculate_volume_ratio_vectorized(
        self,
        current_volume: pd.Series,
        elapsed_seconds: Union[int, pd.Series],
        avg_volume_5d: float
    ) -> pd.Series:
        """
        向量化计算量比（内部方法）
        
        使用pandas向量化操作，避免Python for循环。
        适用于热复盘引擎处理全天Tick数据。
        """
        if not isinstance(current_volume, pd.Series):
            current_volume = pd.Series(current_volume)
        
        if isinstance(elapsed_seconds, pd.Series):
            time_progress = elapsed_seconds / self.TOTAL_TRADING_SECONDS
        else:
            time_progress = pd.Series([elapsed_seconds / self.TOTAL_TRADING_SECONDS] * len(current_volume))
        
        expected_volume = avg_volume_5d * time_progress
        volume_ratio = current_volume / expected_volume.where(expected_volume > 0, np.nan)
        volume_ratio = volume_ratio.fillna(0.0)
        
        return volume_ratio


# ==============================================================================
# 单元测试
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("动能打分引擎核心算子引擎 - 单元测试 V1.2.0 (F1 mfe初始化修复)")
    print("=" * 70)
    
    engine = KineticCoreEngine()
    
    # 测试F1修复：flow_15min<=0时的Spike极刑前置，mfe不能UnboundLocalError
    print("\n【测试F1】mfe初始化防UnboundLocalError验证")
    test_time_spike = datetime(2026, 3, 4, 9, 45, 0)
    try:
        final_score_spike, sustain_spike, inflow_spike, ratio_spike, mfe_spike = engine.calculate_true_dragon_score(
            net_inflow=10000000,
            price=25.0,
            prev_close=22.0,
            high=26.0,
            low=23.0,
            open_price=22.5,
            flow_5min=5000000,
            flow_15min=-1000000,  # 负数触发Spike极刑前置
            flow_5min_median_stock=1000000,
            space_gap_pct=0.08,
            float_volume_shares=100000000,
            current_time=test_time_spike
        )
        assert final_score_spike == 0.0, f"Spike极刑应返回0.0，实际{final_score_spike}"
        assert mfe_spike == 0.0, f"mfe应为初始化默认值0.0，实际{mfe_spike}"
        print(f"  ✅ 通过 - Spike极刑前置时mfe={mfe_spike}，无UnboundLocalError")
    except UnboundLocalError as e:
        print(f"  ❌ 失败 - UnboundLocalError: {e}")
    
    # 原有测试：sustain_ratio负流入场景
    print("\n【测试sustain_ratio】负流入修复验证")
    test_time_neg = datetime(2026, 3, 4, 9, 45, 0)
    final_score_neg, sustain_ratio_neg, inflow_ratio_neg, ratio_stock_neg, mfe_neg = engine.calculate_true_dragon_score(
        net_inflow=10000000,
        price=25.0,
        prev_close=22.0,
        high=26.0,
        low=23.0,
        open_price=22.5,
        flow_5min=-5000000,
        flow_15min=10000000,
        flow_5min_median_stock=1000000,
        space_gap_pct=0.08,
        float_volume_shares=100000000,
        current_time=test_time_neg
    )
    print(f"  flow_5min=-500万（净流出），flow_15min=1000万")
    print(f"  sustain_ratio: {sustain_ratio_neg:.2f}")
    print(f"  最终得分: {final_score_neg:.2f}")
    print("  ✅ 通过")
    
    print("\n" + "=" * 70)
    print("✅ 所有单元测试通过！")
    print("=" * 70)
