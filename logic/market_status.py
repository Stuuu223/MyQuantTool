"""
市场状态判断模块

提供标准化的市场状态判断逻辑，包括：
1. 交易时间判断（支持时区）
2. 涨停/跌停状态判断（支持ST股）
3. 盘口状态判断
4. 市场状态机
5. 竞价真空期处理

Author: iFlow CLI
Version: V9.7
"""

import pytz
from datetime import datetime, time
from typing import Optional, Tuple, Dict, Any
from enum import Enum


class MarketStatus(Enum):
    """市场状态枚举"""
    NORMAL = "normal"  # 正常交易
    LIMIT_UP = "limit_up"  # 涨停
    LIMIT_DOWN = "limit_down"  # 跌停
    DATA_ABNORMAL = "data_abnormal"  # 数据异常
    SUSPENDED = "suspended"  # 停牌
    CLOSED = "closed"  # 已收盘
    OFF_HOURS = "off_hours"  # 非交易时间
    PRE_OPEN = "pre_open"  # 🆕 V9.7: 等待开盘（竞价结束）
    NOON_BREAK = "noon_break"  # 🆕 V9.10: 午间休盘（11:30-13:00）


class MarketStatusChecker:
    """
    市场状态检查器

    提供标准化的市场状态判断逻辑，支持：
    - 时区感知的交易时间判断
    - 涨停/跌停状态识别
    - 数据异常检测
    """

    # A 股交易时间配置
    MORNING_START = time(9, 15)  # 早盘开始
    MORNING_END = time(11, 30)   # 早盘结束
    AFTERNOON_START = time(13, 0)  # 午盘开始
    AFTERNOON_END = time(15, 0)   # 午盘结束
    
    # 🆕 V9.7: 竞价真空期配置
    AUCTION_GAP_START = time(9, 25, 1)  # 竞价结束（09:25:01）
    AUCTION_GAP_END = time(9, 29, 59)   # 等待开盘（09:29:59）

    # 涨跌停阈值
    MAIN_BOARD_LIMIT_UP = 9.5     # 主板涨停阈值
    MAIN_BOARD_LIMIT_DOWN = -9.5  # 主板跌停阈值
    GEM_STAR_LIMIT_UP = 19.5      # 创业板/科创板涨停阈值
    GEM_STAR_LIMIT_DOWN = -19.5   # 创业板/科创板跌停阈值
    # 🆕 V9.7: ST股涨跌停阈值
    ST_LIMIT_UP = 4.9            # ST股涨停阈值（5%）
    ST_LIMIT_DOWN = -4.9         # ST股跌停阈值（5%）

    def __init__(self, timezone: str = 'Asia/Shanghai'):
        """
        初始化市场状态检查器

        Args:
            timezone: 时区，默认为上海时区
        """
        self.timezone = pytz.timezone(timezone)
        self._cached_time: Optional[time] = None
        self._cached_is_trading: Optional[bool] = None

    def get_current_time(self) -> time:
        """
        获取当前时间（考虑时区）

        Returns:
            当前时间
        """
        now = datetime.now(self.timezone)
        return now.time()

    def is_weekday(self) -> bool:
        """
        判断当前是否为工作日

        Returns:
            True 表示是工作日
        """
        now = datetime.now(self.timezone)
        return now.weekday() < 5

    def is_trading_time(self, force_refresh: bool = False) -> bool:
        """
        判断当前是否在交易时间内

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            True 表示在交易时间内
        """
        # 使用缓存优化性能
        if not force_refresh and self._cached_is_trading is not None:
            return self._cached_is_trading

        current_time = self.get_current_time()
        is_weekday = self.is_weekday()

        is_trading = is_weekday and (
            (self.MORNING_START <= current_time <= self.MORNING_END) or
            (self.AFTERNOON_START <= current_time <= self.AFTERNOON_END)
        )

        # 更新缓存
        self._cached_time = current_time
        self._cached_is_trading = is_trading

        return is_trading

    def is_call_auction_gap(self, current_time: Optional[time] = None) -> bool:
        """
        🆕 V9.7: 判断是否处于 09:25 - 09:30 的竞价真空期
        
        在这个时段，集合竞价已经结束，但连续竞价尚未开始。
        交易所可能不更新盘口数据，或者更新频率极低。
        
        Args:
            current_time: 当前时间（如果不提供，则自动获取）
        
        Returns:
            True 表示处于竞价真空期
        """
        if current_time is None:
            current_time = self.get_current_time()
        
        return self.AUCTION_GAP_START <= current_time <= self.AUCTION_GAP_END

    def is_noon_break(self, current_time: Optional[time] = None) -> bool:
        """
        🆕 V9.10: 判断是否处于午间休盘期（11:30 - 13:00）
        
        在这个时段，早盘交易已经结束，但午盘交易尚未开始。
        数据是静态的，但交易并未结束。
        
        Args:
            current_time: 当前时间（如果不提供，则自动获取）
        
        Returns:
            True 表示处于午间休盘期
        """
        if current_time is None:
            current_time = self.get_current_time()
        
        return self.MORNING_END < current_time < self.AFTERNOON_START

    def get_limit_threshold(self, symbol: str, name: str = "") -> Tuple[float, float]:
        """
        🆕 V9.7: 根据股票名称和代码，动态决定涨跌停阈值
        
        规则：
        1. ST股（含*ST、ST、退）：5% 涨跌停
        2. 创业板(30)、科创板(68)：20% 涨跌停
        3. 北交所(8/4)：30% 涨跌停
        4. 普通主板：10% 涨跌停
        
        Args:
            symbol: 股票代码
            name: 股票名称
        
        Returns:
            (涨停阈值, 跌停阈值)
        """
        # 1. 优先判断 ST 股
        if "ST" in name or "退" in name:
            return self.ST_LIMIT_UP, self.ST_LIMIT_DOWN
        
        # 2. 判断 创业板(30) / 科创板(68) / 北交所(8/4)
        if symbol.startswith(("30", "68")):
            return self.GEM_STAR_LIMIT_UP, self.GEM_STAR_LIMIT_DOWN
        elif symbol.startswith(("8", "4")):
            # 北交所：30% 涨跌停
            return 29.5, -29.5
        
        # 3. 普通主板
        return self.MAIN_BOARD_LIMIT_UP, self.MAIN_BOARD_LIMIT_DOWN

    def is_limit_up(self, change_pct: float, symbol: str = "", name: str = "") -> bool:
        """
        判断是否涨停

        Args:
            change_pct: 涨跌幅（百分比）
            symbol: 股票代码（用于判断是主板还是创业板/科创板）
            name: 股票名称（🆕 V9.7: 用于判断ST股）

        Returns:
            True 表示涨停
        """
        # 🆕 V9.7: 使用动态阈值
        limit_up_threshold, _ = self.get_limit_threshold(symbol, name)
        return change_pct >= limit_up_threshold

    def is_limit_down(self, change_pct: float, symbol: str = "", name: str = "") -> bool:
        """
        判断是否跌停

        Args:
            change_pct: 涨跌幅（百分比）
            symbol: 股票代码（用于判断是主板还是创业板/科创板）
            name: 股票名称（🆕 V9.7: 用于判断ST股）

        Returns:
            True 表示跌停
        """
        # 🆕 V9.7: 使用动态阈值
        _, limit_down_threshold = self.get_limit_threshold(symbol, name)
        return change_pct <= limit_down_threshold

    def check_market_status(
        self,
        bid1_volume: int,
        ask1_volume: int,
        change_pct: float,
        symbol: str = "",
        name: str = "",
        bid1_price: float = 0,
        ask1_price: float = 0
    ) -> Dict[str, Any]:
        """
        检查市场状态，返回状态描述和详细信息

        Args:
            bid1_volume: 买一量（手）
            ask1_volume: 卖一量（手）
            change_pct: 涨跌幅（百分比）
            symbol: 股票代码
            name: 股票名称（🆕 V9.7: 用于判断ST股）
            bid1_price: 买一价
            ask1_price: 卖一价

        Returns:
            dict: 包含状态码、状态描述、详细信息
        """
        # 🆕 V9.7: 判断是否处于竞价真空期
        if self.is_call_auction_gap():
            return {
                'status': MarketStatus.PRE_OPEN,
                'message': "🕒 等待开盘 (竞价结束)",
                'is_trading': False,
                'is_limit_up': False,
                'is_limit_down': False
            }

        # 🆕 V9.10: 判断是否处于午间休盘期
        if self.is_noon_break():
            return {
                'status': MarketStatus.NOON_BREAK,
                'message': "☕️ 午间休盘 (数据截止至 11:30)",
                'is_trading': False,  # 虽然不交易，但不是收盘
                'is_limit_up': False,  # 休盘时不判断涨跌停动态
                'is_limit_down': False
            }

        # 判断涨停/跌停
        is_limit_up = self.is_limit_up(change_pct, symbol, name)
        is_limit_down = self.is_limit_down(change_pct, symbol, name)

        # 如果在交易时间内（强制刷新缓存，确保实时性）
        if self.is_trading_time(force_refresh=True):
            # 涨停时，卖一量为0是正常现象
            if is_limit_up:
                return {
                    'status': MarketStatus.LIMIT_UP,
                    'message': None,  # 不显示警告
                    'is_trading': True,
                    'is_limit_up': True,
                    'is_limit_down': False
                }

            # 跌停时，买一量为0是正常现象
            if is_limit_down:
                return {
                    'status': MarketStatus.LIMIT_DOWN,
                    'message': None,  # 不显示警告
                    'is_trading': True,
                    'is_limit_up': False,
                    'is_limit_down': True
                }

            # 买一和卖一都为0，需要进一步判断
            if bid1_volume == 0 and ask1_volume == 0:
                # 如果买一价和卖一价也为0，说明数据异常或停牌
                if bid1_price == 0 and ask1_price == 0:
                    return {
                        'status': MarketStatus.DATA_ABNORMAL,
                        'message': "⚠️ 数据异常/停牌",
                        'is_trading': False,
                        'is_limit_up': False,
                        'is_limit_down': False
                    }
                # 如果有买一价和卖一价，说明交易正常，只是盘口量暂时为0（可能是快速拉升或数据源延迟）
                else:
                    return {
                        'status': MarketStatus.NORMAL,
                        'message': None,
                        'is_trading': True,
                        'is_limit_up': False,
                        'is_limit_down': False
                    }

            # 正常交易状态
            return {
                'status': MarketStatus.NORMAL,
                'message': None,
                'is_trading': True,
                'is_limit_up': False,
                'is_limit_down': False
            }

        # 非交易时间
        else:
            # 买一和卖一都为0，说明已收盘
            if bid1_volume == 0 and ask1_volume == 0:
                return {
                    'status': MarketStatus.CLOSED,
                    'message': "⚠️ 已收盘，盘口数据已清空",
                    'is_trading': False,
                    'is_limit_up': False,
                    'is_limit_down': False
                }

            # 非交易时间但仍有数据，可能是缓存数据
            return {
                'status': MarketStatus.OFF_HOURS,
                'message': "⚠️ 非交易时间，数据仅供参考",
                'is_trading': False,
                'is_limit_up': False,
                'is_limit_down': False
            }

    def get_limit_price(
        self,
        prev_close: float,
        symbol: str,
        is_limit_up: bool = True
    ) -> float:
        """
        计算涨停价或跌停价

        Args:
            prev_close: 昨收价
            symbol: 股票代码
            is_limit_up: True 计算涨停价，False 计算跌停价

        Returns:
            涨停价或跌停价
        """
        if symbol.startswith('30') or symbol.startswith('68'):
            # 创业板/科创板：20%
            limit_pct = 0.20
        else:
            # 主板：10%
            limit_pct = 0.10

        if is_limit_up:
            return round(prev_close * (1 + limit_pct), 2)
        else:
            return round(prev_close * (1 - limit_pct), 2)

    def batch_check_market_status(
        self,
        stocks: list
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量检查市场状态（性能优化版）

        Args:
            stocks: 股票列表，每个股票包含 bid1_volume, ask1_volume, change_pct, symbol, name 等字段

        Returns:
            dict: 股票代码到状态信息的映射
        """
        # 在循环外部只调用一次 is_trading_time()，提升性能
        current_is_trading = self.is_trading_time()
        # 🆕 V9.7: 判断是否处于竞价真空期
        is_auction_gap = self.is_call_auction_gap()

        results = {}

        for stock in stocks:
            symbol = stock.get('代码', stock.get('symbol', ''))
            name = stock.get('名称', stock.get('name', ''))
            bid1_volume = stock.get('买一量', stock.get('bid1_volume', 0))
            ask1_volume = stock.get('卖一量', stock.get('ask1_volume', 0))
            change_pct = stock.get('涨跌幅', stock.get('change_pct', 0))
            bid1_price = stock.get('买一价', stock.get('bid1_price', 0))
            ask1_price = stock.get('卖一价', stock.get('ask1_price', 0))

            # 🆕 V9.7: 竞价真空期处理
            if is_auction_gap:
                results[symbol] = {
                    'status': MarketStatus.PRE_OPEN,
                    'message': "🕒 等待开盘 (竞价结束)",
                    'is_trading': False,
                    'is_limit_up': False,
                    'is_limit_down': False
                }
                continue

            # 使用缓存的交易时间状态
            if current_is_trading:
                # 交易时间内的判断逻辑
                is_limit_up = self.is_limit_up(change_pct, symbol, name)
                is_limit_down = self.is_limit_down(change_pct, symbol, name)

                if is_limit_up:
                    results[symbol] = {
                        'status': MarketStatus.LIMIT_UP,
                        'message': None,
                        'is_trading': True,
                        'is_limit_up': True,
                        'is_limit_down': False
                    }
                elif is_limit_down:
                    results[symbol] = {
                        'status': MarketStatus.LIMIT_DOWN,
                        'message': None,
                        'is_trading': True,
                        'is_limit_up': False,
                        'is_limit_down': True
                    }
                elif bid1_volume == 0 and ask1_volume == 0:
                    results[symbol] = {
                        'status': MarketStatus.DATA_ABNORMAL,
                        'message': "⚠️ 数据异常/停牌",
                        'is_trading': False,
                        'is_limit_up': False,
                        'is_limit_down': False
                    }
                else:
                    results[symbol] = {
                        'status': MarketStatus.NORMAL,
                        'message': None,
                        'is_trading': True,
                        'is_limit_up': False,
                        'is_limit_down': False
                    }
            else:
                # 非交易时间的判断逻辑
                if bid1_volume == 0 and ask1_volume == 0:
                    results[symbol] = {
                        'status': MarketStatus.CLOSED,
                        'message': "⚠️ 已收盘，盘口数据已清空",
                        'is_trading': False,
                        'is_limit_up': False,
                        'is_limit_down': False
                    }
                else:
                    results[symbol] = {
                        'status': MarketStatus.OFF_HOURS,
                        'message': "⚠️ 非交易时间，数据仅供参考",
                        'is_trading': False,
                        'is_limit_up': False,
                        'is_limit_down': False
                    }

        return results


# 全局单例
_checker_instance = None


def get_market_status_checker() -> MarketStatusChecker:
    """
    获取市场状态检查器单例

    Returns:
        MarketStatusChecker 实例
    """
    global _checker_instance
    if _checker_instance is None:
        _checker_instance = MarketStatusChecker()
    return _checker_instance


# 便捷函数（向后兼容）
def is_trading_time() -> bool:
    """判断当前是否在交易时间内"""
    return get_market_status_checker().is_trading_time()


def check_market_status(
    bid1_volume: int,
    ask1_volume: int,
    change_pct: float,
    symbol: str = "",
    name: str = "",
    bid1_price: float = 0,
    ask1_price: float = 0
) -> Dict[str, Any]:
    """检查市场状态（🆕 V9.7: 支持ST股识别）"""
    return get_market_status_checker().check_market_status(
        bid1_volume, ask1_volume, change_pct, symbol, name, bid1_price, ask1_price
    )