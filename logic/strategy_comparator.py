"""
多策略对比功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class MultiStrategyComparator:
    """
    多策略对比器
    
    对比多个策略的表现
    """
    
    def __init__(self, backtest_engine):
        """
        初始化对比器
        
        Args:
            backtest_engine: 回测引擎
        """
        self.engine = backtest_engine
        self.results = {}
    
    def compare_strategies(
        self,
        symbol: str,
        df: pd.DataFrame,
        strategies: List[Dict],
        initial_capital: float = 100000
    ) -> Dict:
        """
        对比多个策略
        
        Args:
            symbol: 股票代码
            df: K线数据
            strategies: 策略列表 [{'name': 'MA', 'params': {...}}, ...]
            initial_capital: 初始资金
        
        Returns:
            对比结果
        """
        self.results = {}
        
        for strategy_config in strategies:
            strategy_name = strategy_config['name']
            params = strategy_config.get('params', {})
            
            try:
                # 生成信号
                signals = self._generate_signals(df, strategy_name, params)
                
                # 运行回测
                metrics = self.engine.backtest(symbol, df, signals, strategy_name)
                
                self.results[strategy_name] = {
                    'metrics': metrics._asdict(),
                    'params': params,
                    'equity_curve': self.engine.equity_curve
                }
                
                logger.info(f"策略 {strategy_name} 回测完成: 收益率 {metrics.total_return:.2%}")
            
            except Exception as e:
                logger.error(f"策略 {strategy_name} 回测失败: {e}")
                continue
        
        # 生成对比报告
        comparison_report = self._generate_comparison_report()
        
        return {
            'results': self.results,
            'report': comparison_report
        }
    
    def _generate_signals(
        self,
        df: pd.DataFrame,
        strategy_name: str,
        params: Dict
    ) -> pd.Series:
        """
        生成信号
        
        Args:
            df: K线数据
            strategy_name: 策略名称
            params: 参数
        
        Returns:
            交易信号
        """
        if strategy_name == 'MA':
            fast = params.get('fast_window', 5)
            slow = params.get('slow_window', 20)
            
            sma_fast = df['close'].rolling(window=fast).mean()
            sma_slow = df['close'].rolling(window=slow).mean()
            
            signals = pd.Series(0, index=df.index)
            signals[sma_fast > sma_slow] = 1
            signals[sma_fast < sma_slow] = -1
            
            return signals
        
        elif strategy_name == 'MACD':
            fast = params.get('fast_period', 12)
            slow = params.get('slow_period', 26)
            signal_period = params.get('signal_period', 9)
            
            ema_fast = df['close'].ewm(span=fast).mean()
            ema_slow = df['close'].ewm(span=slow).mean()
            macd = ema_fast - ema_slow
            signal = macd.ewm(span=signal_period).mean()
            
            signals = pd.Series(0, index=df.index)
            signals[macd > signal] = 1
            signals[macd < signal] = -1
            
            return signals
        
        elif strategy_name == 'RSI':
            period = params.get('period', 14)
            overbought = params.get('overbought', 70)
            oversold = params.get('oversold', 30)
            
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            signals = pd.Series(0, index=df.index)
            signals[rsi < oversold] = 1
            signals[rsi > overbought] = -1
            
            return signals
        
        elif strategy_name == 'BuyHold':
            # 买入持有策略
            signals = pd.Series(0, index=df.index)
            signals.iloc[0] = 1  # 第一天买入
            
            return signals
        
        else:
            raise ValueError(f"不支持的策略: {strategy_name}")
    
    def _generate_comparison_report(self) -> Dict:
        """
        生成对比报告
        
        Returns:
            对比报告
        """
        if not self.results:
            return {}
        
        # 提取指标
        comparison_df = pd.DataFrame()
        
        for strategy_name, result in self.results.items():
            metrics = result['metrics']
            comparison_df[strategy_name] = [
                metrics.get('total_return', 0),
                metrics.get('annual_return', 0),
                metrics.get('sharpe_ratio', 0),
                metrics.get('max_drawdown', 0),
                metrics.get('win_rate', 0),
                metrics.get('profit_factor', 0),
                metrics.get('total_trades', 0)
            ]
        
        comparison_df.index = [
            '总收益率',
            '年化收益',
            '夏普比率',
            '最大回撤',
            '胜率',
            '盈亏比',
            '交易次数'
        ]
        
        # 找出最佳策略
        best_sharpe = max(
            self.results.items(),
            key=lambda x: x[1]['metrics'].get('sharpe_ratio', 0)
        )
        
        best_return = max(
            self.results.items(),
            key=lambda x: x[1]['metrics'].get('total_return', 0)
        )
        
        best_drawdown = min(
            self.results.items(),
            key=lambda x: x[1]['metrics'].get('max_drawdown', 0)
        )
        
        # 计算相关性
        correlation_matrix = self._calculate_correlation()
        
        return {
            'comparison_table': comparison_df,
            'best_sharpe': best_sharpe[0],
            'best_return': best_return[0],
            'best_drawdown': best_drawdown[0],
            'correlation_matrix': correlation_matrix
        }
    
    def _calculate_correlation(self) -> pd.DataFrame:
        """
        计算策略相关性
        
        Returns:
            相关性矩阵
        """
        equity_curves = {}
        
        for strategy_name, result in self.results.items():
            equity_curves[strategy_name] = pd.Series(result['equity_curve'])
        
        # 对齐长度
        min_len = min(len(curve) for curve in equity_curves.values())
        
        for name in equity_curves:
            equity_curves[name] = equity_curves[name][:min_len]
        
        # 计算收益率
        returns_df = pd.DataFrame(equity_curves).pct_change().dropna()
        
        # 计算相关性
        correlation_matrix = returns_df.corr()
        
        return correlation_matrix
    
    def get_ranking(self, metric: str = 'sharpe_ratio') -> List[Dict]:
        """
        获取策略排名
        
        Args:
            metric: 排名指标
        
        Returns:
            排名列表
        """
        if not self.results:
            return []
        
        ranking = []
        
        for strategy_name, result in self.results.items():
            metrics = result['metrics']
            ranking.append({
                'strategy': strategy_name,
                'value': metrics.get(metric, 0),
                'params': result['params']
            })
        
        # 排序
        reverse = metric != 'max_drawdown'
        ranking.sort(key=lambda x: x['value'], reverse=reverse)
        
        return ranking
    
    def get_equity_curves(self) -> Dict[str, List]:
        """
        获取所有策略的净值曲线
        
        Returns:
            净值曲线字典
        """
        return {
            strategy_name: result['equity_curve']
            for strategy_name, result in self.results.items()
        }
    
    def export_comparison(self, filename: str):
        """
        导出对比结果
        
        Args:
            filename: 文件名
        """
        if not self.results:
            logger.warning("无对比结果可导出")
            return
        
        # 导出对比表
        report = self._generate_comparison_report()
        
        with pd.ExcelWriter(filename) as writer:
            report['comparison_table'].to_excel(writer, sheet_name='对比表')
            report['correlation_matrix'].to_excel(writer, sheet_name='相关性矩阵')
        
        logger.info(f"对比结果已导出到: {filename}")


class StrategyPerformanceAnalyzer:
    """
    策略表现分析器
    
    深度分析策略表现
    """
    
    @staticmethod
    def analyze_win_loss_distribution(trades: List[Dict]) -> Dict:
        """
        分析盈亏分布
        
        Args:
            trades: 交易记录
        
        Returns:
            盈亏分布统计
        """
        if not trades:
            return {}
        
        pnls = [trade.get('pnl', 0) for trade in trades]
        
        return {
            'total_trades': len(trades),
            'winning_trades': len([pnl for pnl in pnls if pnl > 0]),
            'losing_trades': len([pnl for pnl in pnls if pnl < 0]),
            'avg_win': np.mean([pnl for pnl in pnls if pnl > 0]) if any(pnl > 0 for pnl in pnls) else 0,
            'avg_loss': np.mean([pnl for pnl in pnls if pnl < 0]) if any(pnl < 0 for pnl in pnls) else 0,
            'largest_win': max(pnls) if pnls else 0,
            'largest_loss': min(pnls) if pnls else 0,
            'std_dev': np.std(pnls) if pnls else 0
        }
    
    @staticmethod
    def analyze_monthly_performance(equity_curve: List[float]) -> pd.DataFrame:
        """
        分析月度表现
        
        Args:
            equity_curve: 净值曲线
        
        Returns:
            月度表现DataFrame
        """
        if not equity_curve:
            return pd.DataFrame()
        
        # 简化: 假设每月20个交易日
        monthly_returns = []
        
        for i in range(0, len(equity_curve), 20):
            if i + 20 < len(equity_curve):
                month_return = (equity_curve[i + 20] - equity_curve[i]) / equity_curve[i]
                monthly_returns.append(month_return)
        
        df = pd.DataFrame({
            '月份': range(1, len(monthly_returns) + 1),
            '收益率': monthly_returns
        })
        
        return df
    
    @staticmethod
    def calculate_information_ratio(
        strategy_returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> float:
        """
        计算信息比率
        
        Args:
            strategy_returns: 策略收益率
            benchmark_returns: 基准收益率
        
        Returns:
            信息比率
        """
        excess_returns = strategy_returns - benchmark_returns
        
        if len(excess_returns) == 0 or np.std(excess_returns) == 0:
            return 0
        
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)