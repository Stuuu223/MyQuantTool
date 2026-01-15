"""
测试新系统集成
"""

import sys
from datetime import datetime, timedelta
import pandas as pd

# 测试实时情绪感知系统
print("=" * 50)
print("测试1: 实时情绪感知系统")
print("=" * 50)

try:
    from logic.realtime_sentiment_system import RealtimeSentimentProcessor

    processor = RealtimeSentimentProcessor()

    # 测试情绪处理
    result = processor.process_sentiment(
        news_score=0.5,
        social_score=0.3,
        price_score=0.4,
        fund_flow_score=0.6,
        current_position=0.5
    )

    print(f"✅ 情绪得分: {result['sentiment_score']:.2f}")
    print(f"✅ 情绪状态: {result['emotion_state']}")
    print(f"✅ 策略: {result['strategy']['strategy']}")
    print(f"✅ 目标仓位: {result['position_suggestion']['target_position']:.0%}")
    print(f"✅ 操作建议: {result['position_suggestion']['action']}")
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    print()

# 测试龙头识别与跟踪系统
print("=" * 50)
print("测试2: 龙头识别与跟踪系统")
print("=" * 50)

try:
    from logic.dragon_tracking_system import DragonTrackingSystem

    system = DragonTrackingSystem()

    # 生成模拟数据
    dates = pd.date_range(start=datetime.now() - timedelta(days=10), periods=10)
    stock_data = pd.DataFrame({
        'date': dates,
        'open': [10.0, 10.5, 11.0, 11.5, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
        'close': [10.5, 11.0, 11.5, 12.0, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5],
        'high': [10.6, 11.1, 11.6, 12.1, 12.6, 13.6, 14.6, 15.6, 16.6, 17.6],
        'low': [10.0, 10.5, 11.0, 11.5, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
        'volume': [1000000, 1200000, 1500000, 1800000, 2000000, 2500000, 3000000, 3500000, 4000000, 4500000],
        'pct_chg': [5.0, 4.8, 4.5, 4.3, 4.2, 8.3, 7.4, 6.9, 6.5, 6.1]
    })

    stock_info = {
        'market_cap': 50000000000,
        'social_heat': 0.8
    }

    sector_data = {
        'change_pct': 5.0
    }

    news_data = [
        {'publish_time': datetime.now() - timedelta(hours=2), 'title': '公司发布重大利好'},
        {'publish_time': datetime.now() - timedelta(hours=5), 'title': '行业前景看好'}
    ]

    # 分析股票
    result = system.analyze_stock(
        stock_code='600000',
        stock_data=stock_data,
        stock_info=stock_info,
        sector_data=sector_data,
        news_data=news_data
    )

    print(f"✅ 股票代码: {result['stock_code']}")
    print(f"✅ 是否为龙头: {'是' if result['is_dragon'] else '否'}")
    print(f"✅ 评分: {result['score']:.2f}")
    print(f"✅ 置信度: {result['confidence']:.2f}")
    print(f"✅ 潜力: {result['potential']}")
    print(f"✅ 生命周期: {result['lifecycle']['current_stage']}")
    print(f"✅ 操作建议: {result['lifecycle']['action']}")
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    print()

# 测试集合竞价预测系统
print("=" * 50)
print("测试3: 集合竞价预测系统")
print("=" * 50)

try:
    from logic.auction_prediction_system import AuctionPredictionSystem

    system = AuctionPredictionSystem()

    # 模拟竞价数据
    auction_data = {
        'price': 11.0,
        'volume': 2000000,
        'buy_volume': 1500000,
        'sell_volume': 500000,
        'high': 11.2,
        'low': 10.8,
        'buy_orders': [
            {'price': 10.9, 'volume': 500000},
            {'price': 10.8, 'volume': 1000000}
        ],
        'sell_orders': [
            {'price': 11.1, 'volume': 300000},
            {'price': 11.2, 'volume': 200000}
        ]
    }

    # 模拟前一日数据
    prev_data = {
        'open': 10.0,
        'close': 10.5,
        'high': 10.6,
        'low': 9.9,
        'volume': 1000000
    }

    # 分析竞价
    result = system.analyze(
        stock_code='600000',
        auction_data=auction_data,
        prev_data=prev_data,
        market_sentiment=0.5
    )

    print(f"✅ 股票代码: {result['stock_code']}")
    print(f"✅ 开盘价预测: {result['opening_prediction']['opening_price']['price']:.2f}")
    print(f"✅ 开盘走势: {result['opening_prediction']['opening_price']['prediction']}")
    print(f"✅ 开盘强度: {result['opening_prediction']['strength']:.2f}")
    print(f"✅ 弱转强: {'是' if result['weak_to_strong']['is_wts'] else '否'}")
    print(f"✅ 弱转强强度: {result['weak_to_strong']['strength']:.2f}")
    print(f"✅ 预测置信度: {result['opening_prediction']['confidence']:.2f}")
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    print()

# 测试在线参数调整系统
print("=" * 50)
print("测试4: 在线参数调整系统")
print("=" * 50)

try:
    from logic.online_parameter_adjustment import OnlineParameterAdjustmentSystem

    system = OnlineParameterAdjustmentSystem()
    system.register_strategy('midway_strategy')

    # 模拟近期性能
    recent_performance = {
        'sharpe_ratio': 0.8,
        'win_rate': 0.35,
        'max_drawdown': 0.18,
        'return': 0.15
    }

    # 调整参数
    result = system.adjust_strategy('midway_strategy', recent_performance)

    print(f"✅ 调整状态: {'已调整' if result['adjustment_made'] else '未调整'}")
    print(f"✅ 调整次数: {result['adjustment_count']}")
    print(f"✅ 当前仓位: {result['current_params']['position_size']:.0%}")
    print(f"✅ 当前止损: {result['current_params']['stop_loss']:.2%}")
    print(f"✅ 当前止盈: {result['current_params']['take_profit']:.2%}")

    if result['adjustment_made']:
        print(f"✅ 调整详情:")
        for adj in result['adjustments']:
            print(f"   - {adj['rule']}")

    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    print()

print("=" * 50)
print("✅ 所有系统测试完成！")
print("=" * 50)