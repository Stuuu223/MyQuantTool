# -*- coding: utf-8 -*-
"""
【CTO V88 纯正物理引擎】无低保、无门槛的连续力场

物理真理：
- 动能 = 质量 × 速度
- 质量 = 流入资金占比
- 速度 = 价格涨跌幅（可以是负数！）
- 摩擦阻尼 = 纯度平方
- 效率激活 = MFE Sigmoid

严禁任何max/min硬编码"低保"！
"""

import math
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def safe_float(value, default=0.0) -> float:
    """安全转换为float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def calculate_true_dragon_score_v88(
    net_inflow: float,
    price: float,
    prev_close: float,
    high: float,
    low: float,
    open_price: float,
    flow_5min: float,
    flow_15min: float,
    flow_5min_median_stock: float,
    float_volume_shares: float,
    stock_code: str = "",
    current_time: datetime = None,
) -> tuple:
    """
    【CTO V88 纯正物理引擎】无低保、无门槛的连续力场
    
    物理公式：
    1. 质量 = inflow_ratio_pct * ratio_stock
    2. 速度 = 涨跌幅%（无底保！负数就是反向速度）
    3. 动能 = 质量 × 速度
    4. 摩擦阻尼 = 纯度平方
    5. 效率激活 = MFE Sigmoid
    6. 最终分数 = 动能 × 摩擦 × 效率 × 1000
    
    Returns:
        tuple: (final_score, sustain_ratio, inflow_ratio_pct, ratio_stock, mfe)
    """
    # ==================== 基础准备 ====================
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
    
    # ==================== 量纲升维 ====================
    float_market_cap = float_volume_shares * price
    
    # 【CTO V66】万股量纲自动升维
    if 0 < float_market_cap < 200000000:
        float_market_cap = float_market_cap * 10000.0
        logger.debug(f"📐 [量纲升维] {stock_code} 市值已升维至真实人民币")
    
    # ==================== 1. 质量与势能 ====================
    # 流入占比（无硬封顶，用对数软压缩）
    if float_market_cap > 1000:
        raw_inflow_pct = (net_inflow / float_market_cap * 100.0)
        # 对数软压缩，避免极端值
        if abs(raw_inflow_pct) > 30.0:
            sign = 1.0 if raw_inflow_pct > 0 else -1.0
            inflow_ratio_pct = sign * (30.0 + 10.0 * math.log10(abs(raw_inflow_pct) - 29.0))
        else:
            inflow_ratio_pct = raw_inflow_pct
    else:
        inflow_ratio_pct = 0.0
    
    # 放量倍数（用tanh自然限制，无硬截断）
    MIN_BASE_FLOW = 2000000.0
    safe_flow_5min = flow_5min if flow_5min > 0 else (flow_15min / 3.0 if flow_15min > 0 else 1.0)
    safe_median = flow_5min_median_stock if flow_5min_median_stock > 0 else MIN_BASE_FLOW
    raw_ratio_stock = safe_flow_5min / safe_median if safe_median > 0 else 1.0
    
    # 【CTO V88】用tanh自然限制，无硬截断！
    # tanh在x很大时渐近1，完美模拟边际递减
    ratio_stock = 1.0 + 6.0 * math.tanh(raw_ratio_stock - 1.0)
    
    # 质量 = 流入占比 × 放量倍数（归一化到0-1范围）
    mass_potential = (inflow_ratio_pct / 100.0) * ratio_stock
    
    # ==================== 2. 真实速度向量 ====================
    # 【CTO V88】无底保！负数就是反向速度，这是物理真理！
    velocity = (price - prev_close) / prev_close * 100.0 if prev_close > 0 else 0.0
    
    # ==================== 3. 基础动能 ====================
    # Ek = m × v（负速度产生负动能，这是正确的物理！）
    base_kinetic_energy = mass_potential * velocity
    
    # ==================== 4. 微观动量阻尼（纯度平方）====================
    price_range = high - low
    if price_range > 0:
        raw_purity = (price - low) / price_range
    else:
        # 一字板：涨给满分，跌给零分
        raw_purity = 1.0 if velocity > 0 else 0.0
    
    # 将纯度限制在 0.0 到 1.0 之间，计算平方阻尼
    friction_multiplier = min(max(raw_purity, 0.0), 1.0) ** 2
    
    # ==================== 5. 做功效率激活场（Sigmoid）====================
    if inflow_ratio_pct <= 0.0:
        efficiency_multiplier = 0.0  # 没流入就没有推升效率
        mfe = 0.0
    else:
        upward_thrust = ((price - low) + (high - open_price)) / 2
        price_range_pct = upward_thrust / prev_close * 100.0 if prev_close > 0 else 0.0
        mfe = price_range_pct / inflow_ratio_pct
        
        # 【CTO V88】MFE Sigmoid激活场
        # MFE 极大逼近 3.0，极小逼近 0。无任何if断层！
        efficiency_multiplier = 3.0 / (1.0 + math.exp(-2.0 * (mfe - 1.2)))
    
    # ==================== 6. 终极融合 ====================
    final_score_raw = base_kinetic_energy * friction_multiplier * efficiency_multiplier
    final_score = round(final_score_raw * 1000.0, 1)
    
    # 动能必须为正才算有效起爆（负动能是出货！）
    if final_score < 0:
        final_score = 0.0
    
    # ==================== Sustain计算（用于兼容）====================
    MIN_BASE_FLOW_15 = MIN_BASE_FLOW * 3.0
    safe_median_15min = flow_5min_median_stock * 3.0 if flow_5min_median_stock > 0 else MIN_BASE_FLOW_15
    sustain_ratio = flow_15min / safe_median_15min if safe_median_15min > 0 else 0.0
    
    # 引力阻尼（保留V65核心）
    float_mc_yi = float_market_cap / 100000000.0
    if float_mc_yi > 0:
        gravity_damper = 1.0 + math.log10(float_mc_yi / 50.0) * 0.5
        gravity_damper = min(max(gravity_damper, 0.5), 2.5)  # 这是合理的物理边界
    else:
        gravity_damper = 0.5
    sustain_ratio = sustain_ratio * gravity_damper
    
    # ==================== 调试日志 ====================
    logger.debug(
        f"[物理透视] {stock_code} | 质量:{mass_potential:.4f} | "
        f"速度:{velocity:.2f} | 动能:{base_kinetic_energy:.4f} | "
        f"摩擦:{friction_multiplier:.2f} | MFE乘数:{efficiency_multiplier:.2f} | "
        f"终分:{final_score}"
    )
    
    return final_score, sustain_ratio, inflow_ratio_pct, ratio_stock, mfe


# ==================== 兼容旧接口 ====================
class KineticCoreEngineV88:
    """V88物理引擎封装，兼容旧接口"""
    
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
        space_gap_pct: float = 0.0,
        float_volume_shares: float = 0.0,
        current_time: datetime = None,
        total_amount: float = 0.0,
        total_volume: float = 0.0,
        is_limit_up: bool = False,
        limit_up_queue_amount: float = 0.0,
        mode: str = "live",
        stock_code: str = "",
        is_yesterday_limit_up: bool = False,
        yesterday_vol_ratio: float = 1.0,
        vampire_ratio_pct: float = 0.0
    ) -> tuple:
        """兼容旧接口的封装"""
        return calculate_true_dragon_score_v88(
            net_inflow=net_inflow,
            price=price,
            prev_close=prev_close,
            high=high,
            low=low,
            open_price=open_price,
            flow_5min=flow_5min,
            flow_15min=flow_15min,
            flow_5min_median_stock=flow_5min_median_stock,
            float_volume_shares=float_volume_shares,
            stock_code=stock_code,
            current_time=current_time
        )
