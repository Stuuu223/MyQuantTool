"""检查资金流数据的单位"""
import json

# 读取快照
with open('E:/MyQuantTool/data/rebuild_snapshots/full_market_snapshot_20260109_rebuild.json', 'r', encoding='utf-8') as f:
    snapshot = json.load(f)

# 查看第一只机会池股票
stock = snapshot['results']['opportunities'][0]

print("="*60)
print("资金流数据检查")
print("="*60)
print(f"代码: {stock['code']}")
print(f"主力净流入原始值: {stock['flow_data']['main_net_inflow']:,} 元")
print(f"主力净流入(万): {stock['flow_data']['main_net_inflow']/1e4:.1f} 万")
print(f"成交额: {stock['price_data']['amount']:,} 元")
print(f"成交额(亿): {stock['price_data']['amount']/1e8:.4f} 亿")
print(f"涨幅: {stock['price_data']['pct_chg']:.2f}%")
print("="*60)

# 检查数据来源
flow_records = stock['flow_data'].get('records', [])
if flow_records:
    latest = flow_records[0]
    print(f"\n最新资金流记录: {latest['date']}")
    print(f"  主力净流入: {latest['main_net_inflow']:,} 元 = {latest['main_net_inflow']/1e4:.1f} 万")
    print(f"  超大单净流入: {latest['super_large_net']:,} 元 = {latest['super_large_net']/1e4:.1f} 万")
    print(f"  大单净流入: {latest['large_net']:,} 元 = {latest['large_net']/1e4:.1f} 万")
    print(f"  中单净流入: {latest['medium_net']:,} 元 = {latest['medium_net']/1e4:.1f} 万")
    print(f"  小单净流入: {latest['small_net']:,} 元 = {latest['small_net']/1e4:.1f} 万")

# 检查几只不同市值的票
print("\n" + "="*60)
print("不同股票的资金流对比")
print("="*60)

for i, stock in enumerate(snapshot['results']['opportunities'][:5]):
    main_inflow_wan = stock['flow_data']['main_net_inflow'] / 1e4
    amount_yi = stock['price_data']['amount'] / 1e8
    print(f"{i+1}. {stock['code']}: 主力流入 {main_inflow_wan:.1f}万, 成交额 {amount_yi:.4f}亿, 涨幅 {stock['price_data']['pct_chg']:.2f}%")