#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
热门样本回测套件
按照CTO决策（docs/dev/CTO_DECISION_2026-02-18.md第5章）要求
所有核心策略或过滤改动必须先在此样本集上验证

V2.0: 集成资金事件标注

⚠️  DEMO / LEGACY（已废弃）
===============================================
【重要声明】本脚本使用硬编码模拟数据，不是真实tick回测

技术限制：
- 数据来源：硬编码模拟数据（如网宿科技2026-01-26的假K线）
- 资金流：未使用真实QmtTickCapitalFlowProvider（replay模式）
- 三漏斗：无真实tick数据，无法验证筛选逻辑

当前状态：
- 网宿科技：硬编码交易（2026-01-26买入，2026-01-27卖出）
- 顽主榜30只：0交易（无模拟数据，也无真实tick数据）

【决策】2026-02-19 CTO决策：
- ❌ 禁止使用此脚本进行任何验收
- ✅ 真实tick回测请走 backtest/run_v17_replay_suite.py（待创建）
- ✅ 或者走 V17 官方推荐：backtest/run_tick_replay_backtest.py（需验证）

【技术债】标记为DEMO/LEGACY，下一步：删除或迁移到V17架构
===============================================
"""

import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.strategies.backtest_engine import BacktestEngine
from logic.utils.capital_event_annotator import CapitalEventAnnotator


class HotCasesSuite:
    """热门样本回测套件（V2.0: 集成资金事件标注）"""

    def __init__(self):
        self.results = {}
        self.capital_annotator = CapitalEventAnnotator()
        self.suite_config = {
            'wangsu': {
                'code': '300017.SZ',
                'name': '网宿科技',
                'date_range': ['2026-01-15', '2026-02-13'],
                'description': '包含2026-01-26涨停日及前后窗口'
            },
            'wanzhu': {
                'codes': [],  # 从配置文件加载
                'date_range': ['2026-02-04', '2026-02-13'],
                'description': '顽主榜单真实窗口'
            },
            'classic': {
                'codes': [],  # 由老板指定
                'date_range': ['2026-01-01', '2026-02-13'],
                'description': '经典个股案例（志特新材、欢乐家、有友食品等）'
            }
        }

    def load_wanzhu_codes(self) -> List[str]:
        """加载顽主榜单代码（V3.0: 统一使用wanzhu_selected_150.csv）"""
        csv_path = PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv'
        if not csv_path.exists():
            print(f"⚠️  找不到顽主榜单: {csv_path}")
            return []

        df = pd.read_csv(csv_path)
        codes = df['code'].tolist()
        print(f"✅ 加载顽主榜单: {len(codes)} 只")
        return codes

    def run_single_stock_backtest(
        self,
        code: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000
    ) -> Dict[str, Any]:
        """
        运行单只股票回测（V2.0: 集成资金事件标注）

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金

        Returns:
            Dict: 回测结果
        """
        print(f"\n{'='*60}")
        print(f"📊 回测: {code}")
        print(f"📅 日期: {start_date} ~ {end_date}")
        print(f"{'='*60}")

        # 🔥 V2.0: 集成资金事件标注
        # 模拟数据：网宿1-26（2026-01-26）
        if code == '300017.SZ' and start_date <= '2026-01-26' <= end_date:
            # 构造市场数据
            import numpy as np
            np.random.seed(42)

            # ratio数据：97只股票 < 0.05，网宿0.05排在前3%
            all_ratios = [0.001 + i*0.0005 for i in range(97)] + [0.05] + [0.051 + i*0.001 for i in range(2)]

            # price_strength数据：90只股票 < 0.127，网宿0.127排在前10%
            all_price_strengths = [0.001 + i*0.0014 for i in range(90)] + [0.127] + [0.128 + i*0.008 for i in range(9)]

            # 标注资金事件
            capital_event = self.capital_annotator.annotate_capital_event(
                code=code,
                date='2026-01-26',
                ratio=0.05,
                price_strength=0.127,
                all_ratios=all_ratios,
                all_price_strengths=all_price_strengths,
                sector_ratio_percentile=0.995
            )

            print(f"\n💰 资金事件标注:")
            print(f"  ratio: {capital_event.ratio:.4f} (分位数: {capital_event.ratio_percentile:.4f})")
            print(f"  price_strength: {capital_event.price_strength:.4f} (分位数: {capital_event.price_percentile:.4f})")
            print(f"  is_attack: {capital_event.is_attack}")
            print(f"  attack_type: {capital_event.attack_type}")

            # 模拟交易（带有资金事件标签）
            trades = []
            if capital_event.is_attack:
                # 模拟TRIVIAL策略交易
                trades.append({
                    'date': '2026-01-26',
                    'code': code,
                    'action': 'BUY',
                    'price': 10.0,
                    'shares': 1000,
                    'amount': 10000.0,
                    'signal_score': 0.85,
                    'capital_event': {
                        'is_attack': capital_event.is_attack,
                        'attack_type': capital_event.attack_type,
                        'ratio': capital_event.ratio,
                        'ratio_percentile': capital_event.ratio_percentile,
                        'price_strength': capital_event.price_strength,
                        'price_percentile': capital_event.price_percentile
                    }
                })

                # 模拟第二天卖出
                trades.append({
                    'date': '2026-01-27',
                    'code': code,
                    'action': 'SELL',
                    'price': 10.8,
                    'shares': 1000,
                    'amount': 10800.0,
                    'profit': 800.0,
                    'profit_ratio': 8.0,
                    'capital_event': None
                })

            result = {
                'code': code,
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': initial_capital,
                'final_equity': initial_capital + 800.0 if trades else initial_capital,
                'total_return': 0.8 if trades else 0.0,
                'max_drawdown': 0.0,
                'total_trades': len(trades),
                'win_rate': 100.0 if trades else 0.0,
                'sharpe_ratio': 2.5 if trades else 0.0,
                'trades': trades,
                'capital_events': [capital_event.to_dict()] if capital_event.is_attack else []
            }
        else:
            # 其他股票使用模拟数据
            result = {
                'code': code,
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': initial_capital,
                'final_equity': initial_capital,
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'sharpe_ratio': 0.0,
                'trades': [],
                'capital_events': []
            }

        print(f"✅ 回测完成")
        return result

    def run_suite(self) -> Dict[str, Any]:
        """运行完整热门样本套件"""
        print(f"\n{'='*80}")
        print(f"🚀 开始热门样本回测套件")
        print(f"{'='*80}")

        suite_results = {
            'timestamp': datetime.now().isoformat(),
            'wangsu': None,
            'wanzhu': None,
            'classic': None,
            'summary': {}
        }

        # 1. 网宿科技回测
        print(f"\n【第一层：单票深挖】")
        wangsu_config = self.suite_config['wangsu']
        suite_results['wangsu'] = self.run_single_stock_backtest(
            code=wangsu_config['code'],
            start_date=wangsu_config['date_range'][0],
            end_date=wangsu_config['date_range'][1]
        )

        # 2. 顽主榜单回测（前30只）
        print(f"\n【第二层：榜单窗口】")
        wanzhu_codes = self.load_wanzhu_codes()
        if wanzhu_codes:
            # 先跑前30只
            sample_codes = wanzhu_codes[:30]
            print(f"📊 样本数: {len(sample_codes)} 只")

            wanzhu_results = []
            for code in sample_codes:
                result = self.run_single_stock_backtest(
                    code=code,
                    start_date=self.suite_config['wanzhu']['date_range'][0],
                    end_date=self.suite_config['wanzhu']['date_range'][1]
                )
                wanzhu_results.append(result)

            suite_results['wanzhu'] = {
                'total_count': len(sample_codes),
                'results': wanzhu_results,
                'summary': self._calculate_summary(wanzhu_results)
            }

        # 3. 经典个股回测
        print(f"\n【经典个股】")
        classic_codes = self.suite_config['classic']['codes']
        if classic_codes:
            classic_results = []
            for code in classic_codes:
                result = self.run_single_stock_backtest(
                    code=code,
                    start_date=self.suite_config['classic']['date_range'][0],
                    end_date=self.suite_config['classic']['date_range'][1]
                )
                classic_results.append(result)

            suite_results['classic'] = {
                'total_count': len(classic_codes),
                'results': classic_results,
                'summary': self._calculate_summary(classic_results)
            }

        # 4. 汇总统计
        suite_results['summary'] = self._calculate_suite_summary(suite_results)

        # 5. 保存结果
        self._save_results(suite_results)

        return suite_results

    def _calculate_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """计算回测结果汇总"""
        if not results:
            return {}

        total_trades = sum(r['total_trades'] for r in results)
        winning_trades = sum(
            r['total_trades'] * r['win_rate'] / 100
            for r in results
        )
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0

        return {
            'total_stocks': len(results),
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_return': sum(r['total_return'] for r in results) / len(results),
            'avg_max_drawdown': sum(r['max_drawdown'] for r in results) / len(results)
        }

    def _calculate_suite_summary(self, suite_results: Dict) -> Dict[str, Any]:
        """计算套件汇总统计"""
        summary = {
            'total_stocks': 0,
            'total_trades': 0,
            'avg_win_rate': 0,
            'avg_return': 0,
            'avg_max_drawdown': 0
        }

        # 汇总所有结果
        all_results = []
        if suite_results['wangsu']:
            all_results.append(suite_results['wangsu'])
        if suite_results['wanzhu']:
            all_results.extend(suite_results['wanzhu']['results'])
        if suite_results['classic']:
            all_results.extend(suite_results['classic']['results'])

        if all_results:
            summary.update(self._calculate_summary(all_results))

        return summary

    def _save_results(self, results: Dict):
        """保存回测结果"""
        output_dir = PROJECT_ROOT / 'backtest' / 'results'
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'hot_cases_suite_{timestamp}.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n{'='*80}")
        print(f"💾 结果已保存: {output_file}")
        print(f"{'='*80}")

        # 打印汇总
        self._print_summary(results)

    def _print_summary(self, results: Dict):
        """打印汇总统计（V2.0: 增加资金事件统计）"""
        summary = results.get('summary', {})

        print(f"\n📊 回测套件汇总:")
        print(f"  总股票数: {summary.get('total_stocks', 0)}")
        print(f"  总交易次数: {summary.get('total_trades', 0)}")
        print(f"  平均胜率: {summary.get('avg_win_rate', 0):.2f}%")
        print(f"  平均收益率: {summary.get('avg_return', 0):.2f}%")
        print(f"  平均最大回撤: {summary.get('avg_max_drawdown', 0):.2f}%")

        # 🔥 V2.0: 资金事件统计
        print(f"\n💰 资金事件统计:")
        capital_events_summary = self.capital_annotator.get_summary()
        print(f"  总资金事件数: {capital_events_summary.get('attack_count', 0)}")
        print(f"  资金事件触发率: {capital_events_summary.get('attack_rate', 0):.2f}%")

        attack_types = capital_events_summary.get('attack_types', {})
        print(f"  MARKET_TOP_3_PRICE_TOP_10: {attack_types.get('MARKET_TOP_3_PRICE_TOP_10', 0)}")
        print(f"  SECTOR_TOP_1_PRICE_TOP_10: {attack_types.get('SECTOR_TOP_1_PRICE_TOP_10', 0)}")

        # 📊 分析"资金事件触发但策略沉默"的情况
        self._analyze_capital_event_silence(results)

    def _analyze_capital_event_silence(self, results: Dict):
        """
        分析"资金事件触发但策略沉默"的情况

        Args:
            results: 回测结果
        """
        print(f"\n🚫 资金事件触发但策略沉默:")

        silence_dates = []

        # 获取所有资金事件
        all_capital_events = self.capital_annotator.get_attack_events()

        for event in all_capital_events:
            code = event.code
            date = event.date

            # 检查该日是否有交易
            has_trade = False
            if results.get('wangsu') and results['wangsu']['code'] == code:
                for trade in results['wangsu'].get('trades', []):
                    if trade['date'] == date:
                        has_trade = True
                        break
            elif results.get('wanzhu'):
                for wanzhu_result in results['wanzhu'].get('results', []):
                    if wanzhu_result['code'] == code:
                        for trade in wanzhu_result.get('trades', []):
                            if trade['date'] == date:
                                has_trade = True
                                break
                        break

            if not has_trade:
                silence_dates.append({
                    'code': code,
                    'date': date,
                    'attack_type': event.attack_type
                })

        if silence_dates:
            print(f"  发现 {len(silence_dates)} 次资金事件触发但策略沉默:")
            for silence in silence_dates:
                print(f"    {silence['date']} {silence['code']} ({silence['attack_type']})")
        else:
            print(f"  无（所有资金事件都有交易）")


def main():
    """主函数"""
    suite = HotCasesSuite()
    results = suite.run_suite()

    print(f"\n✅ 热门样本回测套件完成")


if __name__ == '__main__':
    main()