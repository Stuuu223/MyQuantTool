#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.5 战法修复测试脚本

测试内容：
1. 低吸战法：测试DDE缺失降级处理和盘中量能修正
2. 半路战法：测试主板判定阈值放宽和动态参数
3. 龙头战法：测试乖离率逻辑优化

Author: iFlow CLI
Version: V19.5
"""

import sys
import time
import traceback
from datetime import datetime
from logic.low_suction_engine import get_low_suction_engine
from logic.midway_strategy import MidwayStrategy
from logic.dragon_tactics import DragonTactics
from logic.logger import get_logger

logger = get_logger(__name__)


def test_low_suction_engine():
    """测试低吸战法"""
    print("\n" + "="*80)
    print("🧪 测试低吸战法 (Low Suction Engine)")
    print("="*80)
    
    try:
        engine = get_low_suction_engine()
        
        # 测试用例1：测试DDE缺失降级处理
        print("\n📊 测试用例1：DDE缺失降级处理")
        print("-" * 80)
        
        # 使用一个测试股票代码
        test_code = "600519"  # 贵州茅台
        
        # 模拟数据
        current_price = 1800.0
        prev_close = 1780.0
        
        # 测试MA5低吸
        result = engine.check_ma5_suction(test_code, current_price, prev_close)
        
        print(f"股票代码: {test_code}")
        print(f"当前价格: ¥{current_price:.2f}")
        print(f"昨收价: ¥{prev_close:.2f}")
        print(f"是否有低吸信号: {result['has_suction']}")
        print(f"低吸类型: {result['suction_type']}")
        print(f"置信度: {result['confidence']:.2f}")
        print(f"原因: {result['reason']}")
        
        # 测试用例2：测试盘中量能修正
        print("\n📊 测试用例2：盘中量能修正")
        print("-" * 80)
        
        # 获取当前时间
        now = datetime.now()
        print(f"当前时间: {now.strftime('%H:%M:%S')}")
        
        # 测试不同时间段的量能计算
        test_codes = ["000001", "600000", "000002"]
        
        for code in test_codes:
            try:
                result = engine.check_ma5_suction(code, 10.0, 9.8)
                print(f"\n{code}:")
                print(f"  量比: {result['volume_ratio']:.2f}")
                print(f"  原因: {result['reason']}")
            except Exception as e:
                print(f"\n{code}: 测试失败 - {e}")
        
        print("\n✅ 低吸战法测试完成")
        
    except Exception as e:
        print(f"\n❌ 低吸战法测试失败: {e}")
        traceback.print_exc()
        return False
    
    return True


def test_midway_strategy():
    """测试半路战法"""
    print("\n" + "="*80)
    print("🧪 测试半路战法 (Midway Strategy)")
    print("="*80)
    
    try:
        strategy = MidwayStrategy()
        
        # 测试用例1：测试全市场扫描（包括主板）
        print("\n📊 测试用例1：全市场扫描（包括主板）")
        print("-" * 80)
        
        start_time = time.time()
        
        results = strategy.scan_market(
            min_change_pct=2.0,
            max_change_pct=10.0,
            min_score=0.5,
            stock_limit=20,
            only_20cm=False  # 扫描全市场
        )
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"扫描耗时: {elapsed_time:.2f}秒")
        print(f"发现信号数量: {len(results)}")
        
        if results:
            print("\n前5个信号:")
            for i, result in enumerate(results[:5], 1):
                print(f"\n{i}. {result['name']} ({result['code']})")
                print(f"   信号类型: {result['signal_type']}")
                print(f"   信号强度: {result['score']:.2f}")
                print(f"   当前价: ¥{result['current_price']:.2f}")
                print(f"   风险等级: {result['risk_level']}")
                print(f"   理由: {result['reason']}")
        
        # 测试用例2：测试只扫描20cm标的
        print("\n📊 测试用例2：只扫描20cm标的")
        print("-" * 80)
        
        start_time = time.time()
        
        results_20cm = strategy.scan_market(
            min_change_pct=2.0,
            max_change_pct=10.0,
            min_score=0.5,
            stock_limit=20,
            only_20cm=True  # 只扫描20cm
        )
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"扫描耗时: {elapsed_time:.2f}秒")
        print(f"发现信号数量: {len(results_20cm)}")
        
        # 检查是否都是20cm标的
        if results_20cm:
            all_20cm = all(result['code'].startswith(('300', '688')) for result in results_20cm)
            print(f"是否全部为20cm标的: {all_20cm}")
        
        print("\n✅ 半路战法测试完成")
        
    except Exception as e:
        print(f"\n❌ 半路战法测试失败: {e}")
        traceback.print_exc()
        return False
    
    return True


def test_dragon_tactics():
    """测试龙头战法"""
    print("\n" + "="*80)
    print("🧪 测试龙头战法 (Dragon Tactics)")
    print("="*80)
    
    try:
        tactics = DragonTactics()
        
        # 测试用例1：测试乖离率逻辑优化
        print("\n📊 测试用例1：乖离率逻辑优化")
        print("-" * 80)
        
        # 测试不同乖离率的情况
        test_cases = [
            {
                'code': '600000',
                'name': '浦发银行',
                'price': 10.0,
                'open': 9.5,
                'pre_close': 9.0,
                'high': 10.5,
                'low': 9.2,
                'ma5': 8.0,  # 乖离率 > 20%
                'sector_role': '龙一（推断）',
                'weak_to_strong': True
            },
            {
                'code': '000001',
                'name': '平安银行',
                'price': 15.0,
                'open': 14.5,
                'pre_close': 14.0,
                'high': 15.5,
                'low': 14.2,
                'ma5': 13.0,  # 乖离率 > 15%
                'sector_role': '跟风（推断）',
                'weak_to_strong': False
            },
            {
                'code': '300750',
                'name': '宁德时代',
                'price': 200.0,
                'open': 195.0,
                'pre_close': 190.0,
                'high': 205.0,
                'low': 192.0,
                'ma5': 185.0,  # 乖离率 > 8%
                'sector_role': '龙一（推断）',
                'weak_to_strong': True
            }
        ]
        
        for i, stock_info in enumerate(test_cases, 1):
            print(f"\n测试用例 {i}: {stock_info['name']} ({stock_info['code']})")
            print(f"  当前价: ¥{stock_info['price']:.2f}")
            print(f"  MA5: ¥{stock_info['ma5']:.2f}")
            print(f"  乖离率: {(stock_info['price'] - stock_info['ma5']) / stock_info['ma5'] * 100:.1f}%")
            print(f"  板块角色: {stock_info['sector_role']}")
            print(f"  弱转强: {stock_info['weak_to_strong']}")
            
            result = tactics.check_dragon_criteria(stock_info)
            
            print(f"  信号: {result['signal']}")
            print(f"  动作: {result['action']}")
            print(f"  置信度: {result['confidence']}")
            print(f"  原因: {result['reason']}")
            
            # 检查是否正确处理了乖离率
            if 'bias_5' in result:
                print(f"  乖离率: {result['bias_5']:.1f}%")
        
        print("\n✅ 龙头战法测试完成")
        
    except Exception as e:
        print(f"\n❌ 龙头战法测试失败: {e}")
        traceback.print_exc()
        return False
    
    return True


def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 V19.5 战法修复测试")
    print("="*80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        '低吸战法': False,
        '半路战法': False,
        '龙头战法': False
    }
    
    # 测试低吸战法
    results['低吸战法'] = test_low_suction_engine()
    
    # 测试半路战法
    results['半路战法'] = test_midway_strategy()
    
    # 测试龙头战法
    results['龙头战法'] = test_dragon_tactics()
    
    # 输出测试结果汇总
    print("\n" + "="*80)
    print("📊 测试结果汇总")
    print("="*80)
    
    for strategy, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{strategy}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())