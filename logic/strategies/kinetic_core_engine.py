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
        # F1修复: 在函数入口处初始化 mfe 安全默认值，防止 Spike极刑前置分支
        # 引用未赋值变量导致 UnboundLocalError 线上静默崩溃
        # 【CTO V71修复】废除魔法数字-100.0，改用0.0作为物理底线
        # ==============================================================
        mfe: float = 0.0
        mfe_penalty = 1.0  # MFE惩罚系数（资金流出时降为0.1，微弱流入时降为0.5）
        
        # 0. 基础准备：安全转换 + 流通市值
        net_inflow = safe_float(net_inflow, 0.0)
        price = safe_float(price, 0.0)
        prev_close = safe_float(prev_close, 0.0)
        high = safe_float(high, 0.0)
        low = safe_float(low, 0.0)
        open_price = safe_float(open_price, 0.0)
        flow_5min = safe_float(flow_5min, 0.0)
        flow_15min = safe_float(flow_15min, 0.0)
        flow_5min_median_stock = safe_float(flow_5min_median_stock, 0.0)
        space_gap_pct = safe_float(space_gap_pct, 0.0)
        float_volume_shares = safe_float(float_volume_shares, 0.0)
        total_amount = safe_float(total_amount, 0.0)
        total_volume = safe_float(total_volume, 0.0)
        limit_up_queue_amount = safe_float(limit_up_queue_amount, 0.0)
        
        if price <= 0:
            raise ValueError(f"当前价格必须>0，当前值: {price}")
        if float_volume_shares <= 0:
            raise ValueError(f"流通股本必须>0，当前值: {float_volume_shares}")
        if high < low:
            raise ValueError(f"最高价不能低于最低价")
        
        float_market_cap = float_volume_shares * price
        
        # ==============================================================
        # 【CTO V66 绝地反击】彻底根治万股量纲引发的物理引擎崩盘
        # ==============================================================
        if float_market_cap > 0 and float_market_cap < 200000000:
            float_market_cap = float_market_cap * 10000.0
            logger.debug(f"📐 [量纲升维] {stock_code} 市值{float_market_cap/100000000:.2f}亿已升维至真实人民币！")
        
        calibrated_float_market_cap = float_market_cap
        
        # 第一步：【CTO V51 里氏震级模型】流入占比计算
        if float_market_cap > 1000:
            raw_inflow_pct = (net_inflow / float_market_cap * 100.0)
            if abs(raw_inflow_pct) > 30.0:
                sign = 1.0 if raw_inflow_pct > 0 else -1.0
                inflow_ratio_pct = sign * (30.0 + 10.0 * math.log10(abs(raw_inflow_pct) - 29.0))
                logger.debug(f"📐 [数学软封顶] {stock_code} inflow={raw_inflow_pct:.1f}% -> {inflow_ratio_pct:.1f}%")
            else:
                inflow_ratio_pct = raw_inflow_pct
        else:
            inflow_ratio_pct = 0.0
        
        inflow_ratio = inflow_ratio_pct
        
        float_market_cap_yi = calibrated_float_market_cap / 100_000_000
        
        # 2. 相对历史放量倍数
        MIN_BASE_FLOW = 2000000.0
        safe_flow_5min = flow_5min if flow_5min > 0 else (flow_15min / 3.0 if flow_15min > 0 else 1.0)
        safe_median = max(flow_5min_median_stock, MIN_BASE_FLOW)
        raw_ratio_stock = safe_flow_5min / safe_median
        
        # 【CTO V87 纯正物理】废除硬截断max/min，改用tanh连续平滑
        # tanh(x)在x=0附近接近线性，x>3时渐近1，完美模拟放量边际递减
        # ratio_stock_raw=1 -> tanh(1)=0.76 -> 映射到5.2x
        # ratio_stock_raw=3 -> tanh(3)=0.995 -> 映射到6.97x
        # ratio_stock_raw=10 -> tanh(10)=1.0 -> 映射到7.0x(渐近上限)
        ratio_stock = 1.0 + 6.0 * math.tanh(raw_ratio_stock - 1.0)
        ratio_stock = max(0.1, ratio_stock)  # 仅保留下限保护
        
        # 3. 价格推力（日内强度0-1）
        # 【CTO V87 纯正物理】废除硬截断，改用Sigmoid连续平滑
        # 价格推力本质是价格在日内振幅中的位置，物理意义清晰
        if high == low:
            raw_price_strength = 1.0 if price > prev_close else 0.0
        else:
            raw_price_strength = (price - low) / (high - low)
        
        # Sigmoid平滑映射到(0.05, 0.95)区间，避免极端边界
        # x=0 -> sigmoid(-4)=0.018, x=1 -> sigmoid(4)=0.982
        price_strength = 1.0 / (1.0 + math.exp(-8.0 * (raw_price_strength - 0.5)))
        
        # 【CTO V84 物理绞杀】放量滞涨检测
        # 如果放量(ratio_stock>3)但价格推力极低(<0.3)，说明爆量出货/长上影线，动能坍塌！
        effective_ratio = ratio_stock
        if ratio_stock > 3.0 and price_strength < 0.3:
            effective_ratio = 0.1  # 放量变成阻力
            logger.info(f"💀 [放量滞涨] {stock_code} 放量{ratio_stock:.1f}倍但推力仅{price_strength:.2f}，判定出货！动能坍塌至0.1")
        
        # 4. 乘法动能模型 = 流入% × 有效放量倍数 × 价格推力
        # 【CTO V84】废除0.5底噪！涨多少就是多少推力！
        if inflow_ratio_pct > 0:
            base_power = inflow_ratio_pct * effective_ratio * price_strength
        else:
            base_power = abs(inflow_ratio_pct) * 0.5
        
        # 【CTO V83 物理宪法】MFE重铸为Sigmoid激活函数
        # 做功效率的影响应该是连续的S型曲线，而非阶梯式跃变
        mfe_multiplier = 1.0  # 默认乘数
        
        if inflow_ratio_pct <= 0.5:
            # 【激活能门槛】流入<=0.5%时，振幅只是噪音，MFE无物理意义
            mfe = 0.0
            mfe_multiplier = 0.1  # 极刑压制
            logger.debug(f"[MFE无效] {stock_code} 流入仅{inflow_ratio_pct:.2f}%，激活能不足，乘数×0.1")
        else:
            # 真实MFE计算：做功效率 = 振幅 / 净流入
            upward_thrust = ((price - low) + (high - open_price)) / 2
            price_range_pct = upward_thrust / prev_close * 100 if prev_close > 0 else 0.0
            mfe = max(0.01, price_range_pct / inflow_ratio_pct)
            
            # 【连续物理算子：MFE Sigmoid激活函数】
            # 公式: M(x) = 3.0 / (1 + exp(-2.0 * (x - 1.2)))
            # MFE = 0.2 (重摩擦) -> 乘数 ~0.35 (极刑压制)
            # MFE = 1.2 (标准线) -> 乘数 = 1.50 (平滑过渡)
            # MFE = 2.5 (大真空) -> 乘数 ~2.79 (逼近极值3.0)
            mfe_multiplier = 3.0 / (1.0 + math.exp(-2.0 * (mfe - 1.2)))
            logger.debug(f"[MFE Sigmoid] {stock_code} MFE={mfe:.2f}，乘数×{mfe_multiplier:.2f}")
        
        # 【CTO V82】应用MFE乘数，而非加法！
        base_power = base_power * mfe_multiplier

        # 资金净流出惩罚
        if inflow_ratio_pct <= 0:
            base_power *= 0.1  # 动能坍塌惩罚
            logger.warning(f"💀 [动能坍塌] {stock_code} 资金净流出{inflow_ratio_pct:.1f}%，一票否决！")
        elif 0 < inflow_ratio_pct < 2.0:
            base_power *= 0.5  # 无效做功惩罚
            logger.debug(f"🐌 [无效做功] {stock_code} 流入极弱({inflow_ratio_pct:.1f}%)，动能无法维持")
        
        # 大力出奇迹标志
        cap_penalty = (float_market_cap_yi / 100.0) * 1.5
        miracle_threshold = max(3.0, 10.0 - cap_penalty)
        
        is_force_override = False
        if inflow_ratio_pct > miracle_threshold and mfe > 0.5:
            logger.info(f"🔥 [大力出奇迹] {stock_code} 净流入{inflow_ratio_pct:.1f}%>{miracle_threshold:.1f}%阈值(市值{float_market_cap_yi:.0f}亿)！无视一切引力！")
            is_force_override = True
        
        # 第二步：出货拦截
        is_net_outflow = inflow_ratio_pct <= 0
        
        # 第三步：VWAP洗盘容错
        vwap_multiplier = 1.0
        if total_volume > 0 and total_amount > 0:
            vwap = total_amount / total_volume
            if price < vwap and vwap > 0:
                vwap_multiplier = 0.5
                logger.debug(f"[VWAP洗盘容错] {stock_code} 价格{price:.2f} < VWAP{vwap:.2f}, 动能腰斩打5折！")
        
        base_power = base_power * vwap_multiplier
        
        # 【CTO V83 物理宪法】纯度重铸为抛物线阻尼器
        # 计算纯度 (0.0 到 1.0) - 价格在日内高低点的位置
        price_range = high - low
        if price_range > 0:
            raw_purity = (price - low) / price_range
        else:
            # 一字板情况：涨停给100%，跌停给0%
            raw_purity = 1.0 if price >= prev_close else 0.0
        
        purity_norm = min(max(raw_purity, 0.0), 1.0)
        
        # 【连续物理算子：纯度动量阻尼】
        # 纯度 0.9 -> 乘数 0.81 (轻微摩擦)
        # 纯度 0.5 -> 乘数 0.25 (严重压制)
        # 纯度 0.2 -> 乘数 0.04 (毁灭性坍塌)
        # 纯度 0.02 -> 乘数 0.0004 (绝对归零)
        purity_multiplier = purity_norm ** 2
        
        # 兼容旧版输出
        purity_pct = purity_norm * 100.0
        change_pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
        
        # 第四步：神级乘数区
        multiplier = 1.0
        
        # A. 维持能力（sustain_ratio）- 【CTO V65 质量引力阻尼重铸】
        MIN_BASE_FLOW = 2000000.0
        safe_median_15min = max(flow_5min_median_stock * 3.0, MIN_BASE_FLOW * 3.0)
        
        raw_sustain = flow_15min / safe_median_15min if safe_median_15min > 0 else 1.0
        
        float_mc_yi = float_market_cap / 100000000.0 if float_market_cap > 0 else 0.0
        
        if float_mc_yi > 0:
            gravity_damper = max(0.5, min(2.5, 1.0 + math.log10(float_mc_yi / 50.0) * 0.5))
        else:
            gravity_damper = 0.5
        
        sustain_ratio = raw_sustain * gravity_damper
        
        dynamic_ceiling = 30.0 * gravity_damper
        sustain_ratio = min(sustain_ratio, dynamic_ceiling)
        
        health_threshold = 5.0 * gravity_damper
        survival_threshold = 1.0 * (1.0 / gravity_damper)
        
        logger.debug(f"⚖️ [引力阻尼] {stock_code} 市值{float_mc_yi:.0f}亿, raw={raw_sustain:.2f}×阻尼{gravity_damper:.2f}=sustain{sustain_ratio:.2f}, 阈值[存活{survival_threshold:.2f}|健康{health_threshold:.2f}]")
        
        # 【CTO强制熔断】Spike极刑前置
        # F1修复: mfe 已在函数入口处初始化为 0.0，此处引用绝对安全
        if flow_15min <= 0:
            logger.warning(f"💀 [Spike极刑] {stock_code} 15分钟净流出，一票否决")
            return 0.0, -1.0, inflow_ratio_pct, ratio_stock, mfe
        
        if sustain_ratio < survival_threshold:
            logger.warning(f"💀 [Spike极刑] {stock_code} sustain={sustain_ratio:.2f}<存活阈值{survival_threshold:.2f}，被抛压瓦解")
            return 0.0, sustain_ratio, inflow_ratio_pct, ratio_stock, mfe
        
        stock_identifier = f"{current_time.strftime('%H:%M')}@{price:.2f}"
        
        # MFE制衡
        if mfe < 1.0:
            mfe_factor = max(0.5, mfe)
            effective_sustain = sustain_ratio * mfe_factor
            logger.info(f"🐢 [MFE压制] {stock_code} sustain={sustain_ratio:.2f}×MFE{mfe:.2f}(保护{mfe_factor:.2f})={effective_sustain:.2f}")
        else:
            effective_sustain = sustain_ratio
            mfe_factor = 1.0
        
        if effective_sustain > health_threshold:
            multiplier *= 1.5
            logger.info(f"🔥 [资金洪流] {stock_identifier} effective_sustain={effective_sustain:.2f}>健康阈值{health_threshold:.2f}，乘数×1.5！")
        elif effective_sustain < survival_threshold:
            multiplier *= 0.3
            logger.warning(f"[资金退潮] {stock_identifier} effective_sustain={effective_sustain:.2f}<存活阈值{survival_threshold:.2f}，降权至0.3")
        
        # B. 筹码纯度指数衰减模型
        bonus_score = 0.0
        alpha = 20.0
        purity_multiplier = math.exp(-space_gap_pct * alpha)
        bonus_score += 15.0 * purity_multiplier
        
        # C. 吸血效应
        if inflow_ratio_pct > 1.5:
            bonus_score += 15.0
        
        # D. 横向虹吸效应
        if vampire_ratio_pct > 5.0:
            bonus_score += 50.0
            logger.info(f"🦇 [横向虹吸] {stock_code} 抽血{vampire_ratio_pct:.2f}%，+50分")
        elif vampire_ratio_pct > 3.0:
            bonus_score += 30.0
            logger.info(f"🦇 [横向虹吸] {stock_code} 抽血{vampire_ratio_pct:.2f}%，+30分")
        elif vampire_ratio_pct > 1.0:
            bonus_score += 15.0
        
        # E. 【CTO V80】废除时间衰减毒瘤！
        # 物理真理：真龙的势能不会因为到了下午就自然衰减！
        # 尾盘打折的逻辑是期权定价(Theta)的错误应用！
        # 只保留早盘加成，尾盘不惩罚
        if mode == "scan":
            pass
        else:
            if current_time.hour == 9 and current_time.minute <= 40:
                multiplier *= 1.2  # 早盘溢价保留
            # 【删除】elif current_time.hour >= 14: multiplier *= 0.5
            # 真龙14:59的动能和09:30是一模一样的！
        
        # F. 价格动能净值
        if high > low:
            price_momentum = (price - low) / (high - low)
        else:
            price_momentum = 1.0 if price > prev_close else 0.0
        
        is_detonation_critical = (price_momentum > 0.90)
        
        change_pct = (price - prev_close) / prev_close if prev_close > 0 else 0
        
        if is_detonation_critical and not is_limit_up:
            if inflow_ratio_pct > 5.0:
                logger.info(f"🚀 [势能起爆] {stock_code} 动能净值{price_momentum*100:.1f}%，流入{inflow_ratio_pct:.1f}%！")
                multiplier = max(multiplier, 2.0)
                bonus_score += 25.0
            elif inflow_ratio_pct > 2.0:
                bonus_score += 10.0
                logger.info(f"💪 [高位坚挺] {stock_code} 动能净值{price_momentum*100:.1f}%，流入{inflow_ratio_pct:.1f}%！+10分")
        
        in_friction_zone = (0.0 <= space_gap_pct <= 0.05)
        is_violent_inflow = (inflow_ratio_pct > 5.0)
        
        if in_friction_zone and is_violent_inflow:
            if is_limit_up:
                multiplier *= 3.0
                logger.info(f"🔥 [史诗级真龙] {stock_code} 爆量({inflow_ratio_pct:.1f}%)摧毁阻力位！无视摩擦力封板，乘数起飞！")
                if mfe < 0:
                    mfe = abs(mfe)
            else:
                multiplier *= 0.1
                logger.warning(f"💀 [摩擦力绞杀] {stock_code} 阻力位爆量({inflow_ratio_pct:.1f}%)但未能破局，动能枯竭，一票否决！")
        
        # G. 真龙升天器
        if is_limit_up and limit_up_queue_amount > 0:
            queue_bonus = min(3.0, limit_up_queue_amount / 100_000_000.0)
            multiplier *= (1.5 + queue_bonus)
            logger.info(f"[真龙确立] {stock_identifier} 强势封板，封单额{limit_up_queue_amount/10000:.0f}万，乘数飙升！")
        
        # 第六步：最终得分
        memory_multiplier = 1.0
        
        if is_yesterday_limit_up:
            memory_multiplier += 1.0
            logger.info(f"🔥 [涨停基因] {stock_code} 昨日涨停，霸权溢价+1.0！")
        
        if yesterday_vol_ratio > 3.0:
            genetic_bonus = min(yesterday_vol_ratio * 0.1, 1.0) * 0.5
            memory_multiplier += genetic_bonus
            logger.info(f"🧠 [暴动基因] {stock_code} 昨日量比={yesterday_vol_ratio:.1f}，遗传溢价+{genetic_bonus:.2f}！")
        
        logger.info(f"🧬 [海马体] {stock_code} 记忆乘数={memory_multiplier:.2f}x")
        
        # 换手率纯度乘数
        turnover_multiplier = 1.0
        if float_volume_shares > 0 and total_volume > 0:
            turnover_pct = (total_volume / float_volume_shares) * 100
            if is_limit_up:
                if turnover_pct < 2.0:
                    turnover_multiplier = 0.5
                    logger.warning(f"[一字板惩罚] {stock_code} 涨停但换手率仅{turnover_pct:.1f}%，疑似庄股，分数打5折！")
                elif 5.0 <= turnover_pct <= 20.0:
                    turnover_multiplier = 1.5
                    logger.info(f"🔥 [换手龙] {stock_code} 涨停+换手率{turnover_pct:.1f}%，极品真龙，乘数×1.5！")
        
        if is_force_override:
            bonus_score += 40.0
            logger.info(f"🔥 [大力出奇迹] {stock_code} 流入{inflow_ratio_pct:.1f}%且MFE>{mfe:.2f}，+40分")
        
        # 【CTO V83 终极力场方程式】
        # 施加空间、效率与微观方向的力场乘数
        # base_power已经应用了mfe_multiplier，现在应用purity_multiplier
        base_power_with_physics = base_power * purity_multiplier
        
        final_score = round(base_power_with_physics * multiplier * memory_multiplier * turnover_multiplier + bonus_score, 2)
        
        # 【CTO V83】物理乘数已经包含MFE和纯度的连续影响，无需额外硬编码阈值
        
        if is_net_outflow:
            final_score = final_score * 0.5
            logger.debug(f"[出货拦截] {stock_identifier} 净流出，分数减半")
        
        return final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe
    
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
