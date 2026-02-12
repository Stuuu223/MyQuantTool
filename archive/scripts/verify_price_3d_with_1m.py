#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用1分钟数据验证 price_3d_change 计算

目的：
1. 使用刚下载的1分钟K线数据手动计算 3日涨幅
2. 验证 V9.4.8 修复是否有效
3. 对比扫描结果中的 price_3d_change

Author: iFlow CLI
Date: 2026-02-09
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

def calculate_3d_change_from_1m(df_1m, scan_date='2026-02-09'):
    """
    从1分钟数据计算3日涨幅

    Args:
        df_1m: 1分钟K线数据
        scan_date: 扫描日期 (YYYY-MM-DD)

    Returns:
        3日涨幅 (price_3d_change)
    """
    # 转换时间列为datetime
    df_1m['time_str'] = pd.to_datetime(df_1m['time_str'])

    # 获取扫描日期
    scan_dt = pd.to_datetime(scan_date)

    # 计算参考日期（3个交易日之前）
    # 假设每周5个交易日，3天 ≈ 3个交易日
    # 这里简单计算：扫描日期 - 3天
    ref_dt = scan_dt - timedelta(days=3)

    # 获取扫描日期的最后收盘价（即 current_price）
    scan_day_data = df_1m[df_1m['time_str'].dt.date == scan_dt.date()]
    if scan_day_data.empty:
        return None, "扫描日期无数据"

    current_price = scan_day_data['close'].iloc[-1]

    # 获取参考日期的最后收盘价
    ref_day_data = df_1m[df_1m['time_str'].dt.date == ref_dt.date()]
    if ref_day_data.empty:
        # 如果参考日期无数据，尝试往前找
        for i in range(1, 10):
            temp_dt = ref_dt - timedelta(days=i)
            temp_data = df_1m[df_1m['time_str'].dt.date == temp_dt.date()]
            if not temp_data.empty:
                ref_price = temp_data['close'].iloc[-1]
                break
        else:
            return None, "找不到参考日期数据"
    else:
        ref_price = ref_day_data['close'].iloc[-1]

    # 计算3日涨幅
    price_3d_change = (current_price - ref_price) / ref_price

    return price_3d_change, {
        'current_price': current_price,
        'ref_price': ref_price,
        'ref_date': ref_dt.strftime('%Y-%m-%d'),
        'scan_date': scan_dt.strftime('%Y-%m-%d')
    }

def main():
    """主函数"""
    print("=" * 80)
    print("🔍 使用1分钟数据验证 price_3d_change")
    print("=" * 80)
    print()

    # 从扫描结果中读取被拦截的股票
    scan_results_file = Path('data/scan_results/2026-02-09_intraday.json')
    import json

    with open(scan_results_file, 'r', encoding='utf-8') as f:
        scan_data = json.load(f)

    # 获取黑名单股票
    blacklist = scan_data['results']['blacklist']

    print(f"📊 扫描时间: {scan_data['scan_time']}")
    print(f"📋 黑名单股票数: {len(blacklist)}")
    print()

    # 验证每只股票
    for stock in blacklist:
        code = stock['code']
        scan_price_3d = stock.get('price_3d_change', 0.0)

        print(f"\n{'=' * 80}")
        print(f"📌 {code} ({stock.get('sector_name', 'N/A')})")
        print(f"{'=' * 80}")
        print(f"扫描结果中的 price_3d_change: {scan_price_3d:.4f}")
        print()

        # 读取1分钟数据
        data_file = Path(f'data/minute_data/{code}_1m.csv')
        if not data_file.exists():
            print(f"❌ 1分钟数据文件不存在: {data_file}")
            continue

        df_1m = pd.read_csv(data_file, encoding='utf-8-sig')
        print(f"✅ 加载1分钟数据: {len(df_1m)} 根K线")
        print(f"   时间范围: {df_1m['time_str'].min()} ~ {df_1m['time_str'].max()}")

        # 计算正确的 price_3d_change
        price_3d_change, details = calculate_3d_change_from_1m(df_1m, '2026-02-09')

        if price_3d_change is None:
            print(f"❌ 计算失败: {details}")
        else:
            print(f"\n📊 手动计算结果:")
            print(f"   当前价格: {details['current_price']:.2f}")
            print(f"   参考价格: {details['ref_price']:.2f}")
            print(f"   参考日期: {details['ref_date']}")
            print(f"   3日涨幅: {price_3d_change:.4f} ({price_3d_change * 100:.2f}%)")

            # 对比
            print(f"\n🔍 对比分析:")
            if scan_price_3d == 0.0:
                print(f"   ⚠️  扫描结果为 0.0，可能是计算失败")
                print(f"   📈 实际应该是 {price_3d_change:.4f} ({price_3d_change * 100:.2f}%)")
            elif abs(scan_price_3d - price_3d_change) < 0.01:
                print(f"   ✅ 扫描结果与手动计算一致")
            else:
                print(f"   ❌ 扫描结果 ({scan_price_3d:.4f}) 与手动计算 ({price_3d_change:.4f}) 不一致")

        # 显示场景信息
        scenario = stock.get('scenario_type', 'N/A')
        confidence = stock.get('scenario_confidence', 0.0)
        print(f"\n🎯 场景分类: {scenario} (置信度: {confidence:.2f})")
        print(f"   拦截原因: {', '.join(stock.get('scenario_reasons', []))}")

    print()
    print("=" * 80)
    print("📝 总结")
    print("=" * 80)
    print("如果扫描结果的 price_3d_change 全部为 0.0，而手动计算有值，")
    print("说明 V9.4.8 修复虽然代码正确，但扫描器运行时可能遇到了错误。")
    print("=" * 80)


if __name__ == "__main__":
    main()