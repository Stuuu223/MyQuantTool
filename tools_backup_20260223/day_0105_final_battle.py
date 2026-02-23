#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1月5日最终决战 - 全息回演
验证志特新材右侧起爆排名
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

import pandas as pd
import numpy as np
import json
from datetime import timedelta
from pathlib import Path
from xtquant import xtdata
from logic.strategies.production.unified_warfare_core import UnifiedWarfareCoreV18

def calculate_5min_windows(stock_code, date):
    """计算5分钟窗口数据"""
    result = xtdata.get_local_data(
        field_list=['time', 'volume', 'lastPrice'],
        stock_list=[stock_code],
        period='tick',
        start_time=date,
        end_time=date
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
    
    # 计算成交量增量 (手→股)
    df['vol_delta_shou'] = df['volume'].diff().fillna(df['volume'].iloc[0])
    df['vol_delta_shou'] = df['vol_delta_shou'].clip(lower=0)
    df['vol_delta'] = df['vol_delta_shou'] * 100  # 手→股
    
    # 计算成交额
    df['amount'] = df['vol_delta'] * df['lastPrice']
    
    # 09:40前数据（早盘）
    time_0940 = pd.Timestamp(f'{date[:4]}-{date[4:6]}-{date[6:]} 09:40:00')
    df_morning = df[df['dt'] <= time_0940]
    
    if df_morning.empty:
        return None
    
    # 早盘5分钟聚合
    df_morning = df_morning.set_index('dt')
    windows = df_morning.resample('5min', label='left', closed='left').agg({
        'vol_delta': 'sum',
        'amount': 'sum',
        'lastPrice': 'last'
    }).dropna()
    
    if windows.empty:
        return None
    
    return windows.reset_index().to_dict('records')

def run_0105_battle():
    """执行1月5日最终决战"""
    
    print('='*80)
    print('【1月5日最终决战 - 全息回演】')
    print('='*80)
    print('日期: 20260105')
    print('目标: 验证志特新材右侧起爆排名')
    print()
    
    # 读取66只票名单
    df = pd.read_csv('data/cleaned_candidates_66.csv')
    stock_list = df['ts_code'].tolist()
    
    # 只取有数据的票
    data_dir = Path('E:/qmt/userdata_mini/datadir')
    available_stocks = []
    
    for stock in stock_list:
        code = stock.split('.')[0]
        exchange = stock.split('.')[1]
        tick_file = data_dir / exchange / '0' / code / '20260105'
        if tick_file.exists() and tick_file.stat().st_size > 1000:
            available_stocks.append(stock)
    
    print(f'可用股票数: {len(available_stocks)} / {len(stock_list)}')
    print(f'股票列表: {available_stocks}')
    print()
    
    if len(available_stocks) < 5:
        print('❌ 可用股票太少，无法执行回演')
        return
    
    # 初始化V18核心
    core = UnifiedWarfareCoreV18()
    
    # 收集所有股票的早盘数据
    all_windows = {}
    print('正在计算早盘数据...')
    
    for stock in available_stocks:
        windows = calculate_5min_windows(stock, '20260105')
        if windows:
            all_windows[stock] = windows
            print(f'  ✅ {stock}: {len(windows)}个窗口')
        else:
            print(f'  ❌ {stock}: 无数据')
    
    print()
    print(f'成功加载: {len(all_windows)} 只票')
    print()
    
    if len(all_windows) < 3:
        print('❌ 有效股票太少')
        return
    
    # 计算每只票的得分
    print('正在计算动态乘数得分...')
    results = []
    
    for stock, windows in all_windows.items():
        try:
            score_result = core.calculate_blood_sucking_score(
                stock_code=stock,
                windows=windows,
                all_stocks_data=all_windows
            )
            
            # 获取股票信息
            stock_info = df[df['ts_code'] == stock].iloc[0] if len(df[df['ts_code'] == stock]) > 0 else None
            
            result = {
                'stock_code': stock,
                'name': stock_info['name'] if stock_info is not None else 'Unknown',
                'base_score': score_result.get('base_score', 0),
                'capital_share_pct': score_result.get('capital_share_pct', 0),
                'multiplier': score_result.get('multiplier', 1.0),
                'final_score': score_result.get('final_score', 0)
            }
            results.append(result)
            print(f'  {stock}: 基础分={result["base_score"]:.1f} 占比={result["capital_share_pct"]:.2f}% 最终={result["final_score"]:.1f}')
        except Exception as e:
            print(f'  ❌ {stock}: 计算失败 - {e}')
    
    print()
    
    # 排名
    results_sorted = sorted(results, key=lambda x: x['final_score'], reverse=True)
    
    print('='*80)
    print('【1月5日 Top 10 排名】')
    print('='*80)
    
    zhitexincai_rank = None
    for i, r in enumerate(results_sorted[:10], 1):
        marker = ''
        if r['stock_code'] == '300986.SZ':
            marker = ' <-- 【志特新材】'
            zhitexincai_rank = i
        print(f'{i:2d}. {r["stock_code"]} {r["name"]:8s} 基础:{r["base_score"]:5.1f} 占比:{r["capital_share_pct"]:5.2f}% 乘数:{r["multiplier"]:.3f} 最终:{r["final_score"]:6.1f}{marker}')
    
    print()
    
    # 志特新材详情
    if zhitexincai_rank:
        print(f'🎯 【志特新材排名】: 第 {zhitexincai_rank} 名 / {len(results_sorted)}')
        print('✅ 志特新材1月5日进入Top 10！')
    else:
        # 查找志特排名
        for i, r in enumerate(results_sorted, 1):
            if r['stock_code'] == '300986.SZ':
                zhitexincai_rank = i
                print(f'⚠️ 【志特新材排名】: 第 {i} 名 / {len(results_sorted)}')
                break
    
    print()
    
    # 保存报告
    report = {
        'trade_date': '20260105',
        'total_stocks': len(stock_list),
        'available_stocks': len(available_stocks),
        'valid_stocks': len(results),
        'top10': results_sorted[:10],
        'zhitexincai': {
            'rank': zhitexincai_rank,
            'in_top10': zhitexincai_rank <= 10 if zhitexincai_rank else False
        },
        'all_results': results_sorted
    }
    
    output_path = Path('data/day_0105_final_battle_report.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f'✅ 报告已保存: {output_path}')
    print('='*80)
    
    return report

if __name__ == '__main__':
    run_0105_battle()
