"""
测试V14.2涨停豁免权功能
"""

import sys
import logging
from logic.signal_generator import SignalGenerator
from logic.logger import get_logger

logger = get_logger(__name__)


def test_limit_up_immunity_10cm():
    """
    测试10cm涨停豁免权
    """
    logger.info('='*60)
    logger.info('测试V14.2涨停豁免权：10cm涨停')
    logger.info('='*60)
    
    sg = SignalGenerator()
    
    # 测试用例1：10cm涨停 + 资金流出（应该被豁免）
    result = sg.calculate_final_signal(
        stock_code='600058',
        ai_narrative_score=75,
        capital_flow_data=-20000000,  # -2000万（未触及5000万熔断线）
        trend_status='UP',
        circulating_market_cap=100000000000,
        current_pct_change=9.8  # 9.8%涨幅，接近涨停
    )
    
    logger.info(f'测试用例1: 10cm涨停 + 资金流出')
    logger.info(f'AI分数: 75')
    logger.info(f'资金流出: -2000万')
    logger.info(f'涨幅: 9.8%')
    logger.info(f'结果: {result}')
    
    assert result['limit_up_immunity'] == True, f"Expected limit_up_immunity=True, got {result['limit_up_immunity']}"
    assert result['final_score'] == 75.0, f"Expected final_score=75.0, got {result['final_score']}"
    assert result['signal'] == 'BUY', f"Expected signal=BUY, got {result['signal']}"
    logger.info('✅ 测试用例1通过：10cm涨停豁免权生效')
    
    # 测试用例2：10cm涨停 + 趋势向下（应该被豁免）
    result = sg.calculate_final_signal(
        stock_code='603056',
        ai_narrative_score=75,
        capital_flow_data=30000000,
        trend_status='DOWN',
        circulating_market_cap=50000000000,
        current_pct_change=10.0  # 10%涨幅，涨停
    )
    
    logger.info(f'测试用例2: 10cm涨停 + 趋势向下')
    logger.info(f'AI分数: 75')
    logger.info(f'资金流入: +3000万')
    logger.info(f'趋势: DOWN')
    logger.info(f'涨幅: 10.0%')
    logger.info(f'结果: {result}')
    
    assert result['limit_up_immunity'] == True, f"Expected limit_up_immunity=True, got {result['limit_up_immunity']}"
    assert result['final_score'] == 75.0, f"Expected final_score=75.0, got {result['final_score']}"
    assert result['signal'] == 'BUY', f"Expected signal=BUY, got {result['signal']}"
    logger.info('✅ 测试用例2通过：10cm涨停豁免趋势熔断')
    
    logger.info('='*60)
    logger.info('✅ 10cm涨停豁免权测试全部通过')
    logger.info('='*60)
    
    return True


def test_limit_up_immunity_20cm():
    """
    测试20cm涨停豁免权
    """
    logger.info('='*60)
    logger.info('测试V14.2涨停豁免权：20cm涨停')
    logger.info('='*60)
    
    sg = SignalGenerator()
    
    # 测试用例3：20cm涨停 + 资金流出（应该被豁免）
    result = sg.calculate_final_signal(
        stock_code='300952',
        ai_narrative_score=75,
        capital_flow_data=-30000000,  # -3000万
        trend_status='UP',
        circulating_market_cap=50000000000,
        current_pct_change=20.0  # 20%涨幅，涨停
    )
    
    logger.info(f'测试用例3: 20cm涨停 + 资金流出')
    logger.info(f'AI分数: 75')
    logger.info(f'资金流出: -3000万')
    logger.info(f'涨幅: 20.0%')
    logger.info(f'结果: {result}')
    
    assert result['limit_up_immunity'] == True, f"Expected limit_up_immunity=True, got {result['limit_up_immunity']}"
    assert result['final_score'] == 82.5, f"Expected final_score=82.5, got {result['final_score']}"
    assert result['signal'] == 'BUY', f"Expected signal=BUY, got {result['signal']}"
    logger.info('✅ 测试用例3通过：20cm涨停豁免权生效（权重1.1倍）')
    
    logger.info('='*60)
    logger.info('✅ 20cm涨停豁免权测试全部通过')
    logger.info('='*60)
    
    return True


