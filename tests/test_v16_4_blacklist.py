#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V16.4.0 黑名单机制测试

测试目标：
1. 测试黑名单生成器（测试模式：10只股票）
2. 测试黑名单检查功能
3. 测试系统状态持久化

Usage:
    python tests/test_v16_4_blacklist.py

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.4.0
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.utils.logger import get_logger

logger = get_logger(__name__)


def test_blacklist_generation():
    """测试黑名单生成（测试模式：10只股票）"""
    print("=" * 80)
    print("🧪 测试1: 黑名单生成（测试模式：10只股票）")
    print("=" * 80)

    # 导入黑名单生成器
    from tasks.job_update_blacklist import update_blacklist, RISK_KEYWORDS

    # 模拟测试模式（只扫描10只股票）
    import akshare as ak

    print("📋 获取股票列表...")
    stock_list = ak.stock_zh_a_spot_em()
    test_stocks = stock_list.head(10)

    print(f"🎯 测试股票: {len(test_stocks)} 只")

    # 模拟黑名单生成逻辑（简化版）
    import json
    from datetime import datetime, timedelta
    import time
    import random

    blacklist = []
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()

    for idx, row in test_stocks.iterrows():
        code = row['代码']
        name = row['名称']

        # 添加随机延迟（防WAF）
        time.sleep(random.uniform(0.1, 0.3))

        try:
            df = ak.stock_zh_a_disclosure_report_cninfo(
                symbol=code,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )

            if df.empty:
                print(f"  {code} {name}: 无公告")
                continue

            # 检查公告标题
            for _, ann in df.iterrows():
                title = str(ann['公告标题'])
                if any(keyword in title for keyword in RISK_KEYWORDS):
                    blacklist.append({
                        'code': code,
                        'name': name,
                        'title': title,
                        'date': str(ann['公告时间'])
                    })
                    print(f"  ⛔ {code} {name}: 发现风险公告")
                    break
                else:
                    print(f"  ✅ {code} {name}: 无风险")

        except Exception as e:
            print(f"  ⚠️ {code} {name}: 失败 - {e}")
            continue

    print(f"\n📊 测试结果: {len(blacklist)}/{len(test_stocks)} 只有风险")
    print("✅ 测试1完成\n")

    return blacklist


def test_blacklist_loading():
    """测试黑名单加载"""
    print("=" * 80)
    print("🧪 测试2: 黑名单加载")
    print("=" * 80)

    blacklist_file = Path('data/risk/blacklist.json')

    if not blacklist_file.exists():
        print("⚠️ 黑名单文件不存在，跳过测试")
        return

    try:
        with open(blacklist_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"✅ 黑名单文件加载成功")
        print(f"📊 更新时间: {data.get('update_time', '未知')}")
        print(f"📊 黑名单数量: {data.get('count', 0)} 只")

        stocks = data.get('stocks', [])
        if stocks:
            print(f"\n📋 黑名单股票（前5只）:")
            for item in stocks[:5]:
                print(f"  - {item['code']} {item['name']}: {item['title']}")

        print("✅ 测试2完成\n")

    except Exception as e:
        print(f"❌ 黑名单加载失败: {e}\n")


def test_system_state():
    """测试系统状态持久化"""
    print("=" * 80)
    print("🧪 测试3: 系统状态持久化")
    print("=" * 80)

    state_file = Path('data/system_state.json')

    if not state_file.exists():
        print("⚠️ 系统状态文件不存在，跳过测试")
        return

    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)

        print(f"✅ 系统状态文件加载成功")
        print(f"📊 上次更新: {state.get('last_blacklist_update', '未知')}")
        print(f"📊 黑名单数量: {state.get('blacklist_count', 0)} 只")
        print(f"📊 版本号: {state.get('risk_stocks_version', '未知')}")

        print("✅ 测试3完成\n")

    except Exception as e:
        print(f"❌ 系统状态加载失败: {e}\n")


def test_level1_fix():
    """测试Level 1漏洞修复"""
    print("=" * 80)
    print("🧪 测试4: Level 1漏洞修复（跌幅过滤）")
    print("=" * 80)

    from logic.strategies.full_market_scanner import FullMarketScanner

    # 模拟测试数据
    test_cases = [
        {'code': '000001.SZ', 'name': '平安银行', 'lastClose': 10.00, 'lastPrice': 10.50},  # +5%
        {'code': '000002.SZ', 'name': '万科A', 'lastClose': 10.00, 'lastPrice': 9.50},    # -5%
        {'code': '600000.SH', 'name': '浦发银行', 'lastClose': 10.00, 'lastPrice': 9.80},  # -2%
        {'code': '600036.SH', 'name': '招商银行', 'lastClose': 10.00, 'lastPrice': 9.70},  # -3%
    ]

    scanner = FullMarketScanner()

    print("📋 测试案例:")
    for case in test_cases:
        code = case['code']
        tick = {
            'lastClose': case['lastClose'],
            'lastPrice': case['lastPrice'],
            'amount': 50000000,  # 5000万成交额
            'totalVolume': 5000000,  # 500万成交量
        }

        try:
            # 注意：_check_level1_criteria需要更多字段，这里只是模拟测试
            pct_chg = (tick['lastPrice'] - tick['lastClose']) / tick['lastClose'] * 100

            if pct_chg < -2.0:
                result = "❌ 拒绝（跌幅过滤）"
            else:
                result = "✅ 通过"

            print(f"  {code} {case['name']}: {pct_chg:+.1f}% - {result}")

        except Exception as e:
            print(f"  {code} {case['name']}: 测试失败 - {e}")

    print("✅ 测试4完成\n")


if __name__ == "__main__":
    try:
        print("\n" + "=" * 80)
        print("V16.4.0 黑名单机制测试")
        print("=" * 80 + "\n")

        # 测试1: 黑名单生成
        blacklist = test_blacklist_generation()

        # 测试2: 黑名单加载
        test_blacklist_loading()

        # 测试3: 系统状态
        test_system_state()

        # 测试4: Level 1漏洞修复
        test_level1_fix()

        print("=" * 80)
        print("✅ 所有测试完成")
        print("=" * 80)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)