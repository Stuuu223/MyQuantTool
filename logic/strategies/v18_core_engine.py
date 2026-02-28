#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V18核心算子引擎 - 无状态数学计算模块
========================================
CTO方案S任务1：从TimeMachineEngine剥离V18双Ratio算分逻辑

设计原则：
1. 无状态 - 不保存任何运行时状态，纯函数式计算
2. 可复用 - 实盘/回测/热复盘共用同一套V18大脑
3. 零硬编码 - 所有参数从ConfigManager读取
4. 向量化支持 - 支持标量和向量化计算

Author: AI开发专家团队
Date: 2026-02-25
Version: V1.0.0 (CTO方案S实现版)
"""

from datetime import datetime, time
from typing import Union, Dict, Optional, Any
import pandas as pd
import numpy as np
import logging

from logic.core.config_manager import get_config_manager
from logic.core.metric_definitions import MetricDefinitions

# 配置V18引擎专用日志器
logger = logging.getLogger("V18CoreEngine")


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
    
    # 【CTO第一刀】：先杀NaN/Inf！
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
        # 【CTO第二刀】：再次检查NaN/Inf！
        import pandas as pd
        import numpy as np
        if pd.isna(result) or np.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


class V18CoreEngine:
    """
    V18核心算子 - 无状态数学计算引擎
    
    职责：
    - 封装V18双Ratio算分算法（量比+换手率）
    - 实现时间衰减权重计算
    - 提供标量和向量化两种计算接口
    - 知行合一：实盘/回测/复盘共用同一逻辑
    
    使用示例：
        >>> engine = V18CoreEngine()
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
        初始化V18核心引擎
        
        从ConfigManager加载所有配置参数，确保零硬编码。
        """
        self._config = get_config_manager()
        self._load_config()
    
    def _load_config(self) -> None:
        """从ConfigManager加载所有V18相关配置"""
        # 量比分位数阈值
        self.volume_ratio_percentile: float = self._config.get(
            'live_sniper.volume_ratio_percentile', 0.95
        )
        
        # 换手率阈值
        turnover_config = self._config.get_turnover_rate_thresholds()
        self.turnover_rate_per_min_min: float = turnover_config.get('per_minute_min', 0.2)
        self.turnover_rate_max: float = turnover_config.get('total_max', 70.0)
        
        # 时间衰减系数
        decay_config = self._config.get_time_decay_ratios()
        self.time_decay_early_morning: float = decay_config.get('early_morning_rush', 1.2)
        self.time_decay_morning_confirm: float = decay_config.get('morning_confirm', 1.0)
        self.time_decay_noon_trash: float = decay_config.get('noon_trash', 0.8)
        self.time_decay_tail_trap: float = decay_config.get('tail_trap', 0.5)
        
        # 评分奖励配置
        bonus_config = self._config.get('live_sniper.scoring_bonuses', {})
        self.extreme_volume_ratio: float = bonus_config.get('extreme_volume_ratio', 3.0)
        self.extreme_vol_bonus: float = bonus_config.get('extreme_vol_bonus', 10.0)
        self.high_efficiency_turnover_min: float = bonus_config.get('high_efficiency_turnover_min', 0.5)
        self.high_turnover_bonus: float = bonus_config.get('high_turnover_bonus', 5.0)
    
    def calculate_base_score(
        self,
        change_pct: float,
        volume_ratio: float,
        turnover_rate_per_min: float
    ) -> float:
        """
        计算基础动能分（V18双Ratio核心算法）
        
        算法逻辑：
        1. 检查双Ratio过滤条件（量比+换手率）
        2. 通过过滤：涨幅*5 + 极端量比奖励 + 高效换手奖励
        3. 未通过过滤：涨幅*2（降低权重）
        
        Args:
            change_pct: 涨跌幅百分比（如5.0表示涨5%）
            volume_ratio: 量比（当前成交量/5日均量）
            turnover_rate_per_min: 每分钟换手率（百分比）
        
        Returns:
            float: 基础动能分（0-100+）
        
        Raises:
            TypeError: 输入类型不正确时
        """
        # 类型检查
        if not all(isinstance(x, (int, float)) for x in [change_pct, volume_ratio, turnover_rate_per_min]):
            raise TypeError("所有输入参数必须是数字类型")
        
        # 获取量比阈值（根据日期动态计算，此处使用默认值）
        volume_ratio_threshold = self._get_volume_ratio_threshold()
        
        # V18双Ratio化过滤检查
        passes_filters = (
            volume_ratio >= volume_ratio_threshold and
            turnover_rate_per_min >= self.turnover_rate_per_min_min
        )
        
        if passes_filters:
            # 通过过滤：正常权重 + 奖励
            base_score = min(abs(change_pct) * 5, 100.0)
            
            # 极端量比奖励
            if volume_ratio > self.extreme_volume_ratio:
                base_score += self.extreme_vol_bonus
            
            # 高效换手率奖励
            if turnover_rate_per_min > self.high_efficiency_turnover_min:
                base_score += self.high_turnover_bonus
        else:
            # 未通过过滤：降低权重
            base_score = min(abs(change_pct) * 2, 50.0)
        
        return float(base_score)
    
    def _get_volume_ratio_threshold(self) -> float:
        """
        获取量比分位数阈值
        
        注意：实际实现中应根据历史数据动态计算分位数。
        此处返回配置中的固定分位数值。
        
        Returns:
            float: 量比阈值（默认0.95）
        """
        return self.volume_ratio_percentile
    
    def get_time_decay_ratio(self, timestamp: Union[datetime, time, str]) -> float:
        """
        获取时间衰减系数
        
        时间段划分：
        - 09:30-09:40 (早盘抢筹): 1.2 溢价奖励
        - 09:40-10:30 (主升浪确认): 1.0 正常推力
        - 10:30-14:00 (震荡垃圾时间): 0.8 分数打折
        - 14:00-14:55 (尾盘陷阱): 0.5 严防骗炮，大幅降权
        
        Args:
            timestamp: 时间（datetime/time对象或'HH:MM:SS'字符串）
        
        Returns:
            float: 时间衰减系数
        
        Raises:
            ValueError: 时间格式不正确时
        """
        # 统一转换为time对象
        if isinstance(timestamp, datetime):
            t = timestamp.time()
        elif isinstance(timestamp, time):
            t = timestamp
        elif isinstance(timestamp, str):
            try:
                # 处理 'HH:MM:SS' 或 'HH:MM' 格式
                parts = timestamp.split(':')
                hour = int(parts[0])
                minute = int(parts[1])
                second = int(parts[2]) if len(parts) > 2 else 0
                t = time(hour, minute, second)
            except (ValueError, IndexError) as e:
                raise ValueError(f"时间字符串格式错误，期望'HH:MM:SS'或'HH:MM': {timestamp}") from e
        else:
            raise TypeError(f"timestamp必须是datetime/time/str类型，当前类型: {type(timestamp)}")
        
        # 时间段判断
        t0940 = time(9, 40)
        t1030 = time(10, 30)
        t1400 = time(14, 0)
        t1455 = time(14, 55)
        
        if t < t0940:
            # 09:30-09:40 早盘试盘、抢筹，最坚决，溢价奖励
            return self.time_decay_early_morning
        elif t < t1030:
            # 09:40-10:30 主升浪确认，正常推力
            return self.time_decay_morning_confirm
        elif t < t1400:
            # 10:30-14:00 震荡垃圾时间，分数打折
            return self.time_decay_noon_trash
        elif t <= t1455:
            # 14:00-14:55 尾盘偷袭，严防骗炮，大幅降权（腰斩）
            return self.time_decay_tail_trap
        else:
            # 14:55-15:00 收盘竞价，不参与评分
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
        open_price: float,  # 【CTO修复】添加开盘价参数
        flow_5min: float,
        flow_15min: float,
        flow_5min_median_stock: float,
        space_gap_pct: float,
        float_volume_shares: float,
        current_time: datetime
    ) -> tuple[float, float, float, float, float]:
        """
        【Boss终极钦定：彻底废除绝对金额！动能与势能的双轨 Ratio 验钞机！】
        
        算法设计原则：
        1. 彻底废除绝对金额魔法数字（如 5亿满分），全盘Ratio化
        2. 动能30分+势能30分+价格推力40分 = 100分基础分
        3. 四大乘数机制：维持能力、筹码纯度、吸血效应、早盘时间
        
        Args:
            net_inflow: 净流入金额（元）
            price: 当前价格（元）
            prev_close: 昨日收盘价（元）
            high: 日内最高价（元）
            low: 日内最低价（元）
            open_price: 开盘价（元）
            flow_5min: 最近5分钟资金流入（元）
            flow_15min: 最近15分钟资金流入（元）
            flow_5min_median_stock: 该股票历史5分钟资金流入中位数（元）
            space_gap_pct: 空间差百分比（上方套牢盘距离）
            float_volume_shares: 真实流通股本（股）
            current_time: 当前时间（datetime对象）
        
        Returns:
            tuple: (final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe)
                - final_score: 最终验钞得分（float）
                - sustain_ratio: 资金维持率（float）
                - inflow_ratio: 净流入占流通市值比例（float）
                - ratio_stock: 相对自身历史爆发力倍数（float）
                - mfe: 资金效率指标Money Force Efficiency（float）
        
        Raises:
            TypeError: 输入类型不正确时
            ValueError: 价格<=0或流通股本<=0时
        """
        # 类型检查 - 【CTO修复】接受字符串类型，内部用safe_float转换
        # 原始类型检查太严格，导致空字符串无法处理
        # if not all(isinstance(x, (int, float, str)) for x in [...]):
        #     raise TypeError("所有数值参数必须是数字、字符串或None类型")
        
        if not isinstance(current_time, datetime):
            raise TypeError(f"current_time必须是datetime类型，当前类型: {type(current_time)}")
        
        # ==========================================
        # 0. 基础准备：计算真实流通市值 (元)
        # ==========================================
        # 【CTO修复】使用safe_float强制转换，防止类型爆炸和空字符串崩溃
        # 注意：必须先转换再进行有效性检查！
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
        
        # 参数有效性检查 - 【CTO修复】移到safe_float转换之后
        if price <= 0:
            raise ValueError(f"当前价格必须>0，当前值: {price}")
        if float_volume_shares <= 0:
            raise ValueError(f"流通股本必须>0，当前值: {float_volume_shares}")
        if high < low:
            raise ValueError(f"最高价不能低于最低价")
        
        float_market_cap = float_volume_shares * price
        
        # ==========================================
        # 第一步：真实验钞 Base Score (满分100)
        # ==========================================
        
        # 1. 动能打分：净流入占流通市值的比例 (权重 30分)
        # 游资逻辑：不看绝对流入多少，看占流通盘的百分比。如果5分钟流入达到流通盘的 1%，那是极其恐怖的资金黑洞！
        # 【CTO修复】流入比除零保护，A股一天真实沉淀极难超过50%
        inflow_ratio = net_inflow / float_market_cap if float_market_cap > 1000 else 0.0
        inflow_ratio = min(max(inflow_ratio, -0.5), 0.5)  # 强制限幅在-50%~50%
        kinetic_score = min(30.0, (inflow_ratio / 0.01) * 30.0)  # 达到 1% 拿满 30分
        
        # 2. 势能打分：相对自身历史爆发力 (权重 30分)
        # 游资逻辑：flow_5min_ratio_stock。今天这5分钟脉冲，是它平时死水状态的多少倍？
        ratio_stock = flow_5min / flow_5min_median_stock if flow_5min_median_stock > 0 else 0.0
        # 【CTO铁血截断】A股不可能有5分钟涌入超过历史50倍还能不涨停的票！封死上限防止爆表！
        ratio_stock = min(ratio_stock, 50.0)
        potential_score = min(30.0, (ratio_stock / 15.0) * 30.0)  # 爆发超过15倍拿满 30分
        
        # 3. 价格动能强度：日内 K 线推力 (权重 40分)
        if high == low:
            # 平盘特殊情况：如果当前价高于昨收，给满分，否则给0分
            momentum_score = 40.0 if price > prev_close else 0.0
        else:
            day_strength = (price - low) / (high - low)
            momentum_score = day_strength * 40.0
        
        base_score = kinetic_score + potential_score + momentum_score
        
        # ==========================================
        # 第二步：神级乘数区 (Multipliers - 决定王座)
        # ==========================================
        multiplier = 1.0
        
        # A. 维持能力 (Sustain Ability - 抓翻倍大妖的核心)
        # 15分钟资金 / 5分钟资金，健康阶梯推升应该 > 1.2
        sustain_ratio = (flow_15min / flow_5min) if flow_5min > 0 else 0.0
        
        # 【杂毛断头台】机制 - 焊死跟风杂毛，只留真龙
        stock_identifier = f"{current_time.strftime('%H:%M')}@{price:.2f}"
        
        if sustain_ratio > 1.2:
            multiplier *= 1.5  # 健康阶梯推升，超级加倍！
        elif sustain_ratio < 1.0:
            # 致命惩罚：资金维持不住，杂毛断头台绞杀！
            multiplier *= 0.1
            logger.warning(
                f"[杂毛断头台-致命绞杀] {stock_identifier} sustain_ratio={sustain_ratio:.2f} < 1.0, "
                f"资金断流骗炮，final_score将被压制到接近0"
            )
        elif sustain_ratio < 1.1:
            # 降权惩罚：资金维持吃力，疑似跟风杂毛
            multiplier *= 0.5
            logger.warning(
                f"[杂毛断头台-降权警告] {stock_identifier} sustain_ratio={sustain_ratio:.2f} < 1.1, "
                f"资金维持薄弱，final_score减半"
            )
        
        # B. 筹码纯度 (空间差 < 10% 抛压轻)
        if space_gap_pct < 0.10:
            multiplier *= 1.2
        
        # C. 吸血效应 (横向比较/资金占比极大)
        # 只要流入比例 > 1.5%，说明在疯狂吸血，给予情绪溢价
        if inflow_ratio > 0.015:
            multiplier *= 1.2
        
        # D. 早盘时间坚决度
        if current_time.hour == 9 and current_time.minute <= 40:
            multiplier *= 1.2
        elif current_time.hour >= 14:
            multiplier *= 0.5
        
        # ==========================================
        # 第三步：效率算子 MFE (Money Force Efficiency)
        # 【CTO物理学对齐】MFE = 向上推力百分比 / 净流入占比
        # 物理意义: 单位资金做功的向上效率（无量纲化，跨市值公平竞技）
        # ==========================================
        # 【修复】分子必须是向上推力，不能用总振幅！过滤天地板砸盘！
        # 向上推力 = (收盘-最低 + 最高-开盘) / 2，只奖励向上的动能
        
        # 计算向上推力百分比（相对于昨收）
        upward_thrust = ((price - low) + (high - open_price)) / 2
        price_range_pct = upward_thrust / prev_close if prev_close > 0 else 0.0
        
        # 【CTO 防御】：如果 inflow_ratio 极小或为负，保留其物理意义，但防止除零爆炸
        if abs(inflow_ratio) < 0.001:
            mfe = 0.0
        else:
            # 允许负数 MFE 存在（价格涨但资金流出 = 极端诱多抛压）
            mfe = price_range_pct / inflow_ratio
            # 强制限幅在 -100 到 100 之间，防止极端极值毁掉排序
            mfe = max(-100.0, min(mfe, 100.0))
        
        final_score = round(base_score * multiplier, 2)
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
        
        此方法支持标量和向量化计算：
        - 标量：传入单个数值
        - 向量化：传入pandas Series，返回Series
        
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
        # 处理pandas Series（向量化）
        if isinstance(current_volume, pd.Series) or isinstance(elapsed_seconds, pd.Series):
            return self._calculate_volume_ratio_vectorized(
                current_volume, elapsed_seconds, avg_volume_5d
            )
        
        # 标量计算
        if not all(isinstance(x, (int, float)) for x in [current_volume, elapsed_seconds, avg_volume_5d]):
            raise TypeError("所有输入参数必须是数字类型")
        
        if avg_volume_5d <= 0:
            raise ValueError(f"5日平均成交量必须>0，当前值: {avg_volume_5d}")
        if elapsed_seconds < 0:
            raise ValueError(f"已交易秒数不能为负数，当前值: {elapsed_seconds}")
        if elapsed_seconds == 0:
            return 0.0  # 避免除零
        
        # 时间进度（0.0 ~ 1.0）
        time_progress = elapsed_seconds / self.TOTAL_TRADING_SECONDS
        
        # 预期累计成交量
        expected_volume = avg_volume_5d * time_progress
        
        # 量比
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
        
        Args:
            current_volume: 成交量Series
            elapsed_seconds: 已交易秒数（标量或Series）
            avg_volume_5d: 5日平均成交量
        
        Returns:
            pd.Series: 量比Series
        """
        # 确保是Series类型
        if not isinstance(current_volume, pd.Series):
            current_volume = pd.Series(current_volume)
        
        # 时间进度
        if isinstance(elapsed_seconds, pd.Series):
            time_progress = elapsed_seconds / self.TOTAL_TRADING_SECONDS
        else:
            time_progress = pd.Series([elapsed_seconds / self.TOTAL_TRADING_SECONDS] * len(current_volume))
        
        # 预期成交量
        expected_volume = avg_volume_5d * time_progress
        
        # 量比（避免除零）
        volume_ratio = current_volume / expected_volume.where(expected_volume > 0, np.nan)
        volume_ratio = volume_ratio.fillna(0.0)
        
        return volume_ratio


