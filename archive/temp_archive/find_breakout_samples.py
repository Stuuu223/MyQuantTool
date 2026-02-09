"""从回测结果中找出典型的"起涨点"案例"""
import json

# 加载交易记录
with open('E:/MyQuantTool/data/backtest_results_real/trade_details.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print("="*80)
print("查找典型的'起涨点'案例")
print("="*80)

# 典型"起涨点"的特征：
# 1. 买入日：首次放量突破
# 2. 资金强度：≥1000万
# 3. 后续：有连续上涨（不是一日游）
# 4. 收益率：≥3%

breakout_samples = []

for trade in trades:
    code = trade['code']
    buy_date = trade['buy_date']
    buy_snapshot = trade['buy_snapshot']
    sell_records = trade['sell_records']

    # 找到最成功的一笔卖出
    best_sell = max(sell_records, key=lambda x: x['pnl_pct'])

    # 起涨点特征：
    # 1. 首日资金强度≥1000万
    main_inflow = buy_snapshot['flow']['main_net_inflow_wan']
    
    # 2. 涨幅适中（不是一字板，也不是微涨）
    buy_pct = buy_snapshot['price']['pct_chg']
    
    # 3. 风险可控
    risk_score = buy_snapshot['risk_score']
    
    # 4. 收益率不错（≥3%）
    pnl_pct = best_sell['pnl_pct']
    
    # 5. 持仓时间合理（1-5天，太快是运气，太慢是磨叽）
    holding_days = best_sell['holding_days']
    
    # 判断是否为典型起涨点
    if (main_inflow >= 1000 and 
        1.0 <= buy_pct <= 5.0 and 
        risk_score <= 0.3 and 
        pnl_pct >= 3.0 and 
        1 <= holding_days <= 5):
        
        breakout_samples.append({
            'code': code,
            'buy_date': buy_date,
            'buy_price': buy_snapshot['price']['close'],
            'buy_pct': buy_pct,
            'main_inflow': main_inflow,
            'buy_amount': buy_snapshot['price']['amount_yi'],
            'risk_score': risk_score,
            'attack_score': buy_snapshot.get('attack_score', 0),
            'sell_date': best_sell['date'],
            'sell_price': best_sell['price'],
            'pnl_pct': pnl_pct,
            'holding_days': holding_days
        })

if breakout_samples:
    print(f"\n找到 {len(breakout_samples)} 个典型'起涨点'案例:\n")
    
    for i, sample in enumerate(breakout_samples, 1):
        print(f"案例 {i}: {sample['code']}")
        print(f"  买入: {sample['buy_date']} @ {sample['buy_price']:.2f} ({sample['buy_pct']:+.2f}%)")
        print(f"  卖出: {sample['sell_date']} @ {sample['sell_price']:.2f} ({sample['pnl_pct']:+.2f}%)")
        print(f"  持仓: {sample['holding_days']}天")
        print(f"  成交额: {sample['buy_amount']:.2f}亿")
        print(f"  主力流入: {sample['main_inflow']:.1f}万")
        print(f"  Attack: {sample['attack_score']:.1f}, Risk: {sample['risk_score']:.2f}")
        print()
else:
    print("\n没有找到典型的'起涨点'案例")

print("="*80)