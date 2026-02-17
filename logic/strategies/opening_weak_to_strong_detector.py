#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集合竞价弱转强事件检测器 (Opening Weak-to-Strong Event Detector)

根据CTO指导意见，实现统一的多战法事件检测架构。
该检测器专门负责检测OPENING_WEAK_TO_STRONG事件，使用auction_strength_validator.py中的核心逻辑。

核心功能：
1. 检测竞价弱转强事件（OPENING_WEAK_TO_STRONG）
2. 集成AuctionStrengthValidator的强弱判断逻辑
3. 与统一的EventDriven架构对齐

设计原则：
1. 继承BaseEventDetector基类
2. 使用统一的EventType.OPENING_WEAK_TO_STRONG
3. 与auction_strength_validator.py共享核心逻辑
4. 遵循V12.1.0规范

验收标准：
- 能够正确检测竞价弱转强事件
- 与现有EventDriven系统兼容
- 性能满足实时检测要求
- 代码符合项目规范

Author: iFlow CLI
Version: V12.1.0
Date: 2026-02-17
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from logic.strategies.event_detector import BaseEventDetector, TradingEvent, EventType
from logic.strategies.auction_strength_validator import get_auction_strength_validator
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class OpeningWeakToStrongDetector(BaseEventDetector):
    """
    集合竞价弱转强事件检测器
    
    功能：
    1. 检测竞价弱转强事件
    2. 集成AuctionStrengthValidator逻辑
    3. 生成标准化的TradingEvent
    4. 提供详细的检测日志
    """

    def __init__(self):
        """初始化竞价弱转强检测器"""
        super().__init__(name="OpeningWeakToStrongDetector")
        
        # 获取竞价强弱校验器
        self.validator = get_auction_strength_validator()
        
        # 性能统计
        self._detection_count = 0
        self._success_count = 0
        
        logger.info("✅ [竞价弱转强检测器] 初始化完成")
        logger.info(f"   - 使用校验器: {type(self.validator).__name__}")
    
    def detect(self, tick_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[TradingEvent]:
        """
        检测竞价弱转强事件
        
        Args:
            tick_data: Tick数据字典
            context: 上下文信息（包含竞价数据）
        
        Returns:
            如果检测到竞价弱转强事件，返回TradingEvent；否则返回None
        """
        try:
            # 更新检测计数
            self._detection_count += 1
            
            # 提取关键信息
            stock_code = tick_data.get('stock_code', '')
            current_time = tick_data.get('datetime', datetime.now())
            
            # 检查是否是竞价时间（9:25-9:30）
            if not self._is_auction_time(current_time):
                return None
            
            # 获取竞价数据
            auction_data = self._extract_auction_data(tick_data, context)
            if not auction_data:
                return None
            
            # 使用AuctionStrengthValidator进行验证
            validation_result = self.validator.validate_auction(stock_code, auction_data)
            
            # 根据验证结果判断是否生成事件
            action = validation_result.get('action', 'REJECT')
            confidence = validation_result.get('confidence', 0.0)
            
            # 只有买入级别的信号才生成事件
            if action in ['STRONG_BUY', 'BUY']:
                event = TradingEvent(
                    event_type=EventType.OPENING_WEAK_TO_STRONG,
                    stock_code=stock_code,
                    timestamp=current_time,
                    data={
                        'auction_data': auction_data,
                        'validation_result': validation_result,
                        'action': action,
                        'confidence': confidence
                    },
                    confidence=confidence,
                    description=self._build_description(stock_code, validation_result)
                )
                
                self._success_count += 1
                logger.info(f"🎯 [竞价弱转强] 检测到事件: {stock_code} - {event.description} (置信度: {confidence:.2f})")
                
                return event
            else:
                # 记录未触发事件的原因（用于调试）
                reason = validation_result.get('reason', '不符合条件')
                logger.debug(f"❌ [竞价弱转强] 未触发: {stock_code} - {reason}")
                
        except Exception as e:
            logger.error(f"❌ [竞价弱转强检测器] 检测失败: {stock_code}, 错误: {e}")
        
        return None
    
    def _is_auction_time(self, dt: datetime) -> bool:
        """
        判断是否是竞价时间
        
        Args:
            dt: 时间对象
        
        Returns:
            bool: 是否是竞价时间
        """
        # 集合竞价时间通常在9:25-9:30
        hour = dt.hour
        minute = dt.minute
        
        if hour == 9:
            if 25 <= minute <= 30:
                return True
        elif hour == 14 and minute == 57:
            # 尾盘竞价时间14:57-15:00 (可选)
            return True
        
        return False
    
    def _extract_auction_data(self, tick_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从tick数据和上下文中提取竞价数据
        
        Args:
            tick_data: Tick数据
            context: 上下文信息
        
        Returns:
            dict: 竞价数据，如果无法提取则返回None
        """
        try:
            # 从tick_data中提取基本信息
            open_price = tick_data.get('open', 0)
            prev_close = tick_data.get('prev_close', 0)
            high_price = tick_data.get('high', 0)
            low_price = tick_data.get('low', 0)
            
            # 从上下文获取量比信息
            volume_ratio = context.get('auction_volume_ratio', 0)
            
            # 如果没有量比信息，尝试从tick_data计算
            if volume_ratio <= 0:
                # 使用前几日平均成交量作为基准
                avg_volume = context.get('avg_volume_5d', 0)
                current_volume = tick_data.get('volume', 0)
                if avg_volume > 0:
                    volume_ratio = current_volume / avg_volume
            
            # 检查涨停状态
            is_limit_up = tick_data.get('is_limit_up', False)
            
            # 构建竞价数据
            auction_data = {
                'open_price': open_price,
                'prev_close': prev_close,
                'volume_ratio': volume_ratio,
                'amount': tick_data.get('amount', 0),
                'high_price': high_price,
                'low_price': low_price,
                'is_limit_up': is_limit_up
            }
            
            # 验证必要字段
            if prev_close <= 0:
                logger.debug(f"⚠️ [竞价弱转强] 昨收价无效: {tick_data.get('stock_code', 'UNKNOWN')}")
                return None
            
            return auction_data
            
        except Exception as e:
            logger.error(f"❌ [竞价弱转强] 提取竞价数据失败: {e}")
            return None
    
    def _build_description(self, stock_code: str, validation_result: Dict[str, Any]) -> str:
        """
        构建事件描述
        
        Args:
            stock_code: 股票代码
            validation_result: 验证结果
        
        Returns:
            str: 事件描述
        """
        try:
            details = validation_result.get('details', {})
            open_gap_pct = details.get('open_gap_pct', 0) * 100
            volume_ratio = details.get('volume_ratio', 0)
            is_focus_stock = details.get('is_focus_stock', False)
            
            description_parts = ["竞价弱转强"]
            
            if is_focus_stock:
                description_parts.append("焦点股")
            else:
                description_parts.append("首板股")
            
            description_parts.append(f"：高开{open_gap_pct:.2f}%，量比{volume_ratio:.2f}")
            
            return "".join(description_parts)
            
        except Exception as e:
            logger.error(f"❌ [竞价弱转强] 构建描述失败: {e}")
            return f"竞价弱转强：{stock_code}"
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """
        获取检测统计信息
        
        Returns:
            dict: 检测统计信息
        """
        success_rate = self._success_count / self._detection_count if self._detection_count > 0 else 0
        return {
            '总检测次数': self._detection_count,
            '成功检测次数': self._success_count,
            '成功检测率': f"{success_rate:.2%}",
            '检测器状态': '启用' if self.enabled else '禁用'
        }


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试OpeningWeakToStrongDetector
    print("=" * 80)
    print("集合竞价弱转强事件检测器测试")
    print("=" * 80)
    
    detector = OpeningWeakToStrongDetector()
    
    # 模拟tick数据 - 焦点股竞价超预期
    test_tick_data_focus = {
        'stock_code': '000001',
        'datetime': datetime(2026, 2, 17, 9, 28, 0),
        'open': 16.5,
        'prev_close': 15.0,
        'high': 16.8,
        'low': 16.2,
        'volume': 150000000,  # 成交量
        'amount': 2500000000,  # 成交额
        'is_limit_up': False
    }
    
    # 模拟上下文信息
    test_context = {
        'auction_volume_ratio': 2.5,  # 竞价量比
        'avg_volume_5d': 60000000  # 前5日平均成交量
    }
    
    # 测试用例
    test_cases = [
        {
            'name': '焦点股超预期',
            'tick_data': test_tick_data_focus,
            'context': test_context
        }
    ]
    
    print(f"\n测试用例数: {len(test_cases)}")
    print("\n开始测试...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"测试用例 {i}: {test_case['name']}")
        print(f"{'=' * 80}")
        
        event = detector.detect(test_case['tick_data'], test_case['context'])
        
        print(f"\n股票代码: {test_case['tick_data']['stock_code']}")
        print(f"开盘价: {test_case['tick_data']['open']:.2f}")
        print(f"昨收价: {test_case['tick_data']['prev_close']:.2f}")
        print(f"量比: {test_case['context']['auction_volume_ratio']:.2f}")
        
        if event:
            print(f"\n✅ 检测到事件:")
            print(f"   - 事件类型: {event.event_type.value}")
            print(f"   - 股票代码: {event.stock_code}")
            print(f"   - 描述: {event.description}")
            print(f"   - 置信度: {event.confidence:.2f}")
            print(f"   - 数据: {event.data}")
        else:
            print(f"\n❌ 未检测到事件")
    
    # 获取统计信息
    print("\n" + "=" * 80)
    print("检测统计:")
    print("=" * 80)
    stats = detector.get_detection_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ 测试完成")
    print("=" * 80)
