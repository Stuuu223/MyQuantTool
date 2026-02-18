#!/usr/bin/env python3
"""
HALFWAY 10×15缩样本验证（V3引擎）

目标：
1. 验证HALFWAY策略在V3引擎下逻辑闭合
2. 粗测性能（10只×15天耗时）
3. 生成JSON供A/B对比

股票：前10只（test_10_stocks_halfway.txt）
时间：2025-11-14 至 2025-12-04（15个交易日）
"""

import sys
import json
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backtest.run_single_holding_t1_backtest import (
    SingleHoldingT1Backtester, HalfwaySignalAdapter, CostModel
)
from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy

def run_halfway_10x15():
    """运行HALFWAY 10×15回测"""
    
    print("=" * 60)
    print("🚀 HALFWAY 10×15 缩样本验证")
    print("=" * 60)
    
    # 记录开始时间
    start_time = time.time()
    
    # 加载股票列表（前10只）
    stock_file = Path(__file__).resolve().parent / "test_10_stocks_halfway.txt"
    with open(stock_file, 'r') as f:
        stock_codes = [line.strip() for line in f if line.strip()]
    
    print(f"📊 股票池: {len(stock_codes)} 只")
    print(f"   {stock_codes}")
    
    # 创建HALFWAY策略（V17: 放宽参数以产生信号）
    print("\n⚙️  初始化HALFWAY策略（放宽参数版）...")
    strategy_params = {
        'volatility_threshold': 0.02,      # 从0.03放宽到0.02
        'volume_surge': 1.2,                # 从1.5放宽到1.2
        'breakout_strength': 0.005          # 从0.01放宽到0.005
    }
    halfway_strategy = HalfwayTickStrategy(strategy_params)
    signal_generator = HalfwaySignalAdapter(halfway_strategy)
    
    # 创建回测器（与TRIVIAL相同的成本假设）
    print("💰 成本假设: 万0.85 + 印花税 + 10bp滑点")
    backtester = SingleHoldingT1Backtester(
        initial_capital=100000.0,
        position_size=0.5,
        stop_loss_pct=0.02,
        take_profit_pct=0.05,
        max_holding_minutes=120,
        signal_generator=signal_generator,
        cost_model=CostModel()
    )
    
    # 运行回测（15个交易日）
    start_date = '2025-11-14'
    end_date = '2025-12-04'
    print(f"\n📅 回测区间: {start_date} 至 {end_date} (15个交易日)")
    print("⏳ 开始回测...")
    
    result = backtester.run_backtest(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date
    )
    
    # 计算耗时
    elapsed_time = time.time() - start_time
    print(f"\n⏱️  总耗时: {elapsed_time:.1f}秒")
    
    # 保存结果
    output_path = Path(__file__).resolve().parent / "backtest" / "results" / "t1_halfway_10stocks_15days_v3.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    result_dict = result.to_dict()
    result_dict['performance_metrics'] = {
        'elapsed_time_seconds': elapsed_time,
        'stocks_count': len(stock_codes),
        'trading_days': 15,
        'time_per_stock_day': elapsed_time / (len(stock_codes) * 15)
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n💾 结果已保存: {output_path}")
    
    # 关键结果摘要
    print("\n" + "=" * 60)
    print("📊 回测结果摘要")
    print("=" * 60)
    print(f"Raw Signals: {result_dict['three_layer_stats']['raw_signals']['total']} 笔")
    print(f"  - 开仓: {result_dict['three_layer_stats']['raw_signals']['open_signals']} 笔")
    print(f"Executable Signals: {result_dict['three_layer_stats']['executable_signals']['total']} 笔")
    print(f"Executed Trades: {result_dict['trade_layer']['total_trades']} 笔")
    print(f"胜率: {result_dict['trade_layer']['win_rate']*100:.1f}%")
    print(f"净盈亏: {result_dict['trade_layer']['total_pnl']:.2f} 元")
    print(f"最大回撤: {result_dict['trade_layer']['max_drawdown']*100:.2f}%")
    print(f"最终权益: {result_dict['trade_layer']['final_equity']:.2f} 元")
    print("=" * 60)
    
    # V17 Debug: 显示策略诊断计数器
    print("\n🔍 策略诊断计数器 (Debug)")
    print("=" * 60)
    print(f"【HalfwayTickStrategy内部计数】")
    print(f"  ticks_seen: {halfway_strategy.debug_counters['ticks_seen']}")
    print(f"  history_insufficient: {halfway_strategy.debug_counters['history_insufficient']}")
    print(f"  volatility_pass: {halfway_strategy.debug_counters['volatility_pass']}")
    print(f"  volume_surge_pass: {halfway_strategy.debug_counters['volume_surge_pass']}")
    print(f"  breakout_pass: {halfway_strategy.debug_counters['breakout_pass']}")
    print(f"  all_conditions_pass: {halfway_strategy.debug_counters['all_conditions_pass']}")
    print(f"  raw_signals_generated: {halfway_strategy.debug_counters['raw_signals_generated']}")
    print(f"\n【HalfwaySignalAdapter计数】")
    print(f"  adapter_calls: {signal_generator.debug_counters['adapter_calls']}")
    print(f"  strategy_signals_received: {signal_generator.debug_counters['strategy_signals_received']}")
    
    # 诊断结论
    print("\n📋 诊断分析")
    print("=" * 60)
    if halfway_strategy.debug_counters['ticks_seen'] == 0:
        print("❌ 策略未看到任何tick（数据问题）")
    elif halfway_strategy.debug_counters['history_insufficient'] > halfway_strategy.debug_counters['ticks_seen'] * 0.9:
        print("❌ 绝大多数tick历史数据不足（min_history_points设置过高）")
    elif halfway_strategy.debug_counters['volatility_pass'] == 0:
        print(f"❌ 无tick通过波动率阈值（当前: {strategy_params['volatility_threshold']}, 建议降低）")
    elif halfway_strategy.debug_counters['volume_surge_pass'] == 0:
        print(f"❌ 无tick通过量能阈值（当前: {strategy_params['volume_surge']}, 建议降低）")
    elif halfway_strategy.debug_counters['breakout_pass'] == 0:
        print(f"❌ 无tick通过突破阈值（当前: {strategy_params['breakout_strength']}, 建议降低）")
    elif halfway_strategy.debug_counters['all_conditions_pass'] == 0:
        print("❌ 无tick同时通过三个条件（组合条件过于严格）")
    elif halfway_strategy.debug_counters['raw_signals_generated'] == 0:
        print("❌ 条件通过但未生成信号（platform_detector问题）")
    elif signal_generator.debug_counters['strategy_signals_received'] == 0:
        print("❌ 策略生成信号但适配器未收到（adapter过滤问题）")
    else:
        print("✅ 策略各阶段正常，信号被T+1/成本约束拦截")
    print("=" * 60)
    
    return result, elapsed_time

if __name__ == "__main__":
    try:
        result, elapsed_time = run_halfway_10x15()
        print("\n✅ HALFWAY 10×15 验证完成")
    except Exception as e:
        print(f"\n❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
