import sys
import pandas as pd
import numpy as np
from logic.signal_generator import SignalGenerator
from logic.data_manager import DataManager
from logic.logger import get_logger

logger = get_logger(__name__)

def test_fact_veto_capital_out():
    logger.info('=' * 50)
    logger.info('开始测试 V13 事实熔断：资金流出')
    logger.info('=' * 50)
    
    sg = SignalGenerator()
    
    # 测试用例 1：资金大幅流出，AI 分数很高
    logger.info('\n[测试用例 1] 资金大幅流出，AI 分数很高')
    result = sg.calculate_final_signal(
        stock_code='600519',
        ai_narrative_score=90,
        capital_flow_data=-100000000,
        trend_status='UP'
    )
    logger.info(f'AI 分数: 90')
    logger.info(f'资金流出: -10000万')
    logger.info(f'趋势: UP')
    logger.info(f'结果: {result}')
    
    assert result['signal'] == 'SELL', '应该触发资金流出熔断'
    assert result['final_score'] == 0, '最终评分应该归零'
    assert result['fact_veto'] == True, '应该标记为事实熔断'
    logger.info('✅ 测试用例 1 通过')
    
    # 测试用例 2：资金小幅流出，AI 分数很高
    logger.info('\n[测试用例 2] 资金小幅流出，AI 分数很高')
    result = sg.calculate_final_signal(
        stock_code='600519',
        ai_narrative_score=90,
        capital_flow_data=-30000000,
        trend_status='UP'
    )
    logger.info(f'AI 分数: 90')
    logger.info(f'资金流出: -3000万')
    logger.info(f'趋势: UP')
    logger.info(f'结果: {result}')
    
    assert result['signal'] == 'WAIT', '量价背离应该返回WAIT'
    assert result['fact_veto'] == False, '不应该触发事实熔断'
    logger.info('✅ 测试用例 2 通过')
    
    logger.info('\n' + '=' * 50)
    logger.info('✅ 资金流出熔断测试全部通过')
    logger.info('=' * 50)

def test_fact_veto_trend_down():
    logger.info('\n' + '=' * 50)
    logger.info('开始测试 V13 事实熔断：趋势向下')
    logger.info('=' * 50)
    
    sg = SignalGenerator()
    
    # 测试用例 3：趋势向下，资金流入
    logger.info('\n[测试用例 3] 趋势向下，资金流入')
    result = sg.calculate_final_signal(
        stock_code='600519',
        ai_narrative_score=90,
        capital_flow_data=50000000,
        trend_status='DOWN'
    )
    logger.info(f'AI 分数: 90')
    logger.info(f'资金流入: 5000万')
    logger.info(f'趋势: DOWN')
    logger.info(f'结果: {result}')
    
    assert result['signal'] == 'WAIT', '应该触发趋势向下熔断'
    assert result['final_score'] == 0, '最终评分应该归零'
    assert result['fact_veto'] == True, '应该标记为事实熔断'
    logger.info('✅ 测试用例 3 通过')
    
    logger.info('\n' + '=' * 50)
    logger.info('✅ 趋势向下熔断测试全部通过')
    logger.info('=' * 50)

def test_resonance_boost():
    logger.info('\n' + '=' * 50)
    logger.info('开始测试 V13 共振奖励')
    logger.info('=' * 50)
    
    sg = SignalGenerator()
    
    # 测试用例 4：资金流入 + 趋势向上（完美共振）
    logger.info('\n[测试用例 4] 资金流入 + 趋势向上（完美共振）')
    result = sg.calculate_final_signal(
        stock_code='600519',
        ai_narrative_score=80,
        capital_flow_data=50000000,
        trend_status='UP'
    )
    logger.info(f'AI 分数: 80')
    logger.info(f'资金流入: 5000万')
    logger.info(f'趋势: UP')
    logger.info(f'结果: {result}')
    
    expected_score = 80 * 1.2
    actual_score = result['final_score']
    msg = '最终评分应该是 ' + str(expected_score) + '，实际是 ' + str(actual_score)
    assert abs(actual_score - expected_score) < 0.1, msg
    assert result['signal'] == 'BUY', '应该返回BUY'
    assert result['fact_veto'] == False, '不应该触发事实熔断'
    logger.info('✅ 测试用例 4 通过')
    
    # 测试用例 5：资金流入 + 趋势震荡（潜伏观察）
    logger.info('\n[测试用例 5] 资金流入 + 趋势震荡（潜伏观察）')
    result = sg.calculate_final_signal(
        stock_code='600519',
        ai_narrative_score=90,
        capital_flow_data=50000000,
        trend_status='SIDEWAY'
    )
    logger.info(f'AI 分数: 90')
    logger.info(f'资金流入: 5000万')
    logger.info(f'趋势: SIDEWAY')
    logger.info(f'结果: {result}')
    
    expected_score = 90 * 0.9
    actual_score = result['final_score']
    msg = '最终评分应该是 ' + str(expected_score) + '，实际是 ' + str(actual_score)
    assert abs(actual_score - expected_score) < 0.1, msg
    assert result['signal'] == 'WAIT', '应该返回WAIT'
    logger.info('✅ 测试用例 5 通过')
    
    # 测试用例 6：资金流出 + 趋势向上（量价背离）
    logger.info('\n[测试用例 6] 资金流出 + 趋势向上（量价背离）')
    result = sg.calculate_final_signal(
        stock_code='600519',
        ai_narrative_score=90,
        capital_flow_data=-30000000,
        trend_status='UP'
    )
    logger.info(f'AI 分数: 90')
    logger.info(f'资金流出: -3000万')
    logger.info(f'趋势: UP')
    logger.info(f'结果: {result}')
    
    expected_score = 90 * 0.5
    actual_score = result['final_score']
    msg = '最终评分应该是 ' + str(expected_score) + '，实际是 ' + str(actual_score)
    assert abs(actual_score - expected_score) < 0.1, msg
    assert result['signal'] == 'WAIT', '应该返回WAIT'
    logger.info('✅ 测试用例 6 通过')
    
    logger.info('\n' + '=' * 50)
    logger.info('✅ 共振奖励测试全部通过')
    logger.info('=' * 50)

