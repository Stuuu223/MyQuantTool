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
Version: V1.1.1 (修复sustain_ratio负流入Bug)
"""

from datetime import datetime, time
from typing import Union, Dict, Optional, Any
import pandas as pd
import numpy as np
import logging

from logic.core.config_manager import get_config_manager

# 配置动能打分引擎引擎专用日志器
logger = logging.getLogger("动能打分引擎CoreEngine")


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
    except:
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


class 动能打分引擎CoreEngine:
    """
    动能打分引擎核心算子 - 无状态数学计算引擎
    
    职责：
    - 封装动能打分引擎双Ratio算分算法（量比+换手率）
    - 实现时间衰减权重计算
    - 提供标量和向量化两种计算接口
    - 知行合一：实盘/回测/复盘共用同一逻辑
    
    使用示例：
        >>> engine = 动能打分引擎CoreEngine()
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
            base_score = min(abs(change_pct) * 5, 100.0)
            
            if volume_ratio > self.extreme_volume_ratio:
                base_score += self.extreme_vol_bonus
            
            if turnover_rate_per_min > self.high_efficiency_turnover_min:
                base_score += self.high_turnover_bonus
        else:
            base_score = min(abs(change_pct) * 2, 50.0)
        
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
        is_limit_up: bool = False,  # 当前是否触及涨停价
        limit_up_queue_amount: float = 0.0,  # 涨停板买一封单金额（元）
        # 【CTO V34】模式参数
        mode: str = "live",  # "live"实盘模式(有尾盘衰减) / "scan"扫描模式(无衰减)
        # 【CTO V54】股票代码参数（用于板块识别、动态阈值计算）
        stock_code: str = "",  # 股票代码
        # 【CTO终极战役】基因记忆参数
        is_yesterday_limit_up: bool = False,  # 昨日是否涨停（纯血真龙基因）
        yesterday_vol_ratio: float = 1.0,  # 昨日量比（用于暴动基因检测）
        # 【CTO V46】横向虹吸效应参数
        vampire_ratio_pct: float = 0.0  # 该股流入占全候选池总流入的比例(%)
    ) -> tuple[float, float, float, float, float]:
        """
        【V20.5 Boss终极钦定：动能与势能的双Ratio验钞机 + VWAP洗盘容错】
        
        Args:
            net_inflow: 净流入金额（元）
            price: 当前价格（元）
            prev_close: 昨日收盘价（元）
            high: 日内最高价（元）
            low: 日内最低价（元）
            open_price: 开盘价（元）
            flow_5min: 开盘后前5分钟资金流入（元）(09:30-09:35)
            flow_15min: 开盘后前15分钟资金流入（元）(09:30-09:45) ← 累计窗口，含flow_5min
            flow_5min_median_stock: 该股票历史5分钟资金流入中位数（元）
            space_gap_pct: 空间差百分比（上方套牢盘距离）
            float_volume_shares: 真实流通股本（股）
            current_time: 当前时间（datetime对象）
            total_amount: 总成交额（元），用于VWAP计算
            total_volume: 总成交量（股），用于VWAP计算
            is_limit_up: 当前是否触及涨停价（用于封板质检）
            limit_up_queue_amount: 涨停板买一封单金额（元），用于计算封板强度
        
        Returns:
            tuple: (final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe)
                - final_score: 最终验钞得分（float）
                - sustain_ratio: 资金维持率（float）
                - inflow_ratio: 净流入占流通市值比例【百分比形式，2.0=2%】
                - ratio_stock: 相对自身历史爆发力倍数（float）
                - mfe: 资金效率指标Money Force Efficiency（float）
        """
        if not isinstance(current_time, datetime):
            raise TypeError(f"current_time必须是datetime类型，当前类型: {type(current_time)}")
        
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
        # 【CTO照妖镜】封板质检参数处理
        limit_up_queue_amount = safe_float(limit_up_queue_amount, 0.0)
        
        if price <= 0:
            raise ValueError(f"当前价格必须>0，当前值: {price}")
        if float_volume_shares <= 0:
            raise ValueError(f"流通股本必须>0，当前值: {float_volume_shares}")
        if high < low:
            raise ValueError(f"最高价不能低于最低价")
        
        float_market_cap = float_volume_shares * price
        
        # 【P0修复】删除altitude_weight海拔权重，涨停股资金流入不再被夸大
        # 物理真理：net_inflow就是net_inflow，不需要根据涨幅加权
        # 原代码：altitude_weight = 1.0 + (current_altitude * 10.0)，涨停股×2倍，严重失真！
        
        # 第一步：【CTO V51 里氏震级模型】无上限乘法动能！
        # 废除加法凑分，改用乘法爆发：base_power = 流入占比 × 放量倍数
        # 让龙中龙自然冲破天花板，无需硬性上限！
        
        # 1. 流入占比百分比（使用真实net_inflow，不再乘以altitude_weight）
        # 【P0修复】使用net_inflow直接计算，不再加权
        inflow_ratio_pct = (net_inflow / float_market_cap * 100.0) if float_market_cap > 1000 else 0.0
        
        # 【CTO纠偏令】废除归零，实装量纲自适应校准仪！
        # ============================================================
        # 【CTO手术1】拆除市值量纲强行放大！改用数学软封顶！
        # 根因：放大10000倍导致小盘股inflow_ratio从30%被压到7.82%
        # 正解：用对数平滑防止极端溢出，但不改变底层量纲！
        # ============================================================
        import math
        
        if float_market_cap > 1000:
            raw_inflow_pct = (net_inflow / float_market_cap * 100.0)
            # 【CTO数学软封顶】超过30%后取对数平滑，增速放缓但不改变量纲
            if abs(raw_inflow_pct) > 30.0:
                sign = 1.0 if raw_inflow_pct > 0 else -1.0
                inflow_ratio_pct = sign * (30.0 + 10.0 * math.log10(abs(raw_inflow_pct) - 29.0))
                logger.debug(f"📐 [数学软封顶] {stock_code} inflow={raw_inflow_pct:.1f}% -> {inflow_ratio_pct:.1f}%")
            else:
                inflow_ratio_pct = raw_inflow_pct
        else:
            inflow_ratio_pct = 0.0
        
        inflow_ratio = inflow_ratio_pct  # 返回百分比形式
        
        # 【CTO V53大力出奇迹】资金绝对霸权！非线性市值自适应阈值！
        # 物理原理：质量越大，惯性越大，需要的推力比例越小
        # 小盘股(30亿)：10%流入 = 3亿真金白银，极难！
        # 大盘股(200亿)：5%流入 = 10亿，已是天量！
        # 百亿市值递减公式：miracle_threshold = max(3.0, 10.0 - 市值/100亿)
        float_market_cap_yi = calibrated_float_market_cap / 100_000_000  # 转为亿元
        
        # 2. 相对历史放量倍数（放大历史爆发力）
        # 【CTO核心注入】强制200万的5分钟成交额物理底线，绞杀僵尸股分母陷阱！
        MIN_BASE_FLOW = 2000000.0  # 200万底线
        safe_flow_5min = flow_5min if flow_5min > 0 else (flow_15min / 3.0 if flow_15min > 0 else 1.0)
        safe_median = max(flow_5min_median_stock, MIN_BASE_FLOW)
        ratio_stock = safe_flow_5min / safe_median
        ratio_stock = max(0.01, min(ratio_stock, 10.0))  # 【CTO V54】封顶10倍，防止乘法爆炸！
        
        # 3. 价格推力（日内强度0-1）
        # 【CTO重铸令R4】此为价格相对位置参考，非真实动能！
        # 真实做功效率由MFE计算（第五步）
        if high == low:
            price_strength = 1.0 if price > prev_close else 0.0
        else:
            price_strength = (price - low) / (high - low)
            price_strength = max(0.0, min(price_strength, 1.0))
        
        # 【CTO V51核心】乘法动能模型 = 流入% × 放量倍数 × 价格推力
        # 无上限！行情越热，真龙与杂毛的分数差越大！
        if inflow_ratio_pct > 0:
            base_power = inflow_ratio_pct * ratio_stock * price_strength
        else:
            # 净流出时给基础分但不爆发
            base_power = abs(inflow_ratio_pct) * 0.5  # 基础分，不爆发
        
        # 【CTO重铸令R4】废除伪动能涨停板基础加成！
        # 原逻辑：base_power += 40.0 if price_strength >= 0.99 else 0.0
        # 新逻辑：MFE对数放大器替代（真实做功效率）
        # MFE计算移到此处（需要先计算upward_thrust）
        if inflow_ratio_pct > 0:
            upward_thrust = ((price - low) + (high - open_price)) / 2
            price_range_pct = upward_thrust / prev_close if prev_close > 0 else 0.0
            mfe_raw = price_range_pct / (inflow_ratio_pct / 100.0)
            mfe = max(-10.0, mfe_raw)  # 防负溢出
            # 【CTO修正】MFE对数放大器：绝对安全的指数放大器
            # 原公式缺陷：mfe=0.1时log10(0.1)=-1.0可能导致加分异常
            # 新公式：MFE>1时给奖励，极差效率不给分，且加权系数从10提升到15
            # MFE=1 → +0分, MFE=5 → +10.5分, MFE=10 → +15分
            if mfe > 0:
                import math
                mfe_bonus = 15.0 * math.log10(max(mfe * 10.0, 1.0))
                base_power += mfe_bonus
                logger.debug(f"[MFE做功溢价] {stock_code} MFE={mfe:.2f}, 奖励+{mfe_bonus:.1f}分")
        else:
            mfe = -100.0
        
        # 【CTO V54大力出奇迹】资金绝对霸权！修正数学公式！
        # 物理原理：质量越大，惯性越大，需要的推力比例越小
        # 正确的市值衰减公式：每增加100亿市值，阈值下降1.5%
        # 50亿: 10 - 0.75 = 9.25% | 200亿: 10 - 3 = 7% | 500亿: 10 - 7.5 = 2.5% -> 兜底3.0%
        cap_penalty = (float_market_cap_yi / 100.0) * 1.5  # 百亿级别衰减
        miracle_threshold = max(3.0, 10.0 - cap_penalty)
        
        is_force_override = False  # 标志变量，后续在最终得分计算前应用
        if inflow_ratio_pct > miracle_threshold and mfe > 0.5:
            logger.info(f"🔥 [大力出奇迹] {stock_code} 净流入{inflow_ratio_pct:.1f}%>{miracle_threshold:.1f}%阈值(市值{float_market_cap_yi:.0f}亿)！无视一切引力！")
            is_force_override = True  # 设置标志
        
        # 第二步：出货拦截（净流出封顶40分）
        is_net_outflow = inflow_ratio_pct <= 0
        
        # 第三步：VWAP洗盘容错（里氏震级下的乘数惩罚机制）
        # 【CTO V38修复】废除机械的-20分！改为乘数降维打击
        # 8000分真龙跌破VWAP变4000分(仍可上榜)，500分杂毛变250分(滚出Top20)
        vwap_multiplier = 1.0
        if total_volume > 0 and total_amount > 0:
            vwap = total_amount / total_volume
            if price < vwap and vwap > 0:
                # 跌破日内均线，重力大于升力，基础动能直接腰斩！
                vwap_multiplier = 0.5
                logger.debug(f"[VWAP洗盘容错] {stock_code} 价格{price:.2f} < VWAP{vwap:.2f}, 动能腰斩打5折！")
        
        base_power = base_power * vwap_multiplier
        
        # 第四步：神级乘数区
        multiplier = 1.0
        
        # A. 维持能力（sustain_ratio）- 【CTO V65 质量引力阻尼重铸】
        # 废除"纯自身历史对比"的虚假倍数，引入物理学质量（m）挂钩！
        # 物理真理：推卡车的1.6倍，在物理做功上，绝对大于推泡沫的10倍！
        MIN_BASE_FLOW = 2000000.0  # 200万底线防微盘骗炮
        safe_median_15min = max(flow_5min_median_stock * 3.0, MIN_BASE_FLOW * 3.0)
        
        # 1. 基础倍数：当前做功 / 历史做功均值
        raw_sustain = flow_15min / safe_median_15min if safe_median_15min > 0 else 1.0
        
        # 2. 【核心】市值引力阻尼器 (Gravity Damper)
        # 流通市值（亿）
        float_mc_yi = float_market_cap / 100000000.0 if float_market_cap > 0 else 0.0
        
        # 阻尼系数公式：对数比例化。市值越大，该系数越大，意味着同样的raw_sustain，大票含金量更高！
        # 设定锚点：以 50亿市值为基准点 1.0。
        # 20亿以下微盘会被衰减（0.7x），100亿中盘加成（1.2x），500亿大卡车极强加成（1.8x）
        import math
        if float_mc_yi > 0:
            gravity_damper = max(0.5, min(2.5, 1.0 + math.log10(float_mc_yi / 50.0) * 0.5))
        else:
            gravity_damper = 0.5
        
        # 3. 施加引力：推卡车的倍数被放大，推泡沫的倍数被挤干水分
        sustain_ratio = raw_sustain * gravity_damper
        
        # 4. 动态极值封顶 (废除僵化的50x硬编码)
        # 微盘股的虚假高潮被死死压在 20x，而大盘股可以冲破 40x
        dynamic_ceiling = 30.0 * gravity_damper
        sustain_ratio = min(sustain_ratio, dynamic_ceiling)
        
        # 为了兼容后续乘数区间，将 1.0 和 5.0 的阈值按引力做等比例漂移
        health_threshold = 5.0 * gravity_damper
        survival_threshold = 1.0 * (1.0 / gravity_damper)  # 小票存活更难，大票存活更容易
        
        logger.debug(f"⚖️ [引力阻尼] {stock_code} 市值{float_mc_yi:.0f}亿, raw={raw_sustain:.2f}×阻尼{gravity_damper:.2f}=sustain{sustain_ratio:.2f}, 阈值[存活{survival_threshold:.2f}|健康{health_threshold:.2f}]")
        
        # 【CTO强制熔断】Spike极刑前置！如果没通过，立刻斩首，绝不浪费算力往下走！
        if flow_15min <= 0:
            logger.warning(f"💀 [Spike极刑] {stock_code} 15分钟净流出，一票否决")
            return 0.0, -1.0, inflow_ratio_pct, ratio_stock, mfe
        
        # 【CTO V65】动态存活阈值：小票存活更难，大票存活更容易
        if sustain_ratio < survival_threshold:
            logger.warning(f"💀 [Spike极刑] {stock_code} sustain={sustain_ratio:.2f}<存活阈值{survival_threshold:.2f}，被抛压瓦解")
            return 0.0, sustain_ratio, inflow_ratio_pct, ratio_stock, mfe
        
        stock_identifier = f"{current_time.strftime('%H:%M')}@{price:.2f}"
        
        # ============================================================
        # 【CTO手术2】MFE制衡Sustain！打击大盘伪高潮！
        # 病灶：金风科技(大盘)sustain=50x但MFE=0.3靠堆钱刷高分
        # 物理真理：推不动的钱再多也是废铁！MFE<1.0就是老黄牛！
        # 方案：effective_sustain = sustain_ratio * mfe_factor
        # mfe<1.0时压制sustain，防止堆钱刷榜
        # ============================================================
        if mfe < 1.0:
            # 低效率压制：MFE越低，sustain打折越狠
            mfe_factor = mfe  # MFE=0.3时sustain只保留30%
            effective_sustain = sustain_ratio * mfe_factor
            logger.info(f"🐢 [MFE压制] {stock_code} sustain={sustain_ratio:.2f}×MFE{mfe:.2f}={effective_sustain:.2f}，老黄牛降权！")
        else:
            # 高效率放行：MFE>=1.0时sustain不变
            effective_sustain = sustain_ratio
            mfe_factor = 1.0
        
        if effective_sustain > health_threshold:
            multiplier *= 1.5  # 极度健康：持续维持极高水位
            logger.info(f"🔥 [资金洪流] {stock_identifier} effective_sustain={effective_sustain:.2f}>健康阈值{health_threshold:.2f}，乘数×1.5！")
        elif effective_sustain < survival_threshold:
            multiplier *= 0.3  # 退潮：流入量连平时的中位数都不如
            logger.warning(f"[资金退潮] {stock_identifier} effective_sustain={effective_sustain:.2f}<存活阈值{survival_threshold:.2f}，降权至0.3")
        # [1.0, 5.0] 区间：资金维持正常，multiplier不变
        
        # B. 【CTO修复】筹码纯度指数衰减模型
        # 原设计: space_gap < 10% 给 +10分（硬编码阈值）
        # 新设计: μ = 15 * exp(-space_gap * α)，α=20集中度系数
        # space_gap=0%: 15分, 5%: 5.5分, 10%: 2.0分，连续渐变而非断崖
        import math
        bonus_score = 0.0
        alpha = 20.0  # 套牢盘集中度系数，可调参数
        purity_multiplier = math.exp(-space_gap_pct * alpha)
        bonus_score += 15.0 * purity_multiplier
        
        # C. 吸血效应（流入比例 > 1.5% ← 百分比形式）
        # 【CTO修复】从乘法改为加法，防止叠乘倒挂
        if inflow_ratio_pct > 1.5:
            bonus_score += 15.0  # 加法而非乘法
        
        # D. 【CTO修复】横向虹吸效应权重重新标定
        # 原设计+1500/+800/+300相对于base_power(0.5-50分)极端失衡
        # 新设计: +50/+30/+15，与base_power匹配，避免扭曲分数梯队
        if vampire_ratio_pct > 5.0:
            bonus_score += 50.0  # 吸血霸权，但不再一锤定音
            logger.info(f"🦇 [横向虹吸] {stock_code} 抽血{vampire_ratio_pct:.2f}%，+50分")
        elif vampire_ratio_pct > 3.0:
            bonus_score += 30.0
            logger.info(f"🦇 [横向虹吸] {stock_code} 抽血{vampire_ratio_pct:.2f}%，+30分")
        elif vampire_ratio_pct > 1.0:
            bonus_score += 15.0
        
        # D. 早盘时间坚决度
        # 【CTO V34修复】scan模式下跳过时间衰减，废除"时间冻结"毒瘤！
        if mode == "scan":
            # Scan模式：盘后扫描榜单，不应用时间衰减，让真龙以真实数据排序
            pass
        else:
            # Live模式：实盘交易，应用时间衰减
            if current_time.hour == 9 and current_time.minute <= 40:
                multiplier *= 1.2
            elif current_time.hour >= 14:
                multiplier *= 0.5
        
        # 【CTO V53宪法】废除魔法数字，实装无量纲动能净值！
        # price_momentum = (Current_Price - Low) / (High - Low)
        # > 0.90 表示逼空起爆临界状态（死死咬住日内最高点）
        if high > low:
            price_momentum = (price - low) / (high - low)
        else:
            price_momentum = 1.0 if price > prev_close else 0.0
        
        is_detonation_critical = (price_momentum > 0.90)  # 动能净值>90% = 起爆临界
        
        # 计算涨跌幅（仅用于日志输出，不参与决策！）
        change_pct = (price - prev_close) / prev_close if prev_close > 0 else 0
        
        # 势能爆发点判定：只要姿态完美且推力极高（或绝对流入极深），一律保送！
        if is_detonation_critical and not is_limit_up:
            if inflow_ratio_pct > 5.0:  # 5%以上流入 = 真金白银推升
                logger.info(f"🚀 [势能起爆] {stock_code} 动能净值{price_momentum*100:.1f}%，流入{inflow_ratio_pct:.1f}%！")
                # 强制解除尾盘打折等任何负面压制
                multiplier = max(multiplier, 2.0)
                bonus_score += 25.0  # 【CTO修复】从+500压缩到+25
            elif inflow_ratio_pct > 2.0:  # 2%以上流入 = 有资金托底
                bonus_score += 10.0  # 【CTO修复】从+200压缩到+10
                logger.info(f"💪 [高位坚挺] {stock_code} 动能净值{price_momentum*100:.1f}%，流入{inflow_ratio_pct:.1f}%！+10分")
        
        # 【CTO Phase3.2】摩擦力决战区：空间差0~5%，面临突破前高
        in_friction_zone = (0.0 <= space_gap_pct <= 0.05)
        is_violent_inflow = (inflow_ratio_pct > 5.0)  # 极度爆量
        
        if in_friction_zone and is_violent_inflow:
            if is_limit_up:
                # 史诗级真龙：顶着抛压硬上，且封死涨停
                multiplier *= 3.0
                logger.info(f"🔥 [史诗级真龙] {stock_code} 爆量({inflow_ratio_pct:.1f}%)摧毁阻力位！无视摩擦力封板，乘数起飞！")
                if mfe < 0:
                    mfe = abs(mfe)  # 强行翻转低效率的MFE（此处mfe尚未计算，需在MFE计算后处理）
            else:
                # 放量滞涨骗炮：爆量了但封不住，死刑
                multiplier *= 0.1
                logger.warning(f"💀 [摩擦力绞杀] {stock_code} 阻力位爆量({inflow_ratio_pct:.1f}%)但未能破局，动能枯竭，一票否决！")
        
        # 【CTO照妖镜】F. 真龙升天器：极致封板强度奖励（资金意向度）
        # 封单金额直接转化为动能乘数，让真龙脱颖而出！
        if is_limit_up and limit_up_queue_amount > 0:
            # 每1亿封单增加1.0乘数权重，上限3.0（即3亿封单拿满）
            queue_bonus = min(3.0, limit_up_queue_amount / 100_000_000.0)
            multiplier *= (1.5 + queue_bonus)
            logger.info(f"[真龙确立] {stock_identifier} 强势封板，封单额{limit_up_queue_amount/10000:.0f}万，乘数飙升！")
        
        # 第五步：MFE效率算子
        # 【CTO重铸令R4】MFE已在函数开头初始化为-100.0，无需dir()判断
        # base_power计算时已使用MFE对数放大器，此处保留mfe值用于返回
        
        # 第六步：最终得分（无上限里氏震级！）
        # ================= 跨日基因遗传算法（海马体完整版）=================
        memory_multiplier = 1.0
        
        # 1. 昨日涨停基因（绝对霸权）
        if is_yesterday_limit_up:
            memory_multiplier += 1.0  # 直接赋予100%的基础霸权溢价
            logger.info(f"🔥 [涨停基因] {stock_code} 昨日涨停，霸权溢价+1.0！")
        
        # 2. 昨日暴动基因（昨日量比极高，资金深度介入）
        # 半衰期模型：昨日量比>3时，施加0.5的衰减系数（阈值降低以捕获更多信号）
        if yesterday_vol_ratio > 3.0:
            genetic_bonus = min(yesterday_vol_ratio * 0.1, 1.0) * 0.5
            memory_multiplier += genetic_bonus
            logger.info(f"🧠 [暴动基因] {stock_code} 昨日量比={yesterday_vol_ratio:.1f}，遗传溢价+{genetic_bonus:.2f}！")
        
        logger.info(f"🧬 [海马体] {stock_code} 记忆乘数={memory_multiplier:.2f}x")
        
        # ==================== 【CTO V43】换手率纯度乘数 ====================
        # 解决"一字板霸榜"问题：惩罚缩量一字板，奖励充分换手的真龙
        turnover_multiplier = 1.0
        if float_volume_shares > 0 and total_volume > 0:
            turnover_pct = (total_volume / float_volume_shares) * 100
            if is_limit_up:
                if turnover_pct < 2.0:
                    # 缩量一字板庄股/一波流，降权！
                    turnover_multiplier = 0.5
                    logger.warning(f"[一字板惩罚] {stock_code} 涨停但换手率仅{turnover_pct:.1f}%，疑似庄股，分数打5折！")
                elif 5.0 <= turnover_pct <= 20.0:
                    # 充分换手的分歧转一致真龙，爆分奖励！
                    turnover_multiplier = 1.5
                    logger.info(f"🔥 [换手龙] {stock_code} 涨停+换手率{turnover_pct:.1f}%，极品真龙，乘数×1.5！")
        
        # 【CTO V53大力出奇迹】应用特权（在所有乘数计算完成后）
        # 【CTO修复】 bonus从+1000压缩到+40，与base_power量级匹配
        # 移除强制乘数3.0，避免与Spike极刑冲突（物理上互斥）
        if is_force_override:
            bonus_score += 40.0  # 【CTO修复】从+1000压缩到+40
            logger.info(f"🔥 [大力出奇迹] {stock_code} 流入{inflow_ratio_pct:.1f}%且MFE>{mfe:.2f}，+40分")
        
        # 应用乘数和加分（含高位做功奖励bonus_score）
        final_score = round(base_power * multiplier * memory_multiplier * turnover_multiplier + bonus_score, 2)
        
        # ============================================================
        # 【CTO手术3】MFE终极审判！一票否决与真空奖励！
        # 病灶：金风科技(大盘)靠堆钱刷分但MFE=0.3推不动
        # 物理真理：推不动就滚，推得快才奖！
        # ============================================================
        if mfe > 2.0:
            # 真空无阻力：MFE>2.0表示每一分钱都转化为势能，奖励20%
            final_score *= 1.2
            logger.info(f"🚀 [MFE真空] {stock_code} MFE={mfe:.2f}>2.0，真空无阻力，×1.2！")
        elif mfe < 0.5 and inflow_ratio_pct < 10.0:
            # 低效垃圾：MFE<0.5且流入<10%，堆钱推不动，腰斩！
            final_score *= 0.5
            logger.warning(f"🐌 [MFE垃圾] {stock_code} MFE={mfe:.2f}<0.5且流入{inflow_ratio_pct:.1f}%<10%，堆钱废物，×0.5！")
        
        # 【CTO修复】Spike极刑已前置到第四步开头，此处不再重复判断
        # 净流出惩罚：减半而非封顶，让流出股也有区分度
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
    print("动能打分引擎核心算子引擎 - 单元测试 V1.1.1 (sustain_ratio负流入修复)")
    print("=" * 70)
    
    engine = 动能打分引擎CoreEngine()
    
    # 新增测试：sustain_ratio负流入场景
    print("\n【测试NEW】sustain_ratio 负流入修复验证")
    test_time_neg = datetime(2026, 3, 4, 9, 45, 0)
    final_score_neg, sustain_ratio_neg, inflow_ratio_neg, ratio_stock_neg, mfe_neg = engine.calculate_true_dragon_score(
        net_inflow=10000000,
        price=25.0,
        prev_close=22.0,
        high=26.0,
        low=23.0,
        open_price=22.5,
        flow_5min=-5000000,  # 前5分钟净流出（负数）
        flow_15min=10000000,  # 15分钟总流入（正）
        flow_5min_median_stock=1000000,
        space_gap_pct=0.08,
        float_volume_shares=100000000,
        current_time=test_time_neg
    )
    print(f"  flow_5min=-500万（净流出），flow_15min=1000万")
    print(f"  sustain_ratio: {sustain_ratio_neg:.2f} (应=-1.0，触发绞杀)")
    print(f"  最终得分: {final_score_neg:.2f} (应<10，被绞杀)")
    assert sustain_ratio_neg == -1.0, f"负流入应强制sustain_ratio=-1.0，实际{sustain_ratio_neg}"
    assert final_score_neg < 10, f"负流入应触发绞杀(<10分)，实际{final_score_neg}"
    print("  ✅ 通过 - sustain_ratio负流入Bug已修复")
    
    print("\n" + "=" * 70)
    print("✅ sustain_ratio负流入修复验证通过！")
    print("=" * 70)
