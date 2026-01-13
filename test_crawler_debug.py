"""
调试新闻爬虫
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.news_crawler_enhanced import EastMoneyCrawler, SinaCrawler

def test_eastmoney():
    print("=" * 60)
    print("测试东方财富网爬虫")
    print("=" * 60)
    
    crawler = EastMoneyCrawler()
    
    # 测试API请求
    print("\n1. 测试API请求...")
    try:
        import requests
        params = {
            'StockCode': '',
            'FirstNodeType': '0',
            'CodeFieldType': '0',
            'PageIndex': '1',
            'PageSize': '5',
            'jsVariable': 'noticesData',
            'SecNodeType': '0'
        }
        
        response = crawler.session.get(crawler.api_url, params=params, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应长度: {len(response.text)}")
        
        if response.status_code == 200:
            print(f"响应前200字符: {response.text[:200]}")
            
            # 尝试解析
            if 'noticesData=' in response.text:
                import json
                json_text = response.text.split('noticesData=')[1].strip()
                data = json.loads(json_text)
                print(f"\n解析成功!")
                print(f"数据结构: {list(data.keys())}")
                if 'data' in data:
                    print(f"新闻数量: {len(data['data'])}")
                    if data['data']:
                        print(f"第一条新闻: {data['data'][0]}")
            else:
                print("响应中没有找到 'noticesData='")
    except Exception as e:
        print(f"API请求失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 测试爬取
    print("\n2. 测试爬取功能...")
    try:
        news = crawler.crawl(limit=5)
        print(f"爬取到 {len(news)} 条新闻")
        for i, n in enumerate(news, 1):
            print(f"{i}. {n.title}")
    except Exception as e:
        print(f"爬取失败: {str(e)}")
        import traceback
        traceback.print_exc()

def test_sina():
    print("\n" + "=" * 60)
    print("测试新浪财经爬虫")
    print("=" * 60)
    
    crawler = SinaCrawler()
    
    # 测试页面请求
    print("\n1. 测试页面请求...")
    try:
        url = crawler.base_url.format(1)
        print(f"请求URL: {url}")
        
        html = crawler._get_page(url)
        
        if html:
            print(f"成功获取页面，长度: {len(html)}")
            print(f"前300字符: {html[:300]}")
            
            # 查找新闻列表
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # 尝试多种选择器
            selectors = ['.listBlk li', '.feed-card-item', 'li', 'a']
            
            for selector in selectors:
                items = soup.select(selector)
                print(f"\n选择器 '{selector}' 找到 {len(items)} 个元素")
                
                if items and len(items) > 0:
                    first_item = items[0]
                    print(f"第一个元素的HTML: {str(first_item)[:200]}")
        else:
            print("获取页面失败")
            
    except Exception as e:
        print(f"页面请求失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 测试爬取
    print("\n2. 测试爬取功能...")
    try:
        news = crawler.crawl(limit=5)
        print(f"爬取到 {len(news)} 条新闻")
        for i, n in enumerate(news, 1):
            print(f"{i}. {n.title}")
    except Exception as e:
        print(f"爬取失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_eastmoney()
    test_sina()