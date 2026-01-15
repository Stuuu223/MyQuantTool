"""
V8.5 竞价抢筹度修复测试脚本

测试内容：
1. 五矿发展 (600058) 案例验证
2. 标准竞价抢筹度计算器功能测试
3. 异常值检测和修正功能测试
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.algo_math import calculate_true_auction_aggression


def test_wu_kuang_fa_zhan_case():
    """测试五矿发展 (600058) 案例"""
    print("=" * 60)
    print("测试 1: 五矿发展 (600058) 案例验证")
    print("=" * 60)
    
    # 五矿发展的真实数据
    auction_vol = 174925  # 竞价成交量（手）
    
    # 测试用例1：假设昨日成交量是 50万手（正常情况）
    prev_day_vol = 500000  # 昨日成交量（手）
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol)
    expected = 34.99  # 174925 / 500000 * 100 = 34.99%
    print(f"测试用例1（昨日成交量50万手）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手")
    print(f"  期望输出: {expected}%")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if abs(result - expected) < 0.1 else '❌ 失败'}")
    print()
    
    # 测试用例2：假设昨日成交量是 30万手（正常情况）
    prev_day_vol = 300000  # 昨日成交量（手）
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol)
    expected = 58.31  # 174925 / 300000 * 100 = 58.31%
    print(f"测试用例2（昨日成交量30万手）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手")
    print(f"  期望输出: {expected}%")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if abs(result - expected) < 0.1 else '❌ 失败'}")
    print()
    
    # 测试用例3：模拟错误数据（昨日成交量是分钟均量）
    prev_day_vol = 2525  # 昨日成交量（手，实际是分钟均量）
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol)
    # 174925 / 2525 = 69.28，应该被修正为合理范围
    print(f"测试用例3（昨日成交量是分钟均量2525手）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手（实际是分钟均量）")
    print(f"  期望输出: 应该被修正为合理范围（< 1000%）")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if result < 1000 else '❌ 失败'}")
    print()


def test_normal_cases():
    """测试正常情况"""
    print("=" * 60)
    print("测试 2: 正常情况测试")
    print("=" * 60)
    
    # 测试用例1：正常抢筹（5% - 10%）
    auction_vol = 50000  # 竞价成交量（手）
    prev_day_vol = 1000000  # 昨日成交量（手）
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol)
    expected = 5.0  # 50000 / 1000000 * 100 = 5.0%
    print(f"测试用例1（正常抢筹5%）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手")
    print(f"  期望输出: {expected}%")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if abs(result - expected) < 0.1 else '❌ 失败'}")
    print()
    
    # 测试用例2：强势抢筹（10% - 20%）
    auction_vol = 150000  # 竞价成交量（手）
    prev_day_vol = 1000000  # 昨日成交量（手）
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol)
    expected = 15.0  # 150000 / 1000000 * 100 = 15.0%
    print(f"测试用例2（强势抢筹15%）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手")
    print(f"  期望输出: {expected}%")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if abs(result - expected) < 0.1 else '❌ 失败'}")
    print()
    
    # 测试用例3：妖股级别（20% - 50%）
    auction_vol = 300000  # 竞价成交量（手）
    prev_day_vol = 1000000  # 昨日成交量（手）
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol)
    expected = 30.0  # 300000 / 1000000 * 100 = 30.0%
    print(f"测试用例3（妖股级别30%）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手")
    print(f"  期望输出: {expected}%")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if abs(result - expected) < 0.1 else '❌ 失败'}")
    print()


def test_edge_cases():
    """测试边缘情况"""
    print("=" * 60)
    print("测试 3: 边缘情况测试")
    print("=" * 60)
    
    # 测试用例1：竞价量为0
    auction_vol = 0  # 竞价成交量（手）
    prev_day_vol = 1000000  # 昨日成交量（手）
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol)
    expected = 0.0
    print(f"测试用例1（竞价量为0）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手")
    print(f"  期望输出: {expected}%")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if result == expected else '❌ 失败'}")
    print()
    
    # 测试用例2：昨日成交量为0（使用兜底逻辑）
    auction_vol = 50000  # 竞价成交量（手）
    prev_day_vol = 0  # 昨日成交量（手）
    circulating_cap = 100000000  # 流通股本（股）
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol, circulating_cap, is_new_stock=False)
    print(f"测试用例2（昨日成交量为0，使用兜底逻辑）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手")
    print(f"  流通盘: {circulating_cap} 股")
    print(f"  期望输出: 应该使用兜底逻辑计算")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if result > 0 else '❌ 失败'}")
    print()
    
    # 测试用例3：昨日成交量过小（< 1000手）
    auction_vol = 50000  # 竞价成交量（手）
    prev_day_vol = 500  # 昨日成交量（手）
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol)
    print(f"测试用例3（昨日成交量过小500手）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手")
    print(f"  期望输出: 应该被修正为合理范围")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if result < 1000 else '❌ 失败'}")
    print()


def test_new_stock_cases():
    """测试新股情况"""
    print("=" * 60)
    print("测试 4: 新股情况测试")
    print("=" * 60)
    
    # 测试用例1：新股正常抢筹
    auction_vol = 200000  # 竞价成交量（手）
    prev_day_vol = 500000  # 昨日成交量（手）
    circulating_cap = 50000000  # 流通股本（股）
    is_new_stock = True
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol, circulating_cap, is_new_stock)
    expected = 40.0  # 200000 / 500000 * 100 = 40.0%
    print(f"测试用例1（新股正常抢筹40%）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手")
    print(f"  流通盘: {circulating_cap} 股")
    print(f"  是否新股: {is_new_stock}")
    print(f"  期望输出: {expected}%")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if abs(result - expected) < 0.1 else '❌ 失败'}")
    print()
    
    # 测试用例2：新股昨日成交量为0（使用兜底逻辑）
    auction_vol = 200000  # 竞价成交量（手）
    prev_day_vol = 0  # 昨日成交量（手）
    circulating_cap = 50000000  # 流通股本（股）
    is_new_stock = True
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol, circulating_cap, is_new_stock)
    print(f"测试用例2（新股昨日成交量为0，使用兜底逻辑）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手")
    print(f"  流通盘: {circulating_cap} 股")
    print(f"  是否新股: {is_new_stock}")
    print(f"  期望输出: 应该使用兜底逻辑计算（基准量为流通盘的5%）")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if result > 0 else '❌ 失败'}")
    print()


def test_abnormal_cases():
    """测试异常情况"""
    print("=" * 60)
    print("测试 5: 异常情况测试")
    print("=" * 60)
    
    # 测试用例1：极端异常值（模拟 6900% 的情况）
    auction_vol = 174925  # 竞价成交量（手）
    prev_day_vol = 2525  # 昨日成交量（手，实际是分钟均量）
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol)
    # 174925 / 2525 = 69.28，应该被修正为合理范围
    print(f"测试用例1（极端异常值6900%）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手（实际是分钟均量）")
    print(f"  原始比值: {auction_vol / prev_day_vol:.2f} 倍")
    print(f"  期望输出: 应该被修正为合理范围（< 1000%）")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if result < 1000 else '❌ 失败'}")
    print()
    
    # 测试用例2：单位错误（股 vs 手）
    auction_vol = 174925  # 竞价成交量（手）
    prev_day_vol = 2500  # 昨日成交量（手，实际是股，需要除以100）
    result = calculate_true_auction_aggression(auction_vol, prev_day_vol)
    # 174925 / 2500 = 69.97，应该被修正为合理范围
    print(f"测试用例2（单位错误股vs手）:")
    print(f"  竞价量: {auction_vol} 手")
    print(f"  昨日量: {prev_day_vol} 手（实际是股）")
    print(f"  原始比值: {auction_vol / prev_day_vol:.2f} 倍")
    print(f"  期望输出: 应该被修正为合理范围（< 1000%）")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if result < 1000 else '❌ 失败'}")
    print()


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("V8.5 竞价抢筹度修复测试")
    print("=" * 60 + "\n")
    
    # 运行所有测试
    test_wu_kuang_fa_zhan_case()
    test_normal_cases()
    test_edge_cases()
    test_new_stock_cases()
    test_abnormal_cases()
    
    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()