def test_limit_up_immunity_threshold():
    """
    测试涨停豁免权阈值
    """
    logger.info('='*60)
    logger.info('测试V14.2涨停豁免权：阈值测试')
    logger.info('='*60)
    
    sg = SignalGenerator()
    
    # 测试用例4：涨幅9.0%（未达到9.5%阈值，不应豁免）
    result = sg.calculate_final_signal(
        stock_code='600000',
        ai_narrative_score=75,
        capital_flow_data=-20000000,
        trend_status='UP',
        circulating_market_cap=100000000000,
        current_pct_change=9.0  # 9.0%涨幅，未达到阈值
    )
    
    logger.info(f'测试用例4: 涨幅9.0%（未达到阈值）')
    logger.info(f'AI分数: 75')
    logger.info(f'资金流出: -2000万')
    logger.info(f'涨幅: 9.0%')
    logger.info(f'结果: {result}')
    
    assert result['limit_up_immunity'] == False, f"Expected limit_up_immunity=False, got {result['limit_up_immunity']}"
    assert result['final_score'] == 30.0, f"Expected final_score=30.0, got {result['final_score']}"
    assert result['signal'] == 'WAIT', f"Expected signal=WAIT, got {result['signal']}"
    logger.info('✅ 测试用例4通过：9.0%涨幅未触发豁免')
    
    # 测试用例5：涨幅5.0% + 资金流出5000万（应该触发熔断，不豁免）
    result = sg.calculate_final_signal(
        stock_code='600001',
        ai_narrative_score=90,
        capital_flow_data=-60000000,  # -6000万（超过5000万）
        trend_status='UP',
        circulating_market_cap=100000000000,
        current_pct_change=5.0  # 5.0%涨幅，未达到阈值
    )
    
    logger.info(f'测试用例5: 涨幅5.0% + 资金流出6000万')
    logger.info(f'AI分数: 90')
    logger.info(f'资金流出: -6000万')
    logger.info(f'涨幅: 5.0%')
    logger.info(f'结果: {result}')
    
    assert result['limit_up_immunity'] == False, f"Expected limit_up_immunity=False, got {result['limit_up_immunity']}"
    assert result['signal'] == 'SELL', f"Expected signal=SELL, got {result['signal']}"
    assert result['fact_veto'] == True, f"Expected fact_veto=True, got {result['fact_veto']}"
    logger.info('✅ 测试用例5通过：5.0%涨幅未豁免，触发熔断')
    
    logger.info('='*60)
    logger.info('✅ 涨停豁免权阈值测试全部通过')
    logger.info('='*60)
    
    return True


def test_limit_up_immunity_buy_threshold():
    """
    测试涨停豁免权下的买入阈值调整
    """
    logger.info('='*60)
    logger.info('测试V14.2涨停豁免权：买入阈值调整')
    logger.info('='*60)
    
    sg = SignalGenerator()
    
    # 测试用例6：涨停 + AI分数70（应该买入，阈值降至75）
    result = sg.calculate_final_signal(
        stock_code='600058',
        ai_narrative_score=70,
        capital_flow_data=-20000000,
        trend_status='UP',
        circulating_market_cap=100000000000,
        current_pct_change=9.8  # 涨停
    )
    
    logger.info(f'测试用例6: 涨停 + AI分数70')
    logger.info(f'AI分数: 70')
    logger.info(f'涨幅: 9.8%')
    logger.info(f'结果: {result}')
    
    assert result['limit_up_immunity'] == True, f"Expected limit_up_immunity=True, got {result['limit_up_immunity']}"
    assert result['final_score'] == 70.0, f"Expected final_score=70.0, got {result['final_score']}"
    assert result['signal'] == 'WAIT', f"Expected signal=WAIT, got {result['signal']}"
    logger.info('✅ 测试用例6通过：涨停下70分未达到75分阈值')
    
    # 测试用例7：涨停 + AI分数80（应该买入，阈值降至75）
    result = sg.calculate_final_signal(
        stock_code='600058',
        ai_narrative_score=80,
        capital_flow_data=-20000000,
        trend_status='UP',
        circulating_market_cap=100000000000,
        current_pct_change=9.8  # 涨停
    )
    
    logger.info(f'测试用例7: 涨停 + AI分数80')
    logger.info(f'AI分数: 80')
    logger.info(f'涨幅: 9.8%')
    logger.info(f'结果: {result}')
    
    assert result['limit_up_immunity'] == True, f"Expected limit_up_immunity=True, got {result['limit_up_immunity']}"
    assert result['final_score'] == 80.0, f"Expected final_score=80.0, got {result['final_score']}"
    assert result['signal'] == 'BUY', f"Expected signal=BUY, got {result['signal']}"
    logger.info('✅ 测试用例7通过：涨停下80分达到75分阈值')
    
    logger.info('='*60)
    logger.info('✅ 涨停豁免权买入阈值调整测试全部通过')
    logger.info('='*60)
    
    return True


