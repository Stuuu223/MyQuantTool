"""
增强版板块分析器

功能：整合所有板块分析功能，提供全面的板块分析
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta

from logic.akshare_data_loader import AKShareDataLoader
from logic.technical_indicators import TechnicalIndicators
from logic.sector_heat_index import SectorHeatIndex
from logic.sector_fundamental import SectorFundamental, SectorRelationAnalyzer, SectorHistoricalAnalyzer

logger = logging.getLogger(__name__)


class EnhancedSectorAnalyzer:
    """增强版板块分析器"""
    
    def __init__(self):
        self.loader = AKShareDataLoader()
        self.cache = {}
        self.cache_ttl = 300  # 缓存5分钟
    
    def _get_cache_key(self, operation: str, *args) -> str:
        """生成缓存键"""
        return f"{operation}:{args}"
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return data
            else:
                del self.cache[key]
        return None
    
    def _set_cache(self, key: str, data: Any):
        """设置缓存"""
        self.cache[key] = (data, datetime.now())
    
    def analyze_sector_comprehensive(self, sector_code: str, sector_name: str) -> Dict[str, Any]:
        """
        全面分析单个板块
        
        Args:
            sector_code: 板块代码
            sector_name: 板块名称
            
        Returns:
            Dict: 包含所有分析结果
        """
        try:
            logger.info(f"开始全面分析板块: {sector_name} ({sector_code})")
            
            result = {
                'sector_code': sector_code,
                'sector_name': sector_name,
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 1. 获取板块基本信息
            industry_df = self.loader.get_industry_spot()
            sector_row = industry_df[industry_df['代码'] == sector_code]
            if not sector_row.empty:
                row = sector_row.iloc[0]
                result['basic_info'] = {
                    '代码': sector_code,
                    '名称': sector_name,
                    '最新价': float(row.get('最新价', 0) or 0),
                    '涨跌幅': float(row.get('涨跌幅', 0) or 0),
                    '成交额': float(row.get('成交额', 0) or 0)
                }
            
            # 2. 获取板块个股统计
            stock_stats = self.loader.get_sector_stock_stats(sector_code)
            result['stock_stats'] = stock_stats
            
            # 3. 获取资金流向
            capital_flow = self.loader.get_sector_capital_flow(sector_code)
            result['capital_flow'] = capital_flow
            
            # 4. 获取板块K线数据
            kline_df = self.loader.get_sector_index_kline(sector_code)
            if not kline_df.empty:
                # 计算技术指标
                kline_with_indicators = TechnicalIndicators.calculate_all_indicators(kline_df)
                
                # 获取最新技术指标
                latest = kline_with_indicators.iloc[-1]
                result['technical_indicators'] = {
                    'macd_dif': float(latest.get('macd_dif', 0) or 0),
                    'macd_dea': float(latest.get('macd_dea', 0) or 0),
                    'macd_hist': float(latest.get('macd_hist', 0) or 0),
                    'kdj_k': float(latest.get('kdj_k', 50) or 50),
                    'kdj_d': float(latest.get('kdj_d', 50) or 50),
                    'kdj_j': float(latest.get('kdj_j', 50) or 50),
                    'rsi': float(latest.get('rsi', 50) or 50)
                }
                
                # 历史分析
                historical = SectorHistoricalAnalyzer.analyze_historical_performance(sector_code, kline_df)
                result['historical_analysis'] = historical
            
            # 5. 计算热度指数
            if stock_stats and 'basic_info' in result:
                heat_data = {
                    '涨跌幅': result['basic_info']['涨跌幅'],
                    '成交额': result['basic_info']['成交额'],
                    'up_count': stock_stats.get('up_count', 0),
                    'down_count': stock_stats.get('down_count', 0),
                    'limit_up_count': stock_stats.get('limit_up_count', 0),
                    'main_net_inflow': capital_flow.get('main_net_inflow', 0)
                }
                heat_score = SectorHeatIndex.calculate_heat_index(heat_data)
                heat_level = SectorHeatIndex.get_heat_level(heat_score)
                
                result['heat_index'] = {
                    'score': heat_score,
                    'level': heat_level
                }
            
            # 6. 获取基本面数据
            fundamental = SectorFundamental.get_sector_fundamental_data(sector_name)
            if fundamental:
                result['fundamental'] = fundamental
                result['fundamental_score'] = SectorFundamental.analyze_fundamental_score(fundamental)
            
            # 7. 获取关联板块
            all_sectors = industry_df['名称'].tolist() if not industry_df.empty else []
            relations = SectorRelationAnalyzer.analyze_sector_relations(sector_name, all_sectors)
            result['relations'] = relations
            
            # 8. 获取北向资金（整体）
            northbound = self.loader.get_northbound_fund_flow()
            result['northbound'] = northbound
            
            logger.info(f"板块 {sector_name} 分析完成")
            return result
            
        except Exception as e:
            logger.error(f"分析板块 {sector_name} 失败: {e}")
            return {'error': str(e)}
    
    def analyze_all_sectors(self, top_n: int = 10) -> pd.DataFrame:
        """
        分析所有板块并返回排行
        
        Args:
            top_n: 返回前N个板块
            
        Returns:
            pd.DataFrame: 板块排行数据
        """
        try:
            # 获取所有板块
            industry_df = self.loader.get_industry_spot()
            
            if industry_df.empty:
                return pd.DataFrame()
            
            results = []
            
            # 分析每个板块
            for _, row in industry_df.head(top_n).iterrows():
                sector_code = row.get('代码', '')
                sector_name = row.get('名称', '')
                
                # 获取缓存
                cache_key = self._get_cache_key('analyze_sector', sector_code)
                cached = self._get_cached(cache_key)
                
                if cached:
                    results.append(cached)
                    continue
                
                # 分析板块
                analysis = self.analyze_sector_comprehensive(sector_code, sector_name)
                
                # 提取关键指标
                summary = {
                    '板块名称': sector_name,
                    '板块代码': sector_code,
                    '涨跌幅': analysis.get('basic_info', {}).get('涨跌幅', 0),
                    '成交额': analysis.get('basic_info', {}).get('成交额', 0),
                    '热度指数': analysis.get('heat_index', {}).get('score', 0),
                    '热度等级': analysis.get('heat_index', {}).get('level', '一般'),
                    '主力净流入': analysis.get('capital_flow', {}).get('main_net_inflow', 0),
                    '上涨家数': analysis.get('stock_stats', {}).get('up_count', 0),
                    '涨停家数': analysis.get('stock_stats', {}).get('limit_up_count', 0),
                    'RSI': analysis.get('technical_indicators', {}).get('rsi', 50),
                    '基本面评分': analysis.get('fundamental_score', 0),
                    '综合评分': 0  # 将在下面计算
                }
                
                # 计算综合评分
                summary['综合评分'] = self._calculate_overall_score(summary)
                
                results.append(summary)
                
                # 设置缓存
                self._set_cache(cache_key, summary)
            
            # 转换为DataFrame并排序
            df = pd.DataFrame(results)
            df = df.sort_values('综合评分', ascending=False)
            
            return df
            
        except Exception as e:
            logger.error(f"分析所有板块失败: {e}")
            return pd.DataFrame()
    
    def _calculate_overall_score(self, summary: Dict[str, Any]) -> float:
        """
        计算综合评分
        
        Args:
            summary: 板块摘要数据
            
        Returns:
            float: 综合评分 (0-100)
        """
        score = 0.0
        
        # 1. 热度指数 (30%)
        heat_score = summary.get('热度指数', 0)
        score += heat_score * 0.3
        
        # 2. 涨跌幅 (20%)
        price_change = summary.get('涨跌幅', 0)
        if price_change > 0:
            score += min(price_change * 2, 20)
        
        # 3. 主力净流入 (20%)
        main_inflow = summary.get('主力净流入', 0)
        if main_inflow > 0:
            score += min(main_inflow / 1e8 * 20, 20)
        
        # 4. 技术指标 (15%)
        rsi = summary.get('RSI', 50)
        if 30 < rsi < 70:  # RSI在合理区间
            score += 15
        elif rsi >= 70:  # 超买
            score += 10
        else:  # 超卖
            score += 5
        
        # 5. 基本面评分 (15%)
        fundamental_score = summary.get('基本面评分', 0)
        score += fundamental_score * 0.15
        
        return min(score, 100.0)


if __name__ == "__main__":
    # 测试
    analyzer = EnhancedSectorAnalyzer()
    
    print("=== 测试单个板块分析 ===")
    result = analyzer.analyze_sector_comprehensive("BK0447", "文化传媒")
    print(f"分析结果键: {result.keys()}")
    if 'heat_index' in result:
        print(f"热度指数: {result['heat_index']}")
    
    print("\n=== 测试所有板块分析 ===")
    df = analyzer.analyze_all_sectors(top_n=5)
    if not df.empty:
        print(df[['板块名称', '综合评分', '热度指数', '涨跌幅', '主力净流入']])
    else:
        print("无数据")
