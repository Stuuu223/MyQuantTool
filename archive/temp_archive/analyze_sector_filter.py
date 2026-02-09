"""板块热度过滤 + BAND_2/BAND_3分析"""
import json
import os
from collections import Counter
from datetime import datetime, timedelta

snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'
sector_file = 'E:/MyQuantTool/data/stock_sector_map.json'

# 加载板块数据
with open(sector_file, 'r', encoding='utf-8') as f:
    sector_data = json.load(f)

print("="*80)
print("板块热度过滤 + BAND_2/BAND_3分析")
print("="*80)

# 计算每日行业热度
def calculate_daily_sector_heat(snapshot):
    """计算当日行业热度（平均涨幅）"""
    sector_pct_sums = {}
    sector_counts = {}

    # 检查所有股票
    all_stocks = snapshot['results']['opportunities'] + snapshot['results']['watchlist'] + snapshot['results']['blacklist']

    for stock in all_stocks:
        code = stock['code']
        code_6digit = code.split('.')[0][-6:]

        # 获取行业
        if code_6digit in sector_data:
            industry = sector_data[code_6digit].get('industry', '未知')
        else:
            industry = '未知'

        pct_chg = stock['price_data']['pct_chg']

        if industry not in sector_pct_sums:
            sector_pct_sums[industry] = 0
            sector_counts[industry] = 0

        sector_pct_sums[industry] += pct_chg
        sector_counts[industry] += 1

    # 计算平均涨幅
    sector_heat = {}
    for industry in sector_pct_sums:
        if sector_counts[industry] > 0:
            sector_heat[industry] = sector_pct_sums[industry] / sector_counts[industry]

    return sector_heat

# 识别热点行业（涨幅前30%）
def get_hot_sectors(sector_heat, top_percent=0.3):
    """获取热点行业（涨幅前30%）"""
    if not sector_heat:
        return []

    # 排序
    sorted_sectors = sorted(sector_heat.items(), key=lambda x: x[1], reverse=True)

    # 取前30%
    top_count = max(1, int(len(sorted_sectors) * top_percent))
    hot_sectors = set([item[0] for item in sorted_sectors[:top_count]])

    return hot_sectors

# 收集数据
all_band_2 = []
all_band_3 = []
hot_band_2 = []
hot_band_3 = []

