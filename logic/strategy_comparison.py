"""
策略回测对比模块

功能：
- 多策略回测对比
- 性能指标分析
- 可视化对比结果
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from logic.strategy_factory import Strategy, StrategyFactory
from logic.backtest_engine import BacktestEngine, BacktestResult


class StrategyComparator:
    """策略对比器"""
    
    def __init__(self):
        self.comparison_results = {}
        self.performance_metrics = {}
    
    def run_strategy_comparison(self, 
                              strategies: List[Strategy], 
                              data: pd.DataFrame, 
                              backtest_engine: BacktestEngine) -> pd.DataFrame:
        """
        运行多个策略的对比回测
        
        Args:
            strategies: 策略列表
            data: 回测数据
            backtest_engine: 回测引擎
            
        Returns:
            对比结果DataFrame
        """
        comparison_data = []
        
        print(f"开始对比 {len(strategies)} 个策略的回测表现")
        
        for i, strategy in enumerate(strategies):
            print(f"正在回测策略 {i+1}/{len(strategies)}: {strategy.name}")
            
            try:
                # 运行回测
                result = backtest_engine.run_backtest(strategy, data)
                
                # 提取关键指标
                metrics = result.metrics
                comparison_data.append({
                    'strategy_name': strategy.name,
                    'total_return': metrics.get('total_return', 0),
                    'annual_return': metrics.get('annual_return', 0),
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                    'max_drawdown': metrics.get('max_drawdown', 0),
                    'calmar_ratio': metrics.get('calmar_ratio', 0),
                    'win_rate': metrics.get('win_rate', 0),
                    'profit_factor': metrics.get('profit_factor', 0),
                    'total_trades': metrics.get('total_trades', 0),
                    'winning_trades': metrics.get('winning_trades', 0),
                    'losing_trades': metrics.get('losing_trades', 0),
                    'avg_win_rate': metrics.get('avg_win_rate', 0),
                    'avg_loss_rate': metrics.get('avg_loss_rate', 0),
                    'start_date': result.start_date,
                    'end_date': result.end_date,
                    'final_equity': result.final_equity,
                    'volatility': metrics.get('volatility', 0)
                })
                
                # 保存详细结果
                self.comparison_results[strategy.name] = result
                self.performance_metrics[strategy.name] = metrics
                
            except Exception as e:
                print(f"策略 {strategy.name} 回测失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        if comparison_data:
            df = pd.DataFrame(comparison_data)
            
            # 计算排名
            df['sharpe_rank'] = df['sharpe_ratio'].rank(method='dense', ascending=False).astype(int)
            df['return_rank'] = df['total_return'].rank(method='dense', ascending=False).astype(int)
            df['drawdown_rank'] = df['max_drawdown'].rank(method='dense', ascending=True).astype(int)  # 回撤越小越好
            
            # 计算综合评分（基于夏普比率、收益率和回撤）
            df['composite_score'] = (
                df['sharpe_ratio'].rank(pct=True, ascending=False) * 0.4 +
                df['total_return'].rank(pct=True, ascending=False) * 0.4 +
                df['max_drawdown'].rank(pct=True, ascending=True) * 0.2
            )
            
            df['composite_rank'] = df['composite_score'].rank(method='dense', ascending=False).astype(int)
            
            return df
        else:
            return pd.DataFrame()  # 返回空DataFrame
    
    def generate_comparison_report(self, comparison_df: pd.DataFrame) -> str:
        """生成详细的策略对比报告"""
        if comparison_df.empty:
            return "没有可比较的策略结果"
        
        report = "策略对比分析报告\n"
        report += "=" * 60 + "\n"
        report += f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # 基本统计
        report += "一、基本统计信息\n"
        report += "-" * 30 + "\n"
        report += f"回测策略数量: {len(comparison_df)}\n"
        report += f"回测时间范围: {comparison_df['start_date'].min()} 到 {comparison_df['end_date'].max()}\n\n"
        
        # 按夏普比率排序
        sorted_by_sharpe = comparison_df.sort_values('sharpe_ratio', ascending=False)
        report += "二、按夏普比率排序\n"
        report += "-" * 30 + "\n"
        
        for idx, row in sorted_by_sharpe.iterrows():
            report += f"{row['strategy_name']:<30} "
            report += f"夏普比率: {row['sharpe_ratio']:>8.4f} "
            report += f"总收益率: {row['total_return']:>8.4f} "
            report += f"最大回撤: {row['max_drawdown']:>8.4f}\n"
        
        report += "\n三、综合排名\n"
        report += "-" * 30 + "\n"
        sorted_by_composite = comparison_df.sort_values('composite_score', ascending=False)
        
        for idx, row in sorted_by_composite.iterrows():
            report += f"第{int(row['composite_rank'])}名: {row['strategy_name']:<25} "
            report += f"综合评分: {row['composite_score']:.4f}\n"
        
        report += "\n四、策略详细表现\n"
        report += "-" * 30 + "\n"
        for idx, row in comparison_df.iterrows():
            report += f"策略: {row['strategy_name']}\n"
            report += f"  总收益率: {row['total_return']:.4f} ({row['return_rank']}名)\n"
            report += f"  年化收益率: {row['annual_return']:.4f}\n"
            report += f"  夏普比率: {row['sharpe_ratio']:.4f} ({row['sharpe_rank']}名)\n"
            report += f"  最大回撤: {row['max_drawdown']:.4f} ({row['drawdown_rank']}名)\n"
            report += f"  卡尔玛比率: {row['calmar_ratio']:.4f}\n"
            report += f"  胜率: {row['win_rate']:.4f}\n"
            report += f"  盈利因子: {row['profit_factor']:.4f}\n"
            report += f"  总交易次数: {row['total_trades']}\n"
            report += f"  最终权益: {row['final_equity']:.2f}\n"
            report += f"  波动率: {row['volatility']:.4f}\n"
            report += f"  综合评分: {row['composite_score']:.4f} ({int(row['composite_rank'])}名)\n\n"
        
        return report
    
    def plot_performance_comparison(self, comparison_df: pd.DataFrame, figsize: tuple = (15, 10)):
        """绘制性能对比图表"""
        if comparison_df.empty:
            print("没有数据可绘制")
            return
        
        fig, axes = plt.subplots(2, 3, figsize=figsize)
        fig.suptitle('策略性能对比分析', fontsize=16)
        
        strategies = comparison_df['strategy_name']
        
        # 1. 总收益率对比
        axes[0, 0].bar(strategies, comparison_df['total_return'])
        axes[0, 0].set_title('总收益率对比')
        axes[0, 0].set_ylabel('收益率')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 2. 夏普比率对比
        axes[0, 1].bar(strategies, comparison_df['sharpe_ratio'])
        axes[0, 1].set_title('夏普比率对比')
        axes[0, 1].set_ylabel('夏普比率')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 3. 最大回撤对比
        axes[0, 2].bar(strategies, comparison_df['max_drawdown'])
        axes[0, 2].set_title('最大回撤对比')
        axes[0, 2].set_ylabel('回撤')
        axes[0, 2].tick_params(axis='x', rotation=45)
        
        # 4. 胜率对比
        axes[1, 0].bar(strategies, comparison_df['win_rate'])
        axes[1, 0].set_title('胜率对比')
        axes[1, 0].set_ylabel('胜率')
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 5. 盈利因子对比
        axes[1, 1].bar(strategies, comparison_df['profit_factor'])
        axes[1, 1].set_title('盈利因子对比')
        axes[1, 1].set_ylabel('盈利因子')
        axes[1, 1].tick_params(axis='x', rotation=45)
        
        # 6. 交易次数对比
        axes[1, 2].bar(strategies, comparison_df['total_trades'])
        axes[1, 2].set_title('交易次数对比')
        axes[1, 2].set_ylabel('交易次数')
        axes[1, 2].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.show()
    
    def plot_equity_curves_comparison(self, data: pd.DataFrame, strategies: List[Strategy], backtest_engine: BacktestEngine):
        """绘制多策略权益曲线对比"""
        plt.figure(figsize=(15, 8))
        
        for strategy in strategies:
            try:
                result = backtest_engine.run_backtest(strategy, data)
                if hasattr(result, 'equity_curve') and result.equity_curve is not None:
                    plt.plot(result.equity_curve.index, result.equity_curve.values, label=strategy.name, linewidth=1.5)
                else:
                    print(f"{strategy.name} 没有权益曲线数据")
            except Exception as e:
                print(f"{strategy.name} 回测失败: {e}")
                continue
        
        plt.title('策略权益曲线对比')
        plt.xlabel('时间')
        plt.ylabel('权益')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.show()
    
    def generate_ranking_matrix(self, comparison_df: pd.DataFrame) -> pd.DataFrame:
        """生成排名矩阵"""
        metrics = ['sharpe_ratio', 'total_return', 'max_drawdown', 'win_rate', 'profit_factor']
        strategy_names = comparison_df['strategy_name']
        
        rank_matrix = pd.DataFrame(index=strategy_names, columns=metrics)
        
        for metric in metrics:
            # 根据指标特性决定排序方向
            ascending = metric == 'max_drawdown'  # 最大回撤越小越好
            ranks = comparison_df.set_index('strategy_name')[metric].rank(method='min', ascending=ascending)
            rank_matrix[metric] = ranks.astype(int)
        
        return rank_matrix
    
    def export_results(self, comparison_df: pd.DataFrame, filename: str = None):
        """导出对比结果到CSV"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"strategy_comparison_{timestamp}.csv"
        
        comparison_df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"对比结果已导出到: {filename}")
        
        # 同时导出排名矩阵
        rank_matrix = self.generate_ranking_matrix(comparison_df)
        rank_filename = filename.replace('.csv', '_ranks.csv')
        rank_matrix.to_csv(rank_filename, encoding='utf-8-sig')
        print(f"排名矩阵已导出到: {rank_filename}")


