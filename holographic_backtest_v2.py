#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全息回演引擎 V2 - 优化版（支持缓存和断点续传）

执行流程：
1. Tushare粗筛（5000→~500）
2. 成交额过滤（~500→~100）
3. 量比筛选（~100→Top 20）
4. V18验钞机精算

Author: AI量化工程师
Date: 2026-02-23
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
import json
import time

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.core.metric_definitions import MetricDefinitions
from logic.core.sanity_guards import SanityGuards
from logic.core.path_resolver import PathResolver
from logic.utils.price_utils import get_pre_close, calc_true_change
from logic.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from xtquant import xtdata
    HAS_QMT = True
except ImportError:
    HAS_QMT = False

try:
    import tushare as ts
    HAS_TUSHARE = True
except ImportError:
    HAS_TUSHARE = False

# Tushare Token
TUSHARE_TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"


class HolographicBacktestEngine:
    """全息回演引擎 V2"""
    
    def __init__(self, date: str, cache_dir: Optional[str] = None):
        self.date = date
        self.date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        
        # 初始化Tushare
        self.pro = None
        if HAS_TUSHARE:
            ts.set_token(TUSHARE_TOKEN)
            self.pro = ts.pro_api()
        
        # 初始化路径
        PathResolver.initialize()
        self.output_dir = PathResolver.get_data_dir() / "backtest_out"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 缓存目录
        self.cache_dir = Path(cache_dir) if cache_dir else PathResolver.get_data_dir() / "cache" / "holographic"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 结果存储
        self.layer1_stocks: List[Dict] = []
        self.layer2_stocks: List[Dict] = []
        self.layer3_stocks: List[Dict] = []
        self.final_top10: List[Dict] = []
        
        logger.info(f"全息回演引擎初始化: {date}")
    
    def _get_cache_file(self, layer: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{self.date}_{layer}.json"
    
    def _load_cache(self, layer: str) -> Optional[List[Dict]]:
        """从缓存加载数据"""
        cache_file = self._get_cache_file(layer)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"从缓存加载 {layer}: {len(data)} 条")
                return data
            except Exception as e:
                logger.warning(f"缓存加载失败: {e}")
        return None
    
    def _save_cache(self, layer: str, data: List[Dict]):
        """保存数据到缓存"""
        cache_file = self._get_cache_file(layer)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"缓存已保存 {layer}: {len(data)} 条")
    
    def layer1_tushare_coarse_filter(self, use_cache: bool = True) -> List[Dict]:
        """第一层：Tushare粗筛"""
        logger.info("=" * 60)
        logger.info("第一层：Tushare粗筛")
        logger.info("=" * 60)
        
        # 尝试从缓存加载
        if use_cache:
            cached = self._load_cache('layer1')
            if cached:
                self.layer1_stocks = cached
                return cached
        
        if not self.pro:
            logger.error("Tushare未初始化")
            return []
        
        try:
            # 获取全市场股票列表
            df_basic = self.pro.stock_basic(exchange='', list_status='L', 
                                            fields='ts_code,name,industry,market')
            logger.info(f"全市场股票总数: {len(df_basic)}")
            
            # 过滤北交所和ST
            df_basic = df_basic[~df_basic['ts_code'].str.startswith(('8', '4'))]
            df_basic = df_basic[~df_basic['name'].str.contains('ST', na=False)]
            logger.info(f"过滤北交所和ST后: {len(df_basic)}")
            
            # 获取当日行情数据
            df_daily = self.pro.daily(trade_date=self.date)
            
            if df_daily is None or df_daily.empty:
                logger.error(f"获取{self.date}日行情数据失败")
                return []
            
            # 合并数据
            df_merged = df_basic.merge(df_daily, on='ts_code', how='inner')
            df_merged = df_merged[df_merged['vol'] > 0]
            
            # 转换为列表
            stocks = []
            for _, row in df_merged.iterrows():
                stock = {
                    'ts_code': row['ts_code'],
                    'code': row['ts_code'].split('.')[0],
                    'name': row['name'],
                    'industry': row.get('industry', ''),
                    'market': row.get('market', ''),
                    'close': float(row['close']),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'vol': float(row['vol']),
                    'amount': float(row['amount']),
                    'pre_close': float(row['pre_close']),
                }
                stocks.append(stock)
            
            self.layer1_stocks = stocks
            self._save_cache('layer1', stocks)
            logger.info(f"第一层筛选完成: {len(stocks)} 只股票")
            return stocks
            
        except Exception as e:
            logger.error(f"第一层筛选失败: {e}", exc_info=True)
            return []
    
    def layer2_amount_filter(self, min_avg_amount: float = 3000, use_cache: bool = True) -> List[Dict]:
        """第二层：成交额过滤"""
        logger.info("=" * 60)
        logger.info(f"第二层：成交额过滤 > {min_avg_amount}万")
        logger.info("=" * 60)
        
        if use_cache and not self.layer1_stocks:
            cached = self._load_cache('layer2')
            if cached:
                self.layer2_stocks = cached
                return cached
        
        if not self.pro:
            return []
        
        try:
            # 获取前5个交易日
            end_date = datetime.strptime(self.date, "%Y%m%d")
            start_date = end_date - timedelta(days=30)
            start_date_str = start_date.strftime("%Y%m%d")
            
            df_trade_cal = self.pro.trade_cal(start_date=start_date_str, end_date=self.date)
            trade_days = df_trade_cal[df_trade_cal['is_open'] == 1]['cal_date'].tolist()
            
            if len(trade_days) < 6:
                logger.error(f"交易日数据不足: {len(trade_days)}天")
                return []
            
            prev_5_days = trade_days[-6:-1]
            logger.info(f"前5个交易日: {prev_5_days}")
            
            filtered_stocks = []
            
            for i, stock in enumerate(self.layer1_stocks):
                try:
                    ts_code = stock['ts_code']
                    
                    # 获取5日行情
                    df_5d = self.pro.daily(ts_code=ts_code, start_date=prev_5_days[0], 
                                           end_date=prev_5_days[-1])
                    
                    if df_5d is None or df_5d.empty or len(df_5d) < 3:
                        continue
                    
                    avg_amount = df_5d['amount'].mean()
                    
                    if avg_amount >= min_avg_amount:
                        stock['avg_amount_5d'] = float(avg_amount)
                        stock['avg_vol_5d'] = float(df_5d['vol'].mean())
                        filtered_stocks.append(stock)
                    
                    # 每10只打印一次进度
                    if (i + 1) % 100 == 0:
                        logger.info(f"  已处理 {i+1}/{len(self.layer1_stocks)} 只")
                        
                except Exception as e:
                    continue
            
            self.layer2_stocks = filtered_stocks
            self._save_cache('layer2', filtered_stocks)
            logger.info(f"第二层筛选完成: {len(filtered_stocks)} 只股票")
            return filtered_stocks
            
        except Exception as e:
            logger.error(f"第二层筛选失败: {e}", exc_info=True)
            return []
    
    def layer3_volume_ratio_filter(self, min_volume_ratio: float = 3.0, top_n: int = 20, 
                                   use_cache: bool = True) -> List[Dict]:
        """第三层：量比筛选"""
        logger.info("=" * 60)
        logger.info(f"第三层：量比筛选 Top {top_n} > {min_volume_ratio}")
        logger.info("=" * 60)
        
        if use_cache and not self.layer2_stocks:
            cached = self._load_cache('layer3')
            if cached:
                self.layer3_stocks = cached
                return cached
        
        try:
            stocks_with_ratio = []
            
            for stock in self.layer2_stocks:
                try:
                    if 'avg_vol_5d' in stock and stock['avg_vol_5d'] > 0:
                        volume_ratio = stock['vol'] / stock['avg_vol_5d']
                        
                        if volume_ratio >= min_volume_ratio:
                            stock['volume_ratio'] = float(volume_ratio)
                            stocks_with_ratio.append(stock)
                except Exception as e:
                    continue
            
            # 按量比排序，取Top N
            stocks_sorted = sorted(stocks_with_ratio, key=lambda x: x['volume_ratio'], reverse=True)
            top_stocks = stocks_sorted[:top_n]
            
            self.layer3_stocks = top_stocks
            self._save_cache('layer3', top_stocks)
            
            logger.info(f"第三层筛选完成: {len(top_stocks)} 只股票")
            for i, s in enumerate(top_stocks, 1):
                logger.info(f"  {i}. {s['ts_code']} {s['name']} 量比={s['volume_ratio']:.2f}")
            
            return top_stocks
            
        except Exception as e:
            logger.error(f"第三层筛选失败: {e}", exc_info=True)
            return []
    
    def v18_precise_calculation(self) -> List[Dict]:
        """V18验钞机精算"""
        logger.info("=" * 60)
        logger.info("V18验钞机精算")
        logger.info("=" * 60)
        
        if not HAS_QMT:
            logger.error("QMT不可用")
            return []
        
        try:
            results = []
            
            for stock in self.layer3_stocks:
                try:
                    ts_code = stock['ts_code']
                    code = stock['code']
                    name = stock['name']
                    
                    # 标准化代码格式
                    if code.startswith('6'):
                        qmt_code = f"{code}.SH"
                    else:
                        qmt_code = f"{code}.SZ"
                    
                    logger.info(f"处理: {qmt_code} {name}")
                    
                    # 获取昨收价
                    try:
                        pre_close = get_pre_close(qmt_code, self.date)
                    except Exception as e:
                        logger.warning(f"获取昨收价失败 {qmt_code}: {e}")
                        continue
                    
                    # 下载Tick数据（09:30-09:45）
                    start_time = f"{self.date}093000"
                    end_time = f"{self.date}094500"
                    
                    xtdata.download_history_data(
                        stock_code=qmt_code,
                        period='tick',
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    ticks = xtdata.get_local_data(
                        field_list=['time', 'lastPrice', 'volume', 'amount'],
                        stock_code_list=[qmt_code],
                        period='tick',
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    if qmt_code not in ticks or ticks[qmt_code] is None or ticks[qmt_code].empty:
                        logger.warning(f"无Tick数据: {qmt_code}")
                        continue
                    
                    df_ticks = ticks[qmt_code]
                    
                    # 找到09:40的价格
                    target_time = f"{self.date}094000"
                    target_ts = datetime.strptime(target_time, "%Y%m%d%H%M%S").timestamp() * 1000
                    
                    df_ticks['time_diff'] = abs(df_ticks['time'] - target_ts)
                    nearest_idx = df_ticks['time_diff'].idxmin()
                    price_0940 = float(df_ticks.loc[nearest_idx, 'lastPrice'])
                    
                    # 获取开盘价
                    open_time = f"{self.date}093000"
                    open_ts = datetime.strptime(open_time, "%Y%m%d%H%M%S").timestamp() * 1000
                    df_ticks['open_diff'] = abs(df_ticks['time'] - open_ts)
                    open_idx = df_ticks['open_diff'].idxmin()
                    open_price = float(df_ticks.loc[open_idx, 'lastPrice'])
                    
                    # 计算真实涨幅（基于昨收价）
                    true_change_0940 = MetricDefinitions.TRUE_CHANGE(price_0940, pre_close)
                    
                    # 计算VWAP
                    df_morning = df_ticks[df_ticks['time'] <= target_ts]
                    vwap = price_0940
                    if len(df_morning) > 0:
                        vol_diff = df_morning['volume'].diff().fillna(0)
                        price_x_vol = df_morning['lastPrice'] * vol_diff
                        total_amount = price_x_vol.sum()
                        total_volume = vol_diff.sum()
                        if total_volume > 0:
                            vwap = float(total_amount / total_volume)
                    
                    # Sustain因子
                    time_0935 = f"{self.date}093500"
                    ts_0935 = datetime.strptime(time_0935, "%Y%m%d%H%M%S").timestamp() * 1000
                    df_sustain = df_ticks[(df_ticks['time'] >= ts_0935) & (df_ticks['time'] <= target_ts)]
                    
                    sustain_factor = 0.0
                    if len(df_sustain) > 0:
                        sustain_threshold = open_price * 0.98
                        sustain_count = len(df_sustain[df_sustain['lastPrice'] >= sustain_threshold])
                        sustain_factor = sustain_count / len(df_sustain) * 100
                    
                    # 资金占比
                    capital_share_pct = float(stock.get('amount', 0)) / 10000
                    
                    # 综合得分
                    volume_ratio = stock.get('volume_ratio', 1)
                    base_score = min(30, volume_ratio * 5)
                    multiplier = 1 + (true_change_0940 / 100)
                    final_score = base_score * multiplier * (sustain_factor / 100)
                    
                    result = {
                        'stock_code': qmt_code,
                        'name': name,
                        'pre_close': float(pre_close),
                        'open_price': float(open_price),
                        'price_0940': float(price_0940),
                        'true_change_0940': round(true_change_0940, 2),
                        'volume_ratio': round(volume_ratio, 2),
                        'vwap': round(vwap, 2),
                        'sustain_factor': round(sustain_factor, 2),
                        'capital_share_pct': round(capital_share_pct, 2),
                        'base_score': round(base_score, 2),
                        'multiplier': round(multiplier, 3),
                        'final_score': round(final_score, 2)
                    }
                    
                    results.append(result)
                    logger.info(f"  ✅ {qmt_code} 涨幅={true_change_0940:.2f}% VWAP={vwap:.2f} Sustain={sustain_factor:.1f}%")
                    
                except Exception as e:
                    logger.error(f"V18精算失败 {stock['ts_code']}: {e}")
                    continue
            
            # 按综合得分排序，取Top 10
            results_sorted = sorted(results, key=lambda x: x['final_score'], reverse=True)
            self.final_top10 = results_sorted[:10]
            
            # 保存完整结果到缓存
            self._save_cache('v18_full', results_sorted)
            
            logger.info(f"V18精算完成: {len(self.final_top10)} 只股票")
            return self.final_top10
            
        except Exception as e:
            logger.error(f"V18精算失败: {e}", exc_info=True)
            return []
    
    def find_zhitexincai_ranking(self) -> Dict:
        """查找志特新材排名"""
        target_code = "300986.SZ"
        
        # 加载完整V18结果
        cache_file = self._get_cache_file('v18_full')
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                all_results = json.load(f)
        else:
            all_results = self.final_top10
        
        for i, stock in enumerate(all_results, 1):
            if stock['stock_code'] == target_code:
                return {
                    'rank': i,
                    'in_top10': i <= 10,
                    'data': stock
                }
        
        return {'rank': -1, 'in_top10': False, 'data': None}
    
    def generate_report(self) -> Dict:
        """生成报告"""
        report = {
            'date': self.date,
            'layer1_count': len(self.layer1_stocks),
            'layer2_count': len(self.layer2_stocks),
            'layer3_count': len(self.layer3_stocks),
            'final_top10': [{'rank': i + 1, **stock} for i, stock in enumerate(self.final_top10)],
            'zhitexincai': self.find_zhitexincai_ranking()
        }
        return report
    
    def save_report(self, report: Dict) -> str:
        """保存报告"""
        output_file = self.output_dir / f"{self.date}_holographic_report.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"报告已保存: {output_file}")
        return str(output_file)
    
    def run_full_backtest(self) -> Dict:
        """执行完整回演"""
        logger.info(f"\n{'='*60}")
        logger.info(f"开始全息回演: {self.date}")
        logger.info(f"{'='*60}\n")
        
        # 四层筛选
        self.layer1_tushare_coarse_filter()
        self.layer2_amount_filter()
        self.layer3_volume_ratio_filter()
        self.v18_precise_calculation()
        
        # 生成并保存报告
        report = self.generate_report()
        self.save_report(report)
        self._print_summary(report)
        
        return report
    
    def _print_summary(self, report: Dict):
        """打印摘要"""
        logger.info(f"\n{'='*60}")
        logger.info("全息回演报告摘要")
        logger.info(f"{'='*60}")
        logger.info(f"日期: {report['date']}")
        logger.info(f"第一层(Tushare粗筛): {report['layer1_count']} 只")
        logger.info(f"第二层(成交额过滤): {report['layer2_count']} 只")
        logger.info(f"第三层(量比筛选): {report['layer3_count']} 只")
        
        logger.info("\nTop 10 排名:")
        for stock in report['final_top10']:
            logger.info(f"  {stock['rank']}. {stock['stock_code']} {stock['name']} "
                       f"涨幅={stock['true_change_0940']:.2f}% "
                       f"量比={stock['volume_ratio']:.2f} "
                       f"得分={stock['final_score']:.2f}")
        
        ztxc = report['zhitexincai']
        if ztxc['rank'] > 0:
            logger.info(f"\n志特新材(300986.SZ) 排名: {ztxc['rank']} "
                       f"({'在Top10内' if ztxc['in_top10'] else '不在Top10'})")
        else:
            logger.info("\n志特新材(300986.SZ) 未进入最终排名")
        
        logger.info(f"{'='*60}\n")


def run_single_date(date: str) -> Optional[Dict]:
    """执行单日回演"""
    try:
        engine = HolographicBacktestEngine(date)
        return engine.run_full_backtest()
    except Exception as e:
        logger.error(f"处理日期 {date} 失败: {e}", exc_info=True)
        return None


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='全息回演引擎')
    parser.add_argument('--date', type=str, help='日期 (YYYYMMDD)')
    parser.add_argument('--all', action='store_true', help='执行所有日期')
    args = parser.parse_args()
    
    if args.all:
        dates = ['20251231', '20260105']
        reports = {}
        for date in dates:
            reports[date] = run_single_date(date)
        
        # 对比排名
        if '20251231' in reports and '20260105' in reports:
            logger.info("\n" + "=" * 60)
            logger.info("志特新材排名对比")
            logger.info("=" * 60)
            rank_1231 = reports['20251231']['zhitexincai']['rank'] if reports['20251231'] else -1
            rank_0105 = reports['20260105']['zhitexincai']['rank'] if reports['20260105'] else -1
            logger.info(f"12月31日排名: {rank_1231 if rank_1231 > 0 else '未入榜'}")
            logger.info(f"1月5日排名: {rank_0105 if rank_0105 > 0 else '未入榜'}")
    
    elif args.date:
        run_single_date(args.date)
    
    else:
        # 默认执行12月31日
        run_single_date('20251231')


if __name__ == "__main__":
    main()
