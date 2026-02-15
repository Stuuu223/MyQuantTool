#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股权数据访问器 - 提供流通市值查询接口

核心功能：
- 从 data/equity_info_tushare.json 查询流通市值
- 支持按交易日期查询历史数据
- 温和降级：数据缺失时返回 None，允许上层做温和惩罚处理

Author: iFlow CLI
Version: V1.1
"""

import json
import logging
from pathlib import Path
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

EQUITY_INFO_PATH = Path(__file__).resolve().parents[1] / "data" / "equity_info" / "equity_info_tushare.json"


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
        dict: 股权信息数据，结构: {code: {date: {...}}}

    Raises:
        FileNotFoundError: 如果数据文件不存在
    """
    if not EQUITY_INFO_PATH.exists():
        logger.error(f"[CRITICAL] equity_info 文件不存在: {EQUITY_INFO_PATH}")
        raise FileNotFoundError(f"equity_info_tushare.json 不存在: {EQUITY_INFO_PATH}")

    with EQUITY_INFO_PATH.open("r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 新数据结构: {latest_update, history_days, data_structure, trade_date_count, stock_count, data: {code: {date: {...}}}}
    data_structure = raw_data.get("data_structure", "")

    if "{code: {date: {...}}}" in data_structure:
        # 新结构：{code: {date: {...}}}
        logger.info("✅ 使用新数据结构: {code: {date: {...}}}")
        return raw_data
    else:
        # 旧结构：{data: {date: {code: {...}}}}
        logger.warning("⚠️  检测到旧数据结构，建议运行 rebuild_equity_database.py 重建")
        # 兼容旧结构
        return raw_data


def get_circ_mv(ts_code: str, trade_date: str) -> Optional[float]:
    """
    查询指定股票在指定日期的流通市值（单位：元）

    Args:
        ts_code: 股票代码，如 "603607.SH"
        trade_date: 交易日期，格式 YYYYMMDD

    Returns:
        Optional[float]: 流通市值（元），如果数据缺失则返回 None

    Raises:
        ValueError: 如果 trade_date 格式非法
    """
    # 第1关：校验 trade_date 格式
    _validate_trade_date(trade_date)

    # 第2关：加载数据
    equity_data = _load_equity_info()

    # 检测数据结构
    data_structure = equity_data.get("data_structure", "")
    is_new_structure = "{code: {date: {...}}}" in data_structure

    # 第3关：查询数据（根据结构不同，访问路径不同）
    stock_data = None

    if is_new_structure:
        # 新结构：data[code][date]
        stock_by_date = equity_data.get("data", {}).get(ts_code, {})
        stock_data = stock_by_date.get(trade_date)

        if stock_data is None:
            logger.debug(f"circ_mv 数据缺失: ts_code={ts_code} @ {trade_date} (新结构)")

    else:
        # 🔥 修复：支持多种旧结构
        # 旧结构1：data[date][code]
        data_by_date = equity_data.get("data", {})
        if data_by_date and trade_date in data_by_date:
            stock_data = data_by_date[trade_date].get(ts_code)

        # 旧结构2：直接 code 键（equity_info_mvp.json 格式）
        if stock_data is None and ts_code in equity_data:
            stock_data = equity_data[ts_code]

        if stock_data is None:
            logger.debug(f"circ_mv 数据缺失: ts_code={ts_code} @ {trade_date} (旧结构)")

    if stock_data is None:
        return None

    # 第4关：提取并校验 circ_mv
    # 🔥 修复：支持多种字段名映射（float_mv, circ_mv, circulating_market_cap, float_market_cap）
    circ_mv = (stock_data.get("circ_mv") or
               stock_data.get("float_mv") or
               stock_data.get("circulating_market_cap") or
               stock_data.get("float_market_cap") or 0)

    if not isinstance(circ_mv, (int, float)) or circ_mv <= 0:
        logger.debug(f"circ_mv 数据缺失或非法值: ts_code={ts_code} @ {trade_date}, circ_mv={circ_mv}")
        return None

    return float(circ_mv)