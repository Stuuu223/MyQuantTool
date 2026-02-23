#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查1月5日数据完整性"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

from pathlib import Path
import pandas as pd

def check_0105_data():
    df = pd.read_csv('data/cleaned_candidates_66.csv')
    stock_list = df['ts_code'].tolist()
    
    print('='*80)
    print('【1月5日数据完整性检查】')
    print('='*80)
    
    data_dir = Path('E:/qmt/userdata_mini/datadir')
    complete = []
    missing = []
    
    for stock in stock_list:
        code = stock.split('.')[0]
        exchange = stock.split('.')[1]
        tick_file = data_dir / exchange / '0' / code / '20260105'
        
        if tick_file.exists() and tick_file.stat().st_size > 1000:
            size_kb = tick_file.stat().st_size / 1024
            complete.append({'stock': stock, 'size_kb': size_kb})
        else:
            missing.append(stock)
    
    print(f'数据完整: {len(complete)} 只')
    print(f'数据缺失: {len(missing)} 只')
    print()
    
    # 检查志特新材
    zhite = '300986.SZ'
    zhite_status = '完整' if zhite not in missing else '缺失'
    print(f'【志特新材 300986.SZ】: {zhite_status}')
    
    if missing:
        print(f'\n缺失名单: {missing}')
    
    return len(complete), len(missing)

if __name__ == '__main__':
    check_0105_data()
