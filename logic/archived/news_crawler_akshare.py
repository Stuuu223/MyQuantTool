"""
基于akshare的新闻爬虫模块
使用akshare提供的新闻接口，稳定可靠
"""

import akshare as ak
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
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


class AkshareNewsCrawler:
    """基于akshare的新闻爬虫"""
    
    def _extract_stock_codes(self, text: str) -> List[str]:
        """从文本中提取股票代码"""
        pattern = r'[0-9]{6}'
        codes = re.findall(pattern, text)
        return list(set(codes))
    
    def _parse_time(self, time_str: str) -> datetime:
        """解析时间字符串"""
        try:
            # 处理类似 "2026-01-08 18:28:18" 的时间
            if '-' in time_str and ':' in time_str:
                return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            return datetime.now()
        except:
            return datetime.now()
    
    def crawl_stock_news_em(self, limit: int = 20) -> List[NewsItem]:
        """爬取东方财富网股票新闻"""
        news_list = []
        
        try:
            # 使用akshare获取东方财富网新闻
            df = ak.stock_news_em()
            
            # 限制数量
            df = df.head(limit)
            
            for _, row in df.iterrows():
                try:
                    # 提取信息
                    title = row.get('新闻标题', '')
                    content = row.get('新闻内容', '')
                    source = row.get('新闻来源', '东方财富网')
                    time_str = row.get('发布时间', '')
                    url = row.get('文章链接', '')
                    stock_code = row.get('关键词代码', '')
                    
                    if not title:
                        continue
                    
                    # 解析时间
                    publish_time = self._parse_time(time_str) if time_str else datetime.now()
                    
                    # 提取相关股票代码
                    related_stocks = []
                    if stock_code:
                        related_stocks.append(stock_code)
                    
                    # 从内容中提取股票代码
                    if content:
                        content_stocks = self._extract_stock_codes(content)
                        related_stocks.extend(content_stocks)
                    
                    # 去重
                    related_stocks = list(set(related_stocks))
                    
                    news = NewsItem(
                        title=title,
                        content=content or title,
                        source=source,
                        publish_time=publish_time,
                        url=url,
                        related_stocks=related_stocks
                    )
                    
                    news_list.append(news)
                    
                except Exception as e:
                    print(f"解析新闻失败: {str(e)}")
                    continue
            
            print(f"从东方财富网爬取了 {len(news_list)} 条新闻")
            
        except Exception as e:
            print(f"东方财富网爬取失败: {str(e)}")
        
        return news_list
    
    def crawl_stock_news_main_cx(self, limit: int = 20) -> List[NewsItem]:
        """爬取财联社新闻"""
        news_list = []
        
        try:
            # 使用akshare获取财联社新闻
            df = ak.stock_news_main_cx()
            
            # 限制数量
            df = df.head(limit)
            
            for _, row in df.iterrows():
                try:
                    # 提取信息
                    title = row.get('新闻标题', '')
                    content = row.get('新闻内容', '')
                    source = row.get('新闻来源', '财联社')
                    time_str = row.get('发布时间', '')
                    url = row.get('文章链接', '')
                    stock_code = row.get('关键词代码', '')
                    
                    if not title:
                        continue
                    
                    # 解析时间
                    publish_time = self._parse_time(time_str) if time_str else datetime.now()
                    
                    # 提取相关股票代码
                    related_stocks = []
                    if stock_code:
                        related_stocks.append(stock_code)
                    
                    # 从内容中提取股票代码
                    if content:
                        content_stocks = self._extract_stock_codes(content)
                        related_stocks.extend(content_stocks)
                    
                    # 去重
                    related_stocks = list(set(related_stocks))
                    
                    news = NewsItem(
                        title=title,
                        content=content or title,
                        source=source,
                        publish_time=publish_time,
                        url=url,
                        related_stocks=related_stocks
                    )
                    
                    news_list.append(news)
                    
                except Exception as e:
                    print(f"解析新闻失败: {str(e)}")
                    continue
            
            print(f"从财联社爬取了 {len(news_list)} 条新闻")
            
        except Exception as e:
            print(f"财联社爬取失败: {str(e)}")
        
        return news_list
    
    def crawl_news_cctv(self, limit: int = 20) -> List[NewsItem]:
        """爬取央视新闻"""
        news_list = []
        
        try:
            # 使用akshare获取央视新闻
            df = ak.news_cctv()
            
            # 限制数量
            df = df.head(limit)
            
            for _, row in df.iterrows():
                try:
                    # 提取信息
                    title = row.get('title', '')
                    content = row.get('content', '')
                    time_str = row.get('time', '')
                    url = row.get('url', '')
                    
                    if not title:
                        continue
                    
                    # 解析时间
                    publish_time = self._parse_time(time_str) if time_str else datetime.now()
                    
                    # 从内容中提取股票代码
                    related_stocks = self._extract_stock_codes(title + ' ' + content) if content else []
                    
                    news = NewsItem(
                        title=title,
                        content=content or title,
                        source="央视新闻",
                        publish_time=publish_time,
                        url=url,
                        related_stocks=related_stocks
                    )
                    
                    news_list.append(news)
                    
                except Exception as e:
                    print(f"解析新闻失败: {str(e)}")
                    continue
            
            print(f"从央视新闻爬取了 {len(news_list)} 条新闻")
            
        except Exception as e:
            print(f"央视新闻爬取失败: {str(e)}")
        
        return news_list
    
    def crawl_news_economic_baidu(self, limit: int = 20) -> List[NewsItem]:
        """爬取百度经济新闻"""
        news_list = []
        
        try:
            # 使用akshare获取百度经济新闻
            df = ak.news_economic_baidu()
            
            # 限制数量
            df = df.head(limit)
            
            for _, row in df.iterrows():
                try:
                    # 提取信息
                    title = row.get('title', '')
                    content = row.get('content', '')
                    time_str = row.get('time', '')
                    url = row.get('url', '')
                    
                    if not title:
                        continue
                    
                    # 解析时间
                    publish_time = self._parse_time(time_str) if time_str else datetime.now()
                    
                    # 从内容中提取股票代码
                    related_stocks = self._extract_stock_codes(title + ' ' + content) if content else []
                    
                    news = NewsItem(
                        title=title,
                        content=content or title,
                        source="百度经济新闻",
                        publish_time=publish_time,
                        url=url,
                        related_stocks=related_stocks
                    )
                    
                    news_list.append(news)
                    
                except Exception as e:
                    print(f"解析新闻失败: {str(e)}")
                    continue
            
            print(f"从百度经济新闻爬取了 {len(news_list)} 条新闻")
            
        except Exception as e:
            print(f"百度经济新闻爬取失败: {str(e)}")
        
        return news_list
    
    def crawl_futures_news_shmet(self, limit: int = 20) -> List[NewsItem]:
        """爬取上海有色网期货新闻"""
        news_list = []
        
        try:
            # 使用akshare获取上海有色网期货新闻
            df = ak.futures_news_shmet()
            
            # 限制数量
            df = df.head(limit)
            
            for _, row in df.iterrows():
                try:
                    # 提取信息
                    title = row.get('title', '')
                    content = row.get('content', '')
                    time_str = row.get('time', '')
                    url = row.get('url', '')
                    
                    if not title:
                        continue
                    
                    # 解析时间
                    publish_time = self._parse_time(time_str) if time_str else datetime.now()
                    
                    # 从内容中提取股票代码
                    related_stocks = self._extract_stock_codes(title + ' ' + content) if content else []
                    
                    news = NewsItem(
                        title=title,
                        content=content or title,
                        source="上海有色网",
                        publish_time=publish_time,
                        url=url,
                        related_stocks=related_stocks
                    )
                    
                    news_list.append(news)
                    
                except Exception as e:
                    print(f"解析新闻失败: {str(e)}")
                    continue
            
            print(f"从上海有色网爬取了 {len(news_list)} 条新闻")
            
        except Exception as e:
            print(f"上海有色网爬取失败: {str(e)}")
        
        return news_list


