"""
测试封单金额计算修复

验证五矿发展 (600058) 的封单金额计算是否正确
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.data_sanitizer import DataSanitizer


def test_wu_kuang_fa_zhan_seal_amount():
    """测试五矿发展封单金额计算"""
    print("=" * 60)
    print("测试：五矿发展 (600058) 封单金额计算")
    print("=" * 60)
    
    # 五矿发展的真实数据
    bid1_volume = 174925  # 买一量（手数）
    price = 12.67  # 价格（元）
    
    # 正确计算
    correct_amount = bid1_volume * 100 * price  # 手数 * 100 * 价格
    print(f"\n📊 正确计算：")
    print(f"  买一量：{bid1_volume} 手")
    print(f"  价格：¥{price}")
    print(f"  公式：{bid1_volume} × 100 × {price}")
    print(f"  结果：¥{correct_amount:,.2f} 元")
    print(f"  格式化：{DataSanitizer.format_amount_to_display(correct_amount)}")
    
    # 错误计算（少乘100）
    wrong_amount = bid1_volume * price  # 手数 * 价格（忘记乘以100）
    print(f"\n❌ 错误计算（少乘100）：")
    print(f"  买一量：{bid1_volume} 手")
    print(f"  价格：¥{price}")
    print(f"  公式：{bid1_volume} × {price}")
    print(f"  结果：¥{wrong_amount:,.2f} 元")
    print(f"  格式化：{DataSanitizer.format_amount_to_display(wrong_amount)}")
    
    # 使用DataSanitizer计算
    sanitized_amount = DataSanitizer.calculate_amount_from_volume(bid1_volume, price)
    print(f"\n✅ DataSanitizer计算：")
    print(f"  结果：¥{sanitized_amount:,.2f} 元")
    print(f"  格式化：{DataSanitizer.format_amount_to_display(sanitized_amount)}")
    
    # 验证
    print(f"\n🔍 验证结果：")
    if abs(sanitized_amount - correct_amount) < 0.01:
        print(f"  ✅ DataSanitizer计算正确！")
        print(f"  正确值：{DataSanitizer.format_amount_to_display(correct_amount)}")
        print(f"  计算值：{DataSanitizer.format_amount_to_display(sanitized_amount)}")
    else:
        print(f"  ❌ DataSanitizer计算错误！")
        print(f"  正确值：{DataSanitizer.format_amount_to_display(correct_amount)}")
        print(f"  计算值：{DataSanitizer.format_amount_to_display(sanitized_amount)}")
    
    # 错误倍数
    error_ratio = correct_amount / wrong_amount
    print(f"\n📈 错误倍数：")
    print(f"  正确值：¥{correct_amount:,.2f}")
    print(f"  错误值：¥{wrong_amount:,.2f}")
    print(f"  倍数：{error_ratio:.2f} 倍")
    print(f"  结论：错误值比正确值小了 {error_ratio:.2f} 倍（即少乘了100）")


def test_other_cases():
    """测试其他案例"""
    print("\n" + "=" * 60)
    print("测试：其他案例")
    print("=" * 60)
    
    test_cases = [
        {"name": "山河药辅", "bid1_volume": 420000, "price": 10.0},
        {"name": "神思电子", "bid1_volume": 100000, "price": 15.5},
        {"name": "宏工科技", "bid1_volume": 50000, "price": 25.0},
    ]
    
    for case in test_cases:
        print(f"\n📊 {case['name']}：")
        correct_amount = case['bid1_volume'] * 100 * case['price']
        sanitized_amount = DataSanitizer.calculate_amount_from_volume(case['bid1_volume'], case['price'])
        
        print(f"  买一量：{case['bid1_volume']:,} 手")
        print(f"  价格：¥{case['price']}")
        print(f"  正确值：{DataSanitizer.format_amount_to_display(correct_amount)}")
        print(f"  计算值：{DataSanitizer.format_amount_to_display(sanitized_amount)}")
        
        if abs(sanitized_amount - correct_amount) < 0.01:
            print(f"  ✅ 计算正确")
        else:
            print(f"  ❌ 计算错误")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("封单金额计算修复测试")
    print("=" * 60 + "\n")
    
    # 运行所有测试
    test_wu_kuang_fa_zhan_seal_amount()
    test_other_cases()
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()