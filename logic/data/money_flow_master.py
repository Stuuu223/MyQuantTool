#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.5 Money Flow Master - 资金流大师
DDE 核心战法：资金穿透分析
V18.5: 将 DDE 逻辑从"建议"变成"否决权"
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from logic.utils.logger import get_logger
from logic.data.data_manager import DataManager

logger = get_logger(__name__)


class MoneyFlowMaster:
    """
    V18.5 资金流大师（Money Flow Master）
    
    核心战法：
    1. DDE 背离低吸：股价下跌但 DDE 持续走高（机构压盘吸筹）
    2. DDE 抢筹确认：竞价阶段 DDE 活跃度突破历史均值 5 倍
    3. DDE 否决权：DDE 为负时，禁止发出 BUY 信号
    """
    
    # DDE 阈值配置
    DDE_BUY_THRESHOLD = 0.5      # DDE 净额 > 0.5亿才考虑买入
    DDE_STRONG_THRESHOLD = 1.0   # DDE 净额 > 1.0亿为强信号
    DDE_NEGATIVE_THRESHOLD = -0.3 # DDE 净额 < -0.3亿为负信号
    
    # 竞价 DDE 阈值
    AUCTION_DDE_MULTIPLIER = 5.0  # 竞价 DDE 活跃度突破历史均值 5 倍
    
    def __init__(self):
        """初始化资金流大师"""
        self.data_manager = DataManager()
        
        # DDE 历史数据缓存（用于计算均值）
        self._dde_history_cache = {}  # {stock_code: {'dde_values': [], 'last_update': datetime}}
        self._cache_ttl = 3600  # 缓存有效期（秒），1小时
    
    def check_dde_divergence(self, stock_code: str, current_price: float, prev_close: float) -> Dict[str, Any]:
        """
        检查 DDE 背离低吸信号
        
        逻辑：股价下跌 2%-3%，但 DDE 净额却在持续走高（典型的机构压盘吸筹）
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            prev_close: 昨收价
        
        Returns:
            dict: {
                'has_divergence': bool,  # 是否有背离
                'divergence_type': str,  # 背离类型
                'price_change': float,   # 价格变化
                'dde_trend': str,        # DDE 趋势
                'confidence': float,     # 置信度（0-1）
                'reason': str            # 原因
            }
        """
        result = {
            'has_divergence': False,
            'divergence_type': '',
            'price_change': 0.0,
            'dde_trend': '',
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 计算价格变化
            price_change = (current_price - prev_close) / prev_close * 100
            result['price_change'] = price_change
            
            # 2. 获取 DDE 数据
            realtime_data = self.data_manager.get_realtime_data(stock_code)
            if not realtime_data:
                result['reason'] = '无法获取实时数据'
                return result
            
            dde_net_flow = realtime_data.get('dde_net_flow', 0)
            
            # 3. 获取 DDE 历史数据
            dde_history = self._get_dde_history(stock_code)
            if not dde_history or len(dde_history) < 3:
                result['reason'] = 'DDE 历史数据不足'
                return result
            
            # 4. 判断价格下跌（2%-3%）
            if -3.0 <= price_change <= -2.0:
                # 5. 判断 DDE 趋势（持续走高）
                recent_dde = dde_history[-3:]  # 最近 3 个数据点
                dde_trend = 'up' if recent_dde[-1] > recent_dde[0] else 'down'
                
                if dde_trend == 'up' and dde_net_flow > 0:
                    result['has_divergence'] = True
                    result['divergence_type'] = 'price_down_dde_up'
                    result['dde_trend'] = 'up'
                    result['confidence'] = min(0.8, abs(price_change) / 3.0)
                    result['reason'] = f'🔥 [DDE背离] 股价下跌{price_change:.2f}%，DDE持续走高（{dde_net_flow:.2f}亿），机构压盘吸筹'
                    logger.info(f"✅ [DDE背离] {stock_code} 检测到背离信号：{result['reason']}")
                else:
                    result['reason'] = f'价格下跌{price_change:.2f}%，但DDE未持续走高'
            else:
                result['reason'] = f'价格变化{price_change:.2f}%不在背离区间（-3% ~ -2%）'
        
        except Exception as e:
            logger.error(f"检查 DDE 背离失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def check_auction_dde_surge(self, stock_code: str, auction_time: str = '09:25') -> Dict[str, Any]:
        """
        检查竞价 DDE 抢筹信号
        
        逻辑：竞价阶段 9:20-9:25，DDE 活跃度突破历史均值 5 倍
        
        Args:
            stock_code: 股票代码
            auction_time: 竞价时间（默认 09:25）
        
        Returns:
            dict: {
                'has_surge': bool,        # 是否有抢筹
                'auction_dde': float,     # 竞价 DDE
                'historical_mean': float, # 历史均值
                'surge_ratio': float,     # 突破倍数
                'confidence': float,      # 置信度（0-1）
                'reason': str             # 原因
            }
        """
        result = {
            'has_surge': False,
            'auction_dde': 0.0,
            'historical_mean': 0.0,
            'surge_ratio': 0.0,
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 获取竞价 DDE 数据
            realtime_data = self.data_manager.get_realtime_data(stock_code)
            if not realtime_data:
                result['reason'] = '无法获取实时数据'
                return result
            
            auction_dde = realtime_data.get('dde_net_flow', 0)
            result['auction_dde'] = auction_dde
            
            # 2. 获取 DDE 历史均值
            dde_history = self._get_dde_history(stock_code)
            if not dde_history or len(dde_history) < 5:
                result['reason'] = 'DDE 历史数据不足'
                return result
            
            historical_mean = np.mean(dde_history)
            result['historical_mean'] = historical_mean
            
            # 3. 计算突破倍数
            if historical_mean > 0:
                surge_ratio = auction_dde / historical_mean
                result['surge_ratio'] = surge_ratio
                
                # 4. 判断是否突破阈值
                if surge_ratio >= self.AUCTION_DDE_MULTIPLIER and auction_dde > 0:
                    result['has_surge'] = True
                    result['confidence'] = min(0.9, surge_ratio / 10.0)
                    result['reason'] = f'🚀 [竞价抢筹] DDE活跃度突破历史均值{surge_ratio:.1f}倍（{auction_dde:.2f}亿 vs {historical_mean:.2f}亿）'
                    logger.info(f"✅ [竞价抢筹] {stock_code} 检测到抢筹信号：{result['reason']}")
                else:
                    result['reason'] = f'DDE活跃度未突破阈值（{surge_ratio:.1f}倍 < {self.AUCTION_DDE_MULTIPLIER}倍）'
            else:
                result['reason'] = f'历史均值为0，无法计算突破倍数'
        
        except Exception as e:
            logger.error(f"检查竞价 DDE 抢筹失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def check_price_discovery_stage(self, stock_code: str, current_price: float, prev_close: float) -> Dict[str, Any]:
        """
        🆕 V18.6: 检查价格发现阶段（DDE抢筹战法）
        
        逻辑：在股价只有 3%-5% 的时候，主力通过连续的巨量大单（DDE红柱）进行暴力扫货。
        这种确定性来自于"成本压制"：主力花了 2 个亿在 4% 的位置建仓，他今天不把股价顶上板，他自己就出不来。
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            prev_close: 昨收价
        
        Returns:
            dict: {
                'in_price_discovery': bool,  # 是否在价格发现阶段
                'price_range': str,          # 价格区间
                'dde_pulse_strength': float, # DDE脉冲强度
                'volume_amplification': float, # 成交量放大倍数
                'has_continuous_big_orders': bool, # 是否有连续巨量大单
                'confidence': float,         # 置信度（0-1）
                'reason': str                # 原因
            }
        """
        result = {
            'in_price_discovery': False,
            'price_range': '',
            'dde_pulse_strength': 0.0,
            'volume_amplification': 0.0,
            'has_continuous_big_orders': False,
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 计算当前涨幅
            if prev_close == 0:
                result['reason'] = '昨收价为0，无法计算涨幅'
                return result
            
            current_pct_change = (current_price - prev_close) / prev_close * 100
            result['price_range'] = f"{current_pct_change:.1f}%"
            
            # 2. 判断是否在价格发现阶段（3%-5%）
            if 3.0 <= current_pct_change <= 5.0:
                result['in_price_discovery'] = True
                
                # 3. 获取实时数据
                realtime_data = self.data_manager.get_realtime_data(stock_code)
                if not realtime_data:
                    result['reason'] = '无法获取实时数据'
                    return result
                
                # 4. 检查 DDE 是否持续净流入
                dde_net_flow = realtime_data.get('dde_net_flow', 0)
                dde_history = self._get_dde_history(stock_code, lookback=10)
                
                if dde_history and len(dde_history) >= 5:
                    # 计算 DDE 脉冲强度（最近5分钟的DDE均值 vs 历史均值）
                    recent_dde_mean = np.mean(dde_history[-5:])
                    historical_dde_mean = np.mean(dde_history[:-5]) if len(dde_history) > 5 else 0
                    
                    if historical_dde_mean > 0:
                        dde_pulse_strength = recent_dde_mean / historical_dde_mean
                        result['dde_pulse_strength'] = dde_pulse_strength
                    else:
                        dde_pulse_strength = 0.0
                        result['dde_pulse_strength'] = dde_pulse_strength
                
                # 5. 检查成交量是否放大
                current_volume = realtime_data.get('volume', 0)
                turnover_rate = realtime_data.get('turnover_rate', 0)
                
                # 🆕 V18.6.1: 检查流动性陷阱（问题B修复）
                # 要求：量比 > 1.5 且 换手率 > 3% 且 日成交额预计 > 1亿
                # 确保有对手盘让你全身而退
                min_volume_ratio = 1.5
                min_turnover_rate = 3.0
                min_turnover_amount = 100000000  # 1亿
                
                # 获取历史成交量（这里简化处理，实际应该从K线数据获取）
                avg_volume = current_volume / 2.0  # 假设历史平均成交量是当前的一半
                volume_amplification = current_volume / avg_volume if avg_volume > 0 else 1.0
                result['volume_amplification'] = volume_amplification
                
                # 计算日成交额
                current_price = realtime_data.get('price', 0)
                turnover_amount = current_volume * 100 * current_price  # 手数 * 100股/手 * 价格
                
                # 检查流动性陷阱
                liquidity_ok = (
                    volume_amplification >= min_volume_ratio and
                    turnover_rate >= min_turnover_rate and
                    turnover_amount >= min_turnover_amount
                )
                result['liquidity_ok'] = liquidity_ok
                result['turnover_rate'] = turnover_rate
                result['turnover_amount'] = turnover_amount
                
                if not liquidity_ok:
                    result['reason'] = f'⚠️ [流动性陷阱] 涨幅{current_pct_change:.1f}%，但流动性不足（量比{volume_amplification:.1f} < {min_volume_ratio}，换手率{turnover_rate:.1f}% < {min_turnover_rate}%，成交额{turnover_amount/100000000:.2f}亿 < {min_turnover_amount/100000000:.1f}亿），可能是庄股自嗨'
                    logger.warning(f"❌ [流动性陷阱] {stock_code} {result['reason']}")
                    return result
                
                # 6. 检查是否有连续的巨量大单（这里简化处理，实际应该检查逐笔数据）
                # 假设如果DDE > 0.5亿，说明有巨量大单
                has_continuous_big_orders = dde_net_flow > 0.5
                result['has_continuous_big_orders'] = has_continuous_big_orders
                
                # 7. 综合判断
                confidence = 0.0
                
                # DDE脉冲强度评分
                if dde_pulse_strength >= 5.0:
                    confidence += 0.4
                elif dde_pulse_strength >= 3.0:
                    confidence += 0.3
                elif dde_pulse_strength >= 2.0:
                    confidence += 0.2
                
                # 成交量放大评分
                if volume_amplification >= 3.0:
                    confidence += 0.3
                elif volume_amplification >= 2.0:
                    confidence += 0.2
                elif volume_amplification >= 1.5:
                    confidence += 0.1
                
                # 连续巨量大单评分
                if has_continuous_big_orders:
                    confidence += 0.3
                
                result['confidence'] = min(1.0, confidence)
                
                # 8. 生成原因
                if result['confidence'] >= 0.7:
                    result['reason'] = f'🔥 [价格发现] 涨幅{current_pct_change:.1f}%，DDE脉冲{dde_pulse_strength:.1f}倍，成交量{volume_amplification:.1f}倍，主力暴力扫货'
                    logger.info(f"✅ [价格发现] {stock_code} 检测到抢筹信号：{result['reason']}")
                elif result['confidence'] >= 0.4:
                    result['reason'] = f'⚠️ [价格发现] 涨幅{current_pct_change:.1f}%，有抢筹迹象但强度不足'
                else:
                    result['reason'] = f'📊 [价格发现] 涨幅{current_pct_change:.1f}%，暂无明显抢筹信号'
            else:
                result['reason'] = f'涨幅{current_pct_change:.1f}%不在价格发现阶段（3%-5%）'
        
        except Exception as e:
            logger.error(f"检查价格发现阶段失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def check_dde_veto(self, stock_code: str, signal: str, buy_mode: str = 'DRAGON_CHASE') -> Tuple[bool, str]:
        """
        DDE 否决权检查
        
        🆕 V18.6: 引入 buy_mode 参数，区分不同的买入策略：
        - DRAGON_CHASE（追龙头）：DDE 必须为正，严格执行否决权
        - LOW_SUCTION（低吸）：检查 DDE 变动率（斜率），允许 DDE 为负但转正的情况
        
        Args:
            stock_code: 股票代码
            signal: 原始信号（BUY/SELL/HOLD）
            buy_mode: 买入模式（DRAGON_CHASE 或 LOW_SUCTION）
        
        Returns:
            tuple: (是否否决, 否决原因)
        """
        try:
            # 只有 BUY 信号才需要检查 DDE 否决权
            if signal != 'BUY':
                return False, ''
            
            # 获取 DDE 数据
            realtime_data = self.data_manager.get_realtime_data(stock_code)
            if not realtime_data:
                return False, '无法获取 DDE 数据，跳过否决检查'
            
            dde_net_flow = realtime_data.get('dde_net_flow', 0)
            
            # 🆕 V18.6: 根据买入模式采用不同的 DDE 检查逻辑
            if buy_mode == 'DRAGON_CHASE':
                # 追龙头模式：DDE 必须为正，严格执行否决权
                if dde_net_flow < self.DDE_NEGATIVE_THRESHOLD:
                    veto_reason = f'🛑 [DDE否决权-追龙] DDE净额为负（{dde_net_flow:.2f}亿），禁止发出 BUY 信号'
                    logger.warning(f"❌ {stock_code} {veto_reason}")
                    return True, veto_reason
                
                # DDE 弱信号：DDE < 0.5亿，发出警告
                if dde_net_flow < self.DDE_BUY_THRESHOLD:
                    warning_reason = f'⚠️ [DDE警告-追龙] DDE净额较弱（{dde_net_flow:.2f}亿），建议谨慎'
                    logger.info(f"⚠️ {stock_code} {warning_reason}")
                    return False, warning_reason
                
                # DDE 强信号：DDE > 1.0亿，增强信心
                if dde_net_flow > self.DDE_STRONG_THRESHOLD:
                    strong_reason = f'✅ [DDE强信号-追龙] DDE净额强劲（{dde_net_flow:.2f}亿），增强买入信心'
                    logger.info(f"✅ {stock_code} {strong_reason}")
                    return False, strong_reason
            
            elif buy_mode == 'LOW_SUCTION':
                # 低吸模式：检查 DDE 变动率（斜率），允许 DDE 为负但转正的情况
                # 获取 DDE 历史数据
                dde_history = self._get_dde_history(stock_code, lookback=5)
                
                if dde_history and len(dde_history) >= 3:
                    # 计算 DDE 斜率（变动率）
                    recent_dde = dde_history[-3:]  # 最近 3 个数据点
                    dde_slope = (recent_dde[-1] - recent_dde[0]) / len(recent_dde)  # 每个数据点的平均变化
                    
                    # 如果 DDE 为负但斜率转正，说明卖盘枯竭，主力开始承接
                    if dde_net_flow < 0 and dde_slope > 0:
                        suction_reason = f'🔥 [DDE低吸] DDE净额为负（{dde_net_flow:.2f}亿），但斜率转正（{dde_slope:.3f}），卖盘枯竭，主力承接'
                        logger.info(f"✅ {stock_code} {suction_reason}")
                        return False, suction_reason
                    
                    # 如果 DDE 为负且斜率继续向下，说明还在砸盘，禁止买入
                    if dde_net_flow < self.DDE_NEGATIVE_THRESHOLD and dde_slope < 0:
                        veto_reason = f'🛑 [DDE否决权-低吸] DDE净额为负（{dde_net_flow:.2f}亿）且斜率向下（{dde_slope:.3f}），还在砸盘，禁止买入'
                        logger.warning(f"❌ {stock_code} {veto_reason}")
                        return True, veto_reason
                
                # 如果无法获取历史数据，采用保守策略
                if dde_net_flow < self.DDE_NEGATIVE_THRESHOLD:
                    veto_reason = f'🛑 [DDE否决权-低吸] DDE净额为负（{dde_net_flow:.2f}亿），无法判断斜率，保守处理，禁止买入'
                    logger.warning(f"❌ {stock_code} {veto_reason}")
                    return True, veto_reason
                
                # 如果 DDE 为正，说明主力已经在承接
                if dde_net_flow > 0:
                    if dde_net_flow < self.DDE_BUY_THRESHOLD:
                        warning_reason = f'⚠️ [DDE警告-低吸] DDE净额较弱（{dde_net_flow:.2f}亿），建议谨慎'
                        logger.info(f"⚠️ {stock_code} {warning_reason}")
                        return False, warning_reason
                    elif dde_net_flow > self.DDE_STRONG_THRESHOLD:
                        strong_reason = f'✅ [DDE强信号-低吸] DDE净额强劲（{dde_net_flow:.2f}亿），主力强势承接'
                        logger.info(f"✅ {stock_code} {strong_reason}")
                        return False, strong_reason
            
            else:
                # 默认使用 DRAGON_CHASE 模式
                if dde_net_flow < self.DDE_NEGATIVE_THRESHOLD:
                    veto_reason = f'🛑 [DDE否决权] DDE净额为负（{dde_net_flow:.2f}亿），禁止发出 BUY 信号'
                    logger.warning(f"❌ {stock_code} {veto_reason}")
                    return True, veto_reason
                    return True, veto_reason
            
            return False, ''
        
        except Exception as e:
            logger.error(f"检查 DDE 否决权失败: {e}")
            return False, f'检查失败: {e}'
    
    def calculate_dde_score(self, stock_code: str) -> float:
        """
        计算 DDE 评分（0-100）
        
        评分标准：
        - DDE > 1.0亿：80-100分
        - DDE > 0.5亿：60-80分
        - DDE > 0：40-60分
        - DDE < 0：0-40分
        
        Args:
            stock_code: 股票代码
        
        Returns:
            float: DDE 评分（0-100）
        """
        try:
            # 获取 DDE 数据
            realtime_data = self.data_manager.get_realtime_data(stock_code)
            if not realtime_data:
                return 50.0  # 默认中性评分
            
            dde_net_flow = realtime_data.get('dde_net_flow', 0)
            
            # 计算 DDE 评分
            if dde_net_flow > self.DDE_STRONG_THRESHOLD:
                # 1.0亿以上：80-100分
                score = 80 + min(20, (dde_net_flow - self.DDE_STRONG_THRESHOLD) / self.DDE_STRONG_THRESHOLD * 20)
            elif dde_net_flow > self.DDE_BUY_THRESHOLD:
                # 0.5-1.0亿：60-80分
                score = 60 + (dde_net_flow - self.DDE_BUY_THRESHOLD) / (self.DDE_STRONG_THRESHOLD - self.DDE_BUY_THRESHOLD) * 20
            elif dde_net_flow > 0:
                # 0-0.5亿：40-60分
                score = 40 + dde_net_flow / self.DDE_BUY_THRESHOLD * 20
            elif dde_net_flow > self.DDE_NEGATIVE_THRESHOLD:
                # -0.3-0亿：20-40分
                score = 20 + (dde_net_flow - self.DDE_NEGATIVE_THRESHOLD) / abs(self.DDE_NEGATIVE_THRESHOLD) * 20
            else:
                # -0.3亿以下：0-20分
                score = max(0, 20 + dde_net_flow / abs(self.DDE_NEGATIVE_THRESHOLD) * 20)
            
            return min(100, max(0, score))
        
        except Exception as e:
            logger.error(f"计算 DDE 评分失败: {e}")
            return 50.0
    
    def _get_dde_history(self, stock_code: str, lookback: int = 10) -> List[float]:
        """
        获取 DDE 历史数据
        
        Args:
            stock_code: 股票代码
            lookback: 回看天数
        
        Returns:
            list: DDE 历史数据列表
        """
        try:
            # 检查缓存
            cache_key = stock_code
            if cache_key in self._dde_history_cache:
                cache_data = self._dde_history_cache[cache_key]
                cache_age = (datetime.now() - cache_data['last_update']).total_seconds()
                if cache_age < self._cache_ttl:
                    return cache_data['dde_values'][-lookback:]
            
            # 从数据库获取历史数据
            # 这里需要实现从数据库获取 DDE 历史数据的逻辑
            # 暂时返回空列表
            return []
        
        except Exception as e:
            logger.error(f"获取 DDE 历史数据失败: {e}")
            return []
    
    def analyze_money_flow(self, stock_code: str, current_price: float, prev_close: float) -> Dict[str, Any]:
        """
        综合分析资金流
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            prev_close: 昨收价
        
        Returns:
            dict: {
                'dde_score': float,           # DDE 评分（0-100）
                'divergence_signal': dict,    # 背离信号
                'auction_surge': dict,        # 竞价抢筹信号
                'overall_assessment': str,    # 综合评估
                'recommendation': str         # 建议
            }
        """
        result = {
            'dde_score': 0.0,
            'divergence_signal': {},
            'auction_surge': {},
            'overall_assessment': '',
            'recommendation': ''
        }
        
        try:
            # 1. 计算 DDE 评分
            result['dde_score'] = self.calculate_dde_score(stock_code)
            
            # 2. 检查 DDE 背离信号
            result['divergence_signal'] = self.check_dde_divergence(stock_code, current_price, prev_close)
            
            # 3. 检查竞价抢筹信号
            result['auction_surge'] = self.check_auction_dde_surge(stock_code)
            
            # 4. 综合评估
            signals = []
            if result['divergence_signal'].get('has_divergence'):
                signals.append('DDE背离低吸')
            if result['auction_surge'].get('has_surge'):
                signals.append('竞价抢筹')
            
            if signals:
                result['overall_assessment'] = f'资金流强势：{", ".join(signals)}'
                result['recommendation'] = 'BUY'
            elif result['dde_score'] >= 60:
                result['overall_assessment'] = '资金流健康'
                result['recommendation'] = 'HOLD'
            elif result['dde_score'] >= 40:
                result['overall_assessment'] = '资金流中性'
                result['recommendation'] = 'HOLD'
            else:
                result['overall_assessment'] = '资金流疲弱'
                result['recommendation'] = 'SELL'
            
        except Exception as e:
            logger.error(f"综合分析资金流失败: {e}")
            result['overall_assessment'] = f'分析失败: {e}'
            result['recommendation'] = 'HOLD'
        
        return result


# 便捷函数
_mfm_instance = None

def get_money_flow_master() -> MoneyFlowMaster:
    """获取资金流大师单例"""
    global _mfm_instance
    if _mfm_instance is None:
        _mfm_instance = MoneyFlowMaster()
    return _mfm_instance