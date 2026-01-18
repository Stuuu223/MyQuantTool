"""
V14.4 龙虎榜反制性能测试
"""

import time
from logic.signal_generator import get_signal_generator_v14_4
from logic.logger import get_logger

logger = get_logger(__name__)


def test_performance():
    """性能测试"""
    print("="*70)
    print("V14.4 龙虎榜反制性能测试开始")
    print("="*70)
    
    sg = get_signal_generator_v14_4()
    
    # 测试场景
    test_cases = [
        {
            "name": "陷阱识别（豪华榜 + 高开）",
            "stock_code": "600000",
            "ai_score": 90.0,
            "capital_flow": 10000000,
            "trend": "UP",
            "current_pct_change": 7.0,
            "yesterday_lhb_net_buy": 60000000,
            "open_pct_change": 7.5,
            "expected_signal": "WAIT",
            "expected_reason_contains": "陷阱"
        },
        {
            "name": "弱转强（豪华榜 + 平开）",
            "stock_code": "000001",
            "ai_score": 90.0,
            "capital_flow": 10000000,
            "trend": "UP",
            "current_pct_change": 1.5,
            "yesterday_lhb_net_buy": 80000000,
            "open_pct_change": 0.5,
            "expected_signal": "BUY",
            "expected_reason_contains": "弱转强"
        },
        {
            "name": "不及预期（豪华榜 + 低开）",
            "stock_code": "000002",
            "ai_score": 90.0,
            "capital_flow": 10000000,
            "trend": "UP",
            "current_pct_change": -2.0,
            "yesterday_lhb_net_buy": 60000000,
            "open_pct_change": -3.5,
            "expected_signal": "WAIT",
            "expected_reason_contains": "不及预期"
        },
        {
            "name": "普通榜单（无博弈价值）",
            "stock_code": "000003",
            "ai_score": 90.0,
            "capital_flow": 10000000,
            "trend": "UP",
            "current_pct_change": 3.0,
            "yesterday_lhb_net_buy": 10000000,
            "open_pct_change": 5.0,
            "expected_signal": "BUY",
            "expected_reason_contains": "共振"
        },
        {
            "name": "涨停豁免（20cm）",
            "stock_code": "300000",
            "ai_score": 85.0,
            "capital_flow": 10000000,
            "trend": "UP",
            "current_pct_change": 19.5,
            "yesterday_lhb_net_buy": 0,
            "open_pct_change": 0.0,
            "expected_signal": "BUY",
            "expected_reason_contains": "涨停豁免"
        },
        {
            "name": "资金熔断（流出 > 5000万）",
            "stock_code": "600001",
            "ai_score": 90.0,
            "capital_flow": -60000000,
            "trend": "UP",
            "current_pct_change": 3.0,
            "yesterday_lhb_net_buy": 0,
            "open_pct_change": 0.0,
            "expected_signal": "SELL",
            "expected_reason_contains": "资金熔断"
        },
        {
            "name": "趋势熔断（空头排列）",
            "stock_code": "600002",
            "ai_score": 90.0,
            "capital_flow": 10000000,
            "trend": "DOWN",
            "current_pct_change": 3.0,
            "yesterday_lhb_net_buy": 0,
            "open_pct_change": 0.0,
            "expected_signal": "WAIT",
            "expected_reason_contains": "趋势熔断"
        },
        {
            "name": "量价背离（资金流出 + 趋势向上）",
            "stock_code": "600003",
            "ai_score": 90.0,
            "capital_flow": -10000000,
            "trend": "UP",
            "current_pct_change": 3.0,
            "yesterday_lhb_net_buy": 0,
            "open_pct_change": 0.0,
            "expected_signal": "WAIT",
            "expected_reason_contains": "量价背离"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test_case['name']}")
        print("-" * 70)
        
        start_time = time.time()
        
        result = sg.calculate_final_signal(
            stock_code=test_case['stock_code'],
            ai_score=test_case['ai_score'],
            capital_flow=test_case['capital_flow'],
            trend=test_case['trend'],
            current_pct_change=test_case['current_pct_change'],
            yesterday_lhb_net_buy=test_case['yesterday_lhb_net_buy'],
            open_pct_change=test_case['open_pct_change']
        )
        
        elapsed_time = time.time() - start_time
        
        print(f"耗时: {elapsed_time:.6f}秒")
        print(f"信号: {result['signal']}")
        print(f"得分: {result['score']:.1f}")
        print(f"理由: {result['reason']}")
        print(f"风险: {result['risk']}")
        
        # 验证结果
        success = True
        
        if result['signal'] != test_case['expected_signal']:
            print(f"❌ 信号不匹配: 预期 {test_case['expected_signal']}, 实际 {result['signal']}")
            success = False
        
        if test_case['expected_reason_contains'] not in result['reason']:
            print(f"❌ 理由不匹配: 预期包含 '{test_case['expected_reason_contains']}', 实际 '{result['reason']}'")
            success = False
        
        if success:
            print(f"✅ 测试通过")
            passed += 1
        else:
            print(f"❌ 测试失败")
            failed += 1
    
    print("\n" + "="*70)
    print("测试报告")
    print("="*70)
    print(f"总测试数: {len(test_cases)}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"通过率: {passed/len(test_cases)*100:.1f}%")
    
    if failed == 0:
        print("\n✅ 所有测试通过！")
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败")
    
    print("="*70)
    
    # 保存测试报告
    with open('data/review_cases/v14_4_performance_test_report.txt', 'w', encoding='utf-8') as f:
        f.write("V14.4 龙虎榜反制性能测试报告\n")
        f.write("="*70 + "\n\n")
        f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总测试数: {len(test_cases)}\n")
        f.write(f"通过: {passed}\n")
        f.write(f"失败: {failed}\n")
        f.write(f"通过率: {passed/len(test_cases)*100:.1f}%\n\n")
        
        for i, test_case in enumerate(test_cases, 1):
            f.write(f"测试 {i}: {test_case['name']}\n")
            f.write("-" * 70 + "\n")
            f.write(f"预期信号: {test_case['expected_signal']}\n")
            f.write(f"预期理由包含: {test_case['expected_reason_contains']}\n")
            f.write("\n")
        
        f.write("="*70 + "\n")
        f.write("报告生成完成\n")
    
    print("\n测试报告已保存到: data/review_cases/v14_4_performance_test_report.txt")


if __name__ == '__main__':
    test_performance()