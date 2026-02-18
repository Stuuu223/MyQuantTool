#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V12样本池标签增强脚本
========================

为80只样本补充基础标签（P0任务）：
1. 弹性标签（20cm/10cm）- 代码前缀识别
2. 价格层级（低价/中低价/中高价/高价）- auction数据
3. 竞价强度（强势高开/温和高开/平开/低开）- auction数据
4. 行业/板块标签 - Tushare数据

输出：
- scripts/samples/test_80_stocks_v12_enriched.csv（带完整标签）

Author: AI Project Director
Date: 2026-02-18
"""

import pandas as pd
import tushare as ts
from datetime import datetime
from pathlib import Path


def get_elasticity_label(code: str) -> str:
    """弹性标签：识别20cm/10cm"""
    if code.startswith('300') or code.startswith('301'):
        return '20cm创业板'
    elif code.startswith('688'):
        return '20cm科创板'
    else:
        return '10cm主板'


def get_price_level(price: float) -> str:
    """价格层级"""
    if price < 10:
        return '低价'
    elif price < 30:
        return '中低价'
    elif price < 60:
        return '中高价'
    else:
        return '高价'


def get_auction_strength(pct_change: float) -> str:
    """竞价强度"""
    if pct_change > 5:
        return '强势高开'
    elif pct_change > 1:
        return '温和高开'
    elif pct_change > -1:
        return '平开'
    else:
        return '低开'


def enrich_stock_tags(
    sample_file: str = 'scripts/samples/test_80_stocks_v12_standard.txt',
    auction_file: str = 'data/auction/auction_export.csv',
    output_file: str = 'scripts/samples/test_80_stocks_v12_enriched.csv'
) -> pd.DataFrame:
    """
    为样本池添加基础标签
    
    Args:
        sample_file: 样本池文件路径
        auction_file: 竞价数据文件路径
        output_file: 输出文件路径
        
    Returns:
        带标签的DataFrame
    """
    print('=' * 60)
    print('V12样本池标签增强')
    print('=' * 60)
    
    # 1. 读取80只样本
    print(f'\n[1/4] 读取样本池...')
    with open(sample_file, 'r') as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    print(f'  样本数量: {len(lines)}只')
    print(f'  前5只: {lines[:5]}')
    
    # 2. 读取auction数据
    print(f'\n[2/4] 读取auction数据...')
    auction_df = pd.read_csv(auction_file)
    sample_df = auction_df[auction_df['股票代码'].isin(lines)].copy()
    print(f'  匹配到{len(sample_df)}只股票')
    
    # 3. 添加基础标签（从auction数据）
    print(f'\n[3/4] 添加基础标签...')
    
    # 弹性标签
    sample_df['弹性标签'] = sample_df['股票代码'].apply(get_elasticity_label)
    
    # 价格层级
    sample_df['价格层级'] = sample_df['竞价价格'].apply(get_price_level)
    
    # 竞价强度
    sample_df['涨跌幅'] = (sample_df['竞价价格'] / sample_df['昨收价格'] - 1) * 100
    sample_df['竞价强度'] = sample_df['涨跌幅'].apply(get_auction_strength)
    
    print('  ✅ 基础标签完成')
    
    # 4. 从Tushare获取行业标签
    print(f'\n[4/4] 从Tushare获取行业标签...')
    
    TUSHARE_TOKEN = '1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b'
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    
    # 获取所有股票基础信息
    all_stocks = pro.stock_basic(
        exchange='', 
        list_status='L', 
        fields='ts_code,name,industry,market'
    )
    
    # 匹配80只样本（创建映射表）
    codes_80 = [c.split('.')[0] for c in lines]
    
    # 将Tushare代码格式转为项目格式（添加后缀）
    def add_suffix(ts_code):
        code = ts_code.split('.')[0]
        if code.startswith('6'):
            return f'{code}.SH'
        else:
            return f'{code}.SZ'
    
    all_stocks['股票代码'] = all_stocks['ts_code'].apply(add_suffix)
    
    # 过滤80只样本
    tushare_info = all_stocks[all_stocks['股票代码'].isin(lines)].copy()
    
    # 合并标签
    sample_df = sample_df.merge(
        tushare_info[['股票代码', 'name', 'industry', 'market']], 
        on='股票代码', 
        how='left'
    )
    
    # 重命名列
    sample_df.rename(columns={
        'name': '股票名称',
        'industry': '行业',
        'market': '市场'
    }, inplace=True)
    
    print(f'  从Tushare匹配到{len(sample_df)}只')
    print('  ✅ 行业标签完成')
    
    # 5. 统计报告
    print(f'\n{"=" * 60}')
    print('标签统计报告')
    print('=' * 60)
    
    print(f'\n【弹性标签分布】')
    print(sample_df['弹性标签'].value_counts())
    
    print(f'\n【价格层级分布】')
    print(sample_df['价格层级'].value_counts())
    
    print(f'\n【竞价强度分布】')
    print(sample_df['竞价强度'].value_counts())
    
    print(f'\n【行业分布（Top 10）】')
    print(sample_df['行业'].value_counts().head(10))
    
    print(f'\n【市场分布】')
    print(sample_df['市场'].value_counts())
    
    # 6. 保存
    print(f'\n{"=" * 60}')
    print('保存结果')
    print('=' * 60)
    
    # 选择关键字段保存
    output_columns = [
        '股票代码', '股票名称', '行业', '市场',
        '弹性标签', '价格层级', '竞价强度',
        '竞价价格', '涨跌幅', '成交额'
    ]
    
    output_df = sample_df[output_columns].copy()
    output_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f'✅ 已保存: {output_file}')
    print(f'  字段: {output_columns}')
    print(f'  行数: {len(output_df)}')
    
    return output_df


if __name__ == '__main__':
    df = enrich_stock_tags()
    
    print(f'\n{"=" * 60}')
    print('P0任务完成：基础标签增强')
    print('=' * 60)
    print('已添加标签：')
    print('  - 弹性标签（20cm/10cm）')
    print('  - 价格层级（低价/中低价/中高价/高价）')
    print('  - 竞价强度（强势高开/温和高开/平开/低开）')
    print('  - 行业（Tushare）')
    print('  - 市场（主板/创业板/科创板）')
