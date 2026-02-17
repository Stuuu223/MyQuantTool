#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
半路平台突破事件检测器 (Halfway Breakout Event Detector)

根据CTO指导意见，实现统一的多战法事件检测架构。
该检测器专门负责检测HALFWAY_BREAKOUT事件，使用halfway_core.py中的核心逻辑。

核心功能：
1. 检测半路平台突破事件（HALFWAY_BREAKOUT）
2. 集成halfway_core.py的平台突破逻辑
3. 与统一的EventDriven架构对齐

设计原则：
1. 继承BaseEventDetector基类
2. 使用统一的EventType.HALFWAY_BREAKOUT
3. 与halfway_core.py共享核心逻辑
4. 遵循V12.1.0规范

验收标准：
- 能够正确检测半路平台突破事件
- 与现有EventDriven系统兼容
- 性能满足实时检测要求
- 代码符合项目规范

Author: iFlow CLI
Version: V12.1.0
Date: 2026-02-17
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np

from logic.strategies.event_detector import BaseEventDetector, TradingEvent, EventType
from logic.strategies.halfway_core import evaluate_halfway_state
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class HalfwayBreakoutDetector(BaseEventDetector):
    """
    半路平台突破事件检测器
    
    功能：
    1. 检测半路平台突破事件
    2. 集成halfway_core的平台突破判断逻辑
    3. 生成标准化的TradingEvent
    4. 提供详细的检测日志
    """

    def __init__(self):
        """初始化半路突破检测器"""
        super().__init__(name="HalfwayBreakoutDetector")
        
        # 性能统计
        self._detection_count = 0
        self._success_count = 0
        
        logger.info("✅ [半路突破检测器] 初始化完成")
    
    def detect(self, tick_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[TradingEvent]:
        """
        检测半路平台突破事件
        
        Args:
            tick_data: Tick数据字典
            context: 上下文信息（包含历史价格、成交量、均线等）
        
        Returns:
            如果检测到半路突破事件，返回TradingEvent；否则返回None
        """
        try:
            # 更新检测计数
            self._detection_count += 1
            
            # 提取关键信息
            stock_code = tick_data.get('stock_code', '')
            current_time = tick_data.get('datetime', datetime.now())
            current_price = tick_data.get('price', 0)
            volume = tick_data.get('volume', 0)
            
            # 获取历史数据（用于平台识别）
            price_history = context.get('price_history', [])
            volume_history = context.get('volume_history', [])
            ma5 = context.get('ma5', 0)
            ma20 = context.get('ma20', 0)
            
            if len(price_history) < 20:
                return None  # 数据不足
            
            # 使用halfway_core的逻辑进行平台突破评估
            params = {
                'volatility_threshold': 0.03,
                'volume_surge': 1.5,
                'breakout_strength': 0.01,
                'window_minutes': 30,
                'min_history_points': 20
            }
            
            halfway_result = evaluate_halfway_state(
                prices=price_history,
                volumes=volume_history,
                params=params
            )
            
            # 检查是否符合半路突破条件
            is_breakout = halfway_result.get('is_signal', False)
            volatility = halfway_result.get('factors', {}).get('volatility', 1.0)
            volume_surge = halfway_result.get('factors', {}).get('volume_surge', 1.0)
            breakout_strength = halfway_result.get('factors', {}).get('breakout_strength', 0.0)
            
            # 计算综合置信度（基于多个因子）
            # 突破强度越大，置信度越高；波动率越低，置信度越高；量能放大越大，置信度越高
            confidence = min(1.0, breakout_strength * 10 + (volume_surge - 1.0) * 0.1 + (0.05 - volatility) * 2)
            confidence = max(0.0, confidence)  # 确保置信度不小于0
            
            # 只有高置信度的突破才触发事件
            # 使用更合理的阈值，符合半路突破的实际场景
            if is_breakout and confidence >= 0.3 and breakout_strength >= 0.01:
                event = TradingEvent(
                    event_type=EventType.HALFWAY_BREAKOUT,
                    stock_code=stock_code,
                    timestamp=current_time,
                    data={
                        'halfway_result': halfway_result,
                        'current_price': current_price,
                        'volume': volume,
                        'ma5': ma5,
                        'ma20': ma20,
                        'confidence': confidence
                    },
                    confidence=confidence,
                    description=self._build_description(stock_code, halfway_result, current_price)
                )
                
                self._success_count += 1
                logger.info(f"🎯 [半路突破] 检测到事件: {stock_code} - {event.description} (置信度: {confidence:.2f})")
                
                return event
            else:
                # 记录未触发事件的原因（用于调试）
                reason = halfway_result.get('extra_info', {}).get('reason', '不符合条件')
                platform_status = '未知'  # 旧的逻辑不适用新函数
                logger.debug(f"❌ [半路突破] 未触发: {stock_code} - {reason}, 平台状态: {platform_status}")
                
        except Exception as e:
            logger.error(f"❌ [半路突破检测器] 检测失败: {stock_code}, 错误: {e}")
        
        return None
    
    def _build_description(self, stock_code: str, halfway_result: Dict[str, Any], current_price: float) -> str:
        """
        构建事件描述
        
        Args:
            stock_code: 股票代码
            halfway_result: 半路评估结果
            current_price: 当前价格
        
        Returns:
            str: 事件描述
        """
        try:
            # 从结果中获取真实因子值
            breakout_strength = halfway_result.get('factors', {}).get('breakout_strength', 0)
            platform_volatility = halfway_result.get('factors', {}).get('volatility', 0)
            volume_surge = halfway_result.get('factors', {}).get('volume_surge', 0)
            
            # 根据突破强度判断平台状态
            if breakout_strength >= 0.03:
                platform_status = '强势突破'
            elif breakout_strength >= 0.01:
                platform_status = '温和突破'
            else:
                platform_status = '突破微弱'
            
            description_parts = [
                "半路突破",
                f"：{platform_status}，突破强度{breakout_strength:.4f}，波动率{platform_volatility:.4f}，量比{volume_surge:.2f}，价格{current_price:.2f}"
            ]
            
            return "".join(description_parts)
            
        except Exception as e:
            logger.error(f"❌ [半路突破] 构建描述失败: {e}")
            return f"半路突破：{stock_code} - 价格{current_price:.2f}"
    
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
    # 测试HalfwayBreakoutDetector
    print("=" * 80)
    print("半路平台突破事件检测器测试")
    print("=" * 80)
    
    detector = HalfwayBreakoutDetector()
    
    # 模拟tick数据 - 半路突破
    test_tick_data = {
        'stock_code': '300750',
        'datetime': datetime(2026, 2, 17, 10, 15, 0),
        'price': 205.0,
        'volume': 1200000
    }
    
    # 模拟历史价格数据 - 构造一个平台突破场景
    import random
    base_price = 200.0
    # 模拟平台期（价格在小范围内波动）
    platform_prices = [base_price + random.uniform(-0.5, 0.5) for _ in range(15)]
    # 突破期（价格向上突破）
    breakout_prices = [201.0, 202.5, 204.0, 205.0]  # 突破到205
    all_prices = platform_prices + breakout_prices
    
    # 模拟成交量数据
    platform_volumes = [800000 + random.randint(-100000, 100000) for _ in range(15)]
    breakout_volumes = [1000000, 1100000, 1150000, 1200000]  # 放量突破
    all_volumes = platform_volumes + breakout_volumes
    
    # 模拟上下文信息
    test_context = {
        'price_history': all_prices,
        'volume_history': all_volumes,
        'ma5': 203.0,
        'ma20': 201.5,
        'avg_volume_5d': 950000
    }
    
    # 测试用例
    test_cases = [
        {
            'name': '平台突破',
            'tick_data': test_tick_data,
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
        print(f"当前价格: {test_case['tick_data']['price']:.2f}")
        print(f"历史价格长度: {len(test_case['context']['price_history'])}")
        print(f"均线(MA5/MA20): {test_case['context']['ma5']:.2f}/{test_case['context']['ma20']:.2f}")
        
        if event:
            print(f"\n✅ 检测到事件:")
            print(f"   - 事件类型: {event.event_type.value}")
            print(f"   - 股票代码: {event.stock_code}")
            print(f"   - 描述: {event.description}")
            print(f"   - 置信度: {event.confidence:.2f}")
            print(f"   - 数据: {list(event.data.keys())}")
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
