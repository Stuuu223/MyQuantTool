# -*- coding: utf-8 -*-
"""
CTO V110 史诗级大样本物理光谱扫描器

【核心理念】
"高位承接是涨停的入场券，但不是获奖证书"
173个暴力真龙样本，全维光谱分析，坐实"高位维持洗盘"物理真理！

【物理基因指标】
1. 能量重心比例 (Energy Center Ratio) - 真龙是否90%以上在涨停价85%处高位维持
2. 高位成交占比 (High Altitude Ratio) - +10%以上区间成交额占全天比例
3. 惯性衰竭前兆 (Inertia Depletion) - 换手率和动量维持率分布中位数

【输出】
《真龙物理光谱白皮书》- 统计学终局数据

运行方式：
    python tools/massive_collider_scan.py
"""

import os
import sys
import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np

# 添加项目根目录到路径
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
    limit_price = prev_close * (1 + limit_pct)
    return round(limit_price * 100) / 100


def scan_energy_center(stock_code: str, date: str) -> Dict:
    """
    能量重心扫描器
    
    Args:
        stock_code: 股票代码
        date: 日期
        
    Returns:
        Dict: 能量重心指标
    """
    result = {
        'stock_code': stock_code,
        'date': date,
        'success': False,
        'energy_center_ratio': None,
        'high_altitude_ratio': None,
        'low_altitude_ratio': None,
        'sustain_type': None,
        'limit_up_amount': None,
        'limit_up_ratio': None,
        'is_limit_up': False,
        'prev_close': None,
        'limit_price': None,
        'total_amount': None,
        'error': None,
    }
    
    try:
        # 获取日K数据
        daily_data = xtdata.get_local_data(
            field_list=['open', 'high', 'low', 'close', 'volume', 'amount', 'preClose'],
            stock_list=[stock_code],
            period='1d',
            start_time=date,
            end_time=date
        )
        
        if not daily_data or stock_code not in daily_data:
            result['error'] = '无日K数据'
            return result
            
        df_daily = daily_data[stock_code]
        if df_daily is None or len(df_daily) == 0:
            result['error'] = '日K数据为空'
            return result
        
        # 获取关键字段
        prev_close = float(df_daily['preClose'].iloc[0]) if 'preClose' in df_daily.columns else 0.0
        today_high = float(df_daily['high'].iloc[0])
        total_amount = float(df_daily['amount'].iloc[0])
        
        if prev_close <= 0:
            result['error'] = '昨收价为0'
            return result
        
        result['prev_close'] = prev_close
        result['total_amount'] = total_amount
        
        limit_price = get_limit_up_price(stock_code, prev_close)
        result['limit_price'] = limit_price
        
        # 判断是否涨停
        price_tolerance = 0.01
        is_limit_up = abs(today_high - limit_price) < price_tolerance or today_high >= limit_price
        result['is_limit_up'] = is_limit_up
        
        # 获取Tick数据
        tick_data = xtdata.get_local_data(
            field_list=[],
            stock_list=[stock_code],
            period='tick',
            start_time=date,
            end_time=date
        )
        
        if not tick_data or stock_code not in tick_data:
            result['error'] = '无Tick数据'
            return result
            
        df_tick = tick_data[stock_code]
        if df_tick is None or len(df_tick) == 0:
            result['error'] = 'Tick数据为空'
            return result
        
        # 计算增量成交
        prices = df_tick['lastPrice'] if 'lastPrice' in df_tick.columns else df_tick.get('price', df_tick.iloc[:, 1])
        amounts = df_tick['amount'] if 'amount' in df_tick.columns else df_tick.iloc[:, 3]
        
        prev_amount = 0.0
        price_amount_list = []
        
        for i in range(len(df_tick)):
            try:
                price = float(prices.iloc[i]) if hasattr(prices, 'iloc') else float(prices[i])
                amount = float(amounts.iloc[i]) if hasattr(amounts, 'iloc') else float(amounts[i])
                
                if price <= 0:
                    continue
                    
                delta_amount = amount - prev_amount
                prev_amount = amount
                
                if delta_amount > 0:
                    price_amount_list.append((price, delta_amount))
            except Exception:
                continue
        
        if not price_amount_list:
            result['error'] = '无有效Tick成交'
            return result
        
        # 计算能量重心
        total_delta_amount = sum(amt for _, amt in price_amount_list)
        if total_delta_amount <= 0:
            result['error'] = '成交额为0'
            return result
        
        weighted_sum = sum(price * amt for price, amt in price_amount_list)
        energy_center = weighted_sum / total_delta_amount
        
        # 能量重心相对涨停价比例
        if limit_price > prev_close:
            energy_center_ratio = (energy_center - prev_close) / (limit_price - prev_close)
        else:
            energy_center_ratio = 0.0
        
        result['energy_center_ratio'] = energy_center_ratio
        
        # 计算价格区间分布
        zones = {
            '水下': (0, prev_close),
            '低位': (prev_close, prev_close * 1.05),
            '中位': (prev_close * 1.05, prev_close * 1.10),
            '高位': (prev_close * 1.10, prev_close * 1.15),
            '超高位': (prev_close * 1.15, limit_price * 0.99),
            '涨停价': (limit_price * 0.99, limit_price * 1.01),
        }
        
        zone_amounts = {k: 0.0 for k in zones.keys()}
        
        for price, amt in price_amount_list:
            for zone_name, (low, high) in zones.items():
                if low <= price < high:
                    zone_amounts[zone_name] += amt
                    break
        
        # 高位区占比 (+10%以上)
        high_altitude = zone_amounts['高位'] + zone_amounts['超高位'] + zone_amounts['涨停价']
        result['high_altitude_ratio'] = high_altitude / total_delta_amount
        
        # 低位区占比
        low_altitude = zone_amounts['水下'] + zone_amounts['低位']
        result['low_altitude_ratio'] = low_altitude / total_delta_amount
        
        # 计算板上成交（涨停价成交）
        limit_up_amount = zone_amounts['涨停价']
        result['limit_up_amount'] = limit_up_amount
        result['limit_up_ratio'] = limit_up_amount / total_delta_amount if total_delta_amount > 0 else 0
        
        # 判定类型
        if energy_center_ratio >= 0.80 and result['high_altitude_ratio'] > 0.50:
            result['sustain_type'] = '高位强承接'
        elif energy_center_ratio <= 0.30 and result['low_altitude_ratio'] > 0.50:
            result['sustain_type'] = '低位偷袭'
        else:
            result['sustain_type'] = '中性过渡'
        
        result['success'] = True
        
    except Exception as e:
        result['error'] = str(e)
        
    return result


