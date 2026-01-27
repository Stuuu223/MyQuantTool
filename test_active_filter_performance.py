#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
活跃股筛选器性能测试脚本
测试 ActiveStockFilter 的性能和正确性

Author: iFlow CLI
Version: V19.13
"""

import time
import sys
from logic.active_stock_filter import get_active_stocks
from logic.logger import get_logger

logger = get_logger(__name__)


def test_active_filter_performance():
    """测试活跃股筛选器的性能"""
    print("=" * 60)
    print("🚀 活跃股筛选器性能测试")
    print("=" * 60)

    # 测试1：基础功能测试
    print("\n📊 测试1: 基础功能测试（获取100只活跃股）")
    start_time = time.time()
    try:
        stocks = get_active_stocks(limit=100, sort_by='amount', skip_top=30)
        elapsed = time.time() - start_time

        print(f"✅ 成功！耗时: {elapsed:.2f}秒")
        print(f"📈 返回股票数量: {len(stocks)}")

        if stocks:
            print(f"\n🔍 Top 10 活跃股:")
            for i, stock in enumerate(stocks[:10], 1):
                print(f"  {i}. {stock['code']} {stock['name']} - 成交额: {stock['amount']:.0f}元, 涨跌幅: {stock['change_pct']:.2f}%")
        else:
            print("⚠️ 返回空列表")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试2：20cm标的筛选
    print("\n📊 测试2: 20cm标的筛选（只扫描300/688）")
    start_time = time.time()
    try:
        stocks_20cm = get_active_stocks(limit=50, only_20cm=True, skip_top=0)
        elapsed = time.time() - start_time

        print(f"✅ 成功！耗时: {elapsed:.2f}秒")
        print(f"📈 返回20cm股票数量: {len(stocks_20cm)}")

        if stocks_20cm:
            print(f"\n🔍 Top 10 20cm活跃股:")
            for i, stock in enumerate(stocks_20cm[:10], 1):
                print(f"  {i}. {stock['code']} {stock['name']} - 成交额: {stock['amount']:.0f}元, 涨跌幅: {stock['change_pct']:.2f}%")
        else:
            print("⚠️ 返回空列表")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试3：涨幅筛选
    print("\n📊 测试3: 涨幅筛选（2.5%-8%）")
    start_time = time.time()
    try:
        stocks_filtered = get_active_stocks(
            limit=50,
            min_change_pct=2.5,
            max_change_pct=8.0,
            sort_by='change_pct',
            skip_top=30
        )
        elapsed = time.time() - start_time

        print(f"✅ 成功！耗时: {elapsed:.2f}秒")
        print(f"📈 返回股票数量: {len(stocks_filtered)}")

        if stocks_filtered:
            print(f"\n🔍 Top 10 涨幅在2.5%-8%的活跃股:")
            for i, stock in enumerate(stocks_filtered[:10], 1):
                print(f"  {i}. {stock['code']} {stock['name']} - 涨跌幅: {stock['change_pct']:.2f}%, 成交额: {stock['amount']:.0f}元")
        else:
            print("⚠️ 返回空列表")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试4：性能压力测试（获取200只股票）
    print("\n📊 测试4: 性能压力测试（获取200只活跃股）")
    start_time = time.time()
    try:
        stocks_stress = get_active_stocks(limit=200, sort_by='amount', skip_top=30)
        elapsed = time.time() - start_time

        print(f"✅ 成功！耗时: {elapsed:.2f}秒")
        print(f"📈 返回股票数量: {len(stocks_stress)}")
        print(f"⚡ 平均每只股票处理时间: {elapsed/len(stocks_stress)*1000:.2f}毫秒")

        if stocks_stress:
            print(f"\n🔍 Top 5 活跃股:")
            for i, stock in enumerate(stocks_stress[:5], 1):
                print(f"  {i}. {stock['code']} {stock['name']} - 成交额: {stock['amount']:.0f}元, 涨跌幅: {stock['change_pct']:.2f}%")
        else:
            print("⚠️ 返回空列表")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_active_filter_performance()
    sys.exit(0 if success else 1)
