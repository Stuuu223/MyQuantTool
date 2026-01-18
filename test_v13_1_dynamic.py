import sys
import logging
from logic.signal_generator import SignalGenerator
from logic.logger import get_logger

logger = get_logger(__name__)


def test_dynamic_threshold_absolute():
    '''
    测试V13.1动态阈值：绝对值熔断
    '''
    sg = SignalGenerator()
    
    logger.info('='*50)
    logger.info('测试V13.1动态阈值：绝对值熔断')
    logger.info('='*50)
    
    # 测试用例1：绝对值熔断（流出6000万）
    result = sg.calculate_final_signal(
        stock_code='600519',
        ai_narrative_score=90,
        capital_flow_data=-60000000,  # -6000万
        trend_status='UP',
        circulating_market_cap=200000000000  # 2000亿市值
    )
    
    logger.info(f'AI分数: 90')
    logger.info(f'资金流出: -6000万')
    logger.info(f'流通市值: 2000亿')
    logger.info(f'结果: {result}')
    
    assert result['signal'] == 'SELL', f"Expected SELL, got {result['signal']}"
    assert result['fact_veto'] == True, f"Expected fact_veto=True, got {result['fact_veto']}"
    assert result['risk_level'] == 'HIGH', f"Expected risk_level=HIGH, got {result['risk_level']}"
    logger.info('✅ 测试用例1通过：绝对值熔断触发')
    
    # 测试用例2：未触发绝对值熔断（流出4000万）
    result = sg.calculate_final_signal(
        stock_code='600519',
        ai_narrative_score=90,
        capital_flow_data=-40000000,  # -4000万
        trend_status='UP',
        circulating_market_cap=200000000000  # 2000亿市值
    )
    
    logger.info(f'AI分数: 90')
    logger.info(f'资金流出: -4000万')
    logger.info(f'流通市值: 2000亿')
    logger.info(f'结果: {result}')
    
    assert result['signal'] == 'WAIT', f"Expected WAIT, got {result['signal']}"
    assert result['fact_veto'] == False, f"Expected fact_veto=False, got {result['fact_veto']}"
    logger.info('✅ 测试用例2通过：未触发绝对值熔断')
    
    logger.info('='*50)
    logger.info('✅ 绝对值熔断测试全部通过')
    logger.info('='*50)


def test_dynamic_threshold_relative():
    '''
    测试V13.1动态阈值：相对值熔断
    '''
    sg = SignalGenerator()
    
    logger.info('='*50)
    logger.info('测试V13.1动态阈值：相对值熔断')
    logger.info('='*50)
    
    # 测试用例3：相对值熔断（小盘股流出3000万，占比2%）
    result = sg.calculate_final_signal(
        stock_code='002028',
        ai_narrative_score=90,
        capital_flow_data=-30000000,  # -3000万（未到5000万绝对阈值）
        trend_status='UP',
        circulating_market_cap=1500000000  # 15亿市值（流出占比2%）
    )
    
    logger.info(f'AI分数: 90')
    logger.info(f'资金流出: -3000万')
    logger.info(f'流通市值: 15亿')
    logger.info(f'流出占比: 2%')
    logger.info(f'结果: {result}')
    
    assert result['signal'] == 'SELL', f"Expected SELL, got {result['signal']}"
    assert result['fact_veto'] == True, f"Expected fact_veto=True, got {result['fact_veto']}"
    assert 'Relative outflow' in result['reason'], f"Expected 'Relative outflow' in reason, got {result['reason']}"
    logger.info('✅ 测试用例3通过：相对值熔断触发（小盘股失血）')
    
    # 测试用例4：未触发相对值熔断（小盘股流出1000万，占比0.67%）
    result = sg.calculate_final_signal(
        stock_code='002028',
        ai_narrative_score=90,
        capital_flow_data=-10000000,  # -1000万
        trend_status='UP',
        circulating_market_cap=1500000000  # 15亿市值（流出占比0.67%）
    )
    
    logger.info(f'AI分数: 90')
    logger.info(f'资金流出: -1000万')
    logger.info(f'流通市值: 15亿')
    logger.info(f'流出占比: 0.67%')
    logger.info(f'结果: {result}')
    
    assert result['signal'] == 'WAIT', f"Expected WAIT, got {result['signal']}"
    assert result['fact_veto'] == False, f"Expected fact_veto=False, got {result['fact_veto']}"
    logger.info('✅ 测试用例4通过：未触发相对值熔断')
    
    logger.info('='*50)
    logger.info('✅ 相对值熔断测试全部通过')
    logger.info('='*50)


