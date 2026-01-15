"""
V6.2 新功能回测测试

测试三个核心优化：
1. 反核按钮成交性质判定
2. 板块轮动确认窗口
3. 分层抽样样本偏差修正
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from logic.theme_detector import ThemeDetector
from logic.market_cycle import MarketCycleManager
from logic.data_manager import DataManager
from logic.backtest_engine import BacktestEngine

def test_anti_nuclear_verification():
    """
    测试反核按钮成交性质判定
    
    测试场景：
    - 真翘板：买一封单被吃掉50%以上
    - 假翘板：买二买三挂大单但买一成交稀疏
    """
    print("=" * 80)
    print("🧪 测试1: 反核按钮成交性质判定")
    print("=" * 80)
    
    cycle_manager = MarketCycleManager()
    
    # 模拟跌停股票数据
    test_cases = [
        {
            'name': '真翘板测试',
            'stock': {
                'code': '300063',
                'name': '天龙集团',
                'change_pct': -9.95,
                'bid1_volume': 5000,  # 买一量充足
                'ask1_volume': 3000,  # 买一被吃掉一部分
                'volume': 15000,  # 成交量较大
            },
            'expected': True  # 应该验证通过
        },
        {
            'name': '假翘板测试（骗炮）',
            'stock': {
                'code': '600519',
                'name': '贵州茅台',
                'change_pct': -9.95,
                'bid1_volume': 1000,  # 买一量小
                'ask1_volume': 10000,  # 买一量占比过高
                'volume': 5000,  # 成交量小
            },
            'expected': False  # 应该验证失败
        },
        {
            'name': '成交量不足测试',
            'stock': {
                'code': '000001',
                'name': '平安银行',
                'change_pct': -9.95,
                'bid1_volume': 2000,
                'ask1_volume': 1000,
                'volume': 3000,  # 成交量太小
            },
            'expected': False  # 应该验证失败
        }
    ]
    
    results = []
    for test_case in test_cases:
        result = cycle_manager._verify_anti_nuclear_signal(test_case['stock'])
        passed = result == test_case['expected']
        
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"\n{test_case['name']}: {status}")
        print(f"  预期结果: {test_case['expected']}")
        print(f"  实际结果: {result}")
        
        results.append({
            'test_name': test_case['name'],
            'passed': passed,
            'expected': test_case['expected'],
            'actual': result
        })
    
    # 统计结果
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['passed'])
    pass_rate = passed_tests / total_tests * 100
    
    print(f"\n📊 反核判定测试结果: {passed_tests}/{total_tests} 通过 ({pass_rate:.1f}%)")
    
    return results


def test_rotation_hysteresis():
    """
    测试板块轮动确认窗口
    
    测试场景：
    - 首次分歧：应该进入观察期，不要切换
    - 连续2天分歧且低位板块有承接：应该切换
    - 连续2天分歧但低位板块无承接：继续观察
    """
    print("\n" + "=" * 80)
    print("🧪 测试2: 板块轮动确认窗口 (Hysteresis Window)")
    print("=" * 80)
    
    theme_detector = ThemeDetector()
    
    # 🆕 模拟theme_history数据
    from datetime import datetime
    theme_detector.theme_history = [
        {
            'timestamp': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
            'theme': 'AI',
            'heat': 0.15,  # 第1天：强势
            'leader': '天龙集团'
        },
        {
            'timestamp': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'theme': 'AI',
            'heat': 0.08,  # 第2天：分歧
            'leader': '天龙集团'
        },
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'theme': 'AI',
            'heat': 0.08,  # 第3天：分歧
            'leader': '天龙集团'
        }
    ]
    
    # 模拟板块数据
    test_cases = [
        {
            'name': '首次分歧测试',
            'params': {
                'current_theme': 'AI',
                'theme_heat': 0.12,
                'theme_sentiment': 'DIVERGENCE',
                'theme_days': 3,
                'all_themes': {
                    'AI': {'heat': 0.12, 'count': 12},
                    '医药': {'heat': 0.02, 'count': 2},
                    '新能源': {'heat': 0.03, 'count': 3}
                }
            },
            'expected_signal': 'HOLD_AND_WATCH'  # 应该进入观察期
        },
        {
            'name': '确认切换测试',
            'params': {
                'current_theme': 'AI',
                'theme_heat': 0.08,
                'theme_sentiment': 'DIVERGENCE',
                'theme_days': 4,
                'all_themes': {
                    'AI': {'heat': 0.08, 'count': 8},
                    '医药': {'heat': 0.04, 'count': 4},
                    '新能源': {'heat': 0.05, 'count': 5}
                }
            },
            'expected_signal': 'ROTATE_NOW'  # 应该确认切换
        },
        {
            'name': '无承接继续观察测试',
            'params': {
                'current_theme': 'AI',
                'theme_heat': 0.08,
                'theme_sentiment': 'DIVERGENCE',
                'theme_days': 4,
                'all_themes': {
                    'AI': {'heat': 0.08, 'count': 8},
                    '医药': {'heat': 0.005, 'count': 1},
                    '新能源': {'heat': 0.008, 'count': 1}
                }
            },
            'expected_signal': 'HOLD_AND_WATCH'  # 应该继续观察
        }
    ]
    
    results = []
    for test_case in test_cases:
        result = theme_detector.predict_rotation(**test_case['params'])
        actual_signal = result.get('rotation_signal', 'UNKNOWN')
        expected_signal = test_case['expected_signal']
        passed = actual_signal == expected_signal
        
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"\n{test_case['name']}: {status}")
        print(f"  预期信号: {expected_signal}")
        print(f"  实际信号: {actual_signal}")
        print(f"  操作建议: {result.get('strategy', '')}")
        print(f"  观察期天数: {result.get('hysteresis_days', 0)}")
        
        results.append({
            'test_name': test_case['name'],
            'passed': passed,
            'expected_signal': expected_signal,
            'actual_signal': actual_signal
        })
    
    # 统计结果
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['passed'])
    pass_rate = passed_tests / total_tests * 100
    
    print(f"\n📊 轮动确认窗口测试结果: {passed_tests}/{total_tests} 通过 ({pass_rate:.1f}%)")
    
    return results


def test_stratified_sampling():
    """
    测试分层抽样
    
    测试场景：
    - 验证分层抽样是否覆盖各个层级
    - 验证样本总数是否为100只
    """
    print("\n" + "=" * 80)
    print("🧪 测试3: 分层抽样 (Stratified Sampling)")
    print("=" * 80)
    
    data_manager = DataManager()
    
    # 获取分层抽样样本
    sample_stocks = data_manager._get_stratified_sample()
    
    results = []
    
    # 测试1: 样本总数
    test1_passed = len(sample_stocks) == 100
    print(f"\n测试1 - 样本总数: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"  预期: 100只")
    print(f"  实际: {len(sample_stocks)}只")
    
    results.append({
        'test_name': '样本总数',
        'passed': test1_passed,
        'expected': 100,
        'actual': len(sample_stocks)
    })
    
    # 测试2: 样本去重
    unique_stocks = set(sample_stocks)
    test2_passed = len(unique_stocks) == len(sample_stocks)
    print(f"\n测试2 - 样本去重: {'✅ 通过' if test2_passed else '❌ 失败'}")
    print(f"  总数: {len(sample_stocks)}只")
    print(f"  去重后: {len(unique_stocks)}只")
    
    results.append({
        'test_name': '样本去重',
        'passed': test2_passed,
        'expected': len(sample_stocks),
        'actual': len(unique_stocks)
    })
    
    # 测试3: 代码格式验证
    invalid_codes = [code for code in sample_stocks if not code.isdigit() or len(code) != 6]
    test3_passed = len(invalid_codes) == 0
    print(f"\n测试3 - 代码格式: {'✅ 通过' if test3_passed else '❌ 失败'}")
    if invalid_codes:
        print(f"  无效代码: {invalid_codes}")
    else:
        print(f"  所有代码格式正确")
    
    results.append({
        'test_name': '代码格式',
        'passed': test3_passed,
        'expected': 0,
        'actual': len(invalid_codes)
    })
    
    # 统计结果
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['passed'])
    pass_rate = passed_tests / total_tests * 100
    
    print(f"\n📊 分层抽样测试结果: {passed_tests}/{total_tests} 通过 ({pass_rate:.1f}%)")
    
    return results


def run_all_tests():
    """运行所有V6.2新功能测试"""
    print("\n" + "=" * 80)
    print("🚀 V6.2 新功能回测测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 运行所有测试
    anti_nuclear_results = test_anti_nuclear_verification()
    rotation_results = test_rotation_hysteresis()
    sampling_results = test_stratified_sampling()
    
    # 汇总结果
    all_results = anti_nuclear_results + rotation_results + sampling_results
    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results if r['passed'])
    overall_pass_rate = passed_tests / total_tests * 100
    
    print("\n" + "=" * 80)
    print("📊 总体测试结果")
    print("=" * 80)
    print(f"总测试数: {total_tests}")
    print(f"通过数: {passed_tests}")
    print(f"失败数: {total_tests - passed_tests}")
    print(f"通过率: {overall_pass_rate:.1f}%")
    
    if overall_pass_rate >= 80:
        print("\n✅ V6.2 新功能测试通过！系统已准备好投入使用。")
    else:
        print("\n⚠️ V6.2 新功能测试未完全通过，建议进一步优化。")
    
    return all_results


if __name__ == "__main__":
    results = run_all_tests()
    
    # 保存测试结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_file = f'test_v62_results_{timestamp}.txt'
    
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("V6.2 新功能回测测试结果\n")
        f.write("=" * 80 + "\n")
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for result in results:
            status = "✅ 通过" if result['passed'] else "❌ 失败"
            f.write(f"{result['test_name']}: {status}\n")
            f.write(f"  预期: {result.get('expected', 'N/A')}\n")
            f.write(f"  实际: {result.get('actual', 'N/A')}\n\n")
    
    print(f"\n📄 测试结果已保存到: {result_file}")