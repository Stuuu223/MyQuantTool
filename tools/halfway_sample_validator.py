#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建主观半路样本日标记工具
根据CTO建议，标记典型的半路起爆日
"""

import json
from pathlib import Path


def create_sample_dates():
    """
    创建主观认定的半路样本日期
    """
    sample_dates = {
        # 300997 欢乐家 - 假设的典型半路日
        "300997.SZ": [
            "20260129",  # 假设的典型半路日
            "20260202",  # 假设的典型半路日
            "20260205",  # 假设的典型半路日
        ],
        # 300986 志特新材 - 假设的典型半路日
        "300986.SZ": [
            "20260120",  # 假设的典型半路日
            "20260125",  # 假设的典型半路日
            "20260210",  # 假设的典型半路日
        ],
        # 603697 有友食品 - 假设的典型半路日
        "603697.SH": [
            "20260115",  # 假设的典型半路日
            "20260122",  # 假设的典型半路日
            "20260208",  # 假设的典型半路日
        ]
    }
    
    # 保存到配置文件
    output_path = Path(__file__).parent.parent / "config" / "halfway_sample_dates.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample_dates, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 主观半路样本日期已保存到: {output_path}")
    print("📋 样本日期内容:")
    for stock, dates in sample_dates.items():
        print(f"   {stock}: {dates}")
    
    return sample_dates


def run_on_sample_dates():
    """
    在样本日期上运行Halfway策略
    """
    import sys
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    
    from tools.per_day_tick_runner import PerDayTickRunner
    from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy
    
    # 加载样本日期
    config_path = Path(__file__).parent.parent / "config" / "halfway_sample_dates.json"
    if not config_path.exists():
        print("⚠️  样本日期配置文件不存在，先创建")
        create_sample_dates()
    
    with open(config_path, 'r', encoding='utf-8') as f:
        sample_dates = json.load(f)
    
    print(f"\n📊 在样本日期上运行Halfway策略")
    print("=" * 80)
    
    # 使用相对宽松的参数
    params = {
        'volatility_threshold': 0.04,      # 波动率阈值
        'volume_surge': 1.4,              # 量能放大倍数
        'breakout_strength': 0.008,       # 突破强度
        'min_history_points': 40          # 最小历史点数
    }
    
    total_signals = 0
    results = []
    
    for stock, dates in sample_dates.items():
        print(f"\n📈 测试股票: {stock}")
        print("-" * 40)
        
        for date in dates:
            print(f"  📅 {date} ", end="", flush=True)
            
            try:
                strategy = HalfwayTickStrategy(params)
                runner = PerDayTickRunner(
                    stock_code=stock,
                    trade_date=date,
                    strategy=strategy
                )
                
                signals = runner.run()
                stats = runner.get_statistics()
                
                signal_count = stats['total_signals']
                total_signals += signal_count
                
                result = {
                    'stock': stock,
                    'date': date,
                    'signal_count': signal_count,
                    'win_rate_5min': stats['win_rate']['5min'],
                    'avg_return_5min': stats['avg_return']['5min']
                }
                results.append(result)
                
                if signal_count > 0:
                    print(f"✅ ({signal_count}个信号)")
                else:
                    print("❌")
                    
            except Exception as e:
                print(f"❌ (错误: {str(e)[:20]}...)")
                result = {
                    'stock': stock,
                    'date': date,
                    'signal_count': 0,
                    'win_rate_5min': 0,
                    'avg_return_5min': 0,
                    'error': str(e)
                }
                results.append(result)
    
    print(f"\n📊 总体统计:")
    print(f"   总测试次数: {len(results)}")
    print(f"   总信号数: {total_signals}")
    print(f"   有信号比例: {len([r for r in results if r['signal_count'] > 0])/len(results):.2%}")
    
    # 输出详细结果
    print(f"\n📋 详细结果:")
    for result in results:
        if result.get('error'):
            print(f"   {result['stock']} {result['date']}: ERROR - {result['error'][:50]}")
        else:
            print(f"   {result['stock']} {result['date']}: {result['signal_count']}个信号, "
                  f"5分钟胜率{result['win_rate_5min']:.2%}, "
                  f"5分钟平均收益{result['avg_return_5min']:.4f}")
    
    print(f"\n🎯 结论:")
    if total_signals == 0:
        print(f"   ❌ 当前参数下，在标记的{len(results)}个交易日中未检测到任何Halfway信号")
        print(f"   可能需要：")
        print(f"   - 进一步调整参数")
        print(f"   - 重新审视半路形态定义")
        print(f"   - 验证Tick数据质量")
    else:
        print(f"   ✅ 检测到{total_signals}个信号，策略在部分标记日期上有效")
        print(f"   平均每只股票检测到{total_signals/len(sample_dates):.1f}个信号")
    
    return results


if __name__ == "__main__":
    print("🎯 主观半路样本日标记与验证工具")
    print("=" * 80)
    
    # 创建样本日期
    sample_dates = create_sample_dates()
    
    # 运行验证
    results = run_on_sample_dates()
    
    print(f"\n✅ 工具执行完成")
    print("=" * 80)
