from logic.backtest.time_machine_engine import TimeMachineEngine

print("=" * 80)
print("开始回测测试")
print("=" * 80)

engine = TimeMachineEngine()
result = engine.run_daily_backtest('20251230')

print(f"回测完成")
print(f"状态: {result.get('status', 'unknown')}")
print(f"有效股票数: {result.get('valid_stocks', 0)}")
print(f"Top20数量: {len(result.get('top20', []))}")

if result.get('top20'):
    print(f"\nTop 5 股票:")
    for i, stock in enumerate(result['top20'][:5], 1):
        print(f"  {i}. {stock}")