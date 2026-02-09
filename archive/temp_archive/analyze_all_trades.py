"""分析所有交易，找出相对成功的案例"""
import json

# 加载交易记录
with open('E:/MyQuantTool/data/backtest_results_real/trade_details.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print("="*80)
print("分析所有交易案例")
print("="*80)

for i, trade in enumerate(trades, 1):
    code = trade['code']
    buy_date = trade['buy_date']
    buy_snapshot = trade['buy_snapshot']
    sell_records = trade['sell_records']
    
    # 找到最成功的一笔卖出
    best_sell = max(sell_records, key=lambda x: x['pnl_pct'])
    
    # 数据提取
    main_inflow = buy_snapshot['flow']['main_net_inflow_wan']
    buy_pct = buy_snapshot['price']['pct_chg']
    risk_score = buy_snapshot['risk_score']
    pnl_pct = best_sell['pnl_pct']
    holding_days = best_sell['holding_days']
    
    print(f"\n案例 {i}: {code}")
    print(f"  买入: {buy_date} @ {buy_snapshot['price']['close']:.2f} ({buy_pct:+.2f}%)")
    print(f"  卖出: {best_sell['date']} @ {best_sell['price']:.2f} ({pnl_pct:+.2f}%)")
    print(f"  持仓: {holding_days}天")
    print(f"  主力流入: {main_inflow:.1f}万")
    print(f"  Risk: {risk_score:.2f}")
    
    # 判断特征
    features = []
    if main_inflow >= 1000:
        features.append("✅ 资金强")
    else:
        features.append("❌ 资金弱")
    
    if pnl_pct >= 3:
        features.append("✅ 收益好")
    elif pnl_pct >= 0:
        features.append("⚠️  小赚")
    else:
        features.append("❌ 亏损")
    
    if holding_days <= 5:
        features.append("✅ 持仓短")
    else:
        features.append("⚠️  持仓长")
    
    print(f"  特征: {' '.join(features)}")

print("\n" + "="*80)