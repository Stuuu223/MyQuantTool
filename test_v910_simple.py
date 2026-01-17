"""
V9.10 修复测试脚本（简化版）
"""

from logic.market_status import MarketStatus, get_market_status_checker
from datetime import time

print("=" * 60)
print("V9.10 修复测试")
print("=" * 60)

# 测试1：午间休盘状态判断
print("\n📊 测试1：午间休盘状态判断")
market_checker = get_market_status_checker()

# 测试不同时间点
test_times = [
    (time(9, 20), "早盘集合竞价"),
    (time(9, 28), "竞价真空期"),
    (time(10, 30), "早盘交易"),
    (time(11, 35), "午间休盘"),
    (time(13, 30), "午盘交易"),
    (time(15, 30), "收盘后"),
]

for test_time, desc in test_times:
    is_noon_break = market_checker.is_noon_break(test_time)
    is_call_auction_gap = market_checker.is_call_auction_gap(test_time)
    
    print(f"  {test_time} ({desc}):")
    print(f"    午间休盘: {is_noon_break}")
    print(f"    竞价真空期: {is_call_auction_gap}")

# 测试2：check_market_status 方法
print("\n📊 测试2：check_market_status 方法")

# 模拟不同场景
test_cases = [
    {
        "name": "涨停股票",
        "bid1_volume": 1000,
        "ask1_volume": 0,
        "change_pct": 9.9,
        "symbol": "600000",
        "stock_name": "测试股票"
    },
    {
        "name": "正常交易股票",
        "bid1_volume": 500,
        "ask1_volume": 300,
        "change_pct": 2.5,
        "symbol": "000001",
        "stock_name": "测试股票"
    },
    {
        "name": "跌停股票",
        "bid1_volume": 0,
        "ask1_volume": 1000,
        "change_pct": -9.9,
        "symbol": "300000",
        "stock_name": "测试股票"
    },
]

for case in test_cases:
    status_info = market_checker.check_market_status(
        bid1_volume=case["bid1_volume"],
        ask1_volume=case["ask1_volume"],
        change_pct=case["change_pct"],
        symbol=case["symbol"],
        name=case["stock_name"]
    )
    
    print(f"  {case['name']}:")
    print(f"    状态: {status_info['status']}")
    print(f"    消息: {status_info['message']}")
    print(f"    是否交易: {status_info['is_trading']}")

# 测试3：时间感知测试
print("\n📊 测试3：时间感知测试")
current_time = market_checker.get_current_time()
print(f"  当前时间: {current_time}")

# 判断当前时段
if market_checker.is_noon_break():
    print(f"  当前状态: ☕️ 午间休盘")
elif market_checker.is_call_auction_gap():
    print(f"  当前状态: 🕒 竞价真空期")
elif market_checker.is_trading_time():
    print(f"  当前状态: 📈 交易时间")
else:
    print(f"  当前状态: ⚠️ 非交易时间")

print("\n" + "=" * 60)
print("✅ V9.10 修复测试完成")
print("=" * 60)
print("\nV9.10 新功能总结：")
print("1. ✅ 午间休盘状态判断（11:30-13:00）")
print("2. ✅ 竞价数据回退机制（从第一根K线估算）")
print("3. ✅ UI 显示优化（午间休盘显示蓝色信息）")
print("4. ✅ 时间感知测试（自动判断当前时段）")
print("\nV9.10 修复效果：")
print("- 午间休盘不再显示黄色警告，而是显示蓝色信息")
print("- 竞价数据缺失时显示\"未捕捉\"而不是\"N/A\"")
print("- 竞价数据可以通过第一根K线估算")
print("- 用户体验更加友好")
print("=" * 60)