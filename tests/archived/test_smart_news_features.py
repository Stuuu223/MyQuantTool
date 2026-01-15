"""
测试智能新闻分析功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.news_crawler import NewsCrawlerManager, NewsItem
from logic.ml_news_analyzer import MLNewsAnalyzer
from logic.feedback_learning import FeedbackLearningSystem
from datetime import datetime

def test_news_crawler():
    """测试新闻爬虫"""
    print("=" * 60)
    print("测试 1: 新闻爬虫")
    print("=" * 60)
    
    try:
        manager = NewsCrawlerManager()
        print(f"[OK] 可用新闻源: {manager.get_available_sources()}")
        
        # 测试爬取少量新闻
        print("\n开始爬取新闻（每个源2条）...")
        news_list = manager.crawl_all(limit_per_source=2)
        
        print(f"[OK] 成功爬取 {len(news_list)} 条新闻")
        
        for i, news in enumerate(news_list[:3], 1):
            print(f"\n新闻 {i}:")
            print(f"  标题: {news.title}")
            print(f"  来源: {news.source}")
            print(f"  时间: {news.publish_time}")
            print(f"  相关股票: {news.related_stocks}")
        
        return True, news_list
        
    except Exception as e:
        print(f"[FAIL] 新闻爬虫测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, []

def test_ml_analyzer():
    """测试机器学习分析器"""
    print("\n" + "=" * 60)
    print("测试 2: 机器学习分析器")
    print("=" * 60)
    
    try:
        analyzer = MLNewsAnalyzer()
        
        # 创建示例训练数据
        print("创建示例训练数据...")
        sample_data = analyzer.create_sample_training_data()
        print(f"[OK] 创建了 {len(sample_data)} 条训练数据")
        
        # 训练模型
        print("\n训练模型...")
        results = analyzer.train_models(sample_data)
        print(f"[OK] 情绪分类准确率: {results['sentiment_accuracy']:.4f}")
        print(f"[OK] 影响度预测MSE: {results['impact_mse']:.4f}")
        
        # 测试预测
        print("\n测试预测...")
        test_news = {
            'title': '公司业绩超预期，股价大涨',
            'content': '公司发布业绩报告，净利润大幅增长，超出市场预期，股价应声上涨。',
            'source': '证券时报',
            'related_stocks': ['600519']
        }
        
        prediction = analyzer.analyze(
            test_news['title'],
            test_news['content'],
            test_news['source'],
            test_news['related_stocks']
        )
        
        print(f"[OK] 预测结果:")
        print(f"  情绪: {prediction.sentiment}")
        print(f"  置信度: {prediction.sentiment_confidence:.4f}")
        print(f"  影响度: {prediction.impact_score:.2f}")
        
        # 保存模型
        print("\n保存模型...")
        analyzer.save_models()
        print("[OK] 模型已保存")
        
        # 测试加载模型
        print("\n测试加载模型...")
        new_analyzer = MLNewsAnalyzer()
        new_analyzer.load_models()
        
        prediction2 = new_analyzer.analyze(
            test_news['title'],
            test_news['content'],
            test_news['source'],
            test_news['related_stocks']
        )
        
        print(f"[OK] 加载后预测结果:")
        print(f"  情绪: {prediction2.sentiment}")
        print(f"  置信度: {prediction2.sentiment_confidence:.4f}")
        print(f"  影响度: {prediction2.impact_score:.2f}")
        
        return True, analyzer
        
    except Exception as e:
        print(f"[FAIL] 机器学习分析器测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def test_feedback_learning(ml_analyzer):
    """测试反馈学习系统"""
    print("\n" + "=" * 60)
    print("测试 3: 反馈学习系统")
    print("=" * 60)
    
    try:
        feedback_system = FeedbackLearningSystem(ml_analyzer)
        
        # 测试预测和记录
        print("测试预测和记录...")
        result = feedback_system.predict_and_record(
            title="公司业绩大幅增长，股价创新高",
            content="公司发布业绩报告，净利润同比增长80%，股价应声上涨，创下历史新高。",
            source="证券时报",
            related_stocks=["600519"]
        )
        
        print(f"[OK] 预测已记录，ID: {result['record_id']}")
        print(f"  情绪: {result['prediction'].sentiment}")
        print(f"  置信度: {result['prediction'].sentiment_confidence:.4f}")
        
        # 测试添加反馈
        print("\n测试添加反馈...")
        feedback_system.add_feedback(
            record_id=result['record_id'],
            actual_sentiment="positive",
            actual_impact=85.0,
            stock_price_change=5.2,
            notes="预测准确"
        )
        print("[OK] 反馈已添加")
        
        # 获取性能报告
        print("\n获取性能报告...")
        report = feedback_system.get_performance_report(days=30)
        print(f"[OK] 性能报告:")
        print(f"  {report['summary']}")
        print(f"  总预测数: {report['metrics']['total_predictions']}")
        print(f"  准确率: {report['metrics']['accuracy']:.2%}")
        
        # 获取待审核的预测
        print("\n获取待审核的预测...")
        pending = feedback_system.get_predictions_for_review(limit=5)
        print(f"[OK] 待审核预测数: {len(pending)}")
        
        # 导出训练数据
        print("\n导出训练数据...")
        filepath = feedback_system.export_training_data()
        print(f"[OK] 训练数据已导出到: {filepath}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 反馈学习系统测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("开始测试智能新闻分析功能")
    print("=" * 60)
    
    # 测试1: 新闻爬虫
    crawler_success, news_list = test_news_crawler()
    
    # 测试2: 机器学习分析器
    ml_success, ml_analyzer = test_ml_analyzer()
    
    # 测试3: 反馈学习系统
    feedback_success = False
    if ml_success:
        feedback_success = test_feedback_learning(ml_analyzer)
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"新闻爬虫: {'[PASS]' if crawler_success else '[FAIL]'}")
    print(f"机器学习分析器: {'[PASS]' if ml_success else '[FAIL]'}")
    print(f"反馈学习系统: {'[PASS]' if feedback_success else '[FAIL]'}")
    
    all_passed = crawler_success and ml_success and feedback_success
    
    if all_passed:
        print("\n[SUCCESS] 所有测试通过！")
        return 0
    else:
        print("\n[WARNING] 部分测试失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
