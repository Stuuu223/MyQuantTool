"""
增强版新闻爬虫模块
支持从多个财经网站抓取新闻数据，具有更好的容错性
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _get_page(self, url: str) -> Optional[str]:
        """获取页面内容"""
        try:
            # 随机延迟，避免被封
            time.sleep(random.uniform(0.5, 1.5))
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
        # 使用API接口获取新闻
        self.api_url = "http://data.eastmoney.com/notices/getdata.ashx"
    
    def crawl(self, limit: int = 20) -> List[NewsItem]:
        """爬取东方财富网新闻"""
        news_list = []
        
        try:
            # 使用API获取新闻列表
            params = {
                'StockCode': '',
                'FirstNodeType': '0',
                'CodeFieldType': '0',
                'PageIndex': '1',
                'PageSize': str(limit),
                'jsVariable': 'noticesData',
                'SecNodeType': '0'
            }
            
            response = self.session.get(self.api_url, params=params, timeout=10)
            
            if response.status_code == 200:
                # 解析JSON响应
                import json
                data_text = response.text
                # 提取JSON部分
                if 'noticesData=' in data_text:
                    json_text = data_text.split('noticesData=')[1].strip()
                    data = json.loads(json_text)
                    
                    if 'data' in data and isinstance(data['data'], list):
                        for item in data['data']:
                            if len(news_list) >= limit:
                                break
                            
                            try:
                                title = item.get('notices', {}).get('title', '')
                                url = item.get('notices', {}).get('article_url', '')
                                time_str = item.get('notices', {}).get('art_ShortDateTime', '')
                                
                                if not title:
                                    continue
                                
                                # 解析时间
                                publish_time = self._parse_time(time_str)
                                
                                # 获取新闻详情
                                content = title  # 默认使用标题
                                if url:
                                    detail_html = self._get_page(url)
                                    if detail_html:
                                        content = self._extract_content(detail_html) or title
                                
                                # 提取相关股票代码
                                related_stocks = self._extract_stock_codes(title + ' ' + content)
                                
                                news = NewsItem(
                                    title=title,
                                    content=content,
                                    source="东方财富网",
                                    publish_time=publish_time,
                                    url=url,
                                    related_stocks=related_stocks
                                )
                                
                                news_list.append(news)
                                
                            except Exception as e:
                                print(f"解析新闻项失败: {str(e)}")
                                continue
                
        except Exception as e:
            print(f"东方财富网爬取失败: {str(e)}")
        
        return news_list
    
    def _parse_time(self, time_str: str) -> datetime:
        """解析时间字符串"""
        try:
            # 处理类似 "01-13 10:30" 的时间
            if '-' in time_str and ':' in time_str:
                parts = time_str.split()
                if len(parts) == 2:
                    date_part = parts[0]
                    time_part = parts[1]
                    month, day = map(int, date_part.split('-'))
                    hour, minute = map(int, time_part.split(':'))
                    today = datetime.now()
                    return datetime(today.year, month, day, hour, minute)
            return datetime.now()
        except:
            return datetime.now()
    
    def _extract_content(self, html: str) -> str:
        """提取新闻内容"""
        soup = BeautifulSoup(html, 'html.parser')
        
        content_selectors = [
            '.Body',
            '.article-content',
            '.content',
            '#ContentBody',
            '.news-content',
            '.stockcodec',
            '.emBody'
        ]
        
        content = ""
        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                content = elem.get_text(strip=True)
                if len(content) > 50:
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
            
            # 查找新闻列表 - 尝试多种选择器
            news_items = soup.select('.listBlk li') or soup.select('.feed-card-item')
            
            for item in news_items:
                if len(news_list) >= limit:
                    break
                
                try:
                    title_elem = item.select_one('a') or item.select_one('.feed-card-title')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    news_url = title_elem.get('href', '')
                    
                    # 提取时间
                    time_elem = item.select_one('.date') or item.select_one('.time')
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
                parts = time_text.split()
                if len(parts) == 2:
                    date_part = parts[0]
                    time_part = parts[1]
                    month_day = date_part.replace('月', '-').replace('日', '')
                    month, day = map(int, month_day.split('-'))
                    hour, minute = map(int, time_part.split(':'))
                    today = datetime.now()
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
            '#article',
            '.article-body',
            '.main-content'
        ]
        
        content = ""
        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                content = elem.get_text(strip=True)
                if len(content) > 50:
                    break
        
        return content


class MockCrawler(NewsCrawler):
    """模拟新闻爬虫（用于测试）"""
    
    def crawl(self, limit: int = 20) -> List[NewsItem]:
        """生成模拟新闻数据"""
        news_list = []
        
        sample_news = [
            {
                'title': '某公司发布业绩预告，净利润同比增长50%',
                'content': '某公司今日发布业绩预告，预计2024年上半年净利润同比增长50%，主要受益于主营业务增长和新产品推出。公司表示，将继续加大研发投入，提升市场竞争力。',
                'source': '模拟数据',
                'related_stocks': ['600519']
            },
            {
                'title': '股价暴跌，公司业绩不及预期',
                'content': '受市场环境影响，公司业绩大幅下滑，股价出现暴跌，投资者信心受挫。公司管理层表示将采取措施改善经营状况。',
                'source': '模拟数据',
                'related_stocks': ['000858']
            },
            {
                'title': '公司发布季度财报，业绩符合预期',
                'content': '公司发布季度财报，营收和利润均符合市场预期，经营状况稳定。公司对未来发展充满信心。',
                'source': '模拟数据',
                'related_stocks': ['600036']
            },
            {
                'title': '重大利好！公司获得政府补贴',
                'content': '公司获得政府专项补贴，将显著提升公司盈利能力，股价有望上涨。公司表示将善用资金，推动业务发展。',
                'source': '模拟数据',
                'related_stocks': ['600000']
            },
            {
                'title': '公司面临重大诉讼风险',
                'content': '公司卷入重大诉讼案件，可能对经营产生不利影响，投资者需谨慎。公司表示将积极应对，维护合法权益。',
                'source': '模拟数据',
                'related_stocks': ['601318']
            },
            {
                'title': '新能源板块大涨，多只个股涨停',
                'content': '受政策利好影响，新能源板块今日表现强劲，多只个股涨停。市场人士认为，新能源行业前景广阔。',
                'source': '模拟数据',
                'related_stocks': ['300750', '002594']
            },
            {
                'title': '央行降准，市场流动性充裕',
                'content': '央行宣布降准，释放长期资金，市场流动性充裕。专家认为，这将有利于实体经济发展。',
                'source': '模拟数据',
                'related_stocks': []
            },
            {
                'title': '科技股持续走强，AI概念领涨',
                'content': '科技股今日持续走强，人工智能概念股领涨。市场对AI技术的前景保持乐观态度。',
                'source': '模拟数据',
                'related_stocks': ['300059', '002230']
            }
        ]
        
        for i in range(min(limit, len(sample_news))):
            news_data = sample_news[i % len(sample_news)]
            
            news = NewsItem(
                title=news_data['title'],
                content=news_data['content'],
                source=news_data['source'],
                publish_time=datetime.now() - timedelta(hours=i),
                url=f"mock://news/{i}",
                related_stocks=news_data['related_stocks']
            )
            
            news_list.append(news)
        
        return news_list


class NewsCrawlerManager:
    """新闻爬虫管理器"""
    
    def __init__(self):
        self.crawlers = {
            'eastmoney': EastMoneyCrawler(),
            'sina': SinaCrawler(),
            'mock': MockCrawler()  # 添加模拟爬虫
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
    
    print("可用新闻源:", manager.get_available_sources())
    
    # 从所有来源爬取新闻
    print("\n开始爬取新闻...")
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
