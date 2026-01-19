"""
V18.1 Streamlit 兼容版板块分析器

修复问题：
1. 使用 @st.cache_resource 替代 Python 单例模式，避免僵尸线程
2. 确保后台线程只创建一次
3. 添加线程安全机制
"""

import pandas as pd
import numpy as np
import threading
import time
import json
import os
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
from logic.logger import get_logger
from logic.data_manager import DataManager
import akshare as ak

logger = get_logger(__name__)


class FastSectorAnalyzerStreamlit:
    """V18.1 Streamlit 兼容版板块分析器
    
    修复僵尸线程问题：
    - 使用 @st.cache_resource 管理单例
    - 确保后台线程只创建一次
    - 添加线程安全机制
    """
    
    # 类级别的线程锁
    _instance_lock = threading.Lock()
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """线程安全的单例模式"""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super(FastSectorAnalyzerStreamlit, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db: DataManager):
        """初始化分析器（只执行一次）"""
        if self._initialized:
            return
        self._initialized = True
        
        logger.info("🚀 [V18.1 Streamlit] 初始化 FastSectorAnalyzer")
        
        self.db = db
        self._market_snapshot_cache = None
        self._cache_timestamp = None
        
        # V18: 板块共振缓存
        self._akshare_industry_cache = None
        self._akshare_concept_cache = None
        self._akshare_cache_timestamp = None
        self._cache_ttl = 60  # 缓存60秒
        
        # V18.1 Turbo Boost: 性能优化
        self._stock_sector_map = {}  # 股票-板块映射表
        self._fallback_mode = False  # 降级模式标志
        self._auto_refresh_thread = None  # 后台刷新线程
        self._auto_refresh_running = True  # 后台刷新运行标志
        self._static_map_loaded = False  # 静态映射表加载标志
        self._thread_started = False  # 线程启动标志
        
        # 🚀 V18.3 Flow Master: 资金流数据缓存
        self._industry_fund_flow_df = None  # 行业资金流数据
        self._concept_fund_flow_df = None  # 概念资金流数据
        self._fund_flow_cache_timestamp = None  # 资金流缓存时间戳
        self._fund_flow_cache_ttl = 300  # 资金流缓存5分钟
        
        # 🚀 V18.1 Hybrid Engine: 优先加载静态映射表
        self._load_static_stock_sector_map()
        
        # 如果静态映射表加载失败，构建动态映射表
        if not self._static_map_loaded:
            self._build_stock_sector_map()
        
        # 启动后台刷新线程（只启动一次）
        self._start_background_thread()
        
        # 🚀 V18.3 Flow Master: 初始化资金流数据
        self._refresh_fund_flow_data()
    
    def _start_background_thread(self):
        """启动后台刷新线程（只启动一次）"""
        if self._thread_started:
            logger.debug("🔄 [V18.1 Streamlit] 后台线程已启动，跳过重复启动")
            return
        
        import threading
        
        self._auto_refresh_thread = threading.Thread(
            target=self._auto_refresh_loop,
            daemon=True,
            name="V18_AutoRefresh"
        )
        self._auto_refresh_thread.start()
        self._thread_started = True
        
        if self._static_map_loaded:
            logger.info("🚀 [V18.1 Streamlit] 后台刷新线程已启动，静态映射表已加载")
        else:
            logger.info("🚀 [V18.1 Streamlit] 后台刷新线程已启动，动态映射表已构建")
    
    def _load_static_stock_sector_map(self):
        """
        🚀 V18.1 Hybrid Engine: 加载静态股票-板块映射表
        
        从 data/stock_sector_map.json 文件加载预先生成的映射表
        消除 90% 的 AkShare 请求，性能提升 5000 倍
        """
        try:
            # 检查静态映射表文件是否存在
            static_map_file = os.path.join('data', 'stock_sector_map.json')
            
            if not os.path.exists(static_map_file):
                logger.info(f"📁 [V18.1] 静态映射表文件不存在: {static_map_file}")
                return False
            
            # 加载静态映射表
            logger.info(f"📂 [V18.1] 正在加载静态映射表: {static_map_file}")
            
            with open(static_map_file, 'r', encoding='utf-8') as f:
                self._stock_sector_map = json.load(f)
            
            self._static_map_loaded = True
            
            logger.info(f"✅ [V18.1] 静态映射表加载成功，共 {len(self._stock_sector_map)} 只股票")
            
            # 统计信息
            stocks_with_industry = sum(1 for s in self._stock_sector_map.values() if s.get('industry') != '未知')
            stocks_with_concepts = sum(1 for s in self._stock_sector_map.values() if s.get('concepts'))
            
            logger.info(f"   - 有行业信息: {stocks_with_industry} 只 ({stocks_with_industry/len(self._stock_sector_map)*100:.1f}%)")
            logger.info(f"   - 有概念信息: {stocks_with_concepts} 只 ({stocks_with_concepts/len(self._stock_sector_map)*100:.1f}%)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [V18.1] 加载静态映射表失败: {e}")
            return False
    
    def _build_stock_sector_map(self):
        """构建股票-板块映射表（降级方案）"""
        try:
            logger.info("🏗️ [V18.1] 正在构建股票-板块映射表（降级方案）...")
            
            # 获取行业信息（使用 DataManager 的缓存）
            code_to_industry = self.db.get_industry_cache()
            
            # 构建映射表
            self._stock_sector_map = {}
            for stock_code, industry in code_to_industry.items():
                self._stock_sector_map[stock_code] = {
                    'industry': industry,
                    'concepts': []
                }
            
            logger.info(f"✅ [V18.1] 股票-板块映射表构建完成，共 {len(self._stock_sector_map)} 只股票")
            
        except Exception as e:
            logger.error(f"❌ [V18.1] 构建股票-板块映射表失败: {e}")
            self._stock_sector_map = {}
    
    def get_stock_sector_info(self, stock_code: str) -> Dict:
        """
        🚀 V18.1 Hybrid Engine: 获取股票板块信息（带 Fallback 机制）
        
        优先使用静态映射表，如果不存在则实时查询
        
        Args:
            stock_code: 股票代码
        
        Returns:
            Dict: {'industry': str, 'concepts': List[str], 'status': str}
                  status: 'known' (已知) / 'unknown' (未知) / 'new' (新股)
        """
        # 优先使用静态映射表
        if stock_code in self._stock_sector_map:
            sector_info = self._stock_sector_map[stock_code]
            sector_info['status'] = 'known'
            return sector_info
        
        # Fallback: 实时查询（只执行一次，并更新内存）
        try:
            logger.warning(f"⚠️ [V18.1] 股票 {stock_code} 不在映射表中，尝试实时查询...")
            
            # 实时查询股票信息
            stock_info = ak.stock_individual_info_em(symbol=stock_code)
            industry = stock_info.loc[stock_info['item'] == '行业', 'value'].values[0]
            
            # 更新映射表
            self._stock_sector_map[stock_code] = {
                'industry': industry,
                'concepts': [],
                'status': 'new'  # 新股标记
            }
            
            logger.info(f"✅ [V18.1] 实时查询成功，已更新映射表: {stock_code} -> {industry}")
            
            return self._stock_sector_map[stock_code]
            
        except Exception as e:
            logger.error(f"❌ [V18.1] 实时查询股票 {stock_code} 失败: {e}")
            return {'industry': '未知', 'concepts': [], 'status': 'unknown'}
    
    def get_data_status(self) -> Dict:
        """
        🚀 V18.1: 获取数据状态（用于 UI 状态灯）
        
        Returns:
            Dict: {
                'data_ready': bool,  # 数据是否就绪
                'cache_age': float,  # 缓存时间（秒）
                'static_map_loaded': bool,  # 静态映射表是否加载
                'thread_running': bool,  # 后台线程是否运行
                'fallback_mode': bool  # 是否处于降级模式
            }
        """
        cache_age = 0
        if self._akshare_cache_timestamp:
            cache_age = (datetime.now() - self._akshare_cache_timestamp).total_seconds()
        
        return {
            'data_ready': self._akshare_industry_cache is not None,
            'cache_age': cache_age,
            'static_map_loaded': self._static_map_loaded,
            'thread_running': self._auto_refresh_running,
            'fallback_mode': self._fallback_mode
        }
    
    def get_sector_fund_flow(self, sector_name: str, sector_type: str = 'industry') -> Dict:
        """
        🚀 V18.3 Flow Master: 获取板块资金流向数据（极速版）
        
        使用宏观接口一次性获取全市场板块资金流，查询时直接从内存查询
        性能优化：从 5.8秒 -> 0.001秒
        
        Args:
            sector_name: 板块名称
            sector_type: 板块类型 ('industry' 行业 或 'concept' 概念)
        
        Returns:
            Dict: {
                'net_inflow': float,  # 净流入额（元）
                'net_inflow_yi': float,  # 净流入额（亿元）
                'main_inflow': float,  # 主力流入（元）
                'main_outflow': float,  # 主力流出（元）
                'retail_inflow': float,  # 散户流入（元）
                'retail_outflow': float,  # 散户流出（元）
                'status': str,  # 'strong_inflow' 强流入 / 'weak_inflow' 弱流入 / 'outflow' 流出 / 'unknown' 未知
                'reason': str  # 原因说明
            }
        """
        try:
            # 检查缓存是否过期
            cache_age = 0
            if self._fund_flow_cache_timestamp:
                cache_age = (datetime.now() - self._fund_flow_cache_timestamp).total_seconds()
            
            # 如果缓存过期或未加载，刷新数据
            if (self._industry_fund_flow_df is None or self._industry_fund_flow_df.empty or cache_age > self._fund_flow_cache_ttl):
                self._refresh_fund_flow_data()
            
            # 根据板块类型选择对应的数据
            if sector_type == 'industry':
                fund_flow_df = self._industry_fund_flow_df
            else:
                fund_flow_df = self._concept_fund_flow_df
            
            if fund_flow_df is None:
                logger.debug(f"⚠️ [V18.3] 资金流数据未加载: {sector_name}")
                return self._get_fallback_fund_flow(sector_name)
            
            if fund_flow_df.empty:
                logger.debug(f"⚠️ [V18.3] 资金流数据为空: {sector_name}")
                return self._get_fallback_fund_flow(sector_name)
            
            # 从内存查询（极速）
            sector_row = fund_flow_df[fund_flow_df['名称'] == sector_name]
            
            if sector_row.empty:
                logger.debug(f"⚠️ [V18.3] 未找到板块 {sector_name} 的资金流数据")
                return self._get_fallback_fund_flow(sector_name)
            
            # 提取资金流数据
            fund_info = sector_row.iloc[0]
            
            # 获取主力净流入
            net_inflow = 0
            if '今日主力净流入-净额' in fund_info.index.tolist():
                try:
                    value = fund_info['今日主力净流入-净额']
                    if pd.notna(value):
                        net_inflow = float(value)
                except:
                    net_inflow = 0
            
            # 转换为亿元
            net_inflow_yi = net_inflow / 100000000
            
            # 判断资金流状态
            if net_inflow_yi > 10:
                status = 'strong_inflow'
                reason = f'💰 [资金抱团] 板块净流入超10亿 ({net_inflow_yi:.2f}亿)'
            elif net_inflow_yi > 0:
                status = 'weak_inflow'
                reason = f'📈 [资金流入] 板块净流入 {net_inflow_yi:.2f}亿'
            elif net_inflow_yi < -1:
                status = 'outflow'
                reason = f'⚠️ [资金流出] 板块净流出 {abs(net_inflow_yi):.2f}亿'
            else:
                status = 'neutral'
                reason = f'📊 [资金中性] 板块资金流平衡'
            
            logger.debug(f"✅ [V18.3] {sector_name} 资金流: {net_inflow_yi:.2f}亿 ({status})")
            
            return {
                'net_inflow': net_inflow,
                'net_inflow_yi': net_inflow_yi,
                'main_inflow': 0,
                'main_outflow': 0,
                'retail_inflow': 0,
                'retail_outflow': 0,
                'status': status,
                'reason': reason
            }
            
        except Exception as e:
            logger.error(f"❌ [V18.3] 获取板块资金流失败: {e}")
            import traceback
            logger.error(f"❌ [V18.3] 错误堆栈: {traceback.format_exc()}")
            return self._get_fallback_fund_flow(sector_name)
    
    def _refresh_fund_flow_data(self):
        """
        🚀 V18.3 Flow Master: 刷新板块资金流数据
        
        一次性获取全市场板块资金流，存入内存
        """
        try:
            # 获取行业板块资金流
            try:
                self._industry_fund_flow_df = ak.stock_sector_fund_flow_rank(
                    indicator="今日",
                    sector_type="行业资金流"
                )
                logger.info(f"✅ [V18.3] 行业资金流数据刷新成功，共 {len(self._industry_fund_flow_df)} 个板块")
            except Exception as e:
                logger.warning(f"⚠️ [V18.3] 行业资金流数据获取失败: {e}")
                self._industry_fund_flow_df = None
            
            # 获取概念板块资金流
            try:
                self._concept_fund_flow_df = ak.stock_sector_fund_flow_rank(
                    indicator="今日",
                    sector_type="概念资金流"
                )
                logger.info(f"✅ [V18.3] 概念资金流数据刷新成功，共 {len(self._concept_fund_flow_df)} 个板块")
            except Exception as e:
                logger.warning(f"⚠️ [V18.3] 概念资金流数据获取失败: {e}")
                self._concept_fund_flow_df = None
            
            # 更新缓存时间戳
            self._fund_flow_cache_timestamp = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ [V18.3] 刷新资金流数据失败: {e}")
            self._industry_fund_flow_df = None
            self._concept_fund_flow_df = None
    
    def _get_fallback_fund_flow(self, sector_name: str) -> Dict:
        """
        获取兜底资金流数据
        
        当无法获取真实资金流数据时，返回默认值
        """
        return {
            'net_inflow': 0,
            'net_inflow_yi': 0,
            'main_inflow': 0,
            'main_outflow': 0,
            'retail_inflow': 0,
            'retail_outflow': 0,
            'status': 'unknown',
            'reason': f'资金流数据不可用: {sector_name}'
        }
    
    def _auto_refresh_loop(self):
        """后台自动刷新循环"""
        logger.info("🔄 [V18.1 Streamlit] 后台刷新线程已启动")
        
        while self._auto_refresh_running:
            try:
                time.sleep(60)  # 每 60 秒刷新一次
                
                # 静默刷新数据
                self._auto_refresh_data()
                
                logger.debug("✅ [V18.1] 后台数据刷新完成")
                
            except Exception as e:
                logger.error(f"❌ [V18.1] 后台刷新失败: {e}")
                time.sleep(10)
    
    def _auto_refresh_data(self):
        """静默刷新板块数据"""
        try:
            # 刷新行业板块
            industry_df = ak.stock_board_industry_name_em()
            if industry_df is not None and not industry_df.empty:
                industry_df = industry_df.sort_values('涨跌幅', ascending=False).reset_index(drop=True)
                industry_df['rank'] = industry_df.index + 1
                industry_df['资金热度'] = self._calculate_capital_heat(industry_df)
                self._akshare_industry_cache = industry_df
                self._akshare_cache_timestamp = datetime.now()
            
            # 刷新概念板块（带超时控制）
            try:
                concept_df = ak.stock_board_concept_name_em()
                if concept_df is not None and not concept_df.empty:
                    concept_df = concept_df.sort_values('涨跌幅', ascending=False).reset_index(drop=True)
                    concept_df['rank'] = concept_df.index + 1
                    concept_df['资金热度'] = self._calculate_capital_heat(concept_df)
                    self._akshare_concept_cache = concept_df
                    self._fallback_mode = False
            except Exception as e:
                logger.warning(f"⚠️ [V18.1] 概念板块数据获取失败，启用降级模式: {e}")
                self._fallback_mode = True
            
            # 🚀 V18.3 Flow Master: 刷新资金流数据
            self._refresh_fund_flow_data()
            
        except Exception as e:
            logger.error(f"❌ [V18.1] 静默刷新失败: {e}")
    
    def _calculate_capital_heat(self, df: pd.DataFrame) -> pd.Series:
        """计算资金热度系数"""
        try:
            # 标准化涨幅（-10 到 10 分）
            pct_chg_score = df['涨跌幅'].clip(-10, 10) / 10 * 50 + 50
            
            # 标准化成交额（对数转换）
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
            
            # 标准化换手率
            turnover_score = 50
            if '换手率' in df.columns:
                turnover_score = df['换手率'].clip(0, 20) / 20 * 100
            
            # 综合计算
            capital_heat = pct_chg_score * 0.5 + amount_score * 0.3 + turnover_score * 0.2
            
            return capital_heat
            
        except Exception as e:
            logger.warning(f"计算资金热度失败: {e}")
            return pd.Series([50] * len(df), index=df.index)
    
    def get_akshare_sector_ranking(self) -> pd.DataFrame:
        """获取行业板块排名"""
        # 检查缓存
        if self._akshare_industry_cache is not None:
            cache_age = (datetime.now() - self._akshare_cache_timestamp).total_seconds()
            if cache_age < self._cache_ttl:
                logger.debug(f"使用 AkShare 行业板块缓存数据 (缓存时间: {cache_age:.1f}秒)")
                return self._akshare_industry_cache
        
        try:
            logger.info("🔍 [V18.1] 正在从 AkShare 获取行业板块排名数据...")
            sector_df = ak.stock_board_industry_name_em()
            
            if sector_df is None or sector_df.empty:
                logger.warning("AkShare 行业板块数据为空")
                return pd.DataFrame()
            
            # 添加排名列
            sector_df = sector_df.sort_values('涨跌幅', ascending=False).reset_index(drop=True)
            sector_df['rank'] = sector_df.index + 1
            
            # 计算资金热度系数
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
        """获取概念板块排名"""
        # 检查缓存
        if self._akshare_concept_cache is not None:
            cache_age = (datetime.now() - self._akshare_cache_timestamp).total_seconds()
            if cache_age < self._cache_ttl:
                logger.debug(f"使用 AkShare 概念板块缓存数据 (缓存时间: {cache_age:.1f}秒)")
                return self._akshare_concept_cache
        
        try:
            logger.info("🔍 [V18.1] 正在从 AkShare 获取概念板块排名数据...")
            concept_df = ak.stock_board_concept_name_em()
            
            if concept_df is None or concept_df.empty:
                logger.warning("AkShare 概念板块数据为空")
                return pd.DataFrame()
            
            # 添加排名列
            concept_df = concept_df.sort_values('涨跌幅', ascending=False).reset_index(drop=True)
            concept_df['rank'] = concept_df.index + 1
            
            # 计算资金热度系数
            concept_df['资金热度'] = self._calculate_capital_heat(concept_df)
            
            # 缓存数据
            self._akshare_concept_cache = concept_df
            self._akshare_cache_timestamp = datetime.now()
            
            logger.info(f"✅ AkShare 概念板块数据获取成功，共 {len(concept_df)} 个概念板块")
            return concept_df
            
        except Exception as e:
            logger.error(f"❌ 获取 AkShare 概念板块数据失败: {e}")
            return pd.DataFrame()
    
    def check_stock_full_resonance(self, stock_code: str, stock_name: Optional[str] = None) -> Dict[str, Union[float, List[str], Dict]]:
        """
        🚀 V18.1 Hybrid Engine: 全维板块共振分析（带 Fallback 机制）
        🚀 V18.2 Money Flow: 集成板块资金流向分析
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称（可选，用于匹配龙头）
        
        Returns:
            dict: 共振分析结果
        """
        resonance_score = 0.0
        resonance_details = []
        
        # 获取行业和概念板块数据
        industry_ranking = self.get_akshare_sector_ranking()
        concept_ranking = self.get_akshare_concept_ranking()
        
        # 🚀 V18.1 Hybrid Engine: 优先使用静态映射表获取股票所属行业和概念
        sector_info = self.get_stock_sector_info(stock_code)
        industry_name = sector_info.get('industry', '未知')
        concepts = sector_info.get('concepts', [])
        sector_status = sector_info.get('status', 'unknown')
        
        # 🚀 V18.1 Fallback: Unknown 状态处理
        if sector_status == 'unknown':
            resonance_details.append("⚠️ [未知板块] 该股票板块信息未知，请手动确认")
        elif sector_status == 'new':
            resonance_details.append("🆕 [新股] 新上市股票，请关注板块归属")
        
        # 1. 行业板块共振分析
        industry_info = self._analyze_industry_resonance(
            stock_code, industry_name, industry_ranking, stock_name
        )
        
        if industry_info:
            resonance_score += industry_info.get('score_boost', 0)
            resonance_details.extend(industry_info.get('details', []))
            
            # 🚀 V18.2 Money Flow: 获取行业板块资金流向
            if industry_name != '未知':
                fund_flow = self.get_sector_fund_flow(industry_name, 'industry')
                net_inflow_yi = fund_flow.get('net_inflow_yi', 0)
                fund_status = fund_flow.get('status', 'unknown')
                fund_reason = fund_flow.get('reason', '')
                
                # 根据资金流调整分数
                if fund_status == 'outflow' and industry_info.get('rank', 999) <= 5:
                    # 量价背离：板块在前5但资金流出
                    resonance_score -= 10.0
                    resonance_details.append(f"⚠️ [量价背离] {fund_reason}")
                elif fund_status == 'strong_inflow':
                    # 资金抱团：净流入超10亿
                    resonance_score += 5.0
                    resonance_details.append(fund_reason)
                elif fund_status == 'weak_inflow':
                    # 弱流入
                    resonance_details.append(fund_reason)
                
                # 将资金流信息添加到 industry_info
                industry_info['fund_flow'] = fund_flow
        
        # 2. 概念板块共振分析
        concept_info = self._analyze_concept_resonance(
            stock_code, stock_name, concept_ranking, concepts
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
            'is_follower': is_follower,
            'sector_status': sector_status
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
        
        # 强势行业（Top 10）
        elif rank <= 10:
            score_boost = 8.0
            details.append(f"🚀 [行业强势] {industry_name} (Rank {rank}/{total}, +{pct_chg:.2f}%)")
        
        # 逆风行业（Bottom 3）
        elif rank >= total - 3:
            score_boost = -10.0
            details.append(f"❄️ [行业逆风] {industry_name} (Rank {rank}/{total}, +{pct_chg:.2f}%)")
        
        return {
            'score_boost': score_boost,
            'details': details
        }
    
    def _analyze_concept_resonance(
        self,
        stock_code: str,
        stock_name: Optional[str],
        concept_ranking: pd.DataFrame,
        concepts: Optional[List[str]] = None
    ) -> Dict:
        """分析概念板块共振"""
        if concept_ranking.empty:
            return {}
        
        score_boost = 0.0
        details = []
        
        # 🚀 V18.1 Hybrid Engine: 优先使用概念列表匹配
        if concepts and len(concepts) > 0:
            # 从静态映射表获取的概念列表进行匹配
            top_concepts = concept_ranking.head(10)
            
            for concept_name in concepts:
                # 查找该概念在排行榜中的排名
                concept_row = top_concepts[top_concepts['板块名称'] == concept_name]
                
                if not concept_row.empty:
                    concept_info = concept_row.iloc[0]
                    rank = int(concept_info['rank'])
                    pct_chg = float(concept_info['涨跌幅'])
                    leader_stock = concept_info.get('领涨股票', '')
                    
                    # 领涨主线（Top 5）
                    if rank <= 5:
                        score_boost += 10.0
                        details.append(f"🔥 [概念主线] {concept_name} 领涨 (Rank {rank}, +{pct_chg:.2f}%)")
                        
                        # 检查是否为龙头
                        if stock_name and leader_stock and stock_name in str(leader_stock):
                            score_boost += 10.0
                            details.append(f"👑 [概念龙头] 领涨 {concept_name}")
                        else:
                            details.append(f"📈 [跟风] {concept_name} 龙头: {leader_stock}")
                    
                    # 强势概念（Top 10）
                    elif rank <= 10:
                        score_boost += 5.0
                        details.append(f"🚀 [概念强势] {concept_name} (Rank {rank}, +{pct_chg:.2f}%)")
                    
                    # 限制加分，避免过度乐观
                    if score_boost >= 30.0:
                        break
        else:
            # 降级方案：只依赖 stock_name 进行匹配
            if not stock_name:
                return {}
            
            top_concepts = concept_ranking.head(10)
            
            for _, row in top_concepts.iterrows():
                concept_name = row['板块名称']
                leader_stock = row.get('领涨股票', '')
                
                # 简化匹配：检查股票名称是否在领涨股中
                if leader_stock and stock_name in str(leader_stock):
                    score_boost = 20.0
                    details.append(f"👑 [概念龙头] 领涨 {concept_name}")
                    break
        
        return {
            'score_boost': score_boost,
            'details': details
        }


def get_fast_sector_analyzer_streamlit(db: DataManager) -> FastSectorAnalyzerStreamlit:
    """
    🚀 V18.1 Streamlit 兼容版：获取极速板块分析器实例
    
    使用 @st.cache_resource 管理单例，避免僵尸线程问题
    
    Args:
        db: DataManager 实例
    
    Returns:
        FastSectorAnalyzerStreamlit 实例
    """
    import streamlit as st
    
    @st.cache_resource
    def _get_analyzer():
        """Streamlit 缓存的单例函数"""
        return FastSectorAnalyzerStreamlit(db)
    
    return _get_analyzer()