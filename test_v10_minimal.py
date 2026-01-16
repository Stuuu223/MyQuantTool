"""
V10.0 最小化测试脚本

只测试炸板类型和 AI Context 优化，不依赖概念映射数据。

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


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("V10.0 最小化测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 初始化
        print("\n正在初始化...")
        dm = DataManager()
        sa = SentimentAnalyzer(dm)
        print("✅ 初始化成功")
        
        # 测试炸板类型
        print("\n" + "-"*60)
        print("测试 1: 炸板类型区分")
        print("-"*60)
        
        mood = sa.analyze_market_mood(force_refresh=True)
        
        if mood:
            print(f"✅ 市场情绪分析成功")
            print(f"   - 涨停家数: {mood['limit_up']}")
            print(f"   - 炸板家数: {mood['zhaban_count']}")
            print(f"   - 炸板率: {mood['zhaban_rate']}%")
            
            if mood['zhaban_count'] > 0:
                print(f"\n📊 炸板类型统计:")
                print(f"   - 良性炸板: {mood.get('benign_zhaban_count', 0)}家")
                print(f"   - 恶性炸板: {mood.get('malignant_zhaban_count', 0)}家")
                print(f"   - 平均回撤: {mood.get('avg_drop_pct', 0)}%")
                
                malignant_ratio = mood.get('malignant_zhaban_count', 0) / mood['zhaban_count'] * 100
                print(f"\n📈 恶性炸板占比: {malignant_ratio:.1f}%")
        
        # 测试 AI Context 优化
        print("\n" + "-"*60)
        print("测试 2: AI Context 优化")
        print("-"*60)
        
        start_time = time.time()
        ai_context = sa.generate_ai_context(include_stock_pool=True, stock_pool_size=20)
        elapsed_time = time.time() - start_time
        
        if ai_context and 'error' not in ai_context:
            print(f"✅ AI 数据包生成成功 (耗时: {elapsed_time:.2f}秒)")
            
            stock_pool = ai_context.get('stock_pool', {})
            pool_size = stock_pool.get('size', 0)
            print(f"   - 股票池大小: {pool_size} 只")
            
            if 'stocks' in stock_pool:
                first_stock = stock_pool['stocks'][0]
                print(f"   - 字段数量: {len(first_stock)}")
                
                llm_text = sa.format_ai_context_for_llm(ai_context)
                estimated_tokens = len(llm_text) / 1.5
                print(f"   - 估算 Token 数: {estimated_tokens:.0f}")
        
        print("\n" + "="*60)
        print("✅ 测试完成！")
        print("="*60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())