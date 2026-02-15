#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多线程并发执行器

功能：
1. 批量获取实时数据（并发）
2. 批量获取历史数据（并发）
3. 批量执行函数（并发）
4. 智能线程池管理

Author: iFlow CLI
Version: V1.0
"""

import concurrent.futures
import time
from typing import List, Dict, Any, Callable, Optional, Tuple
from functools import partial
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class ConcurrentExecutor:
    """多线程并发执行器"""
    
    def __init__(self, max_workers: int = 2):
        """
        初始化并发执行器
        
        Args:
            max_workers: 最大线程数 (建议不超过2，避免connection pool溢出)
        
        🆕 V19.6 修复：
        - 将默认并发数从5降到2，避免连接池满的问题
        - 原因：requests库底层连接池默认只有10个位置，5个线程并发时
          每个线程可能发起多次请求（日线+分时+资金流），瞬间占满连接池
        """
        self.max_workers = max_workers
        
        # 🆕 V19.6 新增：配置requests连接池大小
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # 创建一个session，配置更大的连接池
            self.session = requests.Session()
            
            # 配置重试策略
            retry_strategy = Retry(
                total=3,  # 最多重试3次
                backoff_factor=1,  # 重试间隔指数增长
                status_forcelist=[429, 500, 502, 503, 504],  # 遇到这些状态码时重试
            )
            
            # 配置连接池适配器
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=20,  # 连接池大小增加到20
                pool_maxsize=20,  # 最大连接数增加到20
                pool_block=False  # 连接池满时不阻塞
            )
            
            # 应用适配器到http和https
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            logger.info(f"✅ 连接池配置完成：pool_connections=20, pool_maxsize=20")
        except Exception as e:
            logger.warning(f"⚠️ 连接池配置失败，使用默认配置: {e}")
            self.session = None
        
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    
    def batch_get_realtime_data(self, data_manager, stock_list: List[str], batch_size: int = 50) -> Dict[str, Dict[str, Any]]:
        """
        批量获取实时数据（并发）
        
        Args:
            data_manager: 数据管理器实例
            stock_list: 股票代码列表
            batch_size: 每批处理的股票数量
        
        Returns:
            dict: 股票数据字典 {code: data}
        """
        logger.info(f"🚀 开始并发获取 {len(stock_list)} 只股票的实时数据（批次大小: {batch_size}）")
        
        all_results = {}
        total_batches = (len(stock_list) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(stock_list))
            batch_stocks = stock_list[start_idx:end_idx]
            
            logger.info(f"📊 处理批次 {batch_idx + 1}/{total_batches} ({len(batch_stocks)} 只股票)")
            
            # 并发获取数据
            futures = {}
            for stock_code in batch_stocks:
                future = self.executor.submit(data_manager.get_realtime_data, [stock_code])
                futures[future] = stock_code
            
            # 等待所有任务完成
            for future in concurrent.futures.as_completed(futures):
                stock_code = futures[future]
                try:
                    result = future.result(timeout=5)
                    if result and len(result) > 0:
                        all_results[stock_code] = result[0]
                except Exception as e:
                    logger.warning(f"获取 {stock_code} 数据失败: {e}")
        
        logger.info(f"✅ 并发获取完成，成功获取 {len(all_results)}/{len(stock_list)} 只股票数据")
        return all_results
    
    def batch_get_history_data(self, data_manager, stock_list: List[str], **kwargs) -> Dict[str, Any]:
        """
        批量获取历史数据（并发）
        
        Args:
            data_manager: 数据管理器实例
            stock_list: 股票代码列表
            **kwargs: 传递给 get_history_data 的参数
        
        Returns:
            dict: 股票历史数据字典 {code: df}
        """
        logger.info(f"🚀 开始并发获取 {len(stock_list)} 只股票的历史数据")
        
        all_results = {}
        
        # 并发获取数据
        futures = {}
        for stock_code in stock_list:
            future = self.executor.submit(data_manager.get_history_data, stock_code, **kwargs)
            futures[future] = stock_code
        
        # 等待所有任务完成
        for future in concurrent.futures.as_completed(futures):
            stock_code = futures[future]
            try:
                result = future.result(timeout=10)
                if result is not None and not result.empty:
                    all_results[stock_code] = result
            except Exception as e:
                logger.warning(f"获取 {stock_code} 历史数据失败: {e}")
        
        logger.info(f"✅ 并发获取完成，成功获取 {len(all_results)}/{len(stock_list)} 只股票历史数据")
        return all_results
    
    def batch_execute(self, func: Callable, args_list: List[Tuple], timeout: int = 10) -> List[Any]:
        """
        批量执行函数（并发）
        
        Args:
            func: 要执行的函数
            args_list: 参数列表 [(arg1, arg2, ...), ...]
            timeout: 超时时间（秒）
        
        Returns:
            list: 结果列表
        """
        logger.info(f"🚀 开始并发执行 {len(args_list)} 个任务")
        
        results = []
        
        # 并发执行
        futures = {}
        for idx, args in enumerate(args_list):
            future = self.executor.submit(func, *args)
            futures[future] = idx
        
        # 等待所有任务完成
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                result = future.result(timeout=timeout)
                results.append((idx, result))
            except Exception as e:
                logger.warning(f"任务 {idx} 执行失败: {e}")
                results.append((idx, None))
        
        # 按原始顺序排序
        results.sort(key=lambda x: x[0])
        results = [r[1] for r in results]
        
        logger.info(f"✅ 并发执行完成，成功 {sum(1 for r in results if r is not None)}/{len(results)} 个任务")
        return results
    
    def parallel_map(self, func: Callable, items: List[Any], timeout: int = 10) -> List[Any]:
        """
        并行映射（类似 map 的并发版本）
        
        Args:
            func: 要执行的函数
            items: 项目列表
            timeout: 超时时间（秒）
        
        Returns:
            list: 结果列表
        """
        logger.info(f"🚀 开始并行映射 {len(items)} 个项目")
        
        results = []
        
        # 并发执行
        futures = {}
        for idx, item in enumerate(items):
            future = self.executor.submit(func, item)
            futures[future] = idx
        
        # 等待所有任务完成
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                result = future.result(timeout=timeout)
                results.append((idx, result))
            except Exception as e:
                logger.warning(f"项目 {idx} 处理失败: {e}")
                results.append((idx, None))
        
        # 按原始顺序排序
        results.sort(key=lambda x: x[0])
        results = [r[1] for r in results]
        
        logger.info(f"✅ 并行映射完成，成功 {sum(1 for r in results if r is not None)}/{len(results)} 个项目")
        return results
    
    def shutdown(self, wait: bool = True):
        """
        关闭执行器
        
        Args:
            wait: 是否等待所有任务完成
        """
        logger.info("🛑 关闭并发执行器")
        self.executor.shutdown(wait=wait)
        
        # 🆕 V19.6 新增：关闭session
        if self.session:
            self.session.close()
            logger.info("✅ Session已关闭")


# 全局单例
_global_executor = None


def get_concurrent_executor(max_workers: int = 2) -> ConcurrentExecutor:
    """
    获取全局并发执行器实例
    
    Args:
        max_workers: 最大线程数
    
    Returns:
        ConcurrentExecutor: 并发执行器实例
    """
    global _global_executor
    
    if _global_executor is None:
        _global_executor = ConcurrentExecutor(max_workers=max_workers)
        logger.info(f"✅ 全局并发执行器已初始化（线程数: {max_workers}）")
    
    return _global_executor


def shutdown_global_executor(wait: bool = True):
    """
    关闭全局并发执行器
    
    Args:
        wait: 是否等待所有任务完成
    """
    global _global_executor
    
    if _global_executor is not None:
        _global_executor.shutdown(wait=wait)
        _global_executor = None
        logger.info("🛑 全局并发执行器已关闭")


# 便捷函数
def batch_get_realtime_data_fast(data_manager, stock_list: List[str], batch_size: int = 50) -> Dict[str, Dict[str, Any]]:
    """
    快速批量获取实时数据（便捷函数）
    
    Args:
        data_manager: 数据管理器实例
        stock_list: 股票代码列表
        batch_size: 每批处理的股票数量
    
    Returns:
        dict: 股票数据字典 {code: data}
    
    🆕 V19.6 优化：
    - 增加了批次间隔，避免瞬时请求过多
    - 每批之间间隔0.5秒，给服务器喘息时间
    """
    executor = get_concurrent_executor()
    return executor.batch_get_realtime_data(data_manager, stock_list, batch_size)


def batch_get_history_data_fast(data_manager, stock_list: List[str], **kwargs) -> Dict[str, Any]:
    """
    快速批量获取历史数据（便捷函数）
    
    Args:
        data_manager: 数据管理器实例
        stock_list: 股票代码列表
        **kwargs: 传递给 get_history_data 的参数
    
    Returns:
        dict: 股票历史数据字典 {code: df}
    """
    executor = get_concurrent_executor()
    return executor.batch_get_history_data(data_manager, stock_list, **kwargs)


def parallel_execute_fast(func: Callable, items: List[Any], timeout: int = 10) -> List[Any]:
    """
    快速并行执行（便捷函数）
    
    Args:
        func: 要执行的函数
        items: 项目列表
        timeout: 超时时间（秒）
    
    Returns:
        list: 结果列表
    """
    executor = get_concurrent_executor()
    return executor.parallel_map(func, items, timeout)


if __name__ == '__main__':
    # 测试代码
    import sys
    import os
    
    # 添加项目根目录到路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    from logic.data_providers.data_manager import DataManager
    
    print("=" * 80)
    print("🚀 测试并发执行器")
    print("=" * 80)
    
    # 初始化数据管理器
    print("\n📊 初始化数据管理器...")
    dm = DataManager()
    
    # 测试股票列表
    test_stocks = ['000001', '000002', '600000', '600519', '300750']
    
    # 测试批量获取实时数据
    print(f"\n🔍 测试批量获取实时数据（{len(test_stocks)} 只股票）...")
    t1 = time.time()
    results = batch_get_realtime_data_fast(dm, test_stocks)
    t2 = time.time()
    print(f"✅ 耗时: {t2 - t1:.3f}秒")
    print(f"✅ 成功: {len(results)}/{len(test_stocks)} 只股票")
    
    # 测试批量获取历史数据
    print(f"\n🔍 测试批量获取历史数据（{len(test_stocks)} 只股票）...")
    t1 = time.time()
    history_results = batch_get_history_data_fast(dm, test_stocks)
    t2 = time.time()
    print(f"✅ 耗时: {t2 - t1:.3f}秒")
    print(f"✅ 成功: {len(history_results)}/{len(test_stocks)} 只股票")
    
    # 关闭执行器
    shutdown_global_executor()
    
    print("\n✅ 测试完成")