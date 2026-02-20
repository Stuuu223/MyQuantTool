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
        
        # 5. 事件后走势分析
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
        """分析环境条件"""
        print(f"\n🌍 环境条件分析:")
        
        environment = {
            'date': date,
            'resonance_score': None,
            'market_sentiment': None,
            'risk_score': None,
        }
        
        # 尝试加载market_sentiment
        sentiment_path = PROJECT_ROOT / "config" / "market_sentiment.json"
        if sentiment_path.exists():
            try:
                with open(sentiment_path, 'r', encoding='utf-8') as f:
                    sentiment_data = json.load(f)
                # 查找对应日期的情绪数据
                if date in sentiment_data:
                    environment['market_sentiment'] = sentiment_data[date]
                    print(f"   市场情绪: {sentiment_data[date]}")
            except:
                pass
        
        # 这里可以扩展加载WindFilter的resonance_score
        # 目前先占位
        print(f"   板块共振: [待从WindFilter获取]")
        print(f"   风险评分: [待从TrapDetector获取]")
        
        return environment
    
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
