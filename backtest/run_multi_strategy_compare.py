#!/usr/bin/env python3
"""
多策略对比回测 - 同时运行EventDriven所有策略

功能：
1. 同时运行5大战法策略（Opening/Halfway/Leader/DipBuy/TrueAttack）
2. 对比各策略在相同股票上的触发情况
3. 识别哪个策略最能抓大哥

输出：对比报告，显示每只大哥股被哪个策略捕获
"""
import sys
import json
import time
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.strategies.unified_warfare_core import UnifiedWarfareCore
from logic.strategies.true_attack_detector import TrueAttackDetector
from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyCompareResult:
    """策略对比结果"""
    stock_code: str
    stock_name: str
    layer: str  # 高频核心/中频活跃等
    
    # 各策略触发次数
    opening_signals: int = 0
    halfway_signals: int = 0
    leader_signals: int = 0
    dipbuy_signals: int = 0
    attack_signals: int = 0
    
    # 总信号数
    total_signals: int = 0
    
    # 是否被任何策略捕获
    captured: bool = False
    
    # 最佳策略（触发最多的）
    best_strategy: str = "None"


class MultiStrategyComparator:
    """多策略比较器"""
    
    def __init__(self):
        self.warfare_core = UnifiedWarfareCore()
        # 添加资金攻击检测器
        self.attack_detector = TrueAttackDetector()
        self.results: List[StrategyCompareResult] = []
        
    def load_brother_stocks(self, csv_path: Path, top_n: int = 10) -> pd.DataFrame:
        """加载大哥股列表"""
        df = pd.read_csv(csv_path)
        # 按出现次数排序，取前N只大哥股
        df_sorted = df.sort_values('appear_count', ascending=False)
        return df_sorted.head(top_n)
    
    def analyze_stock(self, code: str, name: str, layer: str, 
                      start_date: str, end_date: str) -> StrategyCompareResult:
        """分析单只股票的各策略触发情况"""
        result = StrategyCompareResult(
            stock_code=code,
            stock_name=name,
            layer=layer
        )
        
        # TODO: 接入Tick数据回放，统计各策略触发次数
        # 这里先返回结构，等待TickProvider封装完成后实现
        
        return result
    
    def run_comparison(self, stocks_df: pd.DataFrame, 
                       start_date: str, end_date: str) -> Dict[str, Any]:
        """运行多策略对比"""
        print("="*80)
        print("🎯 多策略对比回测")
        print("="*80)
        print(f"股票数: {len(stocks_df)}")
        print(f"日期范围: {start_date} ~ {end_date}")
        print(f"策略列表: Opening | Halfway | Leader | DipBuy | TrueAttack")
        print("="*80)
        
        for _, row in stocks_df.iterrows():
            code = str(row['code']).zfill(6)
            # 添加后缀
            if code.startswith('6'):
                code = f"{code}.SH"
            else:
                code = f"{code}.SZ"
            
            result = self.analyze_stock(
                code=code,
                name=row['name'],
                layer=row['layer'],
                start_date=start_date,
                end_date=end_date
            )
            self.results.append(result)
            print(f"📊 {row['name']} ({code}) - 等待Tick数据接入")
        
        return self._generate_report()
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成对比报告"""
        return {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'strategies': ['Opening', 'Halfway', 'Leader', 'DipBuy', 'TrueAttack'],
                'stock_count': len(self.results)
            },
            'results': [
                {
                    'code': r.stock_code,
                    'name': r.stock_name,
                    'layer': r.layer,
                    'signals': {
                        'opening': r.opening_signals,
                        'halfway': r.halfway_signals,
                        'leader': r.leader_signals,
                        'dipbuy': r.dipbuy_signals,
                        'attack': r.attack_signals
                    },
                    'best_strategy': r.best_strategy
                }
                for r in self.results
            ],
            'summary': {
                'total_stocks': len(self.results),
                'captured_by_opening': sum(1 for r in self.results if r.opening_signals > 0),
                'captured_by_halfway': sum(1 for r in self.results if r.halfway_signals > 0),
                'captured_by_leader': sum(1 for r in self.results if r.leader_signals > 0),
                'captured_by_dipbuy': sum(1 for r in self.results if r.dipbuy_signals > 0),
                'captured_by_attack': sum(1 for r in self.results if r.attack_signals > 0),
            }
        }


def main():
    """主函数"""
    comparator = MultiStrategyComparator()
    
    # 加载大哥股
    csv_path = PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv'
    stocks_df = comparator.load_brother_stocks(csv_path, top_n=10)
    
    # 运行对比
    results = comparator.run_comparison(
        stocks_df=stocks_df,
        start_date='2025-11-15',
        end_date='2026-02-13'
    )
    
    # 保存结果
    output_dir = PROJECT_ROOT / 'backtest' / 'results'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f'multi_strategy_compare_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 结果已保存: {output_file}")


if __name__ == "__main__":
    main()
