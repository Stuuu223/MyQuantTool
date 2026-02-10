#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史价格数据获取器 - 基于现有的fetch_1m_data.py

复用逻辑：
- 使用tools/fetch_1m_data.py的QMT连接和数据下载功能
- 封装为统一的价格获取接口
- 支持T+1/T+5/T+10收益计算

Author: MyQuantTool Team
Date: 2026-02-10
Version: V1.0 (基于tools/fetch_1m_data.py)
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False
    print("⚠️ xtquant未安装，QMT数据源不可用")

from logic.logger import get_logger

logger = get_logger(__name__)


class PriceHistoryFetcher:
    """
    历史价格数据获取器

    复用tools/fetch_1m_data.py的QMT连接功能
    封装为统一的价格获取接口
    """

    def __init__(self):
        if not QMT_AVAILABLE:
            raise ImportError("❌ xtquant未安装，无法使用QMT数据源")

        logger.info("✅ 价格数据获取器初始化完成（基于QMT）")

    def get_future_prices(self, stock_code: str, base_date: str, days: List[int]) -> Dict[int, float]:
        """
        获取未来N天的收盘价（用于计算T+1/T+5收益）

        Args:
            stock_code: 股票代码（QMT格式，如 002555.SZ）
            base_date: 基准日期（格式：YYYY-MM-DD）
            days: 需要获取的天数列表（如 [1, 5, 10]）

        Returns:
            dict: {1: 26.50, 5: 28.30, 10: 29.80}
        """
        try:
            # 转换日期格式（YYYY-MM-DD → YYYYMMDD）
            base_dt = datetime.strptime(base_date, '%Y-%m-%d')
            base_date_qmt = base_dt.strftime('%Y%m%d')

            # 计算截止日期（base_date + max(days) + 15个自然日缓冲）
            end_dt = base_dt + timedelta(days=max(days) + 15)
            end_date_qmt = end_dt.strftime('%Y%m%d')

            # 使用QMT获取日K线（复用tools/fetch_1m_data.py的逻辑）
            # 🔥 关键：使用download_history_data2先下载到本地缓存
            xtdata.download_history_data2(
                stock_list=[stock_code],
                period='1d',
                start_time=base_date_qmt,
                end_time=end_date_qmt
            )

            # 🔥 关键：从本地缓存读取数据
            data = xtdata.get_market_data(
                field_list=['time', 'close'],
                stock_list=[stock_code],
                period='1d',
                start_time=base_date_qmt,
                end_time=end_date_qmt,
                count=-1,
                dividend_type='front',  # 前复权
                fill_data=True
            )

            if not data or 'close' not in data or stock_code not in data['close'].index:
                logger.warning(f"⚠️ {stock_code} 未来价格数据缺失")
                return {}

            # 提取收盘价序列
            close_series = data['close'].loc[stock_code]

            if len(close_series) == 0:
                logger.warning(f"⚠️ {stock_code} K线数据为空")
                return {}

            # 提取目标日期的收盘价
            result = {}
            for day in days:
                if day < len(close_series):
                    result[day] = float(close_series.iloc[day])
                else:
                    logger.warning(f"⚠️ {stock_code} T+{day} 数据不足（只有{len(close_series)}天）")

            return result

        except Exception as e:
            logger.error(f"❌ 获取未来价格失败 {stock_code}: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def calculate_return(self, buy_price: float, sell_price: float) -> float:
        """
        计算收益率

        Args:
            buy_price: 买入价
            sell_price: 卖出价

        Returns:
            float: 收益率（百分比）
        """
        if buy_price == 0 or buy_price is None or sell_price is None:
            return 0.0

        return (sell_price - buy_price) / buy_price * 100

    def batch_get_future_prices(self, stock_codes: List[str], base_date: str, days: List[int]) -> Dict[str, Dict[int, float]]:
        """
        批量获取多只股票的未来价格

        Args:
            stock_codes: 股票代码列表
            base_date: 基准日期
            days: 需要获取的天数列表

        Returns:
            dict: {code: {1: price1, 5: price5}}
        """
        results = {}

        logger.info(f"📊 批量获取价格数据: {len(stock_codes)} 只股票")

        for i, code in enumerate(stock_codes, 1):
            logger.info(f"   [{i}/{len(stock_codes)}] 获取 {code}...")
            prices = self.get_future_prices(code, base_date, days)
            if prices:
                results[code] = prices

        logger.info(f"✅ 批量获取完成: {len(results)}/{len(stock_codes)} 只股票")

        return results


if __name__ == "__main__":
    # 单元测试
    print()
    print("=" * 80)
    print("🧪 价格数据获取器 - 单元测试")
    print("=" * 80)
    print()

    fetcher = PriceHistoryFetcher()

    # 测试：获取002555的T+1/T+5价格
    test_code = "002555.SZ"
    test_date = "2026-02-07"

    logger.info(f"测试：获取 {test_code} 在 {test_date} 的未来价格")
    prices = fetcher.get_future_prices(test_code, test_date, [1, 5, 10])

    if prices:
        logger.info(f"✅ 成功获取价格数据:")
        for day, price in prices.items():
            logger.info(f"   T+{day}: ¥{price:.2f}")

        # 测试收益率计算
        buy_price = 26.0
        if 1 in prices:
            t1_return = fetcher.calculate_return(buy_price, prices[1])
            logger.info(f"\n📊 收益率测试:")
            logger.info(f"   买入价: ¥{buy_price:.2f}")
            logger.info(f"   T+1价格: ¥{prices[1]:.2f}")
            logger.info(f"   T+1收益: {t1_return:+.2f}%")
    else:
        logger.error("❌ 获取价格数据失败")

    print()
    print("=" * 80)