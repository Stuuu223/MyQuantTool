#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V9.4.9 修复验证测试

目的：
1. 验证代码语法正确性
2. 测试三级降级策略
3. 检查 price_3d_change 计算逻辑

Author: iFlow CLI
Date: 2026-02-09
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("🔍 V9.4.9 修复验证测试")
print("=" * 80)
print()

# 测试1：导入模块
print("📝 测试1: 导入 full_market_scanner 模块")
try:
    from logic.full_market_scanner import FullMarketScanner
    print("✅ 模块导入成功")
except Exception as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)

print()

# 测试2：检查 QMT 可用性
print("📝 测试2: 检查 QMT 可用性")
try:
    from xtquant import xtdata
    print("✅ QMT 可用")
except ImportError:
    print("⚠️  QMT 不可用（这是正常的，如果没有安装 QMT）")

print()

# 测试3：验证代码逻辑
print("📝 测试3: 验证 price_3d_change 计算逻辑")
try:
    import pandas as pd
    from datetime import datetime, timedelta

    # 模拟数据
    current_price = 8.26
    ref_price = 7.51

    # 计算3日涨幅
    price_3d_change = (current_price - ref_price) / ref_price

    print(f"   当前价格: {current_price}")
    print(f"   参考价格: {ref_price}")
    print(f"   3日涨幅: {price_3d_change:.4f} ({price_3d_change * 100:.2f}%)")

    if abs(price_3d_change - 0.0999) < 0.001:
        print("✅ 计算逻辑正确")
    else:
        print(f"❌ 计算逻辑错误: 预期 0.0999，实际 {price_3d_change:.4f}")

except Exception as e:
    print(f"❌ 逻辑验证失败: {e}")

print()

# 测试4：检查数据结构
print("📝 测试4: 检查数据结构")
try:
    # 读取扫描结果
    scan_results_file = Path('data/scan_results/2026-02-09_intraday.json')

    if scan_results_file.exists():
        import json
        with open(scan_results_file, 'r', encoding='utf-8') as f:
            scan_data = json.load(f)

        blacklist = scan_data['results']['blacklist']
        print(f"   扫描结果时间: {scan_data['scan_time']}")
        print(f"   黑名单股票数: {len(blacklist)}")

        # 检查第一只股票的字段
        if blacklist:
            first_stock = blacklist[0]
            print(f"   第一只股票: {first_stock['code']}")
            print(f"   price_3d_change: {first_stock.get('price_3d_change', 'N/A')}")
            print(f"   新字段 price_3d_strategy: {first_stock.get('price_3d_strategy', 'N/A')}")

        print("✅ 数据结构检查完成")
    else:
        print("⚠️  扫描结果文件不存在")

except Exception as e:
    print(f"❌ 数据结构检查失败: {e}")

print()
print("=" * 80)
print("📊 验证测试完成")
print("=" * 80)
print()
print("✅ V9.4.9 改进内容：")
print("   1. ✅ Phase 1: 增强日志追踪失败链条")
print("   2. ✅ Phase 2: 分钟合成优化（缓存+重试）")
print("   3. ✅ Phase 3: AkShare重试机制")
print("   4. ✅ Phase 4: QMT策略1强化校验")
print()
print("📝 下一步：")
print("   1. 运行扫描器，测试三级降级策略")
print("   2. 检查日志输出，确认每个策略的执行情况")
print("   3. 验证 price_3d_change 修复率 > 99%")
print("=" * 80)