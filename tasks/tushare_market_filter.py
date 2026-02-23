#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO指令】Tushare云端粗筛脚本

⚠️ 已弃用警告：此脚本已重构进 logic/analyzers/universe_builder.py
请使用新API：
    >>> from logic.analyzers.universe_builder import UniverseBuilder
    >>> builder = UniverseBuilder()
    >>> universe_df = builder.build_universe(trade_date='20251231')
    >>> top_73 = builder.get_top_candidates(n=73)

保留此脚本作为向后兼容的转发包装器
"""

import warnings
import sys
from pathlib import Path

# 发出弃用警告
warnings.warn(
    "此脚本已弃用！请使用 logic.analyzers.universe_builder.UniverseBuilder",
    DeprecationWarning,
    stacklevel=2
)

sys.path.insert(0, 'E:\\MyQuantTool')

import pandas as pd
import tushare as ts
from datetime import datetime, timedelta
import time
import json

# 配置
TOKEN_FILE = Path('E:/MyQuantTool/config/tushare_token.txt')
OUTPUT_DIR = Path('E:/MyQuantTool/data/scan_results')
TRADE_DATE = '20251231'

# 过滤参数
MIN_AVG_AMOUNT = 3000
VOLUME_RATIO_THRESHOLD = 3.0
MAX_OUTPUT = 200


def get_tushare_token() -> str:
    """⚠️ 已弃用"""
    warnings.warn("已弃用", DeprecationWarning, stacklevel=2)
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
        if token and not token.startswith('替换'):
            return token
    raise ValueError("请先配置Tushare Token到 config/tushare_token.txt")


def init_tushare():
    """⚠️ 已弃用"""
    warnings.warn("已弃用", DeprecationWarning, stacklevel=2)
    token = get_tushare_token()
    ts.set_token(token)
    return ts.pro_api()


def layer1_static_filter(pro) -> pd.DataFrame:
    """⚠️ 已弃用：请使用 UniverseBuilder.filter_layer1_static()"""
    warnings.warn("已弃用", DeprecationWarning, stacklevel=2)
    print("\n" + "="*80)
    print("【Layer 1】Tushare静态过滤")
    print("="*80)
    
    df = pro.stock_basic(exchange='', list_status='L', 
                         fields='ts_code,symbol,name,area,industry,list_date')
    print(f"   全市场股票总数: {len(df)}")
    
    df = df[~df['ts_code'].str.startswith(('8', '4'))]
    print(f"   剔除北交所后: {len(df)}")
    
    df = df[~df['name'].str.contains('ST', na=False)]
    print(f"   剔除ST后: {len(df)}")
    
    return df


def layer2_amount_filter(pro, df_base: pd.DataFrame, trade_date: str) -> pd.DataFrame:
    """⚠️ 已弃用：请使用 UniverseBuilder.filter_layer2_amount()"""
    warnings.warn("已弃用", DeprecationWarning, stacklevel=2)
    print("\n" + "="*80)
    print("【Layer 2】Tushare成交额过滤")
    print("="*80)
    
    date_obj = datetime.strptime(trade_date, '%Y%m%d')
    dates = []
    for i in range(1, 10):
        d = date_obj - timedelta(days=i)
        d_str = d.strftime('%Y%m%d')
        if d.weekday() < 5:
            dates.append(d_str)
        if len(dates) >= 5:
            break
    
    print(f"   分析日期范围: {dates[-1]} 至 {dates[0]}")
    
    all_daily = []
    for date in dates:
        try:
            df_daily = pro.daily(trade_date=date, fields='ts_code,amount')
            if not df_daily.empty:
                all_daily.append(df_daily)
                print(f"   ✅ {date}: {len(df_daily)}只")
            time.sleep(0.5)
        except Exception as e:
            print(f"   ❌ {date}: {e}")
    
    if not all_daily:
        raise ValueError("无法获取历史日线数据")
    
    df_all = pd.concat(all_daily)
    df_avg = df_all.groupby('ts_code')['amount'].mean().reset_index()
    df_avg.columns = ['ts_code', 'avg_amount_5d']
    
    df = df_base.merge(df_avg, on='ts_code', how='inner')
    df = df[df['avg_amount_5d'] >= MIN_AVG_AMOUNT * 10]
    
    print(f"   5日日均成交>{MIN_AVG_AMOUNT}万: {len(df)}只")
    
    return df


def layer3_volume_ratio_filter(pro, df_base: pd.DataFrame, trade_date: str) -> pd.DataFrame:
    """⚠️ 已弃用：请使用 UniverseBuilder.filter_layer3_volume_ratio()"""
    warnings.warn("已弃用", DeprecationWarning, stacklevel=2)
    print("\n" + "="*80)
    print("【Layer 3】Tushare量比过滤")
    print("="*80)
    
    try:
        df_today = pro.daily_basic(trade_date=trade_date, 
                                   fields='ts_code,turnover_rate,volume_ratio')
        print(f"   ✅ 获取当日指标: {len(df_today)}只")
    except Exception as e:
        print(f"   ❌ 获取当日指标失败: {e}")
        return df_base.head(MAX_OUTPUT)
    
    df = df_base.merge(df_today, on='ts_code', how='inner')
    df = df[df['volume_ratio'] >= VOLUME_RATIO_THRESHOLD]
    print(f"   量比>{VOLUME_RATIO_THRESHOLD}: {len(df)}只")
    
    df = df.sort_values('volume_ratio', ascending=False).head(MAX_OUTPUT)
    print(f"   Top {MAX_OUTPUT}: {len(df)}只")
    
    return df


def save_candidates(df: pd.DataFrame, trade_date: str):
    """⚠️ 已弃用：请使用 UniverseBuilder.save_universe()"""
    warnings.warn("已弃用", DeprecationWarning, stacklevel=2)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_file = OUTPUT_DIR / f"{trade_date}_candidates_{len(df)}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n   💾 已保存: {output_file}")
    
    json_file = OUTPUT_DIR / f"{trade_date}_candidates_{len(df)}.json"
    df.to_json(json_file, orient='records', force_ascii=False, indent=2)
    print(f"   💾 已保存: {json_file}")
    
    return output_file


def main():
    """主函数"""
    print("⚠️  警告：此脚本已弃用，建议使用新API")
    print("="*80)
    print("新API用法:")
    print("  from logic.analyzers.universe_builder import UniverseBuilder")
    print("  builder = UniverseBuilder()")
    print("  universe_df = builder.build_universe(trade_date='20251231')")
    print("="*80)
    print()
    
    # 尝试使用新API
    try:
        from logic.analyzers.universe_builder import UniverseBuilder
        print("🔄 正在使用新API UniverseBuilder 执行筛选...\n")
        
        builder = UniverseBuilder(
            min_avg_amount=MIN_AVG_AMOUNT,
            volume_ratio_threshold=VOLUME_RATIO_THRESHOLD,
            max_output=MAX_OUTPUT
        )
        
        df = builder.build_universe(TRADE_DATE)
        
        # 保存结果
        saved_files = builder.save_universe(df, OUTPUT_DIR, TRADE_DATE)
        
        # 检查志特新材
        zhite = builder.check_specific_stock('300986.SZ')
        
        # 输出摘要
        print("\n" + "="*80)
        print("【筛选结果摘要】")
        print("="*80)
        print(f"总股票数: 5000+")
        print(f"最终入选: {len(df)}只")
        
        print(f"\nTop 10候选:")
        for i, row in df.head(10).iterrows():
            print(f"   {row['ts_code']} | {row['name']} | 量比:{row.get('volume_ratio', 'N/A')}")
        
        if zhite:
            print(f"\n🎯 志特新材(300986.SZ): ✅ 入选")
            print(f"   排名: {zhite['rank']}")
            print(f"   量比: {zhite['volume_ratio']}")
        else:
            print(f"\n🎯 志特新材(300986.SZ): ❌ 未入选")
        
        print("\n" + "="*80)
        print("✅ Tushare云端粗筛完成")
        print(f"输出文件: {saved_files}")
        print("="*80)
        
    except Exception as e:
        print(f"❌ 新API调用失败，回退到旧实现: {e}")
        print("正在使用旧API...\n")
        
        # 旧实现
        print("="*80)
        print("【CTO指令】Tushare云端粗筛（5000→200）")
        print("="*80)
        
        print("\n1️⃣ 初始化Tushare Pro...")
        try:
            pro = init_tushare()
            print("   ✅ Tushare Pro初始化成功")
        except Exception as e:
            print(f"   ❌ 初始化失败: {e}")
            return
        
        df = layer1_static_filter(pro)
        df = layer2_amount_filter(pro, df, TRADE_DATE)
        df = layer3_volume_ratio_filter(pro, df, TRADE_DATE)
        output_file = save_candidates(df, TRADE_DATE)
        
        print("\n" + "="*80)
        print("【筛选结果摘要】")
        print("="*80)
        print(f"最终入选: {len(df)}只")
        print(f"输出文件: {output_file}")
        print("="*80)


if __name__ == '__main__':
    main()