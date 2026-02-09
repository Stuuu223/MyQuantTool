"""分析快照数据中的买入信号分布"""
import json
import os
from pathlib import Path

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
    amount = price.get('amount', 0) / 1e8  # 转换为亿
    if amount < 0.05:
        amount_score = 100
    elif amount < 0.1:
        amount_score = 80
    elif amount < 0.3:
        amount_score = 50
    else:
        amount_score = 20
    
    # 综合评分（主力流入50% + 涨幅30% + 成交额20%）
    total_score = flow_score * 0.5 + pct_score * 0.3 + amount_score * 0.2
    return total_score

def analyze_snapshot(snapshot_file: str):
    """分析单个快照"""
    with open(snapshot_file, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)
    
    results = snapshot.get('results', {})
    opportunities = results.get('opportunities', [])
    watchlist = results.get('watchlist', [])
    blacklist = results.get('blacklist', [])
    
    trade_date = snapshot.get('trade_date', 'unknown')
    
    print(f"\n{'='*60}")
    print(f"快照日期: {trade_date}")
    print(f"{'='*60}")
    
    all_stocks = opportunities + watchlist + blacklist
    
    # 统计不同条件的通过率
    total = len(all_stocks)
    high_attack = 0  # attack_score >= 30
    low_risk = 0     # risk_score < 0.7
    both_ok = 0      # 同时满足两个条件
    
    # 按池子分类统计
    pool_stats = {
        'opportunities': {'total': len(opportunities), 'high_attack': 0, 'low_risk': 0, 'both_ok': 0},
        'watchlist': {'total': len(watchlist), 'high_attack': 0, 'low_risk': 0, 'both_ok': 0},
        'blacklist': {'total': len(blacklist), 'high_attack': 0, 'low_risk': 0, 'both_ok': 0}
    }
    
    for stock in all_stocks:
        attack_score = calculate_attack_intensity(stock)
        risk_score = stock.get('risk_score', 1.0)
        
        if attack_score >= 30:
            high_attack += 1
        
        if risk_score < 0.7:
            low_risk += 1
        
        if attack_score >= 30 and risk_score < 0.7:
            both_ok += 1
        
        # 按池子分类
        if stock in opportunities:
            pool_stats['opportunities']['high_attack'] += 1 if attack_score >= 30 else 0
            pool_stats['opportunities']['low_risk'] += 1 if risk_score < 0.7 else 0
            pool_stats['opportunities']['both_ok'] += 1 if (attack_score >= 30 and risk_score < 0.7) else 0
        elif stock in watchlist:
            pool_stats['watchlist']['high_attack'] += 1 if attack_score >= 30 else 0
            pool_stats['watchlist']['low_risk'] += 1 if risk_score < 0.7 else 0
            pool_stats['watchlist']['both_ok'] += 1 if (attack_score >= 30 and risk_score < 0.7) else 0
        elif stock in blacklist:
            pool_stats['blacklist']['high_attack'] += 1 if attack_score >= 30 else 0
            pool_stats['blacklist']['low_risk'] += 1 if risk_score < 0.7 else 0
            pool_stats['blacklist']['both_ok'] += 1 if (attack_score >= 30 and risk_score < 0.7) else 0
    
    print(f"\n总体统计:")
    print(f"  总票数: {total}")
    print(f"  attack_score >= 30: {high_attack} ({high_attack/total*100:.1f}%)")
    print(f"  risk_score < 0.7: {low_risk} ({low_risk/total*100:.1f}%)")
    print(f"  同时满足: {both_ok} ({both_ok/total*100:.1f}%)")
    
    print(f"\n按池子分类:")
    for pool_name, stats in pool_stats.items():
        print(f"\n  {pool_name}:")
        print(f"    总票数: {stats['total']}")
        print(f"    attack_score >= 30: {stats['high_attack']} ({stats['high_attack']/stats['total']*100 if stats['total'] > 0 else 0:.1f}%)")
        print(f"    risk_score < 0.7: {stats['low_risk']} ({stats['low_risk']/stats['total']*100 if stats['total'] > 0 else 0:.1f}%)")
        print(f"    同时满足: {stats['both_ok']} ({stats['both_ok']/stats['total']*100 if stats['total'] > 0 else 0:.1f}%)")
    
    # 显示一些示例数据
    print(f"\n示例数据（前5个同时满足条件的票）:")
    count = 0
    for stock in all_stocks:
        attack_score = calculate_attack_intensity(stock)
        risk_score = stock.get('risk_score', 1.0)
        
        if attack_score >= 30 and risk_score < 0.7:
            print(f"  {stock['code']}: attack={attack_score:.1f}, risk={risk_score:.2f}, main_inflow={stock.get('flow_data', {}).get('main_net_inflow', 0)/1e4:.1f}万")
            count += 1
            if count >= 5:
                break
    
    # 显示一些不满足条件的票
    print(f"\n不满足条件的票示例（前5个）:")
    count = 0
    for stock in all_stocks:
        attack_score = calculate_attack_intensity(stock)
        risk_score = stock.get('risk_score', 1.0)
        
        if not (attack_score >= 30 and risk_score < 0.7):
            print(f"  {stock['code']}: attack={attack_score:.1f}, risk={risk_score:.2f}, main_inflow={stock.get('flow_data', {}).get('main_net_inflow', 0)/1e4:.1f}万")
            count += 1
            if count >= 5:
                break

# 分析所有快照
snapshot_dir = Path("E:/MyQuantTool/data/rebuild_snapshots")
snapshot_files = sorted(snapshot_dir.glob("*.json"), key=lambda x: x.name)

print(f"找到 {len(snapshot_files)} 个快照文件")

# 分析前3个快照
for i, snapshot_file in enumerate(snapshot_files[:3]):
    analyze_snapshot(str(snapshot_file))