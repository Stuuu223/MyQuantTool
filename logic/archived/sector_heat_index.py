"""
板块热度指数计算模块

功能：计算板块热度指数，基于多个维度综合评估
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class SectorHeatIndex:
    """板块热度指数计算类"""
    
    @staticmethod
    def calculate_heat_index(sector_data: Dict[str, Any]) -> float:
        """
        计算板块热度指数
        
        Args:
            sector_data: 板块数据字典，包含以下字段：
                - 涨跌幅
                - 成交额
                - 涨跌家数
                - 涨停家数
                - 主力净流入
                
        Returns:
            float: 热度指数 (0-100)
        """
        try:
            score = 0.0
            
            # 1. 涨跌幅权重 (25%)
            price_change = sector_data.get('涨跌幅', 0)
            if price_change > 0:
                score += min(price_change * 5, 25)  # 最高25分
            
            # 2. 成交额权重 (20%)
            turnover = sector_data.get('成交额', 0)
            if turnover > 0:
                # 归一化处理，假设1e10为最大值
                score += min(turnover / 1e10 * 20, 20)
            
            # 3. 涨跌比例权重 (25%)
            up_count = sector_data.get('up_count', 0)
            down_count = sector_data.get('down_count', 0)
            total_count = up_count + down_count
            if total_count > 0:
                up_ratio = up_count / total_count
                score += up_ratio * 25
            
            # 4. 涨停家数权重 (15%)
            limit_up_count = sector_data.get('limit_up_count', 0)
            if limit_up_count > 0:
                score += min(limit_up_count * 3, 15)  # 每只涨停股3分，最高15分
            
            # 5. 主力净流入权重 (15%)
            main_net_inflow = sector_data.get('main_net_inflow', 0)
            if main_net_inflow > 0:
                # 归一化处理，假设1e9为最大值
                score += min(main_net_inflow / 1e9 * 15, 15)
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"计算热度指数失败: {e}")
            return 0.0
    
    @staticmethod
    def get_heat_level(score: float) -> str:
        """
        获取热度等级
        
        Args:
            score: 热度指数
            
        Returns:
            str: 热度等级
        """
        if score >= 80:
            return "极热"
        elif score >= 60:
            return "热门"
        elif score >= 40:
            return "活跃"
        elif score >= 20:
            return "一般"
        else:
            return "冷淡"
    
    @staticmethod
    def calculate_all_sectors_heat(industry_df: pd.DataFrame, 
                                   sector_stats: Dict[str, Dict]) -> pd.DataFrame:
        """
        计算所有板块的热度指数
        
        Args:
            industry_df: 行业板块数据
            sector_stats: 板块统计数据
            
        Returns:
            pd.DataFrame: 包含热度指数的数据框
        """
        try:
            results = []
            
            for _, row in industry_df.iterrows():
                sector_name = row.get('名称', '')
                sector_code = row.get('代码', '')
                
                # 获取该板块的统计数据
                stats = sector_stats.get(sector_code, {})
                
                # 构建板块数据
                sector_data = {
                    '涨跌幅': float(row.get('涨跌幅', 0) or 0),
                    '成交额': float(row.get('成交额', 0) or 0),
                    'up_count': stats.get('up_count', 0),
                    'down_count': stats.get('down_count', 0),
                    'limit_up_count': stats.get('limit_up_count', 0),
                    'main_net_inflow': stats.get('main_net_inflow', 0)
                }
                
                # 计算热度指数
                heat_score = SectorHeatIndex.calculate_heat_index(sector_data)
                heat_level = SectorHeatIndex.get_heat_level(heat_score)
                
                results.append({
                    '板块名称': sector_name,
                    '板块代码': sector_code,
                    '热度指数': heat_score,
                    '热度等级': heat_level,
                    '涨跌幅': sector_data['涨跌幅'],
                    '成交额': sector_data['成交额']
                })
            
            df = pd.DataFrame(results)
            df = df.sort_values('热度指数', ascending=False)
            
            return df
            
        except Exception as e:
            logger.error(f"计算所有板块热度指数失败: {e}")
            return pd.DataFrame()


if __name__ == "__main__":
    # 测试
    from logic.akshare_data_loader import AKShareDataLoader
    
    # 获取行业板块数据
    loader = AKShareDataLoader()
    industry_df = loader.get_industry_spot()
    
    if not industry_df.empty:
        print(f"获取到 {len(industry_df)} 个行业板块")
        
        # 模拟统计数据
        sector_stats = {}
        for _, row in industry_df.head(5).iterrows():
            code = row.get('代码', '')
            sector_stats[code] = {
                'up_count': np.random.randint(10, 50),
                'down_count': np.random.randint(5, 30),
                'limit_up_count': np.random.randint(0, 5),
                'main_net_inflow': np.random.uniform(-1e8, 1e9)
            }
        
        # 计算热度指数
        heat_df = SectorHeatIndex.calculate_all_sectors_heat(industry_df, sector_stats)
        
        print("\n板块热度指数:")
        print(heat_df)
    else:
        print("行业板块数据为空")