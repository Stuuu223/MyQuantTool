# -*- coding: utf-8 -*-
"""
策略服务 - 统一策略检测门面 (Strategy Service)

整合所有战法策略：
- HALFWAY (半路突破)
- LEADER (龙头候选)
- TRUE_ATTACK (资金攻击)
- TRAP (诱多检测)

设计原则：
1. 所有阈值从config/strategy_params.json读取，禁止硬编码
2. 使用分位数而非绝对值（如>92分位，而非>7%）
3. 依赖上游已计算的标准化因子

禁止直接访问logic.strategies.*，必须通过此服务。
"""

from typing import List, Dict, Optional, Any
import pandas as pd

from logic.strategies.unified_warfare_core import UnifiedWarfareCore
from logic.strategies.true_attack_detector import TrueAttackDetector
from logic.utils.logger import get_logger
from .config_service import ConfigService

logger = get_logger(__name__)


class StrategyService:
    """
    策略服务 - 统一门面
    
    使用示例:
        service = StrategyService()
        events = service.detect_events(tick_data, context)
        
        # 或检测特定策略（使用分位数）
        leader_signal = service.check_leader(stock_code, {
            'change_pct_percentile': 0.95,  # 涨幅95分位
            'volume_ratio_percentile': 0.93  # 量比分位
        })
    """
    
    def __init__(self):
        self._warfare_core = None
        self._attack_detector = None
        self._config_service = ConfigService()
        self._strategy_params = None
    
    def _load_strategy_params(self) -> Dict:
        """懒加载策略参数（从配置文件）"""
        if self._strategy_params is None:
            self._strategy_params = self._config_service.get_strategy_params()
        return self._strategy_params
    
    def _get_warfare_core(self) -> UnifiedWarfareCore:
        """懒加载UnifiedWarfareCore"""
        if self._warfare_core is None:
            self._warfare_core = UnifiedWarfareCore()
        return self._warfare_core
    
    def _get_attack_detector(self) -> TrueAttackDetector:
        """懒加载TrueAttackDetector"""
        if self._attack_detector is None:
            self._attack_detector = TrueAttackDetector()
        return self._attack_detector
    
    def detect_events(
        self,
        tick_data: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        检测所有战法事件
        
        Args:
            tick_data: Tick数据
            context: 上下文信息（含流通市值等）
        
        Returns:
            事件列表
        """
        try:
            core = self._get_warfare_core()
            events = core.process_tick(tick_data, context or {})
            return events
        
        except Exception as e:
            logger.error(f"检测事件失败: {e}")
            return []
    
    def check_halfway(
        self,
        stock_code: str,
        factors: Dict[str, float]
    ) -> Optional[Dict]:
        """
        检查HALFWAY信号（半路突破）
        
        Args:
            stock_code: 股票代码
            factors: 标准化因子字典，必须包含：
                - price_momentum_percentile: 价格动量分位 (0-1)
                - volume_surge_percentile: 成交量突增分位 (0-1)
                - breakout_threshold_percentile: 突破阈值分位 (0-1)
                - timing_window_percentile: 时间窗口内的位置 (0-1)
        
        Returns:
            HALFWAY信号或None
        
        Note:
            所有阈值从config/strategy_params.json的halfway部分读取
            禁止使用绝对值（如>6%），必须使用分位数
        """
        logger.info(f"检查{stock_code} HALFWAY信号")
        
        params = self._load_strategy_params().get('halfway', {})
        
        # 检查是否使用分位数模式
        if not params.get('use_percentile', True):
            logger.warning("HALFWAY策略配置错误：必须启用分位数模式")
            return None
        
        # 从配置读取分位阈值
        price_momentum_threshold = params.get('price_momentum_percentile', 0.85)
        volume_surge_threshold = params.get('volume_surge_percentile', 0.88)
        
        # 使用分位数进行判断（而非绝对值）
        price_momentum_pct = factors.get('price_momentum_percentile', 0)
        volume_surge_pct = factors.get('volume_surge_percentile', 0)
        
        # HALFWAY条件：价格动量>85分位 且 成交量突增>88分位
        if price_momentum_pct >= price_momentum_threshold and \
           volume_surge_pct >= volume_surge_threshold:
            
            # 计算置信度（基于分位数）
            avg_percentile = (price_momentum_pct + volume_surge_pct) / 2
            confidence = min(avg_percentile / 0.95, 1.0)  # 95分位作为100%置信度
            
            return {
                'stock_code': stock_code,
                'signal_type': 'HALFWAY',
                'confidence': confidence,
                'factors': {
                    'price_momentum_percentile': price_momentum_pct,
                    'volume_surge_percentile': volume_surge_pct,
                    'threshold_price': price_momentum_threshold,
                    'threshold_volume': volume_surge_threshold
                }
            }
        
        return None
    
    def check_leader(
        self,
        stock_code: str,
        factors: Dict[str, float]
    ) -> Optional[Dict]:
        """
        检查龙头候选信号
        
        Args:
            stock_code: 股票代码
            factors: 标准化因子字典，必须包含：
                - change_pct_percentile: 涨幅分位 (0-1)，如0.92表示92分位
                - volume_ratio_percentile: 量比分位 (0-1)
                - circ_mv_billion: 流通市值（亿元），用于过滤小票
        
        Returns:
            龙头信号或None
        
        Note:
            龙头条件：涨幅>市场92分位，量比>市场90分位
            市值要求：>50亿（防止小票噪音）
            
            历史教训：V12.1使用绝对值7%/2倍量比，导致小票误触发
            现改用相对分位数，适应不同市场环境
        """
        logger.info(f"检查{stock_code} 龙头信号")
        
        params = self._load_strategy_params().get('leader', {})
        
        # 检查是否使用分位数模式
        if not params.get('use_percentile', True):
            logger.warning("LEADER策略配置错误：必须启用分位数模式")
            return None
        
        # 从配置读取分位阈值
        change_pct_threshold = params.get('change_pct_percentile', 0.92)
        volume_ratio_threshold = params.get('volume_ratio_percentile', 0.90)
        min_circ_mv = params.get('min_circ_mv_billion', 50)
        max_confidence_pct = params.get('max_confidence_change_pct', 0.10)
        
        # 市值过滤
        circ_mv = factors.get('circ_mv_billion', 0)
        if circ_mv < min_circ_mv:
            return None
        
        # 使用分位数进行判断
        change_pct_pct = factors.get('change_pct_percentile', 0)
        volume_ratio_pct = factors.get('volume_ratio_percentile', 0)
        
        # 龙头条件：涨幅分位>92% 且 量比分位>90%
        if change_pct_pct >= change_pct_threshold and \
           volume_ratio_pct >= volume_ratio_threshold:
            
            # 计算置信度（基于分位数，而非绝对涨幅）
            # 达到max_confidence_pct分位时置信度=1.0
            confidence = min(change_pct_pct / max_confidence_pct, 1.0)
            
            return {
                'stock_code': stock_code,
                'signal_type': 'LEADER_CANDIDATE',
                'confidence': confidence,
                'factors': {
                    'change_pct_percentile': change_pct_pct,
                    'volume_ratio_percentile': volume_ratio_pct,
                    'circ_mv_billion': circ_mv,
                    'threshold_change': change_pct_threshold,
                    'threshold_volume': volume_ratio_threshold
                }
            }
        
        return None
    
    def check_true_attack(
        self,
        stock_code: str,
        factors: Dict[str, float]
    ) -> Optional[Dict]:
        """
        检查真资金攻击信号
        
        Args:
            stock_code: 股票代码
            factors: 标准化因子字典，必须包含：
                - inflow_ratio_percentile: 资金流入强度分位 (0-1)
                - price_strength_percentile: 价格强度分位 (0-1)
                - volume_price_coordination: 量价协调度 (0-1)
        
        Returns:
            攻击信号或None
        
        Note:
            资金强度是相对概念，必须基于分位数而非绝对金额
            参考：网宿科技实验，资金分位>99%且价格强度>95%才触发
        """
        try:
            params = self._load_strategy_params().get('true_attack', {})
            
            if not params.get('use_percentile', True):
                logger.warning("TRUE_ATTACK策略配置错误：必须启用分位数模式")
                return None
            
            # 从配置读取分位阈值
            inflow_threshold = params.get('inflow_ratio_percentile', 0.99)
            price_strength_threshold = params.get('price_strength_percentile', 0.95)
            vp_coordination_threshold = params.get('volume_price_coordination_threshold', 0.80)
            
            # 获取因子分位数
            inflow_pct = factors.get('inflow_ratio_percentile', 0)
            price_strength_pct = factors.get('price_strength_percentile', 0)
            vp_coordination = factors.get('volume_price_coordination', 0)
            
            # 资金攻击条件：资金分位>99% 且 价格强度>95% 且 量价协调>80%
            if inflow_pct >= inflow_threshold and \
               price_strength_pct >= price_strength_threshold and \
               vp_coordination >= vp_coordination_threshold:
                
                # 置信度基于多重因子综合
                confidence = (inflow_pct + price_strength_pct + vp_coordination) / 3
                
                return {
                    'stock_code': stock_code,
                    'signal_type': 'TRUE_ATTACK',
                    'confidence': confidence,
                    'factors': {
                        'inflow_ratio_percentile': inflow_pct,
                        'price_strength_percentile': price_strength_pct,
                        'volume_price_coordination': vp_coordination,
                        'threshold_inflow': inflow_threshold,
                        'threshold_price': price_strength_threshold
                    }
                }
            
            return None
        
        except Exception as e:
            logger.error(f"检查资金攻击失败: {e}")
            return None
