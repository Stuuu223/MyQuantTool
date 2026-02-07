#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据质量硬校验模块
遵循"宁可炸也不静默"原则
"""
import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DataQualityError(Exception):
    """数据质量不合格异常"""
    pass


def validate_kline(
    df: Optional[pd.DataFrame],
    code: str,
    period: str,
    min_length: Optional[int] = None
) -> pd.DataFrame:
    """
    K线数据质量硬校验
    
    Args:
        df: K线数据
        code: 股票代码
        period: 周期
        min_length: 最小数据长度（None表示不检查）
    
    Returns:
        校验通过的数据
        
    Raises:
        DataQualityError: 数据质量不合格
    """
    # 1. 空值检查
    if df is None:
        raise DataQualityError(f"K线数据为None: {code} {period}")
    
    if df.empty:
        raise DataQualityError(f"K线数据为空: {code} {period}")
    
    # 2. 字段完整性检查
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise DataQualityError(
            f"K线缺少字段: {code} {period}, 缺失={missing}, "
            f"现有={list(df.columns)}"
        )
    
    # 3. 数据合法性检查
    # 价格必须 > 0
    for price_col in ['open', 'high', 'low', 'close']:
        if (df[price_col] <= 0).any():
            invalid_count = (df[price_col] <= 0).sum()
            raise DataQualityError(
                f"K线存在非法价格: {code} {period}, "
                f"字段={price_col}, 非法数量={invalid_count}"
            )
    
    # 成交量必须 >= 0（可以为0，停牌日）
    if (df['volume'] < 0).any():
        invalid_count = (df['volume'] < 0).sum()
        raise DataQualityError(
            f"K线存在负成交量: {code} {period}, 非法数量={invalid_count}"
        )
    
    # 4. 长度检查（可选）
    if min_length is not None:
        actual_length = len(df)
        # 允许 20% 的容差（考虑停牌、节假日）
        tolerance = min_length * 0.2
        if actual_length < min_length - tolerance:
            raise DataQualityError(
                f"K线数据不完整: {code} {period}, "
                f"预期≥{min_length}, 实际={actual_length}"
            )
    
    logger.debug(f"✅ K线质量校验通过: {code} {period}, 长度={len(df)}")
    return df


def validate_tick(
    df: Optional[pd.DataFrame],
    code: str,
    trade_date: str
) -> pd.DataFrame:
    """
    分时数据质量硬校验
    
    Args:
        df: 分时数据
        code: 股票代码
        trade_date: 交易日期（格式：YYYYMMDD）
    
    Returns:
        校验通过的数据
        
    Raises:
        DataQualityError: 数据质量不合格
    """
    # 1. 空值检查
    if df is None:
        raise DataQualityError(f"分时数据为None: {code} {trade_date}")
    
    if df.empty:
        raise DataQualityError(f"分时数据为空: {code} {trade_date}")
    
    # 2. 字段完整性检查
    required_cols = ['time', 'price', 'volume']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise DataQualityError(
            f"分时缺少字段: {code} {trade_date}, 缺失={missing}"
        )
    
    # 3. 数据合法性检查
    if (df['price'] <= 0).any():
        raise DataQualityError(f"分时存在非法价格: {code} {trade_date}")
    
    if (df['volume'] < 0).any():
        raise DataQualityError(f"分时存在负成交量: {code} {trade_date}")
    
    # 4. 长度检查
    # 交易时间 240 分钟，允许部分缺失
    min_expected = 200
    if len(df) < min_expected:
        raise DataQualityError(
            f"分时数据不完整: {code} {trade_date}, "
            f"预期≥{min_expected}, 实际={len(df)}"
        )
    
    logger.debug(f"✅ 分时质量校验通过: {code} {trade_date}, 长度={len(df)}")
    return df