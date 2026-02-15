#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V12.1.0 动态阈值管理器 (Dynamic Threshold Manager)

核心功能：
- 废弃硬编码阈值，采用动态计算
- 根据流通市值分层计算基础阈值
- 根据时间分段调整阈值（开盘/盘中/尾盘）
- 根据情绪周期调整阈值（启动/主升/高潮/退潮/冰点）
- 提供两种计算方案（市值比例/成交额比例）

设计原则：
1. 小盘股：阈值更宽松（0.2%流通市值）
2. 大盘股：阈值更严格（0.02%流通市值）
3. 开盘：放宽阈值（x0.8），避免错失机会
4. 尾盘：严格阈值（x1.2），控制风险
5. 情绪上升期：激进（x0.8），情绪下降期：保守（x1.2）

Author: iFlow CLI
Version: V12.1.0
Date: 2026-02-14
"""

import json
import time
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Dict, Optional, Tuple

from logic.utils.logger import get_logger
from logic.utils.code_converter import CodeConverter
from logic.data.cache_manager import CacheManager

logger = get_logger(__name__)


class DynamicThreshold:
    """
    动态阈值管理器
    
    功能：
    1. 根据流通市值分层计算基础阈值
    2. 根据时间分段调整阈值
    3. 根据情绪周期调整阈值
    4. 提供降级策略（数据缺失时使用默认值）
    5. 缓存优化，单次计算<50ms
    
    计算方案：
    - 方案1：按流通市值（主力流入 = 流通市值 * 比例）
    - 方案2：按昨日成交额（主力流入 = 昨日成交额 * 0.01）
    """

    # 市值分层配置（单位：亿元）
    MARKET_CAP_TIERS = {
        'small': {'max': 50, 'ratio': 0.002, 'name': '小盘股'},      # 50亿以下：0.2%
        'mid': {'min': 50, 'max': 100, 'ratio': 0.001, 'name': '中盘股'},  # 50-100亿：0.1%
        'large': {'min': 100, 'max': 1000, 'ratio': 0.0005, 'name': '大盘股'},  # 100-1000亿：0.05%
        'mega': {'min': 1000, 'ratio': 0.0002, 'name': '超大盘股'}    # 1000亿以上：0.02%
    }

    # 时间分段配置
    TIME_SEGMENTS = {
        'open': {
            'name': '开盘阶段',
            'start': dt_time(9, 30),
            'end': dt_time(10, 0),
            'adjustment': 0.8  # 放宽阈值
        },
        'mid': {
            'name': '盘中阶段',
            'start': dt_time(10, 0),
            'end': dt_time(14, 30),
            'adjustment': 1.0  # 标准阈值
        },
        'close': {
            'name': '尾盘阶段',
            'start': dt_time(14, 30),
            'end': dt_time(15, 0),
            'adjustment': 1.2  # 严格阈值
        }
    }

    # 情绪周期配置
    SENTIMENT_STAGES = {
        'start': {'name': '启动期', 'adjustment': 0.8},      # 上升期：激进
        'main': {'name': '主升期', 'adjustment': 0.8},       # 上升期：激进
        'climax': {'name': '高潮期', 'adjustment': 0.8},     # 上升期：激进
        'divergence': {'name': '分歧期', 'adjustment': 1.0},  # 震荡期：标准
        'recession': {'name': '退潮期', 'adjustment': 1.2},   # 下降期：保守
        'freeze': {'name': '冰点期', 'adjustment': 1.2}      # 下降期：保守
    }

    # 默认值（降级策略）
    DEFAULT_THRESHOLDS = {
        'pct_chg_min': 3.0,           # 最小涨幅 3%
        'volume_ratio_min': 1.5,      # 最小量比 1.5
        'turnover_min': 2.0,          # 最小换手率 2%
        'main_inflow_min': 10000000,  # 最小主力流入 1000万
        'risk_score_max': 0.6         # 最大风险评分 0.6
    }

    # 缓存时间（秒）
    CACHE_TTL_MARKET_CAP = 3600  # 市值数据缓存1小时
    CACHE_TTL_PRICE = 60  # 价格数据缓存60秒

    def __init__(self):
        """初始化动态阈值管理器"""
        self.converter = CodeConverter()
        self.cache = CacheManager()

        # 加载股本信息
        self.equity_info = self._load_equity_info()

        # 调试：打印前5个股票代码
        if self.equity_info:
            sample_keys = list(self.equity_info.keys())[:5]
            logger.debug(f"📊 [动态阈值] 样本股票代码: {sample_keys}")

        # 加载昨日成交额缓存
        self.yesterday_amount_cache = {}
        self.yesterday_amount_timestamp = 0

        logger.info("✅ [动态阈值管理器] 初始化完成")
        logger.info(f"   - 股本信息: {len(self.equity_info)} 只股票")
        logger.info(f"   - 市值分层: {len(self.MARKET_CAP_TIERS)} 层")
        logger.info(f"   - 时间分段: {len(self.TIME_SEGMENTS)} 段")
        logger.info(f"   - 情绪周期: {len(self.SENTIMENT_STAGES)} 阶段")

    def _load_equity_info(self) -> Dict:
        """
        加载股本信息
        
        Returns:
            dict: 股本信息字典，结构: {code: {float_shares, last_close, amount}}
        """
        try:
            # 优先使用 MVP 版本（数据结构：{data: {code: {date: {...}}}}）
            mvp_path = Path("data/equity_info_mvp.json")
            if mvp_path.exists():
                with open(mvp_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 检查数据结构
                if "data" in data and isinstance(data["data"], dict):
                    data_by_date = data["data"]
                    
                    # 查找所有股票的最新可用日期
                    all_dates = set()
                    for code, dates_data in data_by_date.items():
                        if isinstance(dates_data, dict):
                            all_dates.update(dates_data.keys())
                    
                    # 使用实际存在的最新日期
                    if all_dates:
                        latest_date = max(all_dates)
                    else:
                        latest_date = ""
                    
                    # 提取最新日期的数据，转换为扁平结构
                    equity_info = {}
                    for code, dates_data in data_by_date.items():
                        if isinstance(dates_data, dict) and latest_date in dates_data:
                            stock_data = dates_data[latest_date]
                            equity_info[code] = {
                                'float_mv': stock_data.get('float_mv', 0),
                                'float_shares': stock_data.get('float_mv', 0) / stock_data.get('close', 1) if stock_data.get('close', 0) > 0 else 0,
                                'last_close': stock_data.get('close', 0),
                                'amount': 0  # MVP版本没有成交额数据
                            }

                    logger.info(f"✅ [动态阈值] 加载股本信息（MVP版）: {len(equity_info)} 只股票 (日期: {latest_date})")
                    return equity_info

            # 备用：使用 Tushare 版本
            tushare_path = Path("data/equity_info_tushare.json")
            if tushare_path.exists():
                with open(tushare_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 检查数据结构
                data_structure = data.get("data_structure", "")
                if "{code: {date: {...}}}" in data_structure:
                    # 新结构：获取最新日期的数据
                    data_by_date = data["data"]
                    
                    # 查找所有股票的最新可用日期
                    all_dates = set()
                    for code, dates_data in data_by_date.items():
                        if isinstance(dates_data, dict):
                            all_dates.update(dates_data.keys())
                    
                    # 使用实际存在的最新日期
                    if all_dates:
                        latest_date = max(all_dates)
                    else:
                        latest_date = ""

                    if latest_date:
                        # 提取最新日期的数据，转换为扁平结构
                        equity_info = {}
                        for code, dates_data in data_by_date.items():
                            if isinstance(dates_data, dict) and latest_date in dates_data:
                                stock_data = dates_data[latest_date]
                                equity_info[code] = {
                                    'float_mv': stock_data.get('float_mv', 0) or stock_data.get('circ_mv', 0),
                                    'float_shares': stock_data.get('float_shares', 0),
                                    'last_close': stock_data.get('close', 0),
                                    'amount': 0
                                }

                        logger.info(f"✅ [动态阈值] 加载股本信息（Tushare版）: {len(equity_info)} 只股票 (日期: {latest_date})")
                        return equity_info

                # 旧结构：{data: {date: {code: {...}}}}
                if "data" in data and isinstance(data["data"], dict):
                    dates = list(data["data"].keys())
                    if dates:
                        latest_date = max(dates)
                        data_by_date = data["data"][latest_date]

                        # 转换为扁平结构
                        equity_info = {}
                        for code, stock_data in data_by_date.items():
                            equity_info[code] = {
                                'float_mv': stock_data.get('float_mv', 0) or stock_data.get('circ_mv', 0),
                                'float_shares': stock_data.get('float_shares', 0),
                                'last_close': stock_data.get('close', 0),
                                'amount': 0
                            }

                        logger.info(f"✅ [动态阈值] 加载股本信息（Tushare旧版）: {len(equity_info)} 只股票 (日期: {latest_date})")
                        return equity_info

            # 备用：使用完整版
            full_path = Path("data/equity_info.json")
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                logger.info(f"✅ [动态阈值] 加载股本信息（完整版）: {len(data)} 只股票")
                return data

            logger.warning("⚠️ [动态阈值] 无法加载股本信息，将使用默认阈值")
            return {}

        except Exception as e:
            logger.error(f"❌ [动态阈值] 加载股本信息失败: {e}")
            return {}

    def _get_market_cap_tier(self, circulating_cap: float) -> str:
        """
        获取市值分层
        
        Args:
            circulating_cap: 流通市值（元）
        
        Returns:
            str: 市值分层代码（'small', 'mid', 'large', 'mega'）
        """
        circulating_cap_yi = circulating_cap / 1e8  # 转换为亿元

        if circulating_cap_yi < 50:
            return 'small'
        elif circulating_cap_yi < 100:
            return 'mid'
        elif circulating_cap_yi < 1000:
            return 'large'
        else:
            return 'mega'

    def _get_time_segment(self, current_time: datetime) -> str:
        """
        获取时间分段
        
        Args:
            current_time: 当前时间
        
        Returns:
            str: 时间分段代码（'open', 'mid', 'close'）
        """
        time_only = current_time.time()

        for segment_key, segment_config in self.TIME_SEGMENTS.items():
            if segment_config['start'] <= time_only < segment_config['end']:
                return segment_key

        # 默认返回盘中阶段
        return 'mid'

    def _get_circulating_cap(self, stock_code: str, current_price: float = 0) -> Optional[float]:
        """
        获取流通市值（元）
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格（可选，如果不提供则使用最新收盘价）
        
        Returns:
            Optional[float]: 流通市值（元），如果无法获取则返回 None
        """
        try:
            # 转换为标准代码（不带后缀）
            standard_code = self.converter.to_standard(stock_code)

            # 尝试从缓存获取
            cache_key = f"market_cap_{standard_code}"
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 尝试多种代码格式匹配（带后缀和不带后缀）
            possible_codes = [standard_code]
            
            # 添加带后缀的格式
            if standard_code.startswith('6'):
                possible_codes.append(f"{standard_code}.SH")
            elif standard_code.startswith('0') or standard_code.startswith('3'):
                possible_codes.append(f"{standard_code}.SZ")
            
            # 从股本信息获取
            for code in possible_codes:
                if code in self.equity_info:
                    equity = self.equity_info[code]
                    float_mv = equity.get('float_mv', 0)
                    
                    # 如果有直接的流通市值，直接返回
                    if float_mv > 0:
                        # 缓存结果
                        self.cache.set(cache_key, float_mv, ttl=self.CACHE_TTL_MARKET_CAP)
                        return float_mv
                    
                    # 否则用流通股本计算
                    float_shares = equity.get('float_shares', 0)
                    last_close = equity.get('last_close', 0)

                    if float_shares > 0 and last_close > 0:
                        price = current_price if current_price > 0 else last_close
                        if price > 0:
                            circulating_cap = float_shares * price

                            # 缓存结果
                            self.cache.set(cache_key, circulating_cap, ttl=self.CACHE_TTL_MARKET_CAP)

                            return circulating_cap

            return None

        except Exception as e:
            logger.debug(f"⚠️ [动态阈值] 获取流通市值失败: {stock_code}, {e}")
            return None

    def _get_yesterday_amount(self, stock_code: str) -> Optional[float]:
        """
        获取昨日成交额（元）
        
        Args:
            stock_code: 股票代码
        
        Returns:
            Optional[float]: 昨日成交额（元），如果无法获取则返回 None
        """
        try:
            # 转换为标准代码（不带后缀）
            standard_code = self.converter.to_standard(stock_code)

            # 尝试多种代码格式匹配（带后缀和不带后缀）
            possible_codes = [standard_code]
            
            # 添加带后缀的格式
            if standard_code.startswith('6'):
                possible_codes.append(f"{standard_code}.SH")
            elif standard_code.startswith('0') or standard_code.startswith('3'):
                possible_codes.append(f"{standard_code}.SZ")
            
            # 从股本信息获取
            for code in possible_codes:
                if code in self.equity_info:
                    equity = self.equity_info[code]
                    return equity.get('amount', 0)

            return None

        except Exception as e:
            logger.debug(f"⚠️ [动态阈值] 获取昨日成交额失败: {stock_code}, {e}")
            return None

    def _calculate_base_thresholds(self, stock_code: str, current_price: float = 0) -> Dict:
        """
        计算基础阈值（根据市值分层）
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格（可选）
        
        Returns:
            dict: 基础阈值
        """
        try:
            # 获取流通市值
            circulating_cap = self._get_circulating_cap(stock_code, current_price)

            if circulating_cap is None:
                # 无法获取市值，使用默认阈值
                return self.DEFAULT_THRESHOLDS.copy()

            # 获取市值分层
            tier = self._get_market_cap_tier(circulating_cap)
            tier_config = self.MARKET_CAP_TIERS[tier]
            ratio = tier_config['ratio']

            # 方案1：按流通市值计算主力流入阈值
            main_inflow_min_cap = circulating_cap * ratio

            # 方案2：按昨日成交额计算主力流入阈值
            yesterday_amount = self._get_yesterday_amount(stock_code)
            if yesterday_amount and yesterday_amount > 0:
                main_inflow_min_amount = yesterday_amount * 0.01
                # 取两种方案的最大值
                main_inflow_min = max(main_inflow_min_cap, main_inflow_min_amount)
            else:
                main_inflow_min = main_inflow_min_cap

            # 根据市值分层调整其他阈值
            if tier == 'small':
                # 小盘股：更宽松
                pct_chg_min = 2.0
                volume_ratio_min = 1.2
                turnover_min = 1.5
                risk_score_max = 0.7
            elif tier == 'mid':
                # 中盘股：标准
                pct_chg_min = 3.0
                volume_ratio_min = 1.5
                turnover_min = 2.0
                risk_score_max = 0.6
            elif tier == 'large':
                # 大盘股：较严格
                pct_chg_min = 4.0
                volume_ratio_min = 2.0
                turnover_min = 2.5
                risk_score_max = 0.5
            else:  # mega
                # 超大盘股：严格
                pct_chg_min = 5.0
                volume_ratio_min = 2.5
                turnover_min = 3.0
                risk_score_max = 0.4

            return {
                'pct_chg_min': pct_chg_min,
                'volume_ratio_min': volume_ratio_min,
                'turnover_min': turnover_min,
                'main_inflow_min': main_inflow_min,
                'risk_score_max': risk_score_max,
                'circulating_cap': circulating_cap,
                'market_cap_tier': tier,
                'market_cap_tier_name': tier_config['name']
            }

        except Exception as e:
            logger.error(f"❌ [动态阈值] 计算基础阈值失败: {stock_code}, {e}")
            return self.DEFAULT_THRESHOLDS.copy()

    def _adjust_thresholds_by_time(self, thresholds: Dict, current_time: datetime) -> Dict:
        """
        根据时间分段调整阈值
        
        Args:
            thresholds: 基础阈值
            current_time: 当前时间
        
        Returns:
            dict: 调整后的阈值
        """
        try:
            # 获取时间分段
            segment = self._get_time_segment(current_time)
            segment_config = self.TIME_SEGMENTS[segment]
            adjustment = segment_config['adjustment']

            # 调整主力流入阈值（其他阈值保持不变）
            adjusted_thresholds = thresholds.copy()
            adjusted_thresholds['main_inflow_min'] = thresholds['main_inflow_min'] * adjustment
            adjusted_thresholds['time_segment'] = segment
            adjusted_thresholds['time_segment_name'] = segment_config['name']
            adjusted_thresholds['time_adjustment'] = adjustment

            return adjusted_thresholds

        except Exception as e:
            logger.error(f"❌ [动态阈值] 时间调整失败: {e}")
            return thresholds

    def _adjust_thresholds_by_sentiment(self, thresholds: Dict, sentiment_stage: str) -> Dict:
        """
        根据情绪周期调整阈值
        
        Args:
            thresholds: 基础阈值
            sentiment_stage: 情绪周期阶段
        
        Returns:
            dict: 调整后的阈值
        """
        try:
            # 获取情绪周期配置
            if sentiment_stage not in self.SENTIMENT_STAGES:
                logger.warning(f"⚠️ [动态阈值] 未知情绪周期: {sentiment_stage}，使用默认")
                sentiment_stage = 'divergence'  # 默认使用分歧期

            stage_config = self.SENTIMENT_STAGES[sentiment_stage]
            adjustment = stage_config['adjustment']

            # 调整主力流入阈值和风险评分阈值
            adjusted_thresholds = thresholds.copy()
            adjusted_thresholds['main_inflow_min'] = thresholds['main_inflow_min'] * adjustment
            adjusted_thresholds['risk_score_max'] = thresholds['risk_score_max'] / adjustment  # 情绪差时降低风险容忍度
            adjusted_thresholds['sentiment_stage'] = sentiment_stage
            adjusted_thresholds['sentiment_stage_name'] = stage_config['name']
            adjusted_thresholds['sentiment_adjustment'] = adjustment

            return adjusted_thresholds

        except Exception as e:
            logger.error(f"❌ [动态阈值] 情绪调整失败: {e}")
            return thresholds

    def calculate_thresholds(
        self,
        stock_code: str,
        current_time: datetime,
        sentiment_stage: str = 'divergence',
        current_price: float = 0
    ) -> Dict:
        """
        动态计算阈值
        
        Args:
            stock_code: 股票代码
            current_time: 当前时间
            sentiment_stage: 情绪周期阶段（'start', 'main', 'climax', 'divergence', 'recession', 'freeze'）
            current_price: 当前价格（可选）
        
        Returns:
            dict: {
                "pct_chg_min": float,      # 最小涨幅
                "volume_ratio_min": float, # 最小量比
                "turnover_min": float,     # 最小换手率
                "main_inflow_min": float,  # 最小主力流入（元）
                "risk_score_max": float,   # 最大风险评分
                "circulating_cap": float,  # 流通市值（元）
                "market_cap_tier": str,    # 市值分层
                "market_cap_tier_name": str,  # 市值分层名称
                "time_segment": str,       # 时间分段
                "time_segment_name": str,  # 时间分段名称
                "time_adjustment": float,  # 时间调整系数
                "sentiment_stage": str,    # 情绪周期阶段
                "sentiment_stage_name": str,  # 情绪周期名称
                "sentiment_adjustment": float,  # 情绪调整系数
                "final_adjustment": float,  # 最终调整系数（时间 * 情绪）
                "calculation_time_ms": float  # 计算耗时（毫秒）
            }
        """
        start_time = time.time()

        try:
            # 1. 计算基础阈值（根据市值分层）
            thresholds = self._calculate_base_thresholds(stock_code, current_price)

            # 2. 根据时间分段调整
            thresholds = self._adjust_thresholds_by_time(thresholds, current_time)

            # 3. 根据情绪周期调整
            thresholds = self._adjust_thresholds_by_sentiment(thresholds, sentiment_stage)

            # 4. 计算最终调整系数
            time_adj = thresholds.get('time_adjustment', 1.0)
            sentiment_adj = thresholds.get('sentiment_adjustment', 1.0)
            thresholds['final_adjustment'] = time_adj * sentiment_adj

            # 5. 计算耗时
            elapsed_time = (time.time() - start_time) * 1000  # 毫秒
            thresholds['calculation_time_ms'] = elapsed_time

            # 6. 日志记录
            logger.debug(
                f"📊 [动态阈值] {stock_code} "
                f"市值={thresholds.get('circulating_cap', 0)/1e8:.1f}亿 "
                f"分层={thresholds.get('market_cap_tier_name', '')} "
                f"时间={thresholds.get('time_segment_name', '')} "
                f"情绪={thresholds.get('sentiment_stage_name', '')} "
                f"主力流入阈值={thresholds['main_inflow_min']/1e4:.0f}万 "
                f"耗时={elapsed_time:.1f}ms"
            )

            return thresholds

        except Exception as e:
            logger.error(f"❌ [动态阈值] 计算阈值失败: {stock_code}, {e}")
            # 返回默认阈值
            elapsed_time = (time.time() - start_time) * 1000
            result = self.DEFAULT_THRESHOLDS.copy()
            result['error'] = str(e)
            result['calculation_time_ms'] = elapsed_time
            return result

    def batch_calculate_thresholds(
        self,
        stock_codes: list,
        current_time: datetime,
        sentiment_stage: str = 'divergence'
    ) -> Dict[str, Dict]:
        """
        批量计算阈值
        
        Args:
            stock_codes: 股票代码列表
            current_time: 当前时间
            sentiment_stage: 情绪周期阶段
        
        Returns:
            dict: {stock_code: thresholds}
        """
        results = {}

        for code in stock_codes:
            results[code] = self.calculate_thresholds(code, current_time, sentiment_stage)

        return results

    def get_cache_info(self) -> Dict:
        """
        获取缓存信息
        
        Returns:
            dict: 缓存统计
        """
        cache_info = self.cache.get_cache_info()

        # 统计市值相关的缓存
        market_cap_cache_keys = [
            k for k in cache_info.get('缓存键列表', [])
            if k.startswith('market_cap_')
        ]

        return {
            '总缓存数': cache_info.get('缓存数量', 0),
            '市值相关缓存数': len(market_cap_cache_keys),
            '市值缓存键列表': market_cap_cache_keys
        }


# ==================== 全局实例 ====================

_dynamic_threshold: Optional[DynamicThreshold] = None


def get_dynamic_threshold() -> DynamicThreshold:
    """获取动态阈值管理器单例"""
    global _dynamic_threshold
    if _dynamic_threshold is None:
        _dynamic_threshold = DynamicThreshold()
    return _dynamic_threshold


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试动态阈值管理器
    print("=" * 80)
    print("动态阈值管理器测试")
    print("=" * 80)

    dt_manager = get_dynamic_threshold()

    # 测试股票（覆盖不同市值分层）
    test_stocks = {
        'small': ['000001', '000002'],  # 小盘股
        'mid': ['600519', '000858'],    # 中盘股
        'large': ['601318', '600036'],  # 大盘股
        'mega': ['601857', '601398']    # 超大盘股
    }

    # 测试时间分段
    test_times = [
        datetime(2026, 2, 14, 9, 45),   # 开盘阶段
        datetime(2026, 2, 14, 11, 0),   # 盘中阶段
        datetime(2026, 2, 14, 14, 45)   # 尾盘阶段
    ]

    # 测试情绪周期
    test_sentiments = ['start', 'divergence', 'freeze']

    print("\n测试配置:")
    print(f"  测试股票: {sum(len(v) for v in test_stocks.values())} 只")
    print(f"  时间分段: {len(test_times)} 个")
    print(f"  情绪周期: {len(test_sentiments)} 个")

    print("\n开始测试...\n")

    for sentiment in test_sentiments:
        print(f"\n{'=' * 80}")
        print(f"情绪周期: {sentiment} ({DynamicThreshold.SENTIMENT_STAGES[sentiment]['name']})")
        print(f"调整系数: {DynamicThreshold.SENTIMENT_STAGES[sentiment]['adjustment']}")
        print(f"{'=' * 80}")

        for test_time in test_times:
            print(f"\n🕐 时间: {test_time.strftime('%H:%M')} ({dt_manager._get_time_segment(test_time)})")

            for tier, codes in test_stocks.items():
                for code in codes:
                    thresholds = dt_manager.calculate_thresholds(code, test_time, sentiment)

                    print(f"\n  股票: {code} ({tier})")
                    print(f"    流通市值: {thresholds.get('circulating_cap', 0)/1e8:.1f}亿")
                    print(f"    市值分层: {thresholds.get('market_cap_tier_name', '')}")
                    print(f"    最小涨幅: {thresholds['pct_chg_min']}%")
                    print(f"    最小量比: {thresholds['volume_ratio_min']}")
                    print(f"    最小换手率: {thresholds['turnover_min']}%")
                    print(f"    主力流入阈值: {thresholds['main_inflow_min']/1e4:.0f}万")
                    print(f"    风险评分上限: {thresholds['risk_score_max']}")
                    print(f"    时间调整: {thresholds.get('time_adjustment', 1.0)}")
                    print(f"    情绪调整: {thresholds.get('sentiment_adjustment', 1.0)}")
                    print(f"    最终调整: {thresholds.get('final_adjustment', 1.0):.2f}")
                    print(f"    计算耗时: {thresholds['calculation_time_ms']:.2f}ms")

    print("\n" + "=" * 80)
    print("性能验证:")
    print("=" * 80)

    # 性能测试：批量计算
    batch_codes = []
    for codes in test_stocks.values():
        batch_codes.extend(codes)

    start_time = time.time()
    batch_results = dt_manager.batch_calculate_thresholds(
        batch_codes,
        datetime(2026, 2, 14, 11, 0),
        'divergence'
    )
    elapsed_time = (time.time() - start_time) * 1000

    print(f"批量计算 {len(batch_codes)} 只股票阈值:")
    print(f"  总耗时: {elapsed_time:.2f}ms")
    print(f"  平均耗时: {elapsed_time/len(batch_codes):.2f}ms/股")

    # 验证性能要求
    avg_time = elapsed_time / len(batch_codes)
    if avg_time < 50:
        print(f"  ✅ 性能达标（<50ms）")
    else:
        print(f"  ❌ 性能不达标（>{50}ms）")

    print("\n" + "=" * 80)
    print("缓存信息:")
    print("=" * 80)
    cache_info = dt_manager.get_cache_info()
    print(f"总缓存数: {cache_info['总缓存数']}")
    print(f"市值相关缓存数: {cache_info['市值相关缓存数']}")

    print("\n✅ 测试完成")
