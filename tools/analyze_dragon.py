"""
志特新材六连板物理分析
CTO V108: 高位承接厚度探测器验证
"""
from xtquant import xtdata
import pandas as pd
import sys
import os

# 添加项目根目录
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.physics_collider import calc_energy_center_of_mass

xtdata.connect()

print('=' * 70)
print('CTO V108 高位承接厚度探测器验证')
print('志特新材 300986.SZ 首板 20260105')
print('=' * 70)
print()

# 首板参数
stock_code = '300986.SZ'
date = '20260105'
pre_close = 11.18
limit_price = 13.42

print(f'昨收: {pre_close}, 涨停价: {limit_price} (涨幅20%)')
print()

# 计算能量重心
print('【能量重心分析】')
energy = calc_energy_center_of_mass(stock_code, date, limit_price, pre_close)

print(f'能量重心价格: {energy["energy_center_price"]:.2f}元')
print(f'能量重心位置: 涨停价的 {energy["energy_center_ratio"]*100:.1f}% 处')
print()

print('【价格区间成交分布】')
for zone, pct in energy['zone_distribution'].items():
    bar = '█' * int(pct / 2)
    print(f'  {zone}: {pct:>5.1f}% {bar}')
print()

print(f'高位区(+10%~涨停)成交占比: {energy["high_altitude_ratio"]:.1f}%')
print(f'低位区(水下~+5%)成交占比: {energy["low_altitude_ratio"]:.1f}%')
print()

print('=' * 70)
print('【CTO判定结果】')
print('=' * 70)
print(f'类型: {energy["sustain_type"]}')
print(f'说明: {energy["dominant_zone"]}')
print()

if energy['sustain_type'] == '高位强承接':
    print('结论: 这不是"偷袭"！这是教科书级别的【高位强承接，真空破防】！')
    print()
    print('物理解释:')
    print('  - 能量重心在涨停价80%以上，说明主力全天在高位做功')
    print('  - 高位区成交占比超过50%，抛压被充分洗盘')
    print('  - 尾盘封板时只需极小资金，因为阻力已被消耗殆尽')
    print('  - 这是【强势信号】，预示次日强溢价和连板预期！')
else:
    print(f'注意: 需要进一步分析，当前判定为 {energy["sustain_type"]}')

print()
print('=' * 70)
print('【详细Tick分析】')
print('=' * 70)

tick = xtdata.get_local_data([], ['300986.SZ'], period='tick', start_time='20260105', end_time='20260105')
df = tick['300986.SZ']

# 过滤有效价格
valid = df[df['lastPrice'] > 0]
open_price = valid['lastPrice'].iloc[0]

print(f'开盘价: {open_price:.2f}')
print(f'开盘涨幅: {(open_price/pre_close - 1)*100:.1f}%')
print()

# 按时间段统计
df['delta_amount'] = df['amount'].diff().fillna(0)

print('【分时成交分布】')
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

print(f'  09:25-09:30(竞价): {(auction["delta_amount"].sum())/1e8:.2f}亿')
print(f'  09:30-10:00: {(morning1["delta_amount"].sum())/1e8:.2f}亿')
print(f'  10:00-11:30: {(morning2["delta_amount"].sum())/1e8:.2f}亿')
print(f'  13:00-14:00: {(afternoon1["delta_amount"].sum())/1e8:.2f}亿')
print(f'  14:00-15:00: {(afternoon2["delta_amount"].sum())/1e8:.2f}亿')
print()

print('【关键价格节点】')
for target in [12.0, 12.5, 13.0, 13.42]:
    hit = df[df['lastPrice'] >= target].head(1)
    if len(hit) > 0:
        t = str(hit.index[0])
        if len(t) >= 12:
            time_str = f'{t[8:10]}:{t[10:12]}'
        else:
            time_str = t
        change_pct = (target / pre_close - 1) * 100
        print(f'  首次触及{target:.2f}({change_pct:+.1f}%): {time_str}')