#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""创建测试数据文件"""
import json
import os

# 测试数据：603607.SH 在 20260206 的流通市值
# circ_mv = 454682.2896 万元 = 4546822896 元
data = {
    'latest_update': '20260206',
    'retention_days': 30,
    'data': {
        '20260206': {
            '603607.SH': {
                'float_mv': 4546822896.0,  # 万元→元
                'total_mv': 0,
                'close': 0,
                'turnover_rate': 0,
                'pe': 0,
                'pb': 0
            }
        }
    }
}

os.makedirs('data', exist_ok=True)
with open('data/equity_info_tushare.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('✅ 已创建测试数据文件')
print(f"标准答案: 603607.SH 在 20260206 的流通市值 = {data['data']['20260206']['603607.SH']['float_mv']} 元")