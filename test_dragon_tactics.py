"""
测试龙头战法 - 博士眼镜案例
验证 V3.0 龙头暴力版的效果
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

from logic.dragon_tactics import DragonTactics
from logic.ai_agent import DragonAIAgent, RuleBasedAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_boshi_glasses_data():
    """生成博士眼镜（300622）模拟数据"""
    np.random.seed(42)
    
    # 生成30天的K线数据
    dates = pd.date_range(end=datetime.now(), periods=30)
    
    # 模拟上涨趋势
    base_price = 20.0
    trend = np.linspace(0, 50, 30)  # 上涨趋势
    
    # 生成价格
    prices = base_price + trend + np.random.randn(30) * 2
    
    # 模拟昨天大跌（弱转强前兆）
    prices[-2] = prices[-3] * 0.95  # 昨天大跌5%
    
    # 今天高开
    prices[-1] = prices[-2] * 1.05  # 今天高开5%
    
    data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.uniform(-0.02, 0.02, 30)),
        'high': prices * (1 + np.abs(np.random.randn(30)) * 0.03),
        'low': prices * (1 - np.abs(np.random.randn(30)) * 0.03),
        'close': prices,
        'volume': np.random.randint(1000000, 50000000, 30)
    })
    
    # 调整最后一天（今天）的数据
    data.loc[data.index[-1], 'open'] = data.loc[data.index[-2], 'close'] * 1.05  # 高开5%
    data.loc[data.index[-1], 'close'] = data.loc[data.index[-1], 'open'] * 1.10  # 涨停10%
    data.loc[data.index[-1], 'high'] = data.loc[data.index[-1], 'close']  # 涨停价
    data.loc[data.index[-1], 'volume'] = 80000000  # 放量
    
    return data


def generate_sector_data():
    """生成板块数据（AI眼镜概念）"""
    # 模拟板块内5只股票
    stocks = [
        {'symbol': '300622', 'name': '博士眼镜', 'change_percent': 10.0},
        {'symbol': '300XXX', 'name': '股票A', 'change_percent': 8.5},
        {'symbol': '300YYY', 'name': '股票B', 'change_percent': 7.2},
        {'symbol': '300ZZZ', 'name': '股票C', 'change_percent': 6.1},
        {'symbol': '300WWW', 'name': '股票D', 'change_percent': 4.3}
    ]
    
    sector_df = pd.DataFrame(stocks)
    sector_df = sector_df.sort_values('change_percent', ascending=False).reset_index(drop=True)
    
    return {
        'sector': 'AI眼镜',
        'sector_stocks': sector_df,
        'limit_up_count': 1,  # 博士眼镜涨停
        'sector_heat': '热'
    }


def generate_auction_data():
    """生成竞价数据"""
    return {
        'open_volume': 15000000,  # 9:25成交量1500万
        'prev_day_volume': 80000000,  # 昨天全天成交量8000万
        'open_amount': 300000000,  # 9:25成交额3亿
        'prev_day_amount': 1600000000  # 昨天全天成交额16亿
    }


def generate_intraday_data():
    """生成分时数据"""
    # 生成30分钟的分时数据
    times = pd.date_range(start=datetime.now().replace(hour=9, minute=30), periods=30, freq='1min')
    
    base_price = 28.0
    prices = []
    volumes = []
    
    for i in range(30):
        # 价格在均线上方运行
        price = base_price + i * 0.05 + np.random.randn() * 0.1
        prices.append(price)
        # 上涨放量
        volume = 100000 * (1 + i * 0.1) + np.random.randint(0, 50000)
        volumes.append(volume)
    
    return pd.DataFrame({
        'time': times,
        'price': prices,
        'volume': volumes
    })


def test_dragon_tactics_basic():
    """测试基础龙头战法"""
    logger.info("\n" + "="*60)
    logger.info("测试基础龙头战法")
    logger.info("="*60)
    
    # 初始化龙头战法分析器
    tactics = DragonTactics()
    
    # 1. 代码前缀检查
    logger.info("\n1. 代码前缀检查")
    code_check = tactics.check_code_prefix('300622')
    logger.info(f"  代码: 300622")
    logger.info(f"  赛道: {code_check.get('prefix_type', '未知')}")
    logger.info(f"  涨停限制: {code_check.get('max_limit', 10)}cm")
    logger.info(f"  是否禁止: {code_check.get('banned', False)}")
    
    # 2. 竞价分析
    logger.info("\n2. 竞价分析")
    auction_data = generate_auction_data()
    auction_analysis = tactics.analyze_call_auction(
        auction_data['open_volume'],
        auction_data['prev_day_volume'],
        auction_data['open_amount'],
        auction_data['prev_day_amount']
    )
    logger.info(f"  竞价量比: {auction_analysis.get('call_auction_ratio', 0):.2%}")
    logger.info(f"  竞价强度: {auction_analysis.get('auction_intensity', '未知')}")
    logger.info(f"  竞价评分: {auction_analysis.get('auction_score', 0)}")
    
    # 3. 板块地位分析
    logger.info("\n3. 板块地位分析")
    sector_data = generate_sector_data()
    sector_analysis = tactics.analyze_sector_rank(
        '300622',
        sector_data['sector'],
        10.0,  # 涨幅10%
        sector_data['sector_stocks'],
        sector_data['limit_up_count']
    )
    logger.info(f"  板块: {sector_analysis.get('sector', '未知')}")
    logger.info(f"  角色: {sector_analysis.get('role', '未知')}")
    logger.info(f"  板块排名: {sector_analysis.get('rank_in_sector', 'N/A')}")
    logger.info(f"  板块热度: {sector_analysis.get('sector_heat', '未知')}")
    logger.info(f"  角色评分: {sector_analysis.get('role_score', 0)}")
    
    # 4. 弱转强分析
    logger.info("\n4. 弱转强分析")
    kline_data = generate_boshi_glasses_data()
    weak_to_strong = tactics.analyze_weak_to_strong(kline_data)
    logger.info(f"  弱转强: {'是' if weak_to_strong.get('weak_to_strong', False) else '否'}")
    logger.info(f"  描述: {weak_to_strong.get('weak_to_strong_desc', '无')}")
    logger.info(f"  评分: {weak_to_strong.get('weak_to_strong_score', 0)}")
    
    # 5. 分时承接分析
    logger.info("\n5. 分时承接分析")
    intraday_data = generate_intraday_data()
    intraday_support = tactics.analyze_intraday_support(intraday_data)
    logger.info(f"  承接力度: {intraday_support.get('intraday_support_desc', '未知')}")
    logger.info(f"  承接评分: {intraday_support.get('intraday_support_score', 0)}")
    
    # 6. 决策矩阵
    logger.info("\n6. 决策矩阵")
    decision = tactics.make_decision_matrix(
        sector_analysis.get('role_score', 0),
        auction_analysis.get('auction_score', 0),
        weak_to_strong.get('weak_to_strong_score', 0),
        intraday_support.get('intraday_support_score', 0),
        10.0,  # 涨幅10%
        True  # 20cm
    )
    logger.info(f"  综合评分: {decision.get('total_score', 0):.1f}")
    logger.info(f"  角色: {decision.get('role', '未知')}")
    logger.info(f"  信号: {decision.get('signal', 'WAIT')}")
    logger.info(f"  操作: {decision.get('action', '观望')}")
    logger.info(f"  仓位: {decision.get('position', '0')}")
    logger.info(f"  理由: {decision.get('reason', '无')}")
    
    return decision


def test_dragon_ai_agent():
    """测试龙头战法 AI 代理"""
    logger.info("\n" + "="*60)
    logger.info("测试龙头战法 AI 代理")
    logger.info("="*60)
    
    # 初始化 AI 代理（使用规则代理，因为需要 API Key）
    logger.info("\n使用规则代理（无需 API Key）...")
    
    # 准备数据
    price_data = {
        'current_price': 28.0,
        'change_percent': 10.0,
        'volume': 80000000
    }
    
    technical_data = {
        'rsi': {'RSI': 75},
        'macd': {'Trend': '多头'},
        'money_flow': {'资金流向': '大幅流入'}
    }
    
    auction_data = generate_auction_data()
    sector_data = generate_sector_data()
    kline_data = generate_boshi_glasses_data()
    intraday_data = generate_intraday_data()
    
    # 使用规则代理
    rule_agent = RuleBasedAgent()
    result = rule_agent.analyze_stock('300622', price_data, technical_data)
    
    logger.info("\n规则代理分析结果:")
    logger.info(f"  分析报告: {result[:200]}...")  # 只显示前200个字符
    
    # 如果有 API Key，可以使用 DragonAIAgent
    logger.info("\n" + "-"*60)
    logger.info("提示：配置 LLM API Key 后可获得更智能的龙头战法分析")
    logger.info("  - 使用 V3.0 龙头暴力版 Prompt")
    logger.info("  - 自动识别龙头地位")
    logger.info("  - 分析竞价爆量、弱转强、分时承接")
    logger.info("  - 输出 BUY_AGGRESSIVE/BUY_DIP/WAIT/SELL 信号")
    logger.info("-"*60)


def test_comparison():
    """对比传统分析 vs 龙头战法"""
    logger.info("\n" + "="*60)
    logger.info("对比：传统分析 vs 龙头战法")
    logger.info("="*60)
    
    # 传统分析
    logger.info("\n传统分析（基于技术指标）:")
    logger.info("  关注点：RSI、MACD、KDJ、布林带")
    logger.info("  买入信号：RSI超卖、MACD金叉")
    logger.info("  缺点：反应慢，错过龙头启动点")
    logger.info("  适用场景：趋势反转、波段操作")
    
    # 龙头战法
    logger.info("\n龙头战法（V3.0 暴力版）:")
    logger.info("  关注点：龙头地位、竞价爆量、弱转强、分时承接")
    logger.info("  买入信号：BUY_AGGRESSIVE（猛干）、BUY_DIP（低吸）")
    logger.info("  优势：捕捉龙头加速段，不纠结回调")
    logger.info("  适用场景：短线博弈、龙头追涨")
    
    # 博士眼镜案例
    logger.info("\n博士眼镜（300622）案例分析:")
    logger.info("  传统分析：RSI=75（超买），建议观望")
    logger.info("  龙头战法：龙头+竞价爆量+弱转强，建议 BUY_AGGRESSIVE")
    logger.info("  差异：传统分析错过，龙头战法猛干")


if __name__ == "__main__":
    logger.info("\n" + "="*60)
    logger.info("龙头战法测试 - 博士眼镜案例")
    logger.info("="*60)
    
    # 运行测试
    test_dragon_tactics_basic()
    test_dragon_ai_agent()
    test_comparison()
    
    logger.info("\n" + "="*60)
    logger.info("测试完成！")
    logger.info("="*60)
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_dragon_tactics_results_{timestamp}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("龙头战法测试结果\n")
        f.write("="*60 + "\n\n")
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"测试标的: 博士眼镜（300622）\n")
        f.write(f"\n核心优势:\n")
        f.write("  1. 龙头辨识：板块内唯一涨停、最早上板、有伴助攻\n")
        f.write("  2. 竞价分析：竞价量比>15%为极强，主力抢筹\n")
        f.write("  3. 弱转强：昨日大跌+今日高开，最强买点\n")
        f.write("  4. 分时承接：价格在均线上方，下跌缩量上涨放量\n")
        f.write("  5. 决策矩阵：综合评分，输出 BUY_AGGRESSIVE/BUY_DIP/WAIT/SELL\n")
        f.write(f"\nV3.0 暴力版特色:\n")
        f.write("  - 禁止等待回调：龙头启动不回调\n")
        f.write("  - 禁止看 KDJ/MACD：指标太慢\n")
        f.write("  - 禁止看 PE/PB：短线只看情绪和资金\n")
        f.write("  - 信条：龙头多一条命、强者恒强、分歧是买点\n")
    
    logger.info(f"\n结果已保存到: {output_file}")