#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试脚本 V2 - 直接测试 Level 2 price_3d_change 计算

目标：
1. 绕过 Level 1，直接测试 Level 2 的 price_3d_change 计算
2. 验证 AkShare 降级逻辑是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logic.code_converter import CodeConverter
from logic.fund_flow_analyzer import FundFlowAnalyzer
from logic.logger import get_logger

logger = get_logger(__name__)

def calculate_price_3d_change(code, current_price):
    """
    计算 price_3d_change（模拟 Level 2 的逻辑）
    """
    price_3d_change = 0.0

    try:
        import akshare as ak
        symbol_6 = CodeConverter.to_akshare(code)
        # 获取最近5天数据（包含今天）
        df = ak.stock_zh_a_hist(symbol=symbol_6, period='daily', start_date='20250101', adjust='qfq')
        if df is not None and len(df) >= 2:
            # 使用倒数第4天的收盘价（3天前）
            if len(df) >= 4:
                ref_close = df.iloc[-4]['收盘']
            else:
                ref_close = df.iloc[0]['收盘']

            if ref_close > 0:
                price_3d_change = (current_price - ref_close) / ref_close
                logger.info(f"✅ {code} 使用AkShare计算price_3d_change={price_3d_change:.4f}")
            else:
                logger.warning(f"⚠️  {code} AkShare ref_close=0，无法计算price_3d_change")
        else:
            logger.warning(f"⚠️  {code} AkShare K线数据不足 (len={len(df) if df is not None else 0})，无法计算price_3d_change")
    except Exception as e:
        logger.warning(f"⚠️  {code} AkShare获取K线失败: {e}，无法计算price_3d_change")

    return price_3d_change

def main():
    print("=" * 80)
    print("🧪 price_3d_change AkShare 降级测试")
    print("=" * 80)
    print()

    # 测试股票列表
    test_stocks = [
        ("002514.SZ", 10.50),  # 宝馨科技（假设价格）
        ("002054.SZ", 8.20),   # 德美化工（假设价格）
        ("002987.SZ", 25.30),  # 京北方（假设价格）
        ("001335.SZ", 18.50),  # 鸿路钢构（假设价格）
    ]

    print(f"📊 测试股票：{len(test_stocks)} 只")
    for code, price in test_stocks:
        print(f"   - {code} (假设价格: {price})")
    print()

    print("🚀 开始计算 price_3d_change...")
    print("-" * 80)

    valid_count = 0
    zero_count = 0

    for code, current_price in test_stocks:
        price_3d_change = calculate_price_3d_change(code, current_price)

        print(f"📈 {code}")
        print(f"   假设价格: {current_price}")
        print(f"   price_3d_change: {price_3d_change:.4f}")

        if price_3d_change != 0.0:
            valid_count += 1
            print(f"   ✅ price_3d_change 正常计算")
        else:
            zero_count += 1
            print(f"   ❌ price_3d_change 为 0")
        print()

    # 总结
    print("=" * 80)
    print("📊 验证总结")
    print("=" * 80)
    print(f"   总测试股票: {len(test_stocks)}")
    print(f"   price_3d_change 正常: {valid_count} ({valid_count/len(test_stocks)*100:.1f}%)")
    print(f"   price_3d_change 为0: {zero_count} ({zero_count/len(test_stocks)*100:.1f}%)")
    print()

    if valid_count == len(test_stocks):
        print("✅ 所有测试股票的 price_3d_change 都正常计算！")
        print("🎉 AkShare 降级逻辑验证成功！")
    elif valid_count > 0:
        print(f"⚠️  部分股票的 price_3d_change 正常，但仍有 {zero_count} 只股票失败")
        print("🔍 建议检查日志中的详细错误信息")
    else:
        print("❌ 所有股票的 price_3d_change 都为 0")
        print("🚨 AkShare 降级逻辑验证失败！")
    print()

if __name__ == "__main__":
    main()