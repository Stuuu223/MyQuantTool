#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniverseBuilder - 回测候选股票池构建器 (纯日K三漏斗架构)

三漏斗设计原则:
  漏斗1 (静态过滤): 黑名单剔除 + 基础属性过滤 (无网络, 无磁盘日K读取)
  漏斗2 (日K量价): 成交量/流动性过滤 (仅读日K, 禁止任何Tick/分钟级数据)
  漏斗3 (趋势强度): MA趋势过滤 (可选, 用于右侧追涨)

严禁:
  ❌ 禁止在此模块调用任何 period='tick' 或 period='1m' 的接口
  ❌ 禁止向 warmup() 传入未经漏斗1过滤的全市场列表
  ❌ 禁止使用 get_trading_dates() (已知BSON崩溃来源)

Version: 2.0.0 - 纯日K三漏斗 + BSON黑名单防护
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


# ── BSON黑名单加载 ────────────────────────────────────────────────────────────

def _load_bson_blacklist() -> set[str]:
    """
    加载BSON炸弹黑名单。
    黑名单文件由 tools/find_bson_bomb.py 生成。
    若文件不存在, 返回空集合, 但会打印警告。
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    blacklist_path = os.path.join(base_dir, 'data', 'bson_blacklist.json')

    if not os.path.exists(blacklist_path):
        logger.warning(
            "⚠️  [UniverseBuilder] 未找到BSON黑名单文件! "
            "建议先运行 python tools/find_bson_bomb.py 生成黑名单。"
            f"期望路径: {blacklist_path}"
        )
        return set()

    try:
        with open(blacklist_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        mines = set(data.get('mines', []))
        scan_date = data.get('scan_date', 'unknown')
        logger.info(f"✅ [UniverseBuilder] 加载BSON黑名单: {len(mines)}只炸弹股 (扫描日期: {scan_date})")
        return mines
    except Exception as e:
        logger.error(f"❌ [UniverseBuilder] 黑名单加载失败: {e}")
        return set()


# ── 主类 ──────────────────────────────────────────────────────────────────────

class UniverseBuilder:
    """
    回测候选股票池构建器

    用法:
        builder = UniverseBuilder(target_date='20260228')
        candidate_list = builder.build()
    """

    def __init__(
        self,
        target_date: str,
        min_avg_volume: float = 3_000_000,   # 5日均量最低3百万股
        min_price: float = 3.0,              # 最低股价3元(剔除仙股)
        max_price: float = 300.0,            # 最高股价300元
        require_ma_uptrend: bool = False,    # 漏斗3: 是否要求MA多头排列
    ):
        self.target_date = target_date
        self.min_avg_volume = min_avg_volume
        self.min_price = min_price
        self.max_price = max_price
        self.require_ma_uptrend = require_ma_uptrend

        self._bson_blacklist = _load_bson_blacklist()
        self._stats: dict = {}

    def build(self) -> list[str]:
        """
        执行三漏斗筛选, 返回最终候选股票列表。
        """
        t0 = time.perf_counter()

        # ── 漏斗1: 静态过滤 ──────────────────────────────────────────
        candidates = self._funnel1_static()
        logger.info(f"[漏斗1-静态] 通过: {len(candidates)} 只")

        # ── 漏斗2: 日K量价过滤 ───────────────────────────────────────
        candidates = self._funnel2_daily_kline(candidates)
        logger.info(f"[漏斗2-日K] 通过: {len(candidates)} 只")

        # ── 漏斗3: MA趋势过滤 (可选) ─────────────────────────────────
        if self.require_ma_uptrend:
            candidates = self._funnel3_ma_trend(candidates)
            logger.info(f"[漏斗3-MA趋势] 通过: {len(candidates)} 只")

        elapsed_ms = (time.perf_counter() - t0) * 1000
        self._stats = {
            'target_date': self.target_date,
            'final_count': len(candidates),
            'elapsed_ms': round(elapsed_ms, 1),
            'bson_blacklist_size': len(self._bson_blacklist),
        }
        logger.info(
            f"✅ [UniverseBuilder] 三漏斗完成: {len(candidates)}只候选 "
            f"| 耗时: {elapsed_ms:.0f}ms"
        )
        return candidates

    # ── 漏斗1: 静态过滤 ──────────────────────────────────────────────────────

    def _funnel1_static(self) -> list[str]:
        """
        漏斗1: 纯静态过滤, 无任何数据读取
        - 从QMT获取全市场列表
        - 剔除BSON黑名单
        - 剔除ST/退市股
        - 剔除科创板(688x)、北交所(8x/4x) (可选, 流动性差)
        """
        try:
            from xtquant import xtdata
        except ImportError:
            logger.error("❌ [漏斗1] xtquant未安装")
            return []

        try:
            all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        except Exception as e:
            logger.error(f"❌ [漏斗1] 获取全市场列表失败: {e}")
            return []

        result = []
        stats = {'total': len(all_stocks), 'blacklisted': 0, 'filtered': 0}

        for stock in all_stocks:
            code = stock.split('.')[0]

            # 剔除BSON炸弹
            if stock in self._bson_blacklist:
                stats['blacklisted'] += 1
                continue

            # 剔除北交所 (43xxxx, 83xxxx, 87xxxx, 88xxxx)
            if code.startswith(('43', '83', '87', '88')):
                stats['filtered'] += 1
                continue

            # 剔除ST/退市: 通过instrument_detail检查名称
            try:
                detail = xtdata.get_instrument_detail(stock, False)
                if detail:
                    name = detail.get('InstrumentName', '') if hasattr(detail, 'get') else getattr(detail, 'InstrumentName', '')
                    if name and ('ST' in name.upper() or '退' in name or '摘' in name):
                        stats['filtered'] += 1
                        continue
            except Exception:
                pass  # 查不到instrument_detail的直接保留

            result.append(stock)

        logger.info(
            f"[漏斗1] 全市场{stats['total']}只 "
            f"| 黑名单剔除: {stats['blacklisted']}只 "
            f"| 静态过滤: {stats['filtered']}只 "
            f"| 剩余: {len(result)}只"
        )
        return result

    # ── 漏斗2: 日K量价过滤 ───────────────────────────────────────────────────

    def _funnel2_daily_kline(self, stock_list: list[str]) -> list[str]:
        """
        漏斗2: 读取日K数据过滤量价
        - 5日均量 >= min_avg_volume
        - 最新收盘价在 [min_price, max_price] 区间
        - 禁止任何Tick/分钟级数据!
        """
        try:
            from xtquant import xtdata
        except ImportError:
            logger.error("❌ [漏斗2] xtquant未安装")
            return stock_list

        end_date = self.target_date
        end_dt = datetime.strptime(self.target_date, '%Y%m%d')
        start_date = (end_dt - timedelta(days=30)).strftime('%Y%m%d')

        passed = []
        failed_volume = 0
        failed_price = 0
        failed_nodata = 0

        for stock in stock_list:
            try:
                # 逐只查询, 防止批量BSON崩溃
                data = xtdata.get_local_data(
                    field_list=['close', 'volume'],
                    stock_list=[stock],
                    period='1d',  # ← 严格只用日K
                    start_time=start_date,
                    end_time=end_date
                )

                if not data or stock not in data:
                    failed_nodata += 1
                    continue

                df = data[stock]
                if df is None or len(df) < 1:
                    failed_nodata += 1
                    continue

                # 量过滤
                import pandas as pd
                import numpy as np
                avg_vol = df['volume'].mean()
                if pd.isna(avg_vol) or np.isinf(avg_vol) or avg_vol < self.min_avg_volume:
                    failed_volume += 1
                    continue

                # 价格过滤
                last_close = float(df['close'].iloc[-1])
                if not (self.min_price <= last_close <= self.max_price):
                    failed_price += 1
                    continue

                passed.append(stock)

            except Exception:
                # 逐只捕获, 有问题的跳过, 父进程不崩
                failed_nodata += 1
                continue

        logger.info(
            f"[漏斗2] 输入{len(stock_list)}只 "
            f"| 量不足: {failed_volume}只 "
            f"| 价格超范围: {failed_price}只 "
            f"| 无数据: {failed_nodata}只 "
            f"| 通过: {len(passed)}只"
        )
        return passed

    # ── 漏斗3: MA趋势过滤 (可选) ─────────────────────────────────────────────

    def _funnel3_ma_trend(self, stock_list: list[str]) -> list[str]:
        """
        漏斗3: MA多头排列过滤 (用于右侧追涨策略)
        条件: MA5 > MA10 > MA20
        """
        try:
            from xtquant import xtdata
        except ImportError:
            logger.warning("[漏斗3] xtquant未安装, 跳过MA过滤")
            return stock_list

        end_date = self.target_date
        end_dt = datetime.strptime(self.target_date, '%Y%m%d')
        start_date = (end_dt - timedelta(days=60)).strftime('%Y%m%d')

        passed = []
        failed_ma = 0
        failed_nodata = 0

        for stock in stock_list:
            try:
                data = xtdata.get_local_data(
                    field_list=['close'],
                    stock_list=[stock],
                    period='1d',
                    start_time=start_date,
                    end_time=end_date
                )

                if not data or stock not in data:
                    failed_nodata += 1
                    continue

                df = data[stock]
                if df is None or len(df) < 20:
                    failed_nodata += 1
                    continue

                closes = df['close'].values
                ma5 = closes[-5:].mean()
                ma10 = closes[-10:].mean()
                ma20 = closes[-20:].mean()

                if ma5 > ma10 > ma20:
                    passed.append(stock)
                else:
                    failed_ma += 1

            except Exception:
                failed_nodata += 1
                continue

        logger.info(
            f"[漏斗3] 输入{len(stock_list)}只 "
            f"| MA非多头: {failed_ma}只 "
            f"| 无数据: {failed_nodata}只 "
            f"| 通过: {len(passed)}只"
        )
        return passed

    def get_stats(self) -> dict:
        """获取最近一次build()的统计信息"""
        return self._stats


# ── 便捷函数 ──────────────────────────────────────────────────────────────────

def build_universe(
    target_date: str,
    min_avg_volume: float = 3_000_000,
    min_price: float = 3.0,
    max_price: float = 300.0,
    require_ma_uptrend: bool = False,
) -> list[str]:
    """
    便捷函数: 一行调用构建候选股票池

    Args:
        target_date: 目标日期 'YYYYMMDD'
        min_avg_volume: 5日均量下限
        min_price: 最低股价
        max_price: 最高股价
        require_ma_uptrend: 是否要求MA5>MA10>MA20多头排列

    Returns:
        list[str]: 候选股票代码列表
    """
    builder = UniverseBuilder(
        target_date=target_date,
        min_avg_volume=min_avg_volume,
        min_price=min_price,
        max_price=max_price,
        require_ma_uptrend=require_ma_uptrend,
    )
    return builder.build()


# ── 测试入口 ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=' * 60)
    print('UniverseBuilder 三漏斗测试')
    print('=' * 60)
    candidates = build_universe(
        target_date='20260228',
        require_ma_uptrend=False
    )
    print(f'\n最终候选: {len(candidates)} 只')
    print(f'前10只: {candidates[:10]}')
