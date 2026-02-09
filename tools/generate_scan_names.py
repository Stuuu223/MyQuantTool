# -*- coding: utf-8 -*-
"""
只补全扫描结果中的股票名称

读取扫描结果，获取其中的股票代码
从 QMT 逐个获取名称，生成 stock_names.json

Author: iFlow CLI
Version: V3.0
Date: 2026-02-09 10:58 AM
"""

import json
import os
from datetime import datetime

try:
    from xtquant import xtdata
except ImportError:
    print("❌ xtquant 模块未安装")
    exit(1)

SCAN_FILE = 'data/scan_results/2026-02-09_intraday.json'
OUTPUT_FILE = 'data/stock_names.json'


def generate_names_from_scan():
    """从扫描结果生成股票名称"""
    print("=" * 80)
    print("🚀 从扫描结果生成股票名称")
    print("=" * 80)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 读取扫描结果
    if not os.path.exists(SCAN_FILE):
        print(f"❌ 扫描结果文件不存在: {SCAN_FILE}")
        return False

    print(f"📄 读取扫描结果: {SCAN_FILE}")
    with open(SCAN_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 2. 提取所有股票代码
    all_codes = []

    if 'results' in data and 'blacklist' in data['results']:
        for item in data['results']['blacklist']:
            code = item.get('code', '')
            if code:
                # 去掉后缀，只保留6位代码
                code_6digit = code.replace('.SZ', '').replace('.SH', '')
                all_codes.append(code_6digit)

    if 'results' in data and 'opportunities' in data['results']:
        for item in data['results']['opportunities']:
            code = item.get('code', '')
            if code:
                code_6digit = code.replace('.SZ', '').replace('.SH', '')
                all_codes.append(code_6digit)

    if 'results' in data and 'watchlist' in data['results']:
        for item in data['results']['watchlist']:
            code = item.get('code', '')
            if code:
                code_6digit = code.replace('.SZ', '').replace('.SH', '')
                all_codes.append(code_6digit)

    # 去重
    all_codes = list(set(all_codes))
    print(f"🔍 找到 {len(all_codes)} 只股票")

    # 3. 逐个获取名称
    name_map = {}
    for i, code in enumerate(all_codes):
        # 转换为 QMT 格式
        if code.startswith('6'):
            qmt_code = f'{code}.SH'
        else:
            qmt_code = f'{code}.SZ'

        try:
            info = xtdata.get_instrument_detail(qmt_code)
            if isinstance(info, bytes):
                info = info.decode('utf-8')

            if isinstance(info, str):
                name = info.split(',')[1] if ',' in info else code
            else:
                name = code

            name_map[code] = name

            if (i + 1) % 10 == 0:
                print(f"   已处理 {i+1}/{len(all_codes)}...")

        except Exception as e:
            name_map[code] = code  # 失败就用代码代替

    print(f"✅ 提取到 {len(name_map)} 个股票名称")
    print()

    # 4. 保存
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
        generate_names_from_scan()
    except Exception as e:
        print(f"\n\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()