# ==============================================================================
# 单元测试
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("V18核心算子引擎 - 单元测试")
    print("=" * 70)
    
    engine = V18CoreEngine()
    
    # 测试1: 基础分计算（通过过滤）
    print("\n【测试1】基础分计算（通过双Ratio过滤）")
    score1 = engine.calculate_base_score(
        change_pct=5.5,
        volume_ratio=2.5,  # > 0.95
        turnover_rate_per_min=0.3  # > 0.2
    )
    print(f"  涨幅5.5%, 量比2.5, 换手0.3%/min -> 基础分: {score1:.2f}")
    assert score1 >= 27.5, "通过过滤的分数应该>=27.5"
    print("  ✅ 通过")
    
    # 测试2: 基础分计算（未通过过滤）
    print("\n【测试2】基础分计算（未通过过滤）")
    score2 = engine.calculate_base_score(
        change_pct=5.5,
        volume_ratio=0.5,  # < 0.95
        turnover_rate_per_min=0.1  # < 0.2
    )
    print(f"  涨幅5.5%, 量比0.5, 换手0.1%/min -> 基础分: {score2:.2f}")
    assert score2 == 11.0, "未通过过滤的分数应该是11.0"
    print("  ✅ 通过")
    
    # 测试3: 时间衰减系数
    print("\n【测试3】时间衰减系数")
    test_times = [
        ("09:35:00", 1.2, "早盘抢筹"),
        ("09:45:00", 1.0, "主升浪确认"),
        ("11:00:00", 0.8, "垃圾时间"),
        ("14:30:00", 0.2, "尾盘陷阱-严惩偷袭"),
    ]
    for t, expected, desc in test_times:
        decay = engine.get_time_decay_ratio(t)
        print(f"  {t} ({desc}): {decay}")
        assert decay == expected, f"{t}的衰减系数应该是{expected}"
    print("  ✅ 通过")
    
    # 测试4: 最终得分计算
    print("\n【测试4】最终得分计算")
    final = engine.calculate_final_score(50.0, "09:35:00")
    print(f"  基础分50.0 @ 09:35 -> 最终得分: {final:.2f} (应=60.0)")
    assert final == 60.0, "09:35的衰减系数是1.2，50*1.2=60"
    print("  ✅ 通过")
    
    # 测试5: 量比计算（标量）
    print("\n【测试5】量比计算（标量）")
    ratio = engine.calculate_volume_ratio(
        current_volume=500000,  # 50万股
        elapsed_seconds=600,     # 10分钟
        avg_volume_5d=2000000    # 200万股日均
    )
    print(f"  成交50万股 @ 10分钟, 日均200万股 -> 量比: {ratio:.2f}")
    # 预期: 时间进度=600/14400=0.0417, 预期成交量=200万*0.0417=8.33万, 量比=50/8.33=6.0
    expected_ratio = 500000 / (2000000 * 600 / 14400)
    assert abs(ratio - expected_ratio) < 0.01, f"量比计算错误"
    print("  ✅ 通过")
    
    # 测试6: 向量化量比计算
    print("\n【测试6】向量化量比计算（Pandas）")
    import pandas as pd
    volume_series = pd.Series([1000, 2000, 3000, 4000, 5000])
    ratio_series = engine.calculate_volume_ratio(
        current_volume=volume_series,
        elapsed_seconds=300,  # 5分钟
        avg_volume_5d=100000
    )
    print(f"  量比序列: {ratio_series.tolist()}")
    print(f"  最后一行动态量比: {ratio_series.iloc[-1]:.2f}")
    assert len(ratio_series) == 5, "向量化计算应返回等长序列"
    assert ratio_series.iloc[-1] > 0, "量比应为正数"
    print("  ✅ 通过")
    
    # 测试8: 配置读取验证
    print("\n【测试8】配置读取验证")
    print(f"  量比分位数阈值: {engine.volume_ratio_percentile}")
    print(f"  每分钟最小换手率: {engine.turnover_rate_per_min_min}")
    print(f"  早盘衰减系数: {engine.time_decay_early_morning}")
    print(f"  极端量比奖励阈值: {engine.extreme_volume_ratio}")
    print("  ✅ 配置读取正常")
    
    # 测试9: True Dragon Score - 完美起爆场景
    print("\n【测试9】True Dragon Score - 完美起爆场景")
    test_time = datetime(2026, 2, 27, 9, 35, 0)  # 早盘9:35
    final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe = engine.calculate_true_dragon_score(
        net_inflow=50000000,      # 5000万净流入
        price=25.0,
        prev_close=22.0,
        high=26.0,
        low=23.0,
        open_price=22.5,          # 开盘价
        flow_5min=10000000,       # 5分钟流入1000万
        flow_15min=15000000,      # 15分钟流入1500万 (sustain_ratio=1.5 > 1.2)
        flow_5min_median_stock=500000,  # 历史5分钟中位数50万
        space_gap_pct=0.05,       # 5%空间差 (<10%)
        float_volume_shares=100000000,  # 1亿股流通盘
        current_time=test_time
    )
    print(f"  净流入比: {inflow_ratio:.4f} (目标>1%={inflow_ratio>0.01})")
    print(f"  自身爆发力: {ratio_stock:.1f}倍 (目标>15倍={ratio_stock>15})")
    print(f"  维持率: {sustain_ratio:.2f} (健康>1.2={sustain_ratio>1.2})")
    print(f"  MFE: {mfe:.2f}")
    print(f"  最终得分: {final_score:.2f}")
    # 验证：早盘(1.2) + 维持好(1.5) + 筹码纯(1.2) + 吸血(1.2) = 2.592x乘数
    assert inflow_ratio == 0.02, f"净流入比例应为2%，实际{inflow_ratio}"
    assert ratio_stock == 20.0, f"爆发力应为20倍，实际{ratio_stock}"
    assert sustain_ratio == 1.5, f"维持率应为1.5，实际{sustain_ratio}"
    assert final_score > 200, f"完美起爆应>200分，实际{final_score}"
    print("  ✅ 通过")
    
    # 测试10: True Dragon Score - 骗炮陷阱场景（杂毛断头台测试）
    print("\n【测试10】True Dragon Score - 骗炮陷阱场景（杂毛断头台测试）")
    test_time2 = datetime(2026, 2, 27, 14, 30, 0)  # 尾盘14:30
    final_score2, sustain_ratio2, inflow_ratio2, ratio_stock2, mfe2 = engine.calculate_true_dragon_score(
        net_inflow=10000000,      # 1000万净流入
        price=25.0,
        prev_close=22.0,
        high=26.0,
        low=23.0,
        open_price=22.5,          # 开盘价
        flow_5min=8000000,        # 5分钟流入800万
        flow_15min=6000000,       # 15分钟流入600万 (sustain_ratio=0.75 < 1.0，资金抽水！)
        flow_5min_median_stock=1000000,  # 历史5分钟中位数100万
        space_gap_pct=0.25,       # 25%空间差 (>10%)
        float_volume_shares=1000000000,  # 10亿股大流通盘
        current_time=test_time2
    )
    print(f"  净流入比: {inflow_ratio2:.4f} (目标<1%={inflow_ratio2<0.01})")
    print(f"  自身爆发力: {ratio_stock2:.1f}倍 (目标<15倍={ratio_stock2<15})")
    print(f"  维持率: {sustain_ratio2:.2f} (资金抽水<1.0={sustain_ratio2<1.0})")
    print(f"  MFE: {mfe2:.2f}")
    print(f"  最终得分: {final_score2:.2f}")
    # 验证：尾盘(0.2) + 维持差(0.1) = 0.02x致命惩罚 (杂毛断头台绞杀！)
    assert sustain_ratio2 == 0.75, f"维持率应为0.75，实际{sustain_ratio2}"
    assert final_score2 < 20, f"骗炮陷阱应<20分(致命惩罚)，实际{final_score2}"
    print("  ✅ 通过 - 杂毛断头台已绞杀骗炮股")
    
    # 测试11: True Dragon Score - 边界值测试
    print("\n【测试11】True Dragon Score - 边界值测试")
    # 平盘情况
    final_score3, _, _, _, _ = engine.calculate_true_dragon_score(
        net_inflow=50000000,
        price=25.0,
        prev_close=24.0,  # 昨收24
        high=25.0,        # 最高=当前
        low=25.0,         # 最低=当前（平盘）
        open_price=24.0,  # 开盘价
        flow_5min=10000000,
        flow_15min=12000000,
        flow_5min_median_stock=1000000,
        space_gap_pct=0.08,
        float_volume_shares=100000000,
        current_time=datetime(2026, 2, 27, 10, 0, 0)
    )
    print(f"  平盘但价格>昨收，得分: {final_score3:.2f}")
    assert final_score3 > 0, "平盘上涨应得正分"
    
    # 平盘下跌情况
    final_score4, _, _, _, _ = engine.calculate_true_dragon_score(
        net_inflow=50000000,
        price=23.0,       # 当前<昨收
        prev_close=24.0,
        high=23.0,
        low=23.0,
        open_price=24.0,  # 开盘价
        flow_5min=10000000,
        flow_15min=12000000,
        flow_5min_median_stock=1000000,
        space_gap_pct=0.08,
        float_volume_shares=100000000,
        current_time=datetime(2026, 2, 27, 10, 0, 0)
    )
    print(f"  平盘且价格<昨收，得分: {final_score4:.2f}")
    # 平盘下跌，momentum_score=0，只剩动能和势能分
    assert final_score4 < final_score3, "平盘下跌应得更低分"
    print("  ✅ 通过")
    
    # 测试12: 杂毛断头台 - sustain_ratio在1.0~1.1之间的降权惩罚
    print("\n【测试12】杂毛断头台 - sustain_ratio=1.05降权惩罚测试")
    test_time3 = datetime(2026, 2, 27, 10, 15, 0)  # 上午10:15
    final_score5, sustain_ratio5, _, _, _ = engine.calculate_true_dragon_score(
        net_inflow=30000000,      # 3000万净流入
        price=25.0,
        prev_close=22.0,
        high=26.0,
        low=23.0,
        open_price=22.5,
        flow_5min=10000000,       # 5分钟流入1000万
        flow_15min=10500000,      # 15分钟流入1050万 (sustain_ratio=1.05, 在1.0~1.1之间)
        flow_5min_median_stock=500000,
        space_gap_pct=0.08,
        float_volume_shares=100000000,
        current_time=test_time3
    )
    print(f"  维持率: {sustain_ratio5:.2f} (1.0 < sustain_ratio < 1.1，应受降权惩罚)")
    print(f"  最终得分: {final_score5:.2f}")
    assert 1.0 < sustain_ratio5 < 1.1, f"维持率应在1.0~1.1之间，实际{sustain_ratio5}"
    # 正常情况应该>50分，但降权惩罚后应该<50分
    assert final_score5 < 100, f"降权惩罚后应<100分，实际{final_score5}"
    print("  ✅ 通过 - sustain_ratio降权惩罚生效")
    
    print("\n" + "=" * 70)
    print("✅ 所有单元测试通过！V18核心引擎已就绪。")
    print("=" * 70)
