#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件生命周期分析器
CTO指令：从静态标签升级到动态轨迹研究

核心功能：
1. 定义事件生命周期：起点t_start、终点t_end
2. 真起爆：推升时长T_up、空间Δp_up、资金轨迹、效率结构
3. 骗炮：欺骗时长T_fake、幅度Δp_fake、坠落T_down、资金反转
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List
from datetime import datetime


@dataclass
class EventInterval:
    """事件区间"""
    t_start: str          # 起点时间 (HH:MM:SS)
    t_end: str            # 终点时间
    t_start_idx: int      # 起点索引
    t_end_idx: int        # 终点索引
    
    # 价格指标
    price_start: float    # 起点价格
    price_end: float      # 终点价格
    price_peak: float     # 区间内最高价
    price_trough: float   # 区间内最低价
    
    # 时间指标
    duration_minutes: float  # 持续时长（分钟）
    
    # 涨幅指标（相对pre_close）
    change_start_pct: float   # 起点涨幅
    change_end_pct: float     # 终点涨幅
    change_peak_pct: float    # 最高点涨幅
    max_drawdown_pct: float   # 最大回撤
    
    # 资金指标
    total_inflow: float       # 总净流入
    avg_flow_5min: float      # 平均5分钟流
    max_flow_5min: float      # 最大5分钟流
    sustain_ratio: float      # 持续性比率(15min/5min)
    
    # 效率指标
    price_efficiency: float   # 价格效率：涨幅/资金流


@dataclass
class TrueBreakoutEvent:
    """真起爆事件"""
    event_type: str = "真起爆"
    
    # 推升阶段 [t_start, t_end]
    push_phase: Optional[EventInterval] = None
    
    # 维持阶段（可选）
    sustain_phase: Optional[EventInterval] = None
    
    # 整体统计
    total_duration: float = 0.0        # 总时长
    total_change_pct: float = 0.0      # 总涨幅
    total_inflow: float = 0.0          # 总资金流入
    
    # 结构特征
    is_gradual_push: bool = False      # 是否阶梯式推升
    has_second_wave: bool = False      # 是否有第二波攻击
    
    
@dataclass  
class TrapEvent:
    """骗炮事件"""
    event_type: str = "骗炮"
    
    # 欺骗阶段 [t_fake, t_peak]
    fake_phase: Optional[EventInterval] = None
    
    # 坠落阶段 [t_peak, t_fail]
    fall_phase: Optional[EventInterval] = None
    
    # 关键时间点
    t_fake: str = ""      # 第一次看起来像机会的时刻
    t_peak: str = ""      # 冲高最高点时刻
    t_fail: str = ""      # 确认失败时刻
    
    # 欺骗指标
    fake_duration: float = 0.0         # 欺骗时长（分钟）
    fake_change_pct: float = 0.0       # 欺骗幅度
    
    # 坠落指标
    fall_duration: float = 0.0         # 坠落时长
    fall_change_pct: float = 0.0       # 坠落幅度（负值）
    
    # 资金反转
    flow_reversal_time: str = ""       # 资金由正转负时刻
    reversal_speed: float = 0.0        # 反转速度


