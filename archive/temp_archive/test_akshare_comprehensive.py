#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AkShare 全面连通性测试
测试多个接口，看看是否完全无法获取数据
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("🔍 AkShare 全面连通性测试")
print("=" * 80)
print()

# 清空代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['ALL_PROXY'] = ''
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

print("✅ 已清空代理环境变量")
print()

# 测试AkShare是否安装
print("Step 1: 检查AkShare安装")
try:
    import akshare as ak
    print(f"✅ AkShare已安装，版本: {ak.__version__}")
except ImportError as e:
    print(f"❌ AkShare未安装: {e}")
    sys.exit(1)

print()

# 测试多个接口
test_cases = [
    {
        'name': 'A股实时行情（主要接口）',
        'func': lambda: ak.stock_zh_a_spot_em(),
        'critical': True
    },
    {
        'name': '上证指数',
        'func': lambda: ak.stock_zh_index_spot_em(),
        'critical': True
    },
    {
        'name': '个股资金流向（Level 2用）',
        'func': lambda: ak.stock_individual_fund_flow(stock='000001', market='sz'),
        'critical': True
    },
    {
        'name': '个股历史行情',
        'func': lambda: ak.stock_zh_a_hist(symbol='000001', period='daily', start_date='20250101', end_date='20250206'),
        'critical': False
    },
    {
        'name': '实时涨跌停统计',
        'func': lambda: ak.stock_zt_pool_em(date='20250206'),
        'critical': False
    }
]

success_count = 0
fail_count = 0
critical_failures = []

for idx, test_case in enumerate(test_cases, 1):
    print(f"测试 {idx}: {test_case['name']}")
    print(f"   关键程度: {'关键' if test_case['critical'] else '非关键'}")

    try:
        print("   ⏱️  正在请求数据...")
        result = test_case['func']()

        print(f"   ✅ 获取成功！")

        if hasattr(result, 'shape'):
            print(f"   📊 数据形状: {result.shape}")
            print(f"   📄 数据类型: {type(result)}")

            if hasattr(result, 'head'):
                print(f"   📋 前3行数据:")
                print(result.head(3).to_string(index=False))
        elif isinstance(result, dict):
            print(f"   📊 数据类型: dict")
            print(f"   📋 键: {list(result.keys())}")
        else:
            print(f"   📊 数据类型: {type(result)}")
            print(f"   📋 数据长度: {len(result) if hasattr(result, '__len__') else 'N/A'}")

        success_count += 1

    except Exception as e:
        print(f"   ❌ 获取失败: {str(e)[:100]}")

        if test_case['critical']:
            critical_failures.append(test_case['name'])

        fail_count += 1

    print()

# 打印汇总
print("=" * 80)
print("📊 测试结果汇总")
print("=" * 80)
print(f"总测试数: {len(test_cases)}")
print(f"成功: {success_count}")
print(f"失败: {fail_count}")
print(f"成功率: {success_count/len(test_cases)*100:.1f}%")
print()

if critical_failures:
    print("⚠️  关键接口失败:")
    for failure in critical_failures:
        print(f"   - {failure}")
    print()
    print("💡 结论: AkShare关键接口无法使用，建议:")
    print("   1. 切换到Tushare")
    print("   2. 临时禁用依赖AkShare的功能")
    print("   3. 明天早上再测试（交易时间）")
elif success_count > 0:
    print("✅ 部分接口可用")
    print("💡 建议: 优先使用可用接口，失败的接口可降级或重试")
else:
    print("❌ 所有接口都失败")
    print("💡 结论: AkShare当前环境下完全不可用")
    print("   建议立即切换到Tushare或QMT数据源")

print("=" * 80)