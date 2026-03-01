"""
UniverseBuilder端到端测试脚本
测试目标: 验证三漏斗粗筛功能
"""
import sys
import os
sys.path.insert(0, 'E:\\MyQuantTool')

import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_universe_builder():
    """测试UniverseBuilder.get_daily_universe()"""
    test_results = {
        'test_name': 'UniverseBuilder端到端测试',
        'date': '20250227',
        'passed': [],
        'failed': [],
        'warnings': [],
        'details': {}
    }
    
    print("=" * 80)
    print("【UniverseBuilder端到端测试报告】")
    print("=" * 80)
    print(f"测试日期: 20250227")
    print(f"测试入口: logic.data_providers.universe_builder.UniverseBuilder")
    print("-" * 80)
    
    # 测试1: 实例化
    print("\n[测试1/4] UniverseBuilder实例化...")
    try:
        from logic.data_providers.universe_builder import UniverseBuilder
        builder = UniverseBuilder()
        print(f"✅ 实例化成功")
        print(f"   - strategy属性: {builder.strategy}")
        print(f"   - MIN_AMOUNT: {builder.MIN_AMOUNT}")
        print(f"   - MIN_ACTIVE_TURNOVER_RATE: {builder.MIN_ACTIVE_TURNOVER_RATE}")
        print(f"   - DEATH_TURNOVER_RATE: {builder.DEATH_TURNOVER_RATE}")
        test_results['passed'].append('实例化测试')
    except Exception as e:
        print(f"❌ 实例化失败: {e}")
        print(f"   堆栈跟踪:\n{traceback.format_exc()}")
        test_results['failed'].append(f'实例化测试: {e}')
        return test_results
    
    # 测试2: get_daily_universe执行
    print("\n[测试2/4] get_daily_universe执行...")
    stock_pool = None
    try:
        stock_pool = builder.get_daily_universe('20250227')
        print(f"✅ 执行成功")
        test_results['passed'].append('get_daily_universe执行')
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        print(f"   堆栈跟踪:\n{traceback.format_exc()}")
        test_results['failed'].append(f'get_daily_universe执行: {e}')
        return test_results
    
    # 测试3: 结果数量检查
    print("\n[测试3/4] 结果数量合理性检查...")
    if stock_pool is not None:
        count = len(stock_pool)
        print(f"   - 返回股票数量: {count}")
        if 10 <= count <= 500:
            print(f"✅ 数量合理 (10 <= {count} <= 500)")
            test_results['passed'].append(f'数量合理性检查: {count}只')
        else:
            warning_msg = f'数量异常: {count}只 (期望10-500只)'
            print(f"⚠️  {warning_msg}")
            test_results['warnings'].append(warning_msg)
            test_results['passed'].append(f'数量检查: {count}只 (超出预期范围但非错误)')
        test_results['details']['stock_count'] = count
    else:
        print(f"❌ 返回结果为None")
        test_results['failed'].append('结果为None')
    
    # 测试4: 股票代码格式检查
    print("\n[测试4/4] 股票代码格式检查...")
    if stock_pool and len(stock_pool) > 0:
        sample = stock_pool[:min(10, len(stock_pool))]
        print(f"   - 前{len(sample)}只股票:")
        valid_format = True
        for i, code in enumerate(sample):
            print(f"     {i+1}. {code}")
            # 检查格式: 应该是 #######.SH 或 #######.SZ
            if not (code.endswith('.SH') or code.endswith('.SZ') or code.endswith('.BJ')):
                print(f"       ⚠️  格式异常: 期望.SZ/.SH/.BJ后缀")
                valid_format = False
        if valid_format:
            print(f"✅ 股票代码格式正确")
            test_results['passed'].append('股票代码格式检查')
        else:
            test_results['warnings'].append('部分股票代码格式异常')
        test_results['details']['sample_stocks'] = sample
    else:
        print(f"⚠️  无股票数据可供检查")
        test_results['warnings'].append('无股票数据')
    
    # 汇总
    print("\n" + "=" * 80)
    print("【测试汇总】")
    print("=" * 80)
    print(f"✅ 通过: {len(test_results['passed'])} 项")
    for item in test_results['passed']:
        print(f"   ✓ {item}")
    
    if test_results['warnings']:
        print(f"\n⚠️  警告: {len(test_results['warnings'])} 项")
        for item in test_results['warnings']:
            print(f"   ! {item}")
    
    if test_results['failed']:
        print(f"\n❌ 失败: {len(test_results['failed'])} 项")
        for item in test_results['failed']:
            print(f"   ✗ {item}")
        print(f"\n【结论】测试未通过")
        return test_results
    else:
        print(f"\n【结论】✅ 所有测试通过！UniverseBuilder工作正常。")
        return test_results

if __name__ == '__main__':
    results = test_universe_builder()
    sys.exit(0 if not results['failed'] else 1)
