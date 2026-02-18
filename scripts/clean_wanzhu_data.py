#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顽主杯数据清洗脚本

问题：API返回的早期数据（2025-11-17至2026-02-03）是填充数据，字段值完全不变
解决方案：识别并删除填充数据，只保留真实变化的数据

清洗规则：
1. 如果某只股票在某日期范围内的 holding_amount、amount_change、holder_count 连续不变
2. 则判定为填充数据，予以删除
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json


def identify_filled_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    识别填充数据
    
    判定标准：
    - holding_amount、amount_change、holder_count 连续3天以上完全相同
    - 视为填充数据
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['name', 'date'])
    
    # 对每只股票，标记是否为填充数据
    df['is_filled'] = False
    
    for name in df['name'].unique():
        mask = df['name'] == name
        stock_df = df[mask].copy()
        
        if len(stock_df) < 3:
            continue
        
        # 计算三个关键字段的变化
        stock_df['amount_diff'] = stock_df['holding_amount'].diff().abs()
        stock_df['change_diff'] = stock_df['amount_change'].diff().abs()
        stock_df['holder_diff'] = stock_df['holder_count'].diff().abs()
        
        # 如果连续多天这三个字段都为0（无变化），则为填充数据
        stock_df['no_change'] = (
            (stock_df['amount_diff'] == 0) & 
            (stock_df['change_diff'] == 0) & 
            (stock_df['holder_diff'] == 0)
        )
        
        # 标记填充数据：连续无变化超过3天的记录
        consecutive_no_change = 0
        filled_indices = []
        
        for idx in stock_df.index:
            if stock_df.loc[idx, 'no_change']:
                consecutive_no_change += 1
                if consecutive_no_change >= 2:  # 连续3天（包括当前天）
                    filled_indices.append(idx)
            else:
                consecutive_no_change = 0
        
        df.loc[filled_indices, 'is_filled'] = True
    
    return df


def clean_data(input_path: Path, output_path: Path):
    """清洗数据"""
    print("=" * 60)
    print("🧹 顽主杯数据清洗")
    print("=" * 60)
    
    # 1. 加载原始数据
    print(f"\n📂 加载数据: {input_path}")
    df = pd.read_csv(input_path)
    print(f"   原始记录数: {len(df)}")
    print(f"   日期范围: {df['date'].min()} 至 {df['date'].max()}")
    print(f"   唯一股票数: {df['name'].nunique()}")
    
    # 2. 识别填充数据
    print("\n🔍 识别填充数据...")
    df_marked = identify_filled_data(df)
    
    filled_count = df_marked['is_filled'].sum()
    print(f"   识别到填充数据: {filled_count} 条 ({filled_count/len(df)*100:.1f}%)")
    
    # 3. 删除填充数据
    df_clean = df_marked[~df_marked['is_filled']].copy()
    df_clean = df_clean.drop(columns=['is_filled'], errors='ignore')
    
    print(f"\n✅ 清洗后数据:")
    print(f"   保留记录数: {len(df_clean)} ({len(df_clean)/len(df)*100:.1f}%)")
    print(f"   删除记录数: {len(df) - len(df_clean)}")
    print(f"   唯一股票数: {df_clean['name'].nunique()}")
    
    # 4. 统计每只股票的首次上榜日期（真实）
    print("\n📊 真实首次上榜日期统计 (Top 20):")
    first_rank = df_clean.groupby('name').agg({
        'date': 'min',
        'code': 'first',
        'rank': 'first'
    }).reset_index()
    first_rank.columns = ['name', 'first_rank_date', 'code', 'first_rank']
    first_rank = first_rank.sort_values('first_rank_date')
    
    for row in first_rank.head(20).itertuples():
        print(f"   {row.first_rank_date}: {row.name} ({row.code}) - 排名{row.first_rank}")
    
    # 5. 保存清洗后的数据
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n💾 清洗后数据已保存: {output_path}")
    
    # 6. 保存首次上榜信息
    first_rank_path = output_path.parent / 'wanzhu_first_rank_cleaned.json'
    first_rank_dict = {}
    for _, row in first_rank.iterrows():
        if pd.notna(row['code']) and row['code']:
            # 将Timestamp转换为字符串
            first_rank_date = row['first_rank_date']
            if hasattr(first_rank_date, 'strftime'):
                first_rank_date = first_rank_date.strftime('%Y-%m-%d')
            
            first_rank_dict[row['code']] = {
                'name': row['name'],
                'first_rank_date': first_rank_date,
                'first_rank': int(row['first_rank']) if pd.notna(row['first_rank']) else 0
            }
    
    with open(first_rank_path, 'w', encoding='utf-8') as f:
        json.dump(first_rank_dict, f, ensure_ascii=False, indent=2)
    
    print(f"💾 首次上榜信息已保存: {first_rank_path}")
    print(f"   共 {len(first_rank_dict)} 只有代码映射的股票")
    
    return df_clean, first_rank


def analyze_cleaned_data(df_clean: pd.DataFrame):
    """分析清洗后的数据质量"""
    print("\n" + "=" * 60)
    print("📈 清洗后数据分析")
    print("=" * 60)
    
    # 1. 日期分布
    df_clean['date'] = pd.to_datetime(df_clean['date'])
    print(f"\n日期分布:")
    print(f"   最早: {df_clean['date'].min()}")
    print(f"   最晚: {df_clean['date'].max()}")
    print(f"   交易日数: {df_clean['date'].nunique()}")
    
    # 2. 每月记录数
    df_clean['month'] = df_clean['date'].dt.to_period('M')
    monthly_counts = df_clean.groupby('month').size()
    print(f"\n每月记录数:")
    for month, count in monthly_counts.items():
        print(f"   {month}: {count} 条")
    
    # 3. 股票上榜天数分布
    days_on_list = df_clean.groupby('name').size()
    print(f"\n股票上榜天数分布:")
    print(f"   平均: {days_on_list.mean():.1f} 天")
    print(f"   中位数: {days_on_list.median():.1f} 天")
    print(f"   最多: {days_on_list.max()} 天 ({days_on_list.idxmax()})")
    print(f"   最少: {days_on_list.min()} 天")
    
    # 4. 持仓金额变化示例（验证数据真实性）
    print(f"\n持仓金额变化示例 (网宿科技):")
    wangsu = df_clean[df_clean['name'] == '网宿科技'].sort_values('date')
    if len(wangsu) > 0:
        print(f"   记录数: {len(wangsu)}")
        print(f"   金额范围: {wangsu['holding_amount'].min()} ~ {wangsu['holding_amount'].max()}")
        print(f"   变动范围: {wangsu['amount_change'].min()} ~ {wangsu['amount_change'].max()}")
        
        # 显示前5条和后5条
        print(f"\n   前5条:")
        for _, row in wangsu.head(5).iterrows():
            print(f"     {row['date']}: 金额={row['holding_amount']}, 变动={row['amount_change']}")
        print(f"\n   后5条:")
        for _, row in wangsu.tail(5).iterrows():
            print(f"     {row['date']}: 金额={row['holding_amount']}, 变动={row['amount_change']}")


def main():
    input_path = Path('data/wanzhu_history_mapped.csv')
    output_path = Path('data/wanzhu_history_cleaned.csv')
    
    if not input_path.exists():
        print(f"❌ 输入文件不存在: {input_path}")
        return
    
    # 清洗数据
    df_clean, first_rank = clean_data(input_path, output_path)
    
    # 分析清洗后的数据
    analyze_cleaned_data(df_clean)
    
    print("\n" + "=" * 60)
    print("✅ 数据清洗完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
