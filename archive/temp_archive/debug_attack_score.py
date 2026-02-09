"""调试为什么Attack评分全部是54.0"""
import json

def calculate_attack_intensity(stock_data: dict) -> float:
    """计算资金猛攻强度评分"""
    flow = stock_data.get('flow_data', {})
    price = stock_data.get('price_data', {})
    
    # 主力流入评分（100万=20分，400万=100分）
    main_inflow = flow.get('main_net_inflow', 0)
    flow_score = min(main_inflow / 100 * 20, 100)
    
    # 涨幅评分（5%=0分，10%=80分，15%+=100分）
    pct_chg = price.get('pct_chg', 0)
    if pct_chg < 5:
        pct_score = 0
    elif pct_chg < 10:
        pct_score = pct_chg * 16
    else:
        pct_score = 80 + (pct_chg - 10) * 10
    
    # 成交额评分（越小越容易推动）
    amount_yi = price.get('amount', 0) / 1e8  # 转换为亿
    if amount_yi < 0.05:
        amount_score = 100
    elif amount_yi < 0.1:
        amount_score = 80
    elif amount_yi < 0.3:
        amount_score = 50
    else:
        amount_score = 20
    
    # 综合评分（主力流入50% + 涨幅30% + 成交额20%）
    total_score = flow_score * 0.5 + pct_score * 0.3 + amount_score * 0.2
    
    return total_score, flow_score, pct_score, amount_score

# 从trade_details.json读取
with open('E:/MyQuantTool/data/backtest_results_real/trade_details.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print("Attack评分调试:")
print("="*80)

for trade in trades:
    snapshot = trade['buy_snapshot']
    main_inflow = snapshot['flow']['main_net_inflow']
    amount = snapshot['price']['amount']
    pct = snapshot['price']['pct_chg']
    
    attack, flow_score, pct_score, amount_score = calculate_attack_intensity(snapshot)
    
    print(f"\n{trade['code']} ({trade['buy_date']}):")
    print(f"  主力流入: {main_inflow/1e4:.1f}万")
    print(f"  成交额: {amount/1e8:.2f}亿")
    print(f"  涨幅: {pct:.2f}%")
    print(f"  流入评分: {flow_score:.1f}")
    print(f"  涨幅评分: {pct_score:.1f}")
    print(f"  成交评分: {amount_score:.1f}")
    print(f"  Attack评分: {attack:.1f} = {flow_score:.1f}*0.5 + {pct_score:.1f}*0.3 + {amount_score:.1f}*0.2")