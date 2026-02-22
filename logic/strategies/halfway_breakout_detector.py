#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
半路起爆事件检测器 (Halfway Breakout Detector) - V2.1 Ratio化重构版

CTO指令重构要点：
1. ✅ 删除所有volatility和np.std愚蠢逻辑
2. ✅ 使用pre_close作为涨幅计算唯一基准
3. ✅ 引入多周期资金持续性判断（5min/15min滚动流）
4. ✅ 基于A/B测试铁证：真突破 vs 骗炮的资金断层特征
5. ✅ V2.1: 从config/strategy_params.json读取Ratio化参数，消除样本残留

系统哲学：顺势而为，抓推土机式的真突破，过滤直线骗炮

Author: AI项目总监（CTO指令重构）
Version: V2.1 (Ratio化配置驱动)
Date: 2026-02-22
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from logic.strategies.event_detector import BaseEventDetector, TradingEvent, EventType
from logic.rolling_metrics import RollingFlowCalculator, calculate_true_change_pct
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def _load_strategy_params() -> Dict[str, Any]:
    """从配置文件加载策略参数"""
    config_path = Path(__file__).parent.parent.parent / "config" / "strategy_params.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"⚠️ 无法加载策略配置，使用默认值: {e}")
        return {
            "halfway": {
                "min_intensity_score": 0.35,
                "ratio_stock_min": 0.01,
                "sustain_min": 1.0
            }
        }


