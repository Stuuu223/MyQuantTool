"""
新闻爬虫模块
支持从多个财经网站抓取新闻数据
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import random
from dataclasses import dataclass
import re


@dataclass
class NewsItem:
    """新闻项"""
    title: str
    content: str
    source: str
    publish_time: datetime
    url: str
    related_stocks: List[str] = None


class NewsCrawler:
    """新闻爬虫基类"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _get_page(self, url: str) -> Optional[str]:
        """获取页面内容"""
        try:
            # 随机延迟，避免被封
            time.sleep(random.uniform(1, 3))
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                return response.text
            else:
                print(f"请求失败: {url}, 状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"获取页面失败: {url}, 错误: {str(e)}")
            return None
    
    def _extract_stock_codes(self, text: str) -> List[str]:
        """从文本中提取股票代码"""
        # 匹配6位数字的股票代码
        pattern = r'[0-9]{6}'
        codes = re.findall(pattern, text)
        return list(set(codes))
    
    def crawl(self, limit: int = 20) -> List[NewsItem]:
        """爬取新闻（子类需要实现）"""
        raise NotImplementedError


class EastMoneyCrawler(NewsCrawler):
    """东方财富网新闻爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://finance.eastmoney.com/a/cjkx{}.html"
    
    def crawl(self, limit: int = 20) -> List[NewsItem]:
        """爬取东方财富网新闻"""
        news_list = []
        
        # 获取新闻列表页
        for page in range(1, 3):  # 爬取前2页
            url = self.base_url.format(page)
            html = self._get_page(url)
            
            if not html:
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找新闻列表
            news_items = soup.select('.list-content li')
            
            for item in news_items:
                if len(news_list) >= limit:
                    break
                
                try:
                    # 提取标题和链接
                    title_elem = item.select_one('a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    news_url = title_elem.get('href', '')
                    
                    # 提取时间
                    time_elem = item.select_one('.time')
                    if time_elem:
                        time_text = time_elem.get_text(strip=True)
                        publish_time = self._parse_time(time_text)
                    else:
                        publish_time = datetime.now()
                    
                    # 获取新闻详情
                    if news_url:
                        detail_html = self._get_page(news_url)
                        if detail_html:
                            content = self._extract_content(detail_html)
                        else:
                            content = title  # 如果获取详情失败，使用标题作为内容
                    else:
                        content = title
                    
                    # 提取相关股票代码
                    related_stocks = self._extract_stock_codes(title + ' ' + content)
                    
                    news = NewsItem(
                        title=title,
                        content=content,
                        source="东方财富网",
                        publish_time=publish_time,
                        url=news_url,
                        related_stocks=related_stocks
                    )
                    
                    news_list.append(news)
                    
                except Exception as e:
                    print(f"解析新闻失败: {str(e)}")
                    continue
            
            if len(news_list) >= limit:
                break
        
        return news_list
    
    def _parse_time(self, time_text: str) -> datetime:
        """解析时间字符串"""
        try:
            # 处理类似 "2024-01-13 10:30:00" 的时间
            if ':' in time_text:
                return datetime.strptime(time_text, '%Y-%m-%d %H:%M:%S')
            # 处理类似 "10:30" 的时间
            elif len(time_text) == 5:
                today = datetime.now()
                hour, minute = map(int, time_text.split(':'))
                return datetime(today.year, today.month, today.day, hour, minute)
            else:
                return datetime.now()
        except:
            return datetime.now()
    
    def _extract_content(self, html: str) -> str:
        """提取新闻内容"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试多种选择器
        content_selectors = [
            '.Body',
            '.article-content',
            '.content',
            '#ContentBody',
            '.news-content'
        ]
        
        content = ""
        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                content = elem.get_text(strip=True)
                if len(content) > 50:  # 确保内容不为空
                    break
        
        return content


class SinaCrawler(NewsCrawler):
    """新浪财经新闻爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://finance.sina.com.cn/roll/index.d.html?page={}"
    
    def crawl(self, limit: int = 20) -> List[NewsItem]:
        """爬取新浪财经新闻"""
        news_list = []
        
        for page in range(1, 3):
            url = self.base_url.format(page)
            html = self._get_page(url)
            
            if not html:
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找新闻列表
            news_items = soup.select('.listBlk li')
            
            for item in news_items:
                if len(news_list) >= limit:
                    break
                
                try:
                    title_elem = item.select_one('a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    news_url = title_elem.get('href', '')
                    
                    # 提取时间
                    time_elem = item.select_one('.date')
                    if time_elem:
                        time_text = time_elem.get_text(strip=True)
                        publish_time = self._parse_time(time_text)
                    else:
                        publish_time = datetime.now()
                    
                    # 获取新闻详情
                    if news_url:
                        detail_html = self._get_page(news_url)
                        if detail_html:
                            content = self._extract_content(detail_html)
                        else:
                            content = title
                    else:
                        content = title
                    
                    related_stocks = self._extract_stock_codes(title + ' ' + content)
                    
                    news = NewsItem(
                        title=title,
                        content=content,
                        source="新浪财经",
                        publish_time=publish_time,
                        url=news_url,
                        related_stocks=related_stocks
                    )
                    
                    news_list.append(news)
                    
                except Exception as e:
                    print(f"解析新闻失败: {str(e)}")
                    continue
            
            if len(news_list) >= limit:
                break
        
        return news_list
    
    def _parse_time(self, time_text: str) -> datetime:
        """解析时间字符串"""
        try:
            # 处理类似 "01月13日 10:30" 的时间
            if '月' in time_text and ':' in time_text:
                today = datetime.now()
                parts = time_text.split()
                if len(parts) == 2:
                    date_part = parts[0]
                    time_part = parts[1]
                    month_day = date_part.replace('月', '-').replace('日', '')
                    month, day = map(int, month_day.split('-'))
                    hour, minute = map(int, time_part.split(':'))
                    return datetime(today.year, month, day, hour, minute)
            return datetime.now()
        except:
            return datetime.now()
    
    def _extract_content(self, html: str) -> str:
        """提取新闻内容"""
        soup = BeautifulSoup(html, 'html.parser')
        
        content_selectors = [
            '.article',
            '#artibody',
            '.article-content',
            '#article'
        ]
        
        content = ""
        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                content = elem.get_text(strip=True)
                if len(content) > 50:
                    break
        
        return content


class NewsCrawlerManager:
    """新闻爬虫管理器"""
    
    def __init__(self):
        self.crawlers = {
            'eastmoney': EastMoneyCrawler(),
            'sina': SinaCrawler()
        }
    
    def crawl_from_source(self, source: str, limit: int = 20) -> List[NewsItem]:
        """从指定来源爬取新闻"""
        if source not in self.crawlers:
            raise ValueError(f"不支持的新闻源: {source}")
        
        return self.crawlers[source].crawl(limit)
    
    def crawl_all(self, limit_per_source: int = 10) -> List[NewsItem]:
        """从所有来源爬取新闻"""
        all_news = []
        
        for source_name, crawler in self.crawlers.items():
            try:
                news = crawler.crawl(limit_per_source)
                all_news.extend(news)
                print(f"从 {source_name} 爬取了 {len(news)} 条新闻")
            except Exception as e:
                print(f"从 {source_name} 爬取失败: {str(e)}")
        
        # 按时间排序
        all_news.sort(key=lambda x: x.publish_time, reverse=True)
        
        return all_news
    
    def get_available_sources(self) -> List[str]:
        """获取可用的新闻源"""
        return list(self.crawlers.keys())


# 使用示例
if __name__ == "__main__":
    # 创建爬虫管理器
    manager = NewsCrawlerManager()
    
    # 从所有来源爬取新闻
    print("开始爬取新闻...")
    news_list = manager.crawl_all(limit_per_source=5)
    
    print(f"\n共爬取到 {len(news_list)} 条新闻\n")
    
    # 显示前5条新闻
    for i, news in enumerate(news_list[:5], 1):
        print(f"新闻 {i}:")
        print(f"标题: {news.title}")
        print(f"来源: {news.source}")
        print(f"时间: {news.publish_time}")
        print(f"相关股票: {news.related_stocks}")
        print(f"内容长度: {len(news.content)} 字符")
        print("-" * 60)
