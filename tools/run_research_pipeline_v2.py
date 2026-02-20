#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研究流水线V2.0 - 动态轨迹版
CTO指令：从静态标签升级到动态轨迹研究

核心升级：
1. 自动切分事件区间（起点-过程-终点）
2. 真起爆：推升时长T_up、空间Δp_up、资金轨迹
3. 骗炮：欺骗时长T_fake、幅度Δp_fake、坠落T_down
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.services.data_service import data_service
from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.rolling_metrics import RollingFlowCalculator
from logic.event_lifecycle_analyzer import EventLifecycleAnalyzer, TrueBreakoutEvent, TrapEvent


def analyze_single_day_with_lifecycle(code: str, name: str, date: str, label: str) -> dict:
    """
    分析单日数据，提取事件生命周期
    """
    try:
        # 1. 格式化代码
        formatted_code = data_service._format_code(code)
        
        # 2. 获取昨收价
        pre_close = data_service.get_pre_close(code, date)
        if pre_close <= 0:
            return {'status': 'failed', 'error': '无法获取昨收价'}
        
        # 3. 加载Tick数据
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
            return {'status': 'failed', 'error': '无Tick数据'}
        
        # 4. 计算资金流
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
            })
            last_tick = tick
        
        df = pd.DataFrame(results)
        
        # 5. 事件生命周期分析
        analyzer = EventLifecycleAnalyzer(
            breakout_threshold=5.0,
            trap_reversal_threshold=3.0,
            max_drawdown_threshold=5.0
        )
        
        events = analyzer.analyze_day(df, pre_close)
        
        # 6. 提取关键事件
        result = {
            'code': code,
            'name': name,
            'date': date,
            'pre_close': pre_close,
            'final_change_pct': df['true_change_pct'].iloc[-1],
            'max_change_pct': df['true_change_pct'].max(),
            'min_change_pct': df['true_change_pct'].min(),
            'tick_count': len(df),
            'status': 'success'
        }
        
        # 添加真起爆事件详情
        if events['breakouts']:
            evt = events['breakouts'][0]  # 取第一个
            if evt.push_phase:
                result.update({
                    'breakout_t_start': evt.push_phase.t_start,
                    'breakout_t_end': evt.push_phase.t_end,
                    'breakout_duration': evt.push_phase.duration_minutes,
                    'breakout_change_start': evt.push_phase.change_start_pct,
                    'breakout_change_end': evt.push_phase.change_end_pct,
                    'breakout_change_peak': evt.push_phase.change_peak_pct,
                    'breakout_max_drawdown': evt.push_phase.max_drawdown_pct,
                    'breakout_total_inflow': evt.push_phase.total_inflow,
                    'breakout_max_flow_5min': evt.push_phase.max_flow_5min,
                    'breakout_sustain_ratio': evt.push_phase.sustain_ratio,
                    'breakout_efficiency': evt.push_phase.price_efficiency,
                    'is_gradual_push': evt.is_gradual_push,
                })
        
        # 添加骗炮事件详情
        if events['traps']:
            evt = events['traps'][0]
            if evt.fake_phase:
                result.update({
                    'trap_t_fake': evt.t_fake,
                    'trap_t_peak': evt.t_peak,
                    'trap_t_fail': evt.t_fail,
                    'trap_fake_duration': evt.fake_duration,
                    'trap_fake_change': evt.fake_change_pct,
                    'trap_fall_duration': evt.fall_duration,
                    'trap_fall_change': evt.fall_change_pct,
                })
        
        return result
        
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


def run_pipeline_v2(config_path: Path, output_dir: Path, log_dir: Path):
    """
    执行V2流水线
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file_path = log_dir / f"pipeline_v2_{timestamp}.log"
    
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        # 头信息
        header = f"""
{'='*80}
研究流水线V2.0 - 动态轨迹版
开始时间: {datetime.now().isoformat()}
{'='*80}
"""
        print(header)
        log_file.write(header + '\n')
        
        # 环境检查
        print("\n【1. 环境自检】")
        passed, env_info = data_service.env_check()
        if not passed:
            print("❌ 环境检查失败")
            return
        print(f"✅ 环境检查通过")
        
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        samples = config.get('samples', [])
        print(f"\n【2. 加载配置】样本数: {len(samples)}")
        
        # 执行分析
        all_results = []
        
        for sample in samples:
            code = sample['code']
            name = sample['name']
            
            for date_info in sample.get('dates', []):
                if isinstance(date_info, dict):
                    date = date_info['date']
                    label = date_info['label']
                    verified = date_info.get('verified', False)
                    
                    # 只处理verified=true的
                    if not verified:
                        continue
                    
                    print(f"\n分析 {code} {name} {date} ({label})")
                    result = analyze_single_day_with_lifecycle(code, name, date, label)
                    result['label'] = label
                    
                    if result['status'] == 'success':
                        print(f"  ✅ 完成")
                        if 'breakout_duration' in result:
                            print(f"     推升时长: {result['breakout_duration']:.1f}分钟")
                            print(f"     涨幅: {result['breakout_change_start']:.1f}% -> {result['breakout_change_end']:.1f}%")
                        if 'trap_fake_duration' in result:
                            print(f"     欺骗时长: {result['trap_fake_duration']:.1f}分钟")
                    else:
                        print(f"  ❌ 失败: {result.get('error', 'unknown')}")
                    
                    all_results.append(result)
        
        # 保存结果
        if all_results:
            df = pd.DataFrame([r for r in all_results if r['status'] == 'success'])
            output_file = output_dir / f"lifecycle_analysis_{timestamp}.csv"
            df.to_csv(output_file, index=False)
            print(f"\n✅ 结果已保存: {output_file}")
            
            # 统计
            print("\n【统计汇总】")
            print(f"成功案例: {len(df)}")
            
            if 'breakout_duration' in df.columns:
                print(f"\n真起爆事件:")
                print(f"  平均推升时长: {df['breakout_duration'].mean():.1f}分钟")
                print(f"  平均涨幅: {df['breakout_change_end'].mean():.1f}%")
                print(f"  平均资金流入: {df['breakout_total_inflow'].mean()/1e6:.1f}M")
            
            if 'trap_fake_duration' in df.columns:
                print(f"\n骗炮事件:")
                print(f"  平均欺骗时长: {df['trap_fake_duration'].mean():.1f}分钟")
                print(f"  平均坠落时长: {df['trap_fall_duration'].mean():.1f}分钟")
        
        print(f"\n📄 日志: {log_file_path}")


if __name__ == "__main__":
    config_path = PROJECT_ROOT / "data" / "wanzhu_data" / "research_labels_v2.json"
    output_dir = PROJECT_ROOT / "data" / "wanzhu_data" / "lifecycle_results"
    log_dir = PROJECT_ROOT / "logs" / "pipeline_v2"
    
    run_pipeline_v2(config_path, output_dir, log_dir)
