"""
志特新材六连板物理分析
"""
from xtquant import xtdata
import pandas as pd

xtdata.connect()

# 先分析首板完整走势
print('=== 首板0105完整走势分析 ===')
print()

tick = xtdata.get_local_data([], ['300986.SZ'], period='tick', start_time='20260105', end_time='20260105')
df = tick['300986.SZ']

# 过滤有效价格
valid = df[df['lastPrice'] > 0]

open_price = valid['lastPrice'].iloc[0]
pre_close = 11.18
limit_price = 13.42

print(f'昨收: {pre_close}, 涨停价: {limit_price} (涨幅20%)')
print(f'开盘价: {open_price:.2f}')
print(f'开盘涨幅: {(open_price/pre_close - 1)*100:.1f}%')
print()

# 按时间段统计
df['delta_amount'] = df['amount'].diff().fillna(0)

# 09:25-09:30 竞价
auction = df[(df.index >= '20260105092500') & (df.index < '20260105093000')]
# 09:30-10:00
morning1 = df[(df.index >= '20260105093000') & (df.index < '20260105100000')]
# 10:00-11:30
morning2 = df[(df.index >= '20260105100000') & (df.index < '20260105113000')]
# 13:00-14:00
afternoon1 = df[(df.index >= '20260105130000') & (df.index < '20260105140000')]
# 14:00-15:00
afternoon2 = df[(df.index >= '20260105140000') & (df.index < '20260105150000')]

print('=== 分时成交分布 ===')
print(f'09:25-09:30(竞价): 成交{(auction["delta_amount"].sum())/1e8:.2f}亿')
print(f'09:30-10:00: 成交{(morning1["delta_amount"].sum())/1e8:.2f}亿')
print(f'10:00-11:30: 成交{(morning2["delta_amount"].sum())/1e8:.2f}亿')
print(f'13:00-14:00: 成交{(afternoon1["delta_amount"].sum())/1e8:.2f}亿')
print(f'14:00-15:00: 成交{(afternoon2["delta_amount"].sum())/1e8:.2f}亿')

print()
print('=== 关键价格节点 ===')
# 找首次触及各价格的时间
for target in [12.0, 12.5, 13.0, 13.42]:
    hit = df[df['lastPrice'] >= target].head(1)
    if len(hit) > 0:
        t = str(hit.index[0])
        if len(t) >= 12:
            time_str = f'{t[8:10]}:{t[10:12]}'
        else:
            time_str = t
        print(f'首次触及{target:.2f}: {time_str}')

print()
print('=== 价格区间成交分布 ===')
valid_price = df[df['lastPrice'] > 0].copy()
valid_price['delta'] = valid_price['amount'].diff().fillna(0)

bins = [(11.0, 11.5), (11.5, 12.0), (12.0, 12.5), (12.5, 13.0), (13.0, 13.42)]
for low, high in bins:
    mask = (valid_price['lastPrice'] >= low) & (valid_price['lastPrice'] < high)
    amt = valid_price[mask]['delta'].sum() / 1e8
    print(f'{low:.1f}-{high:.2f}: {amt:.2f}亿')

# 涨停价成交
limit_mask = valid_price['lastPrice'] >= 13.42
limit_amt = valid_price[limit_mask]['delta'].sum() / 1e8
print(f'涨停价13.42: {limit_amt:.2f}亿')

print()
print('=' * 60)
print()

# 六连板总结
print('=== 志特新材六连板物理分析 ===')
print()

dates = ['20260105', '20260106', '20260107', '20260108', '20260109', '20260112']

results = []
for date in dates:
    # 获取日K
    daily = xtdata.get_local_data([], ['300986.SZ'], period='1d', start_time=date, end_time=date)
    df_d = daily['300986.SZ']
    
    pre_close = df_d['preClose'].iloc[0]
    limit_price = round(pre_close * 1.2, 2)
    total_amount = df_d['amount'].iloc[0]
    total_volume = df_d['volume'].iloc[0]
    
    # 获取Tick
    tick = xtdata.get_local_data([], ['300986.SZ'], period='tick', start_time=date, end_time=date)
    df_t = tick['300986.SZ']
    
    # 找首次触及涨停价
    exact = df_t[df_t['lastPrice'] == limit_price]
    if len(exact) > 0:
        first_limit_idx = exact.index[0]
        amount_at_limit = df_t.loc[first_limit_idx, 'amount']
        board_amount = total_amount - amount_at_limit
        
        # 计算封板时间
        first_time_str = str(first_limit_idx)
        if len(first_time_str) >= 12:
            hour = int(first_time_str[8:10])
            minute = int(first_time_str[10:12])
        else:
            hour = 9
            minute = 30
        seal_time = f'{hour:02d}:{minute:02d}'
        
        # 计算封板时长（到15:00）
        minutes_to_close = (15 - hour) * 60 - minute
        if hour >= 15:
            minutes_to_close = 0
    else:
        board_amount = 0
        seal_time = '未封板'
        minutes_to_close = 0
    
    board_ratio = board_amount / total_amount * 100 if total_amount > 0 else 0
    
    results.append({
        'date': date,
        'pre_close': pre_close,
        'limit_price': limit_price,
        'total_amount': total_amount / 1e8,
        'board_amount': board_amount / 1e8,
        'board_ratio': board_ratio,
        'seal_time': seal_time,
        'seal_minutes': minutes_to_close,
        'total_volume': total_volume
    })
    
    print(f'{date}: 昨收{pre_close:.2f} 涨停价{limit_price:.2f}')
    print(f'  封板时间: {seal_time} (距收盘{minutes_to_close}分钟)')
    print(f'  总成交额: {total_amount/1e8:.2f}亿')
    print(f'  板上成交: {board_amount/1e8:.2f}亿 ({board_ratio:.1f}%)')
    print()

print('=== 物理特征总结 ===')
print('日期      封板时间  封板时长  总成交   板上成交  占比')
print('-' * 60)
for r in results:
    print(f"{r['date']}  {r['seal_time']:>8}  {r['seal_minutes']:>5}分钟  {r['total_amount']:>6.2f}亿  {r['board_amount']:>6.2f}亿  {r['board_ratio']:>5.1f}%")

print()
print('=== 惯性衰竭分析 ===')
# 计算动量维持率
for i in range(1, len(results)):
    prev_board = results[i-1]['board_amount']
    curr_total = results[i]['total_amount']
    momentum_rate = curr_total / prev_board if prev_board > 0 else 0
    print(f"{results[i]['date']}: 动量维持率 = {curr_total:.2f}亿 / {prev_board:.2f}亿 = {momentum_rate:.2f}x")
