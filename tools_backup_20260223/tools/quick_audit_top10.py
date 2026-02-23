#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【快速审计】验证志特新材真实排名
只扫描前30只+志特新材，快速获取验证结果
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from xtquant import xtdata

print("="*80)
print("【快速审计】志特新材排名验证（30只样本）")
print("="*80)

# 加载150股池，但只扫描前30只
csv_path = Path('E:/MyQuantTool/data/wanzhu_data/processed/wanzhu_selected_150.csv')
df_pool = pd.read_csv(csv_path)
stock_list = [f"{str(row['code']).zfill(6)}.{'SZ' if str(row['code']).startswith(('0', '3')) else 'SH'}" 
              for _, row in df_pool.iterrows()]

# 确保志特新材在列表中
if '300986.SZ' not in stock_list[:30]:
    stock_list = stock_list[:29] + ['300986.SZ']

print(f"扫描样本：{len(stock_list[:30])} 只")
print(f"日期：2025-12-31")
print("="*80)

detailed_records = []

for idx, stock_code in enumerate(stock_list[:30], 1):
    try:
        print(f"\n[{idx}/30] {stock_code}")
        
        record = {
            'code': stock_code,
            'defense_a': {'passed': False, 'data': {}},
            'defense_b': {'passed': False, 'data': {}},
            'defense_c': {'passed': False, 'data': {}},
            'score': 0
        }
        
        # 防线A：流动性
        daily_result = xtdata.get_local_data(
            field_list=['amount'],
            stock_list=[stock_code],
            period='1d',
            start_time='20251224',
            end_time='20251231'
        )
        
        if daily_result and stock_code in daily_result and not daily_result[stock_code].empty:
            avg_amount = daily_result[stock_code]['amount'].mean() / 10000
            record['defense_a']['data']['avg_amount_wan'] = round(avg_amount, 2)
            
            if avg_amount >= 3000:
                record['defense_a']['passed'] = True
                print(f"   A✅ 日均{avg_amount:.0f}万")
            else:
                print(f"   A❌ 日均{avg_amount:.0f}万")
                continue
        else:
            print(f"   A❌ 无数据")
            continue
        
        # 防线B：量比
        tick_result = xtdata.get_local_data(
            field_list=['time', 'volume', 'lastPrice'],
            stock_list=[stock_code],
            period='tick',
            start_time='20251231',
            end_time='20251231'
        )
        
        if tick_result and stock_code in tick_result and not tick_result[stock_code].empty:
            df = tick_result[stock_code].copy()
            df['dt'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
            
            # 早盘成交量
            morning_mask = ((df['dt'].dt.hour == 9) & (df['dt'].dt.minute >= 30)) | \
                          ((df['dt'].dt.hour == 10) & (df['dt'].dt.minute <= 0))
            morning_data = df[morning_mask]
            
            if not morning_data.empty:
                morning_volume = morning_data['volume'].sum()
                
                # 获取历史平均（前5日）
                hist_total = 0
                hist_count = 0
                for hist_date in ['20251224', '20251225', '20251226', '20251227', '20251230']:
                    try:
                        hist_result = xtdata.get_local_data(
                            field_list=['time', 'volume'],
                            stock_list=[stock_code],
                            period='tick',
                            start_time=hist_date,
                            end_time=hist_date
                        )
                        if hist_result and stock_code in hist_result and not hist_result[stock_code].empty:
                            hist_df = hist_result[stock_code].copy()
                            hist_df['dt'] = pd.to_datetime(hist_df['time'], unit='ms') + pd.Timedelta(hours=8)
                            hist_morning = hist_df[((hist_df['dt'].dt.hour == 9) & (hist_df['dt'].dt.minute >= 30)) | 
                                                   ((hist_df['dt'].dt.hour == 10) & (hist_df['dt'].dt.minute <= 0))]
                            if not hist_morning.empty:
                                hist_total += hist_morning['volume'].sum()
                                hist_count += 1
                    except:
                        continue
                
                hist_avg = hist_total / hist_count if hist_count > 0 else morning_volume * 0.3
                volume_ratio = morning_volume / hist_avg if hist_avg > 0 else 1
                
                record['defense_b']['data']['volume_ratio'] = round(volume_ratio, 2)
                record['defense_b']['data']['morning_volume'] = int(morning_volume)
                
                if volume_ratio >= 3.0:
                    record['defense_b']['passed'] = True
                    print(f"   B✅ 量比{volume_ratio:.2f}")
                else:
                    print(f"   B❌ 量比{volume_ratio:.2f}")
                    continue
            else:
                continue
        else:
            continue
        
        # 防线C：ATR
        if tick_result and stock_code in tick_result:
            df = tick_result[stock_code].copy()
            df['dt'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
            morning_df = df[(df['dt'].dt.hour == 9) | ((df['dt'].dt.hour == 10) & (df['dt'].dt.minute <= 30))]
            
            if not morning_df.empty:
                morning_high = morning_df['lastPrice'].max()
                morning_low = morning_df['lastPrice'].min()
                morning_open = morning_df['lastPrice'].iloc[0]
                
                if morning_open <= 0:
                    morning_open = morning_df[morning_df['lastPrice'] > 0]['lastPrice'].iloc[0] if len(morning_df[morning_df['lastPrice'] > 0]) > 0 else 1
                
                amplitude = (morning_high - morning_low) / morning_open * 100
                atr_ratio = amplitude / 3.0  # 假设20日ATR为3%
                
                record['defense_c']['data']['amplitude'] = round(amplitude, 2)
                record['defense_c']['data']['atr_ratio'] = round(atr_ratio, 2)
                
                if atr_ratio >= 2.0:
                    record['defense_c']['passed'] = True
                    print(f"   C✅ ATR{atr_ratio:.2f}")
                else:
                    print(f"   C❌ ATR{atr_ratio:.2f}")
                    continue
        
        # 计算得分
        if record['defense_a']['passed'] and record['defense_b']['passed'] and record['defense_c']['passed']:
            volume_ratio = record['defense_b']['data'].get('volume_ratio', 1)
            atr_ratio = record['defense_c']['data'].get('atr_ratio', 1)
            amplitude = record['defense_c']['data'].get('amplitude', 0)
            
            volume_score = min(100, volume_ratio * 12)
            atr_score = min(100, atr_ratio * 28)
            turnover_score = min(100, amplitude * 5)
            
            record['score'] = round(volume_score * 0.60 + atr_score * 0.25 + turnover_score * 0.15, 2)
            print(f"   📊 得分：{record['score']:.2f}")
            
            detailed_records.append(record)
        
    except Exception as e:
        print(f"   ❌ 异常：{e}")
        continue

# 排序
detailed_records.sort(key=lambda x: x['score'], reverse=True)

print("\n" + "="*80)
print("【Top 10名单】（30只样本中）")
print("="*80)

for i, stock in enumerate(detailed_records[:10], 1):
    marker = "🎯" if stock['code'] == '300986.SZ' else "  "
    print(f"{marker} {i:2d}. {stock['code']} 得分：{stock['score']:.2f}")

# 志特新材排名
zhite_rank = None
for i, stock in enumerate(detailed_records, 1):
    if stock['code'] == '300986.SZ':
        zhite_rank = i
        break

print("\n" + "="*80)
print("【志特新材验证】")
print("="*80)
if zhite_rank:
    print(f"✅ 排名：第{zhite_rank}名 / {len(detailed_records)}只通过筛选")
    print(f"✅ 得分：{detailed_records[zhite_rank-1]['score']:.2f}分")
    
    zhite = detailed_records[zhite_rank-1]
    print(f"\n详细数据：")
    print(f"   日均成交：{zhite['defense_a']['data'].get('avg_amount_wan')}万")
    print(f"   早盘量比：{zhite['defense_b']['data'].get('volume_ratio')}")
    print(f"   早盘成交量：{zhite['defense_b']['data'].get('morning_volume')}手")
    print(f"   振幅：{zhite['defense_c']['data'].get('amplitude')}%")
    print(f"   ATR比：{zhite['defense_c']['data'].get('atr_ratio')}")
else:
    print("❌ 志特新材未通过筛选")

print("\n" + "="*80)
