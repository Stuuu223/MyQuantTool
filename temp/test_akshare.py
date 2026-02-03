#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试AkShare是否可用"""

import akshare as ak

print('AkShare version:', ak.__version__)

try:
    df = ak.stock_zh_a_spot_em()
    print('Total stocks:', len(df))
    
    stock = df[df['代码'] == '300997']
    print('Found 300997:', len(stock))
    
    if len(stock) > 0:
        print('Price:', stock['最新价'].values[0])
        print('✅ AkShare 可用！')
    else:
        print('❌ 未找到股票 300997')
except Exception as e:
    print(f'❌ AkShare 错误: {e}')