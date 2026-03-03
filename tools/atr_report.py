"""ATR阈值研究报告 - 多日对比"""
import pandas as pd
from pathlib import Path

# 读取三天数据
data_dir = Path('E:/MyQuantTool/data')
df_0228 = pd.read_csv(data_dir / 'atr_probe_20260228.csv')
df_0302 = pd.read_csv(data_dir / 'atr_probe_20260302.csv')
df_0303 = pd.read_csv(data_dir / 'atr_probe_20260303.csv')

print('=' * 70)
print('ATR THRESHOLD RESEARCH REPORT - Multi-Day Comparison')
print('=' * 70)

print('\n【分位数分布对比】')
print('分位    | 0228(周五) | 0302      | 0303(周一)')
print('-' * 50)
for p in [50, 75, 90, 95, 99]:
    v1 = df_0228['atr_ratio'].quantile(p/100)
    v2 = df_0302['atr_ratio'].quantile(p/100)
    v3 = df_0303['atr_ratio'].quantile(p/100)
    print(f'{p:3d}分位  | {v1:.2f}x     | {v2:.2f}x    | {v3:.2f}x')

print('\n【涨停股ATR倍数对比】')
print('日期   | 数量 | 均值  | 中位数')
print('-' * 40)
for name, df in [('0228', df_0228), ('0302', df_0302), ('0303', df_0303)]:
    zt = df[df['change_pct'] >= 9.8]
    print(f'{name}  | {len(zt):3d}  | {zt["atr_ratio"].mean():.2f}x | {zt["atr_ratio"].median():.2f}x')

print('\n【跌停股ATR倍数对比】')
print('日期   | 数量 | 均值  | 中位数')
print('-' * 40)
for name, df in [('0228', df_0228), ('0302', df_0302), ('0303', df_0303)]:
    dt = df[df['change_pct'] <= -9.8]
    if len(dt) > 0:
        print(f'{name}  | {len(dt):3d}  | {dt["atr_ratio"].mean():.2f}x | {dt["atr_ratio"].median():.2f}x')
    else:
        print(f'{name}  |   0  | N/A   | N/A')

print('\n【不同阈值筛选数量对比】')
print('阈值    | 0228  | 0302  | 0303')
print('-' * 40)
for t in [1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]:
    c1 = len(df_0228[df_0228['atr_ratio'] >= t])
    c2 = len(df_0302[df_0302['atr_ratio'] >= t])
    c3 = len(df_0303[df_0303['atr_ratio'] >= t])
    print(f'>= {t:.1f}x | {c1:4d}  | {c2:4d}  | {c3:4d}')

print('\n【石油板块三日对比】')
oil = ['600028.SH', '601857.SH', '000096.SZ', '600339.SH', '601808.SH', '000554.SZ']
print('股票     | 0228(ratio/涨跌)  | 0302(ratio/涨跌)  | 0303(ratio/涨跌)')
print('-' * 75)
for stock in oil:
    r1 = df_0228[df_0228['stock'] == stock]
    r2 = df_0302[df_0302['stock'] == stock]
    r3 = df_0303[df_0303['stock'] == stock]
    a1 = r1['atr_ratio'].values[0] if len(r1) > 0 else 0
    a2 = r2['atr_ratio'].values[0] if len(r2) > 0 else 0
    a3 = r3['atr_ratio'].values[0] if len(r3) > 0 else 0
    c1 = r1['change_pct'].values[0] if len(r1) > 0 else 0
    c2 = r2['change_pct'].values[0] if len(r2) > 0 else 0
    c3 = r3['change_pct'].values[0] if len(r3) > 0 else 0
    v1 = r1['vol_ratio'].values[0] if len(r1) > 0 else 0
    v2 = r2['vol_ratio'].values[0] if len(r2) > 0 else 0
    v3 = r3['vol_ratio'].values[0] if len(r3) > 0 else 0
    print(f'{stock} | {a1:.2f}x/{c1:+.1f}%/{v1:.1f}x   | {a2:.2f}x/{c2:+.1f}%/{v2:.1f}x   | {a3:.2f}x/{c3:+.1f}%/{v3:.1f}x')

print('\n' + '=' * 70)
print('【结论与建议】')
print('=' * 70)

# 计算三天的涨停股ATR均值
all_zt_atr = []
for df in [df_0228, df_0302, df_0303]:
    zt = df[df['change_pct'] >= 9.8]
    all_zt_atr.extend(zt['atr_ratio'].tolist())

import numpy as np
zt_mean = np.mean(all_zt_atr)
zt_median = np.median(all_zt_atr)

print(f'''
1. 涨停股ATR倍数统计（三天汇总）:
   - 均值: {zt_mean:.2f}x
   - 中位数: {zt_median:.2f}x

2. 石油板块预兆验证:
   - 周五(0228): ATR倍数0.47-0.90x，无异常
   - 周一(0303): ATR倍数0.62-2.85x，600028/000096明显异动
   - 结论: 周五无预兆，周一盘中引爆

3. 阈值建议:
   - 保守(捕获涨停股中位数): atr_ratio >= {zt_median:.1f}x
   - 激进(捕获涨停股均值):   atr_ratio >= {zt_mean:.1f}x
''')
