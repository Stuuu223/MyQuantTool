#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试UI封单金额修复

验证五矿发展 (600058) 的封单金额计算是否正确
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.data_sanitizer import DataSanitizer


def test_ui_seal_amount():
    """测试UI封单金额计算"""
    print("=" * 60)
    print("测试：UI封单金额修复验证")
    print("=" * 60)
    
    # 五矿发展的UI显示数据
    bid1_volume = 1749  # 买一量（手数，UI显示的值）
    price = 12.67  # 价格（元）
    
    # 使用 DataSanitizer 计算
    seal_amount_yuan = DataSanitizer.calculate_amount_from_volume(bid1_volume, price)
    seal_amount_wan = seal_amount_yuan / 10000  # 转换为万
    
    print(f"\n📊 UI数据：")
    print(f"  买一量：{bid1_volume} 手")
    print(f"  价格：¥{price}")
    print(f"  公式：{bid1_volume} × 100 × {price}")
    print(f"  结果：¥{seal_amount_yuan:,.2f} 元")
    print(f"  格式化：{DataSanitizer.format_amount_to_display(seal_amount_yuan)}")
    print(f"  显示：¥{seal_amount_wan:.2f} 万")
    
    # 错误计算（少乘100）
    wrong_amount = bid1_volume * price  # 买一量 × 价格（忘记乘以100）
    wrong_amount_wan = wrong_amount / 10000  # 转换为万
    
    print(f"\n❌ 错误计算（少乘100）：")
    print(f"  买一量：{bid1_volume} 手")
    print(f"  价格：¥{price}")
    print(f"  公式：{bid1_volume} × {price}")
    print(f"  结果：¥{wrong_amount:,.2f} 元")
    print(f"  格式化：{DataSanitizer.format_amount_to_display(wrong_amount)}")
    print(f"  显示：¥{wrong_amount_wan:.2f} 万")
    
    # 验证
    print(f"\n🔍 验证结果：")
    if abs(seal_amount_yuan - 2216299.75) < 0.01:  # 1749 × 100 × 12.67 = 221,629,975
        print(f"  ✅ 计算正确！")
        print(f"  正确值：{DataSanitizer.format_amount_to_display(seal_amount_yuan)}")
        print(f"  显示值：¥{seal_amount_wan:.2f} 万")
    else:
        print(f"  ❌ 计算错误！")
        print(f"  期望值：221.63 万")
        print(f"  计算值：¥{seal_amount_wan:.2f} 万")
    
    # 错误倍数
    error_ratio = seal_amount_yuan / wrong_amount
    print(f"\n📈 错误倍数：")
    print(f"  正确值：¥{seal_amount_yuan:,.2f}")
    print(f"  错误值：¥{wrong_amount:,.2f}")
    print(f"  倍数：{error_ratio:.2f} 倍")
    print(f"  结论：错误值比正确值小了 {error_ratio:.2f} 倍（即少乘了100）")


def test_auction_volume():
    """测试竞价量计算"""
    print("\n" + "=" * 60)
    print("测试：竞价量计算")
    print("=" * 60)
    
    # 五矿发展的竞价量数据
    auction_volume = 174925  # 竞价量（手数）
    price = 12.67  # 价格（元）
    
    # 使用 DataSanitizer 计算
    auction_amount_yuan = DataSanitizer.calculate_amount_from_volume(auction_volume, price)
    auction_amount_wan = auction_amount_yuan / 10000  # 转换为万
    
    print(f"\n📊 竞价量数据：")
    print(f"  竞价量：{auction_volume} 手")
    print(f"  价格：¥{price}")
    print(f"  公式：{auction_volume} × 100 × {price}")
    print(f"  结果：¥{auction_amount_yuan:,.2f} 元")
    print(f"  格式化：{DataSanitizer.format_amount_to_display(auction_amount_yuan)}")
    print(f"  显示：¥{auction_amount_wan:.2f} 万")
    
    # 验证
    print(f"\n🔍 验证结果：")
    if abs(auction_amount_yuan - 221629975) < 0.01:  # 174925 × 100 × 12.67 = 2,216,299,750
        print(f"  ✅ 计算正确！")
        print(f"  正确值：{DataSanitizer.format_amount_to_display(auction_amount_yuan)}")
        print(f"  显示值：¥{auction_amount_wan:.2f} 万")
    else:
        print(f"  ❌ 计算错误！")
        print(f"  期望值：2.21 亿")
        print(f"  计算值：¥{auction_amount_wan:.2f} 万")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("UI封单金额修复测试")
    print("=" * 60 + "\n")
    
    # 运行所有测试
    test_ui_seal_amount()
    test_auction_volume()
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)
    print("\n💡 说明：")
    print("- UI显示的买一量：1749 手 → 封单金额应该是 2.22 万")
    print("- 竞价量：174925 手 → 竞价金额应该是 2.21 亿")
    print("- 如果UI显示的封单金额是 221.60 万，说明用了竞价量且少乘了100")
    print("- 修复后，UI应该正确显示买一量的封单金额")


if __name__ == "__main__":
    main()