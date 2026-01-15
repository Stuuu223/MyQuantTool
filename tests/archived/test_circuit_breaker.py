"""
测试情绪过热熔断机制
验证"群魔乱舞"场景的自动识别和熔断
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime

from logic.market_sentiment_monitor import MarketSentimentMonitor, CircuitBreaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_scenarios():
    """生成测试场景"""
    np.random.seed(42)
    
    # 场景1：群魔乱舞（11个80分的股票）
    logger.info("\n" + "="*60)
    logger.info("场景1：群魔乱舞（11个80分）")
    logger.info("="*60)
    
    stocks_divergence = []
    for i in range(11):
        stocks_divergence.append({
            'symbol': f'300{i:03d}',
            'name': f'股票{i}',
            'score': 80 + np.random.randint(-2, 3),  # 78-83分
            'change_percent': 8 + np.random.uniform(-1, 2),
            'amount': 500000000 + np.random.randint(-100000000, 100000000)
        })
    
    # 添加一些低分股票
    for i in range(10):
        stocks_divergence.append({
            'symbol': f'600{i:03d}',
            'name': f'股票{i+11}',
            'score': 40 + np.random.randint(-10, 10),
            'change_percent': 2 + np.random.uniform(-1, 3),
            'amount': 100000000 + np.random.randint(-50000000, 50000000)
        })
    
    # 场景2：真龙引领（1个95分的真龙）
    logger.info("\n" + "="*60)
    logger.info("场景2：真龙引领（1个95分的真龙）")
    logger.info("="*60)
    
    stocks_focus = []
    stocks_focus.append({
        'symbol': '300999',
        'name': '真龙股票',
        'score': 95,
        'change_percent': 15.0,
        'amount': 800000000
    })
    
    for i in range(10):
        stocks_focus.append({
            'symbol': f'600{i:03d}',
            'name': f'股票{i}',
            'score': 40 + np.random.randint(-10, 10),
            'change_percent': 2 + np.random.uniform(-1, 3),
            'amount': 100000000 + np.random.randint(-50000000, 50000000)
        })
    
    # 场景3：平庸扩散（5个80分，无真龙）
    logger.info("\n" + "="*60)
    logger.info("场景3：平庸扩散（5个80分，无真龙）")
    logger.info("="*60)
    
    stocks_mediocre = []
    for i in range(5):
        stocks_mediocre.append({
            'symbol': f'300{i:03d}',
            'name': f'股票{i}',
            'score': 80 + np.random.randint(-2, 3),
            'change_percent': 7 + np.random.uniform(-1, 2),
            'amount': 400000000 + np.random.randint(-50000000, 50000000)
        })
    
    for i in range(10):
        stocks_mediocre.append({
            'symbol': f'600{i:03d}',
            'name': f'股票{i+5}',
            'score': 50 + np.random.randint(-10, 10),
            'change_percent': 3 + np.random.uniform(-1, 2),
            'amount': 150000000 + np.random.randint(-50000000, 50000000)
        })
    
    return stocks_divergence, stocks_focus, stocks_mediocre


def test_scenario(name: str, stocks: List[Dict[str, Any]]):
    """测试单个场景"""
    logger.info(f"\n测试场景：{name}")
    logger.info("-"*60)
    
    # 创建监控器和熔断器
    monitor = MarketSentimentMonitor()
    breaker = CircuitBreaker(monitor)
    
    # 检查市场结构
    structure = monitor.check_market_structure(stocks)
    
    # 打印市场摘要
    summary = monitor.get_market_summary(structure)
    print(summary)
    
    # 检查熔断
    breaker_result = breaker.check_and_break(stocks)
    
    logger.info(f"\n熔断器状态:")
    logger.info(f"  是否触发: {'是' if breaker_result['is_triggered'] else '否'}")
    logger.info(f"  触发原因: {breaker_result['trigger_reason']}")
    logger.info(f"  熔断动作: {breaker_result['breaker_result']['break_action']}")
    logger.info(f"  市场状态: {breaker_result['market_structure']['market_state']}")
    logger.info(f"  预警级别: {breaker_result['market_structure']['warning_level']}")
    
    # 检查是否可以交易
    can_trade = breaker.can_trade()
    logger.info(f"\n是否可以交易: {'是' if can_trade else '否'}")
    
    # 识别龙头
    dragon = monitor.identify_dragon(stocks, min_score=90)
    if dragon:
        logger.info(f"\n识别出的龙头: {dragon['symbol']} - 评分:{dragon['score']} 涨幅:{dragon['change_percent']:.2f}%")
    else:
        logger.info(f"\n未识别出真正的龙头")
    
    # 返回结果
    return {
        'scenario': name,
        'market_state': structure['market_state'],
        'warning_level': structure['warning_level'],
        'is_triggered': breaker_result['is_triggered'],
        'can_trade': can_trade,
        'dragon': dragon
    }


def test_batch_analysis_with_sentiment_monitor():
    """测试批量分析时的情绪监控"""
    logger.info("\n" + "="*60)
    logger.info("测试批量分析时的情绪监控")
    logger.info("="*60)
    
    # 模拟批量分析数据（11个80分的股票）
    stocks = []
    for i in range(11):
        stocks.append({
            'symbol': f'300{i:03d}',
            'price_data': {
                'current_price': 20.0 + i * 0.5,
                'change_percent': 8.0 + np.random.uniform(-1, 2),
                'amount': 500000000 + np.random.randint(-100000000, 100000000)
            },
            'technical_data': {
                'rsi': {'RSI': 70 + np.random.randint(-5, 5)},
                'macd': {'Trend': '多头'},
                'money_flow': {'资金流向': '流入'}
            }
        })
    
    # 添加一些低分股票
    for i in range(10):
        stocks.append({
            'symbol': f'600{i:03d}',
            'price_data': {
                'current_price': 10.0 + i * 0.3,
                'change_percent': 2.0 + np.random.uniform(-1, 2),
                'amount': 100000000 + np.random.randint(-50000000, 50000000)
            },
            'technical_data': {
                'rsi': {'RSI': 50 + np.random.randint(-10, 10)},
                'macd': {'Trend': '震荡'},
                'money_flow': {'资金流向': '观望'}
            }
        })
    
    # 创建 AI 代理（使用规则代理）
    from logic.ai_agent import RuleBasedAgent
    agent = RuleBasedAgent()
    
    # 模拟批量分析（不使用 LLM，使用规则代理）
    logger.info("\n模拟批量分析（使用规则代理）...")
    results = []
    for stock in stocks:
        result = agent.analyze_stock(
            stock['symbol'],
            stock['price_data'],
            stock['technical_data']
        )
        # 添加评分（模拟）
        score = 80 if stock['symbol'].startswith('300') and stock['price_data']['change_percent'] > 5 else 50
        results.append({
            'symbol': stock['symbol'],
            'score': score,
            'change_percent': stock['price_data']['change_percent'],
            'amount': stock['price_data'].get('amount', 0)
        })
    
    # 检查市场结构
    monitor = MarketSentimentMonitor()
    breaker = CircuitBreaker(monitor)
    breaker_result = breaker.check_and_break(results)
    
    logger.info(f"\n批量分析结果:")
    logger.info(f"  分析股票数: {len(results)}")
    logger.info(f"  市场状态: {breaker_result['market_structure']['market_state']}")
    logger.info(f"  预警级别: {breaker_result['market_structure']['warning_level']}")
    logger.info(f"  熔断触发: {'是' if breaker_result['is_triggered'] else '否'}")
    
    if breaker_result['is_triggered']:
        logger.info(f"\n⚠️ 警告：{breaker_result['trigger_reason']}")
        logger.info(f"建议操作：{breaker_result['breaker_result']['break_action']}")
        logger.info(f"停止开仓，空仓观望！")
    else:
        logger.info(f"\n✅ 市场健康，可以正常交易")


def test_real_world_case():
    """测试真实案例：博士眼镜 vs 群魔乱舞"""
    logger.info("\n" + "="*60)
    logger.info("测试真实案例：博士眼镜 vs 群魔乱舞")
    logger.info("="*60)
    
    # 模拟当前市场（11个80分的股票）
    logger.info("\n当前市场状态：11个80分的股票")
    logger.info("股票列表：扬电科技、东方国信、特变电工、威唐、安控等")
    
    stocks = []
    # 扬电科技（龙头候选）
    stocks.append({
        'symbol': '301012',
        'name': '扬电科技',
        'score': 82,
        'change_percent': 10.60,
        'amount': 600000000
    })
    
    # 东方国信
    stocks.append({
        'symbol': '300166',
        'name': '东方国信',
        'score': 80,
        'change_percent': 7.06,
        'amount': 500000000
    })
    
    # 特变电工
    stocks.append({
        'symbol': '600089',
        'name': '特变电工',
        'score': 75,
        'change_percent': 6.72,
        'amount': 800000000
    })
    
    # 其他8个80分股票
    for i in range(8):
        stocks.append({
            'symbol': f'300{i+100:03d}',
            'name': f'股票{i}',
            'score': 80 + np.random.randint(-2, 3),
            'change_percent': 7 + np.random.uniform(-1, 2),
            'amount': 400000000 + np.random.randint(-50000000, 50000000)
        })
    
    # 添加低分股票
    for i in range(10):
        stocks.append({
            'symbol': f'600{i+20:03d}',
            'name': f'股票{i+8}',
            'score': 40 + np.random.randint(-10, 10),
            'change_percent': 2 + np.random.uniform(-1, 3),
            'amount': 100000000 + np.random.randint(-50000000, 50000000)
        })
    
    # 检查市场结构
    monitor = MarketSentimentMonitor()
    breaker = CircuitBreaker(monitor)
    breaker_result = breaker.check_and_break(stocks)
    
    logger.info(f"\n市场分析结果:")
    logger.info(f"  市场状态: {breaker_result['market_structure']['market_state']}")
    logger.info(f"  预警级别: {breaker_result['market_structure']['warning_level']}")
    logger.info(f"  熔断触发: {'是' if breaker_result['is_triggered'] else '否'}")
    
    if breaker_result['is_triggered']:
        logger.info(f"\n⚠️⚠️⚠️ 熔断触发！⚠️⚠️")
        logger.info(f"  触发原因：{breaker_result['trigger_reason']}")
        logger.info(f"  市场状态：{breaker_result['market_structure']['market_state']}")
        logger.info(f"  操作建议：{breaker_result['breaker_result']['break_action']}")
        logger.info(f"")
        logger.info(f"游资视角复盘：")
        logger.info(f"  - 11个80分 = 平庸的扩散，资金分散，无合力")
        logger.info(f"  - 这不是机会，而是陷阱")
        logger.info(f"  - 题材高峰期，马上进入退潮期")
        logger.info(f"  - 冲进去，大概率买在山顶")
        logger.info(f"  - 管住手，一个都别追")
        logger.info(f"  - 只盯住龙一：扬电科技下午能不能硬板")
        logger.info(f"  - 如果封不死，明天大概率集体低开闷杀")
    
    # 识别龙头
    dragon = monitor.identify_dragon(stocks, min_score=90)
    if dragon:
        logger.info(f"\n识别出的龙头: {dragon['name']}（{dragon['symbol']}）")
        logger.info(f"   评分: {dragon['score']}")
        logger.info(f"  涨幅: {dragon['change_percent']:.2f}%")
        logger.info(f"   游资视角：勉强可看，但不是真龙")
    else:
        logger.info(f"\n未识别出真正的龙头（95分以上）")


if __name__ == "__main__":
    logger.info("\n" + "="*60)
    logger.info("情绪过热熔断机制测试")
    logger.info("="*60)
    
    # 生成测试场景
    stocks_divergence, stocks_focus, stocks_mediocre = generate_scenarios()
    
    # 测试各个场景
    result1 = test_scenario("群魔乱舞", stocks_divergence)
    result2 = test_scenario("真龙引领", stocks_focus)
    result3 = test_scenario("平庸扩散", stocks_mediocre)
    
    # 测试批量分析
    test_batch_analysis_with_sentiment_monitor()
    
    # 测试真实案例
    test_real_world_case()
    
    logger.info("\n" + "="*60)
    logger.info("测试总结")
    logger.info("="*60)
    
    logger.info(f"\n场景对比:")
    logger.info(f"  群魔乱舞: {result1['market_state']} - 熔断:{result1['is_triggered']}")
    logger.info(f"  真龙引领: {result2['market_state']} - 熔断:{result2['is_triggered']}")
    logger.info(f"  平庸扩散: {result3['market_state']} - 熔断:{result3['is_triggered']}")
    
    logger.info(f"\n核心优势:")
    logger.info(f"  1. 自动识别'平庸的扩散'（11个80分）")
    logger.info(f"  2. 区分'真龙引领' vs '群魔乱舞'")
    logger.info(f"  3. 情绪过热时自动熔断，停止开仓")
    logger.info(f"  4. 防止在题材高峰期追高被套")
    logger.info(f"  5. 从'盲目追涨'到'理性择时'")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_circuit_breaker_results_{timestamp}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("情绪过热熔断机制测试结果\n")
        f.write("="*60 + "\n\n")
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\n核心功能:\n")
        f.write("  1. 检查市场结构：真龙引领 vs 群魔乱舞\n")
        f.write("  2. 情绪过热熔断：自动识别危险信号\n")
        f.write("  3. 龙头识别：找到真正的龙头\n")
        f.write("  4. 风险预警：提前提示市场退潮\n")
        f.write(f"\n识别模式:\n")
        f.write("  - 健康龙头：1-2个95分真龙 + 3个以下80分\n")
        f.write("  - 群魔乱舞：8个以上80分 + 0个95分\n")
        f.write("  - 平庸扩散：5-8个80分 + 0-1个95分\n")
        f.write(f"\n游资视角:\n")
        f.write("  - 真龙行情：众星捧月，资金聚焦\n")
        f.write("  - 群魔乱舞：平庸扩散，资金分散，无合力\n")
        f.write("  - 题材高峰：马上进入退潮期\n")
        f.write("  - 追高被套：买在山顶，明天低开闷杀\n")
    
    logger.info(f"\n结果已保存到: {output_file}")
