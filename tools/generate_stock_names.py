# -*- coding: utf-8 -*-
"""
生成股票名称字典

从 equity_info_tushare.json 或其他数据源提取股票名称
生成 stock_names.json 供系统使用

Author: iFlow CLI
Version: V1.0
Date: 2026-02-09 10:52 AM
"""

import json
import os
from datetime import datetime

# 配置
EQUITY_FILE = 'data/equity_info_tushare.json'
OUTPUT_FILE = 'data/stock_names.json'


def generate_names():
    """生成股票名称字典"""
    print("=" * 80)
    print("🚀 开始生成股票名称字典")
    print("=" * 80)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 读取股权数据文件
    if not os.path.exists(EQUITY_FILE):
        print(f"❌ 股权数据文件不存在: {EQUITY_FILE}")
        return False

    print(f"📄 读取股权数据: {EQUITY_FILE}")
    with open(EQUITY_FILE, 'r', encoding='utf-8') as f:
        equity_data = json.load(f)

    # 2. 判断数据结构
    # 新结构: {latest_update, history_days, data_structure, data: {code: {date: {...}}}}
    # 旧结构: {latest_update, retention_days, data: {date: {code: {...}}}}

    name_map = {}

    if 'data' in equity_data:
        data_section = equity_data['data']

        # 检查是哪种结构
        if data_section and isinstance(data_section, dict):
            # 取一个样本判断结构
            first_key = list(data_section.keys())[0]

            # 如果第一个key是日期格式（20260206），则是旧结构
            if first_key.isdigit() and len(first_key) == 8:
                print("📊 检测到旧数据结构 (日期 -> 股票)")
                # 旧结构: {date: {code: {...}}}
                for date_code, stocks in data_section.items():
                    for stock_code, stock_info in stocks.items():
                        if stock_code not in name_map:
                            name_map[stock_code] = stock_info.get('name', stock_code)

            else:
                print("📊 检测到新数据结构 (股票 -> 日期)")
                # 新结构: {code: {date: {...}}}
                for stock_code, dates in data_section.items():
                    if stock_code not in name_map:
                        # 取最近一天的数据
                        if dates:
                            latest_date = sorted(dates.keys())[-1]
                            name_map[stock_code] = dates[latest_date].get('name', stock_code)

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
    import sys
    try:
        success = generate_names()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)