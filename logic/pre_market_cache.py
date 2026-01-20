# -*- coding: utf-8 -*-
"""
盘前预计算缓存模块

功能：
- 在盘前（9:25之前）预计算所有股票的MA4
- 存储到缓存中，盘中实时计算MA5时无需下载历史数据
- 避免盘中大量历史数据请求导致系统卡顿

公式：
- Realtime_MA5 = (Pre_Market_MA4 * 4 + Current_Price) / 5

Author: iFlow CLI
Version: V19.1
"""

from logic.logger import get_logger
import akshare as ak
import pandas as pd
from datetime import datetime, time as dt_time
from typing import Dict, Optional

logger = get_logger(__name__)


class PreMarketCache:
    """
    盘前预计算缓存管理器

    功能：
    - 预计算所有股票的MA4
    - 提供快速获取MA4的接口
    - 提供实时计算MA5的接口
    """

    def __init__(self):
        """初始化缓存管理器"""
        self.ma4_cache: Dict[str, float] = {}  # {stock_code: ma4_value}
        self.cache_time: Optional[datetime] = None
        self.cache_valid = False

    def is_cache_valid(self) -> bool:
        """
        检查缓存是否有效

        Returns:
            bool: 缓存是否有效
        """
        if not self.cache_valid or not self.cache_time:
            return False

        # 检查缓存是否过期（超过24小时）
        time_diff = (datetime.now() - self.cache_time).total_seconds()
        if time_diff > 86400:  # 24小时
            return False

        return True

    def precompute_ma4(self, stock_codes: list = None, max_stocks: int = 1000) -> int:
        """
        🚀 V19.1 新增：盘前预计算MA4

        Args:
            stock_codes: 股票代码列表（如果为None，则获取全市场股票）
            max_stocks: 最大处理股票数量（避免一次性处理过多）

        Returns:
            int: 成功计算的股票数量
        """
        if not stock_codes:
            # 获取全市场股票列表
            try:
                stock_list = ak.stock_info_a_code_name()
                stock_codes = stock_list['code'].tolist()
                logger.info(f"✅ 获取全市场股票列表: {len(stock_codes)} 只")
            except Exception as e:
                logger.error(f"❌ 获取股票列表失败: {e}")
                return 0

        # 限制处理数量
        stock_codes = stock_codes[:max_stocks]

        logger.info(f"🚀 [盘前预计算] 开始预计算 {len(stock_codes)} 只股票的MA4...")

        success_count = 0
        failure_count = 0

        for i, code in enumerate(stock_codes):
            try:
                # 获取个股历史行情（最近5天）
                hist = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")

                if len(hist) < 4:
                    # 历史数据不足，跳过
                    continue

                # 计算MA4（过去4天的收盘价）
                last_4_closes = hist['收盘'].iloc[-4:].astype(float).values
                ma4 = sum(last_4_closes) / 4

                # 存入缓存
                self.ma4_cache[code] = ma4
                success_count += 1

                # 每处理100只股票输出一次进度
                if (i + 1) % 100 == 0:
                    logger.info(f"📊 [盘前预计算] 进度: {i + 1}/{len(stock_codes)} ({(i + 1) / len(stock_codes) * 100:.1f}%)")

            except Exception as e:
                failure_count += 1
                # 只在DEBUG级别记录，避免刷屏
                logger.debug(f"预计算MA4失败 {code}: {e}")

        # 更新缓存时间
        self.cache_time = datetime.now()
        self.cache_valid = True

        logger.info(f"✅ [盘前预计算] 完成！成功: {success_count}, 失败: {failure_count}")

        return success_count

    def get_ma4(self, stock_code: str) -> Optional[float]:
        """
        获取股票的MA4

        Args:
            stock_code: 股票代码

        Returns:
            float: MA4值，如果不存在则返回None
        """
        clean_code = stock_code.split('.')[0]
        return self.ma4_cache.get(clean_code)

    def calculate_ma5_realtime(self, stock_code: str, current_price: float) -> Optional[float]:
        """
        实时计算MA5（使用预计算的MA4）

        公式：Realtime_MA5 = (Pre_Market_MA4 * 4 + Current_Price) / 5

        Args:
            stock_code: 股票代码
            current_price: 当前价格

        Returns:
            float: MA5值，如果MA4不存在则返回None
        """
        ma4 = self.get_ma4(stock_code)

        if ma4 is None:
            return None

        # 实时计算MA5
        ma5 = (ma4 * 4 + current_price) / 5
        return ma5

    def calculate_bias_realtime(self, stock_code: str, current_price: float) -> Optional[float]:
        """
        实时计算乖离率（使用预计算的MA4）

        公式：Bias = (Current_Price - MA5) / MA5 * 100

        Args:
            stock_code: 股票代码
            current_price: 当前价格

        Returns:
            float: 乖离率(%)，如果MA4不存在则返回None
        """
        ma5 = self.calculate_ma5_realtime(stock_code, current_price)

        if ma5 is None:
            return None

        # 计算乖离率
        bias = (current_price - ma5) / ma5 * 100
        return round(bias, 2)

    def clear_cache(self):
        """清空缓存"""
        self.ma4_cache.clear()
        self.cache_time = None
        self.cache_valid = False
        logger.info("🗑️ [盘前预计算] 缓存已清空")

    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息

        Returns:
            dict: 缓存统计信息
        """
        return {
            'total_stocks': len(self.ma4_cache),
            'cache_time': self.cache_time.strftime('%Y-%m-%d %H:%M:%S') if self.cache_time else None,
            'cache_valid': self.cache_valid,
            'is_expired': not self.is_cache_valid()
        }


# 全局单例
_pre_market_cache_instance = None


def get_pre_market_cache() -> PreMarketCache:
    """
    获取盘前预计算缓存实例（单例）

    Returns:
        PreMarketCache: 缓存实例
    """
    global _pre_market_cache_instance

    if _pre_market_cache_instance is None:
        _pre_market_cache_instance = PreMarketCache()

    return _pre_market_cache_instance


def should_precompute_now() -> bool:
    """
    判断是否应该执行盘前预计算

    Returns:
        bool: 是否应该执行预计算
    """
    now = datetime.now()
    current_time = now.time()

    # 在9:25之前，且缓存无效时执行预计算
    if current_time < dt_time(9, 25):
        cache = get_pre_market_cache()
        return not cache.is_cache_valid()

    return False


def auto_precompute_if_needed(stock_codes: list = None, max_stocks: int = 1000) -> bool:
    """
    自动执行盘前预计算（如果需要）

    Args:
        stock_codes: 股票代码列表
        max_stocks: 最大处理股票数量

    Returns:
        bool: 是否执行了预计算
    """
    if should_precompute_now():
        logger.info("🚀 [自动预计算] 触发盘前预计算...")
        cache = get_pre_market_cache()
        cache.precompute_ma4(stock_codes, max_stocks)
        return True

    return False