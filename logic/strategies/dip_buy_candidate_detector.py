#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
低吸候选事件检测器 (Dip Buy Candidate Event Detector)

根据CTO指导意见，实现统一的多战法事件检测架构。
该检测器专门负责检测DIP_BUY_CANDIDATE事件，识别低吸机会。

核心功能：
1. 检测低吸候选事件（DIP_BUY_CANDIDATE）
2. 识别股价回调和支撑位机会
3. 与统一的EventDriven架构对齐

设计原则：
1. 继承BaseEventDetector基类
2. 使用统一的EventType.DIP_BUY_CANDIDATE
3. 遵循V12.1.0规范

验收标准：
- 能够正确检测低吸候选事件
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
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class DipBuyCandidateDetector(BaseEventDetector):
    """
    低吸候选事件检测器
    
    功能：
    1. 检测低吸候选事件
    2. 识别股价回调和支撑机会
    3. 生成标准化的TradingEvent
    4. 提供详细的检测日志
    """

    # 低吸条件阈值
    MAX_DROP_PERCENT = -5.0      # 最大跌幅（负值）
    MIN_VOLUME_RATIO = 0.8       # 最小量比（缩量回调）
    RSI_OVERSOLD = 30            # RSI超卖阈值
    SUPPORT_NEARBY = 0.02        # 支撑位附近阈值（2%）
    HIGH_VOLATILITY = 0.05       # 高波动率阈值（5%）

    def __init__(self):
        """初始化低吸候选检测器"""
        super().__init__(name="DipBuyCandidateDetector")
        
        # 性能统计
        self._detection_count = 0
        self._success_count = 0
        
        logger.info("✅ [低吸候选检测器] 初始化完成")
        logger.info(f"   - 最大跌幅阈值: {self.MAX_DROP_PERCENT}%")
        logger.info(f"   - 量比阈值: ≥{self.MIN_VOLUME_RATIO}")
        logger.info(f"   - RSI超卖阈值: ≤{self.RSI_OVERSOLD}")
    
    def detect(self, tick_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[TradingEvent]:
        """
        检测低吸候选事件
        
        Args:
            tick_data: Tick数据字典
            context: 上下文信息（包含历史价格、技术指标等）
        
        Returns:
            如果检测到低吸候选事件，返回TradingEvent；否则返回None
        """
        try:
            # 更新检测计数
            self._detection_count += 1
            
            # 提取关键信息
            stock_code = tick_data.get('stock_code', '')
            current_time = tick_data.get('datetime', datetime.now())
            current_price = tick_data.get('price', 0)
            volume = tick_data.get('volume', 0)
            
            # 获取历史数据
            price_history = context.get('price_history', [])
            volume_history = context.get('volume_history', [])
            rsi = context.get('rsi', 50)  # 默认RSI为50
            ma_support = context.get('ma_support', [20, 30, 60])  # 均线支撑
            
            if len(price_history) < 20:
                return None  # 数据不足
            
            # 计算当前跌幅
            recent_high = max(price_history[-10:]) if len(price_history) >= 10 else price_history[-1]
            prev_close = tick_data.get('prev_close', 0)
            
            if prev_close > 0:
                change_pct = (current_price - prev_close) / prev_close * 100
            else:
                change_pct = 0
            
            # 检查是否满足低吸基本条件
            if not self._is_dip_buy_candidate(
                change_pct, 
                price_history, 
                volume_history, 
                rsi, 
                current_price
            ):
                return None
            
            # 评估低吸置信度
            confidence = self._calculate_dip_confidence(
                change_pct, 
                current_price, 
                price_history, 
                rsi, 
                ma_support
            )
            
            # 只有高置信度的低吸候选才触发事件
            if confidence >= 0.6:
                event = TradingEvent(
                    event_type=EventType.DIP_BUY_CANDIDATE,
                    stock_code=stock_code,
                    timestamp=current_time,
                    data={
                        'change_pct': change_pct,
                        'current_price': current_price,
                        'rsi': rsi,
                        'price_history': price_history[-20:],  # 最近20个价格
                        'volume': volume,
                        'confidence': confidence,
                        'ma_support': ma_support
                    },
                    confidence=confidence,
                    description=self._build_description(stock_code, change_pct, current_price, rsi)
                )
                
                self._success_count += 1
                logger.info(f"🎯 [低吸候选] 检测到事件: {stock_code} - {event.description} (置信度: {confidence:.2f})")
                
                return event
            else:
                # 记录未触发事件的原因（用于调试）
                logger.debug(f"❌ [低吸候选] 未触发: {stock_code} - 置信度不足 ({confidence:.2f})")
                
        except Exception as e:
            logger.error(f"❌ [低吸候选检测器] 检测失败: {stock_code}, 错误: {e}")
        
        return None
    
    def _is_dip_buy_candidate(
        self, 
        change_pct: float, 
        price_history: List[float], 
        volume_history: List[float], 
        rsi: float, 
        current_price: float
    ) -> bool:
        """
        判断是否为低吸候选股
        
        Args:
            change_pct: 涨跌幅
            price_history: 价格历史
            volume_history: 成交量历史
            rsi: RSI值
            current_price: 当前价格
        
        Returns:
            bool: 是否为低吸候选股
        """
        try:
            # 检查跌幅是否在合理范围内（不能跌太多，也不能不跌）
            is_moderate_drop = self.MAX_DROP_PERCENT <= change_pct <= -1.0
            
            # 检查是否缩量回调（成交量小于均价）
            if volume_history:
                avg_volume = np.mean(volume_history[-10:]) if len(volume_history) >= 10 else volume_history[-1]
                is_volume_decline = avg_volume > 0 and volume <= avg_volume * 1.2  # 允许小幅放量
            else:
                is_volume_decline = True  # 没有历史数据则跳过检查
            
            # 检查RSI是否超卖
            is_oversold = rsi <= self.RSI_OVERSOLD
            
            # 检查是否接近支撑位
            is_near_support = self._is_near_support(current_price, price_history)
            
            return is_moderate_drop and is_oversold and is_near_support
            
        except Exception as e:
            logger.debug(f"⚠️ [低吸候选] 条件检查失败: {e}")
            return False
    
    def _is_near_support(self, current_price: float, price_history: List[float]) -> bool:
        """
        检查当前价格是否接近支撑位
        
        Args:
            current_price: 当前价格
            price_history: 价格历史
        
        Returns:
            bool: 是否接近支撑位
        """
        try:
            if len(price_history) < 20:
                return False
            
            # 计算支撑位（使用最近20个价格的最低点）
            recent_low = min(price_history[-20:])
            
            # 如果当前价格接近近期低点（在2%范围内），认为是支撑附近
            price_near_support = abs(current_price - recent_low) / recent_low <= self.SUPPORT_NEARBY
            
            # 也可以考虑均线支撑
            ma_20 = np.mean(price_history[-20:])
            ma_near_support = abs(current_price - ma_20) / ma_20 <= self.SUPPORT_NEARBY
            
            return price_near_support or ma_near_support
            
        except Exception as e:
            logger.debug(f"⚠️ [低吸候选] 支撑位检查失败: {e}")
            return False
    
    def _calculate_dip_confidence(
        self, 
        change_pct: float, 
        current_price: float, 
        price_history: List[float], 
        rsi: float, 
        ma_support: List[int]
    ) -> float:
        """
        计算低吸置信度
        
        Args:
            change_pct: 涨跌幅
            current_price: 当前价格
            price_history: 价格历史
            rsi: RSI值
            ma_support: 均线支撑信息
        
        Returns:
            float: 置信度 (0-1)
        """
        try:
            # RSI超卖得分（RSI越低，得分越高）
            rsi_score = max(0.0, (self.RSI_OVERSOLD - rsi) / self.RSI_OVERSOLD)
            
            # 跌幅得分（跌幅在合适范围内的得分）
            if self.MAX_DROP_PERCENT <= change_pct <= -3.0:
                drop_score = 1.0  # 理想跌幅
            elif -3.0 < change_pct <= -1.0:
                drop_score = 0.7  # 合适跌幅
            else:
                drop_score = 0.3  # 跌幅不足或过大
            
            # 支撑位得分
            support_score = 1.0 if self._is_near_support(current_price, price_history) else 0.4
            
            # 综合置信度
            confidence = (rsi_score * 0.4 + drop_score * 0.3 + support_score * 0.3)
            
            return confidence
            
        except Exception as e:
            logger.error(f"❌ [低吸候选] 计算置信度失败: {e}")
            return 0.0
    
    def _build_description(
        self, 
        stock_code: str, 
        change_pct: float, 
        current_price: float, 
        rsi: float
    ) -> str:
        """
        构建事件描述
        
        Args:
            stock_code: 股票代码
            change_pct: 涨跌幅
            current_price: 当前价格
            rsi: RSI值
        
        Returns:
            str: 事件描述
        """
        try:
            description_parts = [
                "低吸候选",
                f"：跌幅{change_pct:.2f}%",
                f"，价格{current_price:.2f}",
                f"，RSI{rsi:.1f}"
            ]
            
            return "".join(description_parts)
            
        except Exception as e:
            logger.error(f"❌ [低吸候选] 构建描述失败: {e}")
            return f"低吸候选：{stock_code} - 跌幅{change_pct:.2f}%"
    
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
    # 测试DipBuyCandidateDetector
    print("=" * 80)
    print("低吸候选事件检测器测试")
    print("=" * 80)
    
    detector = DipBuyCandidateDetector()
    
    # 模拟价格历史 - 构造回调到支撑位的场景
    import random
    base_price = 100.0
    # 前期上涨后回调
    rising_prices = [base_price * (1 + i * 0.02) for i in range(15)]  # 前15个点上涨
    # 最后回调到支撑位
    dip_prices = [rising_prices[-1] * 0.97, rising_prices[-1] * 0.95]  # 调整
    all_prices = rising_prices + dip_prices
    
    # 模拟成交量历史
    volume_history = [500000 + random.randint(-100000, 100000) for _ in range(17)]
    
    # 模拟tick数据 - 低吸机会
    test_tick_data = {
        'stock_code': '002475',
        'datetime': datetime(2026, 2, 17, 14, 30, 0),
        'price': 95.0,  # 从高点回调
        'prev_close': 100.0,
        'volume': 400000,  # 缩量
    }
    
    # 模拟上下文信息
    test_context = {
        'price_history': all_prices,
        'volume_history': volume_history,
        'rsi': 25,  # RSI超卖
        'ma_support': [20, 30, 60]
    }
    
    # 测试用例
    test_cases = [
        {
            'name': '低吸候选股',
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
        print(f"昨收价格: {test_case['tick_data']['prev_close']:.2f}")
        print(f"涨跌幅: {(test_case['tick_data']['price'] - test_case['tick_data']['prev_close']) / test_case['tick_data']['prev_close'] * 100:.2f}%")
        print(f"RSI: {test_context['rsi']}")
        print(f"价格历史长度: {len(test_context['price_history'])}")
        
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
