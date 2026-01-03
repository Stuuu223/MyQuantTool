import pandas as pd
import numpy as np
from logic.algo import QuantAlgo

# 创建测试数据
np.random.seed(42)
dates = pd.date_range(start='2024-01-01', periods=100, freq='D')

# 模拟箱体震荡（前60天在100-110之间震荡，后40天突破）
prices = []
for i in range(100):
    if i < 60:
        # 箱体震荡
        price = 105 + np.random.randn() * 2
    else:
        # 向上突破
        price = 110 + (i - 60) * 0.5 + np.random.randn() * 2
    prices.append(price)

df = pd.DataFrame({
    'date': dates,
    'open': [p + np.random.randn() for p in prices],
    'high': [p + abs(np.random.randn()) for p in prices],
    'low': [p - abs(np.random.randn()) for p in prices],
    'close': prices,
    'volume': np.random.randint(100000, 500000, 100)
})

# 测试箱体检测
box_pattern = QuantAlgo.detect_box_pattern(df)

print("=" * 50)
print("箱体震荡检测结果")
print("=" * 50)
print(f"是否在箱体内: {box_pattern['is_box']}")
print(f"消息: {box_pattern['message']}")

if box_pattern['is_box']:
    print(f"箱体上沿: {box_pattern['box_high']}")
    print(f"箱体下沿: {box_pattern['box_low']}")
    print(f"箱体宽度: {box_pattern['box_width']}")
    print(f"当前位置: {box_pattern['position_pct']}%")
elif box_pattern.get('is_breakout_up'):
    print(f"向上突破！突破价: {box_pattern['box_high']}")
    print(f"突破幅度: {box_pattern['breakout_pct']}%")
elif box_pattern.get('is_breakout_down'):
    print(f"向下突破！跌破价: {box_pattern['box_low']}")
    print(f"突破幅度: {box_pattern['breakout_pct']}%")

print("=" * 50)
print("测试完成！")