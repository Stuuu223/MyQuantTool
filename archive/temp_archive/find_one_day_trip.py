"""查找典型的一日游案例"""
import json
from datetime import datetime, timedelta

# 加载交易记录
with open('E:/MyQuantTool/data/backtest_results_real/trade_details.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print("="*80)
print("查找典型的一日游案例（首日猛攻 + 次日无溢价）")
print("="*80)

one_day_trips = []

for trade in trades:
    code = trade['code']
    buy_date = trade['buy_date']
    buy_snapshot = trade['buy_snapshot']

    # 首日数据
    buy_price = buy_snapshot['price']['close']
    buy_pct = buy_snapshot['price']['pct_chg']
    buy_amount = buy_snapshot['price']['amount_yi']
    main_inflow = buy_snapshot['flow']['main_net_inflow_wan']

    # 卖出记录
    sell_records = trade['sell_records']

    for sell in sell_records:
        sell_date = sell['date']
        sell_price = sell['price']
        holding_days = sell['holding_days']
        pnl_pct = sell['pnl_pct']

        # 判断是否一日游：持仓1天，且收益率<1%
        if holding_days == 1 and pnl_pct < 1.0:
            # 还要满足首日看起来很猛的条件
            # 条件：涨幅>1% 且 主力流入>100万
            if buy_pct > 1.0 and main_inflow > 100:
                one_day_trips.append({
                    'code': code,
                    'buy_date': buy_date,
                    'sell_date': sell_date,
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'buy_pct': buy_pct,
                    'sell_pnl_pct': pnl_pct,
                    'buy_amount': buy_amount,
                    'main_inflow': main_inflow,
                    'attack_score': buy_snapshot.get('attack_score', 0),
                    'risk_score': buy_snapshot.get('risk_score', 0)
                })

if one_day_trips:
    print(f"\n找到 {len(one_day_trips)} 个典型一日游案例:\n")
    for i, case in enumerate(one_day_trips, 1):
        print(f"案例 {i}: {case['code']}")
        print(f"  买入: {case['buy_date']} @ {case['buy_price']:.2f} ({case['buy_pct']:+.2f}%)")
        print(f"  卖出: {case['sell_date']} @ {case['sell_price']:.2f} ({case['sell_pnl_pct']:+.2f}%)")
        print(f"  成交额: {case['buy_amount']:.2f}亿")
        print(f"  主力流入: {case['main_inflow']:.1f}万")
        print(f"  Attack评分: {case['attack_score']:.1f}")
        print(f"  Risk评分: {case['risk_score']:.2f}")
        print()
else:
    print("\n没有找到典型的一日游案例")

print("="*80)