def test_real_case_600058():
    """
    测试真实案例：600058（踏空案例）
    """
    logger.info('='*60)
    logger.info('测试V14.2真实案例：600058（踏空案例）')
    logger.info('='*60)
    
    sg = SignalGenerator()
    
    # V13.1结果：评分30.0，WAIT
    result_v13_1 = sg.calculate_final_signal(
        stock_code='600058',
        ai_narrative_score=75,
        capital_flow_data=0,  # 无DDE数据
        trend_status='UP',
        circulating_market_cap=100000000000,
        current_pct_change=None  # V13.1无涨幅参数
    )
    
    logger.info(f'V13.1结果: {result_v13_1}')
    
    # V14.2结果：评分75.0，BUY
    result_v14_2 = sg.calculate_final_signal(
        stock_code='600058',
        ai_narrative_score=75,
        capital_flow_data=0,  # 无DDE数据
        trend_status='UP',
        circulating_market_cap=100000000000,
        current_pct_change=10.02  # 10.02%涨幅，涨停
    )
    
    logger.info(f'V14.2结果: {result_v14_2}')
    
    assert result_v14_2['limit_up_immunity'] == True, f"Expected limit_up_immunity=True, got {result_v14_2['limit_up_immunity']}"
    assert result_v14_2['final_score'] == 75.0, f"Expected final_score=75.0, got {result_v14_2['final_score']}"
    assert result_v14_2['signal'] == 'BUY', f"Expected signal=BUY, got {result_v14_2['signal']}"
    
    logger.info(f'✅ 真实案例测试通过：600058从V13.1的{result_v13_1["signal"]}升级到V14.2的{result_v14_2["signal"]}')
    
    logger.info('='*60)
    logger.info('✅ 真实案例测试全部通过')
    logger.info('='*60)
    
    return True


def main():
    """
    主测试函数
    """
    logger.info('='*60)
    logger.info('V14.2涨停豁免权测试开始')
    logger.info('='*60)
    
    results = []
    
    try:
        # 测试1：10cm涨停豁免权
        results.append(('10cm涨停豁免权', test_limit_up_immunity_10cm()))
        
        # 测试2：20cm涨停豁免权
        results.append(('20cm涨停豁免权', test_limit_up_immunity_20cm()))
        
        # 测试3：涨停豁免权阈值
        results.append(('涨停豁免权阈值', test_limit_up_immunity_threshold()))
        
        # 测试4：涨停豁免权买入阈值调整
        results.append(('涨停豁免权买入阈值调整', test_limit_up_immunity_buy_threshold()))
        
        # 测试5：真实案例
        results.append(('真实案例600058', test_real_case_600058()))
        
        logger.info('='*60)
        logger.info('V14.2涨停豁免权测试总结')
        logger.info('='*60)
        
        for test_name, result in results:
            status = '✅ 通过' if result else '❌ 失败'
            logger.info(f'{test_name}: {status}')
        
        # 如果所有测试都通过
        if all(result for _, result in results):
            logger.info('='*60)
            logger.info('✅ 所有V14.2涨停豁免权测试通过！')
            logger.info('='*60)
            return 0
        else:
            logger.warning('='*60)
            logger.warning('⚠️ 部分V14.2涨停豁免权测试未通过')
            logger.warning('='*60)
            return 1
        
    except Exception as e:
        logger.error(f'❌ V14.2涨停豁免权测试异常: {e}')
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())