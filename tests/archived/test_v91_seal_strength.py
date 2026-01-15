"""
V9.1 封单强度熔断测试脚本

测试内容：
1. 主板股票封单强度检测
2. 创业板股票封单强度检测
3. 科创板股票封单强度检测
4. 北交所股票封单强度检测
5. 弱封单熔断测试
6. 强封单加分测试
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.predator_system import PredatorSystem


def test_weak_seal_main_board():
    """测试主板弱封单熔断"""
    print("=" * 60)
    print("测试 1: 主板弱封单熔断")
    print("=" * 60)
    
    predator = PredatorSystem()
    
    # 主板股票，涨停，但封单只有300万
    stock_data = {
        'symbol': '600058',
        'name': '五矿发展',
        'remark': ''
    }
    
    realtime_data = {
        'change_percent': 10.0,  # 涨停
        'bid1': 12.67,  # 买一价
        'ask1': 0,  # 卖一价（表示封板）
        'bid1_volume': 30000,  # 买一量（手数）
        'price': 12.67,  # 当前价格
        'circulating_market_cap': 10000000000  # 流通市值（100亿）
    }
    
    # 封单金额计算：30000 * 100 * 12.67 = 38,010,000 元 = 3801万
    # 主板最小封单金额：3000万
    # 3801万 > 3000万，应该通过
    
    score, status = predator.check_limit_strength(stock_data, realtime_data, score=100)
    
    print(f"股票：{stock_data['name']} ({stock_data['symbol']})")
    print(f"封单金额：{realtime_data['bid1_volume']} 手 × 100 × ¥{realtime_data['price']} = ¥{realtime_data['bid1_volume'] * 100 * realtime_data['price']:,.2f} 元")
    print(f"主板最小封单金额：3000万")
    print(f"调整前评分：100")
    print(f"调整后评分：{score}")
    print(f"状态：{status}")
    print(f"结果：{'✅ 通过' if score > 0 else '❌ 熔断'}")
    print()


def test_weak_seal_chi_next():
    """测试创业板弱封单熔断"""
    print("=" * 60)
    print("测试 2: 创业板弱封单熔断")
    print("=" * 60)
    
    predator = PredatorSystem()
    
    # 创业板股票，涨停，但封单只有1000万
    stock_data = {
        'symbol': '301526',
        'name': '国际复材',
        'remark': ''
    }
    
    realtime_data = {
        'change_percent': 20.0,  # 涨停
        'bid1': 10.0,  # 买一价
        'ask1': 0,  # 卖一价（表示封板）
        'bid1_volume': 100000,  # 买一量（手数）
        'price': 10.0,  # 当前价格
        'circulating_market_cap': 5000000000  # 流通市值（50亿）
    }
    
    # 封单金额计算：100000 * 100 * 10.0 = 100,000,000 元 = 10000万
    # 创业板最小封单金额：1500万
    # 10000万 > 1500万，应该通过
    
    score, status = predator.check_limit_strength(stock_data, realtime_data, score=100)
    
    print(f"股票：{stock_data['name']} ({stock_data['symbol']})")
    print(f"封单金额：{realtime_data['bid1_volume']} 手 × 100 × ¥{realtime_data['price']} = ¥{realtime_data['bid1_volume'] * 100 * realtime_data['price']:,.2f} 元")
    print(f"创业板最小封单金额：1500万")
    print(f"调整前评分：100")
    print(f"调整后评分：{score}")
    print(f"状态：{status}")
    print(f"结果：{'✅ 通过' if score > 0 else '❌ 熔断'}")
    print()


def test_fail_weak_seal():
    """测试弱封单熔断失败"""
    print("=" * 60)
    print("测试 3: 弱封单熔断失败")
    print("=" * 60)
    
    predator = PredatorSystem()
    
    # 主板股票，涨停，但封单只有200万
    stock_data = {
        'symbol': '600000',
        'name': '某主板股票',
        'remark': ''
    }
    
    realtime_data = {
        'change_percent': 10.0,  # 涨停
        'bid1': 5.0,  # 买一价
        'ask1': 0,  # 卖一价（表示封板）
        'bid1_volume': 4000,  # 买一量（手数）
        'price': 5.0,  # 当前价格
        'circulating_market_cap': 10000000000  # 流通市值（100亿）
    }
    
    # 封单金额计算：4000 * 100 * 5.0 = 2,000,000 元 = 200万
    # 主板最小封单金额：3000万
    # 200万 < 3000万，应该熔断
    
    score, status = predator.check_limit_strength(stock_data, realtime_data, score=100)
    
    print(f"股票：{stock_data['name']} ({stock_data['symbol']})")
    print(f"封单金额：{realtime_data['bid1_volume']} 手 × 100 × ¥{realtime_data['price']} = ¥{realtime_data['bid1_volume'] * 100 * realtime_data['price']:,.2f} 元")
    print(f"主板最小封单金额：3000万")
    print(f"调整前评分：100")
    print(f"调整后评分：{score}")
    print(f"状态：{status}")
    print(f"结果：{'✅ 通过' if score > 0 else '❌ 熔断'}")
    print()


def test_strong_seal_bonus():
    """测试强封单加分"""
    print("=" * 60)
    print("测试 4: 强封单加分")
    print("=" * 60)
    
    predator = PredatorSystem()
    
    # 主板股票，涨停，封单10000万
    stock_data = {
        'symbol': '600123',
        'name': '某主板强封单股票',
        'remark': ''
    }
    
    realtime_data = {
        'change_percent': 10.0,  # 涨停
        'bid1': 10.0,  # 买一价
        'ask1': 0,  # 卖一价（表示封板）
        'bid1_volume': 1000000,  # 买一量（手数）
        'price': 10.0,  # 当前价格
        'circulating_market_cap': 5000000000  # 流通市值（50亿）
    }
    
    # 封单金额计算：1000000 * 100 * 10.0 = 1,000,000,000 元 = 100000万
    # 主板最小封单金额：3000万
    # 100000万 > 3000万 * 3 = 9000万，应该加分
    
    score, status = predator.check_limit_strength(stock_data, realtime_data, score=90)
    
    print(f"股票：{stock_data['name']} ({stock_data['symbol']})")
    print(f"封单金额：{realtime_data['bid1_volume']} 手 × 100 × ¥{realtime_data['price']} = ¥{realtime_data['bid1_volume'] * 100 * realtime_data['price']:,.2f} 元")
    print(f"主板最小封单金额：3000万")
    print(f"强封单阈值：3000万 × 3 = 9000万")
    print(f"调整前评分：90")
    print(f"调整后评分：{score}")
    print(f"状态：{status}")
    print(f"结果：{'✅ 加分' if score > 90 else '❌ 未加分'}")
    print()


def test_seal_ratio_check():
    """测试封单占比检查"""
    print("=" * 60)
    print("测试 5: 封单占比检查")
    print("=" * 60)
    
    predator = PredatorSystem()
    
    # 主板股票，涨停，封单金额够，但占比过低
    stock_data = {
        'symbol': '600456',
        'name': '某主板股票',
        'remark': ''
    }
    
    realtime_data = {
        'change_percent': 10.0,  # 涨停
        'bid1': 10.0,  # 买一价
        'ask1': 0,  # 卖一价（表示封板）
        'bid1_volume': 100000,  # 买一量（手数）
        'price': 10.0,  # 当前价格
        'circulating_market_cap': 50000000000  # 流通市值（500亿）
    }
    
    # 封单金额计算：100000 * 100 * 10.0 = 100,000,000 元 = 10000万
    # 封单占比：100,000,000 / 50,000,000,000 = 0.002 = 0.2%
    # 主板最小封单占比：0.5%
    # 0.2% < 0.5%，应该熔断
    
    score, status = predator.check_limit_strength(stock_data, realtime_data, score=100)
    
    print(f"股票：{stock_data['name']} ({stock_data['symbol']})")
    print(f"封单金额：{realtime_data['bid1_volume']} 手 × 100 × ¥{realtime_data['price']} = ¥{realtime_data['bid1_volume'] * 100 * realtime_data['price']:,.2f} 元")
    print(f"流通市值：¥{realtime_data['circulating_market_cap']:,.2f} 元")
    print(f"封单占比：{realtime_data['bid1_volume'] * 100 * realtime_data['price'] / realtime_data['circulating_market_cap'] * 100:.2f}%")
    print(f"主板最小封单占比：0.5%")
    print(f"调整前评分：100")
    print(f"调整后评分：{score}")
    print(f"状态：{status}")
    print(f"结果：{'✅ 通过' if score > 0 else '❌ 熔断'}")
    print()


def test_not_limit_up():
    """测试非涨停股票"""
    print("=" * 60)
    print("测试 6: 非涨停股票")
    print("=" * 60)
    
    predator = PredatorSystem()
    
    # 主板股票，未涨停
    stock_data = {
        'symbol': '600789',
        'name': '某主板股票',
        'remark': ''
    }
    
    realtime_data = {
        'change_percent': 5.0,  # 未涨停
        'bid1': 10.0,  # 买一价
        'ask1': 10.01,  # 卖一价（表示未封板）
        'bid1_volume': 100000,  # 买一量（手数）
        'price': 10.0,  # 当前价格
        'circulating_market_cap': 5000000000  # 流通市值（50亿）
    }
    
    score, status = predator.check_limit_strength(stock_data, realtime_data, score=100)
    
    print(f"股票：{stock_data['name']} ({stock_data['symbol']})")
    print(f"涨幅：{realtime_data['change_percent']}%")
    print(f"状态：{status}")
    print(f"结果：{'✅ 跳过检查' if status == 'NOT_LIMIT' else '❌ 错误'}")
    print()


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("V9.1 封单强度熔断测试")
    print("=" * 60 + "\n")
    
    # 运行所有测试
    test_weak_seal_main_board()
    test_weak_seal_chi_next()
    test_fail_weak_seal()
    test_strong_seal_bonus()
    test_seal_ratio_check()
    test_not_limit_up()
    
    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
