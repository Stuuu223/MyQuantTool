"""
整合顽主杯数据与472只基础池
生成热点优先级列表
"""

import json
import requests
from pathlib import Path
from datetime import datetime

# ================= 配置 =================
WANZHU_API = 'https://bp3qvsy5v2.coze.site/api/stocks'
ACTIVE_STOCKS_FILE = Path(r'E:\MyQuantTool\config\active_stocks.json')
OUTPUT_FILE = Path(r'E:\MyQuantTool\config\hot_stocks_detail.json')
PROJECT_ROOT = Path(r'E:\MyQuantTool')

# ================= 函数 =================

def fetch_wanzhu_data():
    """获取顽主杯数据"""
    try:
        response = requests.get(WANZHU_API, timeout=10)
        return response.json()
    except Exception as e:
        print(f"❌ 获取顽主杯数据失败: {e}")
        return None

def load_active_stocks():
    """加载472只基础池"""
    with open(ACTIVE_STOCKS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_stock_code_from_name(stock_name):
    """通过股票名称获取代码（简化版）"""
    # 这里需要通过API查询，暂时返回None
    # 实际应该调用东财或Tushare的API
    return None

def analyze_sectors(wanzhu_data):
    """分析板块热度"""
    sector_stats = {}

    for stock in wanzhu_data.get('stocks', []):
        sectors = stock.get('sector', '').split('/')
        for sector in sectors:
            if sector:
                if sector not in sector_stats:
                    sector_stats[sector] = {
                        'count': 0,
                        'stocks': [],
                        'total_amount': 0
                    }
                sector_stats[sector]['count'] += 1
                sector_stats[sector]['stocks'].append(stock['stockName'])
                try:
                    sector_stats[sector]['total_amount'] += float(stock.get('holdingAmount', 0))
                except:
                    pass

    # 排序
    sorted_sectors = sorted(sector_stats.items(), key=lambda x: x[1]['count'], reverse=True)
    return sorted_sectors

def integrate_data():
    """整合数据"""
    print("=" * 60)
    print("📊 整合顽主杯数据与基础池")
    print("=" * 60)

    # 1. 获取顽主杯数据
    print("\n1️⃣  获取顽主杯数据...")
    wanzhu_data = fetch_wanzhu_data()
    if not wanzhu_data:
        print("❌ 无法获取顽主杯数据")
        return

    stocks_count = len(wanzhu_data.get('stocks', []))
    current_date = wanzhu_data.get('currentDate', '')
    print(f"   ✅ 获取成功！当前日期: {current_date}")
    print(f"   ✅ 股票数量: {stocks_count} 只")

    # 2. 加载基础池
    print("\n2️⃣  加载472只基础池...")
    active_stocks = load_active_stocks()
    print(f"   ✅ 加载成功！股票数量: {len(active_stocks)} 只")

    # 3. 分析板块热度
    print("\n3️⃣  分析板块热度...")
    sorted_sectors = analyze_sectors(wanzhu_data)
    print(f"   ✅ 发现 {len(sorted_sectors)} 个板块")

    print("\n   🔥 前10个热门板块:")
    for i, (sector, stats) in enumerate(sorted_sectors[:10]):
        print(f"      {i+1}. {sector}: {stats['count']}次, 持仓金额{stats['total_amount']:.2f}万")

    # 4. 生成整合数据
    print("\n4️⃣  生成整合数据...")

    integrated_data = {
        'date': current_date,
        'wanzhu_stocks_count': stocks_count,
        'active_stocks_count': len(active_stocks),
        'hot_sectors': [
            {
                'name': sector,
                'count': stats['count'],
                'top_stocks': stats['stocks'][:5],
                'total_amount': stats['total_amount']
            }
            for sector, stats in sorted_sectors[:10]
        ],
        'wanzhu_top_60': [],
        'integration_result': {
            'hot_priority_stocks': [],
            'missing_codes': []
        }
    }

    # 添加顽主杯前60只股票
    for stock in wanzhu_data.get('stocks', [])[:60]:
        integrated_data['wanzhu_top_60'].append({
            'rank': stock['rank'],
            'name': stock['stockName'],
            'sector': stock['sector'],
            'holder_count': stock.get('holderCount', ''),
            'amount': stock.get('holdingAmount', ''),
            'code': None  # 需要通过API查询
        })

    # 保存结果
    print("\n5️⃣  保存结果...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(integrated_data, f, ensure_ascii=False, indent=2)

    print(f"   ✅ 保存成功！")
    print(f"   📁 文件路径: {OUTPUT_FILE}")

    print("\n" + "=" * 60)
    print("✅ 整合完成！")
    print("=" * 60)
    print(f"\n📊 统计:")
    print(f"   - 顽主杯股票: {stocks_count} 只")
    print(f"   - 基础池股票: {len(active_stocks)} 只")
    print(f"   - 热门板块: {len(sorted_sectors)} 个")
    print(f"\n💡 下一步:")
    print(f"   1. 使用热点板块优化选股策略")
    print(f"   2. 用Tick数据回测验证策略")
    print(f"   3. 根据回测结果调整参数")

if __name__ == "__main__":
    integrate_data()
