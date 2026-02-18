#!/usr/bin/env python3
"""
涨跌停压力测试（CTO要求）

测试场景：
1. 10cm主板股票触及涨停/跌停
2. 20cm创业板股票触及涨停/跌停

验证：_check_limit_price是否正确阻断交易
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backtest.run_single_holding_t1_backtest import (
    SingleHoldingT1Backtester, CostModel
)

def test_limit_check():
    """测试涨跌停检查逻辑"""
    print("=" * 60)
    print("🧪 涨跌停压力测试")
    print("=" * 60)
    
    # 创建回测器
    backtester = SingleHoldingT1Backtester(
        initial_capital=100000,
        cost_model=CostModel()
    )
    
    # 测试1: 10cm主板股票
    print("\n1️⃣ 测试10cm主板股票（000001.SZ）")
    stock_code = "000001.SZ"
    prev_close = 10.0
    limit_up = prev_close * 1.10  # 11.0
    limit_down = prev_close * 0.90  # 9.0
    
    # 创建带pre_close的tick对象
    class MockTick:
        def __init__(self, pre_close):
            self.pre_close = pre_close
    
    tick = MockTick(prev_close)
    
    # 测试买入（涨停价*0.995应被阻断）
    test_price = limit_up * 0.995  # 10.945
    can_buy = backtester._check_limit_price(stock_code, test_price, tick, 'buy')
    print(f"   买入价{test_price:.2f}（涨停价{limit_up}*0.995）")
    print(f"   买入检查: {'✅ 通过' if can_buy else '🚫 阻断'}")
    assert not can_buy, "接近涨停价买入应该被阻断"
    
    # 测试低于涨停价1%（应通过）
    test_price = limit_up * 0.99  # 10.89
    can_buy = backtester._check_limit_price(stock_code, test_price, tick, 'buy')
    print(f"   买入价{test_price:.2f}（低于涨停1%）")
    print(f"   买入检查: {'✅ 通过' if can_buy else '🚫 阻断'}")
    assert can_buy, "低于涨停价应该可以通过"
    
    # 测试卖出（跌停价*1.005应被阻断）
    test_price = limit_down * 1.005  # 9.045
    can_sell = backtester._check_limit_price(stock_code, test_price, tick, 'sell')
    print(f"   卖出价{test_price:.2f}（跌停价{limit_down}*1.005）")
    print(f"   卖出检查: {'✅ 通过' if can_sell else '🚫 阻断'}")
    assert not can_sell, "接近跌停价卖出应该被阻断"
    
    # 测试2: 20cm创业板股票
    print("\n2️⃣ 测试20cm创业板股票（300001.SZ）")
    stock_code = "300001.SZ"
    prev_close = 20.0
    limit_up = prev_close * 1.20  # 24.0
    limit_down = prev_close * 0.80  # 16.0
    tick = MockTick(prev_close)
    
    test_price = limit_up * 0.995  # 23.88
    can_buy = backtester._check_limit_price(stock_code, test_price, tick, 'buy')
    print(f"   买入价{test_price:.2f}（涨停价{limit_up}*0.995）")
    print(f"   买入检查: {'✅ 通过' if can_buy else '🚫 阻断'}")
    assert not can_buy, "20cm接近涨停价买入应该被阻断"
    
    test_price = limit_down * 1.005  # 16.08
    can_sell = backtester._check_limit_price(stock_code, test_price, tick, 'sell')
    print(f"   卖出价{test_price:.2f}（跌停价{limit_down}*1.005）")
    print(f"   卖出检查: {'✅ 通过' if can_sell else '🚫 阻断'}")
    assert not can_sell, "20cm接近跌停价卖出应该被阻断"
    
    # 测试3: 科创板
    print("\n3️⃣ 测试20cm科创板股票（688001.SH）")
    stock_code = "688001.SH"
    tick = MockTick(20.0)  # 科创板pre_close
    test_price = 24.0 * 0.995  # 23.88
    can_buy = backtester._check_limit_price(stock_code, test_price, tick, 'buy')
    print(f"   买入价{test_price:.2f}（20cm涨停边界）")
    print(f"   买入检查: {'✅ 通过' if can_buy else '🚫 阻断'}")
    assert not can_buy, "科创板涨停边界买入应该被阻断"
    
    print("\n" + "=" * 60)
    print("✅ 所有涨跌停压力测试通过！")
    print("=" * 60)

def test_limit_pct_detection():
    """测试涨跌停幅度识别"""
    print("\n" + "=" * 60)
    print("🧪 涨跌停幅度识别测试")
    print("=" * 60)
    
    backtester = SingleHoldingT1Backtester()
    
    test_cases = [
        ("000001.SZ", 0.10, "主板"),
        ("300001.SZ", 0.20, "创业板300开头"),
        ("301001.SZ", 0.20, "创业板301开头"),
        ("688001.SH", 0.20, "科创板"),
        ("830001.BJ", 0.30, "北交所"),
    ]
    
    for stock_code, expected_pct, desc in test_cases:
        pct = backtester._get_limit_pct(stock_code)
        status = "✅" if pct == expected_pct else "❌"
        print(f"   {status} {desc}: {stock_code} -> {pct*100:.0f}%")
        assert pct == expected_pct, f"{stock_code} 应该为{expected_pct*100:.0f}%，但得到{pct*100:.0f}%"
    
    print("\n✅ 涨跌停幅度识别测试通过！")

if __name__ == "__main__":
    test_limit_check()
    test_limit_pct_detection()
    print("\n🎉 所有测试通过！涨跌停检查功能正常。")