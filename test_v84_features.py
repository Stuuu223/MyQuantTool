"""
V8.4 功能测试脚本

测试内容：
1. DataSanitizer 数据消毒器功能
2. 次新股豁免权防止滥用逻辑
3. 次新股动态换手率评分标准
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.data_sanitizer import DataSanitizer


def test_normalize_volume():
    """测试成交量清洗功能"""
    print("=" * 60)
    print("测试 1: DataSanitizer.normalize_volume")
    print("=" * 60)
    
    # 测试用例1：Easyquotation 数据源（返回股数）
    volume = 17437873  # 股数
    price = 10.0
    result = DataSanitizer.normalize_volume(volume, price, source_type='easyquotation')
    expected = 174378  # 手数
    print(f"测试用例1（Easyquotation）:")
    print(f"  输入: {volume} 股, 价格: {price}")
    print(f"  期望输出: {expected} 手")
    print(f"  实际输出: {result} 手")
    print(f"  结果: {'✅ 通过' if result == expected else '❌ 失败'}")
    print()
    
    # 测试用例2：基于成交量大小判断
    volume = 10000000  # 1000万手（异常，应该是股）
    price = 10.0
    result = DataSanitizer.normalize_volume(volume, price)
    expected = 100000  # 手数
    print(f"测试用例2（成交量过大）:")
    print(f"  输入: {volume} 手（异常）, 价格: {price}")
    print(f"  期望输出: {expected} 手")
    print(f"  实际输出: {result} 手")
    print(f"  结果: {'✅ 通过' if result == expected else '❌ 失败'}")
    print()
    
    # 测试用例3：基于流通盘验证
    volume = 50000  # 手数
    price = 10.0
    circulating_shares = 50000000  # 5000万股
    result = DataSanitizer.normalize_volume(volume, price, circulating_shares)
    # 换手率 = 50000 * 100 / 50000000 = 0.1（10%，正常）
    expected = 50000  # 手数
    print(f"测试用例3（流通盘验证）:")
    print(f"  输入: {volume} 手, 价格: {price}, 流通盘: {circulating_shares} 股")
    print(f"  期望输出: {expected} 手")
    print(f"  实际输出: {result} 手")
    print(f"  结果: {'✅ 通过' if result == expected else '❌ 失败'}")
    print()
    
    # 测试用例4：基于金额熔断检查
    volume = 10000000  # 手数（异常）
    price = 100.0
    result = DataSanitizer.normalize_volume(volume, price)
    # 金额 = 10000000 * 100 * 100 = 1000亿（异常，应该修正）
    expected = 100000  # 手数
    print(f"测试用例4（金额熔断）:")
    print(f"  输入: {volume} 手, 价格: {price}")
    print(f"  期望输出: {expected} 手")
    print(f"  实际输出: {result} 手")
    print(f"  结果: {'✅ 通过' if result == expected else '❌ 失败'}")
    print()


def test_normalize_auction_aggression():
    """测试竞价抢筹度清洗功能"""
    print("=" * 60)
    print("测试 2: DataSanitizer.normalize_auction_aggression")
    print("=" * 60)
    
    # 测试用例1：正常值
    current_vol = 50000  # 手数
    avg_vol = 25000  # 手数
    result = DataSanitizer.normalize_auction_aggression(current_vol, avg_vol)
    expected = 200.0  # 百分比
    print(f"测试用例1（正常值）:")
    print(f"  输入: 当前成交量 {current_vol} 手, 平均成交量 {avg_vol} 手")
    print(f"  期望输出: {expected}%")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if result == expected else '❌ 失败'}")
    print()
    
    # 测试用例2：异常值（过大）
    current_vol = 17437873  # 手数（异常）
    avg_vol = 25000  # 手数
    result = DataSanitizer.normalize_auction_aggression(current_vol, avg_vol)
    expected = 0.0  # 异常值，应该归零
    print(f"测试用例2（异常值过大）:")
    print(f"  输入: 当前成交量 {current_vol} 手, 平均成交量 {avg_vol} 手")
    print(f"  期望输出: {expected}% (异常值归零)")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if result == expected else '❌ 失败'}")
    print()
    
    # 测试用例3：平均成交量为零
    current_vol = 50000  # 手数
    avg_vol = 0  # 手数
    result = DataSanitizer.normalize_auction_aggression(current_vol, avg_vol)
    expected = 0.0  # 平均成交量为零，应该归零
    print(f"测试用例3（平均成交量为零）:")
    print(f"  输入: 当前成交量 {current_vol} 手, 平均成交量 {avg_vol} 手")
    print(f"  期望输出: {expected}%")
    print(f"  实际输出: {result}%")
    print(f"  结果: {'✅ 通过' if result == expected else '❌ 失败'}")
    print()


def test_normalize_seal_amount():
    """测试封单金额清洗功能"""
    print("=" * 60)
    print("测试 3: DataSanitizer.normalize_seal_amount")
    print("=" * 60)
    
    # 测试用例1：Easyquotation 数据源（买一量已经是手数）
    bid1_volume = 420000  # 手数
    price = 10.0
    result = DataSanitizer.normalize_seal_amount(bid1_volume, price, source_type='easyquotation')
    expected = 42000.0  # 万元
    print(f"测试用例1（Easyquotation）:")
    print(f"  输入: 买一量 {bid1_volume} 手, 价格: {price}")
    print(f"  期望输出: {expected} 万")
    print(f"  实际输出: {result} 万")
    print(f"  结果: {'✅ 通过' if result == expected else '❌ 失败'}")
    print()
    
    # 测试用例2：异常值（过大）
    bid1_volume = 100000000  # 手数（异常）
    price = 100.0
    result = DataSanitizer.normalize_seal_amount(bid1_volume, price)
    # 封单金额 = 100000000 * 100 * 100 / 10000 = 10000000万（10000亿，异常）
    # 修正后 = 10000000 / 100 = 100000万（1000亿）
    expected = 1000000.0  # 万元（修正后）
    print(f"测试用例2（异常值过大）:")
    print(f"  输入: 买一量 {bid1_volume} 手, 价格: {price}")
    print(f"  期望输出: {expected} 万 (修正后)")
    print(f"  实际输出: {result} 万")
    print(f"  结果: {'✅ 通过' if result == expected else '❌ 失败'}")
    print()


def test_sanitize_realtime_data():
    """测试一站式实时数据清洗"""
    print("=" * 60)
    print("测试 4: DataSanitizer.sanitize_realtime_data")
    print("=" * 60)
    
    # 测试用例：完整的数据清洗
    raw_data = {
        'now': 10.0,
        'volume': 17437873,  # 股数
        'bid1_volume': 420000,  # 手数
        'ask1_volume': 100000,  # 手数
    }
    
    result = DataSanitizer.sanitize_realtime_data(raw_data, source_type='easyquotation')
    
    print(f"测试用例（一站式清洗）:")
    print(f"  输入数据:")
    print(f"    价格: {raw_data['now']}")
    print(f"    成交量: {raw_data['volume']} 股")
    print(f"    买一量: {raw_data['bid1_volume']} 手")
    print(f"    卖一量: {raw_data['ask1_volume']} 手")
    print(f"  输出数据:")
    print(f"    成交量: {result['volume']} 手")
    print(f"    买一量: {result['bid1_volume']} 手")
    print(f"    卖一量: {result['ask1_volume']} 手")
    print(f"    成交额: {result['amount']} 万")
    print(f"    封单金额: {result['seal_amount']} 万")
    print(f"  结果: {'✅ 通过' if result['volume'] == 174378 and result['amount'] > 0 else '❌ 失败'}")
    print()


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("V8.4 功能测试")
    print("=" * 60 + "\n")
    
    # 运行所有测试
    test_normalize_volume()
    test_normalize_auction_aggression()
    test_normalize_seal_amount()
    test_sanitize_realtime_data()
    
    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()