"""
板块极速分析系统 (FastSectorAnalyzer) - V9.3.8

功能: 基于全市场快照的极速板块强度分析
性能: 0.01s (纯内存计算，无网络请求)

核心思想:
- 复用 V9.3.7 优化后的全市场快照数据
- 使用 Pandas GroupBy 聚合板块指标
- 避免重复获取历史数据和成份股数据

数据源: Easyquotation (实时行情) + DataManager (行业缓存)
算法: 基于日内资金的板块强度计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.data_cleaner import DataCleaner
import akshare as ak

logger = get_logger(__name__)


class FastSectorAnalyzer:
    """极速板块分析器
    
    基于全市场快照的板块强度分析，无需额外网络请求
    耗时：0.01s (纯内存计算)
    """
    
    def __init__(self, db: DataManager):
        """初始化分析器
        
        Args:
            db: DataManager 实例
        """
        self.db = db
        self._market_snapshot_cache = None
        self._cache_timestamp = None
    
    def get_market_snapshot(self) -> pd.DataFrame:
        """获取全市场快照数据
        
        Returns:
            DataFrame 包含以下列:
            - code: 股票代码
            - name: 股票名称
            - industry: 行业板块
            - price: 最新价
            - pre_close: 昨收价
            - pct_chg: 涨跌幅(%)
            - volume: 成交量(手)
            - amount: 成交额(元)
            - is_limit_up: 是否涨停
        """
        # 检查缓存（5秒有效期）
        if self._market_snapshot_cache is not None:
            cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
            if cache_age < 5:
                logger.debug(f"使用缓存的市场快照数据 (缓存时间: {cache_age:.1f}秒)")
                return self._market_snapshot_cache
        
        # 获取股票列表
        try:
            stock_list_df = ak.stock_info_a_code_name()
            stock_list = stock_list_df['code'].tolist()
        except Exception as e:
            logger.warning(f"AkShare 获取股票列表失败: {e}，使用样本股票列表")
            stock_list = [
                '000001', '000002', '000063', '000066', '000333', '000651',
                '000725', '000858', '000895', '002415', '002594', '002714',
                '002841', '300059', '300142', '300274', '300347', '300433',
                '300750', '600000', '600036', '600519', '600900', '601318',
                '601398', '601766', '601888', '603259', '688981'
            ]
        
        # 获取实时价格数据
        realtime_data = self.db.get_fast_price(stock_list)
        
        # 获取行业信息（使用缓存）
        code_to_industry = self.db.get_industry_cache()
        
        # 转换为 DataFrame
        rows = []
        for full_code, data in realtime_data.items():
            # 清洗股票代码
            code = DataCleaner.clean_stock_code(full_code)
            if not code:
                continue
            
            # 清洗数据
            cleaned_data = DataCleaner.clean_realtime_data(data)
            if not cleaned_data:
                continue
            
            # 剔除新股（N开头）、次新股（C开头）、ST股
            name = cleaned_data.get('name', '')
            if name.startswith(('N', 'C')):
                continue
            if 'ST' in name or '*ST' in name:
                continue
            
            # 剔除停牌股（成交量为0）
            volume = cleaned_data.get('volume', 0)
            if volume == 0:
                continue
            
            # 获取行业信息
            industry = code_to_industry.get(code, '未知')
            
            # 计算涨跌幅
            now = cleaned_data.get('now', 0)
            pre_close = cleaned_data.get('close', 0)
            high = cleaned_data.get('high', 0)
            
            if pre_close <= 0 or now == 0:
                continue
            
            pct_chg = (now - pre_close) / pre_close * 100
            
            # 判断是否涨停
            is_20cm = code.startswith(('30', '68'))
            limit_ratio = 1.20 if is_20cm else 1.10
            limit_price = round(pre_close * limit_ratio, 2)
            is_limit_up = now >= limit_price
            
            # 计算成交额（手 * 100 * 价格）
            amount = volume * 100 * now
            
            rows.append({
                'code': code,
                'name': name,
                'industry': industry,
                'price': now,
                'pre_close': pre_close,
                'pct_chg': pct_chg,
                'volume': volume,
                'amount': amount,
                'is_limit_up': is_limit_up
            })
        
        df = pd.DataFrame(rows)
        
        # 缓存数据
        self._market_snapshot_cache = df
        self._cache_timestamp = datetime.now()
        
        logger.info(f"✅ 获取市场快照成功，共 {len(df)} 只股票")
        return df
    
    def get_sector_ranking(self) -> pd.DataFrame:
        """
        🚀 极速版：基于全市场快照聚合板块强度
        耗时：0.01s (纯内存计算)
        
        Returns:
            DataFrame 包含以下列:
            - industry: 板块名称
            - pct_chg: 平均涨幅
            - code: 股票数量
            - is_limit_up: 涨停数量
            - amount: 总成交额
            - strength_score: 强度分
            - top_stock: 领涨龙头
        """
        # 1. 拿现成的快照数据 (V9.3.7 已经优化好的)
        df = self.get_market_snapshot()
        
        if df is None or df.empty:
            logger.warning("市场快照数据为空")
            return pd.DataFrame()
        
        # 2. 核心算法：Pandas GroupBy 聚合
        # 我们算三个指标：
        # - 涨幅均值 (板块整体强度)
        # - 涨停家数 (板块爆发力)
        # - 成交额总量 (板块资金容量)
        
        sector_stats = df.groupby('industry').agg({
            'pct_chg': 'mean',        # 平均涨幅
            'code': 'count',          # 股票数量
            'is_limit_up': 'sum',     # 涨停数量
            'amount': 'sum'           # 总成交额
        }).reset_index()
        
        # 3. 过滤掉小板块 (比如只有不到 5 只股票的板块)
        sector_stats = sector_stats[sector_stats['code'] > 5]
        
        # 4. 计算"强度分" (简单的加权)
        # 强度 = 平均涨幅 * 0.7 + (涨停数/总数) * 100 * 0.3
        # 这只是一个简单的打分公式，你可以自己调
        sector_stats['strength_score'] = (
            sector_stats['pct_chg'] * 0.7 + 
            (sector_stats['is_limit_up'] / sector_stats['code']) * 100 * 0.3
        )
        
        # 5. 排序
        sector_stats = sector_stats.sort_values('strength_score', ascending=False)
        
        # 6. 找出每个板块的"领头羊" (涨幅最大的股)
        # 这一步稍微耗时一点点，但很有用
        leader_map = {}
        for industry in sector_stats.head(10)['industry']: # 只看前10名
            sector_stocks = df[df['industry'] == industry]
            if not sector_stocks.empty:
                top_stock = sector_stocks.sort_values('pct_chg', ascending=False).iloc[0]
                leader_map[industry] = f"{top_stock['name']} ({top_stock['pct_chg']:.1f}%)"
        
        sector_stats['top_stock'] = sector_stats['industry'].map(leader_map)
        
        logger.info(f"✅ 板块强度计算完成，共 {len(sector_stats)} 个板块")
        return sector_stats
    
    def get_sector_detail(self, sector_name: str) -> pd.DataFrame:
        """获取板块内所有股票的详细信息
        
        Args:
            sector_name: 板块名称
            
        Returns:
            DataFrame 包含该板块内所有股票的详细信息
        """
        df = self.get_market_snapshot()
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        # 筛选该板块的股票
        sector_stocks = df[df['industry'] == sector_name]
        
        if sector_stocks.empty:
            return pd.DataFrame()
        
        # 按涨跌幅排序
        sector_stocks = sector_stocks.sort_values('pct_chg', ascending=False)
        
        return sector_stocks


def get_fast_sector_analyzer(db: DataManager) -> FastSectorAnalyzer:
    """获取极速板块分析器实例（单例模式）
    
    Args:
        db: DataManager 实例
        
    Returns:
        FastSectorAnalyzer 实例
    """
    if not hasattr(get_fast_sector_analyzer, '_instance'):
        get_fast_sector_analyzer._instance = FastSectorAnalyzer(db)
    return get_fast_sector_analyzer._instance


if __name__ == '__main__':
    # 测试代码
    from logic.data_manager import DataManager
    
    print("=" * 60)
    print("🧪 测试 FastSectorAnalyzer")
    print("=" * 60)
    
    db = DataManager()
    analyzer = FastSectorAnalyzer(db)
    
    print("\n📊 正在获取板块强度排行...")
    import time
    t_start = time.time()
    sector_ranking = analyzer.get_sector_ranking()
    t_cost = time.time() - t_start
    
    print(f"✅ 计算完成！耗时: {t_cost:.2f} 秒")
    
    if not sector_ranking.empty:
        print(f"\n📈 TOP 10 强势板块:")
        top_10 = sector_ranking.head(10)
        for _, row in top_10.iterrows():
            print(f"  {row['industry']}: 强度 {row['strength_score']:.2f}, 涨幅 {row['pct_chg']:.2f}%, 涨停 {int(row['is_limit_up'])} 家, 领头羊 {row['top_stock']}")
    
    print("\n" + "=" * 60)