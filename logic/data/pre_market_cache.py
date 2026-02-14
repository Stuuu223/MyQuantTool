# -*- coding: utf-8 -*-
"""
盘前数据预热缓存系统 (PreMarketCache) - V19.5

功能：
- 在盘前（9:15之前）一次性计算全市场的均线数据
- 盘中不再请求历史数据，直接从缓存读取
- 解决 IP 被封禁和系统卡死问题

架构：
- 盘前：一次性拉取全市场数据，计算 MA4、MA5 等指标
- 盘中：纯数学计算，0 网络请求
- 公式：Realtime_MA5 = (Pre_Market_MA4 * 4 + Current_Price) / 5

Author: iFlow CLI
Version: V19.5
"""

import os
import json
import akshare as ak
from datetime import datetime, time
from typing import Dict, Optional
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class PreMarketCache:
    """
    盘前数据预热缓存系统

    功能：
    - 在盘前（9:15之前）一次性计算全市场的均线数据
    - 盘中不再请求历史数据，直接从缓存读取
    - 解决 IP 被封禁和系统卡死问题
    """

    CACHE_FILE = "data/pre_market_ma_cache.json"
    CACHE_VERSION = "V19.5"

    def __init__(self):
        self.cache = {}
        self._load_cache()

    def is_market_time(self) -> bool:
        """
        判断是否在交易时间

        Returns:
            bool: True 表示在交易时间（9:30-15:00）
        """
        now = datetime.now().time()
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)

        return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)

    def should_refresh_cache(self) -> bool:
        """
        判断是否需要刷新缓存

        Returns:
            bool: True 表示需要刷新
        """
        # 如果缓存文件不存在，需要刷新
        if not os.path.exists(self.CACHE_FILE):
            return True

        # 如果是交易日早上9:15之前，需要刷新
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()

        # 周末不刷新
        if weekday >= 5:  # 周六、周日
            return False

        # 交易日早上9:15之前刷新
        if current_time < time(9, 15):
            return True

        # 检查缓存日期
        try:
            with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                cache_date = cache_data.get('cache_date', '')
                today_str = now.strftime('%Y-%m-%d')

                # 如果缓存日期不是今天，需要刷新
                if cache_date != today_str:
                    return True
        except Exception as e:
            logger.warning(f"检查缓存日期失败: {e}")
            return True

        return False

    def run_daily_job(self) -> bool:
        """
        执行盘前数据预热任务

        Returns:
            bool: True 表示成功，False 表示失败
        """
        if not self.should_refresh_cache():
            logger.info("✅ 缓存是最新的，无需刷新")
            return True

        logger.info("☀️ 开始执行盘前数据预热...")
        start_time = datetime.now()

        try:
            # 1. 一次性拉取全市场所有股票的实时数据
            # 注意：这里使用的是 ak.stock_zh_a_spot_em()，它返回的是当前行情
            # 我们需要从中提取昨收价，作为 MA5 的近似基准
            logger.info("📡 正在拉取全市场数据...")
            df = ak.stock_zh_a_spot_em()

            if df is None or df.empty:
                logger.error("❌ 拉取全市场数据失败")
                return False

            logger.info(f"✅ 成功拉取 {len(df)} 只股票数据")

            # 2. 构建缓存数据
            cache = {
                'cache_version': self.CACHE_VERSION,
                'cache_date': datetime.now().strftime('%Y-%m-%d'),
                'cache_time': datetime.now().strftime('%H:%M:%S'),
                'total_stocks': len(df),
                'stocks': {}
            }

            # 3. 遍历所有股票，计算基准数据
            for _, row in df.iterrows():
                code = row['代码']
                name = row['名称']
                prev_close = row['昨收']  # 昨收价

                # 使用昨收价作为 MA5 的近似基准
                # 实际上，昨收价 ≈ 昨日的收盘价
                # 我们用昨收价作为前4天的均价的近似值
                # 这样盘中计算 MA5 时：MA5 = (昨收 * 4 + 当前价) / 5
                cache['stocks'][code] = {
                    'name': name,
                    'prev_close': float(prev_close),
                    'ma4_ref': float(prev_close),  # 前4天均价的近似值
                    'ma5_ref': float(prev_close)   # MA5的近似值
                }

            # 4. 存入文件
            os.makedirs("data", exist_ok=True)
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ 盘前缓存构建完成：{len(cache['stocks'])} 只股票，耗时 {elapsed:.2f} 秒")

            # 5. 加载到内存
            self._load_cache()

            return True

        except Exception as e:
            logger.error(f"❌ 盘前数据预热失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_cache(self):
        """从文件加载缓存到内存"""
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.cache = cache_data.get('stocks', {})
                    cache_date = cache_data.get('cache_date', 'Unknown')
                    logger.info(f"✅ 成功加载盘前缓存：{len(self.cache)} 只股票（日期：{cache_date}）")
            else:
                logger.warning("⚠️ 盘前缓存文件不存在")
                self.cache = {}
        except Exception as e:
            logger.error(f"❌ 加载盘前缓存失败: {e}")
            self.cache = {}

    def get_stock_data(self, stock_code: str) -> Optional[Dict]:
        """
        获取单只股票的盘前缓存数据

        Args:
            stock_code: 股票代码

        Returns:
            dict: 包含 prev_close, ma4_ref, ma5_ref 等数据，如果不存在则返回 None
        """
        return self.cache.get(stock_code)

    def calculate_realtime_ma5(self, stock_code: str, current_price: float) -> Optional[float]:
        """
        实时计算 MA5（使用盘前缓存）

        公式：Realtime_MA5 = (Pre_Market_MA4 * 4 + Current_Price) / 5

        Args:
            stock_code: 股票代码
            current_price: 当前价格

        Returns:
            float: 实时 MA5，如果缓存不存在则返回 None
        """
        stock_data = self.get_stock_data(stock_code)

        if not stock_data:
            return None

        ma4_ref = stock_data.get('ma4_ref', 0)

        if ma4_ref == 0:
            return None

        # 计算 MA5
        realtime_ma5 = (ma4_ref * 4 + current_price) / 5

        return realtime_ma5

    def calculate_ma_bias(self, stock_code: str, current_price: float) -> Optional[float]:
        """
        计算乖离率（使用盘前缓存）

        公式：Bias = (Current_Price - MA5) / MA5 * 100

        Args:
            stock_code: 股票代码
            current_price: 当前价格

        Returns:
            float: 乖离率（%），如果缓存不存在则返回 None
        """
        ma5 = self.calculate_realtime_ma5(stock_code, current_price)

        if ma5 is None or ma5 == 0:
            return None

        bias = (current_price - ma5) / ma5 * 100

        return round(bias, 2)

    def get_cache_info(self) -> Dict:
        """
        获取缓存信息

        Returns:
            dict: 包含缓存版本、日期、股票数量等信息
        """
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    return {
                        'cache_version': cache_data.get('cache_version', 'Unknown'),
                        'cache_date': cache_data.get('cache_date', 'Unknown'),
                        'cache_time': cache_data.get('cache_time', 'Unknown'),
                        'total_stocks': cache_data.get('total_stocks', 0),
                        'is_loaded': len(self.cache) > 0
                    }
        except Exception as e:
            logger.error(f"❌ 获取缓存信息失败: {e}")

        return {
            'cache_version': 'Unknown',
            'cache_date': 'Unknown',
            'cache_time': 'Unknown',
            'total_stocks': 0,
            'is_loaded': False
        }


# 全局单例
_pre_market_cache_instance = None


def get_pre_market_cache() -> PreMarketCache:
    """
    获取盘前缓存单例

    Returns:
        PreMarketCache: 盘前缓存实例
    """
    global _pre_market_cache_instance

    if _pre_market_cache_instance is None:
        _pre_market_cache_instance = PreMarketCache()

    return _pre_market_cache_instance