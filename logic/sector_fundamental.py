"""
板块基本面数据模块

功能：获取板块的基本面数据，包括营收增速、利润增速等
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class SectorFundamental:
    """板块基本面数据类"""
    
    @staticmethod
    def get_sector_fundamental_data(sector_name: str) -> Dict[str, Any]:
        """
        获取板块基本面数据
        
        Args:
            sector_name: 板块名称
            
        Returns:
            Dict: 包含营收增速、利润增速等基本面数据
        """
        try:
            # 注意：akshare可能没有直接提供板块基本面数据的接口
            # 这里返回模拟数据，实际应用中需要根据具体数据源调整
            
            # 模拟数据
            fundamental_data = {
                'sector_name': sector_name,
                'revenue_growth': np.random.uniform(-10, 30),  # 营收增速 (%)
                'profit_growth': np.random.uniform(-20, 40),   # 利润增速 (%)
                'roe': np.random.uniform(5, 25),                # ROE (%)
                'roa': np.random.uniform(2, 10),                # ROA (%)
                'pe_ratio': np.random.uniform(10, 50),          # 市盈率
                'pb_ratio': np.random.uniform(1, 10),           # 市净率
                'debt_ratio': np.random.uniform(20, 70),        # 资产负债率 (%)
                'update_date': pd.Timestamp.now().strftime('%Y-%m-%d')
            }
            
            logger.info(f"获取板块 {sector_name} 基本面数据")
            return fundamental_data
            
        except Exception as e:
            logger.error(f"获取板块 {sector_name} 基本面数据失败: {e}")
            return {}
    
    @staticmethod
    def analyze_fundamental_score(data: Dict[str, Any]) -> float:
        """
        分析基本面评分
        
        Args:
            data: 基本面数据
            
        Returns:
            float: 基本面评分 (0-100)
        """
        try:
            score = 0.0
            
            # 1. 营收增速 (30%)
            revenue_growth = data.get('revenue_growth', 0)
            if revenue_growth > 0:
                score += min(revenue_growth * 1.5, 30)
            
            # 2. 利润增速 (30%)
            profit_growth = data.get('profit_growth', 0)
            if profit_growth > 0:
                score += min(profit_growth * 1.2, 30)
            
            # 3. ROE (20%)
            roe = data.get('roe', 0)
            score += min(roe * 1.5, 20)
            
            # 4. 负债率 (20%，越低越好)
            debt_ratio = data.get('debt_ratio', 50)
            score += max(0, 20 - debt_ratio * 0.3)
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"分析基本面评分失败: {e}")
            return 0.0


class SectorRelationAnalyzer:
    """板块关联分析类"""
    
    @staticmethod
    def analyze_sector_relations(target_sector: str, all_sectors: List[str]) -> Dict[str, Any]:
        """
        分析板块关联关系
        
        Args:
            target_sector: 目标板块
            all_sectors: 所有板块列表
            
        Returns:
            Dict: 包含上游、下游、同概念板块
        """
        try:
            # 简化的关联关系映射（实际应用中需要更复杂的分析）
            relation_map = {
                '新能源车': {
                    'upstream': ['有色金属', '化工', '钢铁'],
                    'downstream': ['汽车', '电力公用'],
                    'related': ['光伏', '锂电池', '充电桩']
                },
                '光伏': {
                    'upstream': ['有色金属', '化工', '电气设备'],
                    'downstream': ['电力公用', '新能源车'],
                    'related': ['风电', '储能', '新能源车']
                },
                '房地产': {
                    'upstream': ['钢铁', '建材', '有色金属'],
                    'downstream': ['家电', '建筑装饰', '银行'],
                    'related': ['建筑', '水泥', '物业管理']
                },
                '芯片': {
                    'upstream': ['有色金属', '化工', '电子'],
                    'downstream': ['消费电子', '汽车', '通信'],
                    'related': ['半导体', '集成电路', '5G']
                }
            }
            
            # 如果没有预定义的关联关系，返回空
            if target_sector not in relation_map:
                return {
                    'target_sector': target_sector,
                    'upstream': [],
                    'downstream': [],
                    'related': []
                }
            
            # 过滤存在的板块
            relations = relation_map[target_sector]
            upstream = [s for s in relations['upstream'] if s in all_sectors]
            downstream = [s for s in relations['downstream'] if s in all_sectors]
            related = [s for s in relations['related'] if s in all_sectors]
            
            return {
                'target_sector': target_sector,
                'upstream': upstream,
                'downstream': downstream,
                'related': related
            }
            
        except Exception as e:
            logger.error(f"分析板块关联关系失败: {e}")
            return {
                'target_sector': target_sector,
                'upstream': [],
                'downstream': [],
                'related': []
            }


class SectorHistoricalAnalyzer:
    """板块历史数据分析类"""
    
    @staticmethod
    def analyze_historical_performance(sector_code: str, kline_df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析板块历史表现
        
        Args:
            sector_code: 板块代码
            kline_df: K线数据
            
        Returns:
            Dict: 历史分析结果
        """
        try:
            if kline_df.empty:
                return {}
            
            # 找到收盘价列
            close_col = None
            for col in ['close', 'Close', '收盘', '收盘价']:
                if col in kline_df.columns:
                    close_col = col
                    break
            
            if close_col is None:
                return {}
            
            close_prices = kline_df[close_col]
            
            # 计算历史统计
            current_price = close_prices.iloc[-1]
            max_price = close_prices.max()
            min_price = close_prices.min()
            avg_price = close_prices.mean()
            
            # 计算相对位置
            price_position = (current_price - min_price) / (max_price - min_price) * 100 if max_price != min_price else 50
            
            # 计算近期涨跌
            recent_change = (close_prices.iloc[-1] - close_prices.iloc[-5]) / close_prices.iloc[-5] * 100 if len(close_prices) >= 5 else 0
            
            # 计算涨跌天数
            daily_changes = close_prices.pct_change().dropna()
            up_days = len(daily_changes[daily_changes > 0])
            down_days = len(daily_changes[daily_changes < 0])
            total_days = len(daily_changes)
            
            return {
                'sector_code': sector_code,
                'current_price': current_price,
                'max_price': max_price,
                'min_price': min_price,
                'avg_price': avg_price,
                'price_position': price_position,  # 0-100，表示当前价格在历史区间的位置
                'recent_change_5d': recent_change,  # 近5日涨跌幅
                'up_days': up_days,
                'down_days': down_days,
                'up_ratio': up_days / total_days * 100 if total_days > 0 else 0,
                'data_points': len(kline_df)
            }
            
        except Exception as e:
            logger.error(f"分析板块历史表现失败: {e}")
            return {}


if __name__ == "__main__":
    # 测试
    print("=== 测试基本面数据 ===")
    fundamental = SectorFundamental.get_sector_fundamental_data("新能源车")
    print(f"基本面数据: {fundamental}")
    score = SectorFundamental.analyze_fundamental_score(fundamental)
    print(f"基本面评分: {score}")
    
    print("\n=== 测试关联分析 ===")
    relations = SectorRelationAnalyzer.analyze_sector_relations("新能源车", 
        ["有色金属", "化工", "汽车", "光伏", "芯片"])
    print(f"关联关系: {relations}")
    
    print("\n=== 测试历史分析 ===")
    from logic.akshare_data_loader import AKShareDataLoader
    loader = AKShareDataLoader()
    kline = loader.get_sector_index_kline("BK0447")
    if not kline.empty:
        historical = SectorHistoricalAnalyzer.analyze_historical_performance("BK0447", kline)
        print(f"历史分析: {historical}")
    else:
        print("K线数据为空")
