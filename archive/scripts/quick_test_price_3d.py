#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试脚本 - 验证 price_3d_change 修复效果

目标：
1. 模拟扫描几只股票
2. 验证 price_3d_change 是否正常计算
3. 输出详细的计算日志
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logic.full_market_scanner import FullMarketScanner
from logic.logger import get_logger

logger = get_logger(__name__)

def main():
    print("=" * 80)
    print("🧪 price_3d_change 修复验证测试")
    print("=" * 80)
    print()

    # 测试股票列表（从之前的扫描结果中选择）
    test_stocks = [
        "002514.SZ",  # 宝馨科技
        "002054.SZ",  # 德美化工
        "002987.SZ",  # 京北方
        "001335.SZ",  # 鸿路钢构（之前被误判的负ratio股票）
    ]

    print(f"📊 测试股票：{len(test_stocks)} 只")
    for stock in test_stocks:
        print(f"   - {stock}")
    print()

    # 初始化扫描器
    print("🔧 初始化扫描器...")
    scanner = FullMarketScanner()
    print("✅ 扫描器初始化完成")
    print()

    # 执行扫描
    print("🚀 开始扫描...")
    print("-" * 80)

    try:
        results = scanner.scan_with_risk_management(
            stock_list=test_stocks,
            mode='intraday'
        )

        # 分析结果
        print()
        print("=" * 80)
        print("📊 扫描结果分析")
        print("=" * 80)
        print()

        # 统计信息
        total = len(test_stocks)
        valid_price_3d = 0
        zero_price_3d = 0

        # 详细结果
        for stock in test_stocks:
            # 在结果中查找该股票
            found = False
            for result in results.get('blacklist', []):
                if result.get('code') == stock:
                    found = True
                    price_3d_change = result.get('price_3d_change', None)
                    ratio = result.get('ratio', None)
                    risk_score = result.get('risk_score', None)
                    decision_tag = result.get('decision_tag', None)
                    scenario_type = result.get('scenario_type', None)

                    print(f"📈 {stock}")
                    print(f"   price_3d_change: {price_3d_change if price_3d_change is not None else 'N/A'}")
                    if price_3d_change is not None and price_3d_change != 0.0:
                        valid_price_3d += 1
                        print(f"   ✅ price_3d_change 正常计算")
                    else:
                        zero_price_3d += 1
                        print(f"   ❌ price_3d_change 为 0 或 None")

                    print(f"   ratio: {ratio if ratio is not None else 'N/A'}")
                    print(f"   risk_score: {risk_score if risk_score is not None else 'N/A'}")
                    print(f"   decision_tag: {decision_tag}")
                    print(f"   scenario_type: {scenario_type}")
                    print()

            if not found:
                print(f"⚠️  {stock} 未在结果中找到")
                print()

        # 总结
        print("=" * 80)
        print("📊 验证总结")
        print("=" * 80)
        print(f"   总测试股票: {total}")
        print(f"   price_3d_change 正常: {valid_price_3d} ({valid_price_3d/total*100:.1f}%)")
        print(f"   price_3d_change 为0/None: {zero_price_3d} ({zero_price_3d/total*100:.1f}%)")
        print()

        if valid_price_3d == total:
            print("✅ 所有测试股票的 price_3d_change 都正常计算！")
            print("🎉 修复验证成功！")
        elif valid_price_3d > 0:
            print(f"⚠️  部分股票的 price_3d_change 正常，但仍有 {zero_price_3d} 只股票失败")
            print("🔍 建议检查日志中的详细错误信息")
        else:
            print("❌ 所有股票的 price_3d_change 都为 0 或 None")
            print("🚨 修复验证失败！需要进一步调查")
        print()

    except Exception as e:
        print(f"❌ 扫描失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()