"""
测试单个日期的tick数据加载
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from backtest.run_wanzhu_behavior_replay import load_tick_data

# 测试已知有数据的股票和日期
stock_code = "000547.SZ"
test_date = "2026-01-22"

print(f"测试 {stock_code} {test_date}")
print("="*60)

tick_df = load_tick_data(stock_code, test_date)

if tick_df is None:
    print("❌ 加载失败")
else:
    print(f"✅ 加载成功")
    print(f"数据形状: {tick_df.shape}")
    print(f"列名: {tick_df.columns.tolist()}")
    print(f"时间范围: {tick_df['timestamp'].min()} 到 {tick_df['timestamp'].max()}")
    print(f"数据示例:")
    print(tick_df.head(3))
    
    # 检查时间列的数据类型
    print(f"\n时间列数据类型: {tick_df['time'].dtype}")
    print(f"时间列示例值: {tick_df['time'].iloc[:3].tolist()}")
    print(f"时间戳列示例值: {tick_df['timestamp'].iloc[:3].tolist()}")