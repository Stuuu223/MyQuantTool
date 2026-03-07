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
        total_volume: float = 0.0
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
        
        if price <= 0:
            raise ValueError(f"当前价格必须>0，当前值: {price}")
        if float_volume_shares <= 0:
            raise ValueError(f"流通股本必须>0，当前值: {float_volume_shares}")
        if high < low:
            raise ValueError(f"最高价不能低于最低价")
        
        float_market_cap = float_volume_shares * price
        
        # 第一步：【CTO V51 里氏震级模型】无上限乘法动能！
        # 废除加法凑分，改用乘法爆发：base_power = 流入占比 × 放量倍数
        # 让龙中龙自然冲破天花板，无需硬性上限！
        
        # 1. 流入占比百分比（保留极端值裁剪防止溢出）
        inflow_ratio_pct = (net_inflow / float_market_cap * 100.0) if float_market_cap > 1000 else 0.0
        inflow_ratio_pct = min(max(inflow_ratio_pct, -50.0), 50.0)  # 仅防溢出，非打分上限
        inflow_ratio = inflow_ratio_pct  # 返回百分比形式
        
        # 2. 相对历史放量倍数（放大历史爆发力）
        safe_flow_5min = flow_5min if flow_5min > 0 else (flow_15min / 3.0 if flow_15min > 0 else 1.0)
        ratio_stock = safe_flow_5min / flow_5min_median_stock if flow_5min_median_stock > 0 else 1.0
        ratio_stock = max(0.01, min(ratio_stock, 100.0))  # 防溢出上限100倍
        
        # 3. 价格推力（日内强度0-1）
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
        
        # 加上基础分（涨停板基础加成）
        base_power += 40.0 if price > prev_close and price_strength >= 0.99 else 0.0
        
        # 第二步：出货拦截（净流出封顶40分）
        is_net_outflow = inflow_ratio_pct <= 0
        
        # 第三步：VWAP洗盘容错（跌破VWAP -20分，不清零）
        vwap_penalty = 0.0
        if total_volume > 0 and total_amount > 0:
            vwap = total_amount / total_volume
            if price < vwap and vwap > 0:
                vwap_penalty = 20.0
                logger.debug(f"[VWAP洗盘容错] 价格{price:.2f} < VWAP{vwap:.2f}, 重罚-20分")
        
        base_power = max(0.0, base_power - vwap_penalty)
        
        # 第四步：神级乘数区
        multiplier = 1.0
        
        # A. 维持能力（sustain_ratio）
        # 【CTO修复20260304】独立窗口：排除前5分钟累计
        # flow_next_10min = 09:35-09:45独立流入（非累计）
        # 【CTO P0级修复20260304-II】修复负流入Bug
        if flow_5min <= 0:
            # 前5分钟净流出，直接标记为负维持率，触发绞杀
            sustain_ratio = -1.0  # 致命信号
            logger.warning(f"[杂毛断头台-前期净流出] flow_5min={flow_5min:.0f}元 <= 0，sustain_ratio强制=-1.0")
        else:
            flow_next_10min = flow_15min - flow_5min
            sustain_ratio = (flow_next_10min / flow_5min) if flow_5min > 0 else 1.0
            sustain_ratio = max(-10.0, min(sustain_ratio, 10.0))
        
        stock_identifier = f"{current_time.strftime('%H:%M')}@{price:.2f}"
        
        if sustain_ratio > 1.2:
            multiplier *= 1.5  # 健康阶梯推升
        elif sustain_ratio < 1.0:
            multiplier *= 0.1  # 资金退潮：杂毛断头台绞杀
            logger.warning(f"[杂毛断头台-致命绞杀] {stock_identifier} sustain_ratio={sustain_ratio:.2f} < 1.0")
        elif sustain_ratio < 1.1:
            multiplier *= 0.5  # 维持吃力：降权警告
            logger.warning(f"[杂毛断头台-降权警告] {stock_identifier} sustain_ratio={sustain_ratio:.2f} < 1.1")
        # [1.1, 1.2] 区间：资金维持正常但未加速，multiplier不变（设计意图：观察等待）
        
        # B. 筹码纯度（空间差 < 10% 抛压轻）
        if space_gap_pct < 0.10:
            multiplier *= 1.2
        
        # C. 吸血效应（流入比例 > 1.5% ← 百分比形式）
        if inflow_ratio_pct > 1.5:
            multiplier *= 1.2
        
        # D. 早盘时间坚决度
        if current_time.hour == 9 and current_time.minute <= 40:
            multiplier *= 1.2
        elif current_time.hour >= 14:
            multiplier *= 0.5
        
        # 第五步：MFE效率算子
        if inflow_ratio_pct <= 0:
            mfe = -100.0
        else:
            upward_thrust = ((price - low) + (high - open_price)) / 2
            price_range_pct = upward_thrust / prev_close if prev_close > 0 else 0.0
            mfe = price_range_pct / (inflow_ratio_pct / 100.0)
            mfe = max(-100.0, min(mfe, 100.0))
        
        # 第六步：最终得分（无上限里氏震级！）
        final_score = round(base_power * multiplier, 2)
        
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
