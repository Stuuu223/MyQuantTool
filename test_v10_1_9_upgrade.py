"""
V10.1.9 - Technical Vision (K线视野) 升级测试脚本

测试内容：
1. 测试 TechnicalAnalyzer 类是否正常工作
2. 测试 SentimentAnalyzer 是否正确导入和初始化 TechnicalAnalyzer
3. 测试 generate_ai_context 方法是否正确调用技术分析
4. 测试 AI Agent 的 Prompt 是否包含新的风控规则

Author: iFlow CLI
Date: 2026-01-17
"""

import sys
import time
from datetime import datetime

# 测试 1: TechnicalAnalyzer 类
print("=" * 60)
print("测试 1: TechnicalAnalyzer 类")
print("=" * 60)

try:
    from logic.technical_analyzer import TechnicalAnalyzer
    print("✅ TechnicalAnalyzer 导入成功")
    
    # 初始化
    ta = TechnicalAnalyzer()
    print("✅ TechnicalAnalyzer 初始化成功")
    print(f"   start_date: {ta.start_date}")
    
    # 测试单只股票分析
    test_code = "600519"  # 贵州茅台
    print(f"\n🔍 测试单只股票分析: {test_code}")
    result = ta._fetch_single_stock(test_code)
    print(f"   结果: {result}")
    
    # 测试批量分析
    print(f"\n🔍 测试批量分析")
    stock_list = [
        {'code': '600519'},
        {'code': '000001'},
        {'code': '000002'}
    ]
    start_time = time.time()
    batch_results = ta.analyze_batch(stock_list)
    elapsed_time = time.time() - start_time
    
    print(f"   分析数量: {len(stock_list)} 只")
    print(f"   耗时: {elapsed_time:.2f} 秒")
    print(f"   结果:")
    for code, result in batch_results.items():
        print(f"     {code}: {result}")
    
    print("\n✅ TechnicalAnalyzer 测试通过")
    
except Exception as e:
    print(f"❌ TechnicalAnalyzer 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 2: SentimentAnalyzer 是否正确导入和初始化 TechnicalAnalyzer
print("\n" + "=" * 60)
print("测试 2: SentimentAnalyzer 集成")
print("=" * 60)

try:
    from logic.sentiment_analyzer import SentimentAnalyzer
    from logic.data_manager import DataManager
    
    print("✅ SentimentAnalyzer 导入成功")
    
    # 初始化
    db = DataManager()
    analyzer = SentimentAnalyzer(db)
    print("✅ SentimentAnalyzer 初始化成功")
    
    # 检查是否有 ta 属性
    if hasattr(analyzer, 'ta'):
        print("✅ SentimentAnalyzer.ta 属性存在")
        print(f"   类型: {type(analyzer.ta)}")
    else:
        print("❌ SentimentAnalyzer.ta 属性不存在")
        sys.exit(1)
    
    # 测试 generate_ai_context 方法（不包含股票池，避免耗时过长）
    print(f"\n🔍 测试 generate_ai_context 方法（不包含股票池）")
    start_time = time.time()
    ai_context = analyzer.generate_ai_context(include_stock_pool=False)
    elapsed_time = time.time() - start_time
    
    print(f"   耗时: {elapsed_time:.2f} 秒")
    print(f"   市场情绪得分: {ai_context['market_sentiment']['score']}")
    print(f"   市场温度: {ai_context['market_sentiment']['temperature']}")
    
    print("\n✅ SentimentAnalyzer 集成测试通过")
    
except Exception as e:
    print(f"❌ SentimentAnalyzer 集成测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 3: AI Agent 的 Prompt 是否包含新的风控规则
print("\n" + "=" * 60)
print("测试 3: AI Agent Prompt 验证")
print("=" * 60)

try:
    from logic.ai_agent import RealAIAgent
    
    print("✅ RealAIAgent 导入成功")
    
    # 初始化（使用虚拟 API key，仅测试 Prompt 生成）
    agent = RealAIAgent(api_key="test_key", provider="deepseek")
    print("✅ RealAIAgent 初始化成功")
    
    # 检查 _build_prompt 方法
    print(f"\n🔍 检查 _build_prompt 方法")
    
    # 构建测试上下文
    test_context = """
股票代码: 600519
股票名称: 贵州茅台
当前价格: 1800.00
今日涨跌幅: 5.0%
"""
    
    # 生成 Prompt
    prompt = agent._build_prompt(test_context, use_dragon_tactics=True)
    
    # 检查是否包含 V10.1.6 风控规则
    checks = {
        "V10.1.6 核心风控守则": "## V10.1.6 核心风控守则" in prompt,
        "K线趋势否决权": "K线趋势否决权" in prompt,
        "跌破20日线": "跌破20日线" in prompt,
        "多头排列": "多头排列" in prompt,
        "短期超买": "短期超买" in prompt,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}: {'通过' if result else '失败'}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n✅ AI Agent Prompt 验证通过")
    else:
        print("\n❌ AI Agent Prompt 验证失败")
        sys.exit(1)
    
except Exception as e:
    print(f"❌ AI Agent Prompt 验证失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 4: 性能测试
print("\n" + "=" * 60)
print("测试 4: 性能测试")
print("=" * 60)

try:
    from logic.technical_analyzer import TechnicalAnalyzer
    
    ta = TechnicalAnalyzer()
    
    # 测试不同数量的股票分析
    test_cases = [1, 4, 8]
    
    for count in test_cases:
        stock_list = [{'code': f'600{str(i).zfill(3)}'} for i in range(count)]
        
        start_time = time.time()
        results = ta.analyze_batch(stock_list)
        elapsed_time = time.time() - start_time
        
        avg_time = elapsed_time / count if count > 0 else 0
        
        print(f"   {count} 只股票: {elapsed_time:.2f} 秒 (平均 {avg_time:.2f} 秒/只)")
    
    print("\n✅ 性能测试通过")
    
except Exception as e:
    print(f"❌ 性能测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 总结
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)
print("✅ 所有测试通过！")
print("\nV10.1.9 升级完成，功能验证成功！")
print("=" * 60)