def generate_white_paper(results: List[Dict]) -> str:
    """
    生成《真龙物理光谱白皮书》
    
    Args:
        results: 扫描结果列表
        
    Returns:
        白皮书文本
    """
    # 过滤成功结果
    valid_results = [r for r in results if r['success']]
    failed_count = len(results) - len(valid_results)
    
    if not valid_results:
        return "无有效数据！"
    
    # 提取指标
    energy_ratios = [r['energy_center_ratio'] for r in valid_results if r['energy_center_ratio'] is not None]
    high_altitudes = [r['high_altitude_ratio'] for r in valid_results if r['high_altitude_ratio'] is not None]
    low_altitudes = [r['low_altitude_ratio'] for r in valid_results if r['low_altitude_ratio'] is not None]
    limit_up_ratios = [r['limit_up_ratio'] for r in valid_results if r['limit_up_ratio'] is not None]
    sustain_types = [r['sustain_type'] for r in valid_results if r['sustain_type']]
    is_limit_ups = [r['is_limit_up'] for r in valid_results]
    
    # 统计函数
    def stats(values):
        if not values:
            return {'mean': 0, 'median': 0, 'p90': 0, 'min': 0, 'max': 0}
        return {
            'mean': np.mean(values),
            'median': np.median(values),
            'p90': np.percentile(values, 90) if len(values) >= 10 else np.max(values),
            'min': np.min(values),
            'max': np.max(values),
        }
    
    energy_stats = stats(energy_ratios)
    high_stats = stats(high_altitudes)
    low_stats = stats(low_altitudes)
    limit_up_stats = stats(limit_up_ratios)
    
    # 类型分布
    type_counts = {}
    for t in sustain_types:
        type_counts[t] = type_counts.get(t, 0) + 1
    
    # 涨停比例
    limit_up_count = sum(is_limit_ups)
    limit_up_pct = limit_up_count / len(valid_results) * 100 if valid_results else 0
    
    # 生成白皮书
    white_paper = f"""
{'='*70}
                    《真龙物理光谱白皮书》
                CTO V110 史诗级大样本扫描报告
{'='*70}

【样本概览】
  总样本数: {len(results)}
  有效样本: {len(valid_results)}
  失败样本: {failed_count}
  涨停样本: {limit_up_count} ({limit_up_pct:.1f}%)

{'='*70}
【物理基因一：能量重心比例】
  定义: 能量重心相对涨停价的位置比例
  物理意义: 主力在哪个水位做了最大的功
  
  均值: {energy_stats['mean']*100:.1f}%
  中位数: {energy_stats['median']*100:.1f}%
  90%分位: {energy_stats['p90']*100:.1f}%
  最小值: {energy_stats['min']*100:.1f}%
  最大值: {energy_stats['max']*100:.1f}%
  
  【CTO关键发现】
  能量重心>=80%的样本数: {sum(1 for e in energy_ratios if e >= 0.80)} ({sum(1 for e in energy_ratios if e >= 0.80)/len(energy_ratios)*100:.1f}%)
  能量重心>=85%的样本数: {sum(1 for e in energy_ratios if e >= 0.85)} ({sum(1 for e in energy_ratios if e >= 0.85)/len(energy_ratios)*100:.1f}%)

{'='*70}
【物理基因二：高位成交占比】
  定义: 价格在+10%以上区间的成交额占全天比例
  物理意义: 高位换手洗盘的资金投入程度
  
  均值: {high_stats['mean']*100:.1f}%
  中位数: {high_stats['median']*100:.1f}%
  90%分位: {high_stats['p90']*100:.1f}%
  最小值: {high_stats['min']*100:.1f}%
  最大值: {high_stats['max']*100:.1f}%
  
  【CTO关键发现】
  高位成交>=50%的样本数: {sum(1 for h in high_altitudes if h >= 0.50)} ({sum(1 for h in high_altitudes if h >= 0.50)/len(high_altitudes)*100:.1f}%)
  高位成交>=60%的样本数: {sum(1 for h in high_altitudes if h >= 0.60)} ({sum(1 for h in high_altitudes if h >= 0.60)/len(high_altitudes)*100:.1f}%)

{'='*70}
【物理基因三：板上成交占比】
  定义: 涨停价成交额占全天比例
  物理意义: 封板时的真实做功强度
  
  均值: {limit_up_stats['mean']*100:.1f}%
  中位数: {limit_up_stats['median']*100:.1f}%
  90%分位: {limit_up_stats['p90']*100:.1f}%

{'='*70}
【能量重心类型分布】
"""
    
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = count / len(sustain_types) * 100 if sustain_types else 0
        white_paper += f"  {t}: {count} ({pct:.1f}%)\n"
    
    white_paper += f"""
{'='*70}
【CTO终极结论】

1. 【高位强承接定律】
   - 真龙能量重心中位数: {energy_stats['median']*100:.1f}%
   - 真龙高位成交中位数: {high_stats['median']*100:.1f}%
   - 结论: {'符合"高位维持洗盘"物理规律！' if energy_stats['median'] >= 0.70 else '需进一步验证'}
   
2. 【入场券阈值建议】
   - 能量重心阈值: >= 70% (当前{sum(1 for e in energy_ratios if e >= 0.70)/len(energy_ratios)*100:.1f}%样本达标)
   - 高位成交阈值: >= 40% (当前{sum(1 for h in high_altitudes if h >= 0.40)/len(high_altitudes)*100:.1f}%样本达标)
   
3. 【假龙排雷线】
   - 能量重心< 30%: 偷袭嫌疑
   - 高位成交< 20%: 真空区阻力小但高位承接不足

{'='*70}
                    物理真理永存！
{'='*70}
"""
    
    return white_paper


