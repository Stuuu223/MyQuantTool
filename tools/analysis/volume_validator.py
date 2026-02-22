#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO紧急审计】验证tick累加成交额 vs 真实日线数据

团队报告：志特新材12.31全天成交525万，换手率0.19%
CTO质疑：真实成交额应该是上亿元，换手率10-20%

验证方法：
1. 通过akshare获取日线数据（真实成交额）
2. 对比QMT tick累加结果
3. 检查tick数据完整性
"""

import pandas as pd
from datetime import datetime, timedelta
from xtquant import xtdata

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️ akshare未安装，使用xtdata日线数据对比")


def get_qmt_tick_volume(stock_code, date):
    """从QMT获取tick数据并累加"""
    print(f"\n{'='*60}")
    print(f"【QMT Tick数据】{stock_code} - {date}")
    print(f"{'='*60}")
    
    result = xtdata.get_local_data(
        field_list=['time', 'volume', 'lastPrice'],
        stock_list=[stock_code],
        period='tick',
        start_time=date,
        end_time=date
    )
    
    if not result or stock_code not in result:
        print("❌ 无tick数据")
        return None
    
    df = result[stock_code]
    print(f"Tick数据条数: {len(df)}")
    
    if df.empty:
        return None
    
    # UTC+8转换
    df['dt'] = pd.to_datetime(df['time'], unit='ms') + timedelta(hours=8)
    df = df[df['lastPrice'] > 0]
    
    # 计算成交量增量
    df = df.sort_values('dt')
    df['vol_delta'] = df['volume'].diff().fillna(df['volume'].iloc[0])
    df['vol_delta'] = df['vol_delta'].clip(lower=0)
    
    # 累加成交额
    df['amount'] = df['vol_delta'] * df['lastPrice']
    total_volume = df['vol_delta'].sum()
    total_amount = df['amount'].sum()
    
    # 价格统计
    open_price = df['lastPrice'].iloc[0]
    close_price = df['lastPrice'].iloc[-1]
    high_price = df['lastPrice'].max()
    low_price = df['lastPrice'].min()
    
    print(f"\n价格统计:")
    print(f"  开盘: {open_price:.2f}")
    print(f"  收盘: {close_price:.2f}")
    print(f"  最高: {high_price:.2f}")
    print(f"  最低: {low_price:.2f}")
    print(f"  涨幅: {(close_price - open_price) / open_price * 100:.2f}%")
    
    print(f"\n成交统计:")
    print(f"  总成交量: {total_volume:,.0f}股")
    print(f"  总成交额: {total_amount:,.0f}元 ({total_amount/10000:.1f}万)")
    
    return {
        'total_volume': total_volume,
        'total_amount': total_amount,
        'tick_count': len(df),
        'open': open_price,
        'close': close_price,
        'high': high_price,
        'low': low_price
    }


def get_daily_data_from_akshare(stock_code, date):
    """从akshare获取日线数据"""
    if not AKSHARE_AVAILABLE:
        return None
    
    print(f"\n{'='*60}")
    print(f"【AkShare日线数据】{stock_code} - {date}")
    print(f"{'='*60}")
    
    try:
        # 转换股票代码格式
        code = stock_code.split('.')[0]
        
        # 获取日线数据
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=date,
            end_date=date,
            adjust=""
        )
        
        if df.empty:
            print("❌ 无日线数据")
            return None
        
        row = df.iloc[0]
        print(f"日期: {row['日期']}")
        print(f"开盘: {row['开盘']:.2f}")
        print(f"收盘: {row['收盘']:.2f}")
        print(f"最高: {row['最高']:.2f}")
        print(f"最低: {row['最低']:.2f}")
        print(f"成交量: {row['成交量']:,.0f}手")
        print(f"成交额: {row['成交额']:,.0f}元 ({row['成交额']/10000:.1f}万)")
        print(f"振幅: {row['振幅']:.2f}%")
        print(f"涨跌幅: {row['涨跌幅']:.2f}%")
        print(f"换手率: {row['换手率']:.2f}%")
        
        return {
            'open': row['开盘'],
            'close': row['收盘'],
            'high': row['最高'],
            'low': row['最低'],
            'volume': row['成交量'] * 100,  # 手转股
            'amount': row['成交额'],
            'turnover': row['换手率']
        }
    except Exception as e:
        print(f"❌ 获取akshare数据失败: {e}")
        return None


def get_daily_data_from_qmt(stock_code, date):
    """从QMT获取日线数据作为对比"""
    print(f"\n{'='*60}")
    print(f"【QMT日线数据】{stock_code} - {date}")
    print(f"{'='*60}")
    
    try:
        result = xtdata.get_local_data(
            field_list=['open', 'close', 'high', 'low', 'volume', 'amount'],
            stock_list=[stock_code],
            period='1d',
            start_time=date,
            end_time=date
        )
        
        if not result or stock_code not in result:
            print("❌ 无日线数据")
            return None
        
        df = result[stock_code]
        if df.empty:
            return None
        
        row = df.iloc[0]
        print(f"开盘: {row['open']:.2f}")
        print(f"收盘: {row['close']:.2f}")
        print(f"最高: {row['high']:.2f}")
        print(f"最低: {row['low']:.2f}")
        print(f"成交量: {row['volume']:,.0f}")
        print(f"成交额: {row['amount']:,.0f} ({row['amount']/10000:.1f}万)")
        
        return {
            'open': row['open'],
            'close': row['close'],
            'high': row['high'],
            'low': row['low'],
            'volume': row['volume'],
            'amount': row['amount']
        }
    except Exception as e:
        print(f"❌ 获取QMT日线失败: {e}")
        return None


def verify_data_integrity(stock_code, date):
    """验证数据完整性"""
    print(f"\n{'='*70}")
    print(f"【CTO紧急审计】{stock_code} - {date}")
    print(f"{'='*70}")
    
    # 1. 获取tick累加数据
    tick_data = get_qmt_tick_volume(stock_code, date)
    
    # 2. 获取日线数据（优先akshare，其次qmt）
    daily_data = get_daily_data_from_akshare(stock_code, date)
    if not daily_data:
        daily_data = get_daily_data_from_qmt(stock_code, date)
    
    if not tick_data or not daily_data:
        print("\n❌ 数据不足，无法验证")
        return
    
    # 3. 对比
    print(f"\n{'='*70}")
    print("【数据对比审计】")
    print(f"{'='*70}")
    
    print(f"\n{'指标':<20}{'Tick累加':<20}{'日线数据':<20}{'差异':<15}")
    print('-'*70)
    
    # 成交额对比
    tick_amount = tick_data['total_amount']
    daily_amount = daily_data['amount']
    amount_diff_pct = abs(tick_amount - daily_amount) / daily_amount * 100 if daily_amount > 0 else 0
    
    print(f"{'成交额':<20}{tick_amount/10000:>15.1f}万{daily_amount/10000:>18.1f}万{amount_diff_pct:>12.1f}%")
    
    # 成交量对比
    tick_volume = tick_data['total_volume']
    daily_volume = daily_data['volume']
    volume_diff_pct = abs(tick_volume - daily_volume) / daily_volume * 100 if daily_volume > 0 else 0
    
    print(f"{'成交量':<20}{tick_volume/10000:>15.1f}万{daily_volume/10000:>18.1f}万{volume_diff_pct:>12.1f}%")
    
    # 结论
    print(f"\n{'='*70}")
    print("【审计结论】")
    print(f"{'='*70}")
    
    if amount_diff_pct > 10:
        print(f"🔴 CRITICAL: 成交额差异{amount_diff_pct:.1f}% > 10%，数据严重不完整！")
        print(f"   团队报告: {tick_amount/10000:.1f}万")
        print(f"   真实数据: {daily_amount/10000:.1f}万")
        print(f"   遗漏金额: {(daily_amount - tick_amount)/10000:.1f}万")
        
        if 'turnover' in daily_data:
            print(f"\n   真实换手率: {daily_data['turnover']:.2f}%")
    elif amount_diff_pct > 5:
        print(f"🟡 WARNING: 成交额差异{amount_diff_pct:.1f}% > 5%，数据可能不完整")
    else:
        print(f"✅ PASS: 成交额差异{amount_diff_pct:.1f}% < 5%，数据基本完整")
    
    # Tick数据量评估
    tick_count = tick_data['tick_count']
    expected_ticks = 4800  # 正常交易日约4800个tick
    
    print(f"\n   Tick数据量: {tick_count} / {expected_ticks} (预期)")
    if tick_count < expected_ticks * 0.5:
        print(f"   ⚠️ Tick数据量严重不足，可能只有{(tick_count/expected_ticks*100):.0f}%")
    elif tick_count < expected_ticks * 0.8:
        print(f"   ⚠️ Tick数据量偏少，约{(tick_count/expected_ticks*100):.0f}%")
    else:
        print(f"   ✅ Tick数据量正常")


if __name__ == '__main__':
    print('='*70)
    print('【CTO紧急审计】志特新材12.31数据验证')
    print('='*70)
    print("\n团队报告: 全天成交525万，换手率0.19%")
    print("CTO质疑: 应该是上亿元，换手率10-20%")
    print('='*70)
    
    # 验证志特新材
    verify_data_integrity('300986.SZ', '20251231')
    
    # 同时验证网宿科技作为对比
    print(f"\n\n{'='*70}")
    print("【对比验证】网宿科技01.26")
    print(f"{'='*70}")
    verify_data_integrity('300017.SZ', '20260126')
