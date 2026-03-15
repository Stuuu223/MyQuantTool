# -*- coding: utf-8 -*-
"""
【MyQuantLab 模块二】物理特征提取矩阵 (Physics Sensor Array)

核心功能：
- 利用非牛顿流体力学和经典物理学提取特征
- 彻底抛弃"价格"这种表象，只取物理量

特征传感器：
1. MFE做功效率传感器
2. 量比传感器
3. 加速度张量（二阶导数）
4. 纯度传感器（价格位置）
5. 非牛顿流体粘滞度（盘口阻力）
6. 智猪博弈信号（大猪出汗vs小猪白嫖）

Author: CTO
Date: 2026-03-14
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PhysicsFeatures:
    """物理特征集合"""
    mfe: float = 0.0  # 做功效率
    volume_ratio: float = 1.0  # 量比
    acceleration: float = 0.0  # 加速度
    purity: float = 0.5  # 纯度
    viscosity: float = 1.0  # 粘滞度
    smart_pig_score: float = 0.0  # 智猪信号分数
    
    def to_dict(self) -> Dict:
        return {
            'mfe': self.mfe,
            'volume_ratio': self.volume_ratio,
            'acceleration': self.acceleration,
            'purity': self.purity,
            'viscosity': self.viscosity,
            'smart_pig_score': self.smart_pig_score,
        }


# ============== 基础物理量提取器 ==============

def extract_mfe(
    price_range_pct: float,
    inflow_ratio_pct: float
) -> float:
    """
    【MFE做功效率传感器】
    
    MFE = 振幅百分比 / 净流入百分比
    
    物理意义：
    - MFE > 1.0: 真空无阻力状态，少量资金推动大振幅
    - MFE < 0.5: 高摩擦力状态，资金被盘口消耗
    
    Args:
        price_range_pct: 振幅百分比 ((high-low)/prev_close * 100)
        inflow_ratio_pct: 净流入百分比 (net_inflow/float_market_cap * 100)
    
    Returns:
        float: MFE值
    """
    if inflow_ratio_pct <= 0:
        return 0.0
    
    return price_range_pct / inflow_ratio_pct


def extract_volume_ratio(
    current_volume: float,
    avg_volume_5d: float
) -> float:
    """
    【量比传感器】
    
    Volume_Ratio = 今日成交量 / 5日平均成交量
    
    物理意义：
    - 量比 > 3.0: 异常放量（黄金起爆点）
    - 量比 < 1.0: 缩量（洗盘或死水）
    
    Args:
        current_volume: 今日成交量（股）
        avg_volume_5d: 5日平均成交量（股）
    
    Returns:
        float: 量比
    """
    if avg_volume_5d <= 0:
        return 1.0
    
    return current_volume / avg_volume_5d


def extract_acceleration(
    price_series: pd.Series,
    window: int = 5
) -> float:
    """
    【加速度张量】二阶导数传感器
    
    不看涨幅，看价格斜率的二阶导数
    
    物理意义：
    - acceleration > 0: 加速上涨
    - acceleration < 0: 减速/回撤
    
    Args:
        price_series: 价格序列
        window: 计算窗口
    
    Returns:
        float: 加速度值
    """
    if len(price_series) < window * 2:
        return 0.0
    
    try:
        # 一阶导数：速度
        velocity = price_series.diff().rolling(window).mean()
        
        # 二阶导数：加速度
        acceleration = velocity.diff().iloc[-1]
        
        return float(acceleration) if not pd.isna(acceleration) else 0.0
        
    except Exception:
        return 0.0


def extract_purity(
    current_price: float,
    high: float,
    low: float
) -> float:
    """
    【纯度传感器】价格位置
    
    Purity = (Price - Low) / (High - Low)
    
    物理意义：
    - Purity > 0.9: 逼空起爆临界状态
    - Purity < 0.3: 水下潜伏状态
    
    Args:
        current_price: 当前价格
        high: 最高价
        low: 最低价
    
    Returns:
        float: 纯度值 [0, 1]
    """
    if high <= low:
        return 0.5
    
    purity = (current_price - low) / (high - low)
    return max(0.0, min(1.0, purity))


# ============== 高级物理特征提取器 ==============

def extract_non_newtonian_viscosity(
    tick_df: Optional[pd.DataFrame]
) -> float:
    """
    【非牛顿流体粘滞度传感器】
    
    计算Tick级盘口厚度 / ΔPrice
    
    物理意义（非牛顿流体力学）：
    - 真龙真空区：低粘滞态，阻力极小
    - 烂板：剪切增稠（越打越硬），瞬间变成死墙
    
    Args:
        tick_df: Tick数据DataFrame
    
    Returns:
        float: 粘滞度 (0.1-10.0)
    """
    if tick_df is None or len(tick_df) < 10:
        return 1.0
    
    try:
        # 简化计算：用成交量变化率作为代理
        # 真空区：价格变动大但成交量小 → 低粘滞
        # 死墙：价格变动小但成交量大 → 高粘滞
        
        price_change = tick_df['lastPrice'].diff().abs().mean()
        volume_change = tick_df['volume'].diff().abs().mean()
        
        if price_change == 0:
            return 10.0  # 死墙
        
        # 粘滞度 = 成交量变化 / 价格变化
        # 高粘滞 = 大量成交但价格不动
        viscosity = volume_change / (price_change + 1e-6)
        
        # 归一化到 [0.1, 10.0]
        return max(0.1, min(10.0, viscosity / 1000))
        
    except Exception:
        return 1.0


def extract_smart_pig_signal(
    minute_df: Optional[pd.DataFrame],
    vwap: Optional[float] = None
) -> Tuple[float, str]:
    """
    【智猪博弈信号提取器】
    
    识别形态：
    1. 大猪出汗模型：在VWAP下方爆出天量，硬生生把价格推上水面
    2. 小猪白嫖模型：放量突破后，极度缩量+极大涨幅（MFE畸高）的滑行段
    
    Args:
        minute_df: 分K数据
        vwap: 成交均价
    
    Returns:
        Tuple[float, str]: (信号分数, 信号类型)
    """
    if minute_df is None or len(minute_df) < 30:
        return 0.0, "unknown"
    
    try:
        # 计算早盘vs午盘的资金分布
        total_bars = len(minute_df)
        morning_bars = min(120, total_bars // 2)  # 前120根 = 2小时
        
        morning_volume = minute_df['volume'].iloc[:morning_bars].sum()
        afternoon_volume = minute_df['volume'].iloc[morning_bars:].sum()
        
        morning_amount = minute_df['amount'].iloc[:morning_bars].sum()
        afternoon_amount = minute_df['amount'].iloc[morning_bars:].sum()
        
        total_volume = morning_volume + afternoon_volume
        total_amount = morning_amount + afternoon_amount
        
        if total_volume == 0:
            return 0.0, "unknown"
        
        morning_ratio = morning_volume / total_volume
        
        # 计算价格变化
        open_price = minute_df['open'].iloc[0]
        close_price = minute_df['close'].iloc[-1]
        high_price = minute_df['high'].max()
        low_price = minute_df['low'].min()
        
        daily_change = (close_price - open_price) / open_price * 100 if open_price > 0 else 0
        
        # 大猪出汗特征：早盘爆量拉升
        if morning_ratio > 0.6 and daily_change > 5:
            return morning_ratio * 100, "heavy_lifter"
        
        # 小猪白嫖特征：早盘放量突破后，午后缩量滑行
        if morning_ratio > 0.5 and afternoon_volume > 0:
            vol_ratio = morning_volume / afternoon_volume
            if vol_ratio > 2.0 and daily_change > 3:
                return vol_ratio * 20, "smart_pig"
        
        return 0.0, "normal"
        
    except Exception as e:
        logger.debug(f"[SmartPig] 计算失败: {e}")
        return 0.0, "error"


# ============== 综合特征提取器 ==============

# ⚠️ [DEAD CODE] 此函数在整个仓库中零调用。
# 禁止在此函数中增加任何 Pandas/DataFrame 操作。
# 仅保留作为物理铁律的参考实现。
def extract_all_features(
    sample  # HolographicSample
) -> PhysicsFeatures:
    """
    从全息样本中提取所有物理特征
    
    ⚠️ [ARCHITECTURE WARNING] 此函数依赖 HolographicSample 复杂数据舱，
    引入了 DataFrame 依赖。当前实盘引擎使用标量参数版本的独立函数，
    如 extract_purity(close, high, low) 而非 DataFrame 操作。
    
    Args:
        sample: HolographicSample 全息数据舱
    
    Returns:
        PhysicsFeatures: 物理特征集合
    """
    features = PhysicsFeatures()
    
    try:
        # 从日K提取宏观特征
        if sample.macro_daily is not None and len(sample.macro_daily) >= 5:
            daily = sample.macro_daily
            
            # 量比
            current_vol = daily['volume'].iloc[-1]
            avg_vol_5d = daily['volume'].iloc[-6:-1].mean()
            features.volume_ratio = extract_volume_ratio(current_vol, avg_vol_5d)
        
        # 从分K提取中观特征
        if sample.meso_minute is not None and len(sample.meso_minute) >= 30:
            minute = sample.meso_minute
            
            # 当日分K
            today_minute = minute[minute.index.strftime('%Y%m%d') == sample.date]
            
            if len(today_minute) > 0:
                # 纯度
                high = today_minute['high'].max()
                low = today_minute['low'].min()
                close = today_minute['close'].iloc[-1]
                features.purity = extract_purity(close, high, low)
                
                # 加速度
                features.acceleration = extract_acceleration(today_minute['close'])
                
                # 智猪信号
                features.smart_pig_score, _ = extract_smart_pig_signal(today_minute)
        
        # 从Tick提取微观特征
        if sample.micro_tick is not None and len(sample.micro_tick) >= 10:
            features.viscosity = extract_non_newtonian_viscosity(sample.micro_tick)
        
    except Exception as e:
        logger.error(f"[PhysicsSensors] 特征提取失败: {e}")
    
    return features


# ============== 已验证的物理铁律 (V92/V100/V158) ==============

def extract_time_decay_factor(
    minutes_from_open: int
) -> float:
    """
    【时间衰减因子】(V100已验证)
    
    时间 = 能量耗散的刻度
    
    物理意义：
    - 早盘(0-10min): 1.2x 克服最大重力冲天而起
    - 上午(10-60min): 1.0x 正常推力确认主升
    - 午间(60-210min): 0.8x 垃圾时间分数量打折
    - 尾盘(210-240min): 0.2x 陷阱严防骗炮
    
    Args:
        minutes_from_open: 开盘后分钟数 (09:30 = 0)
    
    Returns:
        float: 时间衰减因子
    """
    if minutes_from_open < 10:
        return 1.2  # 早盘冲刺
    elif minutes_from_open < 60:
        return 1.0  # 上午确认
    elif minutes_from_open < 210:
        return 0.8  # 午间垃圾时间
    else:
        return 0.2  # 尾盘陷阱


def extract_dynamic_friction(
    purity: float,
    minutes_from_open: int,
    is_gravitational_escape: bool = False
) -> float:
    """
    【时间动态阻尼场】(V92/V100已验证)
    
    纯度次方的物理意义：
    - 早盘: purity ** 2 温和阻尼
    - 盘中: purity ** 3 中等阻尼
    - 午后: purity ** 5 极刑阻尼
    
    物理验证：高MFE高量比组胜率73.9% vs 低组50.1%，EV差异+2.40%
    
    Args:
        purity: 纯度值 [0, 1]
        minutes_from_open: 开盘后分钟数
        is_gravitational_escape: 是否重力逃逸（豁免）
    
    Returns:
        float: 摩擦因子 [0, 1]
    """
    # 边界保护
    purity = max(0.0, min(1.0, purity))
    
    # 重力逃逸豁免
    if is_gravitational_escape:
        return purity ** 1.5  # 豁免后温和
    
    # 时间动态阻尼
    if minutes_from_open < 60:
        # 早盘：温和
        return purity ** 2
    elif minutes_from_open < 210:
        # 盘中：中等
        return purity ** 3
    else:
        # 午后：极刑
        return purity ** 5


def extract_overdraft_multiplier(
    yesterday_vol_ratio: float,
    min_limit: float | None = None,
    log_coefficient: float | None = None
) -> float:
    """
    【透支效应乘数】(V158已验证)
    
    物理真相：昨日量比越高，今日开盘溢价越低！
    
    回归结果(8014样本):
    - 量比95th(8.2x)次日溢价仅+1.19%
    - 量比50th(1.0x)次日溢价+4.67%
    
    ⚠️ `min_limit` 和 `log_coefficient` 为待定超参，必须由上层注入！
    从 config_manager.get('kinetic_physics.overdraft_min_limit') 获取。
    禁止使用魔法默认值！

    Args:
        yesterday_vol_ratio: 昨日量比
        min_limit: 乘数下界（必须注入，从config读取）
        log_coefficient: 对数衰减系数（必须注入，从config读取）
    
    Returns:
        float: 溢出乘数 [min_limit, 1.0]
    
    Raises:
        ValueError: 如果参数未注入
    """
    import math
    
    # 【CTO V184】强制要求上层注入参数，禁止魔法默认值
    if min_limit is None or log_coefficient is None:
        raise ValueError(
            "min_limit 和 log_coefficient 必须由上层注入！"
            "从 config_manager.get('kinetic_physics.overdraft_min_limit') 获取。"
            "禁止使用魔法默认值。"
        )
    
    if yesterday_vol_ratio <= 1.0:
        return 1.0
    
    # 负相关：量比越高，乘数越低
    return max(min_limit, 1.0 - math.log10(1.0 + yesterday_vol_ratio) * log_coefficient)


# 导出已验证铁律
VALIDATED_LAWS = {
    'time_decay': extract_time_decay_factor,
    'dynamic_friction': extract_dynamic_friction,
    'overdraft_multiplier': extract_overdraft_multiplier,
}


# ============== 正确使用方式示例 ==============
# 
# 【CTO V184 架构指南】
# 
# 实盘引擎应使用标量参数版本的独立函数，而非 DataFrame 依赖版本：
#
# ✅ 正确用法：
#   from logic.core.physics_sensors import (
#       extract_purity,           # 纯度：(close-low)/(high-low)
#       extract_volume_ratio,     # 量比：current_vol / avg_vol_5d
#       extract_mfe_efficiency,   # MFE做功效率
#       extract_time_decay_factor, # 时间衰减
#       extract_overdraft_multiplier, # 透支效应
#   )
#
#   # 在实盘引擎的 _on_tick_data 中：
#   purity = extract_purity(current_price, today_high, today_low)
#   vol_ratio = extract_volume_ratio(current_volume, avg_volume_5d)
#   
#   # 透支效应需要注入config参数：
#   from logic.core.config_manager import get_config_manager
#   cfg = get_config_manager()
#   overdraft = extract_overdraft_multiplier(
#       yesterday_vol_ratio,
#       min_limit=cfg.get('kinetic_physics.overdraft_min_limit', 0.5),
#       log_coefficient=cfg.get('kinetic_physics.overdraft_log_coeff', 0.5)
#   )
#
# ❌ 禁止用法：
#   # 不要使用 extract_all_features，它依赖复杂的 HolographicSample
#   features = extract_all_features(sample)  # ❌ DataFrame 依赖
#
# ⚠️ 架构原则：
#   1. 实盘引擎追求 O(1) 时间复杂度
#   2. 避免 DataFrame 操作带来的内存分配开销
#   3. 使用标量参数，便于 JIT 编译优化
#   4. 配置参数必须从 SSOT 注入，禁止魔法默认值
