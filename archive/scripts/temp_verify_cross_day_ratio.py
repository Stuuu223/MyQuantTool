"""
验证跨日ratio计算
"""
import json

# 读取equity_info数据
with open("data/equity_info_tushare.json", 'r', encoding='utf-8') as f:
    equity_data = json.load(f)

# 读取2026-02-05快照
with open("data/scan_results/2026-02-05_premarket.json", 'r', encoding='utf-8') as f:
    snapshot_20260205 = json.load(f)

# 读取2026-02-06快照
with open("data/scan_results/2026-02-06_094521_intraday.json", 'r', encoding='utf-8') as f:
    snapshot_20260206 = json.load(f)

# 从快照中提取主力净流入数据
def extract_main_net_inflow(snapshot, code):
    """从快照中提取主力净流入"""
    for pool in ['opportunities', 'watchlist', 'blacklist']:
        stocks = snapshot["results"].get(pool, [])
        for stock in stocks:
            if stock.get('code') == code:
                flow_data = stock.get('flow_data', {})
                records = flow_data.get('records', [])
                if records:
                    # 取最新一条记录
                    latest_record = records[0]
                    return latest_record.get('main_net_inflow', 0)
    return None

# 测试股票
test_stocks = ["000592.SZ", "601869.SH", "603607.SH"]

print("=" * 70)
print("验证跨日ratio计算")
print("=" * 70)

for stock in test_stocks:
    print(f"\n📊 {stock}:")
    
    # 2026-02-05
    main_net_20260205 = extract_main_net_inflow(snapshot_20260205, stock)
    float_mv_20260205 = equity_data["data"].get("20260205", {}).get(stock, {}).get("float_mv", 0)
    ratio_20260205 = (main_net_20260205 / float_mv_20260205 * 100) if (main_net_20260205 is not None and float_mv_20260205 > 0) else None
    
    print(f"  2026-02-05:")
    print(f"    主力净流入: {main_net_20260205/1e4:.2f} 万" if main_net_20260205 else "    主力净流入: 未找到")
    print(f"    流通市值: {float_mv_20260205/1e8:.2f} 亿" if float_mv_20260205 > 0 else "    流通市值: 未找到")
    print(f"    ratio: {ratio_20260205:.4f}%" if ratio_20260205 else "    ratio: 无法计算")
    
    # 2026-02-06
    main_net_20260206 = extract_main_net_inflow(snapshot_20260206, stock)
    float_mv_20260206 = equity_data["data"].get("20260206", {}).get(stock, {}).get("float_mv", 0)
    ratio_20260206 = (main_net_20260206 / float_mv_20260206 * 100) if (main_net_20260206 is not None and float_mv_20260206 > 0) else None
    
    print(f"  2026-02-06:")
    print(f"    主力净流入: {main_net_20260206/1e4:.2f} 万" if main_net_20260206 else "    主力净流入: 未找到")
    print(f"    流通市值: {float_mv_20260206/1e8:.2f} 亿" if float_mv_20260206 > 0 else "    流通市值: 未找到")
    print(f"    ratio: {ratio_20260206:.4f}%" if ratio_20260206 else "    ratio: 无法计算")
    
    # ratio变化
    if ratio_20260205 and ratio_20260206:
        ratio_change = ratio_20260206 - ratio_20260205
        print(f"  ratio变化: {ratio_change:+.4f}%")

print("\n" + "=" * 70)
print("跨日ratio计算验证完成")
print("=" * 70)