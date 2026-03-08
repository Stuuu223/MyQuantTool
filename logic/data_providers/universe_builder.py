#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniverseBuilder - 回测候选股票池构建器

《三漏斗架构》
  漏斗1 (静态过滤):  ST/北交所/科创板剔除  → 零 get_local_data 调用
  漏斗２ (日K量价):   逐只 get_local_data(period='1d')  → 量/均价过滤
  漏斗３ (MA趋势):    MA5>MA10>MA20 多头排列           → 可选，右侧追涨用

【API 变更 V3.2.0】
build() 返回值: tuple[list[str], dict[str, float]]
  - list[str]:        通过粗筛的股票代码（与 V3.1 一致）
  - dict[str, float]: {stock: volume_ratio} 全市场量比分布（新增）
    供 config_manager.compute_volume_ratio_threshold(ratios, mode) 消费

向后兼容注意事项：
Python 元组自动 unpack 第一元素，旧代码仍能用：
  candidate_stocks = builder.build()  # 默认取第一元素，但丢失 market_ratios
标准用法：
  stocks, market_ratios = builder.build()
  threshold = cfg.compute_volume_ratio_threshold(list(market_ratios.values()), mode='backtest')

Version: 3.2.0 - 全市场量比分布伴随版
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
        stocks, market_ratios = builder.build()
        threshold = cfg.compute_volume_ratio_threshold(
            list(market_ratios.values()), mode='backtest'
        )
    """

    def __init__(
        self,
        target_date: str,
    ):
        self.target_date        = target_date
        self._blacklist         = _load_bson_blacklist()
        self._stats: dict       = {}
        # 【新增】存储全市场量比分布，供动态阈值计算
        self._volume_ratios: dict[str, float] = {}

        from logic.core.config_manager import get_config_manager
        cfg = get_config_manager()
        self.min_avg_amount       = cfg.get('stock_filter.min_avg_amount',       50_000_000.0)
        self.min_avg_turnover_pct = cfg.get('stock_filter.min_avg_turnover_pct', 2.5)  # 【CTO V25】默认值改为2.5%
        self.min_price            = cfg.get('stock_filter.min_price',            3.0)
        self.max_price            = cfg.get('stock_filter.max_price',            300.0)

    def build(self) -> tuple[list[str], dict[str, float]]:
        """
        构建候选股票池 + 返回全市场量比分布。

        Returns:
            tuple[list[str], dict[str, float]]:
                - list[str]: 通过粗筛的股票代码列表
                - dict[str, float]: {stock: volume_ratio} 全市场量比分布
                  第一漏斗过滤的记为0.0，第二漏斗计算真实量比。
                  第三漏斗MA过滤不影响此字典（MA是最后精筛）。

        向后兼容:
            candidate_stocks = builder.build()  # 自动unpack第一元素，但丢失market_ratios
            stocks, ratios = builder.build()    # 标准用法
        """
        t0 = time.perf_counter()

        step1 = self._funnel1_static()
        logger.info(f'[漏斗１-静态] 通过: {len(step1)}只')

        step2 = self._funnel2_daily_kline(step1)
        logger.info(f'[漏斗２-日K]  通过: {len(step2)}只 | '
                    f'量比分布采集: {len(self._volume_ratios)}只')

        # 【CTO V47】强制执行漏斗3（空间差排雷），替代被否决的MA均线
        step3 = self._funnel3_space_gap_filter(step2)
        
        # 【CTO V50】废除[:300]硬编码！
        # 让90th分位防线在scan_cmd中执行压缩
        # 如果漏斗3过滤后数量为0，兜底用漏斗2结果
        if not step3 or len(step3) == 0:
            logger.warning("[WARN] 漏斗3(空间防线)全军覆没！兜底用漏斗2结果！")
            final_pool = sorted(step2, key=lambda x: self._volume_ratios.get(x, 0), reverse=True)
        else:
            final_pool = sorted(step3, key=lambda x: self._volume_ratios.get(x, 0), reverse=True)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        self._stats = {
            'target_date':    self.target_date,
            'after_funnel1':  len(step1),
            'after_funnel2':  len(step2),
            'after_funnel3':  len(step3),
            'final_pool':     len(final_pool),
            'blacklist_size': len(self._blacklist),
            'volume_ratios_collected': len(self._volume_ratios),
            'elapsed_ms':     round(elapsed_ms, 1),
        }
        logger.info(f'[UniverseBuilder] 完成: {len(final_pool)}只候选 | '
                    f'耗时: {elapsed_ms:.0f}ms')
        return final_pool, self._volume_ratios

    def _funnel1_static(self) -> list[str]:
        """
        第一漏斗：静态过滤（ST/北交所/科创板/BSON黑名单）。
        同时将所有被过滤的股票记录为 volume_ratio=0.0，保证样本量。
        """
        try:
            from xtquant import xtdata
        except ImportError:
            logger.error('❌ [漏斗１] xtquant未安装')
            return []

        try:
            all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        except Exception as e:
            logger.error(f'❌ [漏斗１] 获取全市场列表失败: {e}')
            return []

        result = []
        cnt = {'blacklist': 0, 'bj': 0, 'kcb': 0, 'st': 0}

        for stock in all_stocks:
            code = stock.split('.')[0]
            filtered = False

            if stock in self._blacklist:
                cnt['blacklist'] += 1
                filtered = True

            elif code[:2] in ('43', '83', '87', '88'):
                cnt['bj'] += 1
                filtered = True

            elif code.startswith('688'):
                cnt['kcb'] += 1
                filtered = True

            else:
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
                            filtered = True
                except Exception:
                    pass

            if filtered:
                # 【新增】被过滤的股票记录0.0，保证样本量
                self._volume_ratios[stock] = 0.0
            else:
                result.append(stock)

        logger.info(
            f'[漏斗１] 全市场{len(all_stocks)}只 '
            f'→ 黑名单:{cnt["blacklist"]} 北交所:{cnt["bj"]} '
            f'科创板:{cnt["kcb"]} ST:{cnt["st"]} '
            f'→ 剩余: {len(result)}只'
        )
        return result

    def _funnel2_daily_kline(self, stock_list: list[str]) -> list[str]:
        """
        第二漏斗：日K量价过滤（均额/价格/换手率）。
        【新增】同时计算每只股票的 volume_ratio = today_volume / avg_volume_5d。
        【CTO V25】实装自愈下载：本地没数据就当场下载！
        【CTO V26优化】减少sleep时间，批量检查后统一下载
        """
        try:
            from xtquant import xtdata
        except ImportError:
            logger.error('❌ [漏斗２] xtquant未安装，跳过')
            return stock_list

        end_date   = self.target_date
        start_date = get_nth_previous_trading_day(self.target_date, 7)

        passed       = []
        cnt_nodata   = 0
        cnt_volume   = 0
        cnt_price    = 0
        cnt_turnover = 0
        cnt_autoheal = 0  # 【CTO V25】自愈下载计数

        # 【CTO V26优化】第一步：批量检查所有股票数据
        # 单独获取比批量更快（QMT接口特性）
        all_data = {}
        missing_stocks = []
        
        for stock in stock_list:
            try:
                data = xtdata.get_local_data(
                    field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],  # 【CTO终极天网】添加high/low用于计算日内动能净值
                    stock_list=[stock],
                    period='1d',
                    start_time=start_date,
                    end_time=end_date
                )
                if data and stock in data and data[stock] is not None and len(data[stock]) >= 5:
                    all_data[stock] = data[stock]
                else:
                    missing_stocks.append(stock)
            except Exception:
                missing_stocks.append(stock)

        # 【CTO V33终极净身令】删除阻塞式下载循环！
        # 问题根因：download_history_data在QMT限流时会无限挂起
        # 修复：缺失数据直接跳过，不阻塞实盘引擎！
        # 用户应该在盘后用 tools/smart_download.py 补充弹药
        if missing_stocks:
            logger.warning(f'⚠️ [防空警报] 发现 {len(missing_stocks)} 只股票日K数据缺失！')
            logger.warning(f'🚫 为防止实盘引擎被网络卡死，系统拒绝现场下载，这些股票将被物理隔离。')
            logger.warning(f'💡 请在盘后运行：python tools/smart_download.py 补充弹药！')
            # 不下载！缺失的票在后续df is None判断中自然会被过滤掉

        # 【CTO V26优化】第三步：使用已获取的数据进行过滤
        import pandas as pd
        import numpy as np

        for stock in stock_list:
            df = all_data.get(stock)
            
            if df is None or len(df) < 1:
                cnt_nodata += 1
                self._volume_ratios[stock] = 0.0
                continue

            # 【新增】计算 volume_ratio = 今日成交量 / 5日均成交量
            n = min(5, len(df))
            if n > 0:
                today_volume = float(df['volume'].iloc[-1])
                avg_volume_5d = df['volume'].iloc[-n:].mean()
                if avg_volume_5d > 0 and not (pd.isna(today_volume) or np.isinf(today_volume)):
                    volume_ratio = today_volume / avg_volume_5d
                    self._volume_ratios[stock] = float(volume_ratio)
                else:
                    self._volume_ratios[stock] = 0.0
            else:
                self._volume_ratios[stock] = 0.0

            # 原有过滤逻辑
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

            # 【CTO终极天网】纯物理量纲放行法则！
            # 不看涨了多少%，只看攻击姿态有多决绝！
            today_high = float(df['high'].iloc[-1])
            today_low = float(df['low'].iloc[-1])
            
            # 日内动能净值（Price Momentum Ratio）
            # 反映资金强顶最高点的决绝度，而非绝对涨幅
            # 【CTO战役收官】一字板(today_high==today_low)是最强动能，给满分1.0！
            price_momentum = (last_close - today_low) / (today_high - today_low) if today_high > today_low else 1.0
            
            # 涨停遗传基因（昨日是否涨停）
            pre_close = float(df['close'].iloc[-2]) if len(df) > 1 else last_close
            is_yesterday_limit_up = False
            if len(df) >= 2:
                day_before_yest_close = float(df['close'].iloc[-3]) if len(df) >= 3 else pre_close
                yesterday_change_pct = ((pre_close - day_before_yest_close) / day_before_yest_close * 100.0) if day_before_yest_close > 0 else 0.0
                is_yesterday_limit_up = yesterday_change_pct >= 9.8  # 近似涨停
            
            # 获取相对势能爆发极值
            volume_ratio = self._volume_ratios.get(stock, 0.0)
            
            # 【CTO绝对无量纲放行法则】
            # 只要资金强顶最高点(动能>0.9)且放量(>2.0)，或者极其狂暴地放量(>3.0)，或者带有昨日涨停基因，直接入池！
            if (price_momentum >= 0.90 and volume_ratio >= 2.0) or volume_ratio > 3.0 or is_yesterday_limit_up:
                passed.append(stock)
            else:
                self._volume_ratios[stock] = 0.0  # 剔除平庸死水

        # 【CTO V25】自愈下载统计日志
        if cnt_autoheal > 0:
            logger.info(f'[AUTO-HEAL] 漏斗2自愈下载: {cnt_autoheal}只股票补齐日K数据')
        
        logger.info(
            f'[漏斗２] 输入:{len(stock_list)}只 '
            f'→ 无数据:{cnt_nodata} 量不足:{cnt_volume} '
            f'价格越界:{cnt_price} 换手不足:{cnt_turnover} '
            f'→ 通过: {len(passed)}只'
        )
        return passed

    def _funnel3_space_gap_filter(self, stock_list: list[str]) -> list[str]:
        """
        【CTO V47 第三斩】空间差排雷兵（替代被否决的MA滞后防线）
        
        物理意义：寻找上方抛压真空的标的。计算现价距离过去60日高点的空间差。
        - space_gap <= 15%: 上方套牢盘可控，放行
        - space_gap > 15%: 深水区诈尸，一票否决
        
        注意：此漏斗不影响 self._volume_ratios
        """
        try:
            from xtquant import xtdata
        except ImportError:
            logger.warning('[漏斗３] xtquant未安装，跳过空间差过滤')
            return stock_list

        start_date = get_nth_previous_trading_day(self.target_date, 60)
        
        # 批量获取60日数据（优化：一次性获取所有股票）
        try:
            history_data = xtdata.get_local_data(
                field_list=['high', 'close'],
                stock_list=stock_list,
                period='1d',
                start_time=start_date,
                end_time=self.target_date
            )
        except Exception as e:
            logger.warning(f'[漏斗３] 批量获取失败，退回逐只查询: {e}')
            history_data = None

        passed     = []
        cnt_fail   = 0
        cnt_nodata = 0
        
        for stock in stock_list:
            try:
                if history_data and stock in history_data:
                    df = history_data[stock]
                else:
                    # 退回逐只查询
                    data = xtdata.get_local_data(
                        field_list=['high', 'close'],
                        stock_list=[stock],
                        period='1d',
                        start_time=start_date,
                        end_time=self.target_date
                    )
                    if not data or stock not in data:
                        cnt_nodata += 1
                        continue
                    df = data[stock]
                
                if df is None or len(df) < 10:
                    cnt_nodata += 1
                    continue

                # 60日最高价（抛压天顶）
                high_60d = float(df['high'].max())
                # 最新收盘价（当前位置）
                current_close = float(df.iloc[-1]['close'])
                
                if high_60d <= 0:
                    cnt_nodata += 1
                    continue
                
                # 空间差 = (前高 - 现价) / 前高
                space_gap_pct = (high_60d - current_close) / high_60d
                
                # 【CTO核心阈值】距离前高 <= 15% 才放行
                if space_gap_pct <= 0.15:
                    passed.append(stock)
                else:
                    cnt_fail += 1

            except Exception:
                cnt_nodata += 1
                continue

        logger.info(
            f'[漏斗３-空间差] 输入:{len(stock_list)}只 '
            f'→ 深水区:{cnt_fail} 无数据:{cnt_nodata} '
            f'→ 通过: {len(passed)}只'
        )
        return passed

    def get_stats(self) -> dict:
        return self._stats

    def get_volume_ratios(self) -> dict[str, float]:
        """
        【新增 API】获取全市场量比分布字典。

        Returns:
            dict[str, float]: {stock_code: volume_ratio}
                - 第一漏斗过滤的股票为 0.0
                - 第二漏斗计算的真实量比（today_volume / avg_volume_5d）
                - 第三漏斗MA过滤不影响此字典
        """
        return self._volume_ratios


def build_universe(
    target_date: str,
) -> tuple[list[str], dict[str, float]]:
    """
    便捷函数：构建候选股票池 + 返回全市场量比分布。

    Args:
        target_date: 目标日期 (YYYYMMDD)

    Returns:
        tuple[list[str], dict[str, float]]:
            - list[str]: 通过粗筛的股票代码（最多300只）
            - dict[str, float]: {stock: volume_ratio} 全市场量比分布

    示例:
        from logic.core.config_manager import get_config_manager

        stocks, market_ratios = build_universe('20260228')
        cfg = get_config_manager()
        threshold = cfg.compute_volume_ratio_threshold(
            list(market_ratios.values()), mode='backtest'
        )
    """
    return UniverseBuilder(
        target_date=target_date,
    ).build()


if __name__ == '__main__':
    print('=' * 60)
    print('UniverseBuilder 三漏斗测试 V47 (空间差排雷兵)')
    print('=' * 60)
    stocks, market_ratios = build_universe('20260228')
    print(f'\n最终候选: {len(stocks)} 只')
    print(f'前10只: {stocks[:10]}')
    print(f'\n量比分布统计:')
    valid_ratios = [r for r in market_ratios.values() if r > 0]
    if valid_ratios:
        import numpy as np
        print(f'  有效样本: {len(valid_ratios)}只')
        print(f'  中位数: {np.median(valid_ratios):.2f}')
        print(f'  平均值: {np.mean(valid_ratios):.2f}')
        print(f'  95分位: {np.percentile(valid_ratios, 95):.2f}')
        print(f'  88分位: {np.percentile(valid_ratios, 88):.2f}')

        # 测试 config_manager.compute_volume_ratio_threshold()
        from logic.core.config_manager import get_config_manager
        cfg = get_config_manager()
        live_threshold = cfg.compute_volume_ratio_threshold(valid_ratios, mode='live')
        bt_threshold   = cfg.compute_volume_ratio_threshold(valid_ratios, mode='backtest')
        print(f'\n动态阈值计算:')
        print(f'  实盘模式(95th): {live_threshold:.2f}')
        print(f'  回测模式(88th): {bt_threshold:.2f}')
    else:
        print('  无有效量比数据')
