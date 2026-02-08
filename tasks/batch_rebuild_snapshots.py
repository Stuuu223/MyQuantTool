#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量重建历史快照 - 基于Tushare日线 + eastmoney/Tushare资金流
"""

import sys
import os
from datetime import datetime, timedelta
import json

sys.path.append('E:/MyQuantTool')

import tushare as ts


class SnapshotRebuilder:
    """历史快照重建器"""

    def __init__(self, tushare_token: str, output_dir: str):
        self.tushare_token = tushare_token
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # 初始化Tushare
        self.ts_api = ts.pro_api(tushare_token)

    def get_trade_dates(self, start_date: str, end_date: str) -> list:
        """
        获取交易日历

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            交易日列表
        """
        try:
            df = self.ts_api.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date)
            trade_dates = df[df['is_open'] == 1]['cal_date'].tolist()
            return trade_dates
        except Exception as e:
            print(f"❌ 获取交易日历失败: {e}")
            return []

    def get_stock_list(self) -> list:
        """
        获取股票列表

        Returns:
            股票代码列表
        """
        try:
            # 获取所有A股股票
            df = self.ts_api.stock_basic(exchange='', list_status='L',
                                         fields='ts_code,symbol,name,area,industry,list_date')
            stock_list = df['ts_code'].tolist()
            print(f"✅ 获取到 {len(stock_list)} 只股票")
            return stock_list
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            return []

    def get_daily_data(self, trade_date: str, stock_list: list) -> dict:
        """
        获取日线数据

        Args:
            trade_date: 交易日期
            stock_list: 股票列表

        Returns:
            股票日线数据字典 {ts_code: price_data}
        """
        try:
            # 批量获取日线数据
            df = self.ts_api.daily(trade_date=trade_date)

            if df is None or len(df) == 0:
                print(f"⚠️ {trade_date} 无日线数据")
                return {}

            daily_data = {}
            for _, row in df.iterrows():
                ts_code = row['ts_code']
                daily_data[ts_code] = {
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'pre_close': row['pre_close'],
                    'change': row['change'],
                    'pct_chg': row['pct_chg'],
                    'volume': row['vol'],
                    'amount': row['amount'] * 1000  # Tushare的amount单位是千元，转换为元
                }

            print(f"✅ {trade_date} 获取到 {len(daily_data)} 只股票日线数据")
            return daily_data

        except Exception as e:
            print(f"❌ 获取日线数据失败: {e}")
            return {}

    def get_moneyflow_data(self, trade_date: str, stock_list: list) -> dict:
        """
        获取资金流数据（使用Tushare moneyflow）

        Args:
            trade_date: 交易日期
            stock_list: 股票列表

        Returns:
            资金流数据字典 {ts_code: flow_data}
        """
        flow_data = {}

        try:
            # 获取当天所有股票的资金流数据
            df = self.ts_api.moneyflow(trade_date=trade_date)

            if df is not None and len(df) > 0:
                for _, row in df.iterrows():
                    ts_code = row['ts_code']

                    # 计算主力净流入（超大单 + 大单）
                    # Tushare moneyflow的amount字段单位是千元
                    main_net_inflow = row['buy_elg_amount'] - row['sell_elg_amount']  # 超大单
                    main_net_inflow += row['buy_lg_amount'] - row['sell_lg_amount']   # 大单
                    main_net_inflow *= 1000  # 转换为元

                    # 计算散户净流入（中单 + 小单）
                    retail_net_inflow = row['buy_md_amount'] - row['sell_md_amount']  # 中单
                    retail_net_inflow += row['buy_sm_amount'] - row['sell_sm_amount']  # 小单
                    retail_net_inflow *= 1000  # 转换为元

                    flow_data[ts_code] = {
                        'main_net_inflow': main_net_inflow,
                        'retail_net_inflow': retail_net_inflow,
                        'source': 'tushare'
                    }

            print(f"✅ {trade_date} 获取到 {len(flow_data)} 只股票资金流数据")

        except Exception as e:
            print(f"⚠️ {trade_date} 资金流数据获取失败: {e}")

        return flow_data

    def calculate_tech_factors(self, daily_data: dict, trade_date: str) -> dict:
        """
        计算技术因子（简化版）

        Args:
            daily_data: 日线数据
            trade_date: 交易日期

        Returns:
            技术因子字典 {ts_code: tech_factors}
        """
        tech_factors = {}

        # 简化版：只计算基础因子
        for ts_code, price_data in daily_data.items():
            try:
                pct_chg = price_data['pct_chg']

                # 简化版技术因子（没有历史数据，无法计算MA等）
                factors = {
                    'pct_chg_1d': pct_chg / 100,  # 当日涨跌幅
                    'pct_chg_3d': pct_chg / 100,  # 简化：用当日涨跌幅
                    'ma5': price_data['close'],   # 简化：用收盘价
                    'ma10': price_data['close'],  # 简化：用收盘价
                }

                tech_factors[ts_code] = factors
            except Exception as e:
                continue

        return tech_factors

    def rebuild_snapshot(self, trade_date: str, stock_list: list) -> dict:
        """
        重建单个交易日的快照（集成 Gate 3.5 逻辑）

        Args:
            trade_date: 交易日期
            stock_list: 股票列表

        Returns:
            快照数据
        """
        print(f"\n{'=' * 60}")
        print(f"重建快照: {trade_date}")
        print(f"{'=' * 60}")

        # 获取日线数据
        daily_data = self.get_daily_data(trade_date, stock_list)
        if not daily_data:
            return None

        # 获取资金流数据
        flow_data = self.get_moneyflow_data(trade_date, stock_list)

        # 计算技术因子
        tech_factors = self.calculate_tech_factors(daily_data, trade_date)

        # 导入 Gate 3.5 组件
        from logic.trap_detector import TrapDetector
        from logic.capital_classifier import CapitalClassifier
        from logic.code_converter import CodeConverter

        trap_detector = TrapDetector()
        capital_classifier = CapitalClassifier()

        # 构建候选列表（先筛选涨幅>0且有资金流入的）
        candidates = []

        for ts_code, price_data in daily_data.items():
            pct_chg = price_data['pct_chg']
            flow = flow_data.get(ts_code, {'main_net_inflow': 0, 'source': 'none'})

            # 简单筛选：涨幅>0且有资金流入
            if pct_chg > 0 and flow['main_net_inflow'] > 0:
                candidates.append({
                    'code': ts_code,
                    'price_data': price_data,
                    'tech_factors': tech_factors.get(ts_code, {}),
                    'flow_data': flow
                })

        print(f"📊 候选股票: {len(candidates)} 只")

        # Gate 3.5 三漏斗筛选
        opportunities = []
        watchlist = []
        blacklist = []

        for idx, item in enumerate(candidates):
            ts_code = item['code']
            code_6digit = CodeConverter.to_akshare(ts_code)

            # 临时简化：只用基础规则，不调用诱多检测
            try:
                # 简化版：只根据资金流入强度分类
                flow = item.get('flow_data', {})
                main_net_inflow = flow.get('main_net_inflow', 0)
                price_data = item.get('price_data', {})
                daily_amount = price_data.get('amount', 0)

                # 计算主力净流入占当日成交额的比例
                inflow_to_amount = (main_net_inflow / daily_amount) if daily_amount > 0 else 0
                pct_chg = price_data.get('pct_chg', 0)

                # 根据涨幅和资金占比的组合来分类（momentum_band策略）
                # BAND_0: 噪声（<2%占比 或 涨幅<5%）
                # BAND_1: 保守小肉（5-8%涨幅 + 2-5%占比）
                # BAND_2: 半路推背（8-10%涨幅 + 2-5%占比）
                # BAND_3: 推背加强版（8-10%涨幅 + ≥5%占比）

                momentum_band = 'BAND_0'

                if inflow_to_amount < 0.02 or pct_chg < 5.0:
                    # < 2%占比 或 涨幅<5% → 噪声
                    decision_tag = 'BLACKLIST'
                    risk_score = 0.9
                    category = blacklist
                    momentum_band = 'BAND_0'

                elif 5.0 <= pct_chg < 8.0 and 0.02 <= inflow_to_amount < 0.05:
                    # 5-8%涨幅 + 2-5%占比 → 保守小肉
                    decision_tag = 'WATCHLIST'
                    risk_score = 0.4
                    category = watchlist
                    momentum_band = 'BAND_1'

                elif 8.0 <= pct_chg < 10.0 and 0.02 <= inflow_to_amount < 0.05:
                    # 8-10%涨幅 + 2-5%占比 → 半路推背（主战区）
                    decision_tag = 'OPPORTUNITY'
                    risk_score = 0.3
                    category = opportunities
                    momentum_band = 'BAND_2'

                elif 8.0 <= pct_chg < 10.0 and inflow_to_amount >= 0.05:
                    # 8-10%涨幅 + ≥5%占比 → 推背加强版
                    decision_tag = 'OPPORTUNITY'
                    risk_score = 0.2
                    category = opportunities
                    momentum_band = 'BAND_3'

                elif inflow_to_amount >= 0.05:
                    # ≥5%占比但涨幅不符合上述条件 → 观察池
                    decision_tag = 'WATCHLIST'
                    risk_score = 0.5
                    category = watchlist
                    momentum_band = 'BAND_0'

                else:
                    # 其他情况 → 黑名单
                    decision_tag = 'BLACKLIST'
                    risk_score = 0.8
                    category = blacklist
                    momentum_band = 'BAND_0'

                # 构建股票数据
                stock_data = {
                    'code': ts_code,
                    'code_6digit': code_6digit,
                    'trade_date': trade_date,
                    'price_data': item['price_data'],
                    'tech_factors': item['tech_factors'],
                    'flow_data': item['flow_data'],
                    'decision_tag': decision_tag,
                    'risk_score': risk_score,
                    'trap_signals': [],  # 简化版：空列表
                    'capital_type': 'UNKNOWN',
                    'momentum_band': momentum_band  # 推背段位标签
                }

                category.append(stock_data)

                if (idx + 1) % 50 == 0:
                    print(f"  进度: {idx+1}/{len(candidates)}")

            except Exception as e:
                print(f"  ⚠️ {ts_code} 处理失败: {e}")
                continue

        print(f"✅ Gate 3.5 筛选完成:")
        print(f"  - 机会池: {len(opportunities)} 只")
        print(f"  - 观察池: {len(watchlist)} 只")
        print(f"  - 黑名单: {len(blacklist)} 只")

        # 构建快照
        snapshot = {
            'scan_time': f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}T10:00:00",
            'mode': 'rebuild',
            'trade_date': trade_date,
            'summary': {
                'total_stocks': len(daily_data),
                'success_count': len(daily_data),
                'failed_count': 0
            },
            'results': {
                'opportunities': opportunities,
                'watchlist': watchlist,
                'blacklist': blacklist
            }
        }

        return snapshot

    def save_snapshot(self, snapshot: dict, trade_date: str):
        """
        保存快照

        Args:
            snapshot: 快照数据
            trade_date: 交易日期
        """
        filename = f"full_market_snapshot_{trade_date}_rebuild.json"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        print(f"✅ 快照已保存: {filename}")

    def batch_rebuild(self, start_date: str, end_date: str, max_stocks: int = 100):
        """
        批量重建历史快照

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            max_stocks: 最大股票数（用于测试）
        """
        print("=" * 60)
        print("批量重建历史快照")
        print("=" * 60)
        print(f"时间范围: {start_date} ~ {end_date}")
        print(f"最大股票数: {max_stocks}")
        print(f"输出目录: {self.output_dir}")
        print("=" * 60)

        # 获取交易日历
        trade_dates = self.get_trade_dates(start_date, end_date)
        if not trade_dates:
            print("❌ 无交易日数据")
            return

        print(f"✅ 共 {len(trade_dates)} 个交易日")

        # 获取股票列表
        stock_list = self.get_stock_list()
        if not stock_list:
            print("❌ 无股票数据")
            return

        # 限制股票数量（用于测试）
        if max_stocks > 0:
            stock_list = stock_list[:max_stocks]

        # 批量重建
        success_count = 0
        failed_count = 0

        for i, trade_date in enumerate(trade_dates):
            print(f"\n进度: {i + 1}/{len(trade_dates)}")

            try:
                # 重建快照
                snapshot = self.rebuild_snapshot(trade_date, stock_list)

                if snapshot:
                    # 保存快照
                    self.save_snapshot(snapshot, trade_date)
                    success_count += 1
                else:
                    print(f"❌ {trade_date} 快照重建失败")
                    failed_count += 1

            except Exception as e:
                print(f"❌ {trade_date} 重建失败: {e}")
                import traceback
                traceback.print_exc()
                failed_count += 1

        # 输出汇总
        print("\n" + "=" * 60)
        print("批量重建完成")
        print("=" * 60)
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")
        print(f"成功率: {success_count / (success_count + failed_count) * 100:.2f}%")
        print("=" * 60)


def main():
    """主函数"""
    # 配置
    TUSHARE_TOKEN = '1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b'
    OUTPUT_DIR = 'E:/MyQuantTool/data/rebuild_snapshots'

    # 创建重建器
    rebuilder = SnapshotRebuilder(TUSHARE_TOKEN, OUTPUT_DIR)

    # 生成21天快照（简化版 Gate 3.5）
    rebuilder.batch_rebuild(start_date='20260109', end_date='20260208', max_stocks=0)  # 0表示不限制


if __name__ == '__main__':
    main()