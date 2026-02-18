#!/usr/bin/env python3
"""
顽主杯数据采集 - 快速方案
直接在服务器上运行，通过网页访问顽主杯数据
"""

import requests
import pandas as pd
import json
import time
import random
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# 顽主杯可能的API端点（需要根据实际抓包确认）
WANZHU_APIS = {
    'rank_daily': 'https://api.hunanwanzhu.com/rank/daily',  # 日榜
    'rank_weekly': 'https://api.hunanwanzhu.com/rank/weekly',  # 周榜
    'rank_monthly': 'https://api.hunanwanzhu.com/rank/monthly',  # 月榜
    'stock_list': 'https://api.hunanwanzhu.com/stock/list',  # 股票列表
}

def test_api_endpoint(url, headers=None):
    """测试API端点是否可用"""
    try:
        print(f"测试: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  ✓ 成功! 返回数据类型: {type(data)}")
                return data
            except:
                print(f"  返回非JSON数据")
                return None
        else:
            print(f"  ✗ 失败")
            return None
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return None

def discover_api():
    """
    自动发现顽主杯API
    尝试常见的API端点组合
    """
    print("="*60)
    print("顽主杯API自动发现")
    print("="*60)
    
    # 基础请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    
    # 测试已知端点
    working_apis = {}
    for name, url in WANZHU_APIS.items():
        data = test_api_endpoint(url, headers)
        if data:
            working_apis[name] = {'url': url, 'data': data}
            # 保存数据
            save_path = BASE_DIR / f"wanzhu_{name}_{datetime.now().strftime('%Y%m%d')}.json"
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 数据已保存: {save_path}\n")
        time.sleep(2)
    
    return working_apis

def parse_rank_data(data):
    """解析榜单数据为CSV"""
    if not data or not isinstance(data, dict):
        return None
    
    # 尝试不同的数据字段
    records = (data.get('list') or data.get('data') or 
               data.get('records') or data.get('rankings') or 
               data.get('result') or [])
    
    if not records:
        print("未找到数据记录")
        return None
    
    df = pd.DataFrame(records)
    
    # 标准化字段名
    column_mapping = {
        'stockCode': 'code',
        'stockName': 'name',
        'code': 'code',
        'name': 'name',
        'rank': 'rank',
        'rate': 'return_rate',
        'return': 'return_rate',
        'industry': 'sector',
        'industryName': 'sector',
    }
    
    df = df.rename(columns=column_mapping)
    df['date'] = datetime.now().strftime('%Y%m%d')
    df['source'] = 'wanzhu'
    
    return df

def main():
    """主函数"""
    print("\n开始自动发现顽主杯API...\n")
    
    # 发现API
    apis = discover_api()
    
    if not apis:
        print("\n✗ 未能自动发现可用的API端点")
        print("\n建议:")
        print("1. 在本地使用Charles/Proxyman抓包获取真实API地址")
        print("2. 将抓包结果保存到 wanzhu_api_config.json")
        print("3. 重新运行脚本")
        return
    
    # 解析并保存数据
    print("\n" + "="*60)
    print("解析数据并生成CSV")
    print("="*60)
    
    for name, api_info in apis.items():
        print(f"\n处理 {name}...")
        df = parse_rank_data(api_info['data'])
        if df is not None and len(df) > 0:
            csv_path = BASE_DIR / f"wanzhu_{name}_{datetime.now().strftime('%Y%m%d')}.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"✓ CSV已生成: {csv_path}")
            print(f"  共 {len(df)} 条记录")
            print(f"  字段: {', '.join(df.columns.tolist())}")

if __name__ == "__main__":
    main()