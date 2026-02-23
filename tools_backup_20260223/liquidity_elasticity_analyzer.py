#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO Phase 3】流通市值弹性比分析器

解决老板灵魂拷问：
"35.9万？那我再工作一年充点钱我也是主力了"

核心指标：
1. 5分钟换手率 = 成交额 / 流通市值
2. 资金驱动效率 = 涨幅 / 换手率 (每1%换手推动多少涨幅)
3. 流通市值弹性比 = 涨幅 / (资金/流通市值)

志特新材疑问：
- 流通市值约25亿
- 5分钟35.9万资金推动+2.03%
- 换手率 = 35.9万/25亿 = 0.014% (极低)
- 资金驱动效率 = 2.03% / 0.014% = 145 (极高)

这意味着：极少的资金撬动了极大的涨幅，可能是：
A) 抛压真空(卖盘枯竭)
B) 量化对倒(自买自卖)
C) 数据仍有问题
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from xtquant import xtdata

# 流通市值数据 (股价 × 流通股本)
STOCK_INFO = {
    '300017.SZ': {
        'name': '网宿科技',
        'float_volume': 2306141629,  # 股
        'price_avg': 12.0,  # 均价约12元
        'float_market_cap': 2306141629 * 12.0  # 约277亿
    },
    '301005.SZ': {
        'name': '超捷股份',
        'float_volume': 836269091,
        'price_avg': 65.0,
        'float_market_cap': 836269091 * 65.0  # 约543亿
    },
    '300986.SZ': {
        'name': '志特新材',
        'float_volume': 246000000,
        'price_avg': 11.0,
        'float_market_cap': 246000000 * 11.0  # 约27亿
    }
}


def get_tick_data(stock_code, date):
    """获取tick数据"""
    try:
        result = xtdata.get_local_data(
            field_list=['time', 'volume', 'lastPrice'],
            stock_list=[stock_code],
            period='tick',
            start_time=date,
            end_time=date
        )
        if result and stock_code in result:
            df = result[stock_code].copy()
            if not df.empty:
                df['dt'] = pd.to_datetime(df['time'], unit='ms') + timedelta(hours=8)
                return df[df['lastPrice'] > 0]
        return None
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        return None


def analyze_liquidity_elasticity(stock_code, date, window_time):
    """
    分析流通市值弹性比
    
    计算：
    1. 5分钟换手率 = 成交额 / 流通市值
    2. 资金驱动效率 = 涨幅 / 换手率
    3. 对比全网同类股票
    """
    info = STOCK_INFO.get(stock_code)
    if not info:
        print(f"❌ 未找到{stock_code}信息")
        return None
    
    print(f"\n{'='*70}")
    print(f"【流通市值弹性分析】{stock_code} {info['name']}")
    print(f"日期: {date} 窗口: {window_time}")
    print(f"{'='*70}")
    
    print(f"\n基础数据:")
    print(f"  流通股本: {info['float_volume']/1e8:.2f}亿股")
    print(f"  参考均价: {info['price_avg']:.2f}元")
    print(f"  流通市值: {info['float_market_cap']/1e8:.1f}亿元")
    
    # 获取tick数据
    df = get_tick_data(stock_code, date)
    if df is None or df.empty:
        print("❌ 无数据")
        return None
    
    # 5分钟聚合
    df = df.sort_values('dt').copy()
    df['vol_delta'] = df['volume'].diff().fillna(df['volume'].iloc[0])
    df['vol_delta'] = df['vol_delta'].clip(lower=0)
    
    df = df.set_index('dt')
    resampled = df.resample('5min', label='left', closed='left').agg({
        'vol_delta': 'sum',
        'lastPrice': 'last'
    })
    resampled = resampled.dropna()
    
    if resampled.empty:
        print("❌ 无有效窗口")
        return None
    
    # 找到目标窗口
    target_hour = int(window_time.split(':')[0])
    target_minute = int(window_time.split(':')[1])
    
    window_data = None
    for dt, row in resampled.iterrows():
        if dt.hour == target_hour and dt.minute == target_minute:
            window_data = {
                'time': dt.strftime('%H:%M'),
                'volume': row['vol_delta'],
                'price': row['lastPrice'],
                'amount': row['vol_delta'] * row['lastPrice']
            }
            break
    
    if not window_data:
        print(f"❌ 未找到{window_time}窗口")
        return None
    
    # 核心计算
    amount = window_data['amount']  # 成交额(元)
    float_cap = info['float_market_cap']  # 流通市值(元)
    
    # 1. 5分钟换手率
    turnover_5min = amount / float_cap * 100  # 百分比
    
    # 2. 资金密度 = 成交额 / 流通市值 (无量纲)
    money_density = amount / float_cap
    
    # 3. 获取该窗口的价格变化(需要更多上下文)
    # 简化：用全天的最高涨幅作为参考
    day_open = df['lastPrice'].iloc[0]
    day_close = df['lastPrice'].iloc[-1]
    max_price = df['lastPrice'].max()
    day_change = (day_close - day_open) / day_open * 100
    max_change = (max_price - day_open) / day_open * 100
    
    print(f"\n窗口数据 ({window_time}):")
    print(f"  成交额: {amount/10000:.1f}万元")
    print(f"  价格: {window_data['price']:.2f}元")
    
    print(f"\n【核心指标】")
    print(f"  5分钟换手率: {turnover_5min:.4f}%")
    print(f"  资金密度: {money_density:.6f} ({money_density*1e4:.2f}个基点)")
    
    print(f"\n【全天对比】")
    print(f"  日内最高涨幅: {max_change:.2f}%")
    print(f"  日内收盘涨幅: {day_change:.2f}%")
    
    # 如果这是最高潮窗口，计算资金驱动效率
    if max_change > 0 and turnover_5min > 0:
        # 估算：假设这个窗口贡献了主要涨幅
        efficiency = max_change / turnover_5min
        print(f"\n【资金驱动效率】(估算)")
        print(f"  每1%换手推动涨幅: {efficiency:.2f}%")
        print(f"  解读: 花费{turnover_5min:.4f}%流通市值的资金，推动{max_change:.2f}%涨幅")
        
        if efficiency > 100:
            print(f"  ⚠️ 效率极高({efficiency:.0f})，可能是抛压真空或数据异常")
        elif efficiency > 50:
            print(f"  🔥 效率很高({efficiency:.0f})，强主力控盘")
        elif efficiency > 20:
            print(f"  ✅ 效率正常({efficiency:.0f})，市场合力")
        else:
            print(f"  📉 效率偏低({efficiency:.0f})，抛压较大")
    
    return {
        'stock_code': stock_code,
        'date': date,
        'window_time': window_time,
        'amount_wan': amount / 10000,
        'turnover_5min_pct': turnover_5min,
        'money_density': money_density,
        'day_change_pct': day_change,
        'max_change_pct': max_change
    }


