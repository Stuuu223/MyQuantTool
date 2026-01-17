#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V10.1.9.1 逻辑完整性审计测试
验证Git合并后所有功能是否正常
"""

import sys
from datetime import datetime

def test_ai_agent_rules():
    """测试1：检查AI Agent的规则完整性"""
    print("=" * 60)
    print("测试1：AI Agent 规则完整性检查")
    print("=" * 60)
    
    try:
        with open('logic/ai_agent.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查第4条规则：K线趋势否决权
        if 'K线趋势否决权' in content:
            print("✅ 第4条规则：K线趋势否决权 - 存在")
            
            # 检查规则的三个子规则
            rules = {
                '规则A（跌破20日线）': '🔴 跌破20日线' in content,
                '规则B（短期超买）': '⚠️ 短期超买' in content,
                '规则C（多头排列）': '📈 多头排列' in content
            }
            
            for rule_name, exists in rules.items():
                status = "✅" if exists else "❌"
                print(f"  {status} {rule_name}")
            
            if all(rules.values()):
                print("🎉 AI Agent 规则完整！")
                return True
            else:
                print("⚠️ 部分规则缺失")
                return False
        else:
            print("❌ 第4条规则：K线趋势否决权 - 缺失")
            print("🚨 严重警告：AI Agent 失去了 K线趋势否决权！")
            return False
    
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def test_ui_display():
    """测试2：检查UI显示功能"""
    print("\n" + "=" * 60)
    print("测试2：UI 显示功能检查")
    print("=" * 60)
    
    try:
        with open('ui/dragon_strategy.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查技术形态显示
        features = {
            '技术形态显示': '📊 技术面' in content,
            '技术面颜色区分': 'st.error' in content and 'st.info' in content,
            '风险扫描功能': '风险扫描' in content,
            '风险等级显示': '风险等级' in content
        }
        
        all_ok = True
        for feature_name, exists in features.items():
            status = "✅" if exists else "❌"
            print(f"{status} {feature_name}")
            if not exists:
                all_ok = False
        
        if all_ok:
            print("🎉 UI 显示功能完整！")
            return True
        else:
            print("⚠️ 部分UI功能缺失")
            return False
    
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def test_technical_analyzer():
    """测试3：检查TechnicalAnalyzer功能"""
    print("\n" + "=" * 60)
    print("测试3：TechnicalAnalyzer 功能检查")
    print("=" * 60)
    
    try:
        from logic.technical_analyzer import TechnicalAnalyzer
        
        ta = TechnicalAnalyzer()
        
        # 检查关键方法
        methods = {
            '_fetch_single_stock': hasattr(ta, '_fetch_single_stock'),
            'analyze_batch': hasattr(ta, 'analyze_batch')
        }
        
        all_ok = True
        for method_name, exists in methods.items():
            status = "✅" if exists else "❌"
            print(f"{status} {method_name}")
            if not exists:
                all_ok = False
        
        # 检查实时价格注入功能
        import inspect
        sig = inspect.signature(ta._fetch_single_stock)
        has_real_time_param = 'real_time_price' in sig.parameters
        
        status = "✅" if has_real_time_param else "❌"
        print(f"{status} real_time_price 参数支持")
        
        if not has_real_time_param:
            all_ok = False
        
        if all_ok:
            print("🎉 TechnicalAnalyzer 功能完整！")
            return True
        else:
            print("⚠️ TechnicalAnalyzer 功能不完整")
            return False
    
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def test_sentiment_analyzer():
    """测试4：检查SentimentAnalyzer集成"""
    print("\n" + "=" * 60)
    print("测试4：SentimentAnalyzer 集成检查")
    print("=" * 60)
    
    try:
        with open('logic/sentiment_analyzer.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查集成点
        integrations = {
            '导入TechnicalAnalyzer': 'from logic.technical_analyzer import TechnicalAnalyzer' in content,
            '初始化TechnicalAnalyzer': 'self.ta = TechnicalAnalyzer()' in content,
            '调用analyze_batch': 'self.ta.analyze_batch' in content,
            '注入kline_trend': "stock['kline_trend']" in content
        }
        
        all_ok = True
        for integration_name, exists in integrations.items():
            status = "✅" if exists else "❌"
            print(f"{status} {integration_name}")
            if not exists:
                all_ok = False
        
        if all_ok:
            print("🎉 SentimentAnalyzer 集成完整！")
            return True
        else:
            print("⚠️ SentimentAnalyzer 集成不完整")
            return False
    
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def test_functional_integration():
    """测试5：功能集成测试"""
    print("\n" + "=" * 60)
    print("测试5：功能集成测试")
    print("=" * 60)
    
    try:
        from logic.technical_analyzer import TechnicalAnalyzer
        
        ta = TechnicalAnalyzer()
        
        # 测试1：不传入实时价格（降级方案）
        print("🔍 测试1：不传入实时价格（降级方案）")
        result1 = ta._fetch_single_stock('600519')
        print(f"  结果: {result1}")
        
        # 测试2：传入实时价格（模拟盘中）
        print("🔍 测试2：传入实时价格（模拟盘中）")
        result2 = ta._fetch_single_stock('600519', real_time_price=1800.0)
        print(f"  结果: {result2}")
        
        # 测试3：批量分析
        print("🔍 测试3：批量分析（包含实时价格）")
        test_stocks = [
            {'code': '600519', 'price': 1800.0},
            {'code': '000001', 'price': 10.5}
        ]
        import time
        start_time = time.time()
        results = ta.analyze_batch(test_stocks)
        elapsed_time = time.time() - start_time
        
        print(f"  分析耗时: {elapsed_time:.2f} 秒")
        print(f"  分析结果:")
        for code, result in results.items():
            print(f"    {code}: {result}")
        
        # 验证实时价格是否生效
        if '🟢 站上20日线' in result2:
            print("✅ 实时价格注入功能正常")
            return True
        else:
            print("❌ 实时价格注入功能异常")
            return False
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("V10.1.9.1 逻辑完整性审计测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 执行所有测试
    results = {
        'AI Agent 规则': test_ai_agent_rules(),
        'UI 显示功能': test_ui_display(),
        'TechnicalAnalyzer': test_technical_analyzer(),
        'SentimentAnalyzer': test_sentiment_analyzer(),
        '功能集成': test_functional_integration()
    }
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {test_name}")
    
    # 最终结论
    print("\n" + "=" * 60)
    if all(results.values()):
        print("🎉 所有测试通过！")
        print("✅ V10.1.9.1 功能完整，逻辑无损")
        print("✅ Git 合并成功，无逻辑丢失")
        print()
        print("系统状态：")
        print("  - AI Agent: 拥有完整的K线趋势否决权")
        print("  - UI 显示: 技术形态和风险扫描共存")
        print("  - TechnicalAnalyzer: 实时价格注入正常")
        print("  - SentimentAnalyzer: 集成完整")
        return 0
    else:
        print("⚠️ 部分测试失败")
        print("🚨 发现逻辑丢失或功能异常")
        print()
        print("请检查失败的测试项并修复")
        return 1

if __name__ == '__main__':
    sys.exit(main())
