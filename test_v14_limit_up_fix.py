"""
测试V14涨停板数据获取修复
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


def test_limit_up_data_fetch():
    """
    测试涨停板数据获取功能
    """
    logger.info('='*60)
    logger.info('测试V14涨停板数据获取修复')
    logger.info('='*60)
    
    try:
        reviewer = AutoReviewer()
        
        # 测试日期（使用最近一个交易日）
        test_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 获取涨停板数据
        limit_up_stocks = reviewer._get_limit_up_stocks(test_date)
        
        logger.info(f"✅ 成功获取 {len(limit_up_stocks)} 只涨停板股票")
        
        if limit_up_stocks:
            logger.info(f"示例股票代码: {limit_up_stocks[:5]}")
        
        return True
        
    except Exception as e:
        logger.error(f'❌ 涨停板数据获取测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_missed_opportunities_with_real_data():
    """
    测试踏空案例收集（使用真实涨停板数据）
    """
    logger.info('='*60)
    logger.info('测试V14踏空案例收集（真实数据）')
    logger.info('='*60)
    
    try:
        reviewer = AutoReviewer()
        shm = get_signal_history_manager()
        sg = get_signal_generator_v13()
        
        # 测试日期
        test_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 1. 获取涨停板数据
        limit_up_stocks = reviewer._get_limit_up_stocks(test_date)
        logger.info(f"涨停板股票数量: {len(limit_up_stocks)}")
        
        if not limit_up_stocks:
            logger.warning("无涨停板数据，跳过踏空案例测试")
            return True
        
        # 2. 对每只涨停股票检查系统评分
        missed_cases = []
        
        # 限制测试数量，避免耗时过长
        test_stocks = limit_up_stocks[:10]  # 只测试前10只
        
        for stock_code in test_stocks:
            try:
                # 获取历史数据
                df = reviewer.dm.get_history_data(symbol=stock_code)
                
                if df is None or len(df) < 2:
                    continue
                
                # 获取资金流向
                capital_flow, market_cap = sg.get_capital_flow(stock_code, reviewer.dm)
                
                # 获取趋势
                trend = sg.get_trend_status(df.iloc[:-1])
                
                # 计算系统评分（使用默认AI分数75）
                result = sg.calculate_final_signal(
                    stock_code=stock_code,
                    ai_narrative_score=75,
                    capital_flow_data=capital_flow,
                    trend_status=trend,
                    circulating_market_cap=market_cap
                )
                
                # 踏空条件：系统评分<60但今日涨停
                if result['final_score'] < 60:
                    case = {
                        'stock_code': stock_code,
                        'date': test_date,
                        'system_score': result['final_score'],
                        'today_status': 'LIMIT_UP',
                        'signal': result['signal'],
                        'reason': result['reason'],
                        'fact_veto': result.get('fact_veto', False),
                        'capital_flow': capital_flow,
                        'trend': trend
                    }
                    missed_cases.append(case)
                    logger.warning(f"踏空案例: {stock_code} 评分{result['final_score']:.1f} 今日涨停")
                    
            except Exception as e:
                logger.error(f"处理股票 {stock_code} 失败: {e}")
                continue
        
        logger.info(f"✅ 发现 {len(missed_cases)} 个踏空案例")
        
        # 保存案例
        if missed_cases:
            reviewer._save_cases(missed_cases, reviewer.missed_dir, f"missed_{test_date}.csv")
            logger.info(f"✅ 踏空案例已保存")
        
        return True
        
    except Exception as e:
        logger.error(f'❌ 踏空案例收集测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_performance():
    """
    测试涨停板数据获取性能
    """
    logger.info('='*60)
    logger.info('测试V14涨停板数据获取性能')
    logger.info('='*60)
    
    try:
        import time
        reviewer = AutoReviewer()
        
        test_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 测试获取涨停板数据的耗时
        start_time = time.time()
        limit_up_stocks = reviewer._get_limit_up_stocks(test_date)
        fetch_time = time.time() - start_time
        
        logger.info(f"获取涨停板数据耗时: {fetch_time*1000:.2f}ms")
        logger.info(f"涨停板股票数量: {len(limit_up_stocks)}")
        
        # 性能要求：获取时间 < 5秒
        if fetch_time < 5:
            logger.info('✅ 性能测试通过：获取时间 < 5秒')
            return True
        else:
            logger.warning(f'⚠️ 性能测试警告：获取时间 {fetch_time*1000:.2f}ms > 5秒')
            return False
        
    except Exception as e:
        logger.error(f'❌ 性能测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    主测试函数
    """
    logger.info('='*60)
    logger.info('V14涨停板数据获取修复测试开始')
    logger.info('='*60)
    
    results = []
    
    try:
        # 测试1：涨停板数据获取
        results.append(('涨停板数据获取', test_limit_up_data_fetch()))
        
        # 测试2：踏空案例收集（真实数据）
        results.append(('踏空案例收集', test_missed_opportunities_with_real_data()))
        
        # 测试3：性能测试
        results.append(('性能测试', test_performance()))
        
        logger.info('='*60)
        logger.info('V14涨停板数据获取修复测试总结')
        logger.info('='*60)
        
        for test_name, result in results:
            status = '✅ 通过' if result else '❌ 失败'
            logger.info(f'{test_name}: {status}')
        
        # 如果所有测试都通过
        if all(result for _, result in results):
            logger.info('='*60)
            logger.info('✅ 所有V14涨停板数据获取修复测试通过！')
            logger.info('='*60)
            return 0
        else:
            logger.warning('='*60)
            logger.warning('⚠️ 部分V14涨停板数据获取修复测试未通过')
            logger.warning('='*60)
            return 1
        
    except Exception as e:
        logger.error(f'❌ V14涨停板数据获取修复测试异常: {e}')
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())