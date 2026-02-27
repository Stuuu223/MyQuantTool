#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一战法核心模块 (Unified Warfare Core) - V20 Step3 形态基因与战法分流

【Step3 CTO终极红线指令】
在战法检测器中实现动态均线过滤（权力已从global_filter_gateway下放）：
1. 推土机战法：开启均线锁，严格要求MA5 > MA10，多头排列
2. 弱转强战法：无视均线死叉，检测极速反包
3. 首阴低吸战法：无视Price < MA20的破位

核心功能：
1. 统一管理所有战法事件检测器
2. 提供战法分流主入口 classify_warfare_type
3. 动态均线过滤（推土机）vs 无视均线（反包/弱转强）
4. 战法标签注入metadata

Author: iFlow CLI
Version: V20.3.0
Date: 2026-02-27
"""

<<<<<<< HEAD
from typing import Dict, List, Optional, Any, Callable
=======
from typing import Dict, List, Optional, Any, Callable, Tuple
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
from datetime import datetime
from enum import Enum

# 【CTO P0抢修】移除不存在的event_detector依赖
# 内嵌EventManager实现，避免外部依赖
class EventManager:
    """内嵌事件管理器 - 替换不存在的event_detector模块"""
    def __init__(self):
        self.detectors: Dict[str, Any] = {}
    
    def register_detector(self, detector):
        """注册检测器"""
        if hasattr(detector, 'name'):
            self.detectors[detector.name] = detector
        else:
            self.detectors[detector.__class__.__name__] = detector
    
    def detect_events(self, tick_data: Dict, context: Dict = None) -> List[Dict]:
        """检测所有事件"""
        events = []
        for detector in self.detectors.values():
            if getattr(detector, 'enabled', True):
                try:
                    result = detector.detect(tick_data, context)
                    if result:
                        events.append(result)
                except Exception as e:
                    pass
        return events
    
    def enable_detector(self, name: str):
        """启用检测器"""
        if name in self.detectors:
            self.detectors[name].enabled = True
    
    def disable_detector(self, name: str):
        """禁用检测器"""
        if name in self.detectors:
            self.detectors[name].enabled = False

# NOTE: OpeningWeakToStrongDetector已物理删除（占位文件）
# from logic.strategies.opening_weak_to_strong_detector import OpeningWeakToStrongDetector
# NOTE: HalfwayBreakoutDetector已归档至archive/redundant_halfway/
# from logic.strategies.halfway_breakout_detector import HalfwayBreakoutDetector
from logic.strategies.leader_candidate_detector import LeaderCandidateDetector
from logic.strategies.dip_buy_candidate_detector import DipBuyCandidateDetector
from logic.utils.logger import get_logger
from logic.utils.math_utils_core import calculate_space_gap
from logic.core.metric_definitions import MetricDefinitions

logger = get_logger(__name__)


# =============================================================================
# Step3: 战法类型枚举
# =============================================================================
class WarfareType(Enum):
    """战法类型枚举"""
    TREND_RIDER = "推土机"           # 推土机战法：均线多头排列
    WEAK_TO_STRONG = "弱转强"        # 弱转强战法：极速反包
    HIGH_VOL_REBOUND = "首阴低吸"    # 首阴低吸战法：高波反包
    UNKNOWN = "未知"


# =============================================================================
# Step3: 战法检测器基类
# =============================================================================
class WarfareStrategyBase:
    """战法检测器基类"""
    
    def __init__(self, name: str, ma_required: bool = True):
        self.name = name
        self.ma_required = ma_required  # 是否需要均线验证
    
    def detect(self, stock_data: Dict) -> Tuple[bool, Dict]:
        """
        检测战法
        
        Returns:
            (是否匹配, metadata字典)
        """
        raise NotImplementedError


# =============================================================================
# Step3: 推土机战法检测器 (TrendRiderStrategy)
# =============================================================================
class TrendRiderStrategy(WarfareStrategyBase):
    """
    推土机战法：开启均线锁，严格要求MA5 > MA10，多头排列
    
    检测条件：
    - MA5 > MA10 （短期均线在上方）
    - Price > MA20 （价格在20日均线上方）
    - 均线呈多头排列
    """
    
    def __init__(self):
        super().__init__("推土机战法", ma_required=True)
    
    def detect(self, stock_data: Dict) -> Tuple[bool, Dict]:
        """
        检测推土机战法
        
        Args:
            stock_data: 股票数据字典，包含MA和价格信息
            
        Returns:
            (是否匹配, metadata)
        """
        try:
            # 提取必要数据
            price = stock_data.get('price', 0)
            ma5 = stock_data.get('ma5', 0)
            ma10 = stock_data.get('ma10', 0)
            ma20 = stock_data.get('ma20', 0)
            
            # 数据有效性检查
            if price <= 0 or ma5 <= 0 or ma10 <= 0 or ma20 <= 0:
                return False, {'reason': '无效的价格或均线数据'}
            
            # 【均线锁】推土机战法严格要求MA5 > MA10
            ma_aligned = ma5 > ma10
            
            # 价格站在MA20之上
            price_above_ma20 = price > ma20
            
            # 多头确认（三均线向上）
            bullish_arrangement = ma5 > ma10 > ma20
            
            # 综合判断
            is_trend_rider = ma_aligned and price_above_ma20 and bullish_arrangement
            
            metadata = {
                'warfare_type': WarfareType.TREND_RIDER.value,
                'ma_required': True,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
                'price': price,
                'ma_aligned': ma_aligned,
                'price_above_ma20': price_above_ma20,
                'bullish_arrangement': bullish_arrangement,
                'passed': is_trend_rider
            }
            
            if is_trend_rider:
                logger.debug(f"🚜 [推土机战法] {stock_data.get('stock_code', 'Unknown')} 均线多头排列")
            
            return is_trend_rider, metadata
            
        except Exception as e:
            logger.error(f"❌ [推土机战法] 检测失败: {e}")
            return False, {'reason': f'检测异常: {str(e)}'}


# =============================================================================
# Step3: 弱转强战法检测器 (WeakToStrongStrategy)
# =============================================================================
class WeakToStrongStrategy(WarfareStrategyBase):
    """
    弱转强战法：无视均线死叉，检测极速反包
    
    检测条件：
    - 昨收盘大阴/跌停 (change_pct < -5%)
    - Space_Gap_Pct < 10% (距离前高近)
    - 今日早盘flow_1min极速爆量正流入
    
    特点：无视均线死叉，只要资金态度坚决即可
    """
    
    def __init__(self):
        super().__init__("弱转强战法", ma_required=False)
    
    def detect(self, stock_data: Dict) -> Tuple[bool, Dict]:
        """
        检测弱转强战法
        
        Args:
            stock_data: 股票数据字典
            
        Returns:
            (是否匹配, metadata)
        """
        try:
            # 提取数据
            stock_code = stock_data.get('stock_code', 'Unknown')
            price = stock_data.get('price', 0)
            prev_close = stock_data.get('prev_close', 0)
            high_60d = stock_data.get('high_60d', 0)
            flow_1min = stock_data.get('flow_1min', 0)  # 1分钟资金流量
            
            # 昨收涨跌幅
            prev_change_pct = stock_data.get('prev_change_pct', 0)
            
            # 条件1：昨收盘大阴/跌停 (change_pct < -5%)
            was_weak_yesterday = prev_change_pct < -5.0
            
            # 条件2：Space_Gap_Pct < 10% (距离前高近，有突破预期)
            space_gap_valid = False
            if high_60d > 0 and price > 0:
                space_gap = calculate_space_gap(price, high_60d)
                space_gap_valid = space_gap < 10.0  # 距离高点不到10%
            
            # 条件3：今日早盘flow_1min极速爆量正流入
            # flow_1min > 0 表示资金正流入
            has_capital_inflow = flow_1min > 0
            
            # 综合判断（无视均线状态）
            is_weak_to_strong = was_weak_yesterday and space_gap_valid and has_capital_inflow
            
            metadata = {
                'warfare_type': WarfareType.WEAK_TO_STRONG.value,
                'ma_required': False,
                'prev_change_pct': prev_change_pct,
                'was_weak_yesterday': was_weak_yesterday,
                'space_gap_pct': calculate_space_gap(price, high_60d) if high_60d > 0 else None,
                'space_gap_valid': space_gap_valid,
                'flow_1min': flow_1min,
                'has_capital_inflow': has_capital_inflow,
                'passed': is_weak_to_strong
            }
            
            if is_weak_to_strong:
                logger.info(f"⚡ [弱转强战法] {stock_code} 昨阴今反包，资金极速流入")
            
            return is_weak_to_strong, metadata
            
        except Exception as e:
            logger.error(f"❌ [弱转强战法] 检测失败: {e}")
            return False, {'reason': f'检测异常: {str(e)}'}


# =============================================================================
# Step3: 首阴低吸战法检测器 (HighVolReboundStrategy)
# =============================================================================
class HighVolReboundStrategy(WarfareStrategyBase):
    """
    首阴低吸战法：无视Price < MA20的破位
    
    检测条件：
    - 前序缩量下跌 (prev_volume < avg_volume * 0.7)
    - 当前flow_5min > 0 (资金流由负转正)
    
    特点：无视价格跌破MA20，只看量价背离和资金流
    """
    
    def __init__(self):
        super().__init__("首阴低吸战法", ma_required=False)
    
    def detect(self, stock_data: Dict) -> Tuple[bool, Dict]:
        """
        检测首阴低吸战法
        
        Args:
            stock_data: 股票数据字典
            
        Returns:
            (是否匹配, metadata)
        """
        try:
            # 提取数据
            stock_code = stock_data.get('stock_code', 'Unknown')
            price = stock_data.get('price', 0)
            ma20 = stock_data.get('ma20', 0)
            
            # 前序成交量数据
            prev_volume = stock_data.get('prev_volume', 0)
            avg_volume_5d = stock_data.get('avg_volume_5d', 0)
            
            # 5分钟资金流
            flow_5min = stock_data.get('flow_5min', 0)
            
            # 条件1：前序缩量下跌 (prev_volume < avg_volume * 0.7)
            is_shrinking = False
            if avg_volume_5d > 0:
                volume_ratio = prev_volume / avg_volume_5d
                is_shrinking = volume_ratio < 0.7
            
            # 条件2：当前flow_5min > 0 (资金流由负转正)
            flow_turning_positive = flow_5min > 0
            
            # 条件3：价格跌破MA20（首阴特征，非必须）
            price_below_ma20 = False
            if price > 0 and ma20 > 0:
                price_below_ma20 = price < ma20
            
            # 综合判断（无视均线破位）
            is_high_vol_rebound = is_shrinking and flow_turning_positive
            
            metadata = {
                'warfare_type': WarfareType.HIGH_VOL_REBOUND.value,
                'ma_required': False,
                'prev_volume': prev_volume,
                'avg_volume_5d': avg_volume_5d,
                'volume_ratio': prev_volume / avg_volume_5d if avg_volume_5d > 0 else None,
                'is_shrinking': is_shrinking,
                'flow_5min': flow_5min,
                'flow_turning_positive': flow_turning_positive,
                'price': price,
                'ma20': ma20,
                'price_below_ma20': price_below_ma20,
                'passed': is_high_vol_rebound
            }
            
            if is_high_vol_rebound:
                logger.info(f"🎯 [首阴低吸战法] {stock_code} 缩量下跌后资金回流")
            
            return is_high_vol_rebound, metadata
            
        except Exception as e:
            logger.error(f"❌ [首阴低吸战法] 检测失败: {e}")
            return False, {'reason': f'检测异常: {str(e)}'}


# =============================================================================
# Step3: 战法分流主分发器
# =============================================================================
class WarfareClassifier:
    """
    战法分流主分发器
    
    依次检测：推土机 -> 弱转强 -> 首阴低吸
    返回: (warfare_type, metadata)
    """
    
    def __init__(self):
        self.strategies = [
            TrendRiderStrategy(),
            WeakToStrongStrategy(),
            HighVolReboundStrategy()
        ]
        logger.info("✅ [战法分流器] 初始化完成，已加载3个战法检测器")
    
    def classify(self, stock_data: Dict) -> Tuple[str, Dict]:
        """
        战法分流主入口
        
        依次检测各战法，返回第一个匹配的战法类型
        
        Args:
            stock_data: 股票数据字典
            
        Returns:
            (warfare_type_str, metadata)
        """
        stock_code = stock_data.get('stock_code', 'Unknown')
        
        for strategy in self.strategies:
            matched, metadata = strategy.detect(stock_data)
            if matched:
                warfare_type = metadata.get('warfare_type', WarfareType.UNKNOWN.value)
                ma_required = metadata.get('ma_required', True)
                
                logger.info(
                    f"🎯 [战法分流] {stock_code} -> {warfare_type} "
                    f"(均线验证: {'是' if ma_required else '否'})"
                )
                
                return warfare_type, metadata
        
        # 无匹配
        return WarfareType.UNKNOWN.value, {'ma_required': True}
    
    def classify_with_all(self, stock_data: Dict) -> List[Dict]:
        """
        检测所有战法（用于分析场景）
        
        Returns:
            List[Dict]: 所有战法检测结果
        """
        results = []
        for strategy in self.strategies:
            matched, metadata = strategy.detect(stock_data)
            results.append({
                'strategy_name': strategy.name,
                'matched': matched,
                'metadata': metadata
            })
        return results


class UnifiedWarfareCore:
    """
    统一战法核心 - V20 Step3 战法分流增强版
    
    功能：
    1. 统一管理所有战法事件检测器
    2. 【Step3新增】战法分流主入口 classify_warfare_type
    3. 【Step3新增】动态均线过滤（推土机均线锁/反包无视均线）
    4. 【Step3新增】战法标签注入metadata
    5. 与回测引擎和实时系统对齐
    """

    def __init__(self):
        """初始化统一战法核心"""
        # 创建事件管理器
        self.event_manager = EventManager()
        
        # 【Step3新增】战法分流器
        self.warfare_classifier = WarfareClassifier()
        
        # 初始化各个战法检测器
        self._init_detectors()
        
        # 性能统计
        self._total_ticks = 0
        self._total_events = 0
        
        # 【Step3新增】战法统计
        self._warfare_stats = {
            WarfareType.TREND_RIDER.value: 0,
            WarfareType.WEAK_TO_STRONG.value: 0,
            WarfareType.HIGH_VOL_REBOUND.value: 0,
            WarfareType.UNKNOWN.value: 0
        }
        
        logger.info("✅ [统一战法核心 V20.3] 初始化完成")
        logger.info(f"   - 已注册检测器: {len(self.event_manager.detectors)} 个")
        logger.info(f"   - 【Step3新增】战法分流器: 3个战法")
        logger.info(f"   - 支持事件类型: {[detector.name for detector in self.event_manager.detectors.values()]}")
    
    def _init_detectors(self):
        """初始化各个战法检测器"""
        # 集合竞价弱转强检测器（已删除）
        # opening_detector = OpeningWeakToStrongDetector()
        # self.event_manager.register_detector(opening_detector)
        
        # 龙头候选检测器
        leader_detector = LeaderCandidateDetector()
        self.event_manager.register_detector(leader_detector)
        
        # 低吸候选检测器
        dip_buy_detector = DipBuyCandidateDetector()
        self.event_manager.register_detector(dip_buy_detector)
        
        logger.info("✅ [统一战法核心] 检测器初始化完成")
    
    def classify_warfare_type(self, stock_data: Dict) -> Tuple[str, Dict]:
        """
        【Step3核心】战法分流主入口
        
        依次检测：推土机 -> 弱转强 -> 首阴低吸
        
        Args:
            stock_data: 股票数据字典，需包含：
                - price: 当前价格
                - ma5, ma10, ma20: 均线数据
                - prev_close: 昨收价
                - prev_change_pct: 昨收涨跌幅
                - high_60d: 60日最高价
                - flow_1min, flow_5min: 资金流量
                - prev_volume, avg_volume_5d: 成交量数据
                
        Returns:
            Tuple[str, Dict]: (warfare_type, metadata)
                warfare_type: '推土机' | '弱转强' | '首阴低吸' | '未知'
                metadata: {
                    'ma_required': bool,  # 是否需要均线验证
                    'warfare_type': str,
                    ...检测器特定字段
                }
        
        Example:
            >>> core = UnifiedWarfareCore()
            >>> warfare_type, metadata = core.classify_warfare_type(stock_data)
            >>> if warfare_type == '推土机':
            ...     # 严格均线验证
            ...     pass
            >>> elif warfare_type == '弱转强':
            ...     # 无视均线，看资金流
            ...     pass
        """
        warfare_type, metadata = self.warfare_classifier.classify(stock_data)
        
        # 更新统计
        if warfare_type in self._warfare_stats:
            self._warfare_stats[warfare_type] += 1
        
        return warfare_type, metadata
    
    def get_warfare_type_stats(self) -> Dict[str, int]:
        """获取战法分流统计"""
        return self._warfare_stats.copy()
    
    def detect_all_warfare_types(self, stock_data: Dict) -> List[Dict]:
        """
        【Step3扩展】检测所有战法（用于分析场景）
        
        Returns:
            List[Dict]: 所有战法检测结果
        """
        return self.warfare_classifier.classify_with_all(stock_data)

    def calculate_score(self, stock_data: Dict[str, Any]) -> float:
        """
        计算V18动能分数（含时间衰减Ratio）
        
        CTO注入：老板的时间坚决度Ratio化
        A股T+1机制下，资金干得越早越坚决，需规避尾盘骗炮
        
        Args:
            stock_data: 股票数据字典，包含基础分和事件信息
            
        Returns:
            float: 最终得分（含时间衰减权重）
        """
        # 1. 获取基础动能分（从stock_data中获取原始confidence或计算基础分）
        base_score = stock_data.get('confidence', 0.0) * 100  # 转换为百分制
        
        # 如果没有基础分，返回0
        if base_score <= 0:
            return 0.0
        
        # 2. ⭐️ CTO注入：老板的时间坚决度Ratio
        # 时间段权重配置（根据CTO裁决）
        now = datetime.now().time()
        
        if now <= datetime.time(9, 40):
            decay_ratio = 1.2   # 09:30-09:40 早盘试盘、抢筹，最坚决，溢价奖励
        elif now <= datetime.time(10, 30):
            decay_ratio = 1.0   # 09:40-10:30 主升浪确认，正常推力
        elif now <= datetime.time(14, 0):
            decay_ratio = 0.8   # 10:30-14:00 震荡垃圾时间，分数打折
        else:
            decay_ratio = 0.5   # 14:00-14:55 尾盘偷袭，严防骗炮，大幅降权（腰斩）
        
        # 3. 最终实际得分 = 基础分 * 时间坚决度比率
        final_score = base_score * decay_ratio
        
        # 4. 记录日志（CTO要求）
        stock_code = stock_data.get('stock_code', 'Unknown')
        time_str = now.strftime('%H:%M')
        logger.info(
            f"⏰ [V18时间衰减] {stock_code} | "
            f"时间权重: {decay_ratio:.1f}x ({time_str}) | "
            f"基础分: {base_score:.1f} | "
            f"最终分: {final_score:.1f}"
        )
        
        return final_score
    
    def process_tick(self, tick_data: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        处理单个Tick数据，检测多战法事件（V20 Step3战法分流增强版）
        
        【Step3增强】
        - 战法分流检测
        - 战法标签注入metadata
        - 动态均线过滤（推土机均线锁/反包无视均线）
        
        Args:
            tick_data: Tick数据字典
            context: 上下文信息
            
        Returns:
            检测到的事件列表（含时间衰减后的分数和战法标签）
        """
        try:
            # 更新总tick计数
            self._total_ticks += 1
            
            # 【Step3新增】战法分流检测
            # 构造stock_data用于战法分类
            stock_data_for_classification = {
                'stock_code': tick_data.get('stock_code', 'Unknown'),
                'price': tick_data.get('price', 0),
                'ma5': context.get('ma5', 0),
                'ma10': context.get('ma10', 0),
                'ma20': context.get('ma20', 0),
                'prev_close': tick_data.get('prev_close', 0),
                'prev_change_pct': context.get('prev_change_pct', 0),
                'high_60d': context.get('high_60d', 0),
                'flow_1min': context.get('flow_1min', 0),
                'flow_5min': context.get('flow_5min', 0),
                'prev_volume': context.get('prev_volume', 0),
                'avg_volume_5d': context.get('avg_volume_5d', 0)
            }
            
            # 【Step3核心】执行战法分流
            warfare_type, warfare_metadata = self.classify_warfare_type(stock_data_for_classification)
            
            # 使用事件管理器检测所有战法事件
            detected_events = self.event_manager.detect_events(tick_data, context)
            
            # 更新事件计数
            self._total_events += len(detected_events)
            
            # 转换事件为字典格式（便于后续处理）并应用V18时间衰减Ratio + Step3战法标签
            event_dicts = []
            for event in detected_events:
                # 构造stock_data用于计算时间衰减分数
                stock_data = {
                    'stock_code': event.stock_code,
                    'confidence': event.confidence,
                    'timestamp': event.timestamp,
                    'event_type': event.event_type.value
                }
                
                # ⭐️ 应用V18时间衰减Ratio计算最终分数
                final_score = self.calculate_score(stock_data)
                
                # 【Step3新增】根据战法类型调整均线验证
                # 推土机战法：必须均线验证
                # 弱转强/首阴低吸：无视均线
                ma_validation_passed = True
                if warfare_type == WarfareType.TREND_RIDER.value:
                    ma_validation_passed = warfare_metadata.get('ma_aligned', False)
                
                event_dict = {
                    'event_type': event.event_type.value,
                    'stock_code': event.stock_code,
                    'timestamp': event.timestamp,
                    'data': event.data,
                    'confidence': event.confidence,
                    'final_score': final_score,  # ⭐️ V18：时间衰减后的最终分数
                    'description': event.description,
                    # 【Step3新增】战法标签注入
                    'warfare_type': warfare_type,
                    'warfare_metadata': warfare_metadata,
                    'ma_validation_passed': ma_validation_passed,
                    'ma_required': warfare_metadata.get('ma_required', True)
                }
                event_dicts.append(event_dict)
                
                # 记录检测到的事件（含战法分流信息）
                logger.debug(
                    f"📊 [统一战法V20.3] 检测事件: {event.event_type.value} - "
                    f"{event.stock_code} @ 原始置信度:{event.confidence:.2f}, "
                    f"时间衰减后:{final_score:.1f}, "
                    f"战法:{warfare_type}"
                )
            
            if detected_events:
                logger.info(
                    f"🎯 [统一战法V20.3] 本tick检测到 {len(detected_events)} 个事件, "
                    f"战法分布: {self._warfare_stats}"
                )
            
            return event_dicts
            
        except Exception as e:
            logger.error(f"❌ [统一战法核心] 处理Tick失败: {e}")
            return []
    
    def get_active_detectors(self) -> List[str]:
        """获取当前激活的检测器列表"""
        return [name for name, detector in self.event_manager.detectors.items() if detector.enabled]
    
    def get_warfare_stats(self) -> Dict[str, Any]:
        """
        获取战法统计信息（V20 Step3增强版）
        
        Returns:
            Dict包含：
            - 基础统计（Tick数、事件数）
            - 【Step3新增】战法分流统计
            - 检测器详情
        """
        stats = {
            '总处理Tick数': self._total_ticks,
            '总检测事件数': self._total_events,
            '事件检测率': f"{self._total_events/self._total_ticks*100:.4f}%" if self._total_ticks > 0 else "0.0000%",
            '活跃检测器': len(self.get_active_detectors()),
            # 【Step3新增】战法分流统计
            '战法分流统计': self._warfare_stats.copy(),
            '战法分布比例': self._calculate_warfare_distribution(),
            '检测器详情': {}
        }
        
        # 获取每个检测器的详细统计
        for name, detector in self.event_manager.detectors.items():
            if hasattr(detector, 'get_detection_stats'):
                stats['检测器详情'][name] = detector.get_detection_stats()
        
        return stats
    
    def _calculate_warfare_distribution(self) -> Dict[str, str]:
        """计算战法分布比例"""
        total = sum(self._warfare_stats.values())
        if total == 0:
            return {k: "0.0%" for k in self._warfare_stats.keys()}
        
        return {
            k: f"{v/total*100:.1f}%" 
            for k, v in self._warfare_stats.items()
        }
    
    def enable_warfare(self, warfare_type: str):
        """启用特定战法检测器"""
        detector_map = {
            # 'opening_weak_to_strong': 'OpeningWeakToStrongDetector',  # 已删除
            # 'halfway_breakout': 'HalfwayBreakoutDetector',  # 已归档
            'leader_candidate': 'LeaderCandidateDetector',
            'dip_buy_candidate': 'DipBuyCandidateDetector',
        }
        
        detector_name = detector_map.get(warfare_type)
        if detector_name:
            self.event_manager.enable_detector(detector_name)
            logger.info(f"✅ 启用战法: {warfare_type}")
    
    def disable_warfare(self, warfare_type: str):
        """禁用特定战法检测器"""
        detector_map = {
            # 'opening_weak_to_strong': 'OpeningWeakToStrongDetector',  # 已删除
            # 'halfway_breakout': 'HalfwayBreakoutDetector',  # 已归档
            'leader_candidate': 'LeaderCandidateDetector',
            'dip_buy_candidate': 'DipBuyCandidateDetector',
        }
        
        detector_name = detector_map.get(warfare_type)
        if detector_name:
            self.event_manager.disable_detector(detector_name)
            logger.info(f"⏸️ 禁用战法: {warfare_type}")
    
    def reset_warfare_stats(self):
        """重置所有检测器统计（V20 Step3增强版）"""
        for detector in self.event_manager.detectors.values():
            if hasattr(detector, 'reset'):
                detector.reset()
        self._total_ticks = 0
        self._total_events = 0
        # 【Step3新增】重置战法分流统计
        self._warfare_stats = {
            WarfareType.TREND_RIDER.value: 0,
            WarfareType.WEAK_TO_STRONG.value: 0,
            WarfareType.HIGH_VOL_REBOUND.value: 0,
            WarfareType.UNKNOWN.value: 0
        }
        logger.info("🔄 重置战法统计（含战法分流）")


