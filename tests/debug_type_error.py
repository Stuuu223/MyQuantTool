import sys
import traceback
from logic.backtest.time_machine_engine import TimeMachineEngine

engine = TimeMachineEngine()

# 测试单个股票
test_stock = '000021.SZ'
test_date = '20251231'

print(f"测试股票: {test_stock}, 日期: {test_date}")

try:
    result = engine._calculate_morning_score(test_stock, test_date)
    print(f"结果: {result}")
except Exception as e:
    print(f"错误类型: {type(e).__name__}")
    print(f"错误消息: {str(e)}")
    traceback.print_exc()