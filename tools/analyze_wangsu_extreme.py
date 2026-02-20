#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网宿科技极致拆分分析器 (Phase 0)
CTO指令：把网宿1-26/2-13拆到极致，产出标杆报告

分析维度：
1. 事件生命周期（T_fake/T_up/T_down、Δp_fake/Δp_up/Δp_down、资金ratio路径）
2. 可交易窗口：人可上车节点的收益/回撤分布
3. 环境条件：resonance_score、market_sentiment、risk_score
4. 事件后T+1/T+2/T+3走势结果
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.services.data_service import data_service
from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.rolling_metrics import RollingFlowCalculator
from logic.event_lifecycle_analyzer import EventLifecycleAnalyzer


class WangsuExtremeAnalyzer:
    """网宿科技极致拆分分析器"""
    
    def __init__(self):
        self.code = "300017"
        self.name = "网宿科技"
        self.true_date = "2026-01-26"
        self.trap_date = "2026-02-13"
        
    def analyze_case(self, date: str, label: str) -> dict:
        """分析单个案例"""
        print(f"\n{'='*80}")
        print(f"分析 {self.name} {date} ({label})")
        print(f"{'='*80}")
        
        result = {
            'code': self.code,
            'name': self.name,
            'date': date,
            'label': label,
        }
        
        # 1. 加载Tick数据
        df_ticks = self._load_tick_data(date)
        if df_ticks is None:
            return result
        
        result['tick_count'] = len(df_ticks)
        result['pre_close'] = df_ticks['pre_close'].iloc[0]
        
        # 2. 事件生命周期分析
        lifecycle = self._analyze_lifecycle(df_ticks, result['pre_close'])
        result['lifecycle'] = lifecycle
        
        # 3. 可交易窗口分析
        tradable = self._analyze_tradable_windows(df_ticks, lifecycle)
        result['tradable_windows'] = tradable
        
        # 4. 环境条件分析
        environment = self._analyze_environment(date)
        result['environment'] = environment
        
        # 5. 维持能力分析 (Phase 1核心)
        sustain_ability = self._analyze_sustain_ability(df_ticks, lifecycle)
        result['sustain_ability'] = sustain_ability
        
        # 6. 事件后走势分析
        post_event = self._analyze_post_event(date)
        result['post_event'] = post_event
        
        return result
    
    def _load_tick_data(self, date: str) -> pd.DataFrame:
        """加载Tick数据"""
        formatted_code = data_service._format_code(self.code)
        pre_close = data_service.get_pre_close(self.code, date)
        
        if pre_close <= 0:
            print(f"❌ 无法获取昨收价")
            return None
        
        start_time = date.replace('-', '') + '093000'
        end_time = date.replace('-', '') + '150000'
        
        provider = QMTHistoricalProvider(
            stock_code=formatted_code,
            start_time=start_time,
            end_time=end_time,
            period='tick'
        )
        
        tick_count = provider.get_tick_count()
        if tick_count == 0:
            print(f"❌ 无Tick数据")
            return None
        
        print(f"✅ 加载 {tick_count} 条Tick数据，昨收: {pre_close}")
        
        # 计算资金流
        calc = RollingFlowCalculator(windows=[1, 5, 15])
        results = []
        last_tick = None
        
        for tick in provider.iter_ticks():
            metrics = calc.add_tick(tick, last_tick)
            true_change = (tick['lastPrice'] - pre_close) / pre_close * 100
            
            results.append({
                'time': datetime.fromtimestamp(int(tick['time']) / 1000),
                'price': tick['lastPrice'],
                'true_change_pct': true_change,
                'flow_1min': metrics.flow_1min.total_flow,
                'flow_5min': metrics.flow_5min.total_flow,
                'flow_15min': metrics.flow_15min.total_flow,
                'pre_close': pre_close,
            })
            last_tick = tick
        
        return pd.DataFrame(results)
    
    def _analyze_lifecycle(self, df: pd.DataFrame, pre_close: float) -> dict:
        """分析事件生命周期"""
        analyzer = EventLifecycleAnalyzer(
            breakout_threshold=5.0,
            trap_reversal_threshold=3.0,
            max_drawdown_threshold=5.0
        )
        
        events = analyzer.analyze_day(df, pre_close)
        
        lifecycle = {
            'max_change_pct': df['true_change_pct'].max(),
            'min_change_pct': df['true_change_pct'].min(),
            'final_change_pct': df['true_change_pct'].iloc[-1],
            'total_inflow_yi': df['flow_5min'].sum() / 1e8,  # 单位：亿元
        }
        
        # 真起爆事件
        if events['breakouts']:
            evt = events['breakouts'][0]
            if evt.push_phase:
                # 资金单位转换为亿元（1亿元 = 1e8元）
                total_inflow_yi = evt.push_phase.total_inflow / 1e8
                max_flow_yi = evt.push_phase.max_flow_5min / 1e8
                
                lifecycle['breakout'] = {
                    't_start': evt.push_phase.t_start,
                    't_end': evt.push_phase.t_end,
                    'warmup_duration': evt.push_phase.duration_minutes,  # 真起爆用warmup_duration
                    'change_start_pct': evt.push_phase.change_start_pct,
                    'change_end_pct': evt.push_phase.change_end_pct,
                    'change_peak_pct': evt.push_phase.change_peak_pct,
                    'max_drawdown_pct': evt.push_phase.max_drawdown_pct,
                    'total_inflow_yi': total_inflow_yi,  # 单位：亿元
                    'max_flow_5min_yi': max_flow_yi,  # 单位：亿元
                    'sustain_ratio': evt.push_phase.sustain_ratio,
                    'efficiency': evt.push_phase.price_efficiency,
                    'is_gradual_push': evt.is_gradual_push,
                }
                print(f"\n📈 真起爆推升阶段:")
                print(f"   时间: {evt.push_phase.t_start} -> {evt.push_phase.t_end}")
                print(f"   推升时长: {evt.push_phase.duration_minutes:.1f}分钟")
                print(f"   涨幅: {evt.push_phase.change_start_pct:.2f}% -> {evt.push_phase.change_end_pct:.2f}%")
                print(f"   资金流入: {total_inflow_yi:.2f}亿元")
        
        # 骗炮事件
        if events['traps']:
            evt = events['traps'][0]
            if evt.fake_phase:
                lifecycle['trap'] = {
                    't_fake': evt.t_fake,
                    't_peak': evt.t_peak,
                    't_fail': evt.t_fail,
                    'fake_duration': evt.fake_duration,  # 骗炮用fake_duration
                    'fake_change_pct': evt.fake_change_pct,
                    'fall_duration': evt.fall_duration,
                    'fall_change_pct': evt.fall_change_pct,
                }
                print(f"\n📉 骗炮欺骗阶段:")
                print(f"   起点: {evt.t_fake}, 高点: {evt.t_peak}, 失败: {evt.t_fail}")
                print(f"   欺骗时长: {evt.fake_duration:.1f}分钟, 幅度: {evt.fake_change_pct:.2f}%")
                print(f"   坠落时长: {evt.fall_duration:.1f}分钟, 幅度: {evt.fall_change_pct:.2f}%")
        
        return lifecycle
    
    def _analyze_tradable_windows(self, df: pd.DataFrame, lifecycle: dict) -> dict:
        """分析可交易窗口"""
        print(f"\n🎯 可交易窗口分析:")
        
        tradable = {
            'entry_points': [],
            'pnl_distribution': {}
        }
        
        # 模拟不同入场时机的收益
        # 以突破5%为信号起点
        signal_points = df[df['true_change_pct'] >= 5.0].index.tolist()
        
        if not signal_points:
            return tradable
        
        signal_idx = signal_points[0]
        signal_price = df.loc[signal_idx, 'price']
        
        # 模拟在信号后1min/3min/5min/10min入场
        entry_delays = [1, 3, 5, 10]  # 分钟
        
        for delay in entry_delays:
            entry_idx = signal_idx + delay * 20  # 约20个tick/分钟
            if entry_idx >= len(df):
                continue
            
            entry_price = df.loc[entry_idx, 'price']
            entry_time = df.loc[entry_idx, 'time'].strftime('%H:%M:%S')
            
            # 计算持有到收盘的收益
            exit_price = df['price'].iloc[-1]
            pnl_pct = (exit_price - entry_price) / entry_price * 100
            
            # 计算期间最大回撤
            hold_df = df.iloc[entry_idx:]
            cummax = hold_df['price'].cummax()
            drawdowns = (cummax - hold_df['price']) / cummax * 100
            max_drawdown = drawdowns.max()
            
            tradable['entry_points'].append({
                'delay_minutes': delay,
                'entry_time': entry_time,
                'entry_price': entry_price,
                'pnl_pct': pnl_pct,
                'max_drawdown_pct': max_drawdown,
            })
            
            print(f"   信号后{delay}分钟入场 ({entry_time}):")
            print(f"      入场价: {entry_price:.2f}, 收盘收益: {pnl_pct:+.2f}%, 最大回撤: {max_drawdown:.2f}%")
        
        # 收益分布统计
        if tradable['entry_points']:
            pnls = [e['pnl_pct'] for e in tradable['entry_points']]
            tradable['pnl_distribution'] = {
                'min': min(pnls),
                'max': max(pnls),
                'mean': np.mean(pnls),
            }
        
        return tradable
    
    def _analyze_environment(self, date: str) -> dict:
        """分析环境条件 - Phase 1增强版"""
        print(f"\n🌍 环境条件分析 (Phase 1增强版):")
        
        environment = {
            'date': date,
            'resonance_score': None,
            'market_sentiment': None,
            'risk_score': None,
            'environment_score': 0.0,  # 综合环境评分
        }
        
        # 1. 加载市场情绪数据（支持多种日期格式）
        sentiment_loaded = False
        sentiment_path = PROJECT_ROOT / "config" / "market_sentiment.json"
        if sentiment_path.exists():
            try:
                with open(sentiment_path, 'r', encoding='utf-8') as f:
                    sentiment_data = json.load(f)
                
                # 尝试多种日期格式匹配
                date_formats = [date, date.replace('-', ''), f"{date.replace('-', '')[:8]}"]
                
                for date_fmt in date_formats:
                    if date_fmt in sentiment_data:
                        environment['market_sentiment'] = sentiment_data[date_fmt]
                        sentiment_info = sentiment_data[date_fmt]
                        sentiment_score = sentiment_info.get('sentiment_score', 0)
                        limit_up = sentiment_info.get('limit_up_count', 0)
                        limit_down = sentiment_info.get('limit_down_count', 0)
                        
                        print(f"   市场情绪: {sentiment_score:.2f} [涨停={limit_up}, 跌停={limit_down}]")
                        sentiment_loaded = True
                        break
                
                if not sentiment_loaded:
                    # 使用最近日期的情绪数据作为回退
                    available_dates = list(sentiment_data.keys())
                    if available_dates:
                        latest_date = max(available_dates)
                        environment['market_sentiment'] = sentiment_data[latest_date]
                        print(f"   市场情绪(最近): {sentiment_data[latest_date].get('sentiment_score', 0):.2f} (日期: {latest_date})")
                        sentiment_loaded = True
                        
            except Exception as e:
                print(f"   ⚠️ 市场情绪加载失败: {e}")
        
        if not sentiment_loaded:
            print(f"   市场情绪: [数据缺失]")
        
        # 2. 集成WindFilter获取板块共振分数
        resonance_loaded = False
        try:
            # 延迟导入，避免循环依赖
            from logic.strategies.wind_filter import WindFilter
            
            wind_filter = WindFilter()
            resonance_result = wind_filter.check_sector_resonance(self.code)
            
            environment['resonance_score'] = resonance_result.get('resonance_score', 0)
            environment['resonance_details'] = {
                'is_resonance': resonance_result.get('is_resonance', False),
                'limit_up_count': resonance_result.get('limit_up_count', 0),
                'breadth': resonance_result.get('breadth', 0),
                'passed_conditions': resonance_result.get('passed_conditions', [])
            }
            
            resonance_score = environment['resonance_score']
            limit_up_count = environment['resonance_details']['limit_up_count']
            breadth_pct = environment['resonance_details']['breadth'] * 100
            passed_conditions = environment['resonance_details']['passed_conditions']
            
            print(f"   板块共振: {resonance_score:.2f} [涨停={limit_up_count}, 上涨={breadth_pct:.1f}%, 条件={','.join(passed_conditions) if passed_conditions else '无'}]")
            resonance_loaded = True
            
        except ImportError as e:
            print(f"   ⚠️ WindFilter导入失败: {e}")
        except Exception as e:
            print(f"   ⚠️ WindFilter计算失败: {e}")
        
        if not resonance_loaded:
            print(f"   板块共振: [计算失败，使用占位值0.5]")
            environment['resonance_score'] = 0.5
        
        # 3. 风险评分（占位实现）
        # TODO: 集成RiskService或TrapDetector
        environment['risk_score'] = 0.5  # 默认中等风险
        print(f"   风险评分: {environment['risk_score']:.2f} [占位实现]")
        
        # 4. 计算综合环境评分（0-1）
        # 权重：共振分数40%，市场情绪40%，风险评分20%（风险越高分数越低）
        sentiment_score = 0
        if environment['market_sentiment'] and 'sentiment_score' in environment['market_sentiment']:
            sentiment_score = environment['market_sentiment']['sentiment_score']
        elif environment['market_sentiment'] and isinstance(environment['market_sentiment'], dict):
            # 尝试其他可能的键名
            for key in ['score', 'value', 'rating']:
                if key in environment['market_sentiment']:
                    sentiment_score = environment['market_sentiment'][key]
                    break
        
        resonance_score = environment['resonance_score'] or 0.5
        risk_score = environment['risk_score'] or 0.5
        
        # 风险分数需要反转：风险越高，环境分越低
        risk_adjusted = 1.0 - abs(risk_score - 0.5) * 2  # 0.5风险得1分，0或1风险得0分
        
        environment['environment_score'] = (
            resonance_score * 0.4 + 
            sentiment_score * 0.4 + 
            risk_adjusted * 0.2
        )
        
        print(f"   综合环境分: {environment['environment_score']:.2f}")
        
        return environment
    
    def _analyze_sustain_ability(self, df: pd.DataFrame, lifecycle: dict) -> dict:
        """
        分析维持能力指标 - Phase 1核心功能
        
        核心指标：
        1. 时间维度：高位维持时长（价格保持在推升结束价-2%以上的时间）
        2. 强度维度：维持期间平均资金流入（亿元/5min）
        3. 稳定性维度：价格波动率（维持期间价格标准差）
        4. 综合得分：加权维持能力评分（0-1）
        
        Args:
            df: Tick数据DataFrame
            lifecycle: 事件生命周期分析结果
        
        Returns:
            dict: 维持能力分析结果
        """
        print(f"\n📊 维持能力分析 (Phase 1核心):")
        
        sustain = {
            'high_level_duration_minutes': 0,  # 高位维持时长（分钟）
            'sustain_strength': 0,  # 维持强度（亿元/5min）
            'price_volatility': 0,  # 价格波动率（%）
            'composite_score': 0,  # 综合维持得分（0-1）
            'sustain_grade': 'Unknown',  # 维持等级
            'details': {},  # 详细分析数据
        }
        
        # 1. 识别事件类型并计算维持能力
        t_breakout = lifecycle.get('breakout', {})
        t_trap = lifecycle.get('trap', {})
        
        if t_breakout:
            # 真起爆：基于推升结束点计算维持能力
            sustain_result = self._calculate_true_breakout_sustain(df, t_breakout)
            sustain.update(sustain_result)
            sustain['sustain_type'] = 'TrueBreakout'
            
        elif t_trap:
            # 骗炮：基于欺骗高点计算维持能力（通常很短）
            sustain_result = self._calculate_trap_sustain(df, t_trap)
            sustain.update(sustain_result)
            sustain['sustain_type'] = 'Trap'
        else:
            print(f"   ⚠️ 未识别到明确事件类型")
            sustain['sustain_type'] = 'Unknown'
        
        # 2. 输出分析结果
        if sustain['high_level_duration_minutes'] > 0:
            print(f"   高位维持时长: {sustain['high_level_duration_minutes']:.1f}分钟")
            print(f"   维持强度: {sustain['sustain_strength']:.3f}亿元/5min")
            print(f"   价格波动率: {sustain['price_volatility']:.2f}%")
            print(f"   综合维持得分: {sustain['composite_score']:.2f}")
            print(f"   维持等级: {sustain['sustain_grade']}")
        else:
            print(f"   ⚠️ 维持能力分析失败或无维持阶段")
        
        return sustain
    
    def _calculate_true_breakout_sustain(self, df: pd.DataFrame, breakout_info: dict) -> dict:
        """计算真起爆维持能力"""
        sustain = {
            'high_level_duration_minutes': 0,
            'sustain_strength': 0,
            'price_volatility': 0,
            'composite_score': 0,
            'sustain_grade': 'Poor',
        }
        
        # 获取推升结束时间点
        push_end_time = breakout_info.get('t_end', '')
        if not push_end_time:
            return sustain
        
        # 找到推升结束点在df中的索引
        push_end_idx = self._find_time_index(df, push_end_time)
        if push_end_idx >= len(df) - 1:
            return sustain
        
        # 推升结束价格（作为维持起点）
        push_end_price = df.loc[push_end_idx, 'price']
        sustain_threshold = push_end_price * 0.98  # -2%阈值
        
        # 提取维持阶段数据（推升结束后）
        sustain_df = df.iloc[push_end_idx:]
        
        # 计算高位维持时长：价格保持在阈值以上的时长
        above_threshold = sustain_df[sustain_df['price'] >= sustain_threshold]
        if len(above_threshold) == 0:
            return sustain
        
        # 时间维度：高位维持时长（分钟）
        # 假设Tick数据约3秒一条（实际可能不同）
        tick_interval_seconds = 3  # 保守估计
        sustain_minutes = len(above_threshold) * tick_interval_seconds / 60
        
        # 强度维度：维持期间平均资金流入（亿元/5min）
        avg_flow = above_threshold['flow_5min'].mean() / 1e8  # 转换为亿元
        
        # 稳定性维度：价格波动率（维持期间价格标准差，%）
        price_volatility = above_threshold['price'].std() / above_threshold['price'].mean() * 100
        
        # 计算综合得分（0-1）
        # 权重：时长50%，强度30%，稳定性20%
        duration_score = min(sustain_minutes / 60, 1.0)  # 60分钟为满分
        strength_score = min(avg_flow / 0.5, 1.0)  # 0.5亿元/5min为满分
        stability_score = 1.0 - min(price_volatility / 10.0, 1.0)  # 波动率<10%为满分
        
        composite_score = (
            duration_score * 0.5 + 
            strength_score * 0.3 + 
            stability_score * 0.2
        )
        
        # 确定维持等级
        if composite_score >= 0.8:
            sustain_grade = 'Excellent'
        elif composite_score >= 0.6:
            sustain_grade = 'Good'
        elif composite_score >= 0.4:
            sustain_grade = 'Fair'
        else:
            sustain_grade = 'Poor'
        
        sustain.update({
            'high_level_duration_minutes': sustain_minutes,
            'sustain_strength': avg_flow,
            'price_volatility': price_volatility,
            'composite_score': composite_score,
            'sustain_grade': sustain_grade,
            'details': {
                'push_end_price': push_end_price,
                'sustain_threshold': sustain_threshold,
                'sustain_start_time': df.loc[push_end_idx, 'time'].strftime('%H:%M:%S'),
                'sustain_end_time': df.loc[above_threshold.index[-1], 'time'].strftime('%H:%M:%S'),
                'duration_score': duration_score,
                'strength_score': strength_score,
                'stability_score': stability_score,
            }
        })
        
        return sustain
    
    def _calculate_trap_sustain(self, df: pd.DataFrame, trap_info: dict) -> dict:
        """计算骗炮维持能力（通常很短）"""
        sustain = {
            'high_level_duration_minutes': 0,
            'sustain_strength': 0,
            'price_volatility': 0,
            'composite_score': 0,
            'sustain_grade': 'Poor',
        }
        
        # 骗炮通常没有真正的维持阶段，但我们可以计算"虚假维持"
        # 找到价格高点
        peak_price = df['price'].max()
        peak_idx = df[df['price'] == peak_price].index[0]
        
        if peak_idx >= len(df) - 1:
            return sustain
        
        # 高点后-2%阈值
        sustain_threshold = peak_price * 0.98
        
        # 高点后的数据
        after_peak_df = df.iloc[peak_idx:]
        
        # 计算"虚假维持"时长
        above_threshold = after_peak_df[after_peak_df['price'] >= sustain_threshold]
        if len(above_threshold) == 0:
            return sustain
        
        tick_interval_seconds = 3
        sustain_minutes = len(above_threshold) * tick_interval_seconds / 60
        
        # 骗炮的维持通常很短，强度低，波动大
        avg_flow = above_threshold['flow_5min'].mean() / 1e8
        price_volatility = above_threshold['price'].std() / above_threshold['price'].mean() * 100
        
        # 骗炮的综合得分通常很低
        duration_score = min(sustain_minutes / 30, 1.0)  # 30分钟为满分（对骗炮更宽松）
        strength_score = min(avg_flow / 0.2, 1.0)  # 0.2亿元/5min为满分
        stability_score = 1.0 - min(price_volatility / 15.0, 1.0)  # 波动率<15%为满分
        
        composite_score = (
            duration_score * 0.4 + 
            strength_score * 0.3 + 
            stability_score * 0.3
        )
        
        # 骗炮的维持等级通常为Poor
        if composite_score >= 0.5:
            sustain_grade = 'Fair'  # 罕见的"强骗炮"
        elif composite_score >= 0.3:
            sustain_grade = 'Weak'
        else:
            sustain_grade = 'Poor'
        
        sustain.update({
            'high_level_duration_minutes': sustain_minutes,
            'sustain_strength': avg_flow,
            'price_volatility': price_volatility,
            'composite_score': composite_score,
            'sustain_grade': sustain_grade,
            'details': {
                'peak_price': peak_price,
                'sustain_threshold': sustain_threshold,
                'peak_time': df.loc[peak_idx, 'time'].strftime('%H:%M:%S'),
                'sustain_end_time': df.loc[above_threshold.index[-1], 'time'].strftime('%H:%M:%S'),
                'is_trap': True,
            }
        })
        
        return sustain
    
    def _find_time_index(self, df: pd.DataFrame, target_time: str) -> int:
        """在DataFrame中查找时间点索引"""
        if not target_time or 'time' not in df.columns:
            return 0
        
        # 标准化时间格式
        if ':' in target_time:
            # 已经是HH:MM:SS格式
            time_str = target_time
        else:
            # 可能是其他格式，尝试转换
            try:
                time_obj = datetime.strptime(target_time, '%H%M%S')
                time_str = time_obj.strftime('%H:%M:%S')
            except:
                return 0
        
        # 在df中查找
        for idx, row in df.iterrows():
            if row['time'].strftime('%H:%M:%S') == time_str:
                return idx
        
        # 如果找不到精确匹配，找最接近的时间
        for idx, row in df.iterrows():
            df_time_str = row['time'].strftime('%H:%M:%S')
            if df_time_str >= time_str:
                return idx
        
        return 0
    
    def _analyze_post_event(self, date: str) -> dict:
        """分析事件后T+1/T+2/T+3走势"""
        print(f"\n📊 事件后走势分析:")
        
        post_event = {
            'event_date': date,
            't1': None,
            't2': None,
            't3': None,
        }
        
        # 使用data_service获取事件日收盘价
        try:
            formatted_code = data_service._format_code(self.code)
            
            # 先获取事件日数据
            df_event = data_service.get_daily_data(self.code, date)
            if df_event is None or len(df_event) == 0:
                print(f"   ⚠️ 无法获取事件日数据")
                return post_event
            
            event_close = df_event['close'].iloc[0]
            event_date = datetime.strptime(date, '%Y-%m-%d')
            
            # T+1
            t1_date = (event_date + timedelta(days=1)).strftime('%Y-%m-%d')
            df_t1 = data_service.get_daily_data(self.code, t1_date)
            if df_t1 is not None and len(df_t1) > 0:
                post_event['t1'] = {
                    'date': t1_date,
                    'open_gap': (df_t1['open'].iloc[0] - event_close) / event_close * 100,
                    'high_change': (df_t1['high'].iloc[0] - event_close) / event_close * 100,
                    'low_change': (df_t1['low'].iloc[0] - event_close) / event_close * 100,
                    'close_change': (df_t1['close'].iloc[0] - event_close) / event_close * 100,
                }
                print(f"   T+1 ({t1_date}):")
                print(f"      开盘跳空: {post_event['t1']['open_gap']:+.2f}%")
                print(f"      收盘涨跌: {post_event['t1']['close_change']:+.2f}%")
            
            # T+2
            t2_date = (event_date + timedelta(days=2)).strftime('%Y-%m-%d')
            df_t2 = data_service.get_daily_data(self.code, t2_date)
            if df_t2 is not None and len(df_t2) > 0:
                post_event['t2'] = {
                    'date': t2_date,
                    'close_change': (df_t2['close'].iloc[0] - event_close) / event_close * 100,
                }
                print(f"   T+2 ({t2_date}): 收盘涨跌 {post_event['t2']['close_change']:+.2f}%")
            
            # T+3
            t3_date = (event_date + timedelta(days=3)).strftime('%Y-%m-%d')
            df_t3 = data_service.get_daily_data(self.code, t3_date)
            if df_t3 is not None and len(df_t3) > 0:
                post_event['t3'] = {
                    'date': t3_date,
                    'close_change': (df_t3['close'].iloc[0] - event_close) / event_close * 100,
                }
                print(f"   T+3 ({t3_date}): 收盘涨跌 {post_event['t3']['close_change']:+.2f}%")
        
        except Exception as e:
            print(f"   ⚠️ 获取日线数据失败: {e}")
        
        return post_event
    
    def generate_report(self, true_result: dict, trap_result: dict):
        """生成对比报告"""
        print(f"\n\n{'='*80}")
        print(f"网宿科技极致拆分报告")
        print(f"真起爆 ({self.true_date}) vs 骗炮 ({self.trap_date})")
        print(f"{'='*80}\n")
        
        # 对比表
        print("【核心指标对比】")
        print("-" * 80)
        print(f"{'指标':<30} {'真起爆 (1-26)':<25} {'骗炮 (2-13)':<25}")
        print("-" * 80)
        
        t_life = true_result.get('lifecycle', {})
        p_life = trap_result.get('lifecycle', {})
        
        print(f"{'当日最高涨幅':<30} {t_life.get('max_change_pct', 0):>+.2f}%{'':<18} {p_life.get('max_change_pct', 0):>+.2f}%")
        print(f"{'当日收盘涨幅':<30} {t_life.get('final_change_pct', 0):>+.2f}%{'':<18} {p_life.get('final_change_pct', 0):>+.2f}%")
        
        # 推升阶段对比（真起爆用warmup_duration，骗炮用fake_duration）
        t_breakout = t_life.get('breakout', {})
        p_trap = p_life.get('trap', {})
        
        # 真起爆特征
        if t_breakout:
            print(f"{'推升时长 T_warmup':<30} {t_breakout.get('warmup_duration', 0):>.1f}分钟{'':<15} {'-':<25}")
            print(f"{'推升段涨幅 Δp_push':<30} {t_breakout.get('change_end_pct', 0) - t_breakout.get('change_start_pct', 0):>+.2f}%{'':<17} {'-':<25}")
            print(f"{'推升段资金流入':<30} {t_breakout.get('total_inflow_yi', 0):>.2f}亿元{'':<16} {'-':<25}")
        
        # 骗炮特征
        if p_trap:
            print(f"{'欺骗时长 T_fake':<30} {'-':<25} {p_trap.get('fake_duration', 0):>.1f}分钟")
            print(f"{'欺骗幅度 Δp_fake':<30} {'-':<25} {p_trap.get('fake_change_pct', 0):>+.2f}%")
            print(f"{'坠落时长 T_down':<30} {'-':<25} {p_trap.get('fall_duration', 0):>.1f}分钟")
            print(f"{'坠落幅度 Δp_down':<30} {'-':<25} {p_trap.get('fall_change_pct', 0):>+.2f}%")
        
        print("-" * 80)
        
        # 可交易窗口对比
        print("\n【可交易窗口对比】")
        t_tradable = true_result.get('tradable_windows', {})
        p_tradable = trap_result.get('tradable_windows', {})
        
        t_entries = t_tradable.get('entry_points', [])
        p_entries = p_tradable.get('entry_points', [])
        
        if t_entries and p_entries:
            print(f"{'入场时机':<15} {'真起爆收益':<15} {'真起爆回撤':<15} {'骗炮收益':<15} {'骗炮回撤':<15}")
            print("-" * 80)
            for t_e, p_e in zip(t_entries, p_entries):
                print(f"信号后{t_e['delay_minutes']}分钟{t_e['entry_time']:<6} "
                      f"{t_e['pnl_pct']:>+.2f}%{'':<8} {t_e['max_drawdown_pct']:>.2f}%{'':<8} "
                      f"{p_e['pnl_pct']:>+.2f}%{'':<8} {p_e['max_drawdown_pct']:>.2f}%")
        
        print("\n" + "="*80)


def main():
    """主函数"""
    analyzer = WangsuExtremeAnalyzer()
    
    # 分析真起爆
    true_result = analyzer.analyze_case(analyzer.true_date, "真起爆")
    
    # 分析骗炮
    trap_result = analyzer.analyze_case(analyzer.trap_date, "骗炮")
    
    # 生成对比报告
    analyzer.generate_report(true_result, trap_result)
    
    # 保存详细结果
    output_dir = PROJECT_ROOT / "data" / "wanzhu_data" / "wangsu_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"wangsu_extreme_analysis_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'true_breakout': true_result,
            'trap': trap_result,
            'generated_at': datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n📄 详细结果已保存: {output_file}")


if __name__ == "__main__":
    main()