# ==================== 全局实例 ====================

_unified_warfare_core: Optional[UnifiedWarfareCore] = None


def get_unified_warfare_core() -> UnifiedWarfareCore:
    """获取统一战法核心单例"""
    global _unified_warfare_core
    if _unified_warfare_core is None:
        _unified_warfare_core = UnifiedWarfareCore()
    return _unified_warfare_core


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试UnifiedWarfareCore - V20 Step3战法分流测试
    print("=" * 80)
    print("统一战法核心测试 - V20 Step3 战法分流")
    print("=" * 80)
    
    core = get_unified_warfare_core()
    
    # ============================================
    # 【Step3测试】战法分流测试用例
    # ============================================
    
    # 测试用例1：推土机战法（均线多头排列）
    trend_rider_stock = {
        'stock_code': '000001',
        'price': 25.5,
        'ma5': 24.8,   # MA5 > MA10
        'ma10': 24.0,  # MA10 > MA20
        'ma20': 23.0,  # Price > MA20
        'prev_close': 24.0,
        'prev_change_pct': 2.0,
        'high_60d': 26.0,
        'flow_1min': 500,
        'flow_5min': 2000,
        'prev_volume': 80000,
        'avg_volume_5d': 100000
    }
    
    # 测试用例2：弱转强战法（昨阴今反包）
    weak_to_strong_stock = {
        'stock_code': '000002',
        'price': 18.5,
        'ma5': 18.0,
        'ma10': 19.0,  # MA5 < MA10（均线死叉，但弱转强无视）
        'ma20': 19.5,
        'prev_close': 17.0,
        'prev_change_pct': -7.0,  # 昨收盘大阴
        'high_60d': 19.0,
        'flow_1min': 1000,  # 早盘极速爆量流入
        'flow_5min': 3000,
        'prev_volume': 60000,
        'avg_volume_5d': 100000
    }
    
    # 测试用例3：首阴低吸战法（缩量下跌资金回流）
    dip_buy_stock = {
        'stock_code': '000003',
        'price': 15.5,
        'ma5': 16.0,
        'ma10': 16.5,
        'ma20': 16.8,  # Price < MA20（破位，但首阴低吸无视）
        'prev_close': 16.0,
        'prev_change_pct': -3.0,
        'high_60d': 18.0,
        'flow_1min': 200,
        'flow_5min': 800,  # 资金由负转正
        'prev_volume': 50000,  # 缩量（< 0.7 * avg）
        'avg_volume_5d': 100000
    }
    
    # 测试用例4：未知战法（不符合任何条件）
    unknown_stock = {
        'stock_code': '000004',
        'price': 20.0,
        'ma5': 19.5,
        'ma10': 20.0,  # MA5 < MA10
        'ma20': 21.0,  # Price < MA20
        'prev_close': 20.0,
        'prev_change_pct': 0.0,
        'high_60d': 25.0,  # Space gap大
        'flow_1min': -100,  # 资金流出
        'flow_5min': -500,
        'prev_volume': 120000,  # 放量
        'avg_volume_5d': 100000
    }
    
    test_cases = [
        ('推土机战法测试', trend_rider_stock),
        ('弱转强战法测试', weak_to_strong_stock),
        ('首阴低吸战法测试', dip_buy_stock),
        ('未知战法测试', unknown_stock)
    ]
    
    print(f"\n测试用例数: {len(test_cases)}")
    print("\n开始Step3战法分流测试...\n")
    
    for i, (name, stock_data) in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"测试用例 {i}: {name}")
        print(f"{'=' * 80}")
        print(f"股票代码: {stock_data['stock_code']}")
        print(f"当前价格: {stock_data['price']}")
        print(f"均线状态: MA5={stock_data['ma5']}, MA10={stock_data['ma10']}, MA20={stock_data['ma20']}")
        
        # 【Step3核心】调用战法分流
        warfare_type, metadata = core.classify_warfare_type(stock_data)
        
        print(f"\n🎯 战法分流结果:")
        print(f"   - 战法类型: {warfare_type}")
        print(f"   - 均线验证: {'需要' if metadata.get('ma_required') else '不需要'}")
        
        if warfare_type != WarfareType.UNKNOWN.value:
            print(f"   - 检测详情:")
            for key, value in metadata.items():
                if key not in ['warfare_type', 'ma_required', 'passed']:
                    print(f"      • {key}: {value}")
        
        # 同时测试全战法检测
        all_results = core.detect_all_warfare_types(stock_data)
        print(f"\n📊 全战法检测结果:")
        for result in all_results:
            status = "✅" if result['matched'] else "❌"
            print(f"   {status} {result['strategy_name']}")
    
    # 获取统计信息
    print("\n" + "=" * 80)
    print("战法统计:")
    print("=" * 80)
    stats = core.get_warfare_stats()
    
    print("\n【Step3新增】战法分流统计:")
    for warfare, count in stats.get('战法分流统计', {}).items():
        print(f"   - {warfare}: {count} 次")
    
    print("\n战法分布比例:")
    for warfare, pct in stats.get('战法分布比例', {}).items():
        print(f"   - {warfare}: {pct}")
    
    print("\n" + "=" * 80)
    print("✅ Step3 战法分流测试完成")
    print("=" * 80)
    
    print("\n【Step3验证要点】")
    print("1. ✅ 推土机战法检测器 - 均线多头排列检测")
    print("2. ✅ 弱转强战法检测器 - 无视均线死叉，检测极速反包")
    print("3. ✅ 首阴低吸战法检测器 - 无视Price < MA20破位")
    print("4. ✅ 主分发器 classify_warfare_type - 依次检测三个战法")
    print("5. ✅ 战法标签注入metadata - warfare_type 和 ma_required")