def cross_stock_comparison():
    """跨股票资金效率对比"""
    print(f"\n{'='*70}")
    print("【三只黄金标杆对比】")
    print(f"{'='*70}")
    
    cases = [
        ('300017.SZ', '20260126', '11:25', '网宿科技'),
        ('301005.SZ', '20251205', '09:30', '超捷股份'),
        ('300986.SZ', '20251231', '14:25', '志特新材-首扬'),
        ('300986.SZ', '20260105', '09:40', '志特新材-接力'),
    ]
    
    results = []
    for code, date, time, name in cases:
        result = analyze_liquidity_elasticity(code, date, time)
        if result:
            results.append((name, result))
    
    # 汇总表格
    print(f"\n{'='*70}")
    print("【资金效率对比表】")
    print(f"{'='*70}")
    print(f'{"标的":<20}{"资金(万)":<12}{"5min换手%":<12}{"日内涨幅%":<12}{"效率":<10}')
    print('-'*70)
    
    for name, r in results:
        efficiency = r['max_change_pct'] / r['turnover_5min_pct'] if r['turnover_5min_pct'] > 0 else 0
        print(f"{name:<20}{r['amount_wan']:<12.1f}{r['turnover_5min_pct']:<12.4f}"
              f"{r['max_change_pct']:<12.2f}{efficiency:<10.1f}")
    
    return results


if __name__ == '__main__':
    print('='*70)
    print('【CTO Phase 3】流通市值弹性比分析')
    print('='*70)
    print("\n老板质疑：35.9万就能当主力？")
    print("CTO回答：要看占流通市值的比例！")
    print('='*70)
    
    # 详细分析志特新材
    print("\n" + "="*70)
    print("深度分析：志特新材12.31尾盘爆发")
    print("="*70)
    zhite_1231 = analyze_liquidity_elasticity('300986.SZ', '20251231', '14:25')
    
    print("\n" + "="*70)
    print("深度分析：志特新材01.05早盘接力")
    print("="*70)
    zhite_0105 = analyze_liquidity_elasticity('300986.SZ', '20260105', '09:40')
    
    # 全面对比
    all_results = cross_stock_comparison()
    
    # 结论
    print(f"\n{'='*70}")
    print("【结论与建议】")
    print(f"{'='*70}")
    
    print("\n1. 绝对资金阈值的问题:")
    print("   网宿科技: 828万 (大盘股)")
    print("   超捷股份: 620万 (中盘股)")
    print("   志特新材: 35-170万 (小盘股)")
    print("   → 绝对资金无法横向比较！")
    
    print("\n2. 统一指标建议:")
    print("   5分钟换手率 > 0.01% (志特12.31为0.014%)")
    print("   资金驱动效率 > 50 (每1%换手推动50%涨幅)")
    
    print("\n3. 志特新材数据合理性:")
    if zhite_1231:
        turnover = zhite_1231['turnover_5min_pct']
        if turnover < 0.01:
            print(f"   ⚠️ 换手率{turnover:.4f}%过低，可能存在数据遗漏")
        else:
            print(f"   ✅ 换手率{turnover:.4f}%虽低，但符合小盘股特征")
            print(f"   小盘股27亿流通市值，35万资金占0.013%，可撬动2%涨幅")
    
    # 保存结果
    output = Path('data/liquidity_elasticity_analysis.json')
    with open(output, 'w', encoding='utf-8') as f:
        json.dump([r[1] for r in all_results], f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 分析完成，结果保存: {output}")
