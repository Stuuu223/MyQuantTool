"""
测试参数优化性能

测试遗传算法的性能
"""

import time
import os
from logic.parameter_optimizer import ParameterOptimizer
from logic.backtest_engine import BacktestEngine, dragon_strategy_backtest


def test_genetic_algorithm_performance():
    """测试遗传算法性能"""
    print("=" * 60)
    print("测试遗传算法性能")
    print("=" * 60)
    
    # 获取初始 CPU 使用率（Windows）
    try:
        import psutil
        cpu_before = psutil.cpu_percent(interval=1)
        print(f"初始 CPU 使用率: {cpu_before}%")
        use_psutil = True
    except ImportError:
        cpu_before = 0
        print(f"初始 CPU 使用率: 未知（psutil 未安装）")
        use_psutil = False
    
    # 创建参数优化器
    optimizer = ParameterOptimizer()
    
    # 定义参数范围
    param_ranges = {
        'min_score': (50, 90),
        'min_change_pct': (5.0, 15.0),
        'min_volume_ratio': (1.0, 5.0)
    }
    
    # 测试股票列表（使用少量股票）
    stock_codes = ['300773', '300427', '300758']
    
    # 测试日期范围（使用短时间范围）
    start_date = '2024-01-01'
    end_date = '2024-01-31'
    
    print(f"\n开始遗传算法优化...")
    print(f"参数范围: {param_ranges}")
    print(f"股票数量: {len(stock_codes)}")
    print(f"日期范围: {start_date} 至 {end_date}")
    
    # 记录开始时间
    start_time = time.time()
    
    # 运行遗传算法
    result = optimizer.genetic_algorithm(
        strategy_func=dragon_strategy_backtest,
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        param_ranges=param_ranges,
        objective='sharpe_ratio',
        population_size=10,  # 使用较小的种群
        generations=5,       # 使用较少的代数
        mutation_rate=0.1
    )
    
    # 记录结束时间
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # 获取结束 CPU 使用率
    if use_psutil:
        cpu_after = psutil.cpu_percent(interval=1)
        print(f"\n结束 CPU 使用率: {cpu_after}%")
    else:
        cpu_after = 0
        print(f"\n结束 CPU 使用率: 未知（psutil 未安装）")
    
    # 输出结果
    print(f"\n{'=' * 60}")
    print(f"性能测试结果")
    print(f"{'=' * 60}")
    print(f"总耗时: {elapsed_time:.2f} 秒")
    print(f"CPU 使用率: {cpu_before}% -> {cpu_after}%")
    print(f"平均 CPU 使用率: {(cpu_before + cpu_after) / 2:.2f}%")
    
    if result['best_params']:
        print(f"\n最佳参数: {result['best_params']}")
        print(f"最佳得分: {result['best_score']:.4f}")
    
    if result['best_metrics']:
        print(f"\n最佳指标:")
        for key, value in result['best_metrics'].items():
            print(f"  {key}: {value}")
    
    # 性能评估
    print(f"\n{'=' * 60}")
    print(f"性能评估")
    print(f"{'=' * 60}")
    
    if elapsed_time < 60:
        print(f"✅ 性能良好：耗时 {elapsed_time:.2f} 秒")
    elif elapsed_time < 300:
        print(f"⚠️  性能一般：耗时 {elapsed_time:.2f} 秒")
    else:
        print(f"❌ 性能较差：耗时 {elapsed_time:.2f} 秒")
    
    if cpu_after > 80:
        print(f"⚠️  CPU 使用率高：{cpu_after}%")
        print(f"建议：考虑使用 ProcessPool 替代 ThreadPool")
    elif cpu_after > 50:
        print(f"⚠️  CPU 使用率中等：{cpu_after}%")
        print(f"建议：可以继续使用 ThreadPool")
    else:
        print(f"✅ CPU 使用率正常：{cpu_after}%")
    
    return {
        'elapsed_time': elapsed_time,
        'cpu_before': cpu_before,
        'cpu_after': cpu_after,
        'best_score': result.get('best_score', 0)
    }


if __name__ == '__main__':
    test_genetic_algorithm_performance()