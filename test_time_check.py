"""
测试时间判断逻辑
"""

from datetime import datetime

now = datetime.now()
current_time = now.time()
print(f"当前时间: {current_time}")

# 竞价时间判断
auction_start = current_time.replace(hour=9, minute=25, second=0, microsecond=0)
auction_end = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
is_auction_time = auction_start <= current_time < auction_end

print(f"竞价开始: {auction_start}")
print(f"竞价结束: {auction_end}")
print(f"是否竞价期间: {is_auction_time}")

# 市场状态判断
morning_open = "09:30:00"
morning_close = "11:30:00"
afternoon_open = "13:00:00"
afternoon_close = "15:00:00"

current_time_str = current_time.strftime('%H:%M:%S')
print(f"\n当前时间字符串: {current_time_str}")

if morning_open <= current_time_str <= morning_close:
    market_status = "上午交易中"
elif afternoon_open <= current_time_str <= afternoon_close:
    market_status = "下午交易中"
elif "09:15:00" <= current_time_str < morning_open:
    market_status = "集合竞价"
elif current_time_str < morning_open:
    market_status = "开盘前"
elif morning_close < current_time_str < afternoon_open:
    market_status = "午休"
elif current_time_str > afternoon_close:
    market_status = "收盘后"
else:
    market_status = "未知"

print(f"市场状态: {market_status}")