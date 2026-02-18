#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分层抽样生成80只代表性样本
基于auction_export.csv（5190只全市场竞价股票）
"""

import pandas as pd
import numpy as np

# 读取auction_export.csv
df = pd.read_csv('data/auction/auction_export.csv')
print(f'原始数据: {len(df)}只股票')

# 1. 定义可交易母体过滤
# 价格过滤: 3-100元
df = df[(df['竞价价格'] >= 3) & (df['竞价价格'] <= 100)]
# 成交额过滤: 至少100万（避免僵尸股）
df = df[df['成交额'] >= 1000000]

print(f'过滤后母体: {len(df)}只股票')

# 2. 添加分层标签
# 交易所标签
def get_exchange(code):
    if code.startswith('6'):
        return 'SH'  # 沪主板
    elif code.startswith('00'):
        return 'SZ_MAIN'  # 深主板
    elif code.startswith('30'):
        return 'CYB'  # 创业板
    elif code.startswith('68'):
        return 'KCB'  # 科创板
    elif code.startswith('8') or code.startswith('4'):
        return 'EXCLUDE'  # 北交所/新三板，排除
    else:
        return 'OTHER'

df['交易所'] = df['股票代码'].apply(get_exchange)
df = df[df['交易所'] != 'EXCLUDE']

# 价格分层
df['价格层'] = pd.cut(df['竞价价格'], bins=[0, 10, 30, 60, 100], 
                     labels=['低价', '中低价', '中高价', '高价'])

# 成交额分层（三分位）
df['成交额层'] = pd.qcut(df['成交额'], q=3, labels=['低流动性', '中流动性', '高流动性'])

# 竞价涨跌幅分层
df['涨跌幅'] = (df['竞价价格'] / df['昨收价格'] - 1) * 100
df['涨跌层'] = pd.cut(df['涨跌幅'], bins=[-np.inf, -1, 3, np.inf], 
                     labels=['低开', '平开', '高开'])

print(f'\n分层统计:')
print(f'交易所分布:')
print(df['交易所'].value_counts())
print(f'\n价格层分布:')
print(df['价格层'].value_counts())
print(f'\n成交额层分布:')
print(df['成交额层'].value_counts())

# 3. 分层抽样
np.random.seed(42)  # 固定随机种子，保证可复现

target_total = 80
exchange_counts = df['交易所'].value_counts()
total_stocks = len(df)

sampled = []
for exchange in ['SH', 'SZ_MAIN', 'CYB', 'KCB']:
    exchange_df = df[df['交易所'] == exchange]
    if len(exchange_df) == 0:
        continue
    # 按比例分配名额，至少2只
    target_count = max(2, int(target_total * len(exchange_df) / total_stocks))
    
    if len(exchange_df) > target_count:
        # 在每个交易所内，按成交额分层抽样
        exchange_sample = exchange_df.groupby('成交额层', group_keys=False).apply(
            lambda x: x.sample(min(len(x), max(1, target_count // 3)))
        )
        # 如果还不够，再随机补充
        if len(exchange_sample) < target_count:
            remaining = target_count - len(exchange_sample)
            excluded = exchange_df.index.difference(exchange_sample.index)
            additional = exchange_df.loc[excluded].sample(min(remaining, len(excluded)))
            exchange_sample = pd.concat([exchange_sample, additional])
        # 如果超了，随机删减
        elif len(exchange_sample) > target_count:
            exchange_sample = exchange_sample.sample(target_count)
    else:
        exchange_sample = exchange_df
    
    sampled.append(exchange_sample)
    print(f'{exchange}: 母体{len(exchange_df)}只, 抽样{len(exchange_sample)}只')

final_sample = pd.concat(sampled)

# 如果总数不对，调整
if len(final_sample) > target_total:
    final_sample = final_sample.sample(target_total, random_state=42)
elif len(final_sample) < target_total:
    # 补充
    excluded = df.index.difference(final_sample.index)
    additional = df.loc[excluded].sample(min(target_total - len(final_sample), len(excluded)), random_state=42)
    final_sample = pd.concat([final_sample, additional])

print(f'\n最终样本: {len(final_sample)}只股票')
print(f'\n样本交易所分布:')
print(final_sample['交易所'].value_counts())
print(f'\n样本价格统计:')
print(f'  最低价: {final_sample["竞价价格"].min():.2f}')
print(f'  最高价: {final_sample["竞价价格"].max():.2f}')
print(f'  均价: {final_sample["竞价价格"].mean():.2f}')
print(f'\n样本成交额统计:')
print(f'  最低: {final_sample["成交额"].min()/1e6:.2f}百万')
print(f'  最高: {final_sample["成交额"].max()/1e6:.2f}百万')
print(f'  平均: {final_sample["成交额"].mean()/1e6:.2f}百万')

# 保存样本
sample_codes = final_sample['股票代码'].tolist()
with open('test_80_stocks_stratified.txt', 'w') as f:
    for code in sample_codes:
        f.write(code + '\n')

print(f'\n样本已保存到 test_80_stocks_stratified.txt')
print(f'前20只: {sample_codes[:20]}')
