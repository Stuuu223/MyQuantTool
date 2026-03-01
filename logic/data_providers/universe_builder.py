#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniverseBuilder - 回测候选股票池构建器

【三漏斗架构】
  漏斗1 (静态过滤):  黑名单剔除 + ST/北交所/科创板剔除  → 零 get_local_data 调用
  漏斗2 (日K量价):   逐只 get_local_data(period='1d')  → 量/均价过滤
  漏斗3 (MA趋势):    MA5>MA10>MA20 多头排列           → 可选，右侧追涨用

【铁律】
  ❌ 禁止在任何漏斗中调用 period='tick' 或 period='1m'
  ❌ 禁止向 warmup() 传入未经漏斗1过滤的全市场列表
  ✅ 漏斗2必须在黑名单生成后才能运行（先跑 tools/find_bson_bomb.py）
  ✅ 漏斗2逐只查询，父进程有try/except包裹，单只崩溃不影响整体
     （注意：C++ abort 仍会杀死父进程，这是漏斗2依赖黑名单的根本原因）

【使用顺序】
  1. python tools/find_bson_bomb.py        # 生成 data/bson_blacklist.json
  2. builder = UniverseBuilder('20260228') # 黑名单自动载入
  3. candidates = builder.build()          # 三漏斗筛选
  4. warmup_true_dictionary(candidates)    # 只传候选股，不传全市场

Version: 3.0.0 - 三漏斗正式版
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta

try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


# ── BSON黑名单加载 ────────────────────────────────────────────────────────────

