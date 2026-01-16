"""
V10.0 炸板类型测试脚本

测试炸板类型区分和 AI Context 优化功能。

Author: iFlow CLI
Version: V10.0 Enhanced
Date: 2026-01-16
"""

import sys
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, 'E:\\MyQuantTool')

from logic.data_manager import DataManager
from logic.sentiment_analyzer import SentimentAnalyzer


def test_zhaban_types():
    """测试炸板类型区分"""
    print("\n" + "="*60)
    print("测试 1: 炸板类型区分（良性/恶性）")
    print("="*60)
    
    try:
        dm = DataManager()
        sa = SentimentAnalyzer(dm)
        
        # 获取市场情绪数据
        print("正在获取市场情绪数据...")
        mood = sa.analyze_market_mood(force_refresh=True)
        
        if mood:
            print(f"✅ 市场情绪分析成功")
            print(f"   - 涨停家数: {mood['limit_up']}")
            print(f"   - 炸板家数: {mood['zhaban_count']}")
            print(f"   - 炸板率: {mood['zhaban_rate']}%")
            
            # 炸板类型统计
            if mood['zhaban_count'] > 0:
                print(f"\n📊 炸板类型统计:")
                print(f"   - 良性炸板: {mood.get('benign_zhaban_count', 0)}家")
                print(f"   - 恶性炸板: {mood.get('malignant_zhaban_count', 0)}家")
                print(f"   - 平均回撤: {mood.get('avg_drop_pct', 0)}%")
                
                # 炸板类型解读
                malignant_ratio = mood.get('malignant_zhaban_count', 0) / mood['zhaban_count'] * 100
                print(f"\n📈 恶性炸板占比: {malignant_ratio:.1f}%")
                
                if malignant_ratio > 60:
                    print(f"   - 解读: 恶性炸板占比高，市场抛压极大")
                elif malignant_ratio > 40:
                    print(f"   - 解读: 恶性炸板占比较高，市场分歧严重")
                else:
                    print(f"   - 解读: 良性炸板占主导，市场分歧较小")
            else:
                print(f"\n📊 当前无炸板股票")
            
            return True
        else:
            print("❌ 市场情绪分析失败")
            return False
            
    except Exception as e:
        print(f"❌ 炸板类型区分测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_context_optimization():
    """测试 AI Context 优化（Token 瘦身）"""
    print("\n" + "="*60)
    print("测试 2: AI Context 优化（Token 瘦身）")
    print("="*60)
    
    try:
        dm = DataManager()
        sa = SentimentAnalyzer(dm)
        
        print("正在生成 AI 数据包（包含股票池）...")
        start_time = time.time()
        ai_context = sa.generate_ai_context(include_stock_pool=True, stock_pool_size=20)
        elapsed_time = time.time() - start_time
        
        if ai_context and 'error' not in ai_context:
            print(f"✅ AI 数据包生成成功 (耗时: {elapsed_time:.2f}秒)")
            
            # 检查股票池大小
            stock_pool = ai_context.get('stock_pool', {})
            pool_size = stock_pool.get('size', 0)
            print(f"\n📋 股票池大小: {pool_size} 只")
            
            if pool_size <= 10:
                print(f"✅ 股票池大小符合要求（<= 10）")
            else:
                print(f"⚠️  股票池大小超过建议值（建议 <= 10）")
            
            # 检查字段精简
            if 'stocks' in stock_pool:
                first_stock = stock_pool['stocks'][0]
                print(f"\n📊 股票数据字段数量: {len(first_stock)}")
                print(f"   字段列表: {list(first_stock.keys())}")
                
                # 检查是否去除了冗余字段
                redundant_fields = ['base_score', 'time_weight', 'time_weight_desc', 'turnover_rate', 'amount', 
                                   'weak_to_strong_bonus', 'lianban_bonus', 'high_risk_penalty', 'strategy_key']
                has_redundant = any(field in first_stock for field in redundant_fields)
                
                if not has_redundant:
                    print(f"✅ 已去除冗余字段，Token 消耗优化")
                else:
                    print(f"⚠️  仍存在冗余字段，可进一步优化")
            
            # 检查炸板类型数据
            sentiment = ai_context.get('market_sentiment', {})
            print(f"\n📊 炸板类型数据:")
            print(f"   - 炸板家数: {sentiment.get('zhaban_count', 0)}")
            print(f"   - 良性炸板: {sentiment.get('benign_zhaban_count', 0)}")
            print(f"   - 恶性炸板: {sentiment.get('malignant_zhaban_count', 0)}")
            
            # 格式化为 LLM 文本
            print(f"\n📝 LLM 格式化输出:")
            llm_text = sa.format_ai_context_for_llm(ai_context)
            print(f"   文本长度: {len(llm_text)} 字符")
            
            # 估算 Token 数量（中文约 1.5 字符 = 1 Token）
            estimated_tokens = len(llm_text) / 1.5
            print(f"   估算 Token 数: {estimated_tokens:.0f}")
            
            if estimated_tokens < 2000:
                print(f"✅ Token 数量合理（< 2000）")
            else:
                print(f"⚠️  Token 数量较多，建议进一步精简")
            
            return True
        else:
            print(f"❌ AI 数据包生成失败: {ai_context.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"❌ AI Context 优化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("V10.0 炸板类型和 AI Context 优化测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        '炸板类型区分': test_zhaban_types(),
        'AI Context 优化': test_ai_context_optimization()
    }
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！V10.0 增强功能验证成功！")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查错误信息")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
