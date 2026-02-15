"""
性能基准测试工具 - 测试执行效率、内存使用、缓存率
"""

import time
import psutil
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Any, Optional, Tuple
import logging
import json
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    operation: str
    duration_ms: float
    memory_used_mb: float
    memory_peak_mb: float
    success: bool
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkStats:
    """基准统计数据"""
    operation: str
    count: int
    duration_mean_ms: float
    duration_median_ms: float
    duration_min_ms: float
    duration_max_ms: float
    duration_std_ms: float
    memory_mean_mb: float
    memory_peak_mb: float
    success_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceBenchmark:
    """性能基准测试管理器"""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.process = psutil.Process()
    
    def measure(self, operation: str, func: Callable, *args, **kwargs) -> BenchmarkResult:
        """测量操作性能"""
        success = False
        error = None
        memory_used = 0
        memory_peak = 0
        duration = 0
        
        try:
            # 记录初始内存
            initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            
            # 执行操作
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000  # ms
            
            # 记录终止内存
            final_memory = self.process.memory_info().rss / 1024 / 1024
            memory_used = final_memory - initial_memory
            memory_peak = final_memory
            
            success = True
        except Exception as e:
            error = str(e)
            logger.error(f"Benchmark failed for {operation}: {e}")
        
        result_obj = BenchmarkResult(
            operation=operation,
            duration_ms=duration,
            memory_used_mb=memory_used,
            memory_peak_mb=memory_peak,
            success=success,
            error=error
        )
        
        self.results.append(result_obj)
        return result_obj
    
    def get_stats(self, operation: Optional[str] = None) -> List[BenchmarkStats]:
        """获取统计数据"""
        if operation:
            results = [r for r in self.results if r.operation == operation]
        else:
            results = self.results
        
        if not results:
            return []
        
        # 按操作分组
        grouped = {}
        for r in results:
            if r.operation not in grouped:
                grouped[r.operation] = []
            grouped[r.operation].append(r)
        
        stats_list = []
        for op, rs in grouped.items():
            durations = [r.duration_ms for r in rs]
            memories = [r.memory_used_mb for r in rs]
            success_count = sum(1 for r in rs if r.success)
            
            stats = BenchmarkStats(
                operation=op,
                count=len(rs),
                duration_mean_ms=np.mean(durations),
                duration_median_ms=np.median(durations),
                duration_min_ms=np.min(durations),
                duration_max_ms=np.max(durations),
                duration_std_ms=np.std(durations),
                memory_mean_mb=np.mean(memories),
                memory_peak_mb=np.max(memories),
                success_rate=success_count / len(rs)
            )
            stats_list.append(stats)
        
        return stats_list
    
    def report(self, operation: Optional[str] = None) -> pd.DataFrame:
        """生成报告"""
        stats_list = self.get_stats(operation)
        if not stats_list:
            return pd.DataFrame()
        
        data = [s.to_dict() for s in stats_list]
        return pd.DataFrame(data)
    
    def export_json(self, filepath: str) -> None:
        """导出为 JSON"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'results': [r.to_dict() for r in self.results],
            'stats': [s.to_dict() for s in self.get_stats()]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def clear(self) -> None:
        """清除结果"""
        self.results.clear()


class CacheBenchmark:
    """缓存性能测试"""
    
    def __init__(self, adapter):
        self.adapter = adapter
        self.benchmark = PerformanceBenchmark()
    
    def test_cache_hit_rate(self, iterations: int = 100) -> Dict[str, float]:
        """测试缓存命中率"""
        operations = [
            ('market_overview', lambda: self.adapter.get_market_overview()),
            ('stock_quote', lambda: self.adapter.get_stock_quote('600519')),
            ('sector', lambda: self.adapter.get_sector_performance()),
        ]
        
        results = {}
        for op_name, op_func in operations:
            cache_hits = 0
            total_time_with_cache = 0
            
            # 第一次调用(缓存未存在)
            start = time.time()
            op_func()
            first_call_ms = (time.time() - start) * 1000
            
            # 后续调用(回帐缓存)
            for i in range(iterations - 1):
                start = time.time()
                result = op_func()
                elapsed_ms = (time.time() - start) * 1000
                total_time_with_cache += elapsed_ms
                
                # 定义缓存命中: 执行时间 < 先前执行时间的 10%
                if elapsed_ms < first_call_ms * 0.1:
                    cache_hits += 1
            
            hit_rate = cache_hits / (iterations - 1)
            avg_cache_time = total_time_with_cache / (iterations - 1)
            
            results[op_name] = {
                'hit_rate': hit_rate,
                'first_call_ms': first_call_ms,
                'avg_cache_ms': avg_cache_time,
                'speedup': first_call_ms / avg_cache_time if avg_cache_time > 0 else float('inf')
            }
        
        return results
    
    def test_multi_source_failover(self) -> Dict[str, Any]:
        """测试多数据源降级"""
        results = {}
        
        # 测试正常情形
        start = time.time()
        result1 = self.adapter.get_market_overview()
        time1 = time.time() - start
        results['primary_source'] = {
            'success': result1 is not None,
            'time_ms': time1 * 1000
        }
        
        # 处理总时间
        total_start = time.time()
        for _ in range(10):
            self.adapter.get_market_overview()
        total_time = time.time() - total_start
        
        results['batch_performance'] = {
            'iterations': 10,
            'total_time_ms': total_time * 1000,
            'avg_time_ms': (total_time / 10) * 1000
        }
        
        return results


class IntegrationBenchmark:
    """全流程集成测试"""
    
    def __init__(self, adapter):
        self.adapter = adapter
        self.benchmark = PerformanceBenchmark()
    
    def test_full_dashboard_load(self) -> Dict[str, Any]:
        """测试完整仓表板加载时间"""
        def load_dashboard():
            data = {}
            data['market'] = self.adapter.get_market_overview()
            data['quotes'] = [
                self.adapter.get_stock_quote(f'60{i:04d}')
                for i in range(1, 6)
            ]
            data['limit_ups'] = self.adapter.get_limit_up_stocks(50)
            data['sector'] = self.adapter.get_sector_performance()
            return data
        
        # 测试 5 次加载
        results = []
        for i in range(5):
            result = self.benchmark.measure(
                f'full_load_{i+1}',
                load_dashboard
            )
            results.append(result)
        
        durations = [r.duration_ms for r in results]
        return {
            'iterations': 5,
            'mean_ms': np.mean(durations),
            'median_ms': np.median(durations),
            'min_ms': np.min(durations),
            'max_ms': np.max(durations),
            'std_ms': np.std(durations)
        }
    
    def test_data_consistency(self) -> Dict[str, Any]:
        """测试数据一致性"""
        # 从正式数据源载入 3 次
        results = []
        for i in range(3):
            market = self.adapter.get_market_overview()
            if market:
                results.append({
                    'sh': market.get('sh', {}).get('price'),
                    'timestamp': market.get('timestamp')
                })
        
        return {
            'consistent': len(set(r['sh'] for r in results)) <= 1,
            'samples': results
        }


def run_full_benchmark(adapter, output_file: str = 'benchmark_report.json') -> None:
    """运行完整基准测试"""
    print("\n" + "="*50)
    print("[PERFORMANCE] MyQuantTool 性能基准测试")
    print("="*50)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'cache_performance': None,
        'failover_performance': None,
        'integration_performance': None,
        'data_consistency': None
    }
    
    # 1. 缓存性能测试
    print("\n[1] 测试缓存性能...")
    cache_bench = CacheBenchmark(adapter)
    results['cache_performance'] = cache_bench.test_cache_hit_rate(iterations=50)
    
    for op, stats in results['cache_performance'].items():
        print(f"  {op}:")
        print(f"    - 命中率: {stats['hit_rate']:.1%}")
        print(f"    - 首次执行: {stats['first_call_ms']:.2f}ms")
        print(f"    - 按中时: {stats['avg_cache_ms']:.4f}ms")
        print(f"    - 加速比: {stats['speedup']:.1f}x")
    
    # 2. 故障转移性能测试
    print("\n[2] 测试多源降级...")
    results['failover_performance'] = cache_bench.test_multi_source_failover()
    print(f"  一级数据源: {results['failover_performance']['primary_source']}")
    print(f"  批量性能: {results['failover_performance']['batch_performance']}")
    
    # 3. 完整流程集成测试
    print("\n[3] 测试完整流程...")
    integration_bench = IntegrationBenchmark(adapter)
    results['integration_performance'] = integration_bench.test_full_dashboard_load()
    print(f"  平均加载时间: {results['integration_performance']['mean_ms']:.2f}ms")
    print(f"  最大加载时间: {results['integration_performance']['max_ms']:.2f}ms")
    
    # 4. 数据一致性测试
    print("\n[4] 测试数据一致性...")
    results['data_consistency'] = integration_bench.test_data_consistency()
    print(f"  一致性: {results['data_consistency']['consistent']}")
    
    # 保存结果
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\n" + "="*50)
    print(f基准测试完成！结果保存到: {output_file}")
    print("="*50 + "\n")
    
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from logic.data.multi_source_adapter import get_adapter
    
    adapter = get_adapter()
    run_full_benchmark(adapter)