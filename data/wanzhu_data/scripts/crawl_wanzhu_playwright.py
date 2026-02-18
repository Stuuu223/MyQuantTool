#!/usr/bin/env python3
"""
顽主杯数据采集 - Playwright 自动化方案
无需抓包，直接通过浏览器访问获取数据
"""

import json
import time
import re
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
    import pandas as pd
except ImportError:
    print("请先安装依赖: pip install playwright pandas")
    print("然后运行: playwright install chromium")
    import sys
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "crawl.log"


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def extract_wanzhu_data():
    """
    使用 Playwright 访问顽主杯并提取数据
    """
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            # 尝试访问顽主杯相关页面
            # 注意：这里需要实际的URL，可能是以下之一：
            urls_to_try = [
                "https://www.hunanwanzhu.com/",  # 官网
                "https://mp.hunanwanzhu.com/",   # 小程序web版
                "https://app.hunanwanzhu.com/",  # 可能的APP页面
            ]
            
            for url in urls_to_try:
                log(f"尝试访问: {url}")
                try:
                    page.goto(url, timeout=10000)
                    time.sleep(3)
                    
                    # 等待页面加载
                    page.wait_for_load_state("networkidle")
                    
                    # 尝试找到榜单数据
                    # 这里需要根据实际页面结构调整选择器
                    content = page.content()
                    
                    # 检查是否包含股票数据特征
                    if "rank" in content.lower() or "股票" in content or "榜单" in content:
                        log(f"找到潜在数据页面: {url}")
                        
                        # 尝试提取数据
                        # 方法1: 直接解析页面中的JSON
                        json_matches = re.findall(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', content)
                        if json_matches:
                            data = json.loads(json_matches[0])
                            return data
                        
                        # 方法2: 查找API请求
                        # 监听网络请求
                        break
                        
                except Exception as e:
                    log(f"访问失败: {e}", "WARN")
                    continue
            
            # 如果上述都失败，尝试监听网络请求找API
            log("尝试监听网络请求...")
            api_responses = []
            
            def handle_response(response):
                url = response.url
                if any(keyword in url for keyword in ["rank", "list", "api", "data", "json"]):
                    try:
                        data = response.json()
                        api_responses.append({"url": url, "data": data})
                        log(f"捕获API: {url}")
                    except:
                        pass
            
            page.on("response", handle_response)
            
            # 点击榜单相关按钮（需要根据实际页面调整）
            # page.click("text=排行榜")
            # time.sleep(2)
            
            browser.close()
            
            if api_responses:
                return api_responses[0]
            
            return None
            
        except Exception as e:
            log(f"提取失败: {e}", "ERROR")
            browser.close()
            return None


def save_data(data, trade_date):
    """保存数据"""
    if not data:
        log("无数据可保存", "WARN")
        return
    
    # 解析数据（根据实际结构调整）
    # 这里假设 data 是一个包含列表的字典
    items = data.get("list", []) if isinstance(data, dict) else []
    
    if not items:
        log("数据为空", "WARN")
        return
    
    df = pd.DataFrame(items)
    df["date"] = trade_date
    
    # 保存
    daily_file = BASE_DIR / f"wanzhu_playwright_{trade_date}.csv"
    df.to_csv(daily_file, index=False, encoding="utf-8-sig")
    log(f"保存成功: {daily_file}, 共 {len(df)} 条")


def main():
    log("=" * 50)
    log("顽主杯 Playwright 采集开始")
    log("=" * 50)
    
    today = datetime.now().strftime("%Y%m%d")
    
    data = extract_wanzhu_data()
    save_data(data, today)
    
    log("采集完成")


if __name__ == "__main__":
    main()
