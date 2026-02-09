# -*- coding: utf-8 -*-
"""
生成股票名称字典 V2 - 从 QMT 快速获取

从 QMT 获取全市场股票列表和名称
生成 stock_names.json

Author: iFlow CLI
Version: V2.0
Date: 2026-02-09 10:53 AM
"""

import json
import os
from datetime import datetime

try:
    from xtquant import xtdata
except ImportError:
    print("❌ xtquant 模块未安装")
    exit(1)

OUTPUT_FILE = 'data/stock_names.json'


def generate_names_from_qmt():
    """从 QMT 获取股票名称"""
    print("=" * 80)
    print("🚀 从 QMT 生成股票名称字典")
    print("=" * 80)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 获取沪深A股列表
    print("📥 获取全市场股票列表...")
    stocks = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"✅ 获取到 {len(stocks)} 只股票")
    print()

    # 2. 获取股票信息（包含名称）
    print("📥 获取股票名称信息...")
    stock_info = xtdata.get_instrument_detail(stocks)

    name_map = {}
    count = 0
    for code in stocks:
        info = stock_info.get(code, {})
        name = info.get('InstrumentName', '未知')

        # 去掉后缀，只保留6位代码
        code_6digit = code.replace('.SZ', '').replace('.SH', '')

        name_map[code_6digit] = name
        count += 1

        if count % 1000 == 0:
            print(f"   已处理 {count}/{len(stocks)}...")

    print(f"✅ 提取到 {len(name_map)} 个股票名称")
    print()

    # 3. 保存
    print(f"💾 保存到: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(name_map, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 80)
    print("✅ 股票名称字典生成完成！")
    print(f"   文件: {OUTPUT_FILE}")
    print(f"   数量: {len(name_map)} 个")
    print("=" * 80)
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return True


if __name__ == "__main__":
    try:
        generate_names_from_qmt()
    except Exception as e:
        print(f"\n\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()