def _load_bson_blacklist() -> set[str]:
    """
    加载黑名单。黑名单由 tools/find_bson_bomb.py 生成。
    若文件不存在，返回空集合并警告（漏斗2会跳过，但有崩溃风险）。
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))
    path = os.path.join(base_dir, 'data', 'bson_blacklist.json')

    if not os.path.exists(path):
        logger.warning(
            '⚠️  [UniverseBuilder] 黑名单文件不存在! '
            '请先运行 python tools/find_bson_bomb.py 生成黑名单。'
            '漏斗2在无黑名单时仍会运行，但有被BSON炸弹崩溃的风险。'
        )
        return set()

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        mines = set(data.get('mines', []))
        logger.info(
            f'✅ [UniverseBuilder] BSON黑名单已载入: {len(mines)}只炸弹股 '
            f'(扫描日期: {data.get("scan_date", "unknown")})'
        )
        return mines
    except Exception as e:
        logger.error(f'❌ [UniverseBuilder] 黑名单加载失败: {e}')
        return set()


# ── 主类 ──────────────────────────────────────────────────────────────────────

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
        min_avg_volume:   float = 3_000_000,  # 5日均量下限 300万股
        min_price:        float = 3.0,         # 最低收盘价
        max_price:        float = 300.0,        # 最高收盘价
        require_ma_uptrend: bool = False,       # 漏斗3开关：MA多头排列
    ):
        self.target_date       = target_date
        self.min_avg_volume    = min_avg_volume
        self.min_price         = min_price
        self.max_price         = max_price
        self.require_ma_uptrend = require_ma_uptrend
        self._blacklist        = _load_bson_blacklist()
        self._stats: dict      = {}

    def build(self) -> list[str]:
        """执行三漏斗筛选，返回候选股票列表。"""
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
            'target_date':        self.target_date,
            'after_funnel1':      len(step1),
            'after_funnel2':      len(step2),
            'after_funnel3':      len(step3),
            'blacklist_size':     len(self._blacklist),
            'elapsed_ms':         round(elapsed_ms, 1),
        }
        logger.info(
            f'✅ [UniverseBuilder] 完成: {len(step3)}只候选 '
            f'| 耗时: {elapsed_ms:.0f}ms'
        )
        return step3

    # ── 漏斗1: 静态过滤 ───────────────────────────────────────────────────────

    def _funnel1_static(self) -> list[str]:
        """
        纯静态过滤，零 get_local_data 调用。
        使用 get_instrument_detail 检查股票名称（ST/退市）。
        """
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

            # 1. 黑名单（BSON炸弹）
            if stock in self._blacklist:
                cnt['blacklist'] += 1
                continue

            # 2. 北交所 (43xxxx 83xxxx 87xxxx 88xxxx)
            if code[:2] in ('43', '83', '87', '88'):
                cnt['bj'] += 1
                continue

            # 3. 科创板 (688xxx)
            if code.startswith('688'):
                cnt['kcb'] += 1
                continue

            # 4. ST / 退市：通过 get_instrument_detail 检查名称
            #    get_instrument_detail 是纯内存C++调用，不触发BSON
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
                pass  # 查不到就保留，交给漏斗2

            result.append(stock)

        logger.info(
            f'[漏斗1] 全市场{len(all_stocks)}只 '
            f'→ 黑名单:{cnt["blacklist"]} 北交所:{cnt["bj"]} '
            f'科创板:{cnt["kcb"]} ST:{cnt["st"]} '
            f'→ 剩余: {len(result)}只'
        )
        return result

    # ── 漏斗2: 日K量价过滤 ────────────────────────────────────────────────────

    def _funnel2_daily_kline(self, stock_list: list[str]) -> list[str]:
        """
        逐只读取日K，过滤量/价。

        【前提】必须先有黑名单（漏斗1已剔除BSON炸弹）。
        【方法】逐只try/except，Python层异常可捕获，跳过问题股票。
               C++ abort无法捕获，依赖黑名单保护。
        【严禁】period='tick' / period='1m'  ← 这会触发全量BSON加载
        """
        try:
            from xtquant import xtdata
        except ImportError:
            logger.error('❌ [漏斗2] xtquant未安装，跳过')
            return stock_list

        end_date   = self.target_date
        end_dt     = datetime.strptime(self.target_date, '%Y%m%d')
        start_date = (end_dt - timedelta(days=30)).strftime('%Y%m%d')

        passed       = []
        cnt_nodata   = 0
        cnt_volume   = 0
        cnt_price    = 0

        for stock in stock_list:
            try:
                data = xtdata.get_local_data(
                    field_list=['close', 'volume'],
                    stock_list=[stock],
                    period='1d',          # ← 只用日K，铁律
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

                # 5日均量（最多取最近5条）
                n = min(5, len(df))
                avg_vol = df['volume'].iloc[-n:].mean()
                if pd.isna(avg_vol) or np.isinf(avg_vol) or avg_vol < self.min_avg_volume:
                    cnt_volume += 1
                    continue

                # 最新收盘价
                last_close = float(df['close'].iloc[-1])
                if not (self.min_price <= last_close <= self.max_price):
                    cnt_price += 1
                    continue

                passed.append(stock)

            except Exception:
                # Python层异常（数据格式问题等），跳过此股票
                cnt_nodata += 1
                continue

        logger.info(
            f'[漏斗2] 输入:{len(stock_list)}只 '
            f'→ 无数据:{cnt_nodata} 量不足:{cnt_volume} 价格越界:{cnt_price} '
            f'→ 通过: {len(passed)}只'
        )
        return passed

    # ── 漏斗3: MA多头排列（可选） ─────────────────────────────────────────────

    def _funnel3_ma_trend(self, stock_list: list[str]) -> list[str]:
        """
        MA5 > MA10 > MA20 多头排列过滤。
        右侧追涨策略时开启，左侧埋伏策略不需要。
        """
        try:
            from xtquant import xtdata
        except ImportError:
            logger.warning('[漏斗3] xtquant未安装，跳过MA过滤')
            return stock_list

        end_date   = self.target_date
        end_dt     = datetime.strptime(self.target_date, '%Y%m%d')
        start_date = (end_dt - timedelta(days=60)).strftime('%Y%m%d')

        passed    = []
        cnt_fail  = 0
        cnt_nodata= 0

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
                ma5  = closes[-5:].mean()
                ma10 = closes[-10:].mean()
                ma20 = closes[-20:].mean()

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
        """返回最近一次 build() 的统计信息。"""
        return self._stats


# ── 便捷函数 ──────────────────────────────────────────────────────────────────

def build_universe(
    target_date: str,
    min_avg_volume:   float = 3_000_000,
    min_price:        float = 3.0,
    max_price:        float = 300.0,
    require_ma_uptrend: bool = False,
) -> list[str]:
    """
    一行调用构建候选股票池。

    Example:
        candidates = build_universe('20260228')
    """
    return UniverseBuilder(
        target_date=target_date,
        min_avg_volume=min_avg_volume,
        min_price=min_price,
        max_price=max_price,
        require_ma_uptrend=require_ma_uptrend,
    ).build()


# ── 测试入口 ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=' * 60)
    print('UniverseBuilder 三漏斗测试')
    print('前提: 已运行 python tools/find_bson_bomb.py 生成黑名单')
    print('=' * 60)
    result = build_universe('20260228', require_ma_uptrend=False)
    print(f'\n最终候选: {len(result)} 只')
    print(f'前10只: {result[:10]}')
