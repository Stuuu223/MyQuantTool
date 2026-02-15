#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V12.1.0 板块共振过滤器

拒绝"孤军深入"，只有"个股强 + 板块共振"才是真龙

核心逻辑：
- 条件A: 板块内涨停股 ≥ 3只
- 条件B: 板块内上涨股票占比 ≥ 35%
- 条件C: 板块指数连续3日资金净流入
- 满足至少2个条件才返回True

Author: iFlow CLI
Version: V12.1.0
Date: 2026-02-14
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from logic.utils.logger import get_logger
from logic.utils.code_converter import CodeConverter
from logic.data_providers.data_source_manager import get_smart_data_manager
from logic.data_providers.cache_manager import CacheManager

logger = get_logger(__name__)


class WindFilter:
    """
    板块共振过滤器
    
    功能：
    1. 检查个股所属板块的整体活跃度
    2. 识别板块共振信号（涨停股数/上涨占比/资金流入）
    3. 拒绝"孤军深入"的个股
    4. 提供板块共振评分（0-1）
    
    数据源：
    - 板块映射: data/stock_sector_map.json
    - QMT Tick数据: 实时涨停股统计
    - Tushare数据: 板块指数资金流
    """

    # 配置参数
    SECTOR_MAP_PATH = Path("data/sector_map/stock_sector_map.json")
    MIN_LIMIT_UP_COUNT = 3  # 条件A: 最少涨停股数
    MIN_RISE_RATIO = 0.35  # 条件B: 最少上涨比例 (35%)
    SUSTAINED_INFLOW_DAYS = 3  # 条件C: 连续流入天数
    
    # 缓存时间（秒）
    CACHE_TTL_LIMIT_UP = 60  # 涨停股统计缓存60秒
    CACHE_TTL_SECTOR_PERFORMANCE = 60  # 板块表现缓存60秒
    CACHE_TTL_CAPITAL_FLOW = 600  # 资金流缓存10分钟（API调用慢，需要更长缓存）

    def __init__(self):
        """初始化板块共振过滤器"""
        self.converter = CodeConverter()
        self.data_manager = get_smart_data_manager()
        self.cache = CacheManager()

        # 加载板块映射
        self.sector_map = self._load_sector_map()

        # 全局行业资金流缓存（一次性获取所有行业数据）
        self._global_capital_flow_cache = None
        self._global_capital_flow_timestamp = 0

        # 全局实时价格缓存
        self._global_price_cache = None
        self._global_price_timestamp = 0

        logger.info("✅ [板块共振过滤器] 初始化完成")
        logger.info(f"   - 涨停股阈值: ≥ {self.MIN_LIMIT_UP_COUNT} 只")
        logger.info(f"   - 上涨占比阈值: ≥ {self.MIN_RISE_RATIO*100:.0f}%")
        logger.info(f"   - 连续流入天数: ≥ {self.SUSTAINED_INFLOW_DAYS} 天")
    
    def _load_sector_map(self) -> Dict:
        """
        加载板块映射
        
        Returns:
            dict: 股票代码 -> 板块信息
        """
        try:
            if self.SECTOR_MAP_PATH.exists():
                with open(self.SECTOR_MAP_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"⚠️ [板块共振] 板块映射文件不存在: {self.SECTOR_MAP_PATH}")
                return {}
        except Exception as e:
            logger.error(f"❌ [板块共振] 加载板块映射失败: {e}")
            return {}
    
    def get_stock_sector(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票所属板块
        
        Args:
            stock_code: 股票代码
        
        Returns:
            dict: {
                'industry': str,  # 行业
                'concepts': list,  # 概念列表
            }
        """
        try:
            # 转换为标准代码
            standard_code = self.converter.to_standard(stock_code)
            
            if standard_code in self.sector_map:
                return self.sector_map[standard_code]
            
            return None
        except Exception as e:
            logger.warning(f"⚠️ [板块共振] 获取股票板块失败: {stock_code}, {e}")
            return None
    
    def get_sector_stocks(self, industry: str) -> List[str]:
        """
        获取板块内所有股票
        
        Args:
            industry: 行业名称
        
        Returns:
            list: 股票代码列表
        """
        try:
            stocks = []
            for code, info in self.sector_map.items():
                if info.get('industry') == industry:
                    stocks.append(code)
            
            return stocks
        except Exception as e:
            logger.warning(f"⚠️ [板块共振] 获取板块股票失败: {industry}, {e}")
            return []
    
    def count_limit_up_stocks(self, industry: str) -> int:
        """
        统计板块内涨停股票数量

        策略：
        1. 获取板块内所有股票
        2. 获取实时价格数据
        3. 统计涨幅 >= 9.8% 的股票数

        Args:
            industry: 行业名称

        Returns:
            int: 涨停股票数量
        """
        try:
            # 尝试从缓存获取
            cache_key = f"limit_up_count_{industry}"
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 获取板块股票
            stocks = self.get_sector_stocks(industry)
            if not stocks:
                return 0

            # 限制检查数量（避免性能问题）
            stocks = stocks[:100]

            # 获取实时数据
            limit_up_count = 0

            # 优先使用极速层
            try:
                realtime_data = self.data_manager.get_realtime_price_fast(stocks)

                for code in stocks:
                    if code in realtime_data:
                        info = realtime_data[code]
                        price = info.get('price', 0)
                        yesterday_close = info.get('close', 0)

                        if yesterday_close > 0:
                            change_pct = (price - yesterday_close) / yesterday_close * 100

                            # 涨停判定：涨幅 >= 9.8%
                            if change_pct >= 9.8:
                                limit_up_count += 1

            except Exception as e:
                logger.debug(f"⚠️ [板块共振] 获取实时数据失败: {e}")

                # 备用方案：使用增强层
                try:
                    import akshare as ak

                    # 获取板块行情
                    sector_df = ak.stock_board_industry_cons_em(symbol=industry)

                    if not sector_df.empty:
                        limit_up_count = len(sector_df[sector_df['涨跌幅'] >= 9.8])

                except Exception as e2:
                    logger.debug(f"⚠️ [板块共振] 备用方案也失败: {e2}")

            # 缓存结果
            self.cache.set(cache_key, limit_up_count, ttl=self.CACHE_TTL_LIMIT_UP)

            return limit_up_count

        except Exception as e:
            logger.error(f"❌ [板块共振] 统计涨停股失败: {industry}, {e}")
            return 0
    
    def calculate_rise_breadth(self, industry: str) -> float:
        """
        计算板块上涨比例（广度）
        
        Args:
            industry: 行业名称
        
        Returns:
            float: 上涨比例 (0-1)
        """
        try:
            # 尝试从缓存获取
            cache_key = f"rise_breadth_{industry}"
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # 获取板块股票
            stocks = self.get_sector_stocks(industry)
            if not stocks:
                return 0.0
            
            # 限制检查数量
            stocks = stocks[:100]
            
            # 获取实时数据
            rise_count = 0
            total_count = 0
            
            try:
                realtime_data = self.data_manager.get_realtime_price_fast(stocks)
                
                for code in stocks:
                    if code in realtime_data:
                        info = realtime_data[code]
                        price = info.get('price', 0)
                        yesterday_close = info.get('close', 0)
                        
                        if yesterday_close > 0:
                            change_pct = (price - yesterday_close) / yesterday_close * 100
                            total_count += 1
                            
                            # 上涨判定：涨幅 > 0%
                            if change_pct > 0:
                                rise_count += 1
                
            except Exception as e:
                logger.warning(f"⚠️ [板块共振] 获取实时数据失败: {e}")
            
            # 计算上涨比例
            rise_ratio = rise_count / total_count if total_count > 0 else 0.0
            
            # 缓存结果
            self.cache.set(cache_key, rise_ratio, ttl=self.CACHE_TTL_SECTOR_PERFORMANCE)
            
            return rise_ratio
            
        except Exception as e:
            logger.error(f"❌ [板块共振] 计算上涨比例失败: {industry}, {e}")
            return 0.0
    
    def check_sustained_capital_inflow(self, industry: str) -> bool:
        """
        检查板块指数连续资金净流入

        策略：
        1. 获取板块指数的资金流数据（过去N天）
        2. 判断是否连续N日净流入

        Args:
            industry: 行业名称

        Returns:
            bool: 是否连续流入
        """
        try:
            # 尝试从缓存获取
            cache_key = f"sustained_inflow_{industry}"
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 检查全局缓存是否过期（10分钟）
            current_time = time.time()
            if (self._global_capital_flow_cache is None or
                current_time - self._global_capital_flow_timestamp > 600):

                # 一次性获取所有行业的资金流数据
                try:
                    import akshare as ak
                    logger.debug("🔄 [板块共振] 更新全局行业资金流数据...")
                    self._global_capital_flow_cache = ak.stock_fund_flow_industry(symbol='即时')
                    self._global_capital_flow_timestamp = current_time
                    logger.debug("✅ [板块共振] 全局行业资金流数据更新完成")
                except Exception as e:
                    logger.warning(f"⚠️ [板块共振] 获取资金流数据失败: {e}")
                    return False

            # 从全局缓存中查找对应行业
            if self._global_capital_flow_cache is not None and not self._global_capital_flow_cache.empty:
                # 查找对应行业（使用'行业'列）
                industry_row = self._global_capital_flow_cache[
                    self._global_capital_flow_cache['行业'] == industry
                ]

                if not industry_row.empty:
                    # 检查今日是否净流入（使用'净额'列）
                    net_inflow = industry_row['净额'].values[0]

                    # 简化判断：今日净流入 > 0
                    sustained_inflow = net_inflow > 0

                    # 缓存结果
                    self.cache.set(cache_key, sustained_inflow, ttl=self.CACHE_TTL_CAPITAL_FLOW)

                    return sustained_inflow

            # 默认返回False
            return False

        except Exception as e:
            logger.error(f"❌ [板块共振] 检查持续流入失败: {industry}, {e}")
            return False
    
    def check_sector_resonance(self, stock_code: str) -> Dict:
        """
        检查板块共振状态
        
        核心逻辑：
        - 条件A: 板块内涨停股 ≥ 3只
        - 条件B: 板块内上涨股票占比 ≥ 35%
        - 条件C: 板块指数连续3日资金净流入
        - 满足至少2个条件才返回True
        
        Args:
            stock_code: 股票代码
        
        Returns:
            dict: {
                'is_resonance': bool,  # 是否共振
                'limit_up_count': int,  # 涨停股数
                'breadth': float,  # 上涨比例 (0-1)
                'sustained_inflow': bool,  # 持续流入
                'resonance_score': float,  # 共振分数 (0-1)
                'passed_conditions': list,  # 通过的条件列表
                'industry': str,  # 行业名称
                'details': dict  # 详细信息
            }
        """
        start_time = time.time()
        
        try:
            # 1. 获取股票所属板块
            sector_info = self.get_stock_sector(stock_code)
            
            if not sector_info:
                logger.warning(f"⚠️ [板块共振] 无法获取板块信息: {stock_code}")
                return {
                    'is_resonance': False,
                    'limit_up_count': 0,
                    'breadth': 0.0,
                    'sustained_inflow': False,
                    'resonance_score': 0.0,
                    'passed_conditions': [],
                    'industry': '',
                    'details': {'reason': '无法获取板块信息'}
                }
            
            industry = sector_info.get('industry', '')
            
            if not industry:
                logger.warning(f"⚠️ [板块共振] 无行业信息: {stock_code}")
                return {
                    'is_resonance': False,
                    'limit_up_count': 0,
                    'breadth': 0.0,
                    'sustained_inflow': False,
                    'resonance_score': 0.0,
                    'passed_conditions': [],
                    'industry': '',
                    'details': {'reason': '无行业信息'}
                }
            
            # 2. 检查三个条件
            passed_conditions = []
            
            # 条件A: 涨停股数
            limit_up_count = self.count_limit_up_stocks(industry)
            condition_a_passed = limit_up_count >= self.MIN_LIMIT_UP_COUNT
            if condition_a_passed:
                passed_conditions.append('A')
            
            # 条件B: 上涨比例
            breadth = self.calculate_rise_breadth(industry)
            condition_b_passed = breadth >= self.MIN_RISE_RATIO
            if condition_b_passed:
                passed_conditions.append('B')
            
            # 条件C: 持续流入
            sustained_inflow = self.check_sustained_capital_inflow(industry)
            condition_c_passed = sustained_inflow
            if condition_c_passed:
                passed_conditions.append('C')
            
            # 3. 判断是否共振（满足至少2个条件）
            is_resonance = len(passed_conditions) >= 2
            
            # 4. 计算共振分数 (0-1)
            # 分数 = (通过的条件的权重和) / 总权重
            # 权重: A=0.4, B=0.35, C=0.25
            weights = {'A': 0.4, 'B': 0.35, 'C': 0.25}
            score = sum(weights.get(c, 0) for c in passed_conditions)
            resonance_score = min(1.0, score)
            
            # 5. 计算耗时
            elapsed_time = (time.time() - start_time) * 1000  # 毫秒
            
            # 6. 构建结果
            result = {
                'is_resonance': is_resonance,
                'limit_up_count': limit_up_count,
                'breadth': breadth,
                'sustained_inflow': sustained_inflow,
                'resonance_score': resonance_score,
                'passed_conditions': passed_conditions,
                'industry': industry,
                'details': {
                    'condition_a': {
                        'name': '涨停股数',
                        'threshold': self.MIN_LIMIT_UP_COUNT,
                        'value': limit_up_count,
                        'passed': condition_a_passed
                    },
                    'condition_b': {
                        'name': '上涨占比',
                        'threshold': self.MIN_RISE_RATIO,
                        'value': breadth,
                        'passed': condition_b_passed
                    },
                    'condition_c': {
                        'name': '持续流入',
                        'threshold': self.SUSTAINED_INFLOW_DAYS,
                        'value': '是' if sustained_inflow else '否',
                        'passed': condition_c_passed
                    },
                    'elapsed_time_ms': elapsed_time,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            # 7. 日志记录
            if is_resonance:
                logger.info(
                    f"✅ [板块共振] {stock_code} ({industry}) 共振确认 "
                    f"[{','.join(passed_conditions)}] "
                    f"涨停={limit_up_count} 上涨={breadth*100:.1f}% "
                    f"分数={resonance_score:.2f} "
                    f"耗时={elapsed_time:.1f}ms"
                )
            else:
                logger.debug(
                    f"⚠️ [板块共振] {stock_code} ({industry}) 未共振 "
                    f"[{','.join(passed_conditions) if passed_conditions else '无'}] "
                    f"涨停={limit_up_count} 上涨={breadth*100:.1f}% "
                    f"分数={resonance_score:.2f}"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [板块共振] 检查失败: {stock_code}, {e}")
            return {
                'is_resonance': False,
                'limit_up_count': 0,
                'breadth': 0.0,
                'sustained_inflow': False,
                'resonance_score': 0.0,
                'passed_conditions': [],
                'industry': '',
                'details': {'reason': f'检查失败: {e}'}
            }
    
    def batch_check_resonance(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """
        批量检查板块共振状态
        
        Args:
            stock_codes: 股票代码列表
        
        Returns:
            dict: {stock_code: resonance_result}
        """
        results = {}
        
        for code in stock_codes:
            results[code] = self.check_sector_resonance(code)
        
        return results
    
    def get_cache_info(self) -> Dict:
        """
        获取缓存信息
        
        Returns:
            dict: 缓存统计
        """
        cache_info = self.cache.get_cache_info()
        
        # 统计板块相关的缓存
        sector_cache_keys = [
            k for k in cache_info.get('缓存键列表', [])
            if k.startswith('limit_up_count_') or 
               k.startswith('rise_breadth_') or 
               k.startswith('sustained_inflow_')
        ]
        
        return {
            '总缓存数': cache_info.get('缓存数量', 0),
            '板块相关缓存数': len(sector_cache_keys),
            '板块缓存键列表': sector_cache_keys
        }


# ==================== 全局实例 ====================

_wind_filter: Optional[WindFilter] = None


def get_wind_filter() -> WindFilter:
    """获取板块共振过滤器单例"""
    global _wind_filter
    if _wind_filter is None:
        _wind_filter = WindFilter()
    return _wind_filter


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试板块共振过滤器
    print("=" * 60)
    print("板块共振过滤器测试")
    print("=" * 60)
    
    wind_filter = get_wind_filter()
    
    # 测试股票
    test_stocks = ['000001', '000002', '600519', '000858']
    
    print("\n测试股票列表:", test_stocks)
    print("\n开始检查板块共振状态...\n")
    
    for code in test_stocks:
        result = wind_filter.check_sector_resonance(code)
        
        print(f"\n股票: {code}")
        print(f"行业: {result['industry']}")
        print(f"是否共振: {'✅ 是' if result['is_resonance'] else '❌ 否'}")
        print(f"共振分数: {result['resonance_score']:.2f}")
        print(f"通过条件: {', '.join(result['passed_conditions']) if result['passed_conditions'] else '无'}")
        print(f"涨停股数: {result['limit_up_count']}")
        print(f"上涨占比: {result['breadth']*100:.1f}%")
        print(f"持续流入: {'是' if result['sustained_inflow'] else '否'}")
        print(f"耗时: {result['details']['elapsed_time_ms']:.1f}ms")
    
    print("\n" + "=" * 60)
    print("缓存信息:")
    print("=" * 60)
    cache_info = wind_filter.get_cache_info()
    print(f"总缓存数: {cache_info['总缓存数']}")
    print(f"板块相关缓存数: {cache_info['板块相关缓存数']}")