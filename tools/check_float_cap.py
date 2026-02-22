#!/usr/bin/env python3
"""验证志特新材真实流通市值"""

from xtquant import xtdata

# 获取志特新材的真实流通股本
detail = xtdata.get_instrument_detail('300986.SZ')
if detail:
    print('志特新材(300986.SZ)真实数据:')
    print(f"  流通股本: {detail.get('FloatVolume', 0):,.0f}股")
    print(f"  总股本: {detail.get('TotalVolume', 0):,.0f}股")
    print(f"  当前价: {detail.get('LastPrice', 0)}元")
    
    float_vol = detail.get('FloatVolume', 0)
    last_price = detail.get('LastPrice', 11.18)  # 使用2025-12-31收盘价
    
    float_cap = float_vol * last_price / 1e8  # 亿元
    print(f"  流通市值: {float_cap:.2f}亿元")
else:
    print('无法获取数据')