def test_divergence_detection():
    '''
    测试V13.1背离识别：量价背离
    '''
    sg = SignalGenerator()
    
    logger.info('='*50)
    logger.info('测试V13.1背离识别：量价背离')
    logger.info('='*50)
    
    # 测试用例5：量价背离（股价UP，资金流出2000万）
    result = sg.calculate_final_signal(
        stock_code='600519',
        ai_narrative_score=90,
        capital_flow_data=-20000000,  # -2000万（未触发熔断）
        trend_status='UP',
        circulating_market_cap=200000000000  # 2000亿市值
    )
    
    logger.info(f'AI分数: 90')
    logger.info(f'资金流出: -2000万')
    logger.info(f'趋势: UP')
    logger.info(f'结果: {result}')
    
    # V13.1: 背离时AI分数打折到0.4，所以最终分数 = 90 * 0.4 = 36
    expected_score = 90 * 0.4
    assert abs(result['final_score'] - expected_score) < 0.1, f"Expected score={expected_score}, got {result['final_score']}"
    assert result['signal'] == 'WAIT', f"Expected WAIT, got {result['signal']}"
    assert result['risk_level'] == 'HIGH', f"Expected risk_level=HIGH, got {result['risk_level']}"
    assert 'Divergence' in result['reason'], f"Expected 'Divergence' in reason, got {result['reason']}"
    logger.info('✅ 测试用例5通过：量价背离识别成功（AI分数打折到0.4）')
    
    # 测试用例6：完美共振（股价UP，资金流入5000万）
    result = sg.calculate_final_signal(
        stock_code='600519',
        ai_narrative_score=80,
        capital_flow_data=50000000,  # +5000万
        trend_status='UP',
        circulating_market_cap=200000000000  # 2000亿市值
    )
    
    logger.info(f'AI分数: 80')
    logger.info(f'资金流入: +5000万')
    logger.info(f'趋势: UP')
    logger.info(f'结果: {result}')
    
    # V13.1: 共振时AI分数加权到1.2，所以最终分数 = 80 * 1.2 = 96
    expected_score = 80 * 1.2
    assert abs(result['final_score'] - expected_score) < 0.1, f"Expected score={expected_score}, got {result['final_score']}"
    assert result['signal'] == 'BUY', f"Expected BUY, got {result['signal']}"
    assert result['risk_level'] == 'LOW', f"Expected risk_level=LOW, got {result['risk_level']}"
    assert 'Resonance Attack' in result['reason'], f"Expected 'Resonance Attack' in reason, got {result['reason']}"
    logger.info('✅ 测试用例6通过：完美共振识别成功（AI分数加权到1.2）')
    
    logger.info('='*50)
    logger.info('✅ 背离识别测试全部通过')
    logger.info('='*50)


def test_integration_with_data_manager():
    '''
    测试V13.1与DataManager的集成
    '''
    from logic.data_manager import DataManager
    
    logger.info('='*50)
    logger.info('测试V13.1与DataManager的集成')
    logger.info('='*50)
    
    try:
        sg = SignalGenerator()
        dm = DataManager()
        
        # 测试用例7：获取真实数据
        stock_code = '600519'
        capital_flow, market_cap = sg.get_capital_flow(stock_code, dm)
        
        logger.info(f'股票代码: {stock_code}')
        logger.info(f'资金流向: {capital_flow/10000:.2f}万')
        logger.info(f'流通市值: {market_cap/100000000:.2f}亿')
        
        # 获取趋势
        df = dm.get_history_data(symbol=stock_code)
        if df is not None and len(df) > 0:
            trend = sg.get_trend_status(df)
            logger.info(f'趋势状态: {trend}')
            
            # 计算最终信号
            result = sg.calculate_final_signal(
                stock_code=stock_code,
                ai_narrative_score=75,
                capital_flow_data=capital_flow,
                trend_status=trend,
                circulating_market_cap=market_cap
            )
            
            logger.info(f'最终信号: {result}')
            logger.info('✅ 测试用例7通过：真实数据集成成功')
        else:
            logger.warning('无法获取历史数据，跳过趋势测试')
        
        logger.info('='*50)
        logger.info('✅ DataManager集成测试通过')
        logger.info('='*50)
        
    except Exception as e:
        logger.error(f'集成测试失败: {e}')
        raise


def main():
    '''
    主测试函数
    '''
    logger.info('='*60)
    logger.info('V13.1 动态阈值 + 背离识别测试开始')
    logger.info('='*60)
    
    try:
        test_dynamic_threshold_absolute()
        test_dynamic_threshold_relative()
        test_divergence_detection()
        test_integration_with_data_manager()
        
        logger.info('='*60)
        logger.info('✅ 所有V13.1测试通过！')
        logger.info('='*60)
        
    except AssertionError as e:
        logger.error(f'❌ 测试失败: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'❌ 测试异常: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()