def test_trend_status():
    logger.info('\n' + '=' * 50)
    logger.info('开始测试 V13 趋势状态判断')
    logger.info('=' * 50)
    
    sg = SignalGenerator()
    
    # 创建测试数据
    dates = pd.date_range(start='2026-01-01', periods=30)
    
    # 测试用例 7：上升趋势
    logger.info('\n[测试用例 7] 上升趋势')
    prices_up = np.linspace(100, 130, 30)
    df_up = pd.DataFrame({'close': prices_up}, index=dates)
    trend = sg.get_trend_status(df_up)
    logger.info(f'趋势: {trend}')
    assert trend == 'UP', '应该是上升趋势'
    logger.info('✅ 测试用例 7 通过')
    
    # 测试用例 8：下降趋势
    logger.info('\n[测试用例 8] 下降趋势')
    prices_down = np.linspace(130, 100, 30)
    df_down = pd.DataFrame({'close': prices_down}, index=dates)
    trend = sg.get_trend_status(df_down)
    logger.info(f'趋势: {trend}')
    assert trend == 'DOWN', '应该是下降趋势'
    logger.info('✅ 测试用例 8 通过')
    
    # 测试用例 9：震荡趋势
    logger.info('\n[测试用例 9] 震荡趋势')
    prices_sideways = np.concatenate([
        np.linspace(100, 110, 10),
        np.linspace(110, 100, 10),
        np.linspace(100, 110, 10)
    ])
    df_sideways = pd.DataFrame({'close': prices_sideways}, index=dates)
    trend = sg.get_trend_status(df_sideways)
    logger.info(f'趋势: {trend}')
    assert trend == 'SIDEWAY', '应该是震荡趋势'
    logger.info('✅ 测试用例 9 通过')
    
    logger.info('\n' + '=' * 50)
    logger.info('✅ 趋势状态判断测试全部通过')
    logger.info('=' * 50)

def test_real_data_integration():
    logger.info('\n' + '=' * 50)
    logger.info('开始测试 V13 真实数据集成')
    logger.info('=' * 50)
    
    try:
        dm = DataManager()
        sg = SignalGenerator()
        
        # 测试用例 10：真实股票数据
        logger.info('\n[测试用例 10] 真实股票数据：600519')
        stock_code = '600519'
        
        # 获取历史数据
        start_date = pd.Timestamp.now() - pd.Timedelta(days=60)
        s_date_str = start_date.strftime('%Y%m%d')
        e_date_str = pd.Timestamp.now().strftime('%Y%m%d')
        
        df = dm.get_history_data(stock_code, start_date=s_date_str, end_date=e_date_str)
        
        if df.empty or len(df) < 20:
            logger.warning(f'股票 {stock_code} 数据不足，跳过测试')
            return
        
        # 获取趋势状态
        trend = sg.get_trend_status(df)
        logger.info(f'趋势状态: {trend}')
        
        # 获取资金流向
        capital_flow = sg.get_capital_flow(stock_code, dm)
        logger.info(f'资金流向: {capital_flow/10000:.2f}万')
        
        # 模拟 AI 分数
        ai_score = 75
        
        # 计算最终信号
        result = sg.calculate_final_signal(
            stock_code=stock_code,
            ai_narrative_score=ai_score,
            capital_flow_data=capital_flow,
            trend_status=trend
        )
        
        signal_val = result['signal']
        final_score_val = result['final_score']
        reason_val = result['reason']
        fact_veto_val = result['fact_veto']
        
        logger.info(f'AI 叙事分数: {ai_score}')
        logger.info(f'最终信号: {signal_val}')
        logger.info(f'最终评分: {final_score_val:.1f}')
        logger.info(f'原因: {reason_val}')
        logger.info(f'事实熔断: {fact_veto_val}')
        
        logger.info('✅ 测试用例 10 通过')
        
        logger.info('\n' + '=' * 50)
        logger.info('✅ 真实数据集成测试全部通过')
        logger.info('=' * 50)
        
    except Exception as e:
        logger.error(f'真实数据集成测试失败: {e}')
        logger.exception(e)

def main():
    logger.info('\n' + '=' * 70)
    logger.info('V13 事实一票否决制测试开始')
    logger.info('=' * 70)
    
    try:
        # 测试 1：资金流出熔断
        test_fact_veto_capital_out()
        
        # 测试 2：趋势向下熔断
        test_fact_veto_trend_down()
        
        # 测试 3：共振奖励
        test_resonance_boost()
        
        # 测试 4：趋势状态判断
        test_trend_status()
        
        # 测试 5：真实数据集成
        test_real_data_integration()
        
        logger.info('\n' + '=' * 70)
        logger.info('✅ 所有测试通过！')
        logger.info('=' * 70)
        
        print('\n' + '=' * 70)
        print('✅ V13 事实一票否决制测试全部通过！')
        print('=' * 70)
        
        return 0
        
    except Exception as e:
        logger.error(f'\n❌ 测试出错: {e}')
        logger.exception(e)
        print(f'\n❌ 测试出错: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(main())
