"""
顽主杯数据抓取脚本
从 https://bp3qvsy5v2.coze.site/api/stocks 获取历史榜单数据
"""
import requests
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

BASE_URL = 'https://bp3qvsy5v2.coze.site'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}


def load_stock_mapping(mapping_path: Path) -> Dict[str, str]:
    """从wanzhu_top_120.json加载名称到代码的映射"""
    if not mapping_path.exists():
        print(f"⚠️ 映射文件不存在: {mapping_path}")
        return {}
    
    with open(mapping_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    mapping = {}
    for item in data:
        name = item.get('name', '')
        code = item.get('code', '')
        if name and code:
            mapping[name] = code
    
    print(f"✅ 加载了 {len(mapping)} 条名称-代码映射")
    return mapping


def fetch_date_data(date_str: str) -> Optional[Dict]:
    """获取指定日期的榜单数据"""
    url = f'{BASE_URL}/api/stocks'
    params = {'date': date_str}
    
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"❌ 获取 {date_str} 数据失败: {e}")
        return None


def parse_stock_data(data: Dict, date_str: str, name_to_code: Dict[str, str]) -> List[Dict]:
    """解析股票数据为标准化格式"""
    records = []
    stocks = data.get('stocks', [])
    
    # 转换日期格式 20260213 -> 2025-02-13 (注意：API返回的是未来日期，实际应为2025年)
    # 根据分析，日期格式是YYYYMMDD，需要转换为YYYY-MM-DD
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    
    for stock in stocks:
        name = stock.get('stockName', '')
        code = name_to_code.get(name, '')  # 尝试从映射表获取代码
        
        record = {
            'date': formatted_date,
            'code': code,
            'name': name,
            'rank': stock.get('rank'),
            'rank_change': stock.get('rankChange'),
            'sector': stock.get('sector'),
            'holder_count': stock.get('holderCount'),
            'holder_count_change': stock.get('holderCountChange'),
            'holding_amount': stock.get('holdingAmount'),
            'amount_change': stock.get('amountChange'),
        }
        records.append(record)
    
    return records


def fetch_all_data(output_path: Path, mapping_path: Path):
    """抓取所有可用日期的数据"""
    print("=" * 60)
    print("📊 顽主杯数据抓取")
    print("=" * 60)
    
    # 1. 加载名称映射
    name_to_code = load_stock_mapping(mapping_path)
    
    # 2. 获取可用日期列表
    print("\n🌐 扫描历史数据范围...")
    
    # 基于探索结果：数据范围 20251117 到 20260213
    from datetime import datetime, timedelta
    start = datetime(2025, 11, 17)
    end = datetime(2026, 2, 13)
    
    available_dates = []
    current = start
    while current <= end:
        date_str = current.strftime('%Y%m%d')
        display = current.strftime('%Y-%m-%d')
        available_dates.append({'date': date_str, 'display': display, 'mode': 'full'})
        current += timedelta(days=1)
    
    print(f"✅ 扫描到 {len(available_dates)} 个交易日期 (2025-11-17 至 2026-02-13)")
    
    # 3. 遍历获取每日数据
    all_records = []
    unmatched_names = set()
    
    print("\n📥 开始抓取数据...")
    for date_info in available_dates:
        date_str = date_info['date']
        display = date_info['display']
        
        print(f"\n   抓取 {display}...", end=' ')
        data = fetch_date_data(date_str)
        
        if data and data.get('stocks'):
            stocks = data.get('stocks', [])
            records = parse_stock_data(data, date_str, name_to_code)
            all_records.extend(records)
            
            # 记录未匹配名称
            for record in records:
                if not record['code']:
                    unmatched_names.add(record['name'])
            
            print(f"✅ {len(records)} 只股票")
        else:
            print(f"❌ 无数据")
    
    # 4. 保存数据
    print(f"\n💾 保存数据到: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    df = pd.DataFrame(all_records)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    # 5. 输出统计
    print("\n" + "=" * 60)
    print("📈 抓取完成统计")
    print("=" * 60)
    print(f"总记录数: {len(all_records)}")
    print(f"交易日期: {len(available_dates)}")
    print(f"平均每日期: {len(all_records) // len(available_dates) if available_dates else 0} 只")
    print(f"代码映射成功: {len([r for r in all_records if r['code']])} / {len(all_records)}")
    
    if unmatched_names:
        print(f"\n⚠️ 未匹配代码的股票 ({len(unmatched_names)} 只):")
        for name in sorted(unmatched_names)[:10]:
            print(f"   - {name}")
        if len(unmatched_names) > 10:
            print(f"   ... 还有 {len(unmatched_names) - 10} 只")
    
    print(f"\n✅ 数据已保存: {output_path}")
    return df


def main():
    # 配置路径
    mapping_path = Path('config/wanzhu_top_120.json')
    output_path = Path('data/wanzhu_history_from_api.csv')
    
    try:
        df = fetch_all_data(output_path, mapping_path)
        print(f"\n🎯 数据预览:")
        print(df.head(10).to_string())
    except Exception as e:
        print(f"\n❌ 抓取失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
