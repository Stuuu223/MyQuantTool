#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
半路起爆事件检测器 (Halfway Breakout Detector) - V2.0 重构版

CTO指令重构要点：
1. ✅ 删除所有volatility和np.std愚蠢逻辑
2. ✅ 使用pre_close作为涨幅计算唯一基准
3. ✅ 引入多周期资金持续性判断（5min/15min滚动流）
4. ✅ 基于A/B测试铁证：真突破 vs 骗炮的资金断层特征

系统哲学：顺势而为，抓推土机式的真突破，过滤直线骗炮

Author: AI项目总监（CTO指令重构）
Version: V2.0
Date: 2026-02-20
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from logic.strategies.event_detector import BaseEventDetector, TradingEvent, EventType
from logic.rolling_metrics import RollingFlowCalculator, calculate_true_change_pct
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class HalfwayBreakoutDetector(BaseEventDetector):
    """
    半路起爆事件检测器 V2.0
    
    核心变革：
    - 废除：波动率(volatility)判断
    - 新增：多周期资金持续性判断
    - 基准：pre_close（昨收价）为涨幅计算唯一锚点
    
    触发逻辑（根据网宿A/B测试铁证）：
    1. 真实涨幅突破阈值（5%或8%）- 基于pre_close
    2. 5分钟滚动资金流 > 阈值（3000万）
    3. 15分钟流/5分钟流 > 1.2（资金持续性）
    """

    # CTO指令：基于A/B测试优化的阈值
    TRIGGER_PCT_LEVEL_1 = 5.0   # 第一触发点：+5%
    TRIGGER_PCT_LEVEL_2 = 8.0   # 第二触发点：+8%
    
    FLOW_5MIN_THRESHOLD = 30e6   # 5分钟资金流阈值：3000万
    FLOW_SUSTAINABILITY_MIN = 1.2  # 资金持续性最小比率（15min/5min）
    
    def __init__(self):
        """初始化半路起爆检测器"""
        super().__init__(name="HalfwayBreakoutDetectorV2")
        
        # 每个股票的资金流计算器
        self._flow_calculators: Dict[str, RollingFlowCalculator] = {}
        
        # 性能统计
        self._detection_count = 0
        self._success_count = 0
        
        logger.info("✅ [半路起爆检测器V2] 初始化完成")
        logger.info(f"   - 触发阈值: +{self.TRIGGER_PCT_LEVEL_1}% / +{self.TRIGGER_PCT_LEVEL_2}%")
        logger.info(f"   - 5分钟资金流阈值: {self.FLOW_5MIN_THRESHOLD/1e6:.0f}M")
        logger.info(f"   - 资金持续性要求: {self.FLOW_SUSTAINABILITY_MIN:.1f}x")
    
    def _get_flow_calculator(self, stock_code: str, pre_close: float) -> RollingFlowCalculator:
        """获取或创建资金流计算器"""
        if stock_code not in self._flow_calculators:
            calc = RollingFlowCalculator(windows=[1, 5, 15, 30])
            calc.set_pre_close(pre_close)
            self._flow_calculators[stock_code] = calc
            logger.debug(f"📝 创建资金流计算器: {stock_code}, pre_close={pre_close}")
        return self._flow_calculators[stock_code]
    
    def detect(self, tick_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[TradingEvent]:
        """
        检测半路起爆事件（V2.0核心逻辑）
        
        Args:
            tick_data: Tick数据字典（必须包含preClose或从context获取）
            context: 上下文信息（必须包含pre_close昨收价）
        
        Returns:
            如果检测到真突破事件，返回TradingEvent；否则返回None
        """
        try:
            self._detection_count += 1
            
            # ===== 步骤1: 提取关键数据 =====
            stock_code = tick_data.get('stock_code', '')
            current_time = tick_data.get('datetime', datetime.now())
            current_price = tick_data.get('price', tick_data.get('lastPrice', 0))
            
            # 🔥 CTO指令：从context获取昨收价（pre_close），严禁使用open
            pre_close = context.get('pre_close', tick_data.get('preClose', 0))
            if pre_close <= 0:
                logger.warning(f"⚠️ [{stock_code}] 缺少pre_close，无法计算真实涨幅")
                return None
            
            # ===== 步骤2: 计算真实涨幅（基于pre_close） =====
            true_change_pct = calculate_true_change_pct(current_price, pre_close)
            
            # ===== 步骤3: 快速过滤 - 涨幅未达触发阈值 =====
            if true_change_pct < self.TRIGGER_PCT_LEVEL_1:
                return None  # 涨幅不足5%，不进入资金判断
            
            # ===== 步骤4: 计算多周期资金流 =====
            calc = self._get_flow_calculator(stock_code, pre_close)
            last_tick = context.get('last_tick')
            metrics = calc.add_tick(tick_data, last_tick)
            
            flow_5min = metrics.flow_5min.total_flow
            flow_15min = metrics.flow_15min.total_flow
            
            # ===== 步骤5: 核心判断 - 真突破条件（CTO指令） =====
            # 条件A: 5分钟资金流 > 阈值（爆发力）
            condition_a = flow_5min >= self.FLOW_5MIN_THRESHOLD
            
            # 条件B: 15分钟流/5分钟流 > 1.2（持续性，非骗炮）
            flow_ratio = flow_15min / flow_5min if abs(flow_5min) > 0 else 0
            condition_b = flow_ratio >= self.FLOW_SUSTAINABILITY_MIN
            
            # 条件C: 处于半路区间（5%-20%，已过早盘杂毛期，未封板）
            condition_c = self.TRIGGER_PCT_LEVEL_1 <= true_change_pct <= 20.0
            
            # 综合判断
            is_true_breakout = condition_a and condition_b and condition_c
            
            # ===== 步骤6: 生成事件 =====
            if is_true_breakout:
                confidence = self._calculate_confidence(true_change_pct, flow_5min, flow_ratio)
                
                event = TradingEvent(
                    event_type=EventType.HALFWAY_BREAKOUT,
                    stock_code=stock_code,
                    timestamp=current_time,
                    data={
                        'true_change_pct': true_change_pct,      # 真实涨幅
                        'flow_1min': metrics.flow_1min.total_flow,
                        'flow_5min': flow_5min,                  # 5分钟流
                        'flow_15min': flow_15min,                # 15分钟流
                        'flow_sustainability': flow_ratio,       # 资金持续性
                        'current_price': current_price,
                        'pre_close': pre_close,
                        'confidence': confidence
                    },
                    confidence=confidence,
                    description=self._build_description(
                        stock_code, true_change_pct, flow_5min, flow_ratio, current_price
                    )
                )
                
                self._success_count += 1
                logger.info(f"🎯 [半路起爆V2] 真突破: {stock_code} @ {true_change_pct:.2f}%, "
                           f"5min流={flow_5min/1e6:.1f}M, 持续性={flow_ratio:.2f}x")
                
                return event
            else:
                # 记录未触发原因（调试用）
                if true_change_pct >= self.TRIGGER_PCT_LEVEL_1:
                    reasons = []
                    if not condition_a:
                        reasons.append(f"5min流不足({flow_5min/1e6:.1f}M<{self.FLOW_5MIN_THRESHOLD/1e6:.0f}M)")
                    if not condition_b:
                        reasons.append(f"持续性不足({flow_ratio:.2f}x<{self.FLOW_SUSTAINABILITY_MIN:.1f}x)")
                    logger.debug(f"❌ [半路起爆V2] 未触发: {stock_code} @ {true_change_pct:.2f}%, {', '.join(reasons)}")
                
        except Exception as e:
            logger.error(f"❌ [半路起爆检测器V2] 检测失败: {stock_code}, 错误: {e}")
        
        return None
    
    def _calculate_confidence(self, change_pct: float, flow_5min: float, flow_ratio: float) -> float:
        """
        计算综合置信度
        
        基于：
        - 涨幅位置（8%附近最佳）
        - 5分钟资金强度
        - 资金持续性
        """
        # 涨幅得分（8%附近得最高分）
        change_score = 1.0 - abs(change_pct - 8.0) / 8.0
        change_score = max(0.0, min(1.0, change_score))
        
        # 资金强度得分
        intensity_score = min(1.0, flow_5min / (self.FLOW_5MIN_THRESHOLD * 3))
        
        # 持续性得分
        sustainability_score = min(1.0, (flow_ratio - 1.0) / 1.0)
        
        # 加权综合
        confidence = change_score * 0.3 + intensity_score * 0.4 + sustainability_score * 0.3
        return min(1.0, max(0.3, confidence))
    
    def _build_description(self, stock_code: str, change_pct: float, 
                          flow_5min: float, flow_ratio: float, price: float) -> str:
        """构建事件描述"""
        # 判断突破强度
        if flow_5min >= 100e6 and flow_ratio >= 1.5:
            strength = "强势真突破"
        elif flow_5min >= 50e6:
            strength = "标准真突破"
        else:
            strength = "温和突破"
        
        return (f"{strength}: {stock_code} 涨幅{change_pct:.2f}%, "
                f"5min流{flow_5min/1e6:.1f}M, 持续性{flow_ratio:.2f}x, 价{price:.2f}")
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """获取检测统计信息"""
        success_rate = self._success_count / self._detection_count if self._detection_count > 0 else 0
        return {
            '总检测次数': self._detection_count,
            '成功检测次数': self._success_count,
            '成功检测率': f"{success_rate:.2%}",
            '监控股票数': len(self._flow_calculators),
            '检测器版本': 'V2.0(CTO重构版)',
            '检测器状态': '启用' if self.enabled else '禁用'
        }
    
    def reset_calculator(self, stock_code: Optional[str] = None):
        """重置资金流计算器"""
        if stock_code:
            if stock_code in self._flow_calculators:
                del self._flow_calculators[stock_code]
                logger.info(f"🔄 重置计算器: {stock_code}")
        else:
            self._flow_calculators.clear()
            logger.info("🔄 重置所有计算器")


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("半路起爆事件检测器V2 测试")
    print("CTO重构版：基于pre_close + 多周期资金流")
    print("=" * 80)
    
    detector = HalfwayBreakoutDetector()
    
    # 模拟网宿科技1月26日早盘数据
    pre_close = 11.48  # 昨收价
    
    test_ticks = [
        {'stock_code': '300017', 'datetime': datetime(2026, 1, 26, 9, 35, 0), 'price': 12.05, 'volume': 100000},
        {'stock_code': '300017', 'datetime': datetime(2026, 1, 26, 9, 36, 0), 'price': 12.15, 'volume': 150000},
        {'stock_code': '300017', 'datetime': datetime(2026, 1, 26, 9, 37, 0), 'price': 12.25, 'volume': 200000},
        {'stock_code': '300017', 'datetime': datetime(2026, 1, 26, 9, 38, 0), 'price': 12.35, 'volume': 250000},
        {'stock_code': '300017', 'datetime': datetime(2026, 1, 26, 9, 39, 0), 'price': 12.45, 'volume': 300000},
    ]
    
    print(f"\n测试参数:")
    print(f"  昨收价(pre_close): {pre_close}")
    print(f"  触发阈值: +{detector.TRIGGER_PCT_LEVEL_1}%")
    print(f"  5分钟流阈值: {detector.FLOW_5MIN_THRESHOLD/1e6:.0f}M")
    print("-" * 80)
    
    last_tick = None
    for tick in test_ticks:
        context = {
            'pre_close': pre_close,
            'last_tick': last_tick
        }
        
        event = detector.detect(tick, context)
        
        change_pct = (tick['price'] - pre_close) / pre_close * 100
        print(f"\n时间: {tick['datetime'].strftime('%H:%M:%S')}")
        print(f"  价格: {tick['price']:.2f}, 真实涨幅: {change_pct:.2f}%")
        
        if event:
            print(f"  ✅ 检测到事件: {event.description}")
            print(f"  数据: 5min流={event.data['flow_5min']/1e6:.1f}M, "
                  f"持续性={event.data['flow_sustainability']:.2f}x")
        else:
            print(f"  ❌ 未触发")
        
        last_tick = tick
    
    print("\n" + "=" * 80)
    print("检测统计:")
    stats = detector.get_detection_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ V2测试完成")
    print("=" * 80)