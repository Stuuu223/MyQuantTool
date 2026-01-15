"""
测试市场数据准确性

验证：
1. 涨跌停家数
2. 最高板数
3. 平均溢价
4. 炸板率
5. 晋级率
6. 主线识别
"""

import pandas as pd
from logic.market_cycle import MarketCycleManager
from logic.theme_detector import ThemeDetector
from logic.data_manager import DataManager
from logic.logger import get_logger

logger = get_logger(__name__)

print("=" * 60)
print("市场数据准确性测试")
print("=" * 60)

# 1. 测试涨跌停家数
print("\n[1/6] 测试涨跌停家数...")
cycle_manager = MarketCycleManager()
limit_up_down = cycle_manager.get_limit_up_down_count()
print(f"涨停家数: {limit_up_down['limit_up_count']}")
print(f"跌停家数: {limit_up_down['limit_down_count']}")

if limit_up_down['limit_up_stocks']:
    print(f"\n涨停股票（前5只）:")
    for i, stock in enumerate(limit_up_down['limit_up_stocks'][:5], 1):
        print(f"  {i}. {stock['name']} ({stock['code']}) - {stock['change_pct']:.2f}%")

if limit_up_down['limit_down_stocks']:
    print(f"\n跌停股票（前5只）:")
    for i, stock in enumerate(limit_up_down['limit_down_stocks'][:5], 1):
        print(f"  {i}. {stock['name']} ({stock['code']}) - {stock['change_pct']:.2f}%")

# 2. 测试最高板数
print("\n[2/6] 测试最高板数...")
board_info = cycle_manager.get_consecutive_board_height()
print(f"最高板: {board_info['max_board']}")
print(f"连板分布: {board_info['board_distribution']}")

# 3. 测试平均溢价
print("\n[3/6] 测试平均溢价...")
prev_profit = cycle_manager.get_prev_limit_up_profit()
print(f"平均溢价: {prev_profit['avg_profit']:.2f}%")
print(f"盈利数量: {prev_profit['profit_count']}")
print(f"亏损数量: {prev_profit['loss_count']}")

# 4. 测试炸板率
print("\n[4/6] 测试炸板率...")
burst_rate = cycle_manager.get_limit_up_burst_rate()
print(f"炸板率: {burst_rate:.2%}")

# 5. 测试晋级率
print("\n[5/6] 测试晋级率...")
promotion_rate = cycle_manager.get_board_promotion_rate()
print(f"晋级率: {promotion_rate:.2%}")

# 6. 测试主线识别
print("\n[6/6] 测试主线识别...")
theme_detector = ThemeDetector()
theme_info = theme_detector.analyze_main_theme(limit_up_down['limit_up_stocks'])
print(f"主线板块: {theme_info['main_theme']}")
print(f"主线热度: {theme_info['theme_heat']:.1%}")
if theme_info['leader']:
    print(f"龙头股票: {theme_info['leader']['name']} ({theme_info['leader']['code']}) - {theme_info['leader']['change_pct']:.2f}%")
print(f"投资建议: {theme_info['suggestion']}")

# 7. 获取完整的市场情绪指标
print("\n[7/7] 获取完整的市场情绪指标...")
indicators = cycle_manager.get_market_emotion()
print(f"\n市场情绪指标:")
print(f"  涨停家数: {indicators['limit_up_count']}")
print(f"  跌停家数: {indicators['limit_down_count']}")
print(f"  最高板: {indicators['highest_board']}")
print(f"  平均溢价: {indicators['avg_profit']:.2%}")
print(f"  炸板率: {indicators['burst_rate']:.2%}")
print(f"  晋级率: {indicators['promotion_rate']:.2%}")

# 8. 诊断问题
print("\n" + "=" * 60)
print("问题诊断")
print("=" * 60)

# 检查数据库中是否有历史数据
print("\n检查数据库中是否有历史数据...")
db = DataManager()
from datetime import datetime, timedelta

today = datetime.now().strftime('%Y-%m-%d')
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

print(f"今天日期: {today}")
print(f"昨天日期: {yesterday}")

# 检查今天的数据
today_query = f"SELECT COUNT(*) as count FROM daily_bars WHERE date = '{today}'"
today_df = pd.read_sql(today_query, db.conn)
print(f"今天数据条数: {today_df.iloc[0]['count']}")

# 检查昨天的数据
yesterday_query = f"SELECT COUNT(*) as count FROM daily_bars WHERE date = '{yesterday}'"
yesterday_df = pd.read_sql(yesterday_query, db.conn)
print(f"昨天数据条数: {yesterday_df.iloc[0]['count']}")

# 检查最近的数据
recent_query = f"SELECT date, COUNT(*) as count FROM daily_bars GROUP BY date ORDER BY date DESC LIMIT 5"
recent_df = pd.read_sql(recent_query, db.conn)
print(f"\n最近5天的数据:")
for _, row in recent_df.iterrows():
    print(f"  {row['date']}: {row['count']} 条")

# 检查是否有涨停数据
limit_up_query = f"""
SELECT date, COUNT(*) as count 
FROM daily_bars 
WHERE ((close - open) / open * 100 >= 9.5 OR (close - open) / open * 100 <= -9.5)
GROUP BY date 
ORDER BY date DESC 
LIMIT 5
"""
limit_up_df = pd.read_sql(limit_up_query, db.conn)
print(f"\n最近5天的涨跌停数据:")
for _, row in limit_up_df.iterrows():
    print(f"  {row['date']}: {row['count']} 条")

# 9. 问题总结
print("\n" + "=" * 60)
print("问题总结")
print("=" * 60)

if yesterday_df.iloc[0]['count'] == 0:
    print("⚠️ 数据库中没有昨天的数据")
    print("   原因：平均溢价、炸板率、晋级率都依赖昨天的数据")
    print("   解决：需要确保数据库中有正确的历史数据")

if board_info['max_board'] == 0:
    print("⚠️ 最高板显示为0")
    print("   原因：get_consecutive_board_height 方法可能有问题")
    print("   解决：需要检查连板高度计算逻辑")

if prev_profit['avg_profit'] == 0:
    print("⚠️ 平均溢价显示为0")
    print("   原因：数据库中没有昨天的涨停数据")
    print("   解决：需要确保数据库中有正确的历史数据")

if burst_rate == 0:
    print("⚠️ 炸板率显示为0")
    print("   原因：数据库中没有昨天的涨停数据")
    print("   解决：需要确保数据库中有正确的历史数据")

if promotion_rate == 0:
    print("⚠️ 晋级率显示为0")
    print("   原因：数据库中没有昨天的涨停数据")
    print("   解决：需要确保数据库中有正确的历史数据")

if theme_info['leader'] and theme_info['leader']['change_pct'] > 100:
    print("⚠️ 龙头股票涨幅超过100%")
    print(f"   原因：{theme_info['leader']['name']} 可能是新股（N开头）")
    print("   解决：应该排除新股，或者对新股做特殊处理")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
