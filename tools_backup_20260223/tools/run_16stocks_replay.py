#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
16只顽主票批量Tick回放验证
CTO指令：高频8+中频5+低频3，生成资金-价格-时间画像
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.rolling_metrics import RollingFlowCalculator, calculate_true_change_pct


def get_pre_close(stock_code, date_str):
    """获取昨收价（简化版，从本地已知数据或API获取）"""
    # 这里简化处理，实际应从日线数据获取
    # 临时返回0，让脚本自动从tick数据推算
    return 0


def analyze_stock_day(stock_code, stock_name, date_str, pre_close=None):
    """
    分析单只股票单日数据
    
    Returns:
        dict: 资金画像数据
    """
    try:
        # 格式化代码
        if '.' not in stock_code:
            formatted_code = f"{stock_code}.SZ" if stock_code.startswith(('00', '30')) else f"{stock_code}.SH"
        else:
            formatted_code = stock_code
        
        # 创建历史数据提供者
        start_time = f"{date_str.replace('-', '')}093000"
        end_time = f"{date_str.replace('-', '')}150000"
        
        provider = QMTHistoricalProvider(
            stock_code=formatted_code,
            start_time=start_time,
            end_time=end_time,
            period='tick'
        )
        
        # 检查是否有数据
        tick_count = provider.get_tick_count()
        if tick_count == 0:
            print(f"    ❌ 无Tick数据")
            return None
        
        # 初始化资金流计算器
        calc = RollingFlowCalculator(windows=[1, 5, 15])
        if pre_close:
            calc.set_pre_close(pre_close)
        
        # 存储结果
        records = []
        last_tick = None
        daily_stats = {
            'open_price': 0,
            'pre_close': pre_close if pre_close else 0,
            'high_price': 0,
            'low_price': float('inf'),
            'close_price': 0
        }
        
        # 遍历tick
        for tick in provider.iter_ticks():
            # 设置昨收价（从第一tick的open字段获取）
            if daily_stats['pre_close'] == 0:
                daily_stats['pre_close'] = tick.get('open', tick['lastPrice'])
                calc.set_pre_close(daily_stats['pre_close'])
            
            if daily_stats['open_price'] == 0:
                daily_stats['open_price'] = tick['lastPrice']
            
            daily_stats['high_price'] = max(daily_stats['high_price'], tick['lastPrice'])
            daily_stats['low_price'] = min(daily_stats['low_price'], tick['lastPrice'])
            daily_stats['close_price'] = tick['lastPrice']
            
            # 计算滚动资金流
            metrics = calc.add_tick(tick, last_tick)
            
            # 记录数据
            time_str = datetime.fromtimestamp(int(tick['time']) / 1000).strftime('%H:%M:%S')
            record = {
                'time': time_str,
                'price': tick['lastPrice'],
                'true_change_pct': metrics.true_change_pct,
                'flow_1min': metrics.flow_1min.total_flow,
                'flow_5min': metrics.flow_5min.total_flow,
                'flow_15min': metrics.flow_15min.total_flow,
                'flow_sustainability': metrics.flow_sustainability,
                'confidence': metrics.confidence
            }
            records.append(record)
            last_tick = tick
        
        # 计算日级统计
        df = pd.DataFrame(records)
        if df.empty:
            return None
        
        summary = {
            'date': date_str,
            'code': stock_code,
            'name': stock_name,
            'tick_count': tick_count,
            'open': daily_stats['open_price'],
            'pre_close': daily_stats['pre_close'],
            'high': daily_stats['high_price'],
            'low': daily_stats['low_price'],
            'close': daily_stats['close_price'],
            'true_change_pct': (daily_stats['close_price'] - daily_stats['pre_close']) / daily_stats['pre_close'] * 100 if daily_stats['pre_close'] > 0 else 0,
            'max_flow_5min': df['flow_5min'].max(),
            'avg_flow_5min': df['flow_5min'].mean(),
            'max_flow_15min': df['flow_15min'].max(),
            'records': records
        }
        
        return summary
        
    except Exception as e:
        print(f"    ❌ 处理失败: {e}")
        return None


def main():
    """主函数"""
    print("=" * 80)
    print("16只顽主票批量Tick回放验证")
    print("=" * 80)
    
    # 加载配置
    config_path = PROJECT_ROOT / "data" / "wanzhu_data" / "research_sample_config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    samples = config['samples']
    
    print(f"\n共 {len(samples)} 只票待处理")
    print("-" * 80)
    
    # 创建输出目录
    output_dir = PROJECT_ROOT / "data" / "wanzhu_data" / "samples"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 统计
    results_summary = []
    
    # 处理每只票
    for idx, sample in enumerate(samples, 1):
        code = sample['code']
        name = sample['name']
        layer = sample['layer']
        
        print(f"\n[{idx}/{len(samples)}] {code} {name} ({layer})")
        print("-" * 40)
        
        # 处理已标注的日期
        cases = sample.get('cases', {})
        
        # 处理真起爆日
        for case in cases.get('真起爆', []):
            date = case['date']
            desc = case.get('desc', '')
            print(f"  🟢 真起爆 {date}: {desc[:30]}...")
            
            result = analyze_stock_day(code, name, date)
            if result:
                # 保存CSV
                df = pd.DataFrame(result['records'])
                csv_path = output_dir / f"{code}_{date}_true.csv"
                df.to_csv(csv_path, index=False)
                
                # 记录摘要
                results_summary.append({
                    'code': code,
                    'name': name,
                    'layer': layer,
                    'date': date,
                    'type': '真起爆',
                    'true_change_pct': result['true_change_pct'],
                    'max_flow_5min': result['max_flow_5min'],
                    'avg_flow_5min': result['avg_flow_5min'],
                    'status': '完成'
                })
                print(f"    ✅ 完成: 涨幅{result['true_change_pct']:.2f}%, 5min流{result['max_flow_5min']/1e6:.1f}M")
            else:
                results_summary.append({
                    'code': code, 'name': name, 'layer': layer,
                    'date': date, 'type': '真起爆', 'status': '失败'
                })
        
        # 处理骗炮日
        for case in cases.get('骗炮', []):
            date = case['date']
            desc = case.get('desc', '')
            print(f"  🔴 骗炮 {date}: {desc[:30]}...")
            
            result = analyze_stock_day(code, name, date)
            if result:
                df = pd.DataFrame(result['records'])
                csv_path = output_dir / f"{code}_{date}_trap.csv"
                df.to_csv(csv_path, index=False)
                
                results_summary.append({
                    'code': code,
                    'name': name,
                    'layer': layer,
                    'date': date,
                    'type': '骗炮',
                    'true_change_pct': result['true_change_pct'],
                    'max_flow_5min': result['max_flow_5min'],
                    'avg_flow_5min': result['avg_flow_5min'],
                    'status': '完成'
                })
                print(f"    ✅ 完成: 涨幅{result['true_change_pct']:.2f}%, 5min流{result['max_flow_5min']/1e6:.1f}M")
            else:
                results_summary.append({
                    'code': code, 'name': name, 'layer': layer,
                    'date': date, 'type': '骗炮', 'status': '失败'
                })
    
    # 保存汇总
    if results_summary:
        summary_df = pd.DataFrame(results_summary)
        summary_path = output_dir / "analysis_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        
        print("\n" + "=" * 80)
        print("汇总统计")
        print("=" * 80)
        print(summary_df.to_string())
        print(f"\n💾 结果保存: {output_dir}")
    
    print("\n" + "=" * 80)
    print("✅ 16只票批量验证完成")
    print("=" * 80)


if __name__ == "__main__":
    main()