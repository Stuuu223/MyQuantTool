import pandas as pd

# 加载数据
df = pd.read_csv('data/minute_data_hot/300912.SZ_1m.csv')
df['date'] = df['time_str'].str[:10]
daily_df = df.groupby('date').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
})

# 计算MA5
daily_df['ma5'] = daily_df['close'].rolling(5).mean()
daily_df['prev_close'] = daily_df['close'].shift(1)
daily_df['prev_ma5'] = daily_df['ma5'].shift(1)

# 生成信号
daily_df['signal'] = ((daily_df['close'] > daily_df['ma5']) & (daily_df['prev_close'] < daily_df['prev_ma5'])).astype(int)

# 查找信号
signal_rows = daily_df[daily_df['signal'] == 1]
print(f"发现 {len(signal_rows)} 个买入信号:")
for idx, row in signal_rows.iterrows():
    print(f"  日期: {idx}, 收盘: {row['close']:.2f}, MA5: {row['ma5']:.2f}")

# 模拟交易
if len(signal_rows) > 0:
    signal_idx = signal_rows.index[0]
    buy_idx = list(daily_df.index).index(signal_idx) + 1
    sell_idx = buy_idx + 3  # 持有3天
    
    print(f"\n交易模拟:")
    print(f"  信号日期: {signal_idx}")
    print(f"  买入日期: {daily_df.index[buy_idx]}, 价格: {daily_df.iloc[buy_idx]['open']:.2f}")
    print(f"  卖出日期: {daily_df.index[sell_idx]}, 价格: {daily_df.iloc[sell_idx]['close']:.2f}")
    
    buy_price = daily_df.iloc[buy_idx]['open']
    sell_price = daily_df.iloc[sell_idx]['close']
    pnl = (sell_price - buy_price) / buy_price * 100
    
    print(f"  收益率: {pnl:.2f}%")
    print(f"  持仓天数: {sell_idx - buy_idx} 天")