class MockCrawler:
    """模拟新闻爬虫（备用）"""
    
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
                publish_time=datetime.now(),
                url=f"mock://news/{i}",
                related_stocks=news_data['related_stocks']
            )
            
            news_list.append(news)
        
        return news_list


class NewsCrawlerManager:
    """新闻爬虫管理器"""
    
    def __init__(self):
        self.akshare_crawler = AkshareNewsCrawler()
        self.mock_crawler = MockCrawler()
    
    def crawl_from_source(self, source: str, limit: int = 20) -> List[NewsItem]:
        """从指定来源爬取新闻"""
        if source == 'em':
            return self.akshare_crawler.crawl_stock_news_em(limit)
        elif source == 'cx':
            return self.akshare_crawler.crawl_stock_news_main_cx(limit)
        elif source == 'cctv':
            return self.akshare_crawler.crawl_news_cctv(limit)
        elif source == 'baidu':
            return self.akshare_crawler.crawl_news_economic_baidu(limit)
        elif source == 'shmet':
            return self.akshare_crawler.crawl_futures_news_shmet(limit)
        elif source == 'mock':
            return self.mock_crawler.crawl(limit)
        else:
            raise ValueError(f"不支持的新闻源: {source}")
    
    def crawl_all(self, limit_per_source: int = 10) -> List[NewsItem]:
        """从所有来源爬取新闻"""
        all_news = []
        
        # 爬取东方财富网新闻
        try:
            news = self.akshare_crawler.crawl_stock_news_em(limit_per_source)
            all_news.extend(news)
        except Exception as e:
            print(f"东方财富网爬取失败: {str(e)}")
        
        # 爬取财联社新闻
        try:
            news = self.akshare_crawler.crawl_stock_news_main_cx(limit_per_source)
            all_news.extend(news)
        except Exception as e:
            print(f"财联社爬取失败: {str(e)}")
        
        # 爬取央视新闻
        try:
            news = self.akshare_crawler.crawl_news_cctv(limit_per_source)
            all_news.extend(news)
        except Exception as e:
            print(f"央视新闻爬取失败: {str(e)}")
        
        # 爬取百度经济新闻
        try:
            news = self.akshare_crawler.crawl_news_economic_baidu(limit_per_source)
            all_news.extend(news)
        except Exception as e:
            print(f"百度经济新闻爬取失败: {str(e)}")
        
        # 爬取上海有色网期货新闻
        try:
            news = self.akshare_crawler.crawl_futures_news_shmet(limit_per_source)
            all_news.extend(news)
        except Exception as e:
            print(f"上海有色网爬取失败: {str(e)}")
        
        # 按时间排序
        all_news.sort(key=lambda x: x.publish_time, reverse=True)
        
        return all_news
    
    def get_available_sources(self) -> List[str]:
        """获取可用的新闻源"""
        return ['em', 'cx', 'cctv', 'baidu', 'shmet', 'mock']
    
    def get_source_names(self) -> Dict[str, str]:
        """获取新闻源名称映射"""
        return {
            'em': '东方财富网',
            'cx': '财联社',
            'cctv': '央视新闻',
            'baidu': '百度经济新闻',
            'shmet': '上海有色网',
            'mock': '模拟数据'
        }


# 使用示例
if __name__ == "__main__":
    # 创建爬虫管理器
    manager = NewsCrawlerManager()
    
    print("可用新闻源:", manager.get_available_sources())
    print("新闻源名称:", manager.get_source_names())
    
    # 测试东方财富网
    print("\n" + "=" * 60)
    print("测试东方财富网新闻爬取")
    print("=" * 60)
    news = manager.crawl_from_source('em', 5)
    print(f"爬取了 {len(news)} 条新闻")
    for i, n in enumerate(news, 1):
        print(f"{i}. {n.title} - {n.source}")
        print(f"   相关股票: {n.related_stocks}")
    
    # 测试财联社
    print("\n" + "=" * 60)
    print("测试财联社新闻爬取")
    print("=" * 60)
    news = manager.crawl_from_source('cx', 5)
    print(f"爬取了 {len(news)} 条新闻")
    for i, n in enumerate(news, 1):
        print(f"{i}. {n.title} - {n.source}")
        print(f"   相关股票: {n.related_stocks}")