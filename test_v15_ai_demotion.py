#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V15 "The AI Demotion" 性能测试

测试目标：
1. 验证 AI 降级为信息提取器（ETL）功能
2. 验证决策链重构（DDE 60%, Trend 40%, AI Bonus）
3. 验证数据源过滤功能（优先官方公告，屏蔽自媒体）
4. 验证边界条件和异常处理
"""

import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from logic.ai_agent import RealAIAgent, RuleBasedAgent
from logic.signal_generator import get_signal_generator_v13
from logic.news_crawler import NewsCrawlerManager
from logic.logger import get_logger

logger = get_logger(__name__)


class V15AIDemotionTester:
    """V15 AI 降级测试器"""
    
    def __init__(self):
        """初始化测试器"""
        self.test_results = []
        self.sg = get_signal_generator_v13()
        self.news_manager = NewsCrawlerManager()
        
        # 初始化 AI 代理（使用模拟 API）
        self.ai_agent = RealAIAgent(api_key="test_key", provider="deepseek")
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("="*60)
        logger.info("V15 AI Demotion 性能测试开始")
        logger.info("="*60)
        
        # 测试1：AI 信息提取功能
        self.test_ai_extraction()
        
        # 测试2：决策链重构
        self.test_decision_chain()
        
        # 测试3：数据源过滤
        self.test_news_filtering()
        
        # 测试4：边界条件
        self.test_edge_cases()
        
        # 测试5：异常处理
        self.test_error_handling()
        
        # 生成测试报告
        self.generate_test_report()
        
        logger.info("="*60)
        logger.info("V15 AI Demotion 性能测试完成")
        logger.info("="*60)
    
    def test_ai_extraction(self):
        """测试1：AI 信息提取功能"""
        logger.info("\n" + "="*60)
        logger.info("测试1：AI 信息提取功能（ETL）")
        logger.info("="*60)
        
        try:
            start_time = time.time()
            
            # 测试用例1：官方公告
            official_text = """
            公告编号：2024-001
            XX股份有限公司关于签订重大合同的公告
            本公司于2024年1月15日与XX科技有限公司签订战略合作协议，
            合同金额为15.6亿元，涉及人形机器人研发项目。
            """
            
            result1 = self.ai_agent.extract_structured_info(official_text)
            
            # 验证结果
            assert result1['is_official_announcement'] == True, "官方公告识别失败"
            assert result1['contract_amount'] == 15.6, "合同金额提取失败"
            assert '人形机器人' in result1['core_concepts'], "核心概念提取失败"
            
            logger.info(f"  ✅ 官方公告提取成功: {result1}")
            
            # 测试用例2：风险公告
            risk_text = """
            XX股份有限公司收到监管函
            公司因信息披露违规被立案调查，存在退市风险。
            """
            
            result2 = self.ai_agent.extract_structured_info(risk_text)
            
            # 验证结果
            assert result2['risk_warning'] == True, "风险检测失败"
            assert '监管函' in result2['risk_keywords'] or '立案' in result2['risk_keywords'], "风险关键词提取失败"
            
            logger.info(f"  ✅ 风险公告提取成功: {result2}")
            
            # 测试用例3：普通新闻
            news_text = """
            AI芯片板块持续火热，多家公司发布新产品。
            算力需求激增，相关概念股表现强势。
            """
            
            result3 = self.ai_agent.extract_structured_info(news_text)
            
            # 验证结果
            assert 'AI芯片' in result3['core_concepts'] or '算力' in result3['core_concepts'], "概念提取失败"
            
            logger.info(f"  ✅ 普通新闻提取成功: {result3}")
            
            elapsed_time = time.time() - start_time
            
            test_result = {
                'test_name': 'AI 信息提取功能',
                'status': '✅ 通过',
                'elapsed_time': elapsed_time,
                'details': f'成功测试官方公告、风险公告、普通新闻提取'
            }
            
            logger.info(f"✅ AI 信息提取功能测试通过 (耗时: {elapsed_time:.2f}秒)")
            
        except Exception as e:
            test_result = {
                'test_name': 'AI 信息提取功能',
                'status': '❌ 失败',
                'elapsed_time': 0,
                'details': str(e)
            }
            logger.error(f"❌ AI 信息提取功能测试失败: {e}")
        
        self.test_results.append(test_result)
    
    def test_decision_chain(self):
        """测试2：决策链重构"""
        logger.info("\n" + "="*60)
        logger.info("测试2：决策链重构（DDE 60%, Trend 40%, AI Bonus）")
        logger.info("="*60)
        
        try:
            start_time = time.time()
            
            # 测试用例1：资金流入 + 趋势向上 + AI 命中热门板块
            ai_info = {
                'is_official_announcement': True,
                'contract_amount': 10.0,
                'risk_warning': False,
                'core_concepts': ['人形机器人'],
                'risk_keywords': [],
                'parties': []
            }
            
            result1 = self.sg.calculate_final_signal(
                stock_code='600000',
                ai_narrative_score=50,  # AI 评分不再重要
                capital_flow_data=50000000,  # 资金流入 5000万
                trend_status='UP',
                circulating_market_cap=10000000000,  # 100亿
                current_pct_change=5.0,
                ai_extracted_info=ai_info,
                top_sectors=['机器人', '人形机器人']
            )
            
            # 验证结果
            assert result1['dde_score'] > 0, "DDE 得分计算失败"
            assert result1['trend_score'] > 0, "趋势得分计算失败"
            assert result1['ai_bonus'] > 0, "AI 加分计算失败"
            assert result1['signal'] == 'BUY', "信号生成失败"
            
            logger.info(f"  ✅ 资金流入+趋势向上+AI命中: {result1}")
            
            # 测试用例2：AI 风险一票否决
            ai_info_risk = {
                'is_official_announcement': True,
                'contract_amount': None,
                'risk_warning': True,
                'core_concepts': [],
                'risk_keywords': ['监管函', '立案'],
                'parties': []
            }
            
            result2 = self.sg.calculate_final_signal(
                stock_code='600001',
                ai_narrative_score=90,  # 即使 AI 评分很高
                capital_flow_data=100000000,  # 资金流入
                trend_status='UP',
                circulating_market_cap=10000000000,
                current_pct_change=3.0,
                ai_extracted_info=ai_info_risk,
                top_sectors=[]
            )
            
            # 验证结果
            assert result2['signal'] == 'SELL', "风险一票否决失败"
            assert result2['fact_veto'] == True, "风险标记失败"
            
            logger.info(f"  ✅ AI 风险一票否决: {result2}")
            
            # 测试用例3：资金流出（即使 AI 评分高）
            result3 = self.sg.calculate_final_signal(
                stock_code='600002',
                ai_narrative_score=95,  # AI 评分很高
                capital_flow_data=-60000000,  # 资金流出 6000万（超过阈值）
                trend_status='UP',
                circulating_market_cap=10000000000,
                current_pct_change=2.0,
                ai_extracted_info=None,
                top_sectors=[]
            )
            
            # 验证结果
            assert result3['signal'] == 'SELL', "资金流出否决失败"
            assert result3['fact_veto'] == True, "资金流出标记失败"
            
            logger.info(f"  ✅ 资金流出否决: {result3}")
            
            # 测试用例4：趋势向下（即使资金流入）
            result4 = self.sg.calculate_final_signal(
                stock_code='600003',
                ai_narrative_score=80,
                capital_flow_data=30000000,  # 资金流入
                trend_status='DOWN',  # 趋势向下
                circulating_market_cap=10000000000,
                current_pct_change=-1.0,
                ai_extracted_info=None,
                top_sectors=[]
            )
            
            # 验证结果
            assert result4['signal'] == 'WAIT', "趋势向下否决失败"
            
            logger.info(f"  ✅ 趋势向下否决: {result4}")
            
            elapsed_time = time.time() - start_time
            
            test_result = {
                'test_name': '决策链重构',
                'status': '✅ 通过',
                'elapsed_time': elapsed_time,
                'details': f'成功测试资金流、趋势、AI 加分、风险否决'
            }
            
            logger.info(f"✅ 决策链重构测试通过 (耗时: {elapsed_time:.2f}秒)")
            
        except Exception as e:
            test_result = {
                'test_name': '决策链重构',
                'status': '❌ 失败',
                'elapsed_time': 0,
                'details': str(e)
            }
            logger.error(f"❌ 决策链重构测试失败: {e}")
        
        self.test_results.append(test_result)
    
    def test_news_filtering(self):
        """测试3：数据源过滤"""
        logger.info("\n" + "="*60)
        logger.info("测试3：数据源过滤（优先官方公告，屏蔽自媒体）")
        logger.info("="*60)
        
        try:
            start_time = time.time()
            
            # 测试用例1：官方公告识别
            from logic.news_crawler import NewsItem
            
            official_news = NewsItem(
                title="XX股份有限公司关于签订重大合同的公告",
                content="公司于2024年1月15日与XX科技有限公司签订战略合作协议",
                source="巨潮资讯网",
                publish_time=datetime.now(),
                url="http://www.cninfo.com.cn/new/disclosure/detail?stockCode=000001&announcementId=123456",
                related_stocks=['000001']
            )
            
            is_official = self.news_manager._is_official_announcement(official_news)
            assert is_official == True, "官方公告识别失败"
            
            logger.info(f"  ✅ 官方公告识别成功")
            
            # 测试用例2：自媒体识别
            self_media_news = NewsItem(
                title="🔥 重磅！这只股票明天要涨停！大V独家推荐！",
                content="独家内幕消息，这只股票明天要暴涨，赶紧上车！",
                source="股吧",
                publish_time=datetime.now(),
                url="http://guba.eastmoney.com/news,000001,123456.html",
                related_stocks=['000001']
            )
            
            is_self_media = self.news_manager._is_self_media(self_media_news)
            assert is_self_media == True, "自媒体识别失败"
            
            logger.info(f"  ✅ 自媒体识别成功")
            
            # 测试用例3：新闻过滤
            test_news_list = [
                official_news,
                self_media_news,
                NewsItem(
                    title="AI芯片板块持续火热",
                    content="多家公司发布新产品",
                    source="新浪财经",
                    publish_time=datetime.now(),
                    url="http://finance.sina.com.cn/stock/2024-01-15/123456.html",
                    related_stocks=['000002']
                )
            ]
            
            filtered_news = self.news_manager._filter_news(test_news_list)
            
            # 验证：自媒体应该被过滤掉
            assert len(filtered_news) == 2, "新闻过滤失败"
            assert filtered_news[0] == official_news, "官方公告优先级失败"
            
            logger.info(f"  ✅ 新闻过滤成功: {len(filtered_news)} 条（屏蔽 1 条自媒体）")
            
            elapsed_time = time.time() - start_time
            
            test_result = {
                'test_name': '数据源过滤',
                'status': '✅ 通过',
                'elapsed_time': elapsed_time,
                'details': f'成功测试官方公告识别、自媒体识别、新闻过滤'
            }
            
            logger.info(f"✅ 数据源过滤测试通过 (耗时: {elapsed_time:.2f}秒)")
            
        except Exception as e:
            test_result = {
                'test_name': '数据源过滤',
                'status': '❌ 失败',
                'elapsed_time': 0,
                'details': str(e)
            }
            logger.error(f"❌ 数据源过滤测试失败: {e}")
        
        self.test_results.append(test_result)
    
    def test_edge_cases(self):
        """测试4：边界条件"""
        logger.info("\n" + "="*60)
        logger.info("测试4：边界条件测试")
        logger.info("="*60)
        
        try:
            start_time = time.time()
            
            # 测试用例1：空文本提取
            result1 = self.ai_agent.extract_structured_info("")
            assert result1['is_official_announcement'] == False, "空文本处理失败"
            logger.info(f"  ✅ 空文本处理成功")
            
            # 测试用例2：零资金流
            result2 = self.sg.calculate_final_signal(
                stock_code='600000',
                ai_narrative_score=50,
                capital_flow_data=0,  # 零资金流
                trend_status='SIDEWAY',
                circulating_market_cap=10000000000,
                current_pct_change=0.0,
                ai_extracted_info=None,
                top_sectors=[]
            )
            assert result2['dde_score'] >= 0, "零资金流处理失败"
            logger.info(f"  ✅ 零资金流处理成功")
            
            # 测试用例3：无 AI 信息
            result3 = self.sg.calculate_final_signal(
                stock_code='600001',
                ai_narrative_score=50,
                capital_flow_data=50000000,
                trend_status='UP',
                circulating_market_cap=10000000000,
                current_pct_change=3.0,
                ai_extracted_info=None,  # 无 AI 信息
                top_sectors=['机器人']
            )
            assert result3['ai_bonus'] == 0, "无 AI 信息处理失败"
            logger.info(f"  ✅ 无 AI 信息处理成功")
            
            # 测试用例4：涨停豁免
            result4 = self.sg.calculate_final_signal(
                stock_code='600002',
                ai_narrative_score=50,
                capital_flow_data=-30000000,  # 资金流出（但未达到阈值）
                trend_status='DOWN',  # 趋势向下
                circulating_market_cap=10000000000,
                current_pct_change=9.8,  # 涨停
                ai_extracted_info=None,
                top_sectors=[]
            )
            assert result4['limit_up_immunity'] == True, "涨停豁免识别失败"
            logger.info(f"  ✅ 涨停豁免识别成功")
            
            elapsed_time = time.time() - start_time
            
            test_result = {
                'test_name': '边界条件测试',
                'status': '✅ 通过',
                'elapsed_time': elapsed_time,
                'details': f'成功测试空文本、零资金流、无 AI 信息、涨停豁免'
            }
            
            logger.info(f"✅ 边界条件测试通过 (耗时: {elapsed_time:.2f}秒)")
            
        except Exception as e:
            test_result = {
                'test_name': '边界条件测试',
                'status': '❌ 失败',
                'elapsed_time': 0,
                'details': str(e)
            }
            logger.error(f"❌ 边界条件测试失败: {e}")
        
        self.test_results.append(test_result)
    
    def test_error_handling(self):
        """测试5：异常处理"""
        logger.info("\n" + "="*60)
        logger.info("测试5：异常处理测试")
        logger.info("="*60)
        
        try:
            start_time = time.time()
            
            # 测试用例1：无效股票代码
            result1 = self.sg.calculate_final_signal(
                stock_code='INVALID',
                ai_narrative_score=50,
                capital_flow_data=0,
                trend_status='SIDEWAY',
                circulating_market_cap=0,
                current_pct_change=0,
                ai_extracted_info=None,
                top_sectors=[]
            )
            # 应该不会抛出异常
            assert 'signal' in result1, "无效股票代码处理失败"
            logger.info(f"  ✅ 无效股票代码处理成功")
            
            # 测试用例2：None 输入
            result2 = self.ai_agent.extract_structured_info(None)
            # 应该不会抛出异常
            assert 'is_official_announcement' in result2, "None 输入处理失败"
            logger.info(f"  ✅ None 输入处理成功")
            
            # 测试用例3：超大金额
            ai_info = {
                'is_official_announcement': True,
                'contract_amount': 999999.0,  # 超大金额
                'risk_warning': False,
                'core_concepts': [],
                'risk_keywords': [],
                'parties': []
            }
            
            result3 = self.sg.calculate_final_signal(
                stock_code='600000',
                ai_narrative_score=50,
                capital_flow_data=50000000,
                trend_status='UP',
                circulating_market_cap=10000000000,
                current_pct_change=5.0,
                ai_extracted_info=ai_info,
                top_sectors=[]
            )
            # 应该不会抛出异常
            assert 'final_score' in result3, "超大金额处理失败"
            logger.info(f"  ✅ 超大金额处理成功")
            
            elapsed_time = time.time() - start_time
            
            test_result = {
                'test_name': '异常处理测试',
                'status': '✅ 通过',
                'elapsed_time': elapsed_time,
                'details': f'成功测试无效股票代码、None 输入、超大金额'
            }
            
            logger.info(f"✅ 异常处理测试通过 (耗时: {elapsed_time:.2f}秒)")
            
        except Exception as e:
            test_result = {
                'test_name': '异常处理测试',
                'status': '❌ 失败',
                'elapsed_time': 0,
                'details': str(e)
            }
            logger.error(f"❌ 异常处理测试失败: {e}")
        
        self.test_results.append(test_result)
    
    def generate_test_report(self):
        """生成测试报告"""
        logger.info("\n" + "="*60)
        logger.info("测试报告")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['status'] == '✅ 通过')
        failed_tests = sum(1 for r in self.test_results if r['status'] == '❌ 失败')
        
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"通过: {passed_tests}")
        logger.info(f"失败: {failed_tests}")
        
        logger.info("\n详细结果:")
        for i, result in enumerate(self.test_results, 1):
            logger.info(f"{i}. {result['test_name']}: {result['status']}")
            logger.info(f"   耗时: {result['elapsed_time']:.2f}秒")
            logger.info(f"   详情: {result['details']}")
        
        # 保存测试报告到文件
        report_file = Path("data/review_cases/v15_ai_demotion_test_report.txt")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("V15 AI Demotion 性能测试报告\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"总测试数: {total_tests}\n")
            f.write(f"通过: {passed_tests}\n")
            f.write(f"失败: {failed_tests}\n\n")
            
            f.write("详细结果:\n")
            for i, result in enumerate(self.test_results, 1):
                f.write(f"\n{i}. {result['test_name']}: {result['status']}\n")
                f.write(f"   耗时: {result['elapsed_time']:.2f}秒\n")
                f.write(f"   详情: {result['details']}\n")
        
        logger.info(f"\n测试报告已保存到: {report_file}")


def main():
    """主函数"""
    try:
        tester = V15AIDemotionTester()
        tester.run_all_tests()
        
        print("\n" + "="*60)
        print("V15 AI Demotion 性能测试完成！")
        print("="*60)
        
    except Exception as e:
        logger.error(f"测试运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
