#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股权数据访问器 - 提供流通市值查询接口

核心功能：
- 从 data/equity_info_tushare.json 查询流通市值
- 支持按交易日期查询历史数据
- 硬校验：数据缺失时直接抛异常，不允许静默降级

Author: iFlow CLI
Version: V1.0
"""

import json
import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

EQUITY_INFO_PATH = Path(__file__).resolve().parents[1] / "data" / "equity_info_tushare.json"


def _validate_trade_date(trade_date: str) -> None:
    """
    校验交易日期格式

    Args:
        trade_date: 交易日期，格式 YYYYMMDD

    Raises:
        ValueError: 如果 trade_date 格式非法
    """
    if not trade_date or len(trade_date) != 8 or not trade_date.isdigit():
        logger.error(f"[CRITICAL] trade_date 格式非法: {trade_date}")
        raise ValueError(f"trade_date 格式非法: {trade_date}")


@lru_cache(maxsize=1)
def _load_equity_info() -> dict:
    """
    加载股权信息数据（带缓存）

    Returns:
        dict: 股权信息数据

    Raises:
        FileNotFoundError: 如果数据文件不存在
    """
    if not EQUITY_INFO_PATH.exists():
        logger.error(f"[CRITICAL] equity_info 文件不存在: {EQUITY_INFO_PATH}")
        raise FileNotFoundError(f"equity_info_tushare.json 不存在: {EQUITY_INFO_PATH}")

    with EQUITY_INFO_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def get_circ_mv(ts_code: str, trade_date: str) -> float:
    """
    查询指定股票在指定日期的流通市值（单位：元）

    Args:
        ts_code: 股票代码，如 "603607.SH"
        trade_date: 交易日期，格式 YYYYMMDD

    Returns:
        float: 流通市值（元）

    Raises:
        ValueError: 如果 trade_date 格式非法、数据缺失或 circ_mv 非法
    """
    # 第1关：校验 trade_date 格式
    _validate_trade_date(trade_date)

    # 第2关：加载数据
    equity_data = _load_equity_info()
    data_by_date = equity_data.get("data", {})

    # 第3关：查询日期
    daily_data = data_by_date.get(trade_date)
    if daily_data is None:
        logger.error(f"[CRITICAL] circ_mv 数据缺失: trade_date={trade_date} 不在 equity_info 中")
        logger.error(f"  可能原因: 该日期数据未同步到 equity_info_tushare.json")
        raise ValueError(f"circ_mv 数据缺失: trade_date={trade_date}")

    # 第4关：查询股票
    stock_data = daily_data.get(ts_code)
    if stock_data is None:
        logger.error(f"[CRITICAL] circ_mv 数据缺失: ts_code={ts_code} @ {trade_date} 不存在")
        logger.error(f"  可能原因: 新股、重组、更名、停牌等")
        raise ValueError(f"circ_mv 数据缺失: {ts_code} @ {trade_date}")

    # 第5关：提取并校验 float_mv
    circ_mv = float(stock_data.get("float_mv", 0))
    if circ_mv <= 0:
        logger.error(f"[CRITICAL] circ_mv 非法值: ts_code={ts_code} @ {trade_date}, float_mv={circ_mv}")
        raise ValueError(f"circ_mv 非法值: {ts_code} @ {trade_date}, float_mv={circ_mv}")

    return circ_mv