#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO Phase 3】数据完整性验证器

验证志特新材12.31的tick数据是否完整

问题：资金驱动效率异常高(733)，可能是：
A) 数据缺失（tick数据不完整）
B) 抛压真空（卖盘枯竭）

验证方法：
1. 检查tick数据条数（正常交易日应有4000-5000条）
2. 计算全天总成交额，对比东方财富等公开数据
3. 分析成交量分布，看是否有明显的数据空洞
"""

import pandas as pd
from datetime import timedelta
from xtquant import xtdata

STOCKS = {
    '300986.SZ': {'name': '志特新材', 'date': '20251231', 'float_volume': 246000000},
    '300017.SZ': {'name': '网宿科技', 'date': '20260126', 'float_volume': 2306141629},
    '301005.SZ': {'name': '超捷股份', 'date': '20251205', 'float_volume': 836269091},
}


def check_data_integrity(stock_code, date, stock_info):
    """检查数据完整性"""
    print(f"\n{'='*70}")
    print(f"【数据完整性检查】{stock_code} {stock_info['name']} - {date}")
    print(f"{'='*70}")
    
    # 获取tick数据
    result = xtdata.get_local_data(
        field_list=['time', 'volume', 'lastPrice'],
        stock_list=[stock_code],
        period='tick',
        start_time=date,
        end_time=date
    )
    
    if not result or stock_code not in result:
        print("❌ 无数据")
        return None
    
    df = result[stock_code]
    if df.empty:
        print("❌ 数据为空")
        return None
    
    # 基础统计
    total_ticks = len(df)
    print(f"\n1. Tick数据量: {total_ticks}条")
    
    # 时间范围
    df['dt'] = pd.to_datetime(df['time'], unit='ms') + timedelta(hours=8)
    first_time = df['dt'].iloc[0]
    last_time = df['dt'].iloc[-1]
    print(f"2. 时间范围: {first_time.strftime('%H:%M:%S')} - {last_time.strftime('%H:%M:%S')}")
    
    # 价格统计
    df_valid = df[df['lastPrice'] > 0]
    if df_valid.empty:
        print("❌ 无有效价格数据")
        return None
    
    open_price = df_valid['lastPrice'].iloc[0]
    close_price = df_valid['lastPrice'].iloc[-1]
    high_price = df_valid['lastPrice'].max()
    low_price = df_valid['lastPrice'].min()
    
    print(f"\n3. 价格统计:")
    print(f"   开盘: {open_price:.2f}")
    print(f"   收盘: {close_price:.2f}")
    print(f"   最高: {high_price:.2f}")
    print(f"   最低: {low_price:.2f}")
    print(f"   涨幅: {(close_price - open_price) / open_price * 100:.2f}%")
    
    # 成交量分析
    df_valid = df_valid.sort_values('dt').copy()
    df_valid['vol_delta'] = df_valid['volume'].diff().fillna(df_valid['volume'].iloc[0])
    df_valid['vol_delta'] = df_valid['vol_delta'].clip(lower=0)
    
    total_volume = df_valid['vol_delta'].sum()
    total_amount = (df_valid['vol_delta'] * df_valid['lastPrice']).sum()
    
    print(f"\n4. 成交统计:")
    print(f"   总成交量: {total_volume/10000:.1f}万股")
    print(f"   总成交额: {total_amount/10000:.1f}万元")
    print(f"   均价: {total_amount/total_volume:.2f}元")
    
    # 换手率
    turnover_rate = total_volume / stock_info['float_volume'] * 100
    print(f"   全天换手率: {turnover_rate:.2f}%")
    
    # 数据质量评估
    print(f"\n5. 数据质量评估:")
    if total_ticks < 1000:
        print(f"   ⚠️ Tick数据量偏少({total_ticks})，可能不完整")
    elif total_ticks < 3000:
        print(f"   ⚠️ Tick数据量较少({total_ticks})，可能有缺失")
    else:
        print(f"   ✅ Tick数据量正常({total_ticks})")
    
    # 检查是否有明显的时间空洞
    df_valid = df_valid.set_index('dt')
    time_diff = df_valid.index.to_series().diff().dt.total_seconds()
    large_gaps = time_diff[time_diff > 300]  # 大于5分钟的空洞
    
    if len(large_gaps) > 0:
        print(f"\n   ⚠️ 发现{len(large_gaps)}个时间空洞(>5分钟):")
        for gap_time in large_gaps.head(3).index:
            gap_duration = large_gaps[gap_time]
            print(f"      {gap_time.strftime('%H:%M:%S')} - 空洞{gap_duration:.0f}秒")
    else:
        print(f"   ✅ 无显著时间空洞")
    
    # 5分钟窗口统计
    df_valid = df_valid.reset_index()
    resampled = df_valid.resample('5min', on='dt', label='left', closed='left').agg({
        'vol_delta': 'sum',
        'lastPrice': 'last'
    })
    resampled = resampled.dropna()
    
    # 找出资金量最大的窗口
    resampled['amount'] = resampled['vol_delta'] * resampled['lastPrice']
    max_amount_window = resampled['amount'].idxmax()
    max_amount = resampled.loc[max_amount_window, 'amount']
    
    print(f"\n6. 5分钟窗口分析:")
    print(f"   总窗口数: {len(resampled)}")
    print(f"   最大资金窗口: {max_amount_window.strftime('%H:%M')}")
    print(f"   最大资金: {max_amount/10000:.1f}万元")
    
    # 全天资金分布
    morning_amount = resampled[resampled.index.hour < 11]['amount'].sum()
    afternoon_amount = resampled[resampled.index.hour >= 13]['amount'].sum()
    
    print(f"\n7. 资金时段分布:")
    print(f"   上午(09:30-11:30): {morning_amount/10000:.1f}万元 ({morning_amount/total_amount*100:.1f}%)")
    print(f"   下午(13:00-15:00): {afternoon_amount/10000:.1f}万元 ({afternoon_amount/total_amount*100:.1f}%)")
    
    return {
        'stock_code': stock_code,
        'date': date,
        'total_ticks': total_ticks,
        'total_volume': total_volume,
        'total_amount': total_amount,
        'turnover_rate': turnover_rate,
        'price_change': (close_price - open_price) / open_price * 100
    }


if __name__ == '__main__':
    print('='*70)
    print('【CTO Phase 3】数据完整性验证')
    print('='*70)
    
    results = []
    for code, info in STOCKS.items():
        result = check_data_integrity(code, info['date'], info)
        if result:
            results.append(result)
    
    # 汇总对比
    print(f"\n{'='*70}")
    print("【三只标杆数据完整性对比】")
    print(f"{'='*70}")
    print(f'{"标的":<15}{"Tick数":<10}{"成交额(万)":<12}{"换手率%":<12}{"涨幅%":<10}')
    print('-'*70)
    
    for r in results:
        print(f"{r['stock_code']:<15}{r['total_ticks']:<10}{r['total_amount']/10000:<12.1f}"
              f"{r['turnover_rate']:<12.2f}{r['price_change']:<10.2f}")
    
    print(f"\n{'='*70}")
    print("【结论】")
    print(f"{'='*70}")
    
    # 检查是否有异常
    zhite = next((r for r in results if '300986' in r['stock_code']), None)
    wangsu = next((r for r in results if '300017' in r['stock_code']), None)
    
    if zhite and wangsu:
        print(f"\n志特新材 vs 网宿科技:")
        print(f"  Tick数据: {zhite['total_ticks']} vs {wangsu['total_ticks']}")
        print(f"  全天换手: {zhite['turnover_rate']:.2f}% vs {wangsu['turnover_rate']:.2f}%")
        print(f"  全天成交: {zhite['total_amount']/10000:.1f}万 vs {wangsu['total_amount']/10000:.1f}万")
        
        if zhite['total_ticks'] < wangsu['total_ticks'] * 0.5:
            print(f"\n  ⚠️ 志特新材tick数据量明显偏少，可能存在数据缺失！")
        else:
            print(f"\n  ✅ 数据量正常")
        
        if zhite['turnover_rate'] < 5:
            print(f"  ⚠️ 全天换手率仅{zhite['turnover_rate']:.2f}%，低于活跃标准")
        else:
            print(f"  ✅ 换手率正常")
    
    print(f"\n{'='*70}")
