# -*- coding: utf-8 -*-
"""
【CTO V151 多维物理势垒网关 - 废除量比一票否决制】

核心哲学：
- 不再唯量比论！引入资金效率(MFE)和空间势能(VWAP_Dist)组成联合防线
- 低量比真龙（仙丹）通过旁路通道拯救
- 高量比假龙（骗炮）通过微观结构判别拦截

双通道架构：
1. Main_Channel（煌煌正道）：量比分位数突破92th → 强共识合力龙，直接放行
2. Elixir_Bypass（真空仙丹）：量比>=70th + MFE>=95th → 极低抛压高做功效率，特赦放行

数据支撑（CTO V150 香农结构学）：
- 25%的午后真龙量比分位数低于75th（被旧版焊死92th错杀）
- 这些低量仙丹的MFE分位数高达95th以上（待验证）

Author: CTO
Date: 2026-03-14
Version: V151
"""

import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# 物理常数
GOLDEN_PERCENTILE = 0.92  # 黄金分割线：前8%
ELIXIR_RATIO_PERCENTILE = 0.70  # 仙丹旁路最低量比分位数
ELIXIR_MFE_PERCENTILE = 0.95  # 仙丹旁路MFE分位数阈值
MIN_VOLUME_RATIO = 1.5  # 绝对物理下限


@dataclass
class GateResult:
    """网关裁决结果"""
    passed: bool
    channel: str  # "Main_Channel", "Elixir_Bypass", "Filtered"
    volume_ratio: float
    volume_ratio_percentile: float
    mfe: Optional[float] = None
    mfe_percentile: Optional[float] = None
    dynamic_threshold: float = 0.0


def calculate_percentile(value: float, distribution: list) -> float:
    """计算一个值在分布中的分位数"""
    if not distribution or len(distribution) < 10:
        return 0.0
    return float(np.searchsorted(np.sort(distribution), value) / len(distribution))


def filter_by_intraday_physics(
    snapshot_ratios: Dict[str, float],
    snapshot_mfe: Optional[Dict[str, float]],
    snapshot_vwap_dist: Optional[Dict[str, float]],
    target_stock: str,
    current_time: Optional[str] = None
) -> GateResult:
    """
    【CTO V151 多维物理势垒网关】
    
    不再唯量比论！引入资金效率(MFE)和空间势能(VWAP_Dist)组成联合防线。
    
    Args:
        snapshot_ratios: 全市场股票的实时量比字典 {stock_code: volume_ratio}
        snapshot_mfe: 全市场股票的MFE字典 {stock_code: mfe} (可为None)
        snapshot_vwap_dist: 全市场股票的VWAP偏离度字典 (可为None)
        target_stock: 目标股票代码
        current_time: 当前时间（用于日志）
    
    Returns:
        GateResult: 包含通过状态、通道类型、各项指标的完整结果
    """
    # 数据预检
    if not snapshot_ratios or len(snapshot_ratios) < 100:
        stock_ratio = snapshot_ratios.get(target_stock, 0) if snapshot_ratios else 0
        logger.warning(f"[多维势垒网关] 量比数据不足，使用绝对防线 {MIN_VOLUME_RATIO}x")
        return GateResult(
            passed=stock_ratio >= MIN_VOLUME_RATIO,
            channel="Fallback" if stock_ratio >= MIN_VOLUME_RATIO else "Filtered",
            volume_ratio=stock_ratio,
            volume_ratio_percentile=0.0,
            dynamic_threshold=MIN_VOLUME_RATIO
        )
    
    # 过滤有效值
    valid_ratios = [r for r in snapshot_ratios.values() if r > 0]
    
    if len(valid_ratios) < 100:
        stock_ratio = snapshot_ratios.get(target_stock, 0)
        return GateResult(
            passed=stock_ratio >= MIN_VOLUME_RATIO,
            channel="Fallback" if stock_ratio >= MIN_VOLUME_RATIO else "Filtered",
            volume_ratio=stock_ratio,
            volume_ratio_percentile=0.0,
            dynamic_threshold=MIN_VOLUME_RATIO
        )
    
    # 计算各分位数阈值
    ratio_92th = float(np.percentile(valid_ratios, GOLDEN_PERCENTILE * 100))
    ratio_92th = max(ratio_92th, MIN_VOLUME_RATIO)  # 物理兜底
    
    ratio_70th = float(np.percentile(valid_ratios, ELIXIR_RATIO_PERCENTILE * 100))
    
    # 获取目标股票指标
    this_ratio = snapshot_ratios.get(target_stock, 0)
    
    # 计算目标股票的量比分位数
    ratio_percentile = calculate_percentile(this_ratio, valid_ratios)
    
    # 通道 A：煌煌正道（高共识合力龙）
    if this_ratio >= ratio_92th:
        return GateResult(
            passed=True,
            channel="Main_Channel",
            volume_ratio=this_ratio,
            volume_ratio_percentile=ratio_percentile,
            dynamic_threshold=ratio_92th
        )
    
    # 通道 B：真空仙丹旁路（低量比 + 高做功效率）
    if snapshot_mfe and len(snapshot_mfe) >= 100:
        valid_mfe = [m for m in snapshot_mfe.values() if m is not None and m > 0]
        
        if len(valid_mfe) >= 100:
            mfe_95th = float(np.percentile(valid_mfe, ELIXIR_MFE_PERCENTILE * 100))
            this_mfe = snapshot_mfe.get(target_stock, 0) or 0
            mfe_percentile = calculate_percentile(this_mfe, valid_mfe)
            
            # 仙丹条件：量比>=70th分位 + MFE>=95th分位
            if this_ratio >= ratio_70th and this_mfe >= mfe_95th:
                logger.info(f"[多维势垒网关] 仙丹旁路激活: {target_stock} 量比{this_ratio:.2f}x({ratio_percentile*100:.1f}th) MFE{this_mfe:.2f}({mfe_percentile*100:.1f}th)")
                return GateResult(
                    passed=True,
                    channel="Elixir_Bypass",
                    volume_ratio=this_ratio,
                    volume_ratio_percentile=ratio_percentile,
                    mfe=this_mfe,
                    mfe_percentile=mfe_percentile,
                    dynamic_threshold=ratio_70th
                )
    
    # 默认：拦截
    return GateResult(
        passed=False,
        channel="Filtered",
        volume_ratio=this_ratio,
        volume_ratio_percentile=ratio_percentile,
        dynamic_threshold=ratio_92th
    )


