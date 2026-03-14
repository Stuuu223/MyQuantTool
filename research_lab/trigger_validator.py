# -*- coding: utf-8 -*-
"""
【CTO课题三】动态买点拓扑验证器

物理买点必须满足三维条件：
1. 时间：在正确的时刻
2. 空间：在正确的位置
3. 加速度：有确认信号

三大触发拓扑：
- 引力弹弓：回踩后弹起
- 阶梯突破：横盘后突破
- 真空点火：量比瞬间爆表

Author: CTO Research Lab
Date: 2026-03-14
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class TriggerSignal:
    """触发信号数据结构"""
    trigger_type: str           # 'vwap_bounce' / 'stair_breakout' / 'vacuum_ignition'
    stock_code: str
    timestamp: datetime
    price: float
    confidence: float           # 0.0 - 1.0
    details: Dict               # 详细触发条件
    
    # 后续验证数据
    price_5min_later: Optional[float] = None
    price_15min_later: Optional[float] = None
    max_price_after: Optional[float] = None
    min_price_after: Optional[float] = None


class TriggerValidator:
    """
    动态买点验证器
    
    核心理念：
    打分高只代表"过去15分钟很强"
    真正的买点需要捕捉"现在这一秒钟的异动"
    """
    
    # ==================== 物理阈值（需回测校准） ====================
    VWAP_DISTANCE_MAX = 0.015       # 距离VWAP最大1.5%
    VWAP_BOUNCE_MFE_MIN = 2.0       # 反弹时MFE至少2.0
    
    STAIR_AMPLITUDE_MAX = 0.02      # 横盘振幅最大2%
    STAIR_DURATION_MIN = 15         # 横盘至少15分钟
    STAIR_VOLUME_RATIO_MIN = 1.5    # 突破时量比至少1.5倍历史
    
    IGNITION_VOLUME_RATIO_MIN = 3.0 # 点火量比至少3.0倍
    IGNITION_MFE_MIN = 1.5          # 点火MFE至少1.5
    
    def __init__(self):
        self.signals: List[TriggerSignal] = []
        self.validated_signals: List[TriggerSignal] = []
    
    # ==================== 触发检测方法 ====================
    
    def check_vwap_bounce(
        self,
        stock_code: str,
        current_price: float,
        vwap: float,
        recent_mfe_list: List[float],
        price_history: List[float],
        timestamp: datetime
    ) -> Optional[TriggerSignal]:
        """
        【引力弹弓】VWAP反弹触发器
        
        条件：
        1. 当前价格距离VWAP < 1.5%
        2. 最近3个Tick的MFE均值 > 2.0（有向上动能）
        3. 之前有回踩动作（价格曾低于VWAP）
        
        物理意义：
        主力洗盘后，在成本线（VWAP）附近重新发起攻击
        """
        if vwap <= 0:
            return None
        
        # 条件1：距离VWAP
        distance_ratio = abs(current_price - vwap) / vwap
        if distance_ratio > self.VWAP_DISTANCE_MAX:
            return None
        
        # 条件2：近期MFE（最近3个值）
        if len(recent_mfe_list) < 3:
            return None
        recent_mfe_avg = sum(recent_mfe_list[-3:]) / 3
        if recent_mfe_avg < self.VWAP_BOUNCE_MFE_MIN:
            return None
        
        # 条件3：之前有回踩动作（至少有一个价格低于VWAP）
        if len(price_history) < 5:
            return None
        has_dipped_below = any(p < vwap for p in price_history[-10:])
        if not has_dipped_below:
            return None
        
        # 触发！
        confidence = min(1.0, recent_mfe_avg / 5.0)  # MFE越高置信度越高
        
        return TriggerSignal(
            trigger_type='vwap_bounce',
            stock_code=stock_code,
            timestamp=timestamp,
            price=current_price,
            confidence=confidence,
            details={
                'vwap': vwap,
                'distance_pct': distance_ratio * 100,
                'recent_mfe_avg': recent_mfe_avg,
                'has_dipped': True
            }
        )
    
    def check_stair_breakout(
        self,
        stock_code: str,
        current_price: float,
        price_history: List[float],
        volume_ratio: float,
        current_slope: float,
        timestamp: datetime
    ) -> Optional[TriggerSignal]:
        """
        【阶梯突破】横盘整理后突破触发器
        
        条件：
        1. 之前15分钟振幅 < 2%（横盘）
        2. 当前价格突破横盘区间上沿
        3. 当前斜率急剧变陡（斜率 > 阈值）
        4. 量比 > 1.5（有成交量配合）
        
        物理意义：
        主力在横盘期吸筹完成后，开始拉升
        """
        if len(price_history) < 15:  # 至少15个数据点
            return None
        
        # 条件1：横盘振幅（取最近15个点）
        recent_prices = price_history[-15:]
        high = max(recent_prices[:-1])  # 排除当前价格
        low = min(recent_prices[:-1])
        
        if low <= 0:
            return None
        
        amplitude = (high - low) / low
        if amplitude > self.STAIR_AMPLITUDE_MAX:
            return None
        
        # 条件2：当前价格突破上沿
        if current_price <= high:
            return None
        
        # 条件3：斜率（简化：用最近涨速）
        if current_slope <= 0:
            return None
        # 斜率阈值：横盘期的振幅/时间的3倍
        slope_threshold = amplitude / 15 * 3
        if current_slope < slope_threshold:
            return None
        
        # 条件4：量比
        if volume_ratio < self.STAIR_VOLUME_RATIO_MIN:
            return None
        
        # 触发！
        breakout_pct = (current_price - high) / high * 100
        confidence = min(1.0, breakout_pct / 2.0 + volume_ratio / 5.0)
        
        return TriggerSignal(
            trigger_type='stair_breakout',
            stock_code=stock_code,
            timestamp=timestamp,
            price=current_price,
            confidence=confidence,
            details={
                'consolidation_amplitude': amplitude * 100,
                'breakout_pct': breakout_pct,
                'slope': current_slope,
                'volume_ratio': volume_ratio
            }
        )
    
    def check_vacuum_ignition(
        self,
        stock_code: str,
        current_price: float,
        prev_close: float,
        volume_ratio: float,
        current_mfe: float,
        recent_volume_ratios: List[float],
        timestamp: datetime
    ) -> Optional[TriggerSignal]:
        """
        【真空点火】量比瞬间爆发触发器
        
        条件：
        1. 当前量比 > 3.0（突然放量）
        2. 之前量比 < 当前量比的50%（突然性）
        3. MFE > 1.5（价格轻松上涨，真空无阻力）
        4. 价格上涨（不是放量砸盘）
        
        物理意义：
        主力突然发起攻击，市场还没来得及堆积卖压
        """
        # 条件1：量比
        if volume_ratio < self.IGNITION_VOLUME_RATIO_MIN:
            return None
        
        # 条件2：突然性（之前量比较低）
        if len(recent_volume_ratios) < 3:
            return None
        avg_prev_ratio = sum(recent_volume_ratios[-5:-1]) / max(1, len(recent_volume_ratios[-5:-1]))
        if avg_prev_ratio > volume_ratio * 0.5:  # 之前量比已经很高了，不是"突然"
            return None
        
        # 条件3：MFE
        if current_mfe < self.IGNITION_MFE_MIN:
            return None
        
        # 条件4：价格上涨
        if current_price <= prev_close:
            return None
        
        # 触发！
        change_pct = (current_price - prev_close) / prev_close * 100
        ratio_jump = volume_ratio / max(0.1, avg_prev_ratio)
        confidence = min(1.0, ratio_jump / 5.0 + current_mfe / 5.0)
        
        return TriggerSignal(
            trigger_type='vacuum_ignition',
            stock_code=stock_code,
            timestamp=timestamp,
            price=current_price,
            confidence=confidence,
            details={
                'volume_ratio': volume_ratio,
                'ratio_jump': ratio_jump,
                'mfe': current_mfe,
                'change_pct': change_pct
            }
        )
    
    # ==================== 综合触发判断 ====================
    
    def check_all_triggers(
        self,
        stock_code: str,
        current_price: float,
        prev_close: float,
        vwap: float,
        volume_ratio: float,
        current_mfe: float,
        recent_mfe_list: List[float],
        price_history: List[float],
        recent_volume_ratios: List[float],
        current_slope: float,
        timestamp: datetime
    ) -> Optional[TriggerSignal]:
        """
        综合检查所有触发条件
        
        Returns:
            触发信号（置信度最高的那个）
        """
        signals = []
        
        # 检查三种触发类型
        sig1 = self.check_vwap_bounce(
            stock_code, current_price, vwap,
            recent_mfe_list, price_history, timestamp
        )
        if sig1:
            signals.append(sig1)
        
        sig2 = self.check_stair_breakout(
            stock_code, current_price, price_history,
            volume_ratio, current_slope, timestamp
        )
        if sig2:
            signals.append(sig2)
        
        sig3 = self.check_vacuum_ignition(
            stock_code, current_price, prev_close,
            volume_ratio, current_mfe, recent_volume_ratios, timestamp
        )
        if sig3:
            signals.append(sig3)
        
        if not signals:
            return None
        
        # 返回置信度最高的
        signals.sort(key=lambda x: x.confidence, reverse=True)
        best = signals[0]
        self.signals.append(best)
        
        logger.info(f"[Trigger] {stock_code} 触发{best.trigger_type}, 置信度={best.confidence:.2f}")
        
        return best
    
    # ==================== 买点质量验证 ====================
    
    def validate_trigger_quality(
        self,
        signal: TriggerSignal,
        price_5min: float,
        price_15min: float,
        max_price: float,
        min_price: float
    ) -> Dict:
        """
        验证触发信号的质量
        
        Args:
            signal: 触发信号
            price_5min: 5分钟后的价格
            price_15min: 15分钟后的价格
            max_price: 之后最高价
            min_price: 之后最低价
            
        Returns:
            验证结果字典
        """
        entry_price = signal.price
        
        # 更新信号数据
        signal.price_5min_later = price_5min
        signal.price_15min_later = price_15min
        signal.max_price_after = max_price
        signal.min_price_after = min_price
        
        # 计算收益
        return_5min = (price_5min - entry_price) / entry_price * 100
        return_15min = (price_15min - entry_price) / entry_price * 100
        max_return = (max_price - entry_price) / entry_price * 100
        max_drawdown = (min_price - entry_price) / entry_price * 100
        
        # 质量评估
        is_profitable_5min = return_5min > 0
        is_profitable_15min = return_15min > 0
        has_good_risk_reward = max_return > abs(max_drawdown) * 2  # 收益风险比 > 2
        
        result = {
            'trigger_type': signal.trigger_type,
            'confidence': signal.confidence,
            'return_5min': return_5min,
            'return_15min': return_15min,
            'max_return': max_return,
            'max_drawdown': max_drawdown,
            'is_profitable_5min': is_profitable_5min,
            'is_profitable_15min': is_profitable_15min,
            'has_good_risk_reward': has_good_risk_reward,
            'quality_score': self._calculate_quality_score(
                return_5min, return_15min, max_return, max_drawdown
            )
        }
        
        self.validated_signals.append(signal)
        
        return result
    
    def _calculate_quality_score(
        self,
        return_5min: float,
        return_15min: float,
        max_return: float,
        max_drawdown: float
    ) -> float:
        """
        计算买点质量分数
        
        高质量买点 = 收益高 + 风险低 + 见效快
        """
        # 收益得分（15分钟收益）
        profit_score = max(0, min(50, return_15min * 5))  # 最高50分
        
        # 风险得分（最大回撤）
        risk_score = max(0, 30 - abs(max_drawdown) * 3)  # 最高30分
        
        # 速度得分（5分钟收益vs15分钟收益）
        if return_15min > 0:
            speed_ratio = return_5min / return_15min if return_15min != 0 else 0
            speed_score = min(20, speed_ratio * 20)  # 最高20分
        else:
            speed_score = 0
        
        return profit_score + risk_score + speed_score
    
    # ==================== 统计报告 ====================
    
    def generate_report(self) -> Dict:
        """生成触发信号统计报告"""
        if not self.validated_signals:
            return {'error': 'No validated signals'}
        
        # 按触发类型分组
        by_type = {}
        for sig in self.validated_signals:
            t = sig.trigger_type
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(sig)
        
        # 计算各类型的统计
        stats = {}
        for trigger_type, signals in by_type.items():
            returns_5min = []
            returns_15min = []
            max_returns = []
            max_drawdowns = []
            
            for sig in signals:
                if sig.price_5min_later and sig.price:
                    returns_5min.append((sig.price_5min_later - sig.price) / sig.price * 100)
                if sig.price_15min_later and sig.price:
                    returns_15min.append((sig.price_15min_later - sig.price) / sig.price * 100)
                if sig.max_price_after and sig.price:
                    max_returns.append((sig.max_price_after - sig.price) / sig.price * 100)
                if sig.min_price_after and sig.price:
                    max_drawdowns.append((sig.min_price_after - sig.price) / sig.price * 100)
            
            stats[trigger_type] = {
                'count': len(signals),
                'avg_return_5min': sum(returns_5min) / len(returns_5min) if returns_5min else 0,
                'avg_return_15min': sum(returns_15min) / len(returns_15min) if returns_15min else 0,
                'avg_max_return': sum(max_returns) / len(max_returns) if max_returns else 0,
                'avg_max_drawdown': sum(max_drawdowns) / len(max_drawdowns) if max_drawdowns else 0,
                'win_rate_5min': len([r for r in returns_5min if r > 0]) / len(returns_5min) * 100 if returns_5min else 0,
                'win_rate_15min': len([r for r in returns_15min if r > 0]) / len(returns_15min) * 100 if returns_15min else 0,
            }
        
        return {
            'total_signals': len(self.signals),
            'validated_signals': len(self.validated_signals),
            'by_type': stats
        }


# ==================== 单元测试 ====================

def test_trigger_validator():
    """单元测试：动态买点验证器"""
    print("\n" + "=" * 60)
    print("📊 TriggerValidator 单元测试")
    print("=" * 60)
    
    validator = TriggerValidator()
    
    # 测试1：引力弹弓触发
    print("\n[Test 1] 引力弹弓(VWAP反弹)触发测试")
    sig1 = validator.check_vwap_bounce(
        stock_code='600000.SH',
        current_price=10.15,
        vwap=10.10,
        recent_mfe_list=[1.5, 2.5, 3.0],  # MFE递增
        price_history=[10.05, 10.08, 10.12, 10.15],  # 有回踩
        timestamp=datetime.now()
    )
    if sig1:
        print(f"  ✅ 触发成功: {sig1.trigger_type}, 置信度={sig1.confidence:.2f}")
        print(f"     详情: VWAP={sig1.details['vwap']}, MFE={sig1.details['recent_mfe_avg']:.2f}")
    else:
        print("  ❌ 未触发")
    
    # 测试2：阶梯突破触发
    print("\n[Test 2] 阶梯突破触发测试")
    # 构造横盘数据
    base_price = 10.0
    price_history = [base_price + 0.005 * i for i in range(-7, 8)]  # 振幅约1.5%
    price_history.append(10.20)  # 当前价格突破
    
    sig2 = validator.check_stair_breakout(
        stock_code='000001.SZ',
        current_price=10.20,
        price_history=price_history,
        volume_ratio=2.0,
        current_slope=0.02,  # 斜率
        timestamp=datetime.now()
    )
    if sig2:
        print(f"  ✅ 触发成功: {sig2.trigger_type}, 置信度={sig2.confidence:.2f}")
        print(f"     详情: 突破幅度={sig2.details['breakout_pct']:.2f}%, 量比={sig2.details['volume_ratio']:.2f}")
    else:
        print("  ❌ 未触发")
    
    # 测试3：真空点火触发
    print("\n[Test 3] 真空点火触发测试")
    sig3 = validator.check_vacuum_ignition(
        stock_code='300001.SZ',
        current_price=11.50,
        prev_close=10.0,
        volume_ratio=5.0,  # 高量比
        current_mfe=2.5,   # 高MFE
        recent_volume_ratios=[1.0, 1.2, 0.8, 1.1, 1.0],  # 之前量比较低
        timestamp=datetime.now()
    )
    if sig3:
        print(f"  ✅ 触发成功: {sig3.trigger_type}, 置信度={sig3.confidence:.2f}")
        print(f"     详情: 量比={sig3.details['volume_ratio']:.2f}, 量比跳变={sig3.details['ratio_jump']:.2f}x")
    else:
        print("  ❌ 未触发")
    
    print("\n" + "=" * 60)
    print(f"✅ TriggerValidator 单元测试完成, 共{len(validator.signals)}个触发信号")
    print("=" * 60)


if __name__ == "__main__":
    test_trigger_validator()
