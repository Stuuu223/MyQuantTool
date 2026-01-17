"""
V14 AutoReviewer 测试脚本

测试自动案例收集和复盘功能
"""

import sys
import logging
from datetime import datetime, timedelta
from logic.auto_reviewer import AutoReviewer
from logic.signal_history import get_signal_history_manager
from logic.signal_generator import get_signal_generator_v13
from logic.data_manager import DataManager
from logic.logger import get_logger

logger = get_logger(__name__)


def test_signal_history_storage():
    """
    测试信号历史存储功能
    """
    logger.info('='*60)
    logger.info('测试V14信号历史存储')
    logger.info('='*60)
    
    try:
        shm = get_signal_history_manager()
        sg = get_signal_generator_v13()
        
        # 模拟一些信号数据
        test_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 测试用例1：BUY信号（共振）
        signal1 = sg.calculate_final_signal(
            stock_code='600519',
            ai_narrative_score=80,
            capital_flow_data=50000000,
            trend_status='UP',
            circulating_market_cap=200000000000
        )
        signal1['ai_score'] = 80
        signal1['capital_flow'] = 50000000
        signal1['trend_status'] = 'UP'
        signal1['market_cap'] = 200000000000
        
        shm.save_signal('600519', signal1, test_date)
        logger.info(f"✅ 保存BUY信号: 600519")
        
        # 测试用例2：SELL信号（绝对阈值熔断）
        signal2 = sg.calculate_final_signal(
            stock_code='000001',
            ai_narrative_score=90,
            capital_flow_data=-60000000,
            trend_status='UP',
            circulating_market_cap=100000000000
        )
        signal2['ai_score'] = 90
        signal2['capital_flow'] = -60000000
        signal2['trend_status'] = 'UP'
        signal2['market_cap'] = 100000000000
        
        shm.save_signal('000001', signal2, test_date)
        logger.info(f"✅ 保存SELL信号: 000001")
        
        # 测试用例3：WAIT信号（趋势熔断）
        signal3 = sg.calculate_final_signal(
            stock_code='000002',
            ai_narrative_score=85,
            capital_flow_data=30000000,
            trend_status='DOWN',
            circulating_market_cap=50000000000
        )
        signal3['ai_score'] = 85
        signal3['capital_flow'] = 30000000
        signal3['trend_status'] = 'DOWN'
        signal3['market_cap'] = 50000000000
        
        shm.save_signal('000002', signal3, test_date)
        logger.info(f"✅ 保存WAIT信号: 000002")
        
        # 测试用例4：背离识别（相对阈值熔断）
        signal4 = sg.calculate_final_signal(
            stock_code='002028',
            ai_narrative_score=90,
            capital_flow_data=-30000000,
            trend_status='UP',
            circulating_market_cap=1500000000
        )
        signal4['ai_score'] = 90
        signal4['capital_flow'] = -30000000
        signal4['trend_status'] = 'UP'
        signal4['market_cap'] = 1500000000
        
        shm.save_signal('002028', signal4, test_date)
        logger.info(f"✅ 保存背离信号: 002028")
        
        # 查询信号
        signals = shm.get_signals_by_date(test_date)
        logger.info(f"✅ 查询到 {len(signals)} 个信号")
        
        # 查询BUY信号
        buy_signals = shm.get_buy_signals_by_date(test_date)
        logger.info(f"✅ 查询到 {len(buy_signals)} 个BUY信号")
        
        # 查询被熔断的信号
        vetoed_signals = shm.get_fact_vetoed_signals(test_date)
        logger.info(f"✅ 查询到 {len(vetoed_signals)} 个被熔断的信号")
        
        # 获取统计信息
        stats = shm.get_statistics(test_date)
        logger.info(f"✅ 统计信息: {stats}")
        
        logger.info('='*60)
        logger.info('✅ 信号历史存储测试通过')
        logger.info('='*60)
        
        return True
        
    except Exception as e:
        logger.error(f'❌ 信号历史存储测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_auto_reviewer():
    """
    测试AutoReviewer功能
    """
    logger.info('='*60)
    logger.info('测试V14 AutoReviewer')
    logger.info('='*60)
    
    try:
        reviewer = AutoReviewer()
        
        # 测试日期
        test_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 测试收集打脸案例
        slap_cases = reviewer.collect_slap_cases(test_date)
        logger.info(f"✅ 收集到 {len(slap_cases)} 个打脸案例")
        
        # 测试收集踏空案例
        missed_cases = reviewer.collect_missed_opportunities(test_date)
        logger.info(f"✅ 收集到 {len(missed_cases)} 个踏空案例")
        
        # 测试收集救命案例
        lifesaver_cases = reviewer.collect_lifesaver_cases(test_date)
        logger.info(f"✅ 收集到 {len(lifesaver_cases)} 个救命案例")
        
        # 测试生成每日报告
        report = reviewer.generate_daily_report(test_date)
        logger.info(f"✅ 生成每日报告，长度: {len(report)} 字符")
        
        logger.info('='*60)
        logger.info('✅ AutoReviewer测试通过')
        logger.info('='*60)
        
        return True
        
    except Exception as e:
        logger.error(f'❌ AutoReviewer测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """
    测试完整集成流程
    """
    logger.info('='*60)
    logger.info('测试V14完整集成流程')
    logger.info('='*60)
    
    try:
        # 1. 初始化
        shm = get_signal_history_manager()
        sg = get_signal_generator_v13()
        dm = DataManager()
        
        # 2. 模拟昨天的信号生成和存储
        test_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 生成一些测试信号
        test_stocks = [
            ('600519', 80, 50000000, 'UP', 200000000000),  # BUY
            ('000001', 90, -60000000, 'UP', 100000000000),  # SELL（绝对熔断）
            ('000002', 85, 30000000, 'DOWN', 50000000000),  # WAIT（趋势熔断）
            ('002028', 90, -30000000, 'UP', 1500000000),    # SELL（相对熔断）
        ]
        
        for stock_code, ai_score, capital_flow, trend, market_cap in test_stocks:
            result = sg.calculate_final_signal(
                stock_code=stock_code,
                ai_narrative_score=ai_score,
                capital_flow_data=capital_flow,
                trend_status=trend,
                circulating_market_cap=market_cap
            )
            
            result['ai_score'] = ai_score
            result['capital_flow'] = capital_flow
            result['trend_status'] = trend
            result['market_cap'] = market_cap
            
            shm.save_signal(stock_code, result, test_date)
            logger.info(f"保存信号: {stock_code} -> {result['signal']} (分数: {result['final_score']:.1f})")
        
        # 3. 运行AutoReviewer
        reviewer = AutoReviewer()
        report = reviewer.generate_daily_report(test_date)
        
        # 4. 输出报告摘要
        logger.info('='*60)
        logger.info('每日报告摘要')
        logger.info('='*60)
        
        # 提取关键信息
        lines = report.split('\n')
        for line in lines:
            if '打脸案例' in line or '踏空案例' in line or '救命案例' in line or '累计避免损失' in line:
                logger.info(line)
        
        logger.info('='*60)
        logger.info('✅ 完整集成流程测试通过')
        logger.info('='*60)
        
        return True
        
    except Exception as e:
        logger.error(f'❌ 完整集成流程测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    主测试函数
    """
    logger.info('='*60)
    logger.info('V14 AutoReviewer 测试开始')
    logger.info('='*60)
    
    results = []
    
    try:
        # 测试1：信号历史存储
        results.append(('信号历史存储', test_signal_history_storage()))
        
        # 测试2：AutoReviewer
        results.append(('AutoReviewer', test_auto_reviewer()))
        
        # 测试3：完整集成
        results.append(('完整集成', test_integration()))
        
        logger.info('='*60)
        logger.info('V14 AutoReviewer 测试总结')
        logger.info('='*60)
        
        for test_name, result in results:
            status = '✅ 通过' if result else '❌ 失败'
            logger.info(f'{test_name}: {status}')
        
        # 如果所有测试都通过
        if all(result for _, result in results):
            logger.info('='*60)
            logger.info('✅ 所有V14测试通过！')
            logger.info('='*60)
            return 0
        else:
            logger.warning('='*60)
            logger.warning('⚠️ 部分V14测试未通过')
            logger.warning('='*60)
            return 1
        
    except Exception as e:
        logger.error(f'❌ V14测试异常: {e}')
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())