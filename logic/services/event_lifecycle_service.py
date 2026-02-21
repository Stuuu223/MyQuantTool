#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件生命周期服务 - Phase 3通用化封装

职责：
1. 单票单日事件分析
2. 计算维持能力分、环境分
3. 输出真起爆/骗炮预测

使用：
    service = EventLifecycleService()
    result = service.analyze("300017", "2026-01-26")
    # result = {
    #     'sustain_score': 0.65,      # 维持能力分 (0-1)
    #     'env_score': 0.87,           # 环境分 (0-1)
    #     'is_true_breakout': True,    # 真起爆预测
    #     'confidence': 0.82,          # 置信度
    #     'entry_signal': {...}        # 入场信号详情
    # }

Author: iFlow CLI
Version: Phase 3.0
Date: 2026-02-21
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
from dataclasses import asdict

import pandas as pd
import numpy as np

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.event_lifecycle_analyzer import EventLifecycleAnalyzer, TrueBreakoutEvent, TrapEvent
from logic.services.data_service import data_service
from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.rolling_metrics import RollingFlowCalculator


class EventLifecycleService:
    """
    事件生命周期服务 - Phase 3通用化封装
    
    提供单票单日的事件分析、维持能力评分、环境评分和真起爆/骗炮预测功能。
    """
    
    def __init__(self):
        """初始化事件生命周期服务"""
        self.lifecycle_analyzer = None  # 延迟初始化
        self._env_cache = {}  # 环境数据缓存
        self._tick_cache = {}  # Tick数据缓存（单日内有效）
        
    def analyze(self, code: str, date: str) -> dict:
        """
        主分析接口 - 分析单票单日的事件生命周期
        
        Args:
            code: 股票代码，如 "300017"
            date: 日期，格式 "2026-01-26"
            
        Returns:
            dict: 分析结果，包含维持能力分、环境分、真起爆预测等
            {
                'code': '300017',
                'date': '2026-01-26',
                'sustain_score': 0.65,           # 维持能力分
                'sustain_duration_min': 132.4,   # 维持时长（分钟）
                'env_score': 0.87,               # 环境分
                'env_details': {...},            # 环境详情
                'is_true_breakout': True,        # 真起爆预测
                'confidence': 0.82,              # 置信度
                'entry_signal': {...},           # 入场信号
                'raw_data': {...}                # 原始数据（调试用）
            }
        """
        try:
            # 1. 加载Tick数据
            df = self._load_tick_data(code, date)
            if df is None or df.empty:
                return {
                    'error': f'无法加载 {code} 在 {date} 的Tick数据',
                    'code': code,
                    'date': date,
                    'sustain_score': 0.0,
                    'env_score': 0.0,
                    'is_true_breakout': None,
                    'confidence': 0.0
                }
            
            pre_close = df['pre_close'].iloc[0] if 'pre_close' in df.columns else 0
            if pre_close <= 0:
                return {
                    'error': f'无法获取 {code} 在 {date} 的昨收价',
                    'code': code,
                    'date': date,
                    'sustain_score': 0.0,
                    'env_score': 0.0,
                    'is_true_breakout': None,
                    'confidence': 0.0
                }
            
            # 2. 事件生命周期分析
            lifecycle = self._analyze_lifecycle(code, df, pre_close)
            
            # 3. 计算维持能力分
            sustain_score, sustain_duration = self._calculate_sustain_score(lifecycle, df)
            
            # 4. 计算环境分
            env_score, env_details = self._calculate_env_score(date, code)
            
            # 5. 预测真起爆/骗炮
            is_true_breakout, confidence = self._predict_breakout(sustain_score, env_score)
            
            # 6. 提取入场信号
            entry_signal = self._extract_entry_signal(df, lifecycle, pre_close)
            
            # 7. 组装结果
            result = {
                'code': code,
                'date': date,
                'sustain_score': round(sustain_score, 2),
                'sustain_duration_min': round(sustain_duration, 1),
                'env_score': round(env_score, 2),
                'env_details': env_details,
                'is_true_breakout': is_true_breakout,
                'confidence': round(confidence, 2),
                'entry_signal': entry_signal,
                'raw_data': {
                    'lifecycle': lifecycle,
                    'tick_count': len(df),
                    'pre_close': pre_close,
                    'max_change_pct': df['true_change_pct'].max() if 'true_change_pct' in df.columns else 0,
                }
            }
            
            return result
            
        except Exception as e:
            return {
                'error': f'分析失败: {str(e)}',
                'code': code,
                'date': date,
                'sustain_score': 0.0,
                'env_score': 0.0,
                'is_true_breakout': None,
                'confidence': 0.0
            }
    
    def _load_tick_data(self, code: str, date: str) -> Optional[pd.DataFrame]:
        """
        加载Tick数据
        
        Args:
            code: 股票代码
            date: 日期
            
        Returns:
            DataFrame或None，包含列：time, price, true_change_pct, flow_5min, flow_15min, pre_close
        """
        cache_key = f"{code}_{date}"
        if cache_key in self._tick_cache:
            return self._tick_cache[cache_key]
        
        try:
            formatted_code = data_service._format_code(code)
            pre_close = data_service.get_pre_close(code, date)
            
            if pre_close <= 0:
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
                return None
            
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
            
            df = pd.DataFrame(results)
            self._tick_cache[cache_key] = df
            return df
            
        except Exception as e:
            print(f"加载Tick数据失败 {code} {date}: {e}")
            return None
    
    def _analyze_lifecycle(self, code: str, df: pd.DataFrame, pre_close: float) -> dict:
        """
        分析事件生命周期
        
        Args:
            code: 股票代码
            df: Tick数据DataFrame
            pre_close: 昨收价
            
        Returns:
            dict: 生命周期分析结果
        """
        # 初始化分析器（使用ratio化阈值）
        analyzer = EventLifecycleAnalyzer(
            stock_code=code,
            breakout_threshold=4.0,
            trap_reversal_threshold=-1.5,
            max_drawdown_threshold=3.0
        )
        
        events = analyzer.analyze_day(df, pre_close)
        
        lifecycle = {
            'max_change_pct': df['true_change_pct'].max(),
            'min_change_pct': df['true_change_pct'].min(),
            'final_change_pct': df['true_change_pct'].iloc[-1],
            'total_inflow_yi': df['flow_5min'].sum() / 1e8,
            'breakout': None,
            'trap': None,
            'event_type': 'unknown'
        }
        
        # 真起爆事件
        if events['breakouts']:
            evt = events['breakouts'][0]
            if evt.push_phase:
                lifecycle['breakout'] = {
                    't_start': evt.push_phase.t_start,
                    't_end': evt.push_phase.t_end,
                    'warmup_duration': evt.push_phase.duration_minutes,
                    'change_start_pct': evt.push_phase.change_start_pct,
                    'change_end_pct': evt.push_phase.change_end_pct,
                    'change_peak_pct': evt.push_phase.change_peak_pct,
                    'max_drawdown_pct': evt.push_phase.max_drawdown_pct,
                    'total_inflow_yi': evt.push_phase.total_inflow / 1e8,
                    'max_flow_5min_yi': evt.push_phase.max_flow_5min / 1e8,
                    'sustain_ratio': evt.push_phase.sustain_ratio,
                    'efficiency': evt.push_phase.price_efficiency,
                    'is_gradual_push': evt.is_gradual_push,
                }
                lifecycle['event_type'] = 'true_breakout'
        
        # 骗炮事件
        if events['traps']:
            evt = events['traps'][0]
            if evt.fake_phase:
                lifecycle['trap'] = {
                    't_fake': evt.t_fake,
                    't_peak': evt.t_peak,
                    't_fail': evt.t_fail,
                    'fake_duration': evt.fake_duration,
                    'fake_change_pct': evt.fake_change_pct,
                    'fall_duration': evt.fall_duration,
                    'fall_change_pct': evt.fall_change_pct,
                }
                if lifecycle['event_type'] == 'unknown':
                    lifecycle['event_type'] = 'trap'
        
        return lifecycle
    
    def _calculate_sustain_score(self, lifecycle: dict, df: pd.DataFrame) -> Tuple[float, float]:
        """
        计算维持能力分 (0-1)
        
        Phase 2验证的权重：
        - 时间维度（高位维持时长）：权重50%
        - 强度维度（平均资金流入）：权重30%
        - 稳定性维度（价格波动率）：权重20%
        
        Args:
            lifecycle: 生命周期分析结果
            df: Tick数据DataFrame
            
        Returns:
            Tuple[float, float]: (维持能力分, 维持时长分钟)
        """
        t_breakout = lifecycle.get('breakout', {})
        t_trap = lifecycle.get('trap', {})
        
        if t_breakout:
            # 真起爆：基于推升结束点计算维持能力
            return self._calculate_true_breakout_sustain(df, t_breakout)
        elif t_trap:
            # 骗炮：基于欺骗高点计算维持能力
            return self._calculate_trap_sustain(df, t_trap)
        else:
            # 未识别到明确事件
            return 0.0, 0.0
    
    def _calculate_true_breakout_sustain(self, df: pd.DataFrame, breakout_info: dict) -> Tuple[float, float]:
        """
        计算真起爆维持能力
        
        Args:
            df: Tick数据DataFrame
            breakout_info: 起爆信息
            
        Returns:
            Tuple[float, float]: (综合维持得分, 维持时长分钟)
        """
        push_end_time = breakout_info.get('t_end', '')
        if not push_end_time:
            return 0.0, 0.0
        
        push_end_idx = self._find_time_index(df, push_end_time)
        if push_end_idx >= len(df) - 1:
            return 0.0, 0.0
        
        push_end_price = df.loc[push_end_idx, 'price']
        sustain_threshold = push_end_price * 0.98  # -2%阈值
        
        sustain_df = df.iloc[push_end_idx:]
        above_threshold = sustain_df[sustain_df['price'] >= sustain_threshold]
        
        if len(above_threshold) == 0:
            return 0.0, 0.0
        
        # 时间维度：高位维持时长（分钟）
        tick_interval_seconds = 3  # 约3秒一条Tick
        sustain_minutes = len(above_threshold) * tick_interval_seconds / 60
        
        # 强度维度：维持期间平均资金流入（亿元/5min）
        avg_flow = above_threshold['flow_5min'].mean() / 1e8
        
        # 稳定性维度：价格波动率（%）
        price_volatility = above_threshold['price'].std() / above_threshold['price'].mean() * 100
        
        # 计算综合得分（0-1）
        duration_score = min(sustain_minutes / 60, 1.0)  # 60分钟为满分
        strength_score = min(avg_flow / 0.5, 1.0)  # 0.5亿元/5min为满分
        stability_score = 1.0 - min(price_volatility / 10.0, 1.0)  # 波动率<10%为满分
        
        composite_score = (
            duration_score * 0.5 + 
            strength_score * 0.3 + 
            stability_score * 0.2
        )
        
        return composite_score, sustain_minutes
    
    def _calculate_trap_sustain(self, df: pd.DataFrame, trap_info: dict) -> Tuple[float, float]:
        """
        计算骗炮维持能力（通常很短）
        
        Args:
            df: Tick数据DataFrame
            trap_info: 骗炮信息
            
        Returns:
            Tuple[float, float]: (综合维持得分, 维持时长分钟)
        """
        peak_time = trap_info.get('t_peak', '')
        if not peak_time:
            return 0.0, 0.0
        
        peak_idx = self._find_time_index(df, peak_time)
        if peak_idx >= len(df) - 1:
            return 0.0, 0.0
        
        peak_price = df.loc[peak_idx, 'price']
        sustain_threshold = peak_price * 0.98
        
        after_peak_df = df.iloc[peak_idx:]
        above_threshold = after_peak_df[after_peak_df['price'] >= sustain_threshold]
        
        if len(above_threshold) == 0:
            return 0.0, 0.0
        
        tick_interval_seconds = 3
        sustain_minutes = len(above_threshold) * tick_interval_seconds / 60
        
        avg_flow = above_threshold['flow_5min'].mean() / 1e8
        price_volatility = above_threshold['price'].std() / above_threshold['price'].mean() * 100
        
        # 骗炮的权重略有不同
        duration_score = min(sustain_minutes / 30, 1.0)  # 30分钟为满分
        strength_score = min(avg_flow / 0.2, 1.0)  # 0.2亿元/5min为满分
        stability_score = 1.0 - min(price_volatility / 15.0, 1.0)  # 波动率<15%为满分
        
        composite_score = (
            duration_score * 0.4 + 
            strength_score * 0.3 + 
            stability_score * 0.3
        )
        
        # 骗炮得分打折扣
        composite_score *= 0.5
        
        return composite_score, sustain_minutes
    
    def _find_time_index(self, df: pd.DataFrame, target_time: str) -> int:
        """
        在DataFrame中查找时间点索引
        
        Args:
            df: DataFrame
            target_time: 目标时间，格式 "HH:MM:SS"
            
        Returns:
            int: 索引位置
        """
        if not target_time or 'time' not in df.columns:
            return 0
        
        for idx, row in df.iterrows():
            if row['time'].strftime('%H:%M:%S') == target_time:
                return idx
        
        # 如果找不到精确匹配，找最接近的时间
        for idx, row in df.iterrows():
            if row['time'].strftime('%H:%M:%S') >= target_time:
                return idx
        
        return 0
    
    def _calculate_env_score(self, date: str, code: str) -> Tuple[float, dict]:
        """
        计算环境分 (0-1)
        
        Phase 1权重：
        - 板块共振分数：权重40%
        - 市场情绪分数：权重40%
        - 风险评分：权重20%
        
        Args:
            date: 日期
            code: 股票代码
            
        Returns:
            Tuple[float, dict]: (环境分, 环境详情)
        """
        cache_key = date
        if cache_key in self._env_cache:
            return self._env_cache[cache_key]
        
        env_details = {
            'resonance_score': 0.5,
            'market_sentiment': 0.5,
            'risk_score': 0.5,
            'resonance_source': 'default',
            'sentiment_source': 'default'
        }
        
        # 1. 加载板块共振分数（优先使用手工回填数据）
        resonance_score = 0.5
        resonance_loaded = False
        
        env_path = PROJECT_ROOT / "config" / "event_environment.json"
        if env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    env_data = json.load(f)
                
                env_data_dict = env_data.get('environment_data', {})
                date_formats = [date, date.replace('-', ''), f"{date.replace('-', '')[:8]}"]
                
                for date_fmt in date_formats:
                    if date_fmt in env_data_dict:
                        env_info = env_data_dict[date_fmt]
                        resonance_score = env_info.get('resonance_score', 0.5)
                        env_details['resonance_score'] = resonance_score
                        env_details['resonance_source'] = 'event_environment.json'
                        env_details['resonance_info'] = {
                            'limit_up_count': env_info.get('limit_up_count', 0),
                            'limit_down_count': env_info.get('limit_down_count', 0),
                            'sector_active_stocks': env_info.get('sector_active_stocks', 0),
                            'sector_total_stocks': env_info.get('sector_total_stocks', 45),
                            'description': env_info.get('description', '')
                        }
                        resonance_loaded = True
                        break
                        
            except Exception as e:
                pass
        
        # 如果手工回填数据未找到，回退到WindFilter实时计算
        if not resonance_loaded:
            try:
                from logic.strategies.wind_filter import WindFilter
                wind_filter = WindFilter()
                resonance_result = wind_filter.check_sector_resonance(code)
                resonance_score = resonance_result.get('resonance_score', 0.5)
                env_details['resonance_score'] = resonance_score
                env_details['resonance_source'] = 'WindFilter'
                env_details['resonance_info'] = resonance_result
            except Exception:
                pass
        
        # 2. 加载市场情绪数据
        sentiment_score = 0.5
        sentiment_loaded = False
        
        sentiment_path = PROJECT_ROOT / "config" / "market_sentiment.json"
        if sentiment_path.exists():
            try:
                with open(sentiment_path, 'r', encoding='utf-8') as f:
                    sentiment_data = json.load(f)
                
                date_formats = [date, date.replace('-', ''), f"{date.replace('-', '')[:8]}"]
                
                for date_fmt in date_formats:
                    if date_fmt in sentiment_data:
                        sentiment_info = sentiment_data[date_fmt]
                        sentiment_score = sentiment_info.get('sentiment_score', 0.5)
                        env_details['market_sentiment'] = sentiment_score
                        env_details['sentiment_source'] = 'market_sentiment.json'
                        env_details['sentiment_info'] = sentiment_info
                        sentiment_loaded = True
                        break
                
                if not sentiment_loaded and sentiment_data:
                    # 使用最近日期的情绪数据作为回退
                    available_dates = list(sentiment_data.keys())
                    if available_dates:
                        latest_date = max(available_dates)
                        sentiment_info = sentiment_data[latest_date]
                        sentiment_score = sentiment_info.get('sentiment_score', 0.5)
                        env_details['market_sentiment'] = sentiment_score
                        env_details['sentiment_source'] = f'market_sentiment.json({latest_date})'
                        env_details['sentiment_info'] = sentiment_info
                        sentiment_loaded = True
                        
            except Exception as e:
                pass
        
        # 3. 风险评分（占位实现）
        risk_score = 0.5  # 默认中等风险
        env_details['risk_score'] = risk_score
        
        # 4. 计算综合环境评分（0-1）
        # 风险分数需要反转：风险越高，环境分越低
        risk_adjusted = 1.0 - abs(risk_score - 0.5) * 2
        
        env_score = (
            resonance_score * 0.4 + 
            sentiment_score * 0.4 + 
            risk_adjusted * 0.2
        )
        
        result = (round(env_score, 2), env_details)
        self._env_cache[cache_key] = result
        return result
    
    def _predict_breakout(self, sustain_score: float, env_score: float) -> Tuple[Optional[bool], float]:
        """
        预测真起爆/骗炮，返回 (is_true_breakout, confidence)
        
        预测逻辑（基于Phase 2验证结果）：
        - 真起爆平均维持时长 132.4分钟，环境分0.62
        - 骗炮平均维持时长 28.7分钟，环境分0.21
        - 真/骗炮比率 4.61
        
        预测规则：
        - sustain_score >= 0.5 且 env_score >= 0.6 → 真起爆
        - sustain_score < 0.3 或 env_score < 0.4 → 骗炮
        - 其他 → 不确定
        
        Args:
            sustain_score: 维持能力分 (0-1)
            env_score: 环境分 (0-1)
            
        Returns:
            Tuple[Optional[bool], float]: (是否真起爆, 置信度)
        """
        if sustain_score >= 0.5 and env_score >= 0.6:
            return True, 0.8
        elif sustain_score < 0.3 or env_score < 0.4:
            return False, 0.7
        else:
            return None, 0.5  # 不确定
    
    def _extract_entry_signal(self, df: pd.DataFrame, lifecycle: dict, pre_close: float) -> Optional[dict]:
        """
        提取入场信号详情
        
        Args:
            df: Tick数据DataFrame
            lifecycle: 生命周期分析结果
            pre_close: 昨收价
            
        Returns:
            dict或None: 入场信号详情
        """
        t_breakout = lifecycle.get('breakout', {})
        if not t_breakout:
            return None
        
        trigger_time = t_breakout.get('t_start', '')
        if not trigger_time:
            return None
        
        trigger_idx = self._find_time_index(df, trigger_time)
        if trigger_idx >= len(df):
            return None
        
        entry_price = df.loc[trigger_idx, 'price']
        
        # 计算预期收益（到收盘）
        exit_price = df['price'].iloc[-1]
        expected_return = (exit_price - entry_price) / entry_price
        
        # 计算最大回撤
        hold_df = df.iloc[trigger_idx:]
        cummax = hold_df['price'].cummax()
        drawdowns = (cummax - hold_df['price']) / cummax
        max_drawdown = drawdowns.max()
        
        return {
            'trigger_time': trigger_time,
            'entry_price': round(entry_price, 2),
            'expected_return': round(expected_return, 3),
            'max_drawdown': round(max_drawdown, 3)
        }
    
    def clear_cache(self):
        """清除缓存"""
        self._env_cache.clear()
        self._tick_cache.clear()
    
    def _get_market_cap_multiplier(self, code: str) -> float:
        """
        根据流通市值获取阈值乘数
        
        优先级：
        1. Tushare实时数据（在线）
        2. 本地equity_info/market_cap.json（离线fallback）
        3. 默认值1.0x（中盘）
        
        Args:
            code: 股票代码，如 "300017"
            
        Returns:
            float: 阈值乘数 (0.8=小盘, 1.0=中盘, 1.2=大盘)
        """
        circ_mv = None
        data_source = "default"
        
        # 1. 尝试Tushare实时获取
        try:
            circ_mv = self._get_circ_mv_from_tushare(code)
            if circ_mv and circ_mv > 0:
                data_source = "tushare"
        except Exception as e:
            print(f"   Tushare获取市值失败 {code}: {e}")
        
        # 2. 尝试本地fallback
        if not circ_mv:
            try:
                circ_mv = self._get_circ_mv_from_local(code)
                if circ_mv and circ_mv > 0:
                    data_source = "local"
            except Exception as e:
                print(f"   本地市值数据失败 {code}: {e}")
        
        # 3. 使用默认值
        if not circ_mv:
            circ_mv = 50e9  # 默认50亿（中盘）
            data_source = "default"
        
        # 计算乘数
        if circ_mv < 30e9:       # 小盘<30亿
            multiplier = 0.8
            tier = "small"
        elif circ_mv < 80e9:     # 中盘30-80亿
            multiplier = 1.0
            tier = "mid"
        else:                    # 大盘>80亿
            multiplier = 1.2
            tier = "large"
        
        print(f"   市值分层: {code} {tier} ({circ_mv/1e9:.1f}亿) ×{multiplier} [{data_source}]")
        return multiplier
    
    def _get_circ_mv_from_tushare(self, code: str) -> Optional[float]:
        """
        从Tushare获取流通市值
        
        Args:
            code: 股票代码
            
        Returns:
            Optional[float]: 流通市值（元），失败返回None
        """
        try:
            # 尝试从equity_info_tushare.json读取
            tushare_path = PROJECT_ROOT / "data" / "equity_info" / "equity_info_tushare.json"
            if tushare_path.exists():
                with open(tushare_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 获取最新日期的数据
                latest_date = data.get('latest_update', '')
                if not latest_date:
                    return None
                    
                date_data = data.get('data', {}).get(latest_date, {})
                
                # 尝试带后缀的代码
                for suffix in ['.SZ', '.SH', '.BJ']:
                    key = f"{code}{suffix}"
                    if key in date_data:
                        float_mv = date_data[key].get('float_mv', 0)
                        # Tushare数据单位是万元，转换为元
                        if float_mv > 0:
                            return float(float_mv) * 10000
                
                # 尝试不带前导零
                if code.startswith('0'):
                    code_no_leading = code.lstrip('0')
                    for suffix in ['.SZ', '.SH', '.BJ']:
                        key = f"{code_no_leading}{suffix}"
                        if key in date_data:
                            float_mv = date_data[key].get('float_mv', 0)
                            if float_mv > 0:
                                return float(float_mv) * 10000
        except Exception as e:
            pass
        
        return None
    
    def _get_circ_mv_from_local(self, code: str) -> Optional[float]:
        """
        从本地JSON加载流通市值（离线fallback）
        
        Args:
            code: 股票代码
            
        Returns:
            Optional[float]: 流通市值（元），失败返回None
        """
        # 尝试多个路径
        paths = [
            PROJECT_ROOT / "data" / "equity_info" / "market_cap.json",
            PROJECT_ROOT / "data" / "equity_info.json",
            PROJECT_ROOT / "config" / "equity_info.json",
        ]
        
        for path in paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 跳过metadata
                    if code in data and not code.startswith('_'):
                        return float(data[code].get('circ_mv', 0))
                    
                    # 尝试不带前导零
                    if code.startswith('0') and code.lstrip('0') in data:
                        return float(data[code.lstrip('0')].get('circ_mv', 0))
                except Exception as e:
                    continue
        
        return None


# ==================== 测试代码 ====================
if __name__ == "__main__":
    print("="*80)
    print("EventLifecycleService 测试")
    print("="*80)
    
    service = EventLifecycleService()
    
    # 测试用例1: 网宿科技真起爆日 (2026-01-26)
    print("\n【测试用例1】网宿科技 2026-01-26 (已知真起爆)")
    print("-"*80)
    result1 = service.analyze("300017", "2026-01-26")
    
    if 'error' in result1 and result1['error']:
        print(f"❌ 错误: {result1['error']}")
    else:
        print(f"✅ 分析完成")
        print(f"   维持能力分: {result1['sustain_score']}")
        print(f"   维持时长: {result1['sustain_duration_min']:.1f}分钟")
        print(f"   环境分: {result1['env_score']}")
        print(f"   真起爆预测: {result1['is_true_breakout']}")
        print(f"   置信度: {result1['confidence']}")
        if result1['entry_signal']:
            print(f"   入场信号: {result1['entry_signal']['trigger_time']} @ {result1['entry_signal']['entry_price']}")
    
    # 测试用例2: 网宿科技骗炮日 (2026-02-13)
    print("\n【测试用例2】网宿科技 2026-02-13 (已知骗炮)")
    print("-"*80)
    result2 = service.analyze("300017", "2026-02-13")
    
    if 'error' in result2 and result2['error']:
        print(f"❌ 错误: {result2['error']}")
    else:
        print(f"✅ 分析完成")
        print(f"   维持能力分: {result2['sustain_score']}")
        print(f"   维持时长: {result2['sustain_duration_min']:.1f}分钟")
        print(f"   环境分: {result2['env_score']}")
        print(f"   真起爆预测: {result2['is_true_breakout']}")
        print(f"   置信度: {result2['confidence']}")
    
    # 测试用例3: 无效数据测试
    print("\n【测试用例3】无效股票代码测试")
    print("-"*80)
    result3 = service.analyze("999999", "2026-01-26")
    if 'error' in result3 and result3['error']:
        print(f"⚠️ 预期错误: {result3['error']}")
    else:
        print(f"   结果: {result3}")
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)
