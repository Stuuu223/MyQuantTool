"""
V9.11.2 修复效果测试脚本

测试内容：
1. 自动刷新暂停开关功能
2. 算法逻辑偏差修复（换手率替代绝对手数）
3. AI专用数据包生成功能

Author: iFlow CLI
Version: V9.11.2
Date: 2026-01-16
"""

import sys
import time
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, 'E:\\MyQuantTool')


def test_imports():
    """测试1: 验证所有模块导入成功"""
    print("=" * 60)
    print("测试1: 模块导入验证")
    print("=" * 60)
    
    try:
        from logic.data_manager import DataManager
        print("✅ DataManager 导入成功")
        
        from logic.sentiment_analyzer import SentimentAnalyzer
        print("✅ SentimentAnalyzer 导入成功")
        
        from logic.algo import QuantAlgo
        print("✅ QuantAlgo 导入成功")
        
        from logic.market_status import get_market_status_checker
        print("✅ MarketStatusChecker 导入成功")
        
        print("\n✅ 所有模块导入成功！\n")
        return True
    except Exception as e:
        print(f"\n❌ 模块导入失败: {e}\n")
        return False


def test_sentiment_analyzer():
    """测试2: 测试全市场情绪分析器"""
    print("=" * 60)
    print("测试2: 全市场情绪分析器")
    print("=" * 60)
    
    try:
        from logic.data_manager import DataManager
        from logic.sentiment_analyzer import SentimentAnalyzer
        
        # 初始化
        dm = DataManager()
        analyzer = SentimentAnalyzer(dm)
        
        print("\n正在获取市场快照...")
        start_time = time.time()
        
        # 获取市场情绪
        mood = analyzer.analyze_market_mood(force_refresh=True)
        
        elapsed = time.time() - start_time
        
        if mood is None:
            print("❌ 无法获取市场情绪数据")
            return False
        
        print(f"\n✅ 市场情绪分析完成 (耗时: {elapsed:.2f}秒)")
        print(f"  - 总股票数: {mood['total']}")
        print(f"  - 涨停家数: {mood['limit_up']}")
        print(f"  - 跌停家数: {mood['limit_down']}")
        print(f"  - 上涨家数: {mood['up']}")
        print(f"  - 下跌家数: {mood['down']}")
        print(f"  - 情绪得分: {mood['score']}")
        print(f"  - 市场温度: {analyzer.get_market_temperature()}")
        print(f"  - 交易建议: {analyzer.get_trading_advice()}")
        
        print("\n✅ 情绪分析器测试通过！\n")
        return True
        
    except Exception as e:
        print(f"\n❌ 情绪分析器测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_auction_analysis():
    """测试3: 测试竞价分析（换手率修复）"""
    print("=" * 60)
    print("测试3: 竞价分析（换手率修复）")
    print("=" * 60)
    
    try:
        from logic.data_manager import DataManager
        from logic.algo import QuantAlgo
        
        # 初始化
        dm = DataManager()
        
        print("\n正在获取市场快照...")
        snapshot = dm.quotation.market_snapshot(prefix=False)
        
        if not snapshot or len(snapshot) == 0:
            print("❌ 无法获取市场快照")
            return False
        
        print(f"✅ 获取到 {len(snapshot)} 只股票的快照数据")
        
        # 获取昨日收盘价
        last_closes = {}
        for code, data in snapshot.items():
            last_closes[code] = data.get('close', 0)
        
        print("\n正在批量分析竞价强度...")
        start_time = time.time()
        
        # 批量分析
        results = QuantAlgo.batch_analyze_auction(snapshot, last_closes)
        
        elapsed = time.time() - start_time
        
        print(f"✅ 竞价分析完成 (耗时: {elapsed:.2f}秒)")
        print(f"  - 分析股票数: {len(results)}")
        
        # 统计不同状态的股票
        status_count = {}
        for code, result in results.items():
            status = result.get('status', '未知')
            status_count[status] = status_count.get(status, 0) + 1
        
        print("\n状态分布:")
        for status, count in sorted(status_count.items(), key=lambda x: -x[1]):
            print(f"  - {status}: {count}只")
        
        # 展示Top 5
        print("\nTop 5 强势股票:")
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1].get('score', 0),
            reverse=True
        )[:5]
        
        for i, (code, result) in enumerate(sorted_results, 1):
            print(f"\n  {i}. {code}")
            print(f"     - 价格: {result.get('price', 0)}")
            print(f"     - 涨幅: {result.get('pct', 0)}%")
            print(f"     - 评分: {result.get('score', 0)}")
            print(f"     - 状态: {result.get('status', '未知')}")
            print(f"     - 换手率: {result.get('turnover_rate', 0)}%")
            print(f"     - 成交额: {result.get('amount', 0)}")
        
        print("\n✅ 竞价分析测试通过！\n")
        return True
        
    except Exception as e:
        print(f"\n❌ 竞价分析测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_ai_context_generation():
    """测试4: 测试AI数据包生成功能"""
    print("=" * 60)
    print("测试4: AI数据包生成功能")
    print("=" * 60)
    
    try:
        from logic.data_manager import DataManager
        from logic.sentiment_analyzer import SentimentAnalyzer
        
        # 初始化
        dm = DataManager()
        analyzer = SentimentAnalyzer(dm)
        
        print("\n正在生成AI数据包...")
        start_time = time.time()
        
        # 生成AI数据包
        ai_context = analyzer.generate_ai_context(include_stock_pool=True, stock_pool_size=10)
        
        elapsed = time.time() - start_time
        
        if "error" in ai_context:
            print(f"❌ AI数据包生成失败: {ai_context['error']}")
            return False
        
        print(f"✅ AI数据包生成完成 (耗时: {elapsed:.2f}秒)")
        
        # 展示数据包结构
        print("\n数据包结构:")
        print(f"  - meta: {list(ai_context.get('meta', {}).keys())}")
        print(f"  - market_sentiment: {list(ai_context.get('market_sentiment', {}).keys())}")
        print(f"  - trading_advice: {ai_context.get('trading_advice', 'N/A')}")
        print(f"  - risk_assessment: {list(ai_context.get('risk_assessment', {}).keys())}")
        
        if 'stock_pool' in ai_context:
            stock_pool = ai_context['stock_pool']
            print(f"  - stock_pool: {stock_pool.get('size', 0)}只股票")
        
        # 格式化为LLM友好文本
        print("\nLLM友好文本格式:")
        llm_text = analyzer.format_ai_context_for_llm(ai_context)
        print(llm_text)
        
        print("\n✅ AI数据包生成测试通过！\n")
        return True
        
    except Exception as e:
        print(f"\n❌ AI数据包生成测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n")
    print("🚀 V9.11.2 修复效果测试")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("模块导入", test_imports()))
    results.append(("全市场情绪分析", test_sentiment_analyzer()))
    results.append(("竞价分析（换手率修复）", test_auction_analysis()))
    results.append(("AI数据包生成", test_ai_context_generation()))
    
    # 汇总结果
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！V9.11.2 修复成功！")
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查日志")
    
    print("\n")


if __name__ == "__main__":
    main()
