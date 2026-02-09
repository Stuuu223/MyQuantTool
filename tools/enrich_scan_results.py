# -*- coding: utf-8 -*-
"""
扫描结果数据补全脚本

功能：
- 读取扫描结果 JSON
- 补全股票名称
- 从 QMT 获取实时行情（价格、涨幅、振幅等）
- 写回原文件

Author: iFlow CLI
Version: V1.0
Date: 2026-02-09 10:48 AM
"""

import json
import os
from datetime import datetime

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from xtquant import xtdata
except ImportError:
    print("❌ xtquant 模块未安装")
    sys.exit(1)

# 配置
SCAN_FILE = 'data/scan_results/2026-02-09_intraday.json'
NAME_FILE = 'data/stock_names.json'


def enrich_results():
    """补全扫描结果数据"""
    print("=" * 80)
    print("🚀 开始补全扫描结果数据")
    print("=" * 80)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 读取原始 JSON
    if not os.path.exists(SCAN_FILE):
        print(f"❌ 扫描结果文件不存在: {SCAN_FILE}")
        return False

    print(f"📄 读取扫描结果: {SCAN_FILE}")
    with open(SCAN_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 2. 读取名称字典
    name_map = {}
    if os.path.exists(NAME_FILE):
        print(f"📄 读取股票名称: {NAME_FILE}")
        with open(NAME_FILE, 'r', encoding='utf-8') as f:
            name_map = json.load(f)
        print(f"✅ 加载 {len(name_map)} 个股票名称")
    else:
        print("⚠️  股票名称文件不存在")

    # 3. 提取所有涉及的股票代码
    all_codes = []

    # 提取 blacklist
    if 'results' in data and 'blacklist' in data['results']:
        for item in data['results']['blacklist']:
            code = item.get('code', '')
            if code:
                # 去掉后缀，只保留6位代码
                code_6digit = code.replace('.SZ', '').replace('.SH', '')
                all_codes.append(code_6digit)

    # 提取 opportunities
    if 'results' in data and 'opportunities' in data['results']:
        for item in data['results']['opportunities']:
            code = item.get('code', '')
            if code:
                code_6digit = code.replace('.SZ', '').replace('.SH', '')
                all_codes.append(code_6digit)

    # 提取 watchlist
    if 'results' in data and 'watchlist' in data['results']:
        for item in data['results']['watchlist']:
            code = item.get('code', '')
            if code:
                code_6digit = code.replace('.SZ', '').replace('.SH', '')
                all_codes.append(code_6digit)

    # 去重
    all_codes = list(set(all_codes))
    print(f"🔍 需要补全信息的股票: {len(all_codes)} 只")
    print()

    # 4. 从 QMT 获取最新行情
    print("📥 从 QMT 获取实时行情...")

    # 转换为 QMT 格式（添加后缀）
    qmt_codes = []
    for code in all_codes:
        if code.startswith('6'):
            qmt_codes.append(f'{code}.SH')
        else:
            qmt_codes.append(f'{code}.SZ')

    try:
        full_tick = xtdata.get_full_tick(qmt_codes)
        print(f"✅ 获取到 {len(full_tick)} 只股票的行情数据")
    except Exception as e:
        print(f"❌ 获取行情失败: {e}")
        full_tick = {}

    print()

    # 5. 补全逻辑
    def process_list(target_list):
        """处理股票列表"""
        for item in target_list:
            code = item.get('code', '')
            code_6digit = code.replace('.SZ', '').replace('.SH', '')
            qmt_code = code if '.' in code else (f'{code}.SH' if code.startswith('6') else f'{code}.SZ')

            # 补全名称
            item['name'] = name_map.get(code_6digit, '未知')

            # 补全行情
            tick = full_tick.get(qmt_code, {})

            if tick:
                # 基础行情
                item['price'] = tick.get('lastPrice', 0)
                item['pct_chg'] = tick.get('pctChg', 0)  # 涨跌幅
                item['high'] = tick.get('high', 0)
                item['low'] = tick.get('low', 0)
                item['open'] = tick.get('open', 0)
                item['vol'] = tick.get('volume', 0)  # 成交量（手）
                item['amount'] = tick.get('amount', 0)  # 成交额（元）
                item['turnover_rate'] = tick.get('turnover', 0)  # 换手率

                # 计算振幅
                last_close = tick.get('lastClose', 1)
                if last_close > 0:
                    item['amplitude'] = (item['high'] - item['low']) / last_close * 100
                else:
                    item['amplitude'] = 0

                # 判断是否涨停
                limit_up = False
                if code.startswith('6'):  # 主板
                    limit_up = item['pct_chg'] >= 9.9
                elif code.startswith('3'):  # 创业板
                    limit_up = item['pct_chg'] >= 19.9
                elif code.startswith('688'):  # 科创板
                    limit_up = item['pct_chg'] >= 19.9
                item['is_limit_up'] = limit_up

            else:
                item['note'] = "行情获取失败"
                item['price'] = 0
                item['pct_chg'] = 0
                item['amplitude'] = 0

    # 处理黑名单
    if 'results' in data and 'blacklist' in data['results']:
        print(f"💾 补全黑名单数据 ({len(data['results']['blacklist'])} 只)...")
        process_list(data['results']['blacklist'])

    # 处理机会池
    if 'results' in data and 'opportunities' in data['results']:
        print(f"💾 补全机会池数据 ({len(data['results']['opportunities'])} 只)...")
        process_list(data['results']['opportunities'])

    # 处理观察列表
    if 'results' in data and 'watchlist' in data['results']:
        print(f"💾 补全观察列表数据 ({len(data['results']['watchlist'])} 只)...")
        process_list(data['results']['watchlist'])

    # 6. 保存回写
    print()
    print(f"💾 保存结果到: {SCAN_FILE}")

    # 备份原文件
    backup_file = f"{SCAN_FILE}.backup_{datetime.now().strftime('%H%M%S')}"
    import shutil
    shutil.copy2(SCAN_FILE, backup_file)
    print(f"✅ 原文件已备份至: {backup_file}")

    # 保存新文件
    with open(SCAN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 80)
    print("✅ 结果文件已增强！")
    print()
    print("补全字段:")
    print("   - name: 股票名称")
    print("   - price: 现价")
    print("   - pct_chg: 涨跌幅")
    print("   - high: 最高价")
    print("   - low: 最低价")
    print("   - open: 开盘价")
    print("   - vol: 成交量")
    print("   - amount: 成交额")
    print("   - amplitude: 振幅")
    print("   - is_limit_up: 是否涨停")
    print("=" * 80)
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return True


if __name__ == "__main__":
    try:
        success = enrich_results()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)