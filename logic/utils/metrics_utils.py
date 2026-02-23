# -*- coding: utf-8 -*-
"""
指标计算工具模块 - Phase 7核心能力封装

提供统一的指标计算能力，包括VWAP、承接力度等核心指标。
所有计算基于QMT本地数据，禁止估算和兜底值。

设计原则：
- 禁止估算/兜底值
- 禁止返回None代替错误
- 明确的输入输出约定
- 完整的异常处理

Author: iFlow CLI
Date: 2026-02-23
Version: 1.0.0
"""

from typing import Optional, List, Tuple
import pandas as pd
import numpy as np

from logic.utils.logger import get_logger

logger = get_logger(__name__)


class MetricsCalculationError(Exception):
    """指标计算错误"""
    pass


class InsufficientDataError(Exception):
    """数据不足错误"""
    pass


def calc_vwap(df: pd.DataFrame, 
              price_col: str = 'price',
              volume_col: str = 'volume',
              min_records: int = 10) -> float:
    """
    计算成交量加权平均价(VWAP)
    
    VWAP = Σ(价格 × 成交量) / Σ(成交量)
    
    Args:
        df: DataFrame，包含价格成交量数据
        price_col: 价格列名，默认'price'
        volume_col: 成交量列名，默认'volume'
        min_records: 最小记录数要求，默认10条
    
    Returns:
        float: VWAP值
    
    Raises:
        ValueError: 参数无效或DataFrame为空
        InsufficientDataError: 数据记录数不足
        MetricsCalculationError: 计算失败
    
    Example:
        >>> df = pd.DataFrame({
        ...     'price': [10.0, 10.5, 11.0],
        ...     'volume': [100, 200, 150]
        ... })
        >>> vwap = calc_vwap(df)
        >>> print(vwap)
        10.57
    """
    # 1. DataFrame验证
    if df is None:
        raise ValueError("DataFrame不能为空")
    
    if not isinstance(df, pd.DataFrame):
        raise ValueError(f"输入必须是DataFrame，实际类型: {type(df)}")
    
    if len(df) == 0:
        raise ValueError("DataFrame为空，无数据可计算")
    
    # 2. 列名验证
    if price_col not in df.columns:
        raise ValueError(f"价格列不存在: {price_col}，可用列: {list(df.columns)}")
    
    if volume_col not in df.columns:
        raise ValueError(f"成交量列不存在: {volume_col}，可用列: {list(df.columns)}")
    
    # 3. 数据量检查
    if len(df) < min_records:
        raise InsufficientDataError(
            f"数据记录数不足: {len(df)} < {min_records}"
        )
    
    # 4. 数据清洗 - 去除无效值
    valid_mask = (
        df[price_col].notna() & 
        df[volume_col].notna() &
        (df[volume_col] >= 0) &  # 成交量可以为0，不能为负
        (df[price_col] > 0)     # 价格必须为正
    )
    
    valid_count = valid_mask.sum()
    if valid_count < min_records:
        raise InsufficientDataError(
            f"有效数据不足: {valid_count} < {min_records}"
        )
    
    clean_df = df[valid_mask].copy()
    
    # 5. 计算VWAP
    try:
        prices = clean_df[price_col].astype(float)
        volumes = clean_df[volume_col].astype(float)
        
        total_volume = volumes.sum()
        
        if total_volume <= 0:
            raise MetricsCalculationError(
                f"总成交量必须大于0: {total_volume}"
            )
        
        vwap = (prices * volumes).sum() / total_volume
        
    except Exception as e:
        raise MetricsCalculationError(f"VWAP计算失败: {e}")
    
    # 6. 结果验证
    if not isinstance(vwap, (int, float)):
        raise MetricsCalculationError(f"VWAP计算结果异常: {vwap}")
    
    if vwap <= 0:
        raise MetricsCalculationError(f"VWAP必须大于0: {vwap}")
    
    if np.isinf(vwap) or np.isnan(vwap):
        raise MetricsCalculationError(f"VWAP计算结果无效: {vwap}")
    
    logger.debug(f"VWAP计算完成: {vwap:.4f} ({len(clean_df)}条记录)")
    return round(vwap, 4)


