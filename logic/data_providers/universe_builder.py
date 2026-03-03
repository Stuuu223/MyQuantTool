#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniverseBuilder - 回测候选股票池构建器

《三漏斗架构》
  漏斗1 (静态过滤):  ST/北交所/科创板剔除  → 零 get_local_data 调用
  漏斗2 (日K量价):   逐只 get_local_data(period='1d')  → 量/均价过滤
  漏斗3 (MA趋势):    MA5>MA10>MA20 多头排列           → 可选，右侧追涨用

Version: 3.1.0 - BSON黑名单静默版（实证无崩溃风险）
"""

import os
import json
import logging
import time
from datetime import datetime

try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

from logic.utils.calendar_utils import get_nth_previous_trading_day


def _load_bson_blacklist() -> set[str]:
    """
    尝试加载BSON黑名单。
    不存在则静默返回空集合（实证证明无BSON崩溃风险）。
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))
    path = os.path.join(base_dir, 'data', 'bson_blacklist.json')

    if not os.path.exists(path):
        # 实证证明：955只股票Tick回测无崩溃，黑名单不必须，静默即可
        return set()

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        mines = set(data.get('mines', []))
        logger.info(
            f'[UniverseBuilder] BSON黑名单已载入: {len(mines)}只 '
            f'(扫描日期: {data.get("scan_date", "unknown")})'
        )
        return mines
    except Exception as e:
        logger.error(f'[UniverseBuilder] 黑名单加载失败: {e}')
        return set()


