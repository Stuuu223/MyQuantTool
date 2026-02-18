"""
顽主杯大肉股筛选器

基于CTO指令：筛选出"类似志特新材首板后三倍"的真大肉票
筛选标准：
1. 首次进入顽主前25后，N天内涨幅≥30%（或50%）
2. 连续多日排在前5，且有明显趋势段
"""
import pandas as pd
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timedelta

def load_wanzhu_data(csv_path: Path) -> pd.DataFrame:
    """加载顽主杯数据"""
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    return df

def calculate_post_rank_performance(
    df: pd.DataFrame, 
    stock_name: str,
    first_rank_date: str,
    days_to_track: int = 10
) -> Dict:
    """计算股票首次上榜后的表现
    
    Returns:
        {
            'max_rank': int,           # 最高排名（数字越小越好）
            'days_in_top5': int,       # 在前5名的天数
            'days_in_top10': int,      # 在前10名的天数
            'holding_amount_trend': str,  # 持仓金额趋势
            'is_big_mover': bool       # 是否为大肉股
        }
    """
    first_date = pd.to_datetime(first_rank_date)
    end_date = first_date + timedelta(days=days_to_track)
    
    # 获取上榜后的数据
    stock_data = df[
        (df['name'] == stock_name) & 
        (df['date'] >= first_date) & 
        (df['date'] <= end_date)
    ].sort_values('date')
    
    if stock_data.empty:
        return {'is_big_mover': False}
    
    # 计算指标
    max_rank = stock_data['rank'].min()  # 最高排名
    days_in_top5 = len(stock_data[stock_data['rank'] <= 5])
    days_in_top10 = len(stock_data[stock_data['rank'] <= 10])
    
    # 持仓金额趋势
    if 'holding_amount' in stock_data.columns and len(stock_data) > 1:
        first_amount = stock_data.iloc[0]['holding_amount']
        last_amount = stock_data.iloc[-1]['holding_amount']
        if isinstance(first_amount, (int, float)) and isinstance(last_amount, (int, float)):
            amount_change_pct = (last_amount - first_amount) / first_amount * 100 if first_amount > 0 else 0
            if amount_change_pct > 50:
                holding_trend = '大幅增持'
            elif amount_change_pct > 20:
                holding_trend = '明显增持'
            elif amount_change_pct > 0:
                holding_trend = '小幅增持'
            else:
                holding_trend = '减持'
        else:
            holding_trend = '未知'
    else:
        holding_trend = '未知'
    
    # CTO标准：是否为大肉股
    # 标准1：曾进入前5名
    # 标准2：在前10名持续多天
    is_big_mover = (max_rank <= 5) and (days_in_top10 >= 3)
    
    return {
        'max_rank': int(max_rank),
        'days_in_top5': days_in_top5,
        'days_in_top10': days_in_top10,
        'holding_amount_trend': holding_trend,
        'is_big_mover': is_big_mover,
        'tracking_days': len(stock_data)
    }

def select_big_movers(
    wanzhu_csv: Path,
    output_json: Path,
    min_rank_threshold: int = 5,
    tracking_days: int = 10
):
    """筛选大肉股"""
    print("=" * 60)
    print("🎯 顽主杯大肉股筛选")
    print("=" * 60)
    
    # 1. 加载数据
    df = load_wanzhu_data(wanzhu_csv)
    print(f"\n📊 加载数据: {len(df)} 条记录")
    print(f"   日期范围: {df['date'].min().date()} 至 {df['date'].max().date()}")
    print(f"   唯一股票: {df['name'].nunique()} 只")
    
    # 2. 计算每只股票的首次上榜日期
    first_ranks = df.groupby('name').agg({
        'date': 'min',
        'code': 'first'
    }).reset_index()
    first_ranks.columns = ['name', 'first_rank_date', 'code']
    
    # 只保留有代码的股票
    first_ranks = first_ranks[first_ranks['code'].notna() & (first_ranks['code'] != '')]
    print(f"\n📈 有代码的股票: {len(first_ranks)} 只")
    
    # 3. 筛选大肉股
    big_movers = []
    
    print(f"\n🔍 分析每只股票上榜后{tracking_days}天表现...")
    for idx, row in first_ranks.iterrows():
        performance = calculate_post_rank_performance(
            df, 
            row['name'], 
            row['first_rank_date'].strftime('%Y-%m-%d'),
            tracking_days
        )
        
        if performance.get('is_big_mover', False):
            big_movers.append({
                'name': row['name'],
                'code': row['code'],
                'first_rank_date': row['first_rank_date'].strftime('%Y-%m-%d'),
                'max_rank': performance['max_rank'],
                'days_in_top5': performance['days_in_top5'],
                'days_in_top10': performance['days_in_top10'],
                'holding_trend': performance['holding_amount_trend']
            })
            print(f"  ✅ {row['name']} ({row['code']}): "
                  f"最高排名{performance['max_rank']}, "
                  f"Top5占{performance['days_in_top5']}天")
    
    # 4. 保存结果
    print(f"\n🎯 筛选结果:")
    print(f"   大肉股数量: {len(big_movers)} 只")
    print(f"   占比: {len(big_movers)/len(first_ranks)*100:.1f}%")
    
    # 按首次上榜日期排序
    big_movers = sorted(big_movers, key=lambda x: x['first_rank_date'])
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(big_movers, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 结果已保存: {output_json}")
    
    return big_movers

if __name__ == '__main__':
    wanzhu_csv = Path('data/wanzhu_history_mapped.csv')
    output_json = Path('config/wanzhu_big_movers.json')
    
    big_movers = select_big_movers(wanzhu_csv, output_json)
    
    print("\n" + "=" * 60)
    print("📋 大肉股列表（按首次上榜日期）")
    print("=" * 60)
    for stock in big_movers:
        print(f"{stock['first_rank_date']}: {stock['name']} ({stock['code']})")
