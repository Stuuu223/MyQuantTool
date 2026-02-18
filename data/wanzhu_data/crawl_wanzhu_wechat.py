#!/usr/bin/env python3
"""
顽主杯小程序数据采集 - Playwright方案
直接控制微信内置浏览器，无需手机抓包
"""

from playwright.sync_api import sync_playwright
import pandas as pd
import json
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def crawl_wanzhu():
    """
    使用Playwright访问顽主杯小程序
    """
    with sync_playwright() as p:
        # 启动浏览器（连接到已打开的微信内置浏览器）
        print("正在连接浏览器...")
        print("请确保微信已打开顽主杯小程序")
        
        # 尝试连接已存在的浏览器实例
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            print("✓ 已连接到微信浏览器")
        except:
            print("✗ 无法连接，尝试启动新浏览器...")
            browser = p.chromium.launch(headless=False)
        
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()
        
        # 监听网络请求
        api_data = []
        
        def handle_route(route, request):
            url = request.url
            if "wanzhu" in url or "rank" in url or "api" in url:
                print(f"\n🎯 捕获API请求: {url[:80]}...")
                try:
                    response = route.fetch()
                    body = response.body()
                    data = json.loads(body)
                    api_data.append({
                        'url': url,
                        'data': data,
                        'time': datetime.now().strftime('%Y%m%d_%H%M%S')
                    })
                    print(f"✓ 数据已保存")
                except:
                    pass
            route.continue_()
        
        page.route("**/*", handle_route)
        
        print("\n请在微信中操作顽主杯小程序...")
        print("浏览榜单页面，数据会自动捕获")
        print("按 Ctrl+C 停止采集\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n采集停止，正在保存数据...")
        
        # 保存数据
        if api_data:
            save_path = BASE_DIR / f"wanzhu_api_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(api_data, f, ensure_ascii=False, indent=2)
            print(f"✓ 数据已保存: {save_path}")
            
            # 解析并生成CSV
            parse_and_save_csv(api_data)
        
        browser.close()

def parse_and_save_csv(api_data):
    """解析API数据并保存为CSV"""
    all_records = []
    
    for item in api_data:
        data = item['data']
        # 根据顽主杯实际数据结构解析
        if isinstance(data, dict):
            # 尝试不同的字段名
            records = data.get('list') or data.get('data') or data.get('records') or data.get('rankings') or []
            if records:
                for record in records:
                    all_records.append(record)
    
    if all_records:
        df = pd.DataFrame(all_records)
        csv_path = BASE_DIR / f"wanzhu_data_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✓ CSV已生成: {csv_path}")
        print(f"  共 {len(df)} 条记录")
        print(f"  字段: {df.columns.tolist()}")

if __name__ == "__main__":
    crawl_wanzhu()