"""
获取顽主杯热点股票的代码并补充Tick数据
"""

import json
import requests
from pathlib import Path
import time

# ================= 配置 =================
WANZHU_DATA_FILE = Path(r'E:\MyQuantTool\temp\wanzhu_cup_data.json')
ACTIVE_STOCKS_FILE = Path(r'E:\MyQuantTool\config\active_stocks.json')
OUTPUT_FILE = Path(r'E:\MyQuantTool\config\hot_stocks_codes.json')
PROJECT_ROOT = Path(r'E:\MyQuantTool')

# ================= 东财API =================
# 使用东财的搜索API获取股票代码
SEARCH_API = 'http://searchapi.eastmoney.com/api/suggest/get'

def get_stock_code_by_name(stock_name):
    """
    通过股票名称获取股票代码
    使用东财搜索API
    """
    try:
        params = {
            'input': stock_name,
            'type': '14',  # 股票类型
            'token': 'D43BF722C8E33BDC906FB84D85E326E8'
        }
        response = requests.get(SEARCH_API, params=params, timeout=5)
        data = response.json()

        if data.get('QuotationCodeTable'):
            # 取第一个结果
            result = data['QuotationCodeTable'][0]
            return result['Code']
        return None
    except Exception as e:
        print(f"  ⚠️  查询 {stock_name} 失败: {e}")
        return None

def fetch_wanzhu_top_60():
    """获取顽主杯前60只股票"""
    with open(WANZHU_DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('stocks', [])[:60]

def load_active_stocks():
    """加载472只基础池"""
    with open(ACTIVE_STOCKS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def convert_stocks_to_codes():
    """转换股票名称为代码"""
    print("=" * 60)
    print("📋 转换顽主杯热点股票为代码")
    print("=" * 60)

    # 1. 获取顽主杯前60只股票
    print("\n1️⃣  获取顽主杯前60只股票...")
    wanzhu_stocks = fetch_wanzhu_top_60()
    print(f"   ✅ 获取 {len(wanzhu_stocks)} 只股票")

    # 2. 加载基础池
    print("\n2️⃣  加载472只基础池...")
    active_stocks = load_active_stocks()
    active_set = set(active_stocks)
    print(f"   ✅ 基础池包含 {len(active_stocks)} 只股票")

    # 3. 转换为代码
    print("\n3️⃣  转换股票代码...")
    result = {
        'date': '',
        'total': 0,
        'in_pool': 0,
        'missing': 0,
        'stocks': []
    }

    for i, stock in enumerate(wanzhu_stocks):
        stock_name = stock['stockName']
        rank = stock['rank']
        sector = stock.get('sector', '')

        # 获取代码
        code = get_stock_code_by_name(stock_name)
        if not code:
            print(f"  [{i+1}/60] ❌ {stock_name} 未找到")
            continue

        # 检查是否在基础池中
        in_pool = code in active_set

        result['stocks'].append({
            'rank': rank,
            'name': stock_name,
            'code': code,
            'sector': sector,
            'in_pool': in_pool,
            'holding_amount': stock.get('holdingAmount', '')
        })

        status = '✓ 在基础池' if in_pool else '✗ 缺失'
        print(f"  [{i+1}/60] {code} {stock_name} {status}")

        if in_pool:
            result['in_pool'] += 1
        else:
            result['missing'] += 1

        result['total'] += 1

        # 限速：每查询一个暂停0.1秒
        time.sleep(0.1)

    # 4. 保存结果
    print("\n4️⃣  保存结果...")
    result['date'] = json.load(open(WANZHU_DATA_FILE, 'r', encoding='utf-8')).get('currentDate', '')

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"   ✅ 保存成功！")
    print(f"   📁 文件路径: {OUTPUT_FILE}")

    print("\n" + "=" * 60)
    print("✅ 转换完成！")
    print("=" * 60)
    print(f"\n📊 统计:")
    print(f"   - 成功转换: {result['total']} 只")
    print(f"   - 在基础池中: {result['in_pool']} 只")
    print(f"   - 缺失: {result['missing']} 只")

    if result['missing'] > 0:
        print(f"\n📋 需要下载Tick数据的股票:")
        missing_stocks = [s for s in result['stocks'] if not s['in_pool']]
        for stock in missing_stocks[:10]:
            print(f"   - {stock['code']} {stock['name']} ({stock['sector']})")
        if len(missing_stocks) > 10:
            print(f"   ... 还有 {len(missing_stocks) - 10} 只")

    return result

if __name__ == "__main__":
    convert_stocks_to_codes()