def main():
    print("="*70)
    print("CTO V110 史诗级大样本物理光谱扫描器")
    print("173只暴力真龙，全维光谱分析！")
    print("="*70)
    
    # 读取样本数据
    samples_path = os.path.join(ROOT, 'data', 'validation', 'recent_samples_2025_2026.csv')
    
    if not os.path.exists(samples_path):
        print(f"[ERROR] 样本文件不存在: {samples_path}")
        return
    
    df = pd.read_csv(samples_path)
    
    # 只取violent_surge样本(label=1)
    surge_samples = df[df['label'] == 1].copy()
    total_samples = len(surge_samples)
    
    print(f"\n[样本库] 共{total_samples}个violent_surge样本")
    
    # 扫描
    results = []
    success_count = 0
    fail_count = 0
    
    for idx, row in surge_samples.iterrows():
        stock_code = row['stock_code']
        date = str(row['date'])
        
        print(f"\r[扫描中] {stock_code} {date} ({idx+1}/{total_samples}) 成功:{success_count} 失败:{fail_count}", end='', flush=True)
        
        result = scan_energy_center(stock_code, date)
        results.append(result)
        
        if result['success']:
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\n\n[扫描完成] 成功:{success_count} 失败:{fail_count}")
    
    # 生成白皮书
    white_paper = generate_white_paper(results)
    print(white_paper)
    
    # 保存结果
    output_dir = os.path.join(ROOT, 'data', 'research_lab')
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存详细结果
    df_results = pd.DataFrame(results)
    results_path = os.path.join(output_dir, 'massive_collider_scan_results.csv')
    df_results.to_csv(results_path, index=False, encoding='utf-8-sig')
    print(f"\n详细结果已保存至: {results_path}")
    
    # 保存白皮书
    white_paper_path = os.path.join(output_dir, 'physics_white_paper.txt')
    with open(white_paper_path, 'w', encoding='utf-8') as f:
        f.write(white_paper)
    print(f"白皮书已保存至: {white_paper_path}")


if __name__ == '__main__':
    main()