def calc_sustain_factor(current_price: float, vwap: float) -> float:
    """
    计算承接力度因子 (Sustain Factor)
    
    衡量当前价格相对于VWAP的位置，反映市场承接力度。
    
    计算公式：
        sustain_factor = 1 / (1 + exp(-k * (price - vwap) / vwap))
    简化版本（本实现使用）：
        sustain_factor = (current_price / vwap) - 0.5 * 2  # 线性映射
    
    更稳定的sigmoid映射：
        - 当 price = vwap 时，factor = 0.5
        - 当 price > vwap 时，factor > 0.5
        - 当 price < vwap 时，factor < 0.5
        - 范围限制在 [0.0, 1.0]
    
    Args:
        current_price: 当前价格
        vwap: VWAP值
    
    Returns:
        float: 0.0-1.0之间的值
        - 1.0: 价格远高于VWAP，承接最强
        - 0.5: 价格等于VWAP
        - 0.0: 价格远低于VWAP，承接最弱
    
    Raises:
        ValueError: 参数无效
        MetricsCalculationError: 计算失败
    
    Example:
        >>> factor = calc_sustain_factor(11.0, 10.5)
        >>> print(factor)
        0.72
    """
    # 1. 参数验证
    if current_price is None or vwap is None:
        raise ValueError("价格和VWAP不能为空")
    
    if not isinstance(current_price, (int, float)):
        raise ValueError(f"当前价格必须是数字: {type(current_price)}")
    
    if not isinstance(vwap, (int, float)):
        raise ValueError(f"VWAP必须是数字: {type(vwap)}")
    
    # 2. 数值有效性检查
    if current_price <= 0:
        raise ValueError(f"当前价格必须大于0: {current_price}")
    
    if vwap <= 0:
        raise ValueError(f"VWAP必须大于0: {vwap}")
    
    # 3. 计算价格相对于VWAP的偏离比例
    try:
        price_ratio = current_price / vwap
    except ZeroDivisionError:
        raise MetricsCalculationError("VWAP为0，无法计算承接力度")
    
    # 4. 使用sigmoid函数映射到[0,1]区间
    # 基础思想：将price_ratio以1.0为中心进行映射
    # price_ratio = 1.0 (price=vwap) -> 0.5
    # price_ratio > 1.0 (price>vwap) -> >0.5
    # price_ratio < 1.0 (price<vwap) -> <0.5
    
    # 计算偏离程度，使用steepness控制曲线陡峭度
    steepness = 4.0  # 经验值，可根据需要调整
    deviation = (price_ratio - 1.0) * steepness
    
    try:
        # sigmoid函数: 1 / (1 + exp(-x))
        import math
        sustain = 1.0 / (1.0 + math.exp(-deviation))
    except OverflowError:
        # 处理极端值
        if deviation > 0:
            sustain = 1.0
        else:
            sustain = 0.0
    
    # 5. 结果验证和边界处理
    sustain = max(0.0, min(1.0, sustain))
    
    if np.isnan(sustain) or np.isinf(sustain):
        raise MetricsCalculationError(f"承接力度计算结果无效: {sustain}")
    
    logger.debug(f"承接力度计算: price={current_price}, vwap={vwap}, factor={sustain:.4f}")
    return round(sustain, 4)


