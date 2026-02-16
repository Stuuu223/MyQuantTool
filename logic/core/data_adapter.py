#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据适配器 (Data Adapter)

V16.0 - 统一数据获取接口
封装现有的provider，提供统一的数据访问接口

核心功能：
1. 批量获取实时快照（支持并发优化）
2. 获取昨日涨停池（用于情绪计算）
3. 处理Windows编码问题
4. 与现有provider无缝兼容

Author: MyQuantTool Team
Date: 2026-02-16
"""

import pandas as pd
import platform
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

# 尝试导入 QMT，如果失败则静默降级
try:
    from xtquant import xtdata
    HAS_QMT = True
except ImportError:
    HAS_QMT = False

# 导入现有的provider（适配现有架构）
from logic.data_providers import get_provider
from logic.utils.code_converter import CodeConverter
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class DataAdapter:
    """
    数据适配器（V16.0）

    职责：
    - 封装现有的provider，提供统一的接口
    - 处理Windows编码问题
    - 支持批量获取数据（为并发优化做准备）
    - 提供数据缓存和TTL管理
    """

    def __init__(self, use_qmt: bool = True):
        """
        初始化数据适配器

        Args:
            use_qmt: 是否使用QMT数据源
        """
        self.os_type = platform.system()
        self.is_windows = self.os_type == 'Windows'
        self.has_qmt = HAS_QMT  # 初始化has_qmt属性
        self.use_qmt = use_qmt and self.has_qmt

        # 初始化现有的provider（适配现有架构）
        try:
            self.level1_provider = get_provider('level1')
            logger.info("✅ Level-1 提供者已初始化")
        except Exception as e:
            logger.warning(f"⚠️ Level-1 提供者初始化失败: {e}")
            self.level1_provider = None

        # 代码转换器
        self.converter = CodeConverter()

        # 数据缓存（用于优化性能）
        self.cache = {}
        self.cache_ttl = 5  # 缓存有效期5秒

        logger.info(f"✅ 数据适配器初始化成功 (OS: {self.os_type}, QMT: {HAS_QMT})")

    def _safe_read_csv(self, file_path: str) -> pd.DataFrame:
        """
        [Windows编码卫士] 安全读取CSV，自动尝试 utf-8 和 gbk

        Args:
            file_path: 文件路径

        Returns:
            pd.DataFrame: 读取的数据
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return pd.DataFrame()

        try:
            # 优先尝试 UTF-8 (标准)
            return pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            # 降级尝试 GBK (Windows常见)
            logger.warning(f"UTF-8读取失败，尝试GBK: {file_path}")
            try:
                return pd.read_csv(file_path, encoding='gbk')
            except Exception as e:
                logger.error(f"文件读取彻底失败 {file_path}: {e}")
                return pd.DataFrame()

    def _safe_write_csv(self, df: pd.DataFrame, file_path: str) -> bool:
        """
        [Windows编码卫士] 安全写入CSV，强制使用 utf-8

        Args:
            df: 要写入的数据
            file_path: 文件路径

        Returns:
            bool: 是否写入成功
        """
        try:
            # 强制使用 UTF-8 (标准)
            df.to_csv(file_path, index=False, encoding='utf-8')
            return True
        except Exception as e:
            logger.error(f"文件写入失败 {file_path}: {e}")
            return False

    def get_realtime_snapshot(self, code_list: List[str]) -> pd.DataFrame:
        """
        获取实时快照（批量）

        Args:
            code_list: 股票代码列表

        Returns:
            pd.DataFrame: 实时快照数据
        """
        if not code_list:
            return pd.DataFrame()

        # 生成缓存键
        cache_key = f"snapshot_{'_'.join(sorted(code_list))}"
        cache_time = datetime.now()

        # 检查缓存
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (cache_time - cached_time).total_seconds() < self.cache_ttl:
                logger.debug(f"使用缓存数据: {cache_key}")
                return cached_data

        # 获取数据（优先使用现有provider）
        if self.level1_provider is not None:
            try:
                # 使用现有provider获取数据
                df = self._fetch_via_provider(code_list)

                # 缓存数据
                self.cache[cache_key] = (df, cache_time)

                return df
            except Exception as e:
                logger.error(f"Provider数据获取失败: {e}")

        # 降级到QMT直接获取
        if self.use_qmt:
            try:
                df = self._fetch_via_qmt(code_list)

                # 缓存数据
                self.cache[cache_key] = (df, cache_time)

                return df
            except Exception as e:
                logger.error(f"QMT数据获取失败: {e}")

        logger.warning("所有数据源均失败，返回空DataFrame")
        return pd.DataFrame()

    def _fetch_via_provider(self, code_list: List[str]) -> pd.DataFrame:
        """
        通过现有provider获取数据（适配现有架构）

        Args:
            code_list: 股票代码列表

        Returns:
            pd.DataFrame: 数据
        """
        # 尝试使用data_source_manager（极速层）
        try:
            from logic.data_providers.data_source_manager import get_data_source_manager

            ds = get_data_source_manager()
            tick_data = ds.get_realtime_price_fast(code_list)

            if tick_data:
                data_list = []
                for code, tick in tick_data.items():
                    # 转换为统一格式
                    last_close = tick.get('close', 0)
                    price = tick.get('price', 0)
                    pct_chg = (price - last_close) / last_close if last_close > 0 else 0

                    data_list.append({
                        'code': code,
                        'price': price,
                        'open': tick.get('open', 0),
                        'high': tick.get('high', 0),
                        'low': tick.get('low', 0),
                        'vol': tick.get('volume', 0),
                        'amount': tick.get('turnover', 0),
                        'last_close': last_close,
                        'pct_chg': pct_chg,
                        'volume_ratio': 0,  # 需要额外计算
                        'bid1_vol': 0,  # 极速层不提供盘口数据
                        'ask1_vol': 0,
                    })

                if data_list:
                    return pd.DataFrame(data_list)
        except Exception as e:
            logger.warning(f"data_source_manager获取数据失败: {e}")

        # 降级方案：返回空DataFrame
        return pd.DataFrame()

    def _fetch_via_qmt(self, code_list: List[str]) -> pd.DataFrame:
        """
        通过QMT直接获取数据（降级方案）

        Args:
            code_list: 股票代码列表

        Returns:
            pd.DataFrame: 数据
        """
        try:
            # 批量获取 QMT 数据
            full_tick = xtdata.get_full_tick(code_list)
            if not full_tick:
                return pd.DataFrame()

            # 快速转换为 DataFrame
            data_list = []
            for code, tick in full_tick.items():
                data_list.append({
                    'code': code,
                    'price': tick.get('lastPrice', 0),
                    'open': tick.get('open', 0),
                    'high': tick.get('high', 0),
                    'low': tick.get('low', 0),
                    'vol': tick.get('volume', 0),
                    'amount': tick.get('amount', 0),
                    'last_close': tick.get('lastClose', 0),
                    'pct_chg': (tick.get('lastPrice', 0) - tick.get('lastClose', 0)) / tick.get('lastClose', 1) if tick.get('lastClose', 0) > 0 else 0,
                    'volume_ratio': 0,  # 需要额外计算
                    'bid1_vol': tick.get('bidVol', [0])[0] if isinstance(tick.get('bidVol'), list) else 0,
                    'ask1_vol': tick.get('askVol', [0])[0] if isinstance(tick.get('askVol'), list) else 0,
                })

            return pd.DataFrame(data_list)
        except Exception as e:
            logger.error(f"QMT数据获取异常: {e}")
            return pd.DataFrame()

    def get_yesterday_limit_up_pool(self) -> List[str]:
        """
        获取昨日涨停池（用于情绪计算）

        Returns:
            List[str]: 涨停股票代码列表
        """
        # 尝试从本地缓存读取
        cache_file = "data/cache/yesterday_limit_up_pool.csv"
        if os.path.exists(cache_file):
            df = self._safe_read_csv(cache_file)
            if not df.empty:
                # 检查文件日期是否是昨天
                file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
                if (datetime.now() - file_time).days <= 1:
                    # 确保代码都是字符串格式
                    codes = [str(code) for code in df['code'].tolist()]
                    logger.info(f"从缓存读取昨日涨停池: {len(codes)} 只股票")
                    return codes

        # 尝试从AkShare获取
        try:
            import akshare as ak

            # 获取昨天日期
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

            # 获取涨停池
            limit_stocks = ak.stock_zt_pool_em(date=yesterday)

            if not limit_stocks.empty:
                # 确保代码都是字符串格式
                codes = [str(code) for code in limit_stocks['代码'].tolist()]

                # 缓存到本地
                df = pd.DataFrame({'code': codes})
                os.makedirs('data/cache', exist_ok=True)
                self._safe_write_csv(df, cache_file)

                logger.info(f"从AkShare获取昨日涨停池: {len(codes)} 只股票")
                return codes
        except Exception as e:
            logger.warning(f"AkShare获取昨日涨停池失败: {e}")

        # 返回空列表
        logger.warning("无法获取昨日涨停池")
        return []

    def get_historical_data(self, code: str, period: str = '1d', start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取历史数据（用于ATR等指标计算）

        Args:
            code: 股票代码
            period: 周期 (1d, 1w, 1m)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            pd.DataFrame: 历史数据
        """
        try:
            if self.use_qmt:
                # 使用QMT获取历史数据
                df = xtdata.get_market_data(
                    stock_list=[code],
                    period=period,
                    start_time=start_date,
                    end_time=end_date,
                    count=-1
                )

                if df is not None and not df.empty:
                    return df

            # 降级到AkShare
            import akshare as ak

            df = ak.stock_zh_a_hist(
                symbol=code.replace('.SH', '').replace('.SZ', ''),
                period="daily" if period == '1d' else "weekly",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )

            return df
        except Exception as e:
            logger.error(f"获取历史数据失败 {code}: {e}")
            return pd.DataFrame()

    def clear_cache(self):
        """
        清空数据缓存
        """
        self.cache.clear()
        logger.info("✅ 数据缓存已清空")


# 全局适配器实例（单例模式）
_global_adapter: DataAdapter = None


def get_data_adapter(use_qmt: bool = True) -> DataAdapter:
    """
    获取全局数据适配器（单例模式）

    Args:
        use_qmt: 是否使用QMT数据源

    Returns:
        DataAdapter: 全局适配器实例
    """
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = DataAdapter(use_qmt=use_qmt)
    return _global_adapter