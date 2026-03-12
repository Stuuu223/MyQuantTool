# -*- coding: utf-8 -*-
"""
CTO V111 分K级别完整上升周期研究

【目标】
- 分析暴力真龙从起爆到断板的完整周期
- 使用分钟K线数据（1分钟）
- 研究上升周期中的分K物理特征
"""

import os
import sys
from typing import Dict, List
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    import xtquant.xtdata as xtdata
except ImportError:
    print("[ERROR] 无法导入xtquant，请确保在venv_qmt环境中运行")
    sys.exit(1)


def get_limit_up_price(stock_code: str, prev_close: float) -> float:
    """计算涨停价"""
    if stock_code.startswith(('30', '68')):
        limit_pct = 0.20
    elif 'ST' in stock_code or 'st' in stock_code:
        limit_pct = 0.05
    else:
        limit_pct = 0.10
    return round(prev_close * (1 + limit_pct) * 100) / 100


def analyze_minute_cycle(stock_code: str, dates: List) -> Dict:
    """
    分析分K级别的完整上升周期
    """
    result = {
        'stock_code': stock_code,
        'total_days': len(dates),
        'dates': dates,
        'success': False,
        'day_details': [],
        'cycle_summary': {},
        'error': None,
    }
    
    if not dates:
        result['error'] = '无日期数据'
        return result
    
    for i, date in enumerate(dates):
        day_num = i + 1
        date_str = str(date)  # 确保日期是字符串
        
        # 获取日K数据
        try:
            daily_data = xtdata.get_local_data(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount', 'preClose'],
                stock_list=[stock_code],
                period='1d',
                start_time=date_str,
                end_time=date_str
            )
            
            if not daily_data or stock_code not in daily_data:
                continue
                
            df_daily = daily_data[stock_code]
            if df_daily is None or len(df_daily) == 0:
                continue
            
            prev_close = float(df_daily['preClose'].iloc[0]) if 'preClose' in df_daily.columns else 0
            today_open = float(df_daily['open'].iloc[0])
            today_high = float(df_daily['high'].iloc[0])
            today_low = float(df_daily['low'].iloc[0])
            today_close = float(df_daily['close'].iloc[0])
            total_amount = float(df_daily['amount'].iloc[0])
            total_volume = float(df_daily['volume'].iloc[0])
            
            limit_price = get_limit_up_price(stock_code, prev_close)
            is_sealed = abs(today_close - limit_price) < 0.01
            
        except Exception as e:
            continue
        
        # 获取分钟K线数据
        try:
            minute_data = xtdata.get_local_data(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=[stock_code],
                period='1m',
                start_time=date_str,
                end_time=date_str
            )
            
            if not minute_data or stock_code not in minute_data:
                continue
                
            df_minute = minute_data[stock_code]
            if df_minute is None or len(df_minute) == 0:
                continue
            
            df_minute = df_minute.copy()
            # 分K的amount/volume已经是增量值
            df_minute['delta_amount'] = df_minute['amount']
            df_minute['delta_volume'] = df_minute['volume']
            
        except Exception as e:
            continue
        
        # 分析分K特征
        day_analysis = {
            'date': date_str,
            'day_num': day_num,
            'prev_close': prev_close,
            'open': today_open,
            'high': today_high,
            'low': today_low,
            'close': today_close,
            'limit_price': limit_price,
            'is_sealed': is_sealed,
            'total_amount': total_amount,
            'total_volume': total_volume,
            'change_pct': (today_close - prev_close) / prev_close * 100 if prev_close > 0 else 0,
            'amplitude': (today_high - today_low) / prev_close * 100 if prev_close > 0 else 0,
            'minute_count': len(df_minute),
        }
        
        # 计算分K能量分布
        if len(df_minute) > 0:
            n = len(df_minute)
            morning_end = n // 2
            
            morning_amount = float(df_minute['delta_amount'].iloc[:morning_end].sum())
            afternoon_amount = float(df_minute['delta_amount'].iloc[morning_end:].sum())
            
            day_analysis['morning_amount'] = morning_amount
            day_analysis['afternoon_amount'] = afternoon_amount
            day_analysis['morning_ratio'] = morning_amount / total_amount if total_amount > 0 else 0
            
            # 早盘爆发期 (前30分钟)
            early_30 = min(30, n // 4)
            early_amount = float(df_minute['delta_amount'].iloc[:early_30].sum())
            day_analysis['early_30min_amount'] = early_amount
            day_analysis['early_30min_ratio'] = early_amount / total_amount if total_amount > 0 else 0
            
            # VWAP
            if df_minute['delta_volume'].sum() > 0:
                vwap = (df_minute['close'] * df_minute['delta_volume']).sum() / df_minute['delta_volume'].sum()
                day_analysis['vwap'] = vwap
                day_analysis['vwap_position'] = (today_close - vwap) / prev_close * 100 if prev_close > 0 else 0
            
            # 封板时间估计
            limit_ticks = df_minute[df_minute['high'] >= limit_price * 0.99]
            if len(limit_ticks) > 0:
                first_limit_time = limit_ticks.index[0]
                if hasattr(first_limit_time, 'strftime'):
                    day_analysis['first_limit_time'] = first_limit_time.strftime('%H:%M')
                else:
                    day_analysis['first_limit_time'] = str(first_limit_time)[8:12]
        
        result['day_details'].append(day_analysis)
    
    # 汇总周期特征
    if result['day_details']:
        details = result['day_details']
        
        # 过滤有效数据
        valid_details = [d for d in details if d.get('minute_count', 0) > 0]
        
        if valid_details:
            result['cycle_summary'] = {
                'total_days': len(valid_details),
                'sealed_days': sum(1 for d in valid_details if d.get('is_sealed', False)),
                'total_amount_yi': sum(d.get('total_amount', 0) for d in valid_details) / 1e8,
                'avg_change_pct': np.mean([d.get('change_pct', 0) for d in valid_details]),
                'avg_amplitude': np.mean([d.get('amplitude', 0) for d in valid_details]),
                'avg_morning_ratio': np.mean([d.get('morning_ratio', 0) for d in valid_details]),
                'avg_early_30min_ratio': np.mean([d.get('early_30min_ratio', 0) for d in valid_details]),
            }
            result['success'] = True
        else:
            result['error'] = '无有效分K数据'
    
    return result


def main():
    print("="*70)
    print("CTO V111 分K级别完整上升周期研究")
    print("="*70)
    
    # 读取violent_surge样本
    samples_path = os.path.join(ROOT, 'data', 'validation', 'recent_samples_2025_2026.csv')
    df = pd.read_csv(samples_path)
    surge = df[df['label'] == 1].copy()
    
    # 按股票分组
    stock_dates = surge.groupby('stock_code')['date'].apply(list).reset_index()
    stock_dates['period_days'] = stock_dates['date'].apply(len)
    stock_dates = stock_dates.sort_values('period_days', ascending=False)
    
    print(f"\n[样本库] {len(surge)}个样本，{len(stock_dates)}只股票")
    print(f"[平均周期] {stock_dates['period_days'].mean():.1f}天")
    
    # 分析每只股票的完整周期
    all_results = []
    
    for idx, row in stock_dates.head(50).iterrows():
        stock_code = row['stock_code']
        dates = sorted(row['date'])
        
        print(f"\n[分析] {stock_code} 周期{len(dates)}天: {dates[0]} ~ {dates[-1]}")
        
        result = analyze_minute_cycle(stock_code, dates)
        all_results.append(result)
        
        if result['success']:
            summary = result['cycle_summary']
            print(f"  ✓ 封板{summary['sealed_days']}/{summary['total_days']}天, "
                  f"总成交{summary['total_amount_yi']:.2f}亿, "
                  f"均涨幅{summary['avg_change_pct']:.1f}%, "
                  f"早盘占比{summary['avg_morning_ratio']*100:.0f}%")
        else:
            print(f"  ✗ {result.get('error', '未知错误')}")
    
    # 生成汇总报告
    print("\n" + "="*70)
    print("【分K周期研究报告】")
    print("="*70)
    
    valid_results = [r for r in all_results if r['success']]
    
    if valid_results:
        # 汇总统计
        total_days = sum(r['cycle_summary']['total_days'] for r in valid_results)
        total_sealed = sum(r['cycle_summary']['sealed_days'] for r in valid_results)
        avg_change = np.mean([r['cycle_summary']['avg_change_pct'] for r in valid_results])
        avg_morning = np.mean([r['cycle_summary']['avg_morning_ratio'] for r in valid_results])
        avg_early = np.mean([r['cycle_summary']['avg_early_30min_ratio'] for r in valid_results])
        
        print(f"\n【有效样本】: {len(valid_results)}只股票")
        print(f"【总交易日】: {total_days}天")
        print(f"【封板率】: {total_sealed}/{total_days} = {total_sealed/total_days*100:.1f}%")
        print(f"\n【分K物理特征】")
        print(f"  平均涨幅: {avg_change:.2f}%")
        print(f"  早盘成交占比: {avg_morning*100:.1f}%")
        print(f"  前30分钟成交占比: {avg_early*100:.1f}%")
        
        # 按周期长度分组
        short_cycle = [r for r in valid_results if r['cycle_summary']['total_days'] == 1]
        long_cycle = [r for r in valid_results if r['cycle_summary']['total_days'] >= 2]
        
        if short_cycle:
            print(f"\n【单日样本({len(short_cycle)}只)】")
            print(f"  早盘占比: {np.mean([r['cycle_summary']['avg_morning_ratio'] for r in short_cycle])*100:.1f}%")
            print(f"  前30分钟占比: {np.mean([r['cycle_summary']['avg_early_30min_ratio'] for r in short_cycle])*100:.1f}%")
        
        if long_cycle:
            print(f"\n【多日连板样本({len(long_cycle)}只)】")
            print(f"  平均周期: {np.mean([r['cycle_summary']['total_days'] for r in long_cycle]):.1f}天")
            print(f"  早盘占比: {np.mean([r['cycle_summary']['avg_morning_ratio'] for r in long_cycle])*100:.1f}%")
    else:
        print("\n【警告】无有效样本！")
    
    # 保存结果
    output_dir = os.path.join(ROOT, 'data', 'research_lab')
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, 'minute_cycle_analysis.csv')
    df_results = pd.DataFrame([{
        'stock_code': r['stock_code'],
        'total_days': r['cycle_summary'].get('total_days', 0),
        'sealed_days': r['cycle_summary'].get('sealed_days', 0),
        'total_amount_yi': r['cycle_summary'].get('total_amount_yi', 0),
        'avg_change_pct': r['cycle_summary'].get('avg_change_pct', 0),
        'avg_morning_ratio': r['cycle_summary'].get('avg_morning_ratio', 0),
        'avg_early_30min_ratio': r['cycle_summary'].get('avg_early_30min_ratio', 0),
    } for r in valid_results])
    df_results.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n结果已保存至: {output_path}")


if __name__ == '__main__':
    main()
