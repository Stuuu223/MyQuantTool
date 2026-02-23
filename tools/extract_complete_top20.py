#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取12.31和1.5的完整Top 20数据
用真实历史数据验证后续走势
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
from xtquant import xtdata

def get_pre_close(stock_code, date_str):
    """获取昨收价 - 使用Tushare获取前一天的收盘价"""
    try:
        import tushare as ts
        
        # 从config读取token
        token_path = Path('config/tushare_token.txt')
        if token_path.exists():
            token = token_path.read_text().strip()
        else:
            token = '1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b'
        
        pro = ts.pro_api(token)
        
        # 转换日期格式
        date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        
        # 获取前一个交易日
        df_trade = pro.trade_cal(exchange='', start_date='20251201', end_date=date_fmt)
        trade_dates = df_trade[df_trade['is_open']==1]['cal_date'].tolist()
        
        if len(trade_dates) >= 2:
            prev_date = trade_dates[-2]  # 前一个交易日
            
            # 获取前一天数据
            df_daily = pro.daily(ts_code=stock_code, trade_date=prev_date)
            if not df_daily.empty:
                return float(df_daily.iloc[0]['close'])
    except Exception as e:
        print(f"  获取昨收价失败: {e}")
    
    return None

def analyze_stock_day(stock_code, date_str, name=""):
    """分析单只股票单日数据"""
    
    result = xtdata.get_local_data(
        field_list=['time', 'volume', 'lastPrice', 'amount'],
        stock_list=[stock_code],
        period='tick',
        start_time=date_str,
        end_time=date_str
    )
    
    if not result or stock_code not in result:
        return None
    
    df = result[stock_code].copy()
    if df.empty:
        return None
    
    # UTC+8转换
    df['dt'] = pd.to_datetime(df['time'], unit='ms') + timedelta(hours=8)
    df = df[df['lastPrice'] > 0]
    
    if df.empty:
        return None
    
    # 计算成交量增量
    df['vol_delta'] = df['volume'].diff().fillna(df['volume'].iloc[0])
    df['vol_delta'] = df['vol_delta'].clip(lower=0) * 100  # 手→股
    
    # 获取关键价格
    open_price = df.iloc[0]['lastPrice']
    close_price = df.iloc[-1]['lastPrice']
    high_price = df['lastPrice'].max()
    low_price = df['lastPrice'].min()
    
    # 获取昨收价
    pre_close = get_pre_close(stock_code, date_str)
    if pre_close is None:
        pre_close = open_price * 0.97  # 估算
    
    # 真实涨幅
    true_change = (close_price - pre_close) / pre_close * 100
    
    # 09:40数据
    time_0940 = pd.Timestamp(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} 09:40:00")
    df_0940 = df[df['dt'] <= time_0940]
    
    if not df_0940.empty:
        price_0940 = df_0940.iloc[-1]['lastPrice']
        change_0940 = (price_0940 - pre_close) / pre_close * 100
        vol_0940 = df_0940['vol_delta'].sum()
    else:
        price_0940 = open_price
        change_0940 = (open_price - pre_close) / pre_close * 100
        vol_0940 = 0
    
    # 全天统计
    total_volume = df['vol_delta'].sum()
    
    # 涨停判断（创业板20%，主板10%）
    is_limit_up = true_change >= 19.5 if stock_code.startswith('3') else true_change >= 9.5
    
    return {
        'stock_code': stock_code,
        'name': name,
        'date': date_str,
        'pre_close': float(pre_close),
        'open_price': float(open_price),
        'close_price': float(close_price),
        'high_price': float(high_price),
        'low_price': float(low_price),
        'true_change_pct': round(float(true_change), 2),
        'is_limit_up': bool(is_limit_up),
        'price_0940': float(price_0940),
        'change_0940': round(float(change_0940), 2),
        'vol_0940': int(vol_0940),
        'total_volume': int(total_volume),
        'tick_count': int(len(df))
    }

def extract_top20_complete():
    """提取完整的Top 20数据"""
    
    print('='*100)
    print('【完整Top 20数据提取】')
    print('='*100)
    
    # 读取66只票
    df = pd.read_csv('data/cleaned_candidates_66.csv')
    stock_list = df.set_index('ts_code')['name'].to_dict()
    
    # 提取12月31日数据
    print('\n【12月31日 - 提取所有66只票数据】')
    results_1231 = []
    
    for stock_code, name in stock_list.items():
        result = analyze_stock_day(stock_code, '20251231', name)
        if result:
            results_1231.append(result)
            print(f"✅ {stock_code} {name}: 涨{result['true_change_pct']:+.2f}% {'涨停' if result['is_limit_up'] else ''}")
        else:
            print(f"❌ {stock_code} {name}: 无数据")
    
    # 按涨幅排序取Top 20
    results_1231_sorted = sorted(results_1231, key=lambda x: x['true_change_pct'], reverse=True)
    top20_1231 = results_1231_sorted[:20]
    
    print(f'\n12月31日有效数据: {len(results_1231)} 只')
    print(f'12月31日Top 20已提取')
    
    # 提取1月5日数据（只提取有数据的）
    print('\n【1月5日 - 提取有数据的票】')
    data_dir = Path('E:/qmt/userdata_mini/datadir')
    
    available_stocks = []
    for stock_code in stock_list.keys():
        code = stock_code.split('.')[0]
        exchange = stock_code.split('.')[1]
        tick_file = data_dir / exchange / '0' / code / '20260105'
        if tick_file.exists() and tick_file.stat().st_size > 1000:
            available_stocks.append(stock_code)
    
    results_0105 = []
    for stock_code in available_stocks:
        name = stock_list.get(stock_code, '')
        result = analyze_stock_day(stock_code, '20260105', name)
        if result:
            results_0105.append(result)
            print(f"✅ {stock_code} {name}: 涨{result['true_change_pct']:+.2f}% {'涨停' if result['is_limit_up'] else ''}")
    
    # 按涨幅排序
    results_0105_sorted = sorted(results_0105, key=lambda x: x['true_change_pct'], reverse=True)
    
    print(f'\n1月5日有效数据: {len(results_0105)} 只')
    
    # 保存完整报告
    report = {
        'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '20251231': {
            'total': len(results_1231),
            'top20': top20_1231
        },
        '20260105': {
            'total': len(results_0105),
            'all': results_0105_sorted
        }
    }
    
    output_path = Path('data/complete_top20_analysis.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 完整报告已保存: {output_path}')
    print('='*100)
    
    return report

if __name__ == '__main__':
    extract_top20_complete()