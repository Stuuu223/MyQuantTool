"""
CTO终极防爆日历引擎 - 物理降级版

【CTO铁令】：绝不允许调用xtdata.get_trading_dates！
原因：该API会触发C++层BSON崩溃！
方案：使用Python datetime进行物理推算，绝对不依赖QMT日历缓存！

Author: CTO
Date: 2026-03-01
Version: 3.0.0 - 物理降级防爆版
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)


def is_trading_day(date_str: str) -> bool:
    """
    粗略判断是否是交易日
    
    【CTO防爆】：只排除周末，不考虑节假日以防C++崩溃
    周末不交易是铁律，节假日影响不大（多查几天数据而已）
    """
    try:
        dt = datetime.strptime(date_str, '%Y%m%d')
        # weekday: 0=周一, ..., 5=周六, 6=周日
        if dt.weekday() >= 5:
            return False
        return True
    except Exception:
        return False


def get_latest_completed_trading_day() -> str:
    """
    获取最近一个已收盘的交易日
    
    【CTO防爆】：纯Python推算，不调用QMT API
    """
    now = datetime.now()
    
    # 如果今天是工作日且过了15:00，就是今天
    if now.weekday() < 5 and now.hour >= 15:
        return now.strftime('%Y%m%d')
    
    # 否则往前推，直到找到一个工作日
    curr = now - timedelta(days=1)
    while curr.weekday() >= 5:
        curr -= timedelta(days=1)
    return curr.strftime('%Y%m%d')


def get_nth_previous_trading_day(date_str: str, n: int) -> str:
    """
    往前推n个交易日
    
    【CTO物理推演】：
    1个交易日约等于1.4个自然日（考虑周末）
    我们直接放大系数推算，确保一定能包含到n个交易日
    
    Args:
        date_str: 基准日期 (YYYYMMDD)
        n: 倒推的交易日数量
        
    Returns:
        目标日期 (YYYYMMDD)
    """
    try:
        dt = datetime.strptime(date_str, '%Y%m%d')
        # 直接暴力往前推自然日：n天交易日，至少需要n*1.5天自然日
        # 我们给双倍保险，确保数据充足
        days_to_sub = int(n * 2)
        target_dt = dt - timedelta(days=days_to_sub)
        return target_dt.strftime('%Y%m%d')
    except Exception as e:
        logger.error(f"日期推算失败: {e}")
        # 如果报错，给出极其保守的兜底：直接推45天
        dt = datetime.strptime(date_str, '%Y%m%d')
        return (dt - timedelta(days=45)).strftime('%Y%m%d')


def get_trading_day_range(end_date_str: str, n_days: int) -> tuple:
    """
    获取以end_date_str为结束日期的N个交易日范围
    
    Returns: (start_date_str, end_date_str)
    """
    start_date = get_nth_previous_trading_day(end_date_str, n_days)
    return (start_date, end_date_str)


def get_real_trading_dates() -> List[str]:
    """
    【已废弃】获取真实交易日历列表
    
    【CTO铁令】：此方法不再调用QMT API，返回空列表防止崩溃
    所有日期计算改用get_nth_previous_trading_day
    """
    logger.warning("[CTO防爆] get_real_trading_dates已废弃，返回空列表")
    return []


def get_next_trading_day(date_str: str) -> Optional[str]:
    """
    获取指定日期的下一个交易日
    
    【CTO防爆】：纯Python推算
    """
    try:
        dt = datetime.strptime(date_str, '%Y%m%d')
        curr = dt + timedelta(days=1)
        # 跳过周末
        while curr.weekday() >= 5:
            curr += timedelta(days=1)
        return curr.strftime('%Y%m%d')
    except Exception:
        return None