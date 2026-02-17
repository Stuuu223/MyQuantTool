#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙头候选事件检测器 (Leader Candidate Event Detector)

根据CTO指导意见，实现统一的多战法事件检测架构。
该检测器专门负责检测LEADER_CANDIDATE事件，识别市场龙头股票。

核心功能：
1. 检测龙头候选事件（LEADER_CANDIDATE）
2. 识别市场情绪和板块龙头
3. 与统一的EventDriven架构对齐

设计原则：
1. 继承BaseEventDetector基类
2. 使用统一的EventType.LEADER_CANDIDATE
3. 遵循V12.1.0规范

验收标准：
- 能够正确检测龙头候选事件
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
from logic.utils.code_converter import CodeConverter

logger = get_logger(__name__)


class LeaderCandidateDetector(BaseEventDetector):
    """
    龙头候选事件检测器
    
    功能：
    1. 检测龙头候选事件
    2. 识别市场情绪和板块龙头
    3. 生成标准化的TradingEvent
    4. 提供详细的检测日志
    """

    # 龙头股识别阈值
    MIN_CHANGE_PERCENT = 7.0    # 最小涨幅百分比
    MIN_VOLUME_RATIO = 2.0      # 最小量比
    MIN_MONEY_FLOW = 100000000  # 最小资金流（1亿）
    SECTOR_LEAD_THRESHOLD = 1.5 # 板块领涨阈值

    def __init__(self):
        """初始化龙头候选检测器"""
        super().__init__(name="LeaderCandidateDetector")
        
        self.converter = CodeConverter()
        
        # 性能统计
        self._detection_count = 0
        self._success_count = 0
        
        logger.info("✅ [龙头候选检测器] 初始化完成")
        logger.info(f"   - 涨幅阈值: ≥{self.MIN_CHANGE_PERCENT}%")
        logger.info(f"   - 量比阈值: ≥{self.MIN_VOLUME_RATIO}")
        logger.info(f"   - 资金阈值: ≥{self.MIN_MONEY_FLOW/1e8:.1f}亿")
    
    def detect(self, tick_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[TradingEvent]:
        """
        检测龙头候选事件
        
        Args:
            tick_data: Tick数据字典
            context: 上下文信息（包含板块数据、市场情绪等）
        
        Returns:
            如果检测到龙头候选事件，返回TradingEvent；否则返回None
        """
        try:
            # 更新检测计数
            self._detection_count += 1
            
            # 提取关键信息
            stock_code = tick_data.get('stock_code', '')
            current_time = tick_data.get('datetime', datetime.now())
            current_price = tick_data.get('price', 0)
            volume = tick_data.get('volume', 0)
            amount = tick_data.get('amount', 0)  # 成交额
            
            # 获取涨跌幅信息
            prev_close = tick_data.get('prev_close', 0)
            if prev_close > 0:
                change_pct = (current_price - prev_close) / prev_close * 100
            else:
                change_pct = 0
            
            # 获取量比信息
            avg_volume = context.get('avg_volume_5d', 0)
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            
            # 检查是否满足龙头候选基本条件
            if not self._is_leader_candidate(change_pct, volume_ratio, amount):
                return None
            
            # 检查板块领导地位
            sector_data = context.get('sector_data', {})
            is_sector_leader = self._check_sector_leadership(stock_code, change_pct, sector_data)
            
            # 计算龙头置信度
            confidence = self._calculate_leader_confidence(
                change_pct, volume_ratio, amount, is_sector_leader
            )
            
            # 只有高置信度的龙头候选才触发事件
            if confidence >= 0.6:
                event = TradingEvent(
                    event_type=EventType.LEADER_CANDIDATE,
                    stock_code=stock_code,
                    timestamp=current_time,
                    data={
                        'change_pct': change_pct,
                        'volume_ratio': volume_ratio,
                        'amount': amount,
                        'is_sector_leader': is_sector_leader,
                        'confidence': confidence,
                        'sector_data': sector_data
                    },
                    confidence=confidence,
                    description=self._build_description(stock_code, change_pct, volume_ratio, is_sector_leader)
                )
                
                self._success_count += 1
                logger.info(f"🎯 [龙头候选] 检测到事件: {stock_code} - {event.description} (置信度: {confidence:.2f})")
                
                return event
            else:
                # 记录未触发事件的原因（用于调试）
                logger.debug(f"❌ [龙头候选] 未触发: {stock_code} - 置信度不足 ({confidence:.2f})")
                
        except Exception as e:
            logger.error(f"❌ [龙头候选检测器] 检测失败: {stock_code}, 错误: {e}")
        
        return None
    
    def _is_leader_candidate(self, change_pct: float, volume_ratio: float, amount: float) -> bool:
        """
        判断是否为龙头候选股
        
        Args:
            change_pct: 涨跌幅
            volume_ratio: 量比
            amount: 成交额
        
        Returns:
            bool: 是否为龙头候选股
        """
        # 检查基本条件
        is_high_change = change_pct >= self.MIN_CHANGE_PERCENT
        is_high_volume = volume_ratio >= self.MIN_VOLUME_RATIO
        is_high_amount = amount >= self.MIN_MONEY_FLOW
        
        return is_high_change and is_high_volume and is_high_amount
    
    def _check_sector_leadership(self, stock_code: str, change_pct: float, sector_data: Dict[str, Any]) -> bool:
        """
        检查是否为板块龙头
        
        Args:
            stock_code: 股票代码
            change_pct: 涨跌幅
            sector_data: 板块数据
        
        Returns:
            bool: 是否为板块龙头
        """
        try:
            if not sector_data:
                return False
            
            # 获取同板块股票数据
            sector_stocks = sector_data.get('stocks', [])
            if not sector_stocks:
                return False
            
            # 检查是否为板块涨幅第一或领先
            sector_changes = [stock.get('change_pct', 0) for stock in sector_stocks]
            if not sector_changes:
                return False
            
            max_sector_change = max(sector_changes)
            
            # 如果当前股票涨幅接近板块最高涨幅且为板块内靠前
            return change_pct >= (max_sector_change - self.SECTOR_LEAD_THRESHOLD)
            
        except Exception as e:
            logger.debug(f"⚠️ [龙头候选] 检查板块领导地位失败: {stock_code}, {e}")
            return False
    
    def _calculate_leader_confidence(
        self, 
        change_pct: float, 
        volume_ratio: float, 
        amount: float, 
        is_sector_leader: bool
    ) -> float:
        """
        计算龙头置信度
        
        Args:
            change_pct: 涨跌幅
            volume_ratio: 量比
            amount: 成交额
            is_sector_leader: 是否为板块龙头
        
        Returns:
            float: 置信度 (0-1)
        """
        try:
            # 基础置信度计算
            change_score = min(1.0, (change_pct - self.MIN_CHANGE_PERCENT) / 5.0)  # 涨幅得分
            volume_score = min(1.0, (volume_ratio - self.MIN_VOLUME_RATIO) / 3.0)  # 量比得分
            amount_score = min(1.0, amount / (self.MIN_MONEY_FLOW * 3))  # 资金得分
            
            # 平均基础得分
            base_confidence = (change_score + volume_score + amount_score) / 3.0
            
            # 如果是板块龙头，增加置信度
            if is_sector_leader:
                bonus = 0.2
                final_confidence = min(1.0, base_confidence + bonus)
            else:
                final_confidence = base_confidence
            
            return final_confidence
            
        except Exception as e:
            logger.error(f"❌ [龙头候选] 计算置信度失败: {e}")
            return 0.0
    
    def _build_description(
        self, 
        stock_code: str, 
        change_pct: float, 
        volume_ratio: float, 
        is_sector_leader: bool
    ) -> str:
        """
        构建事件描述
        
        Args:
            stock_code: 股票代码
            change_pct: 涨跌幅
            volume_ratio: 量比
            is_sector_leader: 是否为板块龙头
        
        Returns:
            str: 事件描述
        """
        try:
            leader_type = "板块龙头" if is_sector_leader else "独立龙头"
            description_parts = [
                "龙头候选",
                f"：{leader_type}",
                f"，涨幅{change_pct:.2f}%",
                f"，量比{volume_ratio:.2f}",
                f"，成交额{amount/1e8:.2f}亿" if (amount := self._get_amount_from_context(stock_code)) else ""
            ]
            
            return "".join(description_parts)
            
        except Exception as e:
            logger.error(f"❌ [龙头候选] 构建描述失败: {e}")
            return f"龙头候选：{stock_code} - 涨幅{change_pct:.2f}%"
    
    def _get_amount_from_context(self, stock_code: str) -> float:
        """
        从上下文获取成交额（辅助函数）
        注意：实际使用中需要从tick_data获取
        """
        # 这里是占位符，实际使用中通过其他方式获取
        return 0.0
    
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
    # 测试LeaderCandidateDetector
    print("=" * 80)
    print("龙头候选事件检测器测试")
    print("=" * 80)
    
    detector = LeaderCandidateDetector()
    
    # 模拟tick数据 - 龙头候选股
    test_tick_data = {
        'stock_code': '300750',
        'datetime': datetime(2026, 2, 17, 10, 30, 0),
        'price': 220.5,
        'prev_close': 200.0,  # 涨幅10.25%
        'volume': 1500000,
        'amount': 330750000  # 3.3亿成交额
    }
    
    # 模拟上下文信息
    test_context = {
        'avg_volume_5d': 500000,  # 前5日平均成交量
        'sector_data': {
            'stocks': [
                {'code': '300750', 'change_pct': 10.25},
                {'code': '300015', 'change_pct': 8.5},
                {'code': '300014', 'change_pct': 7.2}
            ]
        }
    }
    
    # 测试用例
    test_cases = [
        {
            'name': '龙头候选股',
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
        print(f"成交额: {test_case['tick_data']['amount'] / 1e8:.2f}亿")
        
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
