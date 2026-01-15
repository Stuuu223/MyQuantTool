"""
实用版新闻爬虫模块
使用RSS和更可靠的数据源
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
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _get_page(self, url: str) -> Optional[str]:
        """获取页面内容"""
        try:
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
        pattern = r'[0-9]{6}'
        codes = re.findall(pattern, text)
        return list(set(codes))
    
    def crawl(self, limit: int = 20) -> List[NewsItem]:
        """爬取新闻（子类需要实现）"""
        raise NotImplementedError


# RSSCrawler已移除，需要feedparser依赖


class ChinaStockCrawler(NewsCrawler):
    """中国证券网爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://www.cnstock.com/"
    
    def crawl(self, limit: int = 20) -> List[NewsItem]:
        """爬取中国证券网新闻"""
        news_list = []
        
        try:
            html = self._get_page(self.base_url)
            
            if not html:
                return news_list
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找新闻列表
            news_items = soup.select('.news-list li') or soup.select('.article-item')
            
            for item in news_items:
                if len(news_list) >= limit:
                    break
                
                try:
                    title_elem = item.select_one('a') or item.select_one('.title')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    news_url = title_elem.get('href', '')
                    
                    if not news_url.startswith('http'):
                        news_url = self.base_url + news_url.lstrip('/')
                    
                    # 获取发布时间
                    time_elem = item.select_one('.time') or item.select_one('.date')
                    if time_elem:
                        time_text = time_elem.get_text(strip=True)
                        publish_time = self._parse_time(time_text)
                    else:
                        publish_time = datetime.now()
                    
                    # 获取内容
                    content = title
                    if news_url:
                        detail_html = self._get_page(news_url)
                        if detail_html:
                            content = self._extract_content(detail_html) or title
                    
                    related_stocks = self._extract_stock_codes(title + ' ' + content)
                    
                    news = NewsItem(
                        title=title,
                        content=content,
                        source="中国证券网",
                        publish_time=publish_time,
                        url=news_url,
                        related_stocks=related_stocks
                    )
                    
                    news_list.append(news)
                    
                except Exception as e:
                    print(f"解析新闻失败: {str(e)}")
                    continue
        
        except Exception as e:
            print(f"中国证券网爬取失败: {str(e)}")
        
        return news_list
    
    def _parse_time(self, time_text: str) -> datetime:
        """解析时间"""
        try:
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
        """提取内容"""
        soup = BeautifulSoup(html, 'html.parser')
        
        content_selectors = [
            '.article-content',
            '.content',
            '#content',
            '.article-body'
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
    """模拟新闻爬虫"""
    
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
            },
            {
                'title': '半导体行业迎来新机遇',
                'content': '随着国产化进程加速，半导体行业迎来新的发展机遇。多家公司表示将加大研发投入。',
                'source': '模拟数据',
                'related_stocks': ['600584', '002049']
            },
            {
                'title': '医药板块表现活跃',
                'content': '医药板块今日表现活跃，多只个股上涨。市场关注创新药和医疗器械领域的发展。',
                'source': '模拟数据',
                'related_stocks': ['300015', '000661']
            }
        ]
        
        for i in range(min(limit, len(sample_news))):
            news_data = sample_news[i]
            
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
            'mock': MockCrawler(),
            'cnstock': ChinaStockCrawler(),
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
        print("-" * 60)