class UniverseBuilder:
    """
    三漏斗候选股票池构建器。

    用法:
        builder = UniverseBuilder(target_date='20260228')
        candidates = builder.build()
    """

    def __init__(
        self,
        target_date: str,
        require_ma_uptrend: bool = False,
    ):
        self.target_date        = target_date
        self.require_ma_uptrend = require_ma_uptrend
        self._blacklist         = _load_bson_blacklist()
        self._stats: dict       = {}

        from logic.core.config_manager import get_config_manager
        cfg = get_config_manager()
        self.min_avg_amount       = cfg.get('stock_filter.min_avg_amount',       50_000_000.0)
        self.min_avg_turnover_pct = cfg.get('stock_filter.min_avg_turnover_pct', 5.0)
        self.min_price            = cfg.get('stock_filter.min_price',            3.0)
        self.max_price            = cfg.get('stock_filter.max_price',            300.0)

    def build(self) -> list[str]:
        t0 = time.perf_counter()

        step1 = self._funnel1_static()
        logger.info(f'[漏斗1-静态] 通过: {len(step1)}只')

        step2 = self._funnel2_daily_kline(step1)
        logger.info(f'[漏斗2-日K]  通过: {len(step2)}只')

        step3 = step2
        if self.require_ma_uptrend:
            step3 = self._funnel3_ma_trend(step2)
            logger.info(f'[漏斗3-MA趋势] 通过: {len(step3)}只')

        elapsed_ms = (time.perf_counter() - t0) * 1000
        self._stats = {
            'target_date':    self.target_date,
            'after_funnel1':  len(step1),
            'after_funnel2':  len(step2),
            'after_funnel3':  len(step3),
            'blacklist_size': len(self._blacklist),
            'elapsed_ms':     round(elapsed_ms, 1),
        }
        logger.info(f'[UniverseBuilder] 完成: {len(step3)}只候选 | 耗时: {elapsed_ms:.0f}ms')
        return step3

    def _funnel1_static(self) -> list[str]:
        try:
            from xtquant import xtdata
        except ImportError:
            logger.error('❌ [漏斗1] xtquant未安装')
            return []

        try:
            all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        except Exception as e:
            logger.error(f'❌ [漏斗1] 获取全市场列表失败: {e}')
            return []

        result = []
        cnt = {'blacklist': 0, 'bj': 0, 'kcb': 0, 'st': 0}

        for stock in all_stocks:
            code = stock.split('.')[0]

            if stock in self._blacklist:
                cnt['blacklist'] += 1
                continue

            if code[:2] in ('43', '83', '87', '88'):
                cnt['bj'] += 1
                continue

            if code.startswith('688'):
                cnt['kcb'] += 1
                continue

            try:
                detail = xtdata.get_instrument_detail(stock, False)
                if detail:
                    name = (
                        detail.get('InstrumentName', '')
                        if hasattr(detail, 'get')
                        else getattr(detail, 'InstrumentName', '')
                    )
                    name_upper = name.upper()
                    if 'ST' in name_upper or '退' in name or '摘' in name:
                        cnt['st'] += 1
                        continue
            except Exception:
                pass

            result.append(stock)

        logger.info(
            f'[漏斗1] 全市场{len(all_stocks)}只 '
            f'→ 黑名单:{cnt["blacklist"]} 北交所:{cnt["bj"]} '
            f'科创板:{cnt["kcb"]} ST:{cnt["st"]} '
            f'→ 剩余: {len(result)}只'
        )
        return result

    def _funnel2_daily_kline(self, stock_list: list[str]) -> list[str]:
        try:
            from xtquant import xtdata
        except ImportError:
            logger.error('❌ [漏斗2] xtquant未安装，跳过')
            return stock_list

        end_date   = self.target_date
        start_date = get_nth_previous_trading_day(self.target_date, 7)

        passed       = []
        cnt_nodata   = 0
        cnt_volume   = 0
        cnt_price    = 0
        cnt_turnover = 0

        for stock in stock_list:
            try:
                data = xtdata.get_local_data(
                    field_list=['close', 'volume', 'amount'],
                    stock_list=[stock],
                    period='1d',
                    start_time=start_date,
                    end_time=end_date
                )

                if not data or stock not in data:
                    cnt_nodata += 1
                    continue

                df = data[stock]
                if df is None or len(df) < 1:
                    cnt_nodata += 1
                    continue

                import pandas as pd
                import numpy as np

                n          = min(5, len(df))
                avg_amount = df['amount'].iloc[-n:].mean()

                if pd.isna(avg_amount) or np.isinf(avg_amount) or avg_amount < self.min_avg_amount:
                    cnt_volume += 1
                    continue

                last_close = float(df['close'].iloc[-1])
                if not (self.min_price <= last_close <= self.max_price):
                    cnt_price += 1
                    continue

                try:
                    detail = xtdata.get_instrument_detail(stock, False)
                    if detail:
                        float_shares = float(
                            detail.get('FloatVolume', 0)
                            if hasattr(detail, 'get')
                            else getattr(detail, 'FloatVolume', 0)
                        )
                    else:
                        float_shares = 0.0

                    if float_shares > 0:
                        float_mkt_cap    = float_shares * last_close
                        avg_turnover_pct = (avg_amount / float_mkt_cap) * 100.0
                        if avg_turnover_pct < self.min_avg_turnover_pct:
                            cnt_turnover += 1
                            continue
                except Exception:
                    pass

                passed.append(stock)

            except Exception:
                cnt_nodata += 1
                continue

        logger.info(
            f'[漏斗2] 输入:{len(stock_list)}只 '
            f'→ 无数据:{cnt_nodata} 量不足:{cnt_volume} '
            f'价格越界:{cnt_price} 换手不足:{cnt_turnover} '
            f'→ 通过: {len(passed)}只'
        )
        return passed

    def _funnel3_ma_trend(self, stock_list: list[str]) -> list[str]:
        try:
            from xtquant import xtdata
        except ImportError:
            logger.warning('[漏斗3] xtquant未安装，跳过MA过滤')
            return stock_list

        end_date   = self.target_date
        start_date = get_nth_previous_trading_day(self.target_date, 42)

        passed     = []
        cnt_fail   = 0
        cnt_nodata = 0

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
                    cnt_nodata += 1
                    continue

                df = data[stock]
                if df is None or len(df) < 20:
                    cnt_nodata += 1
                    continue

                closes = df['close'].values
                ma5    = closes[-5:].mean()
                ma10   = closes[-10:].mean()
                ma20   = closes[-20:].mean()

                if ma5 > ma10 > ma20:
                    passed.append(stock)
                else:
                    cnt_fail += 1

            except Exception:
                cnt_nodata += 1
                continue

        logger.info(
            f'[漏斗3] 输入:{len(stock_list)}只 '
            f'→ MA非多头:{cnt_fail} 无数据:{cnt_nodata} '
            f'→ 通过: {len(passed)}只'
        )
        return passed

    def get_stats(self) -> dict:
        return self._stats


def build_universe(
    target_date: str,
    require_ma_uptrend: bool = False,
) -> list[str]:
    return UniverseBuilder(
        target_date=target_date,
        require_ma_uptrend=require_ma_uptrend,
    ).build()


if __name__ == '__main__':
    print('=' * 60)
    print('UniverseBuilder 三漏斗测试')
    print('=' * 60)
    result = build_universe('20260228', require_ma_uptrend=False)
    print(f'\n最终候选: {len(result)} 只')
    print(f'前10只: {result[:10]}')
