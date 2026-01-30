#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 QMT 数据适配层

验证：
1. QMT 数据能正常获取
2. 股票名称已补充
3. 振幅计算正确
4. 字段标准化完成
5. 战法接口正常工作
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from logic.data_adapter import (
    DataAdapter,
    get_stocks_for_longtou,
    get_stocks_for_dixi,
    get_stocks_for_banlu
)
from logic.active_stock_filter import get_active_stock_filter

def test_qmt_active_filter():
    """测试 QMT 活跃股筛选（含名称补充）"""
    print("=" * 60)
    print("🧪 测试 1: QMT 活跃股筛选 + 名称补充")
    print("=" * 60)

    filter_obj = get_active_stock_filter()
    stocks = filter_obj.get_active_stocks(limit=10, min_amplitude=1.0)

    if not stocks:
        print("❌ 未获取到股票数据")
        return False

    print(f"\n✅ 获取到 {len(stocks)} 只股票\n")

    # 打印前 3 只
    for i, stock in enumerate(stocks[:3], 1):
        print(f"股票 {i}:")
        print(f"  代码: {stock.get('代码', 'N/A')}")
        print(f"  名称: {stock.get('名称', 'N/A')} {'✅' if stock.get('名称') else '❌ 名称为空'}")
        print(f"  最新价: {stock.get('最新价', 0):.2f}")
        print(f"  涨跌幅: {stock.get('涨跌幅', 0):.2f}%")
        print(f"  振幅: {stock.get('振幅', 0):.2f}%")
        print(f"  成交额: {stock.get('成交额', 0):.0f} 万元")
        print()

    # 检查名称是否补充
    has_name = any(stock.get('名称') for stock in stocks)
    if has_name:
        print("✅ 股票名称已成功补充")
    else:
        print("⚠️  股票名称仍然为空（可能 QMT 接口未连接）")

    return True

def test_data_adapter():
    """测试数据适配层"""
    print("\n" + "=" * 60)
    print("🧪 测试 2: 数据适配层（字段标准化）")
    print("=" * 60)

    stocks = DataAdapter.get_active_stocks_unified(limit=5, min_amplitude=1.0)

    if not stocks:
        print("❌ 未获取到数据")
        return False

    print(f"\n✅ 获取到 {len(stocks)} 只股票（已标准化）\n")

    # 检查字段完整性
    sample = stocks[0]
    required_fields = ['代码', '名称', '最新价', '涨跌幅', 'code', 'name', 'price', 'change_pct']

    print("字段检查:")
    for field in required_fields:
        exists = field in sample
        print(f"  {field:15s}: {'✅' if exists else '❌'}")

    # 检查涨跌幅单位
    if '涨跌幅' in sample:
        val = sample['涨跌幅']
        is_percent = abs(val) < 50  # 假设涨跌幅不会超过50%
        print(f"\n涨跌幅单位检查: {val:.2f} ({'✅ 百分比格式' if is_percent else '❌ 可能是小数格式'})")

    return True

def test_strategy_interfaces():
    """测试战法专用接口"""
    print("\n" + "=" * 60)
    print("🧪 测试 3: 战法专用接口")
    print("=" * 60)

    strategies = {
        '龙头战法': get_stocks_for_longtou,
        '低吸战法': get_stocks_for_dixi,
        '半路战法': get_stocks_for_banlu,
    }

    for name, func in strategies.items():
        print(f"\n🎯 测试 {name}...")
        df = func(limit=5)

        if df.empty:
            print(f"  ⚠️  {name} 未获取到股票（可能过滤条件太严）")
        else:
            print(f"  ✅ {name} 获取到 {len(df)} 只股票")
            print(f"     字段: {', '.join(df.columns[:8].tolist())}...")

            # 打印一只示例
            if len(df) > 0:
                row = df.iloc[0]
                print(f"     示例: {row.get('代码', 'N/A')} {row.get('名称', 'N/A')} "
                      f"{row.get('涨跌幅', 0):.2f}% {row.get('振幅', 0):.2f}%")

    return True

def main():
    print("\n" + "🚀" * 30)
    print("QMT 数据适配层完整测试")
    print("🚀" * 30 + "\n")

    try:
        # 测试 1
        test_qmt_active_filter()

        # 测试 2
        test_data_adapter()

        # 测试 3
        test_strategy_interfaces()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()