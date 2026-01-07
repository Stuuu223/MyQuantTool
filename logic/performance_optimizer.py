"""PerformanceOptimizer - Performance Optimization & Parallel Computing

Version: 1.0.0
Feature: Vectorization, Parallel Backtesting, Grid/Random Search
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp
import time

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """Stock Optimization Engine"""

    def __init__(self, num_workers: int = 4):
        self.num_workers = min(num_workers, mp.cpu_count())
        self.cache = {}
        self.benchmarks = []
        logger.info(f"PerformanceOptimizer initialized ({self.num_workers} workers)")

    def vectorized_ma(self, prices: np.ndarray, periods: List[int]) -> Dict[int, np.ndarray]:
        """Vectorized moving averages
        
        Args:
            prices: Array of prices
            periods: List of MA periods
            
        Returns:
            Dict of MA arrays
        """
        try:
            mas = {}
            for period in periods:
                kernel = np.ones(period) / period
                ma = np.convolve(prices, kernel, mode='valid')
                ma = np.concatenate([np.full(period - 1, np.nan), ma])
                mas[period] = ma
            
            logger.info(f"Calculated {len(mas)} MAs")
            return mas
        except Exception as e:
            logger.error(f"vectorized_ma failed: {e}")
            return {}

    def parallel_backtest(self, codes: List[str], backtest_func: Callable, 
                         signals_list: List[np.ndarray]) -> List[Dict[str, Any]]:
        """Run backtests in parallel"""
        try:
            results = []
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                futures = {executor.submit(backtest_func, code, sig): code 
                          for code, sig in zip(codes, signals_list)}
                
                for future in futures:
                    try:
                        result = future.result(timeout=30)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Backtest failed: {e}")
            
            logger.info(f"Parallel backtest completed for {len(results)} stocks")
            return results
        except Exception as e:
            logger.error(f"parallel_backtest failed: {e}")
            return []

    def grid_search(self, param_grid: Dict[str, List[Any]], 
                   objective_func: Callable) -> Dict[str, Any]:
        """Grid search optimization"""
        try:
            from itertools import product
            
            best_score = -np.inf
            best_params = {}
            total = 1
            for values in param_grid.values():
                total *= len(values)
            
            logger.info(f"Grid search starting ({total} combinations)")
            
            tested = 0
            for combination in product(*param_grid.values()):
                params = dict(zip(param_grid.keys(), combination))
                try:
                    score = objective_func(**params)
                    tested += 1
                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                except Exception as e:
                    logger.debug(f"Combination failed: {e}")
                    continue
            
            logger.info(f"Grid search complete: best_score={best_score:.4f}")
            return {'best_params': best_params, 'best_score': best_score, 'tested': tested}
        except Exception as e:
            logger.error(f"grid_search failed: {e}")
            return {'error': str(e)}


def get_performance_optimizer(num_workers: int = 4) -> PerformanceOptimizer:
    """Get or create PerformanceOptimizer instance"""
    return PerformanceOptimizer(num_workers=num_workers)
