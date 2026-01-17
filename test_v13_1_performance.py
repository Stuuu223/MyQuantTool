import sys
import time
import logging
from logic.signal_generator import SignalGenerator, get_signal_generator_v13
from logic.data_manager import DataManager
from logic.logger import get_logger

logger = get_logger(__name__)


def test_performance_single_stock():
    '''
    测试V13.1单只股票的性能
    '''
    sg = get_signal_generator_v13()
    dm = DataManager()
    
    stock_code = '600519'
    
    logger.info('='*60)
    logger.info(f'V13.1性能测试：单只股票 {stock_code}')
    logger.info('='*60)
    
    # 获取数据
    start_time = time.time()
    
    capital_flow, market_cap = sg.get_capital_flow(stock_code, dm)
    df = dm.get_history_data(symbol=stock_code)
    
    data_fetch_time = time.time() - start_time
    
    # 计算信号
    start_time = time.time()
    
    trend = sg.get_trend_status(df)
    result = sg.calculate_final_signal(
        stock_code=stock_code,
        ai_narrative_score=75,
        capital_flow_data=capital_flow,
        trend_status=trend,
        circulating_market_cap=market_cap
    )
    
    signal_calc_time = time.time() - start_time
    total_time = data_fetch_time + signal_calc_time
    
    logger.info(f'数据获取耗时: {data_fetch_time*1000:.2f}ms')
    logger.info(f'信号计算耗时: {signal_calc_time*1000:.2f}ms')
    logger.info(f'总耗时: {total_time*1000:.2f}ms')
    logger.info(f'信号结果: {result}')
    
    # 性能要求：总耗时 < 100ms
    if total_time < 0.1:
        logger.info('✅ 性能测试通过：总耗时 < 100ms')
        return True
    else:
        logger.warning(f'⚠️ 性能测试警告：总耗时 {total_time*1000:.2f}ms > 100ms')
        return False


def test_performance_batch():
    '''
    测试V13.1批量股票的性能
    '''
    sg = get_signal_generator_v13()
    dm = DataManager()
    
    stock_list = ['600519', '000001', '000002', '000858', '600036']
    
    logger.info('='*60)
    logger.info(f'V13.1性能测试：批量股票 {len(stock_list)} 只')
    logger.info('='*60)
    
    start_time = time.time()
    
    results = []
    for stock_code in stock_list:
        capital_flow, market_cap = sg.get_capital_flow(stock_code, dm)
        df = dm.get_history_data(symbol=stock_code)
        
        if df is not None and len(df) > 0:
            trend = sg.get_trend_status(df)
            result = sg.calculate_final_signal(
                stock_code=stock_code,
                ai_narrative_score=75,
                capital_flow_data=capital_flow,
                trend_status=trend,
                circulating_market_cap=market_cap
            )
            results.append(result)
    
    total_time = time.time() - start_time
    avg_time = total_time / len(stock_list)
    
    logger.info(f'总耗时: {total_time*1000:.2f}ms')
    logger.info(f'平均每只股票: {avg_time*1000:.2f}ms')
    logger.info(f'成功处理: {len(results)}/{len(stock_list)} 只')
    
    # 性能要求：平均耗时 < 100ms
    if avg_time < 0.1:
        logger.info('✅ 性能测试通过：平均耗时 < 100ms')
        return True
    else:
        logger.warning(f'⚠️ 性能测试警告：平均耗时 {avg_time*1000:.2f}ms > 100ms')
        return False


def test_performance_calculation_only():
    '''
    测试V13.1纯计算性能（不含数据获取）
    '''
    sg = get_signal_generator_v13()
    
    logger.info('='*60)
    logger.info('V13.1性能测试：纯计算性能')
    logger.info('='*60)
    
    # 模拟100次计算
    iterations = 100
    
    start_time = time.time()
    
    for i in range(iterations):
        result = sg.calculate_final_signal(
            stock_code='600519',
            ai_narrative_score=75,
            capital_flow_data=50000000,
            trend_status='UP',
            circulating_market_cap=200000000000
        )
    
    total_time = time.time() - start_time
    avg_time = total_time / iterations
    
    logger.info(f'总耗时: {total_time*1000:.2f}ms')
    logger.info(f'计算次数: {iterations}')
    logger.info(f'平均每次: {avg_time*1000:.2f}ms')
    logger.info(f'每秒可处理: {1/avg_time:.0f} 次')
    
    # 性能要求：单次计算 < 1ms
    if avg_time < 0.001:
        logger.info('✅ 性能测试通过：单次计算 < 1ms')
        return True
    else:
        logger.warning(f'⚠️ 性能测试警告：单次计算 {avg_time*1000:.2f}ms > 1ms')
        return False


def test_memory_usage():
    '''
    测试V13.1内存使用
    '''
    try:
        import psutil
        import os
    except ImportError:
        logger.warning('⚠️ psutil模块未安装，跳过内存测试')
        return True  # 跳过测试不算失败
    
    process = psutil.Process(os.getpid())
    
    logger.info('='*60)
    logger.info('V13.1性能测试：内存使用')
    logger.info('='*60)
    
    # 初始内存
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # 创建1000个实例
    instances = []
    for i in range(1000):
        sg = SignalGenerator()
        instances.append(sg)
    
    # 创建后内存
    after_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = after_memory - initial_memory
    
    logger.info(f'初始内存: {initial_memory:.2f}MB')
    logger.info(f'创建1000个实例后: {after_memory:.2f}MB')
    logger.info(f'内存增加: {memory_increase:.2f}MB')
    logger.info(f'平均每个实例: {memory_increase/1000:.4f}MB')
    
    # 清理
    del instances
    
    # 内存要求：单个实例 < 1KB
    avg_memory_per_instance = memory_increase / 1000
    if avg_memory_per_instance < 0.001:  # 1KB = 0.001MB
        logger.info('✅ 内存测试通过：单个实例 < 1KB')
        return True
    else:
        logger.warning(f'⚠️ 内存测试警告：单个实例 {avg_memory_per_instance*1024:.2f}KB > 1KB')
        return False


def main():
    '''
    主测试函数
    '''
    logger.info('='*60)
    logger.info('V13.1 性能测试开始')
    logger.info('='*60)
    
    results = []
    
    try:
        # 测试1：单只股票性能
        results.append(('单只股票性能', test_performance_single_stock()))
        
        # 测试2：批量股票性能
        results.append(('批量股票性能', test_performance_batch()))
        
        # 测试3：纯计算性能
        results.append(('纯计算性能', test_performance_calculation_only()))
        
        # 测试4：内存使用
        results.append(('内存使用', test_memory_usage()))
        
        logger.info('='*60)
        logger.info('V13.1 性能测试总结')
        logger.info('='*60)
        
        for test_name, result in results:
            status = '✅ 通过' if result else '⚠️ 警告'
            logger.info(f'{test_name}: {status}')
        
        # 如果所有测试都通过
        if all(result for _, result in results):
            logger.info('='*60)
            logger.info('✅ 所有性能测试通过！')
            logger.info('='*60)
            return 0
        else:
            logger.warning('='*60)
            logger.warning('⚠️ 部分性能测试未通过，建议优化')
            logger.warning('='*60)
            return 1
        
    except Exception as e:
        logger.error(f'❌ 性能测试异常: {e}')
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())