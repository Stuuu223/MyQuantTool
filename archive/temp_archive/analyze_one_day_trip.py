"""深入分析一日游案例"""
import json
from datetime import datetime

# 分析000001.SZ的一日游案例
code = '000001.SZ'
buy_date = '20260205'
sell_date = '20260206'

print("="*80)
print(f"深度分析: {code} 典型一日游案例")
print("="*80)

# 加载买入日快照
with open(f'E:/MyQuantTool/data/rebuild_snapshots/full_market_snapshot_{buy_date}_rebuild.json', 'r', encoding='utf-8') as f:
    buy_snap = json.load(f)

# 加载卖出日快照
with open(f'E:/MyQuantTool/data/rebuild_snapshots/full_market_snapshot_{sell_date}_rebuild.json', 'r', encoding='utf-8') as f:
    sell_snap = json.load(f)

# 查找这只票在两天的数据
buy_stock = None
sell_stock = None

for stock in buy_snap['results']['opportunities']:
    if stock['code'] == code:
        buy_stock = stock
        break

for stock in sell_snap['results']['opportunities'] + sell_snap['results']['watchlist'] + sell_snap['results']['blacklist']:
    if stock['code'] == code:
        sell_stock = stock
        break

if not buy_stock or not sell_stock:
    print("❌ 数据不完整")
    exit()

print(f"\n【买入日: {buy_date}】")
print("-"*80)
print(f"价格: {buy_stock['price']['close']:.2f}元 ({buy_stock['price']['pct_chg']:+.2f}%)")
print(f"成交额: {buy_stock['price']['amount_yi']:.2f}亿")
print(f"主力净流入: {buy_stock['flow']['main_net_inflow_wan']:.1f}万")
print(f"Risk评分: {buy_stock['risk_score']:.2f}")
print(f"资金类型: {buy_stock['capital_type']}")
print(f"诱多信号: {buy_stock['trap_signals'] if buy_stock['trap_signals'] else '无'}")

print(f"\n【次日: {sell_date}】")
print("-"*80)
print(f"价格: {sell_stock['price']['close']:.2f}元 ({sell_stock['price']['pct_chg']:+.2f}%)")
print(f"成交额: {sell_stock['price']['amount_yi']:.2f}亿")
print(f"主力净流入: {sell_stock['flow']['main_net_inflow_wan']:.1f}万")
print(f"Risk评分: {sell_stock['risk_score']:.2f}")
print(f"资金类型: {sell_stock['capital_type']}")
print(f"诱多信号: {sell_stock['trap_signals'] if sell_stock['trap_signals'] else '无'}")
print(f"所属池子: {'机会池' if sell_stock in sell_snap['results']['opportunities'] else '观察池' if sell_stock in sell_snap['results']['watchlist'] else '黑名单'}")

# 计算变化
price_change = (sell_stock['price']['close'] - buy_stock['price']['close']) / buy_stock['price']['close'] * 100
amount_change = (sell_stock['price']['amount_yi'] - buy_stock['price']['amount_yi']) / buy_stock['price']['amount_yi'] * 100
inflow_change = sell_stock['flow']['main_net_inflow_wan'] - buy_stock['flow']['main_net_inflow_wan']

print(f"\n【变化分析】")
print("-"*80)
print(f"价格变化: {price_change:+.2f}%")
print(f"成交额变化: {amount_change:+.2f}%")
print(f"主力流入变化: {inflow_change:+.1f}万")

print(f"\n【一日游特征判断】")
print("-"*80)
features = []

# 特征1: 次日价格下跌或持平
if price_change <= 0:
    features.append(f"✅ 次日价格{'下跌' if price_change < 0 else '持平'} ({price_change:+.2f}%)")

# 特征2: 次日成交额缩量
if amount_change < -20:
    features.append(f"✅ 次日成交额缩量 ({amount_change:+.2f}%)")

# 特征3: 主力流出或大幅减少
if inflow_change < -500:
    features.append(f"✅ 主力大幅流出 ({inflow_change:+.1f}万)")
elif inflow_change < 0:
    features.append(f"⚠️  主力小幅流出 ({inflow_change:+.1f}万)")

# 特征4: 次日风险评分上升
if sell_stock['risk_score'] > buy_stock['risk_score']:
    features.append(f"✅ 风险评分上升 ({buy_stock['risk_score']:.2f} → {sell_stock['risk_score']:.2f})")

# 特征5: 次日被踢出机会池
if sell_stock not in sell_snap['results']['opportunities']:
    features.append(f"✅ 次日被踢出机会池")

if features:
    for feature in features:
        print(f"  {feature}")
    print(f"\n结论: 典型的一日游，首日{'猛攻' if buy_stock['price']['pct_chg'] > 2 else '温和攻击'}，次日资金撤离")
else:
    print(f"  未发现明显一日游特征")

print("="*80)