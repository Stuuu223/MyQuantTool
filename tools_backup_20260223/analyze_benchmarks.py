#!/usr/bin/env python3
"""分析黄金标杆数据并反推阈值"""

import json

with open('data/golden_benchmarks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('='*70)
print('【黄金标杆深度分析】')
print('='*70)

ratios_85 = [d['ratio_60d_85th'] for d in data]
ratios_75 = [d['ratio_60d_75th'] for d in data]
sustains = [d['sustain_ratio'] for d in data]
amounts = [d['amount_5min']/10000 for d in data]  # 万元

print(f'\n1. Ratio分布 (85分位基准):')
print(f'   最小: {min(ratios_85):.2f} (志特新材)')
print(f'   最大: {max(ratios_85):.2f} (网宿科技)')
print(f'   平均: {sum(ratios_85)/len(ratios_85):.2f}')
print(f'   建议阈值: > {min(ratios_85)*0.8:.1f} (取最小值的80%)')

print(f'\n2. Ratio分布 (75分位基准):')
print(f'   最小: {min(ratios_75):.2f}')
print(f'   最大: {max(ratios_75):.2f}')
print(f'   平均: {sum(ratios_75)/len(ratios_75):.2f}')

print(f'\n3. Sustain问题警示:')
print(f'   当前值: {[f"{s:.2f}" for s in sustains]}')
print(f'   注意: Sustain=1.6-2.3 远低于预期的 50+')
print(f'   可能原因: Sustain计算逻辑错误或应该用flow而非volume')

print(f'\n4. 资金分布:')
print(f'   最小: {min(amounts):.1f}万 (志特新材)')
print(f'   最大: {max(amounts):.1f}万 (网宿科技)')
print(f'   平均: {sum(amounts)/len(amounts):.1f}万')

print(f'\n5. 建议阈值配置:')
print(f'   Ratio(85分位): > 3.5 (覆盖全部标杆)')
print(f'   绝对资金: > 400万 (排除流动性不足)')
print(f'   Sustain: 待重新计算')

# 详细表格
print(f'\n6. 标杆详细数据:')
print(f'{"股票":<15} {"Ratio85":<10} {"Ratio75":<10} {"Sustain":<10} {"资金(万)":<10}')
print('-'*60)
for d in data:
    print(f"{d['stock_code']:<15} {d['ratio_60d_85th']:<10.2f} {d['ratio_60d_75th']:<10.2f} "
          f"{d['sustain_ratio']:<10.2f} {d['amount_5min']/10000:<10.1f}")