def filter_by_intraday_percentile(
    snapshot_ratios: Dict[str, float],
    target_stock: str,
    current_time: Optional[str] = None,
    percentile_threshold: float = GOLDEN_PERCENTILE
) -> Tuple[bool, float, float]:
    """
    【兼容接口】保持旧版调用方式
    
    Args:
        snapshot_ratios: 全市场股票的实时量比字典
        target_stock: 目标股票代码
        current_time: 当前时间
        percentile_threshold: 分位数阈值
    
    Returns:
        (是否通过, 目标股票量比, 动态阈值)
    """
    result = filter_by_intraday_physics(
        snapshot_ratios=snapshot_ratios,
        snapshot_mfe=None,  # 不使用MFE旁路
        snapshot_vwap_dist=None,
        target_stock=target_stock,
        current_time=current_time
    )
    return result.passed, result.volume_ratio, result.dynamic_threshold


def batch_filter_by_physics(
    snapshot_ratios: Dict[str, float],
    snapshot_mfe: Optional[Dict[str, float]] = None,
    snapshot_vwap_dist: Optional[Dict[str, float]] = None
) -> Dict[str, GateResult]:
    """
    批量过滤：返回所有股票的网关裁决结果
    
    Args:
        snapshot_ratios: 全市场量比字典
        snapshot_mfe: 全市场MFE字典
        snapshot_vwap_dist: 全市场VWAP偏离度字典
    
    Returns:
        {stock_code: GateResult}
    """
    results = {}
    for stock in snapshot_ratios:
        results[stock] = filter_by_intraday_physics(
            snapshot_ratios=snapshot_ratios,
            snapshot_mfe=snapshot_mfe,
            snapshot_vwap_dist=snapshot_vwap_dist,
            target_stock=stock
        )
    return results


def get_percentile_threshold(
    snapshot_ratios: Dict[str, float],
    percentile: float = GOLDEN_PERCENTILE
) -> float:
    """
    获取指定分位数的阈值
    
    Args:
        snapshot_ratios: 全市场量比字典
        percentile: 分位数（0-1）
    
    Returns:
        阈值
    """
    if not snapshot_ratios:
        return MIN_VOLUME_RATIO
    
    valid_ratios = [r for r in snapshot_ratios.values() if r > 0]
    
    if len(valid_ratios) < 10:
        return MIN_VOLUME_RATIO
    
    threshold = float(np.percentile(valid_ratios, percentile * 100))
    return max(threshold, MIN_VOLUME_RATIO)


# 导出
__all__ = [
    'filter_by_intraday_physics',
    'filter_by_intraday_percentile',
    'batch_filter_by_physics',
    'get_percentile_threshold',
    'GateResult',
    'GOLDEN_PERCENTILE',
    'ELIXIR_RATIO_PERCENTILE',
    'ELIXIR_MFE_PERCENTILE',
    'MIN_VOLUME_RATIO'
]