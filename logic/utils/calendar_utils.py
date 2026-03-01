"""
QMT原生交易日历工具
解决跨日Bug：使用xtdata.get_trading_dates('SH')获取真实交易日历
禁止在量化系统中使用datetime.timedelta推算交易日！

【CTO防爆修正】：xtdata.get_trading_dates可能触发BSON崩溃
添加熔断机制，降级到自然日推算
"""
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional

# 【CTO防爆】：全局缓存交易日历，避免重复调用xtdata
_TRADING_DATES_CACHE = None
_TRADING_DATES_AVAILABLE = None

try:
    from xtquant import xtdata
except ImportError:
    xtdata = None
    logging.warning("[Calendar] xtquant未导入，可能在非QMT环境")

logger = logging.getLogger(__name__)


def _safe_get_trading_dates() -> List[str]:
    """
    【CTO防爆】安全获取交易日历，带熔断机制
    """
    global _TRADING_DATES_CACHE, _TRADING_DATES_AVAILABLE
    
    # 如果已经确定不可用，直接返回空
    if _TRADING_DATES_AVAILABLE == False:
        return []
    
    # 如果有缓存，直接返回
    if _TRADING_DATES_CACHE is not None:
        return _TRADING_DATES_CACHE
    
    if xtdata is None:
        _TRADING_DATES_AVAILABLE = False
        return []
    
    try:
        # 【CTO防爆】：尝试获取交易日历
        dates = xtdata.get_trading_dates('SH')
        if not dates:
            logger.warning("[日历工具] 未能获取到原生日历，QMT可能未就绪")
            _TRADING_DATES_AVAILABLE = False
            return []
        
        # 统一转换为YYYYMMDD字符串格式
        formatted_dates = []
        for d in dates:
            if isinstance(d, (int, float)):
                # 毫秒时间戳转日期字符串
                formatted_dates.append(time.strftime('%Y%m%d', time.localtime(d / 1000)))
            elif isinstance(d, str):
                # 已经是字符串，标准化格式
                formatted_dates.append(d.replace('-', ''))
        
        # 去重并排序
        result = sorted(list(set(formatted_dates)))
        logger.info(f"[日历工具] 成功获取 {len(result)} 个交易日")
        _TRADING_DATES_CACHE = result
        _TRADING_DATES_AVAILABLE = True
        return result
        
    except Exception as e:
        logger.warning(f"[日历工具] 获取交易日历失败(CTO熔断): {e}")
        _TRADING_DATES_AVAILABLE = False
        return []


def get_real_trading_dates() -> List[str]:
    """
    获取A股上交所(SH)的真实交易日历列表
    返回: YYYYMMDD格式字符串列表，按时间排序
    """
    return _safe_get_trading_dates()


def get_latest_completed_trading_day() -> str:
    """
    【核心方法】获取最近一个已收盘的交易日
    
    逻辑:
    - 获取当前时间
    - 如果今天是交易日且时间>=15:00 → 返回今天
    - 如果今天是交易日但时间<15:00 → 返回上一个交易日
    - 如果今天是非交易日(周末/节假日) → 返回最近的一个交易日
    
    用途: 解决周六凌晨、周日凌晨、节假日前后运行时的日期定位问题
    """
    now = datetime.now()
    today_str = now.strftime('%Y%m%d')
    
    trading_dates = get_real_trading_dates()
    if not trading_dates:
        logger.warning(f"[日历工具] 日历获取失败，回退到自然日: {today_str}")
        return today_str
    
    # 找出所有小于等于今天的交易日
    past_dates = [d for d in trading_dates if d <= today_str]
    
    if not past_dates:
        logger.warning(f"[日历工具] 今天{today_str}之前无交易日记录，回退到今天")
        return today_str
    
    latest_day = past_dates[-1]
    
    if latest_day == today_str:
        # 今天是交易日，检查是否已收盘(15:00)
        if now.hour < 15:
            # 尚未收盘，复盘数据还没产生，取上一个交易日
            if len(past_dates) > 1:
                prev_day = past_dates[-2]
                logger.info(f"[日历工具] 今天{today_str}交易尚未收盘(当前{now.hour}:00)，复盘日期定为: {prev_day}")
                return prev_day
            else:
                logger.warning(f"[日历工具] 今天{today_str}是第一个交易日，无前一交易日")
                return today_str
        else:
            # 已收盘，可以使用今天的数据
            logger.info(f"[日历工具] 今天{today_str}已收盘，复盘日期: {today_str}")
            return today_str
    else:
        # 今天是非交易日(周末/节假日)，直接返回最近交易日
        logger.info(f"[日历工具] 今天{today_str}非交易日，最近交易日: {latest_day}")
        return latest_day


def get_nth_previous_trading_day(base_date_str: str, n: int) -> str:
    """
    从指定日期倒推N个交易日
    
    参数:
    - base_date_str: 基准日期 (YYYYMMDD)
    - n: 倒推的交易日数量
    
    返回: 目标日期 (YYYYMMDD)
    
    用途: ATR计算需要20个交易日数据，不能使用timedelta(days=20)
    """
    trading_dates = get_real_trading_dates()
    if not trading_dates:
        logger.warning(f"[日历工具] 日历获取失败，使用自然日倒推: {base_date_str}")
        base_dt = datetime.strptime(base_date_str, '%Y%m%d')
        target_dt = base_dt - timedelta(days=n)
        return target_dt.strftime('%Y%m%d')
    
    # 找出所有小于等于基准日期的交易日
    past_dates = [d for d in trading_dates if d <= base_date_str]
    
    if len(past_dates) <= n:
        # 数据不足，返回最早的交易日
        earliest = past_dates[0] if past_dates else base_date_str
        logger.warning(f"[日历工具] 历史数据不足{n}个交易日，回退到最早可用: {earliest}")
        return earliest
    
    target_date = past_dates[-(n + 1)]
    logger.debug(f"[日历工具] 从{base_date_str}倒推{n}个交易日: {target_date}")
    return target_date


def get_trading_day_range(end_date_str: str, n_days: int) -> tuple:
    """
    获取以end_date_str为结束日期的N个交易日范围
    
    返回: (start_date_str, end_date_str)
    """
    start_date = get_nth_previous_trading_day(end_date_str, n_days)
    return (start_date, end_date_str)


# 快捷函数：判断是否为交易日
def is_trading_day(date_str: str) -> bool:
    """判断指定日期是否为交易日"""
    trading_dates = get_real_trading_dates()
    return date_str in trading_dates


# 快捷函数：获取下一个交易日
def get_next_trading_day(date_str: str) -> Optional[str]:
    """获取指定日期的下一个交易日"""
    trading_dates = get_real_trading_dates()
    if not trading_dates:
        return None
    
    future_dates = [d for d in trading_dates if d > date_str]
    return future_dates[0] if future_dates else None
