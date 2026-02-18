#!/usr/bin/env python3
"""
生成150只股票的tick下载配置文件

基于wanzhu_top_120.json，添加30只热门股票
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取wanzhu_top_120.json
top120_path = PROJECT_ROOT / 'config' / 'wanzhu_top_120.json'
with open(top120_path, 'r', encoding='utf-8') as f:
    top120 = json.load(f)

# 额外30只热门股票（从其他配置文件或手动指定）
extra_stocks = [
    {"code": "600519.SH", "qmt_code": "600519", "market": "SH", "name": "贵州茅台"},
    {"code": "000858.SZ", "qmt_code": "000858", "market": "SZ", "name": "五粮液"},
    {"code": "300750.SZ", "qmt_code": "300750", "market": "SZ", "name": "宁德时代"},
    {"code": "002594.SZ", "qmt_code": "002594", "market": "SZ", "name": "比亚迪"},
    {"code": "601318.SH", "qmt_code": "601318", "market": "SH", "name": "中国平安"},
    {"code": "600036.SH", "qmt_code": "600036", "market": "SH", "name": "招商银行"},
    {"code": "000001.SZ", "qmt_code": "000001", "market": "SZ", "name": "平安银行"},
    {"code": "601012.SH", "qmt_code": "601012", "market": "SH", "name": "隆基绿能"},
    {"code": "002415.SZ", "qmt_code": "002415", "market": "SZ", "name": "海康威视"},
    {"code": "600276.SH", "qmt_code": "600276", "market": "SH", "name": "恒瑞医药"},
    {"code": "300015.SZ", "qmt_code": "300015", "market": "SZ", "name": "爱尔眼科"},
    {"code": "600900.SH", "qmt_code": "600900", "market": "SH", "name": "长江电力"},
    {"code": "601888.SH", "qmt_code": "601888", "market": "SH", "name": "中国中免"},
    {"code": "603259.SH", "qmt_code": "603259", "market": "SH", "name": "药明康德"},
    {"code": "300760.SZ", "qmt_code": "300760", "market": "SZ", "name": "迈瑞医疗"},
    {"code": "002475.SZ", "qmt_code": "002475", "market": "SZ", "name": "立讯精密"},
    {"code": "600690.SH", "qmt_code": "600690", "market": "SH", "name": "海尔智家"},
    {"code": "000333.SZ", "qmt_code": "000333", "market": "SZ", "name": "美的集团"},
    {"code": "601138.SH", "qmt_code": "601138", "market": "SH", "name": "工业富联"},
    {"code": "688981.SH", "qmt_code": "688981", "market": "SH", "name": "中芯国际"},
    {"code": "600030.SH", "qmt_code": "600030", "market": "SH", "name": "中信证券"},
    {"code": "002592.SZ", "qmt_code": "002592", "market": "SZ", "name": "八亿时空"},
    {"code": "601668.SH", "qmt_code": "601668", "market": "SH", "name": "中国建筑"},
    {"code": "600028.SH", "qmt_code": "600028", "market": "SH", "name": "中国石化"},
    {"code": "601857.SH", "qmt_code": "601857", "market": "SH", "name": "中国石油"},
    {"code": "000725.SZ", "qmt_code": "000725", "market": "SZ", "name": "京东方A"},
    {"code": "002129.SZ", "qmt_code": "002129", "market": "SZ", "name": "TCL中环"},
    {"code": "300059.SZ", "qmt_code": "300059", "market": "SZ", "name": "东方财富"},
    {"code": "002142.SZ", "qmt_code": "002142", "market": "SZ", "name": "宁波银行"},
]

# 转换top120为标准格式
stocks_150 = []

# 前120只来自wanzhu_top_120.json
for i, stock in enumerate(top120[:120], 1):
    code = stock['code']
    if code.endswith('.SH'):
        qmt_code = code[:-3]
        market = 'SH'
    elif code.endswith('.SZ'):
        qmt_code = code[:-3]
        market = 'SZ'
    else:
        continue

    stocks_150.append({
        "code": code,
        "qmt_code": qmt_code,
        "market": market,
        "name": stock['name'],
        "rank": i
    })

# 后30只来自extra_stocks
for i, stock in enumerate(extra_stocks, 121):
    stocks_150.append({
        "code": stock['code'],
        "qmt_code": stock['qmt_code'],
        "market": stock['market'],
        "name": stock['name'],
        "rank": i
    })

# 保存配置文件
output_path = PROJECT_ROOT / 'config' / 'wanzhu_top150_tick_download.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(stocks_150, f, ensure_ascii=False, indent=2)

print(f"✅ 已生成150只股票配置文件")
print(f"   文件路径：{output_path}")
print(f"   股票数量：{len(stocks_150)}")
print(f"   前120只：来自wanzhu_top_120.json")
print(f"   后30只：热门蓝筹股")
print()
print("前10只股票：")
for stock in stocks_150[:10]:
    print(f"   {stock['rank']:3d}. {stock['name']} ({stock['code']})")