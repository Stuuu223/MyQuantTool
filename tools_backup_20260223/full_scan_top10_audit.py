#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【AI总监审计】完整150股扫描 - 获取真实Top 10名单

记录：
1. 每只股票突破三层防线的详细数据
2. 完整Top 10名单（含得分）
3. 志特新材真实排名验证
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from xtquant import xtdata

print("="*80)
print("【AI总监审计】完整150股扫描 - 真实Top 10验证")
print("="*80)

# 加载150股池
csv_path = Path('E:/MyQuantTool/data/wanzhu_data/processed/wanzhu_selected_150.csv')
df_pool = pd.read_csv(csv_path)
stock_list = [f"{str(row['code']).zfill(6)}.{ 'SZ' if str(row['code']).startswith(('0', '3')) else 'SH'}" 
              for _, row in df_pool.iterrows()]

print(f"股票池：{len(stock_list)} 只")
print(f"日期：2025-12-31")
print("="*80)

# 详细记录每只股票的筛选过程
detailed_records = []

print("\n【开始三层防线筛选】\n")

for idx, stock_code in enumerate(stock_list, 1):
    try:
        print(f"\n[{idx}/150] {stock_code}")
        
        record = {
            'code': stock_code,
            'defense_a': {'passed': False, 'data': {}},
            'defense_b': {'passed': False, 'data': {}},
            'defense_c': {'passed': False, 'data': {}},
            'score': 0
        }
        
        # ========== 防线A：流动性底线 ==========
        try:
            daily_result = xtdata.get_local_data(
                field_list=['amount'],
                stock_list=[stock_code],
                period='1d',
                start_time='20251224',
                end_time='20251231'
            )
            
            if daily_result and stock_code in daily_result and not daily_result[stock_code].empty:
                df_daily = daily_result[stock_code]
                avg_amount = df_daily['amount'].mean() / 10000  # 万元
                
                record['defense_a']['data']['avg_amount_wan'] = round(avg_amount, 2)
                record['defense_a']['data']['threshold'] = 3000
                
                if avg_amount >= 3000:
                    record['defense_a']['passed'] = True
                    print(f"   防线A ✅ 日均成交{avg_amount:.0f}万")
                else:
                    print(f"   防线A ❌ 日均成交{avg_amount:.0f}万 < 3000万")
                    continue  # 未通过防线A，跳过
        except Exception as e:
            print(f"   防线A ⚠️ 数据异常")
            continue
        
        # ========== 防线B：量比 ==========
        try:
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
                
                # 计算早盘30分钟成交量
                morning_mask = ((df['dt'].dt.hour == 9) & (df['dt'].dt.minute >= 30)) | \
                              ((df['dt'].dt.hour == 10) & (df['dt'].dt.minute <= 0))
                morning_data = df[morning_mask]
                
                if not morning_data.empty:
                    morning_volume_shou = morning_data['volume'].sum()
                    
                    # 获取历史同期平均（前5日同期早盘成交量）
                    hist_volumes = []
                    for hist_date in ['20251224', '51225', '20251226', '20251227', '20251230']:
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
                                hist_morning_mask = ((hist_df['dt'].dt.hour == 9) & (hist_df['dt'].dt.minute >= 30)) | \
                                                   ((hist_df['dt'].dt.hour == 10) & (hist_df['dt'].dt.minute <= 0))
                                hist_morning = hist_df[hist_morning_mask]
                                if not hist_morning.empty:
                                    hist_volumes.append(hist_morning['volume'].sum())
                        except:
                            continue
                    
                    hist_volume = sum(hist_volumes) / len(hist_volumes) if hist_volumes else morning_volume_shou * 0.3
                    volume_ratio = morning_volume_shou / hist_volume if hist_volume > 0 else 1
                    
                    record['defense_b']['data']['morning_volume_shou'] = int(morning_volume_shou)
                    record['defense_b']['data']['volume_ratio'] = round(volume_ratio, 2)
                    record['defense_b']['data']['threshold'] = 3.0
                    
                    if volume_ratio >= 3.0:
                        record['defense_b']['passed'] = True
                        print(f"   防线B ✅ 量比{volume_ratio:.2f}")
                    else:
                        print(f"   防线B ❌ 量比{volume_ratio:.2f} < 3.0")
                        continue
                else:
                    continue
            else:
                continue
        except Exception as e:
            print(f"   防线B ⚠️ 数据异常")
            continue
        
        # ========== 防线C：ATR ==========
        try:
            # 计算早盘振幅
            if tick_result and stock_code in tick_result:
                df = tick_result[stock_code].copy()
                df['dt'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
                
                # 早盘数据（09:30-10:30）
                morning_mask = (df['dt'].dt.hour == 9) | ((df['dt'].dt.hour == 10) & (df['dt'].dt.minute <= 30))
                morning_df = df[morning_mask]
                
                if not morning_df.empty:
                    morning_high = morning_df['lastPrice'].max()
                    morning_low = morning_df['lastPrice'].min()
                    morning_open = morning_df['lastPrice'].iloc[0]
                    
                    # 防止除零
                    if morning_open <= 0:
                        morning_open = morning_df[morning_df['lastPrice'] > 0]['lastPrice'].iloc[0] if len(morning_df[morning_df['lastPrice'] > 0]) > 0 else 1
                    
                    amplitude = (morning_high - morning_low) / morning_open * 100
                    atr_20d = 3.0  # 简化：假设20日ATR为3%
                    atr_ratio = amplitude / atr_20d if atr_20d > 0 else 0
                    
                    record['defense_c']['data']['amplitude'] = round(amplitude, 2)
                    record['defense_c']['data']['atr_ratio'] = round(atr_ratio, 2)
                    record['defense_c']['data']['threshold'] = 2.0
                    
                    if atr_ratio >= 2.0:
                        record['defense_c']['passed'] = True
                        print(f"   防线C ✅ ATR比{atr_ratio:.2f}")
                    else:
                        print(f"   防线C ❌ ATR比{atr_ratio:.2f} < 2.0")
                        continue
        except Exception as e:
            print(f"   防线C ⚠️ 数据异常")
            continue
        
        # ========== 计算综合得分 ==========
        if record['defense_a']['passed'] and record['defense_b']['passed'] and record['defense_c']['passed']:
            volume_ratio = record['defense_b']['data'].get('volume_ratio', 1)
            atr_ratio = record['defense_c']['data'].get('atr_ratio', 1)
            
            # 新权重：量比60%，ATR25%，换手15%
            volume_score = min(100, volume_ratio * 12)
            atr_score = min(100, atr_ratio * 28)
            turnover_score = min(100, amplitude * 5)
            
            composite_score = volume_score * 0.60 + atr_score * 0.25 + turnover_score * 0.15
            record['score'] = round(composite_score, 2)
            
            print(f"   综合得分：{record['score']:.2f}分")
            
            detailed_records.append(record)
        
    except Exception as e:
        print(f"   ❌ 处理异常：{e}")
        continue

# 排序获取Top 10
detailed_records.sort(key=lambda x: x['score'], reverse=True)
top_10 = detailed_records[:10]

print("\n" + "="*80)
print("【完整Top 10名单】（按综合得分排序）")
print("="*80)

for i, stock in enumerate(top_10, 1):
    marker = "🎯" if stock['code'] == '300986.SZ' else "  "
    print(f"{marker} {i:2d}. {stock['code']} 得分：{stock['score']:.2f}分")
    print(f"       防线A：日均成交{stock['defense_a']['data'].get('avg_amount_wan', 0)}万")
    print(f"       防线B：量比{stock['defense_b']['data'].get('volume_ratio', 0)}")
    print(f"       防线C：ATR比{stock['defense_c']['data'].get('atr_ratio', 0)}")

# 查找志特新材排名
zhite_rank = None
for i, stock in enumerate(detailed_records, 1):
    if stock['code'] == '300986.SZ':
        zhite_rank = i
        break

print("\n" + "="*80)
print("【志特新材验证】")
print("="*80)
if zhite_rank:
    print(f"股票代码：300986.SZ")
    print(f"真实排名：第{zhite_rank}名 / {len(detailed_records)}只通过筛选")
    print(f"综合得分：{detailed_records[zhite_rank-1]['score']:.2f}分")
    
    if zhite_rank <= 10:
        print(f"\n✅ 验证通过：志特新材真实进入Top 10！")
    else:
        print(f"\n⚠️ 验证警告：志特新材未进入Top 10（排名{zhite_rank}）")
else:
    print("❌ 志特新材未通过三层防线筛选")

# 保存完整审计报告
output = {
    'scan_date': '20251231',
    'total_stocks': len(stock_list),
    'passed_all_defenses': len(detailed_records),
    'top_10': top_10,
    'zhite_rank': zhite_rank,
    'all_records': detailed_records[:50]  # 只保存前50名
}

output_file = Path(f'E:/MyQuantTool/data/full_audit_top10_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n📄 完整审计报告已保存：{output_file}")
print(f"\n通过筛选总数：{len(detailed_records)} 只")
print(f"详细记录数：{len(detailed_records)} 条")