for filename in sorted(os.listdir(snapshot_dir)):
    if not filename.startswith('full_market_snapshot_') or not filename.endswith('_rebuild.json'):
        continue

    filepath = os.path.join(snapshot_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    trade_date = snapshot['trade_date']

    # 计算当日行业热度
    sector_heat = calculate_daily_sector_heat(snapshot)
    hot_sectors = get_hot_sectors(sector_heat, top_percent=0.3)

    # 检查BAND_2/BAND_3样本
    all_stocks = snapshot['results']['opportunities'] + snapshot['results']['watchlist']

    for stock in all_stocks:
        momentum_band = stock.get('momentum_band', 'UNKNOWN')
        code = stock['code']
        pct_chg = stock['price_data']['pct_chg']
        close_price = stock['price_data']['close']
        main_net_inflow = stock['flow_data']['main_net_inflow']
        daily_amount = stock['price_data']['amount']
        inflow_to_amount = (main_net_inflow / daily_amount) if daily_amount > 0 else 0

        if momentum_band not in ['BAND_2', 'BAND_3']:
            continue

        # 获取行业
        code_6digit = code.split('.')[0][-6:]
        industry = sector_data.get(code_6digit, {}).get('industry', '未知')
        is_hot_sector = industry in hot_sectors

        data = {
            'code': code,
            'date': trade_date,
            'pct': pct_chg,
            'ratio': inflow_to_amount,
            'price': close_price,
            'industry': industry,
            'is_hot_sector': is_hot_sector
        }

        # 保存所有样本
        if momentum_band == 'BAND_2':
            all_band_2.append(data)
            if is_hot_sector:
                hot_band_2.append(data)
        elif momentum_band == 'BAND_3':
            all_band_3.append(data)
            if is_hot_sector:
                hot_band_3.append(data)

print(f"\nBAND_2 样本统计:")
print(f"  总样本: {len(all_band_2)}")
print(f"  热点行业样本: {len(hot_band_2)} ({len(hot_band_2)/len(all_band_2)*100:.1f}%)")

print(f"\nBAND_3 样本统计:")
print(f"  总样本: {len(all_band_3)}")
print(f"  热点行业样本: {len(hot_band_3)} ({len(hot_band_3)/len(all_band_3)*100:.1f}%)")

# 分析次日表现
def analyze_next_day(samples, name):
    if not samples:
        print(f"\n{name}: 无样本")
        return None

    limit_up = 0
    profit_count = 0
    loss_count = 0
    total_pnl = 0
    valid_samples = 0

    for s in samples:
        code = s['code']
        date = s['date']
        price = s['price']

        # 查找次日数据
        next_date = (datetime.strptime(date, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
        next_file = f'{snapshot_dir}/full_market_snapshot_{next_date}_rebuild.json'

        if os.path.exists(next_file):
            with open(next_file, 'r', encoding='utf-8') as f:
                next_snapshot = json.load(f)

            # 查找股票
            next_data = None
            for pool in ['opportunities', 'watchlist', 'blacklist']:
                for stock in next_snapshot['results'][pool]:
                    if stock['code'] == code:
                        next_data = stock
                        break
                if next_data:
                    break

            if next_data:
                next_pct = next_data['price_data']['pct_chg']
                next_price = next_data['price_data']['close']
                pnl = (next_price - price) / price * 100

                is_limit_up = next_pct >= 9.8
                valid_samples += 1

                if is_limit_up:
                    limit_up += 1
                if pnl > 0.5:
                    profit_count += 1
                elif pnl < -0.5:
                    loss_count += 1
                total_pnl += pnl

    if valid_samples > 0:
        print(f"\n{name}:")
        print(f"  有效样本: {valid_samples}")
        print(f"  涨停率: {limit_up}/{valid_samples} ({limit_up/valid_samples*100:.1f}%)")
        print(f"  盈利率: {profit_count}/{valid_samples} ({profit_count/valid_samples*100:.1f}%)")
        print(f"  亏损率: {loss_count}/{valid_samples} ({loss_count/valid_samples*100:.1f}%)")
        print(f"  平均收益: {total_pnl/valid_samples:+.2f}%")

        return {
            'valid_samples': valid_samples,
            'limit_up_rate': limit_up/valid_samples*100,
            'profit_rate': profit_count/valid_samples*100,
            'avg_pnl': total_pnl/valid_samples
        }
    else:
        print(f"\n{name}: 无有效次日数据")
        return None

# 对比分析
print("\n" + "="*80)
print("BAND_2 板块过滤效果对比")
print("="*80)
print("过滤前（所有BAND_2）:")
result_band_2_all = analyze_next_day(all_band_2, "  所有BAND_2")

print("\n过滤后（热点行业BAND_2）:")
result_band_2_hot = analyze_next_day(hot_band_2, "  热点行业BAND_2")

print("\n" + "="*80)
print("BAND_3 板块过滤效果对比")
print("="*80)
print("过滤前（所有BAND_3）:")
result_band_3_all = analyze_next_day(all_band_3, "  所有BAND_3")

print("\n过滤后（热点行业BAND_3）:")
result_band_3_hot = analyze_next_day(hot_band_3, "  热点行业BAND_3")

# 总结
print("\n" + "="*80)
print("总结")
print("="*80)
if result_band_2_all and result_band_2_hot:
    print(f"BAND_2 板块过滤效果:")
    print(f"  涨停率: {result_band_2_all['limit_up_rate']:.1f}% → {result_band_2_hot['limit_up_rate']:.1f}%")
    print(f"  平均收益: {result_band_2_all['avg_pnl']:+.2f}% → {result_band_2_hot['avg_pnl']:+.2f}%")

if result_band_3_all and result_band_3_hot:
    print(f"\nBAND_3 板块过滤效果:")
    print(f"  涨停率: {result_band_3_all['limit_up_rate']:.1f}% → {result_band_3_hot['limit_up_rate']:.1f}%")
    print(f"  平均收益: {result_band_3_all['avg_pnl']:+.2f}% → {result_band_3_hot['avg_pnl']:+.2f}%")

print("="*80)