class EventLifecycleAnalyzer:
    """事件生命周期分析器"""
    
    def __init__(self,
                 stock_code: str = None,                # 新增：股票代码用于ratio化
                 breakout_threshold: float = 4.0,       # 基础阈值从5.0降到4.0
                 trap_reversal_threshold: float = -1.5, # 基础阈值从-3.0降到-1.5
                 max_drawdown_threshold: float = 3.0,   # 基础阈值从5.0降到3.0
                 trap_final_change_threshold: float = 8.0,  # 🔥 P1: 骗炮判定最终涨幅阈值
                 sustain_duration: int = 15):

        # 基础阈值
        base_breakout = breakout_threshold
        base_trap = trap_reversal_threshold
        base_max_dd = max_drawdown_threshold

        # ratio化：按流通市值动态调整（小盘波动大，阈值降低；大盘波动小，阈值提高）
        if stock_code:
            try:
                circ_mv = self._get_circ_mv(stock_code)
                if circ_mv < 30e9:       # 小盘<30亿
                    multiplier = 0.8
                elif circ_mv < 80e9:     # 中盘30-80亿
                    multiplier = 1.0
                else:                    # 大盘>80亿
                    multiplier = 1.2
            except:
                multiplier = 1.0
        else:
            multiplier = 1.0

        self.breakout_threshold = base_breakout * multiplier
        self.trap_reversal_threshold = base_trap * multiplier
        self.max_drawdown_threshold = base_max_dd * multiplier
        self.trap_final_change_threshold = trap_final_change_threshold  # 🔥 P1: 骗炮最终涨幅阈值
        self.sustain_duration = sustain_duration
        self.multiplier = multiplier  # 保存用于调试

    def _get_circ_mv(self, stock_code: str) -> float:
        """获取流通市值（亿元）"""
        try:
            from logic.services.data_service import data_service
            # 尝试获取流通市值
            daily_data = data_service.get_daily_data(stock_code, datetime.now().strftime('%Y-%m-%d'))
            if daily_data is not None and len(daily_data) > 0:
                # 流通市值字段可能在不同数据源中名称不同
                for col in ['circ_mv', 'mktcap', '流通市值', '总市值']:
                    if col in daily_data.columns:
                        return float(daily_data[col].iloc[0]) * 1e8  # 转换为元
            # 如果获取失败，返回默认值（中盘）
            return 50e9
        except Exception as e:
            print(f"获取流通市值失败 {stock_code}: {e}")
            return 50e9  # 默认中盘

    def analyze_day(self, df: pd.DataFrame, pre_close: float) -> dict:
        """
        分析单日数据，提取所有事件
        
        Args:
            df: DataFrame包含['time', 'price', 'true_change_pct', 'flow_5min', 'flow_15min']
            pre_close: 昨收价
            
        Returns:
            dict: {'breakouts': [...], 'traps': [...]}
        """
        if df.empty or pre_close <= 0:
            return {'breakouts': [], 'traps': []}
        
        # 确保数据按时间排序
        df = df.copy()
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        
        events = {
            'breakouts': [],
            'traps': []
        }
        
        # 1. 寻找所有潜在起爆点（涨幅突破阈值）
        breakout_indices = self._find_breakout_points(df)
        
        # 2. 对每个起爆点，判断是真起爆还是骗炮
        for idx in breakout_indices:
            event = self._classify_event(df, idx, pre_close)
            
            if isinstance(event, TrueBreakoutEvent):
                events['breakouts'].append(event)
            elif isinstance(event, TrapEvent):
                events['traps'].append(event)
        
        return events
    
    def _find_breakout_points(self, df: pd.DataFrame) -> List[int]:
        """寻找所有潜在起爆点"""
        breakout_indices = []

        # 条件：涨幅首次突破阈值，且5分钟流为正
        for i in range(1, len(df)):
            if (df.loc[i, 'true_change_pct'] >= self.breakout_threshold and
                df.loc[i-1, 'true_change_pct'] < self.breakout_threshold and
                df.loc[i, 'flow_5min'] > -5e5):  # ← 放宽：允许轻微负流-50万
                breakout_indices.append(i)

        return breakout_indices
    
    def _classify_event(self, df: pd.DataFrame, start_idx: int, pre_close: float):
        """
        分类事件：真起爆 vs 骗炮
        
        判断逻辑：
        - 真起爆：突破后维持高位，回撤<阈值，资金持续
        - 骗炮：突破后快速回落，回撤>阈值，资金反转
        """
        # 从start_idx往后观察
        df_slice = df.iloc[start_idx:].copy()
        if len(df_slice) < 10:  # 数据不足
            return None
        
        start_price = df_slice.iloc[0]['price']
        start_change = df_slice.iloc[0]['true_change_pct']
        start_time = df_slice.iloc[0]['time']
        
        # 寻找区间内最高点
        peak_idx = df_slice['true_change_pct'].idxmax()
        peak_change = df_slice.loc[peak_idx, 'true_change_pct']
        peak_price = df_slice.loc[peak_idx, 'price']
        peak_time = df_slice.loc[peak_idx, 'time']
        
        # 计算从起点到最高点的回撤
        drawdown = peak_change - start_change
        
        # 观察后续走势
        # 如果在最高点之后出现大幅回落，判定为骗炮
        after_peak = df_slice[df_slice['time'] > peak_time]
        
        is_trap = False
        fail_time = None
        fail_price = None
        
        if len(after_peak) > 0:
            # 检查是否回落超过阈值
            min_after_peak = after_peak['true_change_pct'].min()
            drawdown_from_peak = peak_change - min_after_peak
            
            # 骗炮判定：回撤>阈值 且 收盘涨幅明显低于高点（至少回撤一半以上）
            final_change = df_slice['true_change_pct'].iloc[-1]
            pullback_ratio = (peak_change - final_change) / drawdown_from_peak if drawdown_from_peak > 0 else 0

            # 条件：回撤>阈值 且 收盘相对于高点的回撤比例>30% 且 最终涨幅<阈值
            if (drawdown_from_peak >= abs(self.trap_reversal_threshold) and
                pullback_ratio > 0.3 and   # 回撤比例阈值
                final_change < self.trap_final_change_threshold):  # 🔥 P1: 使用参数替代硬编码
                is_trap = True
                fail_idx = after_peak['true_change_pct'].idxmin()
                fail_time = after_peak.loc[fail_idx, 'time']
                fail_price = after_peak.loc[fail_idx, 'price']
        
        # 提取区间数据
        if is_trap:
            # 骗炮事件
            end_idx = df.index[df['time'] == fail_time].tolist()[0] if fail_time else len(df) - 1
            interval_df = df.iloc[start_idx:end_idx+1]
            
            fake_interval = self._create_interval(df, start_idx, end_idx, pre_close)
            
            return TrapEvent(
                fake_phase=fake_interval,
                t_fake=start_time.strftime('%H:%M:%S'),
                t_peak=peak_time.strftime('%H:%M:%S'),
                t_fail=fail_time.strftime('%H:%M:%S') if fail_time else "",
                fake_duration=(peak_time - start_time).total_seconds() / 60,
                fake_change_pct=peak_change - start_change,
                fall_duration=(fail_time - peak_time).total_seconds() / 60 if fail_time else 0,
                fall_change_pct=(fail_price - peak_price) / pre_close * 100 if fail_price else 0
            )
        else:
            # 真起爆事件
            # 找到推升阶段终点（资金衰竭或横盘）
            end_idx = self._find_push_end(df_slice, start_idx)
            push_interval = self._create_interval(df, start_idx, end_idx, pre_close)
            
            return TrueBreakoutEvent(
                push_phase=push_interval,
                total_duration=push_interval.duration_minutes,
                total_change_pct=push_interval.change_end_pct - push_interval.change_start_pct,
                total_inflow=push_interval.total_inflow,
                is_gradual_push=self._check_gradual_push(df, start_idx, end_idx)
            )
    
    def _find_push_end(self, df_slice: pd.DataFrame, start_idx: int) -> int:
        """找到推升阶段终点"""
        # 逻辑：资金持续为负或价格大幅回撤时结束
        for i in range(10, len(df_slice)):
            recent_df = df_slice.iloc[i-5:i]
            
            # 条件1：连续5分钟资金为负
            if (recent_df['flow_5min'] < 0).all():
                return start_idx + i
            
            # 条件2：从高点回撤超过阈值
            peak_so_far = df_slice.iloc[:i]['true_change_pct'].max()
            current_change = df_slice.iloc[i]['true_change_pct']
            if peak_so_far - current_change >= self.max_drawdown_threshold:
                return start_idx + i
        
        return start_idx + len(df_slice) - 1
    
    def _create_interval(self, df: pd.DataFrame, start_idx: int, end_idx: int, 
                        pre_close: float) -> EventInterval:
        """创建事件区间对象"""
        interval_df = df.iloc[start_idx:end_idx+1]
        
        start_price = interval_df.iloc[0]['price']
        end_price = interval_df.iloc[-1]['price']
        peak_price = interval_df['price'].max()
        trough_price = interval_df['price'].min()
        
        start_time = interval_df.iloc[0]['time']
        end_time = interval_df.iloc[-1]['time']
        duration = (end_time - start_time).total_seconds() / 60
        
        # 计算回撤
        cummax = interval_df['true_change_pct'].cummax()
        drawdowns = cummax - interval_df['true_change_pct']
        max_drawdown = drawdowns.max()
        
        # 资金统计
        total_inflow = interval_df['flow_5min'].sum()
        avg_flow = interval_df['flow_5min'].mean()
        max_flow = interval_df['flow_5min'].max()
        
        # 持续性比率（如果有15分钟数据）
        if 'flow_15min' in interval_df.columns:
            sustain = interval_df['flow_15min'].iloc[-1] / interval_df['flow_5min'].iloc[-1] \
                      if interval_df['flow_5min'].iloc[-1] != 0 else 0
        else:
            sustain = 0
        
        # 效率：每百万资金推动的价格变化
        price_change = end_price - start_price
        efficiency = price_change / (total_inflow / 1e6) if total_inflow != 0 else 0
        
        return EventInterval(
            t_start=start_time.strftime('%H:%M:%S'),
            t_end=end_time.strftime('%H:%M:%S'),
            t_start_idx=start_idx,
            t_end_idx=end_idx,
            price_start=start_price,
            price_end=end_price,
            price_peak=peak_price,
            price_trough=trough_price,
            duration_minutes=duration,
            change_start_pct=(start_price - pre_close) / pre_close * 100,
            change_end_pct=(end_price - pre_close) / pre_close * 100,
            change_peak_pct=(peak_price - pre_close) / pre_close * 100,
            max_drawdown_pct=max_drawdown,
            total_inflow=total_inflow,
            avg_flow_5min=avg_flow,
            max_flow_5min=max_flow,
            sustain_ratio=sustain,
            price_efficiency=efficiency
        )
    
    def _check_gradual_push(self, df: pd.DataFrame, start_idx: int, end_idx: int) -> bool:
        """检查是否是阶梯式推升（而非直线拉升）"""
        interval_df = df.iloc[start_idx:end_idx+1]
        
        # 简单判断：看价格变化是否有明显的平台期
        price_changes = interval_df['price'].diff().abs()
        # 如果有超过3次小于0.1%的变化，认为是阶梯式
        small_changes = (price_changes < 0.001 * interval_df['price'].mean()).sum()
        
        return small_changes >= 3


