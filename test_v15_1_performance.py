"""
V15.1 动态离场系统性能测试

测试三级火箭防守的性能和响应时间
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.position_manager import PositionManager
import logging

# 配置日志
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_performance_basic():
    """
    测试基本性能：单次计算耗时
    """
    print("\n" + "=" * 80)
    print("性能测试 1：基本性能 - 单次计算耗时")
    print("=" * 80)
    
    pm = PositionManager(account_value=100000)
    
    # 测试 1000 次计算
    num_tests = 1000
    start_time = time.time()
    
    for i in range(num_tests):
        result = pm.calculate_dynamic_stop_loss(
            current_price=105.0,
            cost_price=100.0,
            highest_price=108.0,
            is_limit_up=False
        )
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / num_tests * 1000  # 毫秒
    
    print(f"✅ 测试 {num_tests} 次计算")
    print(f"   总耗时: {total_time:.4f} 秒")
    print(f"   平均耗时: {avg_time:.4f} 毫秒/次")
    print(f"   吞吐量: {num_tests/total_time:.2f} 次/秒")
    
    # 性能要求：单次计算 < 1 毫秒
    assert avg_time < 1.0, f"性能不达标：平均耗时 {avg_time:.4f} 毫秒 > 1 毫秒"
    
    print("\n✅ 性能测试 1 通过：基本性能达标")


def test_performance_multiple_scenarios():
    """
    测试多场景性能：不同防守等级的计算耗时
    """
    print("\n" + "=" * 80)
    print("性能测试 2：多场景性能 - 不同防守等级")
    print("=" * 80)
    
    pm = PositionManager(account_value=100000)
    
    scenarios = [
        {
            'name': '无防守',
            'params': {
                'current_price': 102.0,
                'cost_price': 100.0,
                'highest_price': 102.0,
                'is_limit_up': False
            }
        },
        {
            'name': '一级防守',
            'params': {
                'current_price': 103.5,
                'cost_price': 100.0,
                'highest_price': 103.5,
                'is_limit_up': False
            }
        },
        {
            'name': '二级防守',
            'params': {
                'current_price': 105.0,
                'cost_price': 100.0,
                'highest_price': 108.0,
                'is_limit_up': False
            }
        },
        {
            'name': '三级防守',
            'params': {
                'current_price': 107.5,
                'cost_price': 100.0,
                'highest_price': 110.0,
                'is_limit_up': True,
                'limit_up_price': 110.0
            }
        }
    ]
    
    for scenario in scenarios:
        num_tests = 1000
        start_time = time.time()
        
        for i in range(num_tests):
            result = pm.calculate_dynamic_stop_loss(**scenario['params'])
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / num_tests * 1000  # 毫秒
        
        print(f"✅ 场景: {scenario['name']}")
        print(f"   平均耗时: {avg_time:.4f} 毫秒/次")
        print(f"   吞吐量: {num_tests/total_time:.2f} 次/秒")
        
        # 性能要求：所有场景 < 1 毫秒
        assert avg_time < 1.0, f"性能不达标：{scenario['name']} 平均耗时 {avg_time:.4f} 毫秒 > 1 毫秒"
    
    print("\n✅ 性能测试 2 通过：所有场景性能达标")


def test_performance_exit_signal():
    """
    测试离场信号检测性能
    """
    print("\n" + "=" * 80)
    print("性能测试 3：离场信号检测性能")
    print("=" * 80)
    
    pm = PositionManager(account_value=100000)
    
    # 测试 1000 次离场信号检测
    num_tests = 1000
    start_time = time.time()
    
    for i in range(num_tests):
        result = pm.check_position_exit_signal(
            stock_code="603056",
            current_price=105.0,
            cost_price=100.0,
            highest_price=108.0,
            is_limit_up=False
        )
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / num_tests * 1000  # 毫秒
    
    print(f"✅ 测试 {num_tests} 次离场信号检测")
    print(f"   总耗时: {total_time:.4f} 秒")
    print(f"   平均耗时: {avg_time:.4f} 毫秒/次")
    print(f"   吞吐量: {num_tests/total_time:.2f} 次/秒")
    
    # 性能要求：单次检测 < 1 毫秒
    assert avg_time < 1.0, f"性能不达标：平均耗时 {avg_time:.4f} 毫秒 > 1 毫秒"
    
    print("\n✅ 性能测试 3 通过：离场信号检测性能达标")


def test_performance_stress():
    """
    压力测试：模拟高频交易场景
    """
    print("\n" + "=" * 80)
    print("性能测试 4：压力测试 - 高频交易场景")
    print("=" * 80)
    
    pm = PositionManager(account_value=100000)
    
    # 模拟 100 只股票，每只股票 100 次价格更新
    num_stocks = 100
    num_updates = 100
    total_operations = num_stocks * num_updates
    
    start_time = time.time()
    
    for stock_id in range(num_stocks):
        cost_price = 100.0
        highest_price = cost_price
        
        for update_id in range(num_updates):
            # 模拟价格波动
            current_price = cost_price * (1 + (update_id % 20 - 10) / 100)
            highest_price = max(highest_price, current_price)
            
            result = pm.calculate_dynamic_stop_loss(
                current_price=current_price,
                cost_price=cost_price,
                highest_price=highest_price,
                is_limit_up=False
            )
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / total_operations * 1000  # 毫秒
    
    print(f"✅ 测试 {total_operations} 次操作（{num_stocks} 只股票 x {num_updates} 次更新）")
    print(f"   总耗时: {total_time:.4f} 秒")
    print(f"   平均耗时: {avg_time:.4f} 毫秒/次")
    print(f"   吞吐量: {total_operations/total_time:.2f} 次/秒")
    
    # 性能要求：高频场景 < 0.5 毫秒
    assert avg_time < 0.5, f"性能不达标：高频场景平均耗时 {avg_time:.4f} 毫秒 > 0.5 毫秒"
    
    print("\n✅ 性能测试 4 通过：压力测试达标")


def main():
    """运行所有性能测试"""
    print("\n" + "=" * 80)
    print("V15.1 动态离场系统性能测试")
    print("=" * 80)
    
    try:
        test_performance_basic()
        test_performance_multiple_scenarios()
        test_performance_exit_signal()
        test_performance_stress()
        
        print("\n" + "=" * 80)
        print("✅ 所有性能测试通过！")
        print("=" * 80)
        return 0
    except AssertionError as e:
        print(f"\n❌ 性能测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 性能测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
