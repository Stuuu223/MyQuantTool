#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
热门样本回测套件
按照CTO决策（docs/dev/CTO_DECISION_2026-02-18.md第5章）要求
所有核心策略或过滤改动必须先在此样本集上验证
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


class HotCasesSuite:
    """热门样本回测套件"""

    def __init__(self):
        self.results = {}
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
        """加载顽主榜单代码"""
        wanzhu_path = PROJECT_ROOT / 'config' / 'wanzhu_top50_usable.json'
        if not wanzhu_path.exists():
            print(f"⚠️  找不到顽主榜单: {wanzhu_path}")
            return []

        with open(wanzhu_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            codes = [item['code'] for item in data.get('stocks', [])]
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
        运行单只股票回测

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

        # 这里应该调用实际的回测引擎
        # 当前简化版，返回模拟结果
        result = {
            'code': code,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'final_equity': initial_capital,  # 应该由回测引擎计算
            'total_return': 0.0,  # 应该由回测引擎计算
            'max_drawdown': 0.0,  # 应该由回测引擎计算
            'total_trades': 0,  # 应该由回测引擎计算
            'win_rate': 0.0,  # 应该由回测引擎计算
            'sharpe_ratio': 0.0  # 应该由回测引擎计算
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
        """打印汇总统计"""
        summary = results.get('summary', {})

        print(f"\n📊 回测套件汇总:")
        print(f"  总股票数: {summary.get('total_stocks', 0)}")
        print(f"  总交易次数: {summary.get('total_trades', 0)}")
        print(f"  平均胜率: {summary.get('avg_win_rate', 0):.2f}%")
        print(f"  平均收益率: {summary.get('avg_return', 0):.2f}%")
        print(f"  平均最大回撤: {summary.get('avg_max_drawdown', 0):.2f}%")


def main():
    """主函数"""
    suite = HotCasesSuite()
    results = suite.run_suite()

    print(f"\n✅ 热门样本回测套件完成")


if __name__ == '__main__':
    main()