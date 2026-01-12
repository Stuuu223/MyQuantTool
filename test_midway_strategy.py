# -*- coding: utf-8 -*-
"""测试半路战法功能"""
import sys
import pandas as pd
from logic.midway_strategy import MidwayStrategyAnalyzer
from logic.data_manager import DataManager

def test_midway_strategy():
    """测试半路战法"""
    print("=" * 60)
    print("测试半路战法功能")
    print("=" * 60)

    # 初始化数据管理器
    db = DataManager()
    analyzer = MidwayStrategyAnalyzer(lookback_days=30)

    # 测试几只热门股票
    test_stocks = [
        ('600519', '贵州茅台'),
        ('000858', '五粮液'),
        ('600036', '招商银行'),
        ('601318', '中国平安'),
        ('000001', '平安银行')
    ]

    print(f"\n测试 {len(test_stocks)} 只股票...")

    signals = []
    for code, name in test_stocks:
        try:
            print(f"\n{'='*40}")
            print(f"分析: {name} ({code})")
            print(f"{'='*40}")

            # 获取数据
            df = db.get_history_data(code)
            if df is None or df.empty:
                print(f"[FAIL] 无法获取数据")
                continue

            print(f"[OK] 获取到 {len(df)} 行数据")
            print(f"[OK] 最新收盘价: {df.iloc[-1]['close']:.2f}")
            print(f"[OK] 最新成交量: {df.iloc[-1]['volume']:,.0f}")

            # 分析半路战法
            signal = analyzer.analyze_midway_opportunity(df, code, name)

            if signal:
                signals.append(signal)
                print(f"\n[SUCCESS] 发现半路战法信号!")
                print(f"   - 入场价: {signal.entry_price:.2f}")
                print(f"   - 止损价: {signal.stop_loss:.2f}")
                print(f"   - 目标价: {signal.target_price:.2f}")
                print(f"   - 信号强度: {signal.signal_strength:.2f}")
                print(f"   - 风险等级: {signal.risk_level}")
                print(f"   - 理由: {', '.join(signal.reasons)}")
            else:
                print(f"\n[NO SIGNAL] 未发现半路战法信号")

        except Exception as e:
            print(f"[ERROR] 分析失败: {e}")
            import traceback
            traceback.print_exc()

    # 总结
    print(f"\n{'='*60}")
    print(f"测试完成: 共扫描 {len(test_stocks)} 只股票，发现 {len(signals)} 个信号")
    print(f"{'='*60}")

    if signals:
        print(f"\n发现的信号:")
        for i, signal in enumerate(signals, 1):
            print(f"\n{i}. {signal.stock_name} ({signal.stock_code})")
            print(f"   信号强度: {signal.signal_strength:.2f}")
            print(f"   入场价: {signal.entry_price:.2f}")
            print(f"   目标价: {signal.target_price:.2f}")

if __name__ == "__main__":
    test_midway_strategy()