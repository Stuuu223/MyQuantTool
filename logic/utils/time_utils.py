# -*- coding: utf-8 -*-
"""
时间解析工具函数

【M1】safe_parse_entry_time - 全局唯一的 entry_time 解析入口
彻底终结 entry_time 格式反复出现的问题。

使用规范:
    所有需要解析 entry_time 的地方，必须调用此函数，
    禁止在业务代码里裸写 strptime。

Author: AI Project Director
Date: 2026-03-17
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def safe_parse_entry_time(
    entry_time: str | None,
    fallback_date: str,
    stock_code: str = '',
) -> datetime:
    """
    全局唯一的 entry_time 解析入口。
    
    支持格式（按优先级）:
        1. 'YYYY-MM-DD HH:MM:SS'  → 最标准，直接 strptime
        2. 'YYYYMMDDHHMMSS'       → 14位纯数字，取前8位作为日期
        3. 'YYYY-MM-DD'           → 只有日期，用 14:57:00 作为时间
        4. 'YYYYMMDD'             → 8位纯数字，用 14:57:00 作为时间
        5. 其他/None              → 使用 fallback_date + 14:57:00，打 ERROR 日志
    
    Args:
        entry_time: 原始 entry_time 字符串，可能为 None
        fallback_date: YYYYMMDD 格式的日期字符串，解析失败时使用
        stock_code: 股票代码，仅用于日志
    
    Returns:
        datetime 对象，永远不返回 None
    
    Raises:
        永远不抛出异常（内部全部 try-except）
    """
    DEFAULT_TIME = (14, 57, 0)  # 默认使用收盘时间
    
    def _make_datetime(date_str: str, hour: int, minute: int, second: int) -> datetime:
        """将 YYYYMMDD 格式转换为 datetime"""
        return datetime.strptime(date_str, '%Y%m%d').replace(
            hour=hour, minute=minute, second=second, microsecond=0
        )
    
    def _extract_date_from_str(s: str) -> str | None:
        """从字符串中提取 YYYYMMDD 格式的日期"""
        s = s.strip()
        
        # 尝试14位纯数字格式: YYYYMMDDHHMMSS
        if len(s) >= 14 and s[:14].isdigit():
            return s[:8]
        
        # 尝试标准日期格式: YYYY-MM-DD
        if len(s) >= 10 and s[4] == '-' and s[7] == '-':
            return s[:10].replace('-', '')
        
        # 尝试8位纯数字: YYYYMMDD
        if len(s) == 8 and s.isdigit():
            return s
        
        return None
    
    # ===== 主解析逻辑 =====
    
    # Case 1: entry_time 为空或 None
    if not entry_time:
        logger.error(
            f"[safe_parse] {stock_code} entry_time为空，"
            f"使用fallback_date={fallback_date}"
        )
        return _make_datetime(fallback_date, *DEFAULT_TIME)
    
    raw = str(entry_time).strip()
    
    # Case 2: 标准格式 'YYYY-MM-DD HH:MM:SS'
    if len(raw) == 19 and raw[4] == '-' and raw[10] == ' ':
        try:
            result = datetime.strptime(raw, '%Y-%m-%d %H:%M:%S')
            logger.debug(f"[safe_parse] {stock_code} 标准格式解析成功: {raw}")
            return result
        except ValueError:
            pass  # 继续尝试其他格式
    
    # Case 3: 14位纯数字格式 'YYYYMMDDHHMMSS'
    if len(raw) == 14 and raw.isdigit():
        date_part = raw[:8]
        # time_part = raw[8:14]  # 暂不解析时间部分，使用默认时间
        logger.debug(f"[safe_parse] {stock_code} 14位格式解析: {date_part}")
        return _make_datetime(date_part, *DEFAULT_TIME)
    
    # Case 4: 只有日期 'YYYY-MM-DD'
    if len(raw) == 10 and raw[4] == '-' and raw[7] == '-':
        date_part = raw.replace('-', '')
        logger.debug(f"[safe_parse] {stock_code} 日期格式解析: {date_part}")
        return _make_datetime(date_part, *DEFAULT_TIME)
    
    # Case 5: 8位纯数字 'YYYYMMDD'
    if len(raw) == 8 and raw.isdigit():
        logger.debug(f"[safe_parse] {stock_code} 8位格式解析: {raw}")
        return _make_datetime(raw, *DEFAULT_TIME)
    
    # Case 6: 尝试从混合格式中提取日期
    extracted = _extract_date_from_str(raw)
    if extracted:
        logger.warning(
            f"[safe_parse] {stock_code} 非标准格式'{raw}'，提取日期={extracted}"
        )
        return _make_datetime(extracted, *DEFAULT_TIME)
    
    # Case 7: 完全无法解析，使用 fallback
    logger.error(
        f"[safe_parse] {stock_code} 无法解析entry_time='{raw}'，"
        f"使用fallback_date={fallback_date}"
    )
    return _make_datetime(fallback_date, *DEFAULT_TIME)


def calculate_hold_minutes(entry_time: datetime, current_time: datetime) -> int:
    """
    计算持仓分钟数（安全版本）。
    
    Args:
        entry_time: 买入时间
        current_time: 当前时间
    
    Returns:
        持仓分钟数，最小返回0
    """
    if entry_time is None or current_time is None:
        return 0
    
    delta = (current_time - entry_time).total_seconds() / 60
    return max(0, int(delta))