# ==================== 测试代码 ====================
if __name__ == "__main__":
    print("事件生命周期分析器测试")
    print("="*60)
    
    # 创建测试数据（模拟网宿科技2026-01-26）
    import numpy as np
    
    np.random.seed(42)
    n_ticks = 100
    
    # 模拟数据：早盘平稳，午后起爆
    times = pd.date_range('09:30:00', periods=n_ticks, freq='3S')
    
    # 价格：从+2%起步，14:19左右冲到+20%
    base_price = 11.48
    price_changes = np.concatenate([
        np.random.normal(0.02, 0.005, 60),  # 早盘震荡
        np.linspace(0.02, 0.18, 20),         # 起爆推升
        np.random.normal(0.18, 0.002, 20)    # 封板横盘
    ])
    prices = base_price * (1 + price_changes)
    
    # 资金流：起爆时放量
    flows = np.concatenate([
        np.random.normal(1e6, 5e5, 60),      # 早盘正常
        np.random.normal(5e7, 2e7, 20),      # 起爆放量
        np.random.normal(1e6, 3e5, 20)       # 封板缩量
    ])
    
    df_test = pd.DataFrame({
        'time': times.strftime('%H:%M:%S'),
        'price': prices,
        'true_change_pct': price_changes * 100,
        'flow_5min': flows,
        'flow_15min': flows * 3  # 简化
    })
    
    # 分析
    analyzer = EventLifecycleAnalyzer()
    events = analyzer.analyze_day(df_test, base_price)
    
    print(f"\n检测到 {len(events['breakouts'])} 个真起爆事件")
    print(f"检测到 {len(events['traps'])} 个骗炮事件")
    
    if events['breakouts']:
        evt = events['breakouts'][0]
        print(f"\n真起爆事件详情:")
        print(f"  推升时长: {evt.push_phase.duration_minutes:.1f}分钟")
        print(f"  起点涨幅: {evt.push_phase.change_start_pct:.2f}%")
        print(f"  终点涨幅: {evt.push_phase.change_end_pct:.2f}%")
        print(f"  总资金流入: {evt.push_phase.total_inflow/1e6:.1f}M")
        print(f"  价格效率: {evt.push_phase.price_efficiency:.6f}")
    
    print("\n" + "="*60)
