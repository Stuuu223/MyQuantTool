#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO Phase 6.2】数据验尸官 - QMT数据完整性检查
清洗标准：宁缺毋滥，直接剔除缺失/损坏数据
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

import pandas as pd
from pathlib import Path
import json
from datetime import datetime

def check_data_integrity():
    """检查73只票QMT数据完整性"""
    
    # 读取73只票名单
    df = pd.read_csv('data/scan_results/20251231_candidates_73.csv')
    stock_list = df['ts_code'].tolist()
    
    print('='*80)
    print('【数据验尸官报告】73只票QMT数据完整性检查')
    print('='*80)
    print(f'检查日期: 20251231')
    print(f'股票总数: {len(stock_list)}')
    print()
    
    # 检查结果
    results = {
        'complete': [],
        'missing': [],
        'corrupt': []
    }
    
    data_dir = Path('E:/qmt/userdata_mini/datadir')
    
    for stock in stock_list:
        code = stock.split('.')[0]
        exchange = stock.split('.')[1]
        
        # 检查Tick数据目录
        tick_dir = data_dir / exchange / '0' / code
        
        if not tick_dir.exists():
            results['missing'].append({'stock': stock, 'reason': '目录不存在'})
            continue
        
        # 检查20251231文件
        tick_file = tick_dir / '20251231'
        
        if not tick_file.exists():
            results['missing'].append({'stock': stock, 'reason': '20251231数据缺失'})
            continue
        
        # 检查文件大小
        file_size = tick_file.stat().st_size
        
        if file_size < 1000:  # 小于1KB认为损坏
            results['corrupt'].append({'stock': stock, 'size': file_size})
            continue
        
        results['complete'].append({'stock': stock, 'size_kb': file_size/1024})
    
    # 输出统计
    complete_count = len(results['complete'])
    missing_count = len(results['missing'])
    corrupt_count = len(results['corrupt'])
    
    print(f'✅ 数据完整: {complete_count} 只')
    print(f'❌ 数据缺失: {missing_count} 只')
    print(f'⚠️  数据损坏: {corrupt_count} 只')
    print()
    
    # 输出缺失名单
    if results['missing']:
        print('-'*80)
        print('【缺失名单】')
        for item in results['missing']:
            print(f'  {item["stock"]}: {item["reason"]}')
        print()
    
    # 输出完整名单前10
    print('-'*80)
    print('【完整数据前10只】')
    for item in results['complete'][:10]:
        print(f'  {item["stock"]}: {item["size_kb"]:.1f} KB')
    
    # 检查志特新材
    zhitexincai_status = '✅ 完整' if any(x['stock'] == '300986.SZ' for x in results['complete']) else '❌ 缺失'
    print()
    print('-'*80)
    print(f'【志特新材】{zhitexincai_status}')
    print('-'*80)
    
    # 保存结果
    output = {
        'check_date': '20251231',
        'total': len(stock_list),
        'complete_count': complete_count,
        'missing_count': missing_count,
        'corrupt_count': corrupt_count,
        'complete_list': [x['stock'] for x in results['complete']],
        'missing_list': results['missing'],
        'zhitexincai_status': zhitexincai_status
    }
    
    output_path = Path('data/audit_data_integrity_20251231.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # 生成清洗后的名单
    cleaned_df = df[df['ts_code'].isin(output['complete_list'])]
    cleaned_path = Path('data/cleaned_candidates_66.csv')
    cleaned_df.to_csv(cleaned_path, index=False)
    
    print()
    print('='*80)
    print(f'✅ 验尸报告已保存: {output_path}')
    print(f'✅ 清洗后名单已保存: {cleaned_path} ({complete_count}只)')
    print('='*80)
    
    return results

if __name__ == '__main__':
    check_data_integrity()