#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试QMT实时tick数据
"""
import sys
sys.path.insert(0, 'E:/MyQuantTool')

try:
    import xtdata
    print('✅ xtdata导入成功')
    
    # 获取股票列表
    stocks = xtdata.get_stock_list_in_sector('沪深A股')
    print(f'📊 股票数量: {len(stocks)}')
    
    if len(stocks) > 0:
        code = stocks[0]
        print(f'🧪 测试股票: {code}')
        
        # 尝试获取tick数据
        data = xtdata.get_market_data(
            [code], 
            period='tick', 
            start_time='20260209 09:15:00', 
            end_time='20260209 09:17:00', 
            count=10
        )
        print(f'📊 Tick数据: {data}')
        
        # 尝试获取最新行情
        latest = xtdata.get_full_tick([code])
        print(f'📊 最新行情: {latest}')
    
except Exception as e:
    print(f'❌ 错误: {e}')
    import traceback
    traceback.print_exc()