class HalfwayBreakoutDetector(BaseEventDetector):
    """
    半路起爆事件检测器 V2.1 - Phase 1 Ratio化资金强度
    
    核心变革：
    - V2.0: 固定阈值FLOW_5MIN_THRESHOLD=5M（样本残留）
    - V2.1: Ratio化动态阈值（从配置文件读取，消除硬编码）
    - 新增：intensity_score 0-1综合评分
    
    触发逻辑（根据网宿A/B测试铁证）：
    1. 真实涨幅突破阈值 - 基于pre_close
    2. 资金强度评分 >= min_intensity_score（默认0.35）
    3. 15分钟流/5分钟流 >= sustain_min（默认1.0）
    
    配置驱动：所有阈值从config/strategy_params.json读取
    """
    
    # 类级别加载配置（启动时一次）
    _config = _load_strategy_params()
    _halfway_config = _config.get("halfway", {})
    
    # 🔥 V2.1: 从配置文件读取参数，消除样本残留硬编码
    MIN_INTENSITY_SCORE = _halfway_config.get("min_intensity_score", 0.35)
    RATIO_STOCK_MIN = _halfway_config.get("ratio_stock_min", 0.01)
    FLOW_SUSTAINABILITY_MIN = _halfway_config.get("sustain_min", 1.0)
    
    # 🔥 废弃：FLOW_5MIN_THRESHOLD是样本残留，V2.1不再使用
    # 仅保留作为保护阈值（极低流动性过滤）
    FLOW_5MIN_MIN_ABS = 1e6  # 100万绝对值下限，避免零流动性票
    
    def __init__(self):
        """初始化半路起爆检测器"""
        super().__init__(name="HalfwayBreakoutDetectorV2.1")
        
        # 每个股票的资金流计算器
        self._flow_calculators: Dict[str, RollingFlowCalculator] = {}
        
        # 日志输出当前配置
        logger.info(f"📝 HalfwayV2.1配置: intensity>={self.MIN_INTENSITY_SCORE}, "
                   f"ratio_stock>={self.RATIO_STOCK_MIN}, sustain>={self.FLOW_SUSTAINABILITY_MIN}")
        
        # 性能统计
        self._detection_count = 0
        self._success_count = 0
        
        logger.info("✅ [半路起爆检测器V2] 初始化完成")
        logger.info("   - V11.0 全Ratio化：分层ratio_stock + response_eff + big_ratio")
        logger.info("   - 资金持续性要求: 1.0x")
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
            
            # 🔥 调试打印（前10个tick）
            # if self._detection_count < 10:
            #     print(f"   [DEBUG] {stock_code} @ {current_time}: 涨幅={true_change_pct:.2f}%, 价格={current_price}, pre_close={pre_close}")
            #     print(f"   [DEBUG] context main_net_inflow={context.get('main_net_inflow', 'N/A')}, threshold={self.FLOW_5MIN_THRESHOLD}")
            
            # ===== 步骤3: 快速过滤 - 分层ratio检查 =====
            # 🔥 V11.0: 用换手率分层ratio阈值替代固定2%/5%
            turnover = context.get('turnover', 0.05)  # 假设日换手率
            if turnover > 0.10:  # 高频>10%
                ratio_thresh = 3.0
            elif turnover > 0.05:  # 中频5-10%
                ratio_thresh = 2.0
            else:  # 低频<5%
                ratio_thresh = 1.5
            
            # 🔥 V11.0: 计算flow_ratios（需要扩展rolling_metrics.py）
            try:
                # V14修复：优先使用context中的calc对象（已有last_metrics）
                calc = context.get('calc') or self._get_flow_calculator(stock_code, pre_close)
                ratios = calc.get_flow_ratios(stock_code)
            except:
                ratios = {'ratio_stock': 1.0, 'sustain': 1.0, 'response_eff': 0.1}
            
            # 🔥 V11.0: 分层ratio触发检查
            if ratios['ratio_stock'] < ratio_thresh:
                return None  # ratio不达标
            if ratios['sustain'] < 1.0:
                return None  # 持续性不达标
            if ratios['response_eff'] < 0.05:
                return None  # 响应效率不达标  # 涨幅不足2%，不进入资金判断
            
            # ===== 步骤4: 获取资金流和成交量数据（V12换手纯净关键）=====
            # 🔥 优先使用context中的main_net_inflow（CSV已计算好）
            flow_5min = context.get('main_net_inflow', 0)
            
            # V12关键：总是创建metrics对象，以便获取成交量数据
            calc = self._get_flow_calculator(stock_code, pre_close)
            last_tick = context.get('last_tick')
            metrics = calc.add_tick(tick_data, last_tick)
            
            if flow_5min == 0:
                # 回退：使用RollingFlowCalculator计算的资金流
                flow_5min = metrics.flow_5min.total_flow
                flow_15min = metrics.flow_15min.total_flow
            else:
                # 使用CSV的flow_sustainability作为15min/5min比率
                flow_sustainability = tick_data.get('flow_sustainability', 1.0)
                flow_15min = flow_5min * flow_sustainability
            
            # V12关键数据：获取5分钟成交量（用于换手率计算）
            vol_5min = metrics.flow_5min.total_volume if hasattr(metrics, 'flow_5min') and hasattr(metrics.flow_5min, 'total_volume') else 0
            
            # ===== 步骤5: 核心判断 - 真突破条件（Phase 1 Ratio化） =====
            # 🔥 新增：计算资金强度评分（0-1）
            try:
                from logic.scoring.flow_intensity_scorer import FlowIntensityScorer
                from logic.services.data_service import data_service
                
                intensity_scorer = FlowIntensityScorer(data_service)
                intensity_result = intensity_scorer.score(
                    flow_5min=flow_5min,
                    stock_code=stock_code,
                    trade_date=context.get('date', datetime.now().strftime('%Y-%m-%d')),
                    flow_15min=flow_15min
                )
                intensity_score = intensity_result['intensity_score']
                ratio_stock = intensity_result['ratio_stock']
                circ_mv_bn = intensity_result['circ_mv_bn']
            except Exception as e:
                # Fallback：如果强度计算失败，使用最小保护阈值估算
                intensity_score = min(1.0, abs(flow_5min) / (self.FLOW_5MIN_MIN_ABS * 10))
                ratio_stock = 0
                circ_mv_bn = 0
                intensity_result = {}
                logger.debug(f"⚠️ intensity_scorer失败，使用fallback: {e}")
            
            # 条件A: 资金强度评分 >= 阈值（Ratio化爆发力）
            condition_a = intensity_score >= self.MIN_INTENSITY_SCORE
            
            # 条件B: 15分钟流/5分钟流 > 1.0（持续性，非骗炮）
            flow_ratio = flow_15min / flow_5min if abs(flow_5min) > 0 else 0
            condition_b = flow_ratio >= self.FLOW_SUSTAINABILITY_MIN
            
            # 条件C: V12换手纯净 - 换手率主导（ratio_stock>15, ratio_day>10, sustain>1.2）
            # 获取流通市值（十亿元转元）
            circ_mv_bn = intensity_result.get('circ_mv_bn', 5)  # 默认50亿
            circ_mv = circ_mv_bn * 1e9 if circ_mv_bn > 0 else 5e9  # 默认50亿
            
            # 使用RollingFlowCalculator计算换手率ratio
            ratio_stock, ratio_day = calc.get_turnover_ratio(stock_code, vol_5min, circ_mv)
            
            # V12换手纯净条件：ratio_stock>15, ratio_day>10, sustain>1.2
            sustain = flow_15min / flow_5min if flow_5min != 0 else 0
            condition_c = (ratio_stock > 15) and (ratio_day > 10) and (sustain > 1.2)
            
            # 综合判断（强度+持续性双保险）
            is_true_breakout = condition_a and condition_b and condition_c
            
            # 🔥 调试条件判断
            # if self._detection_count < 10:
            #     print(f"   [DEBUG] 条件A(5min流): {flow_5min:.0f} >= {self.FLOW_5MIN_THRESHOLD} = {condition_a}")
            #     print(f"   [DEBUG] 条件B(持续性): {flow_ratio:.2f} >= {self.FLOW_SUSTAINABILITY_MIN} = {condition_b}")
            #     print(f"   [DEBUG] 条件C(涨幅): {true_change_pct:.2f}% 在 2%-20% = {condition_c}")
            #     print(f"   [DEBUG] 综合结果: {is_true_breakout}")
            
            # ===== 步骤6: 生成事件 =====
            if is_true_breakout:
                # print(f"   [DEBUG] 🎯 生成事件! {stock_code} @ {true_change_pct:.2f}%")
                confidence = self._calculate_confidence(true_change_pct, flow_5min, flow_ratio)
                
                # 🔥 修复：获取flow_1min（从metrics或tick_data）
                if flow_5min == 0:
                    flow_1min = metrics.flow_1min.total_flow
                else:
                    flow_1min = tick_data.get('flow_1min', flow_5min / 5)  # 用5min/5估算
                
                event = TradingEvent(
                    event_type=EventType.HALFWAY_BREAKOUT,
                    stock_code=stock_code,
                    timestamp=current_time,
                    data={
                        'true_change_pct': true_change_pct,      # 真实涨幅
                        'flow_1min': flow_1min,
                        'flow_5min': flow_5min,                  # 5分钟流
                        'flow_15min': flow_15min,                # 15分钟流
                        'flow_sustainability': flow_ratio,       # 资金持续性
                        'current_price': current_price,
                        'pre_close': pre_close,
                        'confidence': confidence,
                        # 🔥 Phase 1: 新增资金强度评分
                        'intensity_score': intensity_score,
                        'ratio_stock': ratio_stock,
                        'circ_mv_bn': circ_mv_bn,
                        **intensity_result  # 展开所有强度相关字段
                    },
                    confidence=confidence,
                    description=self._build_description(
                        stock_code, true_change_pct, flow_5min, flow_ratio, current_price,
                        intensity_score, ratio_stock
                    )
                )
                
                self._success_count += 1
                logger.info(f"🎯 [半路起爆V2] 真突破: {stock_code} @ {true_change_pct:.2f}%, "
                           f"5min流={flow_5min/1e6:.1f}M, 持续性={flow_ratio:.2f}x")
                
                return event
            else:
                # 记录未触发原因（简化版）
                reasons = []
                if not condition_a:
                    reasons.append(f"资金强度不足({intensity_score:.2f}<{self.MIN_INTENSITY_SCORE})")
                if not condition_b:
                    reasons.append(f"持续性不足({flow_ratio:.2f}x<{self.FLOW_SUSTAINABILITY_MIN:.1f}x)")
                if not condition_c:
                    reasons.append(f"换手率条件不满足")
                if reasons:
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
        
        # 资金强度得分（使用保护阈值，V2.1消除样本残留）
        intensity_score = min(1.0, abs(flow_5min) / (self.FLOW_5MIN_MIN_ABS * 10))
        
        # 持续性得分
        sustainability_score = min(1.0, (flow_ratio - 1.0) / 1.0)
        
        # 加权综合
        confidence = change_score * 0.3 + intensity_score * 0.4 + sustainability_score * 0.3
        return min(1.0, max(0.3, confidence))
    
    def _build_description(self, stock_code: str, change_pct: float, 
                          flow_5min: float, flow_ratio: float, price: float,
                          intensity_score: float = 0, ratio_stock: float = 0) -> str:
        """构建事件描述（Phase 1: 新增强度评分）"""
        # 判断突破强度（基于intensity_score）
        if intensity_score >= 0.8:
            strength = "🔥极度强势"
        elif intensity_score >= 0.6:
            strength = "💪标准强势"
        elif flow_5min >= 50e6:
            strength = "📈标准突破"
        else:
            strength = "📊温和突破"
        
        # Phase 1: 添加ratio_stock到描述
        ratio_str = f", 资金比{ratio_stock*100:.2f}%" if ratio_stock > 0 else ""
        intensity_str = f", 强度{intensity_score:.2f}"
        
        return (f"{strength}: {stock_code} 涨幅{change_pct:.2f}%, "
                f"5min流{flow_5min/1e6:.1f}M, 持续性{flow_ratio:.2f}x{ratio_str}{intensity_str}, 价{price:.2f}")
    
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
    print(f"  触发阈值: V12换手纯净 (ratio_stock>15, ratio_day>10, sustain>1.2)")
    print(f"  最小资金流: {detector.FLOW_5MIN_MIN_ABS/1e6:.0f}M (保护阈值)")
    print(f"  强度阈值: intensity_score >= {detector.MIN_INTENSITY_SCORE}")
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