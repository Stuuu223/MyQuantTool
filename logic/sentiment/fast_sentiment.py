"""
极速情绪分析器 (FastSentimentAnalyzer) - V9.3.8

功能: 基于全市场快照的极速情绪分析
性能: <1s (纯内存计算，复用 V9.3.7 优化后的数据)

核心思想:
- 复用 V9.3.7 优化后的全市场快照数据
- 避免重复调用 AkShare 获取数据
- 一次性计算所有情绪指标

数据源: Easyquotation (实时行情) + DataManager (行业缓存)
算法: 基于日内数据的情绪指数计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from logic.utils.logger import get_logger
from logic.data.data_manager import DataManager
from logic.data.data_cleaner import DataCleaner
from logic.sector_analysis import FastSectorAnalyzer
import akshare as ak

logger = get_logger(__name__)


class FastSentimentAnalyzer:
    """极速情绪分析器
    
    基于全市场快照的情绪分析，无需额外网络请求
    耗时：<1s (纯内存计算)
    """
    
    def __init__(self, db: DataManager):
        """初始化分析器
        
        Args:
            db: DataManager 实例
        """
        self.db = db
        self.sector_analyzer = FastSectorAnalyzer(db)
        self._market_snapshot_cache = None
        self._cache_timestamp = None
    
    def get_market_snapshot(self) -> pd.DataFrame:
        """获取全市场快照数据（复用 FastSectorAnalyzer 的数据）"""
        return self.sector_analyzer.get_market_snapshot()
    
    def get_market_sentiment_index(self) -> Dict:
        """
        获取市场情绪指数（极速版）
        
        指标包括:
        - 涨停数量/跌停数量
        - 连板高度分布
        - 涨停打开率
        - 市场整体情绪评分
        """
        try:
            # 获取市场快照
            df = self.get_market_snapshot()
            
            if df is None or df.empty:
                return {
                    '数据状态': '无数据',
                    '说明': '暂无市场数据'
                }
            
            # 统计涨停数据
            limit_up_stocks = df[df['is_limit_up'] == True]
            zt_count = len(limit_up_stocks)
            
            # 统计跌停数据
            is_20cm = df['code'].str.startswith(('30', '68'))
            import numpy as np
            limit_ratio = np.where(is_20cm, 1.20, 1.10)
            limit_down_price = df['pre_close'] / limit_ratio
            
            limit_down_stocks = df[df['price'] <= limit_down_price]
            dt_count = len(limit_down_stocks)
            
            # 计算情绪指数 (0-100)
            # 涨停数量权重: 40%
            # 跌停数量权重: 30%
            # 平均涨幅权重: 20%
            # 涨停占比权重: 10%
            
            zt_score = min(zt_count / 100 * 40, 40)  # 最多40分
            dt_score = min(dt_count / 100 * 30, 30)  # 最多30分
            
            # 平均涨幅评分
            avg_change = df['pct_chg'].mean()
            change_score = min(avg_change / 10 * 20, 20)
            
            # 涨停占比评分
            total_count = len(df)
            zt_ratio = zt_count / total_count if total_count > 0 else 0
            ratio_score = min(zt_ratio * 100 * 10, 10)
            
            sentiment_score = round(zt_score + dt_score + change_score + ratio_score, 2)
            
            # 情绪等级
            if sentiment_score >= 80:
                sentiment_level = "🔥 极热"
                sentiment_desc = "市场情绪极度亢奋,注意风险"
            elif sentiment_score >= 60:
                sentiment_level = "📈 活跃"
                sentiment_desc = "市场情绪活跃,可以参与"
            elif sentiment_score >= 40:
                sentiment_level = "🟡 一般"
                sentiment_desc = "市场情绪一般,谨慎操作"
            elif sentiment_score >= 20:
                sentiment_level = "📉 情绪低迷"
                sentiment_desc = "市场情绪低迷,观望为主"
            else:
                sentiment_level = "❄️ 冰点"
                sentiment_desc = "市场情绪冰点,机会来临"
            
            # 连板高度分布（简化版，基于涨停次数估算）
            # 由于没有历史数据，这里使用涨停次数作为替代
            board_heights = {}
            if zt_count > 0:
                board_heights = {1: zt_count}  # 假设都是首板
            
            # 涨停打开率（基于涨停数量和跌停数量估算）
            zt_open_rate = round(dt_count / zt_count * 100, 2) if zt_count > 0 else 0
            
            return {
                '数据状态': '正常',
                '情绪指数': sentiment_score,
                '情绪等级': sentiment_level,
                '情绪描述': sentiment_desc,
                '涨停数量': zt_count,
                '涨停打开数': dt_count,
                '涨停打开率': f"{zt_open_rate:.2f}%",
                '连板分布': board_heights,
                '详细数据': limit_up_stocks[['code', 'name', 'price', 'pct_chg', 'industry']].copy()
            }
            
        except Exception as e:
            logger.error(f"获取情绪指数失败: {e}")
            return {
                '数据状态': '异常',
                '说明': f'获取数据失败: {str(e)}'
            }
    
    def analyze_limit_up_stocks(self) -> Dict:
        """
        涨停板深度分析（极速版）
        
        识别龙头股、分析封板强度、统计板块分布
        """
        try:
            # 获取市场快照
            df = self.get_market_snapshot()
            
            if df is None or df.empty:
                return {
                    '数据状态': '无数据',
                    '说明': '暂无市场数据'
                }
            
            # 筛选涨停股票
            limit_up_stocks = df[df['is_limit_up'] == True].copy()
            
            if limit_up_stocks.empty:
                return {
                    '数据状态': '无涨停',
                    '说明': '今日暂无涨停股票'
                }
            
            # 总体统计
            zt_count = len(limit_up_stocks)
            
            # 计算龙头评分（基于涨跌幅、成交额、行业强度）
            # 龙头评分 = 涨跌幅 * 0.4 + 成交额占比 * 0.3 + 行业强度 * 0.3
            
            # 获取板块强度
            sector_ranking = self.sector_analyzer.get_sector_ranking()
            sector_strength_map = {}
            if not sector_ranking.empty:
                sector_strength_map = dict(zip(
                    sector_ranking['industry'],
                    sector_ranking['strength_score']
                ))
            
            # 计算龙头评分
            limit_up_stocks['sector_strength'] = limit_up_stocks['industry'].map(
                lambda x: sector_strength_map.get(x, 0)
            )
            
            # 成交额占比
            total_amount = limit_up_stocks['amount'].sum()
            limit_up_stocks['amount_ratio'] = limit_up_stocks['amount'] / total_amount if total_amount > 0 else 0
            
            # 龙头评分
            limit_up_stocks['dragon_score'] = (
                limit_up_stocks['pct_chg'] * 0.4 +
                limit_up_stocks['amount_ratio'] * 100 * 0.3 +
                limit_up_stocks['sector_strength'] * 0.3
            )
            
            # 按龙头评分排序
            limit_up_stocks = limit_up_stocks.sort_values('dragon_score', ascending=False)
            
            # 龙头股（评分前10）
            dragon_stocks = limit_up_stocks.head(10).copy()
            dragon_stocks['龙头评分'] = dragon_stocks['dragon_score'].round(2)
            
            # 板块分布
            sector_distribution = limit_up_stocks['industry'].value_counts().to_dict()
            
            # 连板统计（简化版，基于涨停次数）
            board_distribution = {1: zt_count}
            
            # 详细数据
            detail_df = limit_up_stocks[['code', 'name', 'price', 'pct_chg', 'industry', 'amount', 'dragon_score']].copy()
            
            return {
                '数据状态': '正常',
                '涨停总数': zt_count,
                '龙头股': dragon_stocks[['code', 'name', 'price', 'pct_chg', 'industry', 'dragon_score']].to_dict('records'),
                '板块分布': sector_distribution,
                '连板统计': board_distribution,
                '详细数据': detail_df
            }
            
        except Exception as e:
            logger.error(f"涨停板分析失败: {e}")
            return {
                '数据状态': '异常',
                '说明': f'分析失败: {str(e)}'
            }
    
    def analyze_sentiment_cycle(self) -> Dict:
        """
        情绪周期分析（极速版）
        
        情绪周期五阶段论:冰点期→复苏期→活跃期→高潮期→退潮期
        """
        try:
            # 获取情绪指数
            sentiment_data = self.get_market_sentiment_index()
            
            if sentiment_data['数据状态'] != '正常':
                return sentiment_data
            
            sentiment_score = sentiment_data['情绪指数']
            zt_count = sentiment_data['涨停数量']
            
            # 确定情绪周期阶段
            if sentiment_score >= 80:
                cycle_stage = "高潮期"
                stage_desc = "市场情绪极度亢奋，涨停数量多，连板高度高"
                features = ["涨停数量众多", "连板高度突破", "资金疯狂涌入", "风险快速积累"]
                advice = "注意风险，考虑减仓，不要追高"
                space_board_height = "5+"
            elif sentiment_score >= 60:
                cycle_stage = "活跃期"
                stage_desc = "市场情绪活跃，涨停数量增加，连板高度提升"
                features = ["涨停数量增加", "连板高度提升", "板块轮动加快", "赚钱效应明显"]
                advice = "积极操作，把握机会，控制仓位"
                space_board_height = "3-4"
            elif sentiment_score >= 40:
                cycle_stage = "复苏期"
                stage_desc = "市场情绪开始复苏，涨停数量增多，连板高度恢复"
                features = ["涨停数量开始增多", "连板高度恢复", "板块开始活跃", "赚钱效应显现"]
                advice = "可以开始参与，轻仓试错，寻找机会"
                space_board_height = "2-3"
            elif sentiment_score >= 20:
                cycle_stage = "退潮期"
                stage_desc = "市场情绪开始退潮，涨停数量减少，连板高度下降"
                features = ["涨停数量减少", "连板高度下降", "炸板率上升", "亏钱效应显现"]
                advice = "谨慎操作，控制风险，观望为主"
                space_board_height = "1-2"
            else:
                cycle_stage = "冰点期"
                stage_desc = "市场情绪极度低迷，涨停数量极少，连板高度消失"
                features = ["涨停数量极少", "连板高度消失", "炸板率极高", "亏钱效应明显"]
                advice = "耐心等待，不要参与，准备抄底"
                space_board_height = "0"
            
            return {
                '数据状态': '正常',
                '情绪周期阶段': cycle_stage,
                '阶段描述': stage_desc,
                '周期特征': features,
                '操作建议': advice,
                '空间板高度': space_board_height,
                '情绪指数': sentiment_score,
                '情绪等级': sentiment_data['情绪等级'],
                '涨停数量': zt_count,
                '连板分布': sentiment_data['连板分布']
            }
            
        except Exception as e:
            logger.error(f"情绪周期分析失败: {e}")
            return {
                '数据状态': '异常',
                '说明': f'分析失败: {str(e)}'
            }


def get_fast_sentiment_analyzer(db: DataManager) -> FastSentimentAnalyzer:
    """获取极速情绪分析器实例（单例模式）
    
    Args:
        db: DataManager 实例
        
    Returns:
        FastSentimentAnalyzer 实例
    """
    if not hasattr(get_fast_sentiment_analyzer, '_instance'):
        get_fast_sentiment_analyzer._instance = FastSentimentAnalyzer(db)
    return get_fast_sentiment_analyzer._instance


if __name__ == '__main__':
    # 测试代码
    from logic.data.data_manager import DataManager
    
    print("=" * 60)
    print("🧪 测试 FastSentimentAnalyzer")
    print("=" * 60)
    
    db = DataManager()
    analyzer = FastSentimentAnalyzer(db)
    
    print("\n📊 正在获取情绪指数...")
    import time
    t_start = time.time()
    sentiment_index = analyzer.get_market_sentiment_index()
    t_cost = time.time() - t_start
    
    print(f"✅ 计算完成！耗时: {t_cost:.2f} 秒")
    
    if sentiment_index['数据状态'] == '正常':
        print(f"情绪指数: {sentiment_index['情绪指数']}")
        print(f"情绪等级: {sentiment_index['情绪等级']}")
        print(f"涨停数量: {sentiment_index['涨停数量']}")
    
    print("\n" + "=" * 60)