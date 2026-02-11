import json

with open('data/equity_info_tushare.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

stock_data = data.get('data', {}).get('20260206', {}).get('603607.SH', {})

print('603607.SH 数据:')
print(f'  float_mv: {stock_data.get("float_mv")} 元 ({stock_data.get("float_mv", 0) / 1e8:.2f} 亿)')
print(f'  total_mv: {stock_data.get("total_mv")} 元 ({stock_data.get("total_mv", 0) / 1e8:.2f} 亿)')