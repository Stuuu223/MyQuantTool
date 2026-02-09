"""提取所有交易的详细信息到JSON文件"""
import json
import csv
from pathlib import Path
from datetime import datetime

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

def load_snapshot(trade_date: str, snapshot_dir: str) -> dict:
    """加载指定日期的快照"""
    # 尝试两种文件名格式
    possible_names = [
        f"{trade_date}.json",
        f"full_market_snapshot_{trade_date}_rebuild.json"
    ]
    
    for name in possible_names:
        snapshot_file = Path(snapshot_dir) / name
        if snapshot_file.exists():
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    return None

def find_stock_in_snapshot(snapshot: dict, code: str) -> dict:
    """在快照中查找股票数据"""
    if not snapshot:
        return None
    
    results = snapshot.get('results', {})
    for pool_name in ['opportunities', 'watchlist', 'blacklist']:
        pool = results.get(pool_name, [])
        for stock in pool:
            if stock['code'] == code:
                stock['pool'] = pool_name
                return stock
    return None

def extract_trade_details():
    """提取所有交易的详细信息"""
    snapshot_dir = "E:/MyQuantTool/data/rebuild_snapshots"
    trades_file = "E:/MyQuantTool/data/backtest_results_real/trades.csv"
    
    # 读取交易记录
    trades = []
    with open(trades_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append(row)
    
    # 按代码分组买卖对
    buy_trades = {}
    sell_trades = {}
    
    for trade in trades:
        code = trade['code']
        if trade['type'] == 'buy':
            buy_trades[code] = trade
        else:
            if code not in sell_trades:
                sell_trades[code] = []
            sell_trades[code].append(trade)
    
    # 提取详细信息
    trade_details = []
    
    for code, buy_trade in buy_trades.items():
        buy_date = buy_trade['date']
        buy_price = float(buy_trade['price'])
        
        # 获取买入时的快照数据
        snapshot = load_snapshot(buy_date, snapshot_dir)
        stock_data = find_stock_in_snapshot(snapshot, code)
        
        # 构建详细信息
        detail = {
            'code': code,
            'buy_date': buy_date,
            'buy_price': buy_price,
            'buy_snapshot': {},
            'sell_records': []
        }
        
        if stock_data:
            price_data = stock_data.get('price_data', {})
            flow_data = stock_data.get('flow_data', {})
            
            detail['buy_snapshot'] = {
                'pool': stock_data.get('pool', 'unknown'),
                'decision_tag': stock_data.get('decision_tag', None),
                'risk_score': stock_data.get('risk_score', 1.0),
                'trap_signals': stock_data.get('trap_signals', []),
                'capital_type': stock_data.get('capital_type', 'unknown'),
                'price': {
                    'close': price_data.get('close', 0),
                    'pct_chg': price_data.get('pct_chg', 0),
                    'amount': price_data.get('amount', 0),
                    'amount_yi': price_data.get('amount', 0) / 1e8,
                    'high': price_data.get('high', 0),
                    'low': price_data.get('low', 0),
                    'vol': price_data.get('vol', 0)
                },
                'flow': {
                    'main_net_inflow': flow_data.get('main_net_inflow', 0),
                    'main_net_inflow_wan': flow_data.get('main_net_inflow', 0) / 1e4,
                    'super_large_net': flow_data.get('super_large_net', 0),
                    'large_net': flow_data.get('large_net', 0),
                    'medium_net': flow_data.get('medium_net', 0),
                    'small_net': flow_data.get('small_net', 0)
                },
                'attack_score': calculate_attack_intensity(stock_data)
            }
        
        # 获取卖出记录
        if code in sell_trades:
            for sell_trade in sell_trades[code]:
                sell_price = float(sell_trade['price'])
                pnl = float(sell_trade.get('pnl', 0))
                pnl_pct = float(sell_trade.get('pnl_pct', 0))
                
                # 计算持仓天数
                buy_dt = datetime.strptime(buy_date, '%Y%m%d')
                sell_dt = datetime.strptime(sell_trade['date'], '%Y%m%d')
                holding_days = (sell_dt - buy_dt).days
                
                detail['sell_records'].append({
                    'date': sell_trade['date'],
                    'price': sell_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'holding_days': holding_days
                })
        
        trade_details.append(detail)
    
    # 按买入日期排序
    trade_details.sort(key=lambda x: x['buy_date'])
    
    # 保存到JSON
    output_file = "E:/MyQuantTool/data/backtest_results_real/trade_details.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(trade_details, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 交易详情已保存到: {output_file}")
    print(f"共提取 {len(trade_details)} 笔交易")
    
    # 打印摘要
    print(f"\n{'='*80}")
    print(f"交易摘要")
    print(f"{'='*80}")
    
    for trade in trade_details:
        print(f"\n{trade['code']} ({trade['buy_date']})")
        if trade['buy_snapshot']:
            print(f"  买入价: {trade['buy_price']:.2f}")
            print(f"  池子: {trade['buy_snapshot']['pool']}")
            print(f"  涨幅: {trade['buy_snapshot']['price']['pct_chg']:.2f}%")
            print(f"  主力流入: {trade['buy_snapshot']['flow']['main_net_inflow_wan']:.1f}万")
            print(f"  Attack评分: {trade['buy_snapshot']['attack_score']:.1f}")
            print(f"  Risk评分: {trade['buy_snapshot']['risk_score']:.2f}")
        
        for sell in trade['sell_records']:
            print(f"  卖出: {sell['date']}, {sell['price']:.2f}, {sell['pnl_pct']:+.2f}%, 持仓{sell['holding_days']}天")

if __name__ == '__main__':
    extract_trade_details()