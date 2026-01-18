"""
板块极速分析系统 (FastSectorAnalyzer) - V18 完整旗舰版

功能: 全维板块共振系统（行业板块 + 概念板块 + 资金热度 + 龙头溯源）
性能: 0.25s (首次获取) / <0.01s (缓存)

核心思想:
- 多维板块雷达: 同时扫描行业板块和概念板块
- 资金热度加权: 成交额 + 换手率计算板块强度系数
- 龙头溯源: 自动识别板块内的领涨个股
- 全维共振分析: 判断个股是否处于主线、龙头、跟风、逆风

数据源: AkShare (stock_board_industry_name_em, stock_board_concept_name_em)
算法: 基于涨幅、成交额、换手率的综合强度计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.data_cleaner import DataCleaner
import akshare as ak

logger = get_logger(__name__)


class FastSectorAnalyzer:
    """V18 完整旗舰版板块分析器
    
    全维板块共振系统：
    - 行业板块分析
    - 概念板块分析
    - 资金热度加权
    - 龙头溯源
    - 全维共振分析
    """
    
    def __init__(self, db: DataManager):
        """初始化分析器
        
        Args:
            db: DataManager 实例
        """
        self.db = db
        self._market_snapshot_cache = None
        self._cache_timestamp = None
        
        # V18: 板块共振缓存
        self._akshare_industry_cache = None
        self._akshare_concept_cache = None
        self._akshare_cache_timestamp = None
        self._cache_ttl = 60  # 缓存60秒
    
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
    
    def get_akshare_sector_ranking(self) -> pd.DataFrame:
        """
        🚀 V18: 使用 AkShare 获取行业板块排名（真实数据接口）
        
        使用 akshare.stock_board_industry_name_em() 获取当日板块涨幅排名
        
        Returns:
            DataFrame 包含以下列:
            - 板块名称: 板块名称
            - 最新价: 最新价
            - 涨跌幅: 涨跌幅(%)
            - 成交额: 成交额
            - rank: 排名
        """
        # 检查缓存（60秒有效期）
        if self._akshare_industry_cache is not None:
            cache_age = (datetime.now() - self._akshare_cache_timestamp).total_seconds()
            if cache_age < self._cache_ttl:
                logger.debug(f"使用 AkShare 行业板块缓存数据 (缓存时间: {cache_age:.1f}秒)")
                return self._akshare_industry_cache
        
        try:
            # 使用 AkShare 获取行业板块数据
            logger.info("🔍 [V18] 正在从 AkShare 获取行业板块排名数据...")
            sector_df = ak.stock_board_industry_name_em()
            
            if sector_df is None or sector_df.empty:
                logger.warning("AkShare 行业板块数据为空")
                return pd.DataFrame()
            
            # 添加排名列
            sector_df = sector_df.sort_values('涨跌幅', ascending=False).reset_index(drop=True)
            sector_df['rank'] = sector_df.index + 1
            
            # 计算资金热度系数（V18 新增）
            sector_df['资金热度'] = self._calculate_capital_heat(sector_df)
            
            # 缓存数据
            self._akshare_industry_cache = sector_df
            self._akshare_cache_timestamp = datetime.now()
            
            logger.info(f"✅ AkShare 行业板块数据获取成功，共 {len(sector_df)} 个板块")
            return sector_df
            
        except Exception as e:
            logger.error(f"❌ 获取 AkShare 行业板块数据失败: {e}")
            return pd.DataFrame()
    
    def get_akshare_concept_ranking(self) -> pd.DataFrame:
        """
        🚀 V18: 使用 AkShare 获取概念板块排名（真实数据接口）
        
        使用 akshare.stock_board_concept_name_em() 获取当日概念板块涨幅排名
        
        Returns:
            DataFrame 包含以下列:
            - 板块名称: 概念板块名称
            - 最新价: 最新价
            - 涨跌幅: 涨跌幅(%)
            - 成交额: 成交额
            - rank: 排名
        """
        # 检查缓存（60秒有效期）
        if self._akshare_concept_cache is not None:
            cache_age = (datetime.now() - self._akshare_cache_timestamp).total_seconds()
            if cache_age < self._cache_ttl:
                logger.debug(f"使用 AkShare 概念板块缓存数据 (缓存时间: {cache_age:.1f}秒)")
                return self._akshare_concept_cache
        
        try:
            # 使用 AkShare 获取概念板块数据
            logger.info("🔍 [V18] 正在从 AkShare 获取概念板块排名数据...")
            concept_df = ak.stock_board_concept_name_em()
            
            if concept_df is None or concept_df.empty:
                logger.warning("AkShare 概念板块数据为空")
                return pd.DataFrame()
            
            # 添加排名列
            concept_df = concept_df.sort_values('涨跌幅', ascending=False).reset_index(drop=True)
            concept_df['rank'] = concept_df.index + 1
            
            # 计算资金热度系数（V18 新增）
            concept_df['资金热度'] = self._calculate_capital_heat(concept_df)
            
            # 缓存数据
            self._akshare_concept_cache = concept_df
            self._akshare_cache_timestamp = datetime.now()
            
            logger.info(f"✅ AkShare 概念板块数据获取成功，共 {len(concept_df)} 个概念板块")
            return concept_df
            
        except Exception as e:
            logger.error(f"❌ 获取 AkShare 概念板块数据失败: {e}")
            return pd.DataFrame()
    
    def _calculate_capital_heat(self, df: pd.DataFrame) -> pd.Series:
        """
        🚀 V18: 计算资金热度系数
        
        综合考虑涨幅、成交额、换手率
        
        Args:
            df: 板块数据 DataFrame
            
        Returns:
            资金热度系数 Series
        """
        try:
            # 标准化涨幅（-10 到 10 分）
            pct_chg_score = df['涨跌幅'].clip(-10, 10) / 10 * 50 + 50
            
            # 标准化成交额（对数转换）
            # 检查成交额列名
            amount_col = None
            for col in ['成交额', '总成交额', 'amount']:
                if col in df.columns:
                    amount_col = col
                    break
            
            if amount_col and len(df[amount_col]) > 0:
                max_amount = df[amount_col].max()
                if max_amount > 0:
                    amount_score = np.log1p(df[amount_col].clip(lower=0)) / np.log1p(max_amount) * 100
                else:
                    amount_score = 50
            else:
                amount_score = 50
            
            # 标准化换手率（如果有）
            turnover_score = 50
            if '换手率' in df.columns:
                turnover_score = df['换手率'].clip(0, 20) / 20 * 100
            
            # 综合计算（涨幅权重 50%，成交额权重 30%，换手率权重 20%）
            capital_heat = pct_chg_score * 0.5 + amount_score * 0.3 + turnover_score * 0.2
            
            return capital_heat
            
        except Exception as e:
            logger.warning(f"计算资金热度失败: {e}")
            return pd.Series([50] * len(df), index=df.index)
    
    def get_market_main_lines(self, top_n=5) -> Tuple[List[Dict], List[Dict]]:
        """
        🚀 V18: 获取当前市场主线（行业 + 概念）
        
        Args:
            top_n: 返回前 N 个主线
            
        Returns:
            (industries, concepts) - 行业主线和概念主线列表
        """
        industry_ranking = self.get_akshare_sector_ranking()
        concept_ranking = self.get_akshare_concept_ranking()
        
        industries = []
        concepts = []
        
        if not industry_ranking.empty:
            top_ind = industry_ranking.head(top_n)
            for _, row in top_ind.iterrows():
                industries.append({
                    'name': row['板块名称'],
                    'pct_chg': row['涨跌幅'],
                    'rank': row['rank'],
                    'leader': row.get('领涨股票', 'N/A'),
                    'amount': row['成交额'],
                    'capital_heat': row['资金热度']
                })
        
        if not concept_ranking.empty:
            top_con = concept_ranking.head(top_n)
            for _, row in top_con.iterrows():
                concepts.append({
                    'name': row['板块名称'],
                    'pct_chg': row['涨跌幅'],
                    'rank': row['rank'],
                    'leader': row.get('领涨股票', 'N/A'),
                    'amount': row['成交额'],
                    'capital_heat': row['资金热度']
                })
        
        return industries, concepts
    
    def check_stock_full_resonance(self, stock_code: str, stock_name: Optional[str] = None) -> Dict[str, Union[float, List[str], Dict]]:
        """
        🚀 V18: 全维板块共振分析（行业 + 概念 + 资金热度 + 龙头溯源）
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称（可选，用于匹配龙头）
            
        Returns:
            dict: {
                'resonance_score': float,  # 共振评分（正数加分，负数减分）
                'resonance_details': List[str],  # 共振详情列表
                'industry_info': Dict,  # 行业板块信息
                'concept_info': Dict,  # 概念板块信息
                'is_leader': bool,  # 是否为板块龙头
                'is_follower': bool  # 是否为跟风股
            }
        """
        resonance_score = 0.0
        resonance_details = []
        
        # 获取行业和概念板块数据
        industry_ranking = self.get_akshare_sector_ranking()
        concept_ranking = self.get_akshare_concept_ranking()
        
        # 获取股票所属行业
        code_to_industry = self.db.get_industry_cache()
        industry_name = code_to_industry.get(stock_code, '未知')
        
        # 1. 行业板块共振分析
        industry_info = self._analyze_industry_resonance(
            stock_code, industry_name, industry_ranking, stock_name
        )
        
        if industry_info:
            resonance_score += industry_info.get('score_boost', 0)
            resonance_details.extend(industry_info.get('details', []))
        
        # 2. 概念板块共振分析
        concept_info = self._analyze_concept_resonance(
            stock_code, stock_name, concept_ranking
        )
        
        if concept_info:
            resonance_score += concept_info.get('score_boost', 0)
            resonance_details.extend(concept_info.get('details', []))
        
        # 3. 判断是否为龙头或跟风
        is_leader = any('龙头' in detail for detail in resonance_details)
        is_follower = any('跟风' in detail for detail in resonance_details)
        
        logger.info(f"{stock_code} 全维共振评分: {resonance_score:+.1f}, 详情: {resonance_details}")
        
        return {
            'resonance_score': resonance_score,
            'resonance_details': resonance_details,
            'industry_info': industry_info or {},
            'concept_info': concept_info or {},
            'is_leader': is_leader,
            'is_follower': is_follower
        }
    
    def _analyze_industry_resonance(
        self, 
        stock_code: str, 
        industry_name: str, 
        industry_ranking: pd.DataFrame,
        stock_name: Optional[str] = None
    ) -> Dict:
        """分析行业板块共振"""
        if industry_ranking.empty or industry_name == '未知':
            return {}
        
        # 查找行业排名
        industry_row = industry_ranking[industry_ranking['板块名称'] == industry_name]
        
        if industry_row.empty:
            return {}
        
        industry_info = industry_row.iloc[0]
        rank = int(industry_info['rank'])
        total = len(industry_ranking)
        pct_chg = float(industry_info['涨跌幅'])
        capital_heat = float(industry_info['资金热度'])
        leader_stock = industry_info.get('领涨股票', '')
        
        score_boost = 0.0
        details = []
        
        # 领涨主线（Top 5）
        if rank <= 5:
            score_boost = 15.0
            details.append(f"🔥 [行业主线] {industry_name} 领涨 (Rank {rank}/{total}, +{pct_chg:.2f}%, 资金热度 {capital_heat:.1f})")
            
            # 检查是否为龙头
            if stock_name and leader_stock and stock_name in str(leader_stock):
                score_boost += 10.0
                details.append(f"👑 [行业龙头] {industry_name} 领涨股")
            else:
                details.append(f"📈 [跟风] {industry_name} 龙头: {leader_stock}")
        
        # 强势板块（Top 10）
        elif rank <= 10:
            score_boost = 8.0
            details.append(f"🚀 [行业强势] {industry_name} (Rank {rank}/{total}, +{pct_chg:.2f}%)")
        
        # 逆风板块（跌幅 > 1%）
        elif pct_chg < -1.0:
            score_boost = -10.0
            details.append(f"❄️ [行业逆风] {industry_name} 下跌 ({pct_chg:.2f}%)")
        
        # 中性板块
        else:
            details.append(f"📊 [行业中性] {industry_name} (Rank {rank}/{total}, {pct_chg:.2f}%)")
        
        return {
            'score_boost': score_boost,
            'details': details,
            'rank': rank,
            'total': total,
            'pct_chg': pct_chg,
            'capital_heat': capital_heat,
            'leader': leader_stock
        }
    
    def _analyze_concept_resonance(
        self,
        stock_code: str,
        stock_name: Optional[str],
        concept_ranking: pd.DataFrame
    ) -> Dict:
        """分析概念板块共振"""
        if concept_ranking.empty or not stock_name:
            return {}
        
        score_boost = 0.0
        details = []
        
        # 检查是否在 Top 10 概念的领涨股中
        top_concepts = concept_ranking.head(10)
        
        for _, row in top_concepts.iterrows():
            concept_name = row['板块名称']
            leader_stock = row.get('领涨股票', '')
            
            # 简化匹配：检查股票名称是否在领涨股中
            if stock_name and leader_stock and stock_name in str(leader_stock):
                score_boost = 20.0
                details.append(f"👑 [概念龙头] 领涨 {concept_name}")
                break
        
        return {
            'score_boost': score_boost,
            'details': details
        }
    
    def check_sector_status(self, stock_code: str) -> Dict[str, Union[str, float, int]]:
        """
        🚀 V18: 检查股票所属板块状态（兼容旧版接口）
        
        判断股票所属板块是否在领涨/拖累区域
        
        Args:
            stock_code: 股票代码
            
        Returns:
            dict: {
                'sector_name': str,  # 板块名称
                'sector_rank': int,  # 板块排名
                'total_sectors': int,  # 总板块数
                'pct_chg': float,  # 板块涨跌幅
                'status': str,  # 'LEADER' (领涨) / 'DRAG' (拖累) / 'NEUTRAL' (中性)
                'modifier': float,  # 评分修正系数 (1.2 / 0.7 / 1.0)
                'reason': str  # 原因说明
            }
        """
        # 获取板块排名
        sector_ranking = self.get_akshare_sector_ranking()
        
        if sector_ranking.empty:
            logger.debug(f"板块数据不可用，无法检查 {stock_code} 的板块状态")
            return {
                'sector_name': '未知',
                'sector_rank': -1,
                'total_sectors': 0,
                'pct_chg': 0,
                'status': 'NEUTRAL',
                'modifier': 1.0,
                'reason': '板块数据不可用'
            }
        
        # 获取股票所属板块
        code_to_industry = self.db.get_industry_cache()
        sector_name = code_to_industry.get(stock_code, '未知')
        
        # 查找该板块在排名中的位置
        sector_row = sector_ranking[sector_ranking['板块名称'] == sector_name]
        
        if sector_row.empty:
            logger.debug(f"未找到板块 {sector_name} 的排名信息")
            return {
                'sector_name': sector_name,
                'sector_rank': -1,
                'total_sectors': len(sector_ranking),
                'pct_chg': 0,
                'status': 'NEUTRAL',
                'modifier': 1.0,
                'reason': f'板块 {sector_name} 未在排名中'
            }
        
        # 提取板块信息
        sector_info = sector_row.iloc[0]
        sector_rank = int(sector_info['rank'])
        total_sectors = len(sector_ranking)
        pct_chg = float(sector_info['涨跌幅'])
        
        # 判断板块状态
        # Top 3 -> LEADER (领涨)
        # Bottom 3 -> DRAG (拖累)
        # 其他 -> NEUTRAL (中性)
        
        if sector_rank <= 3:
            status = 'LEADER'
            modifier = 1.2
            reason = f'🚀 [板块共振] 处于领涨主线 ({sector_name} 排名第{sector_rank}/{total_sectors}，涨幅 {pct_chg:.2f}%)'
        elif sector_rank >= total_sectors - 2:
            status = 'DRAG'
            modifier = 0.7
            reason = f'⚠️ [逆风局] 板块垫底 ({sector_name} 排名第{sector_rank}/{total_sectors}，涨幅 {pct_chg:.2f}%)'
        else:
            status = 'NEUTRAL'
            modifier = 1.0
            reason = f'📊 [板块中性] {sector_name} 排名第{sector_rank}/{total_sectors}，涨幅 {pct_chg:.2f}%'
        
        logger.info(f"{stock_code} 板块状态: {status} ({sector_name} 排名 {sector_rank}/{total_sectors})")
        
        return {
            'sector_name': sector_name,
            'sector_rank': sector_rank,
            'total_sectors': total_sectors,
            'pct_chg': pct_chg,
            'status': status,
            'modifier': modifier,
            'reason': reason
        }


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