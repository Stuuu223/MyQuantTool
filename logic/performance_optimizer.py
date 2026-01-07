"""
性能优化器 - 向量化+并行+参数优化
功能：
- NumPy向量化计算
- 并行回测执行
- 网格搜索参数优化
- 性能基准测试
- 内存优化
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable, Any
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
import time
import multiprocessing as mp


@dataclass
class OptimizationResult:
    """优化结果"""
    best_params: Dict[str, Any]
    best_score: float
    all_results: List[Dict[str, Any]]
    optimization_time: float


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    operation: str
    execution_time: float
    memory_usage: float
    throughput: float


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self, num_workers: Optional[int] = None):
        """
        Args:
            num_workers: 并行工作进程数（None表示使用CPU核心数）
        """
        self.num_workers = num_workers or mp.cpu_count()
    
    def vectorized_ma(
        self,
        prices: np.ndarray,
        periods: List[int]
    ) -> Dict[int, np.ndarray]:
        """
        向量化计算移动平均线
        
        Args:
            prices: 价格序列
            periods: 周期列表
        
        Returns:
            周期到MA数组的映射
        """
        results = {}
        for period in periods:
            # 使用卷积计算移动平均
            kernel = np.ones(period) / period
            ma = np.convolve(prices, kernel, mode='valid')
            # 填充前period-1个值为NaN
            ma_padded = np.full_like(prices, np.nan, dtype=float)
            ma_padded[period-1:] = ma
            results[period] = ma_padded
        
        return results
    
    def vectorized_rsi(
        self,
        prices: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """
        向量化计算RSI指标
        
        Args:
            prices: 价格序列
            period: 周期
        
        Returns:
            RSI序列
        """
        # 计算价格变化
        deltas = np.diff(prices)
        
        # 分离涨跌
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # 计算平均涨跌
        avg_gains = np.convolve(gains, np.ones(period)/period, mode='valid')
        avg_losses = np.convolve(losses, np.ones(period)/period, mode='valid')
        
        # 计算RSI
        rs = avg_gains / (avg_losses + 1e-10)  # 避免除零
        rsi = 100 - (100 / (1 + rs))
        
        # 填充前period个值为NaN
        rsi_padded = np.full_like(prices, np.nan, dtype=float)
        rsi_padded[period:] = rsi
        
        return rsi_padded
    
    def vectorized_macd(
        self,
        prices: np.ndarray,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        向量化计算MACD指标
        
        Args:
            prices: 价格序列
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
        
        Returns:
            (DIF, DEA, MACD)
        """
        # 计算EMA
        ema_fast = self._vectorized_ema(prices, fast_period)
        ema_slow = self._vectorized_ema(prices, slow_period)
        
        # DIF
        dif = ema_fast - ema_slow
        
        # DEA
        dea = self._vectorized_ema(dif, signal_period)
        
        # MACD
        macd = 2 * (dif - dea)
        
        return dif, dea, macd
    
    def _vectorized_ema(
        self,
        data: np.ndarray,
        period: int,
        alpha: Optional[float] = None
    ) -> np.ndarray:
        """
        向量化计算EMA
        
        Args:
            data: 数据序列
            period: 周期
            alpha: 平滑系数（None则自动计算）
        
        Returns:
            EMA序列
        """
        if alpha is None:
            alpha = 2 / (period + 1)
        
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        
        return ema
    
    def vectorized_atr(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """
        向量化计算ATR指标
        
        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 周期
        
        Returns:
            ATR序列
        """
        # 计算真实波幅
        high_low = high - low
        high_close = np.abs(high - np.roll(close, 1))
        low_close = np.abs(low - np.roll(close, 1))
        
        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        
        # 计算ATR（使用RMA）
        atr = self._vectorized_rma(tr, period)
        
        return atr
    
    def _vectorized_rma(
        self,
        data: np.ndarray,
        period: int
    ) -> np.ndarray:
        """
        向量化计算RMA（Wilder's Smoothing）
        
        Args:
            data: 数据序列
            period: 周期
        
        Returns:
            RMA序列
        """
        alpha = 1 / period
        rma = np.zeros_like(data)
        rma[0] = data[0]
        
        for i in range(1, len(data)):
            rma[i] = alpha * data[i] + (1 - alpha) * rma[i-1]
        
        return rma
    
    def parallel_backtest(
        self,
        codes: List[str],
        backtest_func: Callable[[str, Any], Dict],
        signals_list: Optional[List[Any]] = None,
        **kwargs
    ) -> List[Dict]:
        """
        并行回测多只股票
        
        Args:
            codes: 股票代码列表
            backtest_func: 回测函数
            signals_list: 信号列表（可选）
            **kwargs: 其他参数
        
        Returns:
            回测结果列表
        """
        results = [None] * len(codes)
        
        # 创建任务
        tasks = []
        if signals_list:
            for code, signals in zip(codes, signals_list):
                task = partial(backtest_func, code, signals, **kwargs)
                tasks.append((code, task))
        else:
            for code in codes:
                task = partial(backtest_func, code, **kwargs)
                tasks.append((code, task))
        
        # 并行执行
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            future_to_code = {
                executor.submit(task): code
                for code, task in tasks
            }
            
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    result = future.result()
                    idx = codes.index(code)
                    results[idx] = result
                except Exception as e:
                    print(f"回测 {code} 失败: {e}")
                    results[codes.index(code)] = {'error': str(e)}
        
        return results
    
    def grid_search(
        self,
        param_grid: Dict[str, List[Any]],
        objective_func: Callable[..., float],
        maximize: bool = True,
        verbose: bool = True
    ) -> OptimizationResult:
        """
        网格搜索参数优化
        
        Args:
            param_grid: 参数网格
            objective_func: 目标函数
            maximize: 是否最大化目标函数
            verbose: 是否打印进度
        
        Returns:
            优化结果
        """
        start_time = time.time()
        
        # 生成所有参数组合
        import itertools
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        all_combinations = list(itertools.product(*param_values))
        
        all_results = []
        best_score = float('-inf') if maximize else float('inf')
        best_params = {}
        
        # 评估每个参数组合
        for i, combination in enumerate(all_combinations):
            params = dict(zip(param_names, combination))
            
            try:
                score = objective_func(**params)
                
                result = {
                    'params': params.copy(),
                    'score': score
                }
                all_results.append(result)
                
                # 更新最佳参数
                if (maximize and score > best_score) or (not maximize and score < best_score):
                    best_score = score
                    best_params = params.copy()
                
                if verbose and (i + 1) % 10 == 0:
                    print(f"已完成 {i + 1}/{len(all_combinations)} 次，当前最佳: {best_score:.4f}")
            
            except Exception as e:
                if verbose:
                    print(f"参数组合 {params} 评估失败: {e}")
                all_results.append({
                    'params': params.copy(),
                    'score': None,
                    'error': str(e)
                })
        
        optimization_time = time.time() - start_time
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_results=all_results,
            optimization_time=optimization_time
        )
    
    def parallel_grid_search(
        self,
        param_grid: Dict[str, List[Any]],
        objective_func: Callable[..., float],
        maximize: bool = True,
        verbose: bool = True
    ) -> OptimizationResult:
        """
        并行网格搜索参数优化
        
        Args:
            param_grid: 参数网格
            objective_func: 目标函数
            maximize: 是否最大化目标函数
            verbose: 是否打印进度
        
        Returns:
            优化结果
        """
        start_time = time.time()
        
        # 生成所有参数组合
        import itertools
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        all_combinations = list(itertools.product(*param_values))
        
        # 并行评估
        all_results = []
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            future_to_params = {
                executor.submit(objective_func, **dict(zip(param_names, combination))): combination
                for combination in all_combinations
            }
            
            for future in as_completed(future_to_params):
                combination = future_to_params[future]
                try:
                    score = future.result()
                    result = {
                        'params': dict(zip(param_names, combination)),
                        'score': score
                    }
                    all_results.append(result)
                except Exception as e:
                    if verbose:
                        print(f"参数组合评估失败: {e}")
                    all_results.append({
                        'params': dict(zip(param_names, combination)),
                        'score': None,
                        'error': str(e)
                    })
        
        # 找到最佳参数
        valid_results = [r for r in all_results if r['score'] is not None]
        if valid_results:
            if maximize:
                best_result = max(valid_results, key=lambda x: x['score'])
            else:
                best_result = min(valid_results, key=lambda x: x['score'])
            
            best_params = best_result['params']
            best_score = best_result['score']
        else:
            best_params = {}
            best_score = float('-inf') if maximize else float('inf')
        
        optimization_time = time.time() - start_time
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_results=all_results,
            optimization_time=optimization_time
        )
    
    def benchmark_operation(
        self,
        operation: Callable,
        *args,
        iterations: int = 100,
        **kwargs
    ) -> BenchmarkResult:
        """
        基准测试操作性能
        
        Args:
            operation: 要测试的操作
            *args: 操作参数
            iterations: 迭代次数
            **kwargs: 操作关键字参数
        
        Returns:
            基准测试结果
        """
        import sys
        import tracemalloc
        
        # 预热
        for _ in range(5):
            operation(*args, **kwargs)
        
        # 内存测试
        tracemalloc.start()
        operation(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # 时间测试
        start_time = time.time()
        for _ in range(iterations):
            operation(*args, **kwargs)
        end_time = time.time()
        
        execution_time = (end_time - start_time) / iterations
        memory_usage = peak / (1024 * 1024)  # MB
        throughput = 1 / execution_time if execution_time > 0 else 0
        
        return BenchmarkResult(
            operation=operation.__name__,
            execution_time=execution_time,
            memory_usage=memory_usage,
            throughput=throughput
        )
    
    def optimize_dataframe_memory(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        优化DataFrame内存使用
        
        Args:
            df: 输入DataFrame
        
        Returns:
            优化后的DataFrame
        """
        df_optimized = df.copy()
        
        for col in df_optimized.columns:
            col_type = df_optimized[col].dtype
            
            if col_type == 'object':
                # 尝试转换为category
                if df_optimized[col].nunique() / len(df_optimized[col]) < 0.5:
                    df_optimized[col] = df_optimized[col].astype('category')
            
            elif col_type == 'float64':
                # 尝试转换为float32
                df_optimized[col] = df_optimized[col].astype('float32')
            
            elif col_type == 'int64':
                # 尝试转换为更小的整数类型
                col_min = df_optimized[col].min()
                col_max = df_optimized[col].max()
                
                if col_min >= 0:
                    if col_max < 256:
                        df_optimized[col] = df_optimized[col].astype('uint8')
                    elif col_max < 65536:
                        df_optimized[col] = df_optimized[col].astype('uint16')
                    elif col_max < 4294967296:
                        df_optimized[col] = df_optimized[col].astype('uint32')
                else:
                    if col_min >= -128 and col_max < 128:
                        df_optimized[col] = df_optimized[col].astype('int8')
                    elif col_min >= -32768 and col_max < 32768:
                        df_optimized[col] = df_optimized[col].astype('int16')
                    elif col_min >= -2147483648 and col_max < 2147483648:
                        df_optimized[col] = df_optimized[col].astype('int32')
        
        return df_optimized
    
    def batch_vectorized_indicators(
        self,
        df: pd.DataFrame,
        indicators: List[str]
    ) -> pd.DataFrame:
        """
        批量计算技术指标（向量化）
        
        Args:
            df: K线数据
            indicators: 指标列表 ['MA5', 'MA10', 'MA20', 'RSI', 'MACD', 'ATR']
        
        Returns:
            包含指标的DataFrame
        """
        result_df = df.copy()
        
        prices = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        for indicator in indicators:
            if indicator.startswith('MA'):
                period = int(indicator[2:])
                ma_dict = self.vectorized_ma(prices, [period])
                result_df[indicator] = ma_dict[period]
            
            elif indicator == 'RSI':
                result_df['RSI'] = self.vectorized_rsi(prices)
            
            elif indicator == 'MACD':
                dif, dea, macd = self.vectorized_macd(prices)
                result_df['DIF'] = dif
                result_df['DEA'] = dea
                result_df['MACD'] = macd
            
            elif indicator == 'ATR':
                result_df['ATR'] = self.vectorized_atr(high, low, prices)
        
        return result_df


def get_performance_optimizer(num_workers: Optional[int] = None) -> PerformanceOptimizer:
    """
    获取性能优化器实例
    
    Args:
        num_workers: 并行工作进程数
    
    Returns:
        PerformanceOptimizer实例
    """
    return PerformanceOptimizer(num_workers=num_workers)