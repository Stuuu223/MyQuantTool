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

from logic.core.config_manager import get_config_manager
from logic.core.metric_definitions import MetricDefinitions


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
    assert score1 > 27.5, "通过过滤的分数应该>27.5"
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
        ("14:30:00", 0.5, "尾盘陷阱"),
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
    df = pd.DataFrame({
        'time': ['09:30:00', '09:31:00', '09:32:00', '09:33:00', '09:34:00'],
        'volume': [1000, 2000, 3000, 4000, 5000]
    })
    df_result = engine.calculate_volume_ratio_with_progress(df, avg_volume_5d=100000)
    print(f"  DataFrame列: {list(df_result.columns)}")
    print(f"  最后一行动态量比: {df_result['dynamic_volume_ratio'].iloc[-1]:.2f}")
    assert 'dynamic_volume_ratio' in df_result.columns
    print("  ✅ 通过")
    
    # 测试7: 寻找起爆点
    print("\n【测试7】向量化寻找起爆点")
    df2 = pd.DataFrame({
        'time': ['09:30:00', '09:31:00', '09:32:00', '09:33:00', '09:34:00'],
        'dynamic_volume_ratio': [0.5, 0.7, 0.9, 1.2, 1.5]  # 09:33突破0.95
    })
    breakout = engine.find_breakout_point(df2, volume_ratio_threshold=0.95)
    print(f"  起爆点: {breakout}")
    assert breakout is not None, "应该找到起爆点"
    assert breakout['timestamp'] == '09:33:00', "起爆时间应该是09:33:00"
    print("  ✅ 通过")
    
    # 测试8: 配置读取验证
    print("\n【测试8】配置读取验证")
    print(f"  量比分位数阈值: {engine.volume_ratio_percentile}")
    print(f"  每分钟最小换手率: {engine.turnover_rate_per_min_min}")
    print(f"  早盘衰减系数: {engine.time_decay_early_morning}")
    print(f"  极端量比奖励阈值: {engine.extreme_volume_ratio}")
    print("  ✅ 配置读取正常")
    
    print("\n" + "=" * 70)
    print("✅ 所有单元测试通过！V18核心引擎已就绪。")
    print("=" * 70)
