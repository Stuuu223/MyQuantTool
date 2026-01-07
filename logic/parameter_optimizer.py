"""
参数网格搜索优化模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
import logging
from itertools import product

logger = logging.getLogger(__name__)


class ParameterGridSearch:
    """
    参数网格搜索优化器
    
    用于自动寻找最优策略参数
    """
    
    def __init__(self, backtest_engine, metric: str = 'sharpe_ratio'):
        """
        初始化参数网格搜索器
        
        Args:
            backtest_engine: 回测引擎实例
            metric: 优化目标指标 (sharpe_ratio, annual_return, max_drawdown, etc.)
        """
        self.engine = backtest_engine
        self.metric = metric
        self.results = []
    
    def search(
        self,
        symbol: str,
        df: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        signal_type: str = 'MA'
    ) -> Dict[str, Any]:
        """
        执行网格搜索
        
        Args:
            symbol: 股票代码
            df: K线数据
            param_grid: 参数网格字典
            signal_type: 信号类型
        
        Returns:
            最优参数和结果
        """
        # 生成所有参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        all_combinations = list(product(*param_values))
        
        logger.info(f"开始网格搜索: {len(all_combinations)} 个参数组合")
        
        best_params = None
        best_score = -np.inf if self.metric != 'max_drawdown' else np.inf
        best_metrics = None
        
        for i, combination in enumerate(all_combinations):
            # 构建参数字典
            params = dict(zip(param_names, combination))
            
            try:
                # 生成信号
                signals = self._generate_signals(df, params, signal_type)
                
                # 运行回测
                metrics = self.engine.backtest(symbol, df, signals, signal_type)
                
                # 获取优化指标值
                score = getattr(metrics, self.metric)
                
                # 记录结果
                result = {
                    'params': params,
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'annual_return': metrics.annual_return,
                    'max_drawdown': metrics.max_drawdown,
                    'win_rate': metrics.win_rate,
                    'total_trades': metrics.total_trades
                }
                self.results.append(result)
                
                # 更新最优参数
                is_better = (self.metric == 'max_drawdown' and score < best_score) or \
                           (self.metric != 'max_drawdown' and score > best_score)
                
                if is_better:
                    best_score = score
                    best_params = params
                    best_metrics = metrics
                
                logger.info(f"[{i+1}/{len(all_combinations)}] {params} -> {self.metric}: {score:.4f}")
            
            except Exception as e:
                logger.error(f"参数组合 {params} 回测失败: {e}")
                continue
        
        logger.info(f"网格搜索完成! 最优参数: {best_params}, {self.metric}: {best_score:.4f}")
        
        return {
            'best_params': best_params,
            'best_metrics': best_metrics._asdict() if best_metrics else None,
            'all_results': self.results
        }
    
    def _generate_signals(
        self,
        df: pd.DataFrame,
        params: Dict[str, Any],
        signal_type: str
    ) -> pd.Series:
        """
        根据参数生成信号
        
        Args:
            df: K线数据
            params: 参数字典
            signal_type: 信号类型
        
        Returns:
            交易信号
        """
        if signal_type == 'MA':
            fast_window = params.get('fast_window', 5)
            slow_window = params.get('slow_window', 20)
            
            sma_fast = df['close'].rolling(window=fast_window).mean()
            sma_slow = df['close'].rolling(window=slow_window).mean()
            
            signals = pd.Series(0, index=df.index)
            signals[sma_fast > sma_slow] = 1
            signals[sma_fast < sma_slow] = -1
            
            return signals
        
        elif signal_type == 'MACD':
            fast_period = params.get('fast_period', 12)
            slow_period = params.get('slow_period', 26)
            signal_period = params.get('signal_period', 9)
            
            # MACD 计算
            ema_fast = df['close'].ewm(span=fast_period).mean()
            ema_slow = df['close'].ewm(span=slow_period).mean()
            macd = ema_fast - ema_slow
            signal = macd.ewm(span=signal_period).mean()
            
            signals = pd.Series(0, index=df.index)
            signals[macd > signal] = 1
            signals[macd < signal] = -1
            
            return signals
        
        elif signal_type == 'RSI':
            period = params.get('period', 14)
            overbought = params.get('overbought', 70)
            oversold = params.get('oversold', 30)
            
            # RSI 计算
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            signals = pd.Series(0, index=df.index)
            signals[rsi < oversold] = 1
            signals[rsi > overbought] = -1
            
            return signals
        
        else:
            raise ValueError(f"不支持的信号类型: {signal_type}")
    
    def get_results_dataframe(self) -> pd.DataFrame:
        """
        获取搜索结果DataFrame
        
        Returns:
            结果表格
        """
        if not self.results:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.results)
        
        # 展开参数列
        params_df = pd.DataFrame(df['params'].tolist())
        result_df = pd.concat([params_df, df.drop('params', axis=1)], axis=1)
        
        # 按优化指标排序
        ascending = self.metric == 'max_drawdown'
        result_df = result_df.sort_values(by=self.metric, ascending=ascending)
        
        return result_df
    
    def get_top_n(self, n: int = 5) -> List[Dict]:
        """
        获取前N个最优参数组合
        
        Args:
            n: 返回数量
        
        Returns:
            前N个结果
        """
        df = self.get_results_dataframe()
        return df.head(n).to_dict('records')


class BayesianOptimization:
    """
    贝叶斯优化 (简化版)
    
    用于更高效的参数搜索
    """
    
    def __init__(self, backtest_engine, n_iter: int = 20):
        """
        初始化贝叶斯优化器
        
        Args:
            backtest_engine: 回测引擎
            n_iter: 迭代次数
        """
        self.engine = backtest_engine
        self.n_iter = n_iter
        self.history = []
    
    def optimize(
        self,
        symbol: str,
        df: pd.DataFrame,
        param_bounds: Dict[str, Tuple[int, int]],
        signal_type: str = 'MA'
    ) -> Dict[str, Any]:
        """
        执行贝叶斯优化
        
        Args:
            symbol: 股票代码
            df: K线数据
            param_bounds: 参数边界
            signal_type: 信号类型
        
        Returns:
            最优参数
        """
        # 简化版: 随机搜索 + 局部优化
        best_params = None
        best_score = -np.inf
        
        for i in range(self.n_iter):
            # 随机采样
            params = {}
            for param_name, (min_val, max_val) in param_bounds.items():
                params[param_name] = np.random.randint(min_val, max_val + 1)
            
            try:
                # 生成信号
                signals = self._generate_signals(df, params, signal_type)
                
                # 运行回测
                metrics = self.engine.backtest(symbol, df, signals, signal_type)
                score = metrics.sharpe_ratio
                
                self.history.append({'params': params, 'score': score})
                
                if score > best_score:
                    best_score = score
                    best_params = params
                
                logger.info(f"[{i+1}/{self.n_iter}] {params} -> Sharpe: {score:.4f}")
            
            except Exception as e:
                logger.error(f"参数组合 {params} 回测失败: {e}")
                continue
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'history': self.history
        }
    
    def _generate_signals(
        self,
        df: pd.DataFrame,
        params: Dict[str, Any],
        signal_type: str
    ) -> pd.Series:
        """生成信号 (复用ParameterGridSearch的逻辑)"""
        grid_search = ParameterGridSearch(self.engine)
        return grid_search._generate_signals(df, params, signal_type)