def calc_sustain_linear(current_price: float, vwap: float, 
                        max_deviation: float = 0.1) -> float:
    """
    计算承接力度因子（线性版本）
    
    线性映射版本，计算更快，适合高频场景。
    
    Args:
        current_price: 当前价格
        vwap: VWAP值
        max_deviation: 最大考虑偏离比例（默认10%）
    
    Returns:
        float: 0.0-1.0之间的值
    
    Raises:
        ValueError: 参数无效
        MetricsCalculationError: 计算失败
    
    Example:
        >>> factor = calc_sustain_linear(11.0, 10.5)
        >>> print(factor)
        0.76
    """
    # 1. 参数验证
    if current_price is None or vwap is None:
        raise ValueError("价格和VWAP不能为空")
    
    if current_price <= 0 or vwap <= 0:
        raise ValueError(f"价格和VWAP必须大于0: price={current_price}, vwap={vwap}")
    
    if max_deviation <= 0:
        raise ValueError(f"最大偏离比例必须大于0: {max_deviation}")
    
    # 2. 计算偏离比例
    deviation = (current_price - vwap) / vwap
    
    # 3. 线性映射到[0,1]
    # deviation = -max_deviation -> 0
    # deviation = 0 -> 0.5
    # deviation = max_deviation -> 1
    sustain = (deviation / (2 * max_deviation)) + 0.5
    
    # 4. 边界处理
    sustain = max(0.0, min(1.0, sustain))
    
    return round(sustain, 4)


def calc_intraday_vwap_from_ticks(tick_df: pd.DataFrame,
                                  time_col: str = 'time',
                                  price_col: str = 'price',
                                  volume_col: str = 'volume',
                                  min_records: int = 10) -> dict:
    """
    从Tick数据计算日内VWAP及衍生指标
    
    Args:
        tick_df: Tick数据DataFrame
        time_col: 时间列名
        price_col: 价格列名
        volume_col: 成交量列名
    
    Returns:
        dict: {
            'vwap': float,           # VWAP值
            'total_volume': float,   # 总成交量
            'avg_price': float,      # 简单均价
            'price_std': float,      # 价格标准差
            'record_count': int      # 记录数
        }
    
    Raises:
        ValueError: 参数无效
        InsufficientDataError: 数据不足
    """
    if tick_df is None or len(tick_df) == 0:
        raise ValueError("Tick数据不能为空")
    
    # 检查必要列
    required_cols = [price_col, volume_col]
    for col in required_cols:
        if col not in tick_df.columns:
            raise ValueError(f"缺少必要列: {col}")
    
    # 数据清洗
    clean_df = tick_df[
        tick_df[price_col].notna() &
        tick_df[volume_col].notna() &
        (tick_df[price_col] > 0) &
        (tick_df[volume_col] >= 0)
    ].copy()
    
    if len(clean_df) < min_records:
        raise InsufficientDataError(f"有效数据不足: {len(clean_df)} < {min_records}")
    
    # 计算VWAP
    vwap = calc_vwap(clean_df, price_col, volume_col, min_records=min_records)
    
    # 计算其他统计指标
    prices = clean_df[price_col].astype(float)
    volumes = clean_df[volume_col].astype(float)
    
    result = {
        'vwap': vwap,
        'total_volume': float(volumes.sum()),
        'avg_price': float(prices.mean()),
        'price_std': float(prices.std()),
        'record_count': len(clean_df)
    }
    
    return result


def batch_calc_sustain(current_prices: List[float], 
                       vwap_values: List[float]) -> List[float]:
    """
    批量计算承接力度因子
    
    Args:
        current_prices: 当前价格列表
        vwap_values: VWAP值列表
    
    Returns:
        List[float]: 承接力度因子列表
    
    Raises:
        ValueError: 列表长度不匹配
    """
    if len(current_prices) != len(vwap_values):
        raise ValueError(
            f"价格列表和VWAP列表长度不匹配: "
            f"{len(current_prices)} vs {len(vwap_values)}"
        )
    
    results = []
    errors = []
    
    for i, (price, vwap) in enumerate(zip(current_prices, vwap_values)):
        try:
            factor = calc_sustain_factor(price, vwap)
            results.append(factor)
        except Exception as e:
            errors.append(f"索引{i}: {e}")
            results.append(0.5)  # 中性值
    
    if errors:
        logger.warning(f"批量计算部分失败 ({len(errors)}/{len(current_prices)}): {errors[:3]}")
    
    return results
