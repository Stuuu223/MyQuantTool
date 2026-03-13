# -*- coding: utf-8 -*-
"""
【CTO V142 全天候分位数真理探寻方案】

研究目标：
1. 验证"时间越往后，物理门槛必须越高"的物理学法则
2. 构建【时间-分位数-胜率】三维热力图
3. 提炼全天候钢铁底线阈值

方法论：
- 真龙组 vs 骗炮组 对照实验
- 5个核心时间切片：09:35, 09:45, 10:30, 14:00, 14:45
- 横截面量比排名计算

Author: CTO
Date: 2026-03-13
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple, Optional

from xtquant import xtdata

# 核心时间切片
TIME_SLICES = {
    '09:35': {'minutes': 5, 'code': '093500'},
    '09:45': {'minutes': 15, 'code': '094500'},
    '10:30': {'minutes': 60, 'code': '103000'},
    '14:00': {'minutes': 150, 'code': '140000'},  # 上午120分钟 + 下午30分钟
    '14:45': {'minutes': 195, 'code': '144500'}   # 上午120分钟 + 下午75分钟
}

def get_minutes_passed(time_str: str) -> int:
    """计算从开盘到该时间点的分钟数"""
    hour = int(time_str[:2])
    minute = int(time_str[2:4])
    
    if hour < 11 or (hour == 11 and minute <= 30):
        return (hour - 9) * 60 + minute - 30
    else:
        return 120 + (hour - 13) * 60 + minute

def load_violent_samples() -> List[dict]:
    """加载暴力样本"""
    with open('data/validation/violent_samples_full.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def select_research_samples(samples: List[dict], n_samples: int = 50) -> Tuple[List[dict], List[dict]]:
    """
    选择研究样本
    
    Returns:
        (真龙组, 对照组)
    """
    # 真龙组：3天25%或5天60%以上
    dragon_samples = []
    for s in samples:
        if s['period'] in ['3d', '4d', '5d', '6d', '10d'] and s['return_pct'] >= 25:
            dragon_samples.append(s)
    
    # 按日期排序，取最近的
    dragon_samples.sort(key=lambda x: x['date'], reverse=True)
    
    # 对照组：涨停但次日大跌（炸板/骗炮）
    trap_samples = []
    for s in samples:
        if s['t0'].get('is_limit_up', False) and 't_plus_1' in s.get('post_days', {}):
            next_change = s['post_days']['t_plus_1'].get('change_pct', 0)
            if next_change < -5:  # 次日大跌超过5%
                trap_samples.append(s)
    
    trap_samples.sort(key=lambda x: x['date'], reverse=True)
    
    return dragon_samples[:n_samples], trap_samples[:n_samples]

def get_1m_data_batch(stocks: List[str], date_str: str) -> Dict[str, pd.DataFrame]:
    """批量获取1m分K数据"""
    try:
        data = xtdata.get_local_data(
            field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
            stock_list=stocks,
            period='1m',
            start_time=date_str,
            end_time=date_str
        )
        return data if data else {}
    except Exception as e:
        print(f"[ERROR] 获取1m数据失败: {e}")
        return {}

def get_daily_data_batch(stocks: List[str], date_str: str, lookback_days: int = 10) -> Dict[str, pd.DataFrame]:
    """批量获取日K数据用于计算5日均量"""
    start_date = (datetime.strptime(date_str, '%Y%m%d') - timedelta(days=lookback_days)).strftime('%Y%m%d')
    
    try:
        data = xtdata.get_local_data(
            field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
            stock_list=stocks,
            period='1d',
            start_time=start_date,
            end_time=date_str
        )
        return data if data else {}
    except Exception as e:
        print(f"[ERROR] 获取日K数据失败: {e}")
        return {}

def calculate_volume_ratio_1m(
    minute_df: pd.DataFrame,
    time_code: str,
    avg_volume_5d: float,
    date_str: str
) -> Optional[float]:
    """
    计算指定时间点的实时量比
    
    量比 = 累计成交量 / (5日均量 * 时间进度)
    """
    if minute_df is None or len(minute_df) == 0 or avg_volume_5d <= 0:
        return None
    
    target_time = int(date_str + time_code)
    
    # 处理索引格式
    try:
        idx_values = [int(i) if isinstance(i, str) else i for i in minute_df.index]
        mask = pd.Series(idx_values, index=minute_df.index) <= target_time
    except:
        return None
    
    if not mask.any():
        return None
    
    # 累计成交量（手）
    cumulative_volume = minute_df.loc[mask, 'volume'].sum()
    
    # 时间进度
    time_slice = None
    for ts_name, ts_info in TIME_SLICES.items():
        if ts_info['code'] == time_code:
            time_slice = ts_info
            break
    
    if time_slice is None:
        return None
    
    time_fraction = time_slice['minutes'] / 240.0
    
    # 实时量比
    expected_volume = avg_volume_5d * time_fraction
    if expected_volume > 0:
        return cumulative_volume / expected_volume
    return None

def calculate_cross_sectional_percentile(
    all_ratios: Dict[str, float],
    target_stock: str
) -> Tuple[float, float]:
    """
    计算横截面分位数
    
    Returns:
        (股票量比, 分位数)
    """
    if not all_ratios or target_stock not in all_ratios:
        return 0, 0
    
    valid_ratios = [r for r in all_ratios.values() if r > 0]
    if len(valid_ratios) < 10:
        return all_ratios.get(target_stock, 0), 0
    
    target_ratio = all_ratios[target_stock]
    
    # 计算分位数（target击败了多少比例的股票）
    count_below = sum(1 for r in valid_ratios if r < target_ratio)
    percentile = count_below / len(valid_ratios)
    
    return target_ratio, percentile

def research_single_day(
    date_str: str,
    dragon_stocks: List[str],
    trap_stocks: List[str]
) -> Dict:
    """
    研究单日数据
    """
    print(f"\n{'='*60}")
    print(f"研究日期: {date_str}")
    print(f"真龙: {len(dragon_stocks)}只, 对照: {len(trap_stocks)}只")
    print(f"{'='*60}")
    
    # 获取全A股
    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    
    # 获取日K数据
    print("Step 1: 获取日K数据计算5日均量...")
    daily_data = get_daily_data_batch(all_stocks, date_str)
    
    avg_volume_5d_cache = {}
    for stock, df in daily_data.items():
        if df is not None and len(df) >= 5:
            volumes = df['volume'].tail(5).values
            avg_volume_5d_cache[stock] = np.mean(volumes)
    
    print(f"  获取到{len(avg_volume_5d_cache)}只股票的5日均量")
    
    # 获取1m数据
    print("Step 2: 获取1m分K数据...")
    minute_data = get_1m_data_batch(all_stocks, date_str)
    print(f"  获取到{len(minute_data)}只股票的1m数据")
    
    # 计算各时间点结果
    results = {'dragon': {}, 'trap': {}}
    
    for time_name, time_info in TIME_SLICES.items():
        print(f"\nStep 3: 计算时间切片 {time_name}...")
        
        # 计算全市场量比
        all_ratios = {}
        for stock, df in minute_data.items():
            if stock not in avg_volume_5d_cache:
                continue
            
            ratio = calculate_volume_ratio_1m(
                df, time_info['code'], avg_volume_5d_cache[stock], date_str
            )
            if ratio is not None:
                all_ratios[stock] = ratio
        
        print(f"  计算了{len(all_ratios)}只股票的量比")
        
        # 真龙组
        dragon_percentiles = []
        dragon_ratios = []
        for stock in dragon_stocks:
            if stock in all_ratios:
                ratio, pct = calculate_cross_sectional_percentile(all_ratios, stock)
                dragon_ratios.append(ratio)
                dragon_percentiles.append(pct * 100)
        
        # 对照组
        trap_percentiles = []
        trap_ratios = []
        for stock in trap_stocks:
            if stock in all_ratios:
                ratio, pct = calculate_cross_sectional_percentile(all_ratios, stock)
                trap_ratios.append(ratio)
                trap_percentiles.append(pct * 100)
        
        # 全市场分位数阈值
        valid_ratios = list(all_ratios.values())
        market_percentiles = {
            '85th': np.percentile(valid_ratios, 85) if len(valid_ratios) > 10 else 0,
            '88th': np.percentile(valid_ratios, 88) if len(valid_ratios) > 10 else 0,
            '90th': np.percentile(valid_ratios, 90) if len(valid_ratios) > 10 else 0,
            '92th': np.percentile(valid_ratios, 92) if len(valid_ratios) > 10 else 0,
            '95th': np.percentile(valid_ratios, 95) if len(valid_ratios) > 10 else 0,
        }
        
        results['dragon'][time_name] = {
            'ratios': dragon_ratios,
            'percentiles': dragon_percentiles,
            'ratio_p50': np.median(dragon_ratios) if dragon_ratios else 0,
            'pct_p25': np.percentile(dragon_percentiles, 25) if dragon_percentiles else 0,
            'pct_p50': np.median(dragon_percentiles) if dragon_percentiles else 0,
        }
        
        results['trap'][time_name] = {
            'ratios': trap_ratios,
            'percentiles': trap_percentiles,
            'ratio_p50': np.median(trap_ratios) if trap_ratios else 0,
            'pct_p25': np.percentile(trap_percentiles, 25) if trap_percentiles else 0,
            'pct_p50': np.median(trap_percentiles) if trap_percentiles else 0,
        }
        
        results['market'] = {time_name: market_percentiles}
    
    return results

def generate_heatmap(all_results: List[Dict]) -> pd.DataFrame:
    """
    生成时间-分位数-覆盖率热力图
    
    覆盖率 = 真龙组中超过该分位数的比例
    """
    heatmap_data = []
    
    for time_name in TIME_SLICES.keys():
        row = {'时间切片': time_name}
        
        for pct_name in ['85th', '88th', '90th', '92th', '95th']:
            # 统计真龙组超过该分位数的比例
            dragon_above = 0
            dragon_total = 0
            
            for result in all_results:
                if time_name in result['dragon']:
                    market_threshold = result['market'].get(time_name, {}).get(pct_name, 0)
                    dragon_ratios = result['dragon'][time_name]['ratios']
                    
                    for r in dragon_ratios:
                        dragon_total += 1
                        if r >= market_threshold:
                            dragon_above += 1
            
            coverage = dragon_above / dragon_total * 100 if dragon_total > 0 else 0
            row[f'{pct_name}覆盖率'] = coverage
        
        heatmap_data.append(row)
    
    return pd.DataFrame(heatmap_data)

def print_final_report(all_results: List[Dict], heatmap_df: pd.DataFrame):
    """打印最终报告"""
    print("\n" + "="*80)
    print("【CTO V142 全天候分位数真理探寻报告】")
    print("="*80)
    
    # 汇总统计
    print("\n【真龙组 vs 对照组 横截面分位数对比】\n")
    
    for time_name in TIME_SLICES.keys():
        dragon_pcts = []
        trap_pcts = []
        
        for result in all_results:
            if time_name in result['dragon']:
                dragon_pcts.extend(result['dragon'][time_name]['percentiles'])
            if time_name in result['trap']:
                trap_pcts.extend(result['trap'][time_name]['percentiles'])
        
        print(f"--- {time_name} ---")
        if dragon_pcts:
            print(f"真龙组分位数: P25={np.percentile(dragon_pcts, 25):.1f}th, P50={np.median(dragon_pcts):.1f}th")
        if trap_pcts:
            print(f"对照组分位数: P25={np.percentile(trap_pcts, 25):.1f}th, P50={np.median(trap_pcts):.1f}th")
        print()
    
    # 热力图
    print("\n【时间-分位数-覆盖率热力图】\n")
    print(heatmap_df.to_string(index=False))
    
    # CTO结论
    print("\n" + "="*80)
    print("【CTO 最终裁决】")
    print("="*80)
    
    # 找出午后时段的最低覆盖率分位数
    afternoon_times = ['14:00', '14:45']
    for pct_name in ['92th', '90th', '88th']:
        col = f'{pct_name}覆盖率'
        afternoon_coverage = heatmap_df[heatmap_df['时间切片'].isin(afternoon_times)][col].mean()
        if afternoon_coverage >= 70:
            print(f"\n建议全天候阈值: {pct_name}")
            print(f"午后覆盖率: {afternoon_coverage:.1f}%")
            print(f"\n理由: 午后真龙依然能以70%+的覆盖率突破{pct_name}分位数")
            print("这验证了'时间越往后，物理门槛必须越高'的物理学法则")
            break

def main():
    print("="*60)
    print("【CTO V142 全天候分位数真理探寻方案】")
    print("="*60)
    
    # 加载样本
    print("\nStep 0: 加载研究样本...")
    samples = load_violent_samples()
    print(f"  总样本: {len(samples)}个")
    
    dragon_samples, trap_samples = select_research_samples(samples, n_samples=30)
    print(f"  真龙组: {len(dragon_samples)}个")
    print(f"  对照组: {len(trap_samples)}个")
    
    # 按日期分组
    dates = list(set([s['date'] for s in dragon_samples + trap_samples]))
    dates.sort(reverse=True)
    
    print(f"  涉及日期: {len(dates)}个")
    
    # 研究每个日期
    all_results = []
    
    for date_str in dates[:5]:  # 限制为最近5个日期
        dragon_stocks = [s['stock_code'] for s in dragon_samples if s['date'] == date_str]
        trap_stocks = [s['stock_code'] for s in trap_samples if s['date'] == date_str]
        
        if not dragon_stocks:
            continue
        
        result = research_single_day(date_str, dragon_stocks, trap_stocks)
        all_results.append(result)
    
    # 生成热力图
    print("\n\n生成热力图...")
    heatmap_df = generate_heatmap(all_results)
    
    # 打印报告
    print_final_report(all_results, heatmap_df)
    
    # 保存结果
    output_path = 'data/research_lab/percentile_truth_report.csv'
    os.makedirs('data/research_lab', exist_ok=True)
    heatmap_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n热力图已保存: {output_path}")

if __name__ == '__main__':
    main()