def demo_strategy_comparison():
    """演示策略对比功能"""
    print("=== 策略对比演示 ===")
    
    # 创建策略工厂和回测引擎
    factory = StrategyFactory()
    
    try:
        from logic.backtest_engine import BacktestEngine
        backtest_engine = BacktestEngine()
        
        # 创建示例数据
        dates = pd.date_range(end=datetime.now(), periods=252)  # 一年交易日
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.normal(0.001, 0.02, 252))  # 模拟价格走势
        
        data = pd.DataFrame({
            'date': dates,
            'open': prices + np.random.normal(0, 0.1, 252),
            'high': prices + abs(np.random.normal(0, 0.15, 252)),
            'low': prices - abs(np.random.normal(0, 0.15, 252)),
            'close': prices,
            'volume': np.random.normal(1000000, 200000, 252)
        }).set_index('date')
        
        # 创建多个策略进行对比
        strategies = [
            factory.create_strategy_from_template('ma_crossover', {'short_window': 10, 'long_window': 30}),
            factory.create_strategy_from_template('ma_crossover', {'short_window': 5, 'long_window': 20}),
            factory.create_strategy_from_template('rsi_reversion', {'rsi_period': 14, 'overbought_level': 70, 'oversold_level': 30}),
            factory.create_strategy_from_template('rsi_reversion', {'rsi_period': 10, 'overbought_level': 80, 'oversold_level': 20}),
            factory.create_strategy_from_template('bollinger_bands', {'period': 20, 'std_dev': 2.0}),
            factory.create_strategy_from_template('bollinger_bands', {'period': 10, 'std_dev': 1.5})
        ]
        
        # 创建策略对比器
        comparator = StrategyComparator()
        
        # 运行对比回测
        comparison_results = comparator.run_strategy_comparison(strategies, data, backtest_engine)
        
        if not comparison_results.empty:
            print("\n对比结果摘要:")
            print(comparison_results[['strategy_name', 'total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate', 'composite_score']].round(4))
            
            print("\n" + "="*60)
            # 生成详细报告
            report = comparator.generate_comparison_report(comparison_results)
            print(report)
            
            print("\n生成排名矩阵:")
            rank_matrix = comparator.generate_ranking_matrix(comparison_results)
            print(rank_matrix)
            
            # 导出结果
            comparator.export_results(comparison_results)
        else:
            print("未能生成对比结果")
            
    except ImportError:
        print("回测引擎未找到，跳过演示")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_strategy_comparison()