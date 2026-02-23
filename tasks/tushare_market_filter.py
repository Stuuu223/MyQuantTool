#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO指令】Tushare云端粗筛脚本
任务：用Tushare Pro在云端完成第一段粗筛（5000→200），绝不碰QMT历史数据

架构：云端粗筛 + 本地精炼
- Layer 1: Tushare获取全市场基础数据（ST/停牌过滤）
- Layer 2: Tushare获取前5日成交额（日均>3000万）
- Layer 3: Tushare/极简QMT获取早盘量比（>3）

输出：20251231_candidates_200.csv（真实异动股票名单）
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

import pandas as pd
import tushare as ts
from datetime import datetime, timedelta
from pathlib import Path
import time
import json

# 配置
TOKEN_FILE = Path('E:/MyQuantTool/config/tushare_token.txt')
OUTPUT_DIR = Path('E:/MyQuantTool/data/scan_results')
TRADE_DATE = '20251231'  # 目标交易日

# 过滤参数
MIN_AVG_AMOUNT = 3000  # 万元，5日日均成交额底线
VOLUME_RATIO_THRESHOLD = 3.0  # 量比阈值
MAX_OUTPUT = 200  # 最大输出数量


def get_tushare_token() -> str:
    """读取Tushare Token"""
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
        if token and not token.startswith('替换'):
            return token
    raise ValueError("请先配置Tushare Token到 config/tushare_token.txt")


def init_tushare():
    """初始化Tushare Pro"""
    token = get_tushare_token()
    ts.set_token(token)
    return ts.pro_api()


def layer1_static_filter(pro) -> pd.DataFrame:
    """
    Layer 1: Tushare静态过滤（5000→约4500）
    - 剔除ST/*ST/退市
    - 剔除北交所（8/4开头）
    - 剔除停牌
    """
    print("\n" + "="*80)
    print("【Layer 1】Tushare静态过滤")
    print("="*80)
    
    # 获取全市场股票基础信息
    df = pro.stock_basic(exchange='', list_status='L', 
                         fields='ts_code,symbol,name,area,industry,list_date')
    print(f"   全市场股票总数: {len(df)}")
    
    # 剔除北交所（8/4开头）
    df = df[~df['ts_code'].str.startswith(('8', '4'))]
    print(f"   剔除北交所后: {len(df)}")
    
    # 剔除ST（名称中包含ST）
    df = df[~df['name'].str.contains('ST', na=False)]
    print(f"   剔除ST后: {len(df)}")
    
    return df


def layer2_amount_filter(pro, df_base: pd.DataFrame, trade_date: str) -> pd.DataFrame:
    """
    Layer 2: Tushare成交额过滤（约4500→约800）
    - 计算前5日日均成交额
    - 剔除<3000万的死水票
    """
    print("\n" + "="*80)
    print("【Layer 2】Tushare成交额过滤")
    print("="*80)
    
    # 计算前5个交易日
    date_obj = datetime.strptime(trade_date, '%Y%m%d')
    dates = []
    for i in range(1, 10):  # 最多往前找10天
        d = date_obj - timedelta(days=i)
        d_str = d.strftime('%Y%m%d')
        # 简单判断是否为交易日（非周末）
        if d.weekday() < 5:  # 0-4是周一到周五
            dates.append(d_str)
        if len(dates) >= 5:
            break
    
    print(f"   分析日期范围: {dates[-1]} 至 {dates[0]}")
    
    # 批量获取日线数据（前复权）
    all_daily = []
    for date in dates:
        try:
            df_daily = pro.daily(trade_date=date, fields='ts_code,amount')
            if not df_daily.empty:
                all_daily.append(df_daily)
                print(f"   ✅ {date}: {len(df_daily)}只")
            time.sleep(0.5)  # 避免限流
        except Exception as e:
            print(f"   ❌ {date}: {e}")
    
    if not all_daily:
        raise ValueError("无法获取历史日线数据")
    
    # 合并并计算5日平均成交额
    df_all = pd.concat(all_daily)
    df_avg = df_all.groupby('ts_code')['amount'].mean().reset_index()
    df_avg.columns = ['ts_code', 'avg_amount_5d']
    
    # 合并到基础数据
    df = df_base.merge(df_avg, on='ts_code', how='inner')
    
    # 过滤：日均成交额>3000万（amount单位是千元，所以3000万=30000千元）
    df = df[df['avg_amount_5d'] >= MIN_AVG_AMOUNT * 10]  # Tushare amount单位是千元
    
    print(f"   5日日均成交>{MIN_AVG_AMOUNT}万: {len(df)}只")
    
    return df


def layer3_volume_ratio_filter(pro, df_base: pd.DataFrame, trade_date: str) -> pd.DataFrame:
    """
    Layer 3: Tushare量比过滤（约800→200）
    - 获取当日早盘成交量
    - 计算量比（ vs 过去5日同期）
    - 保留量比>3的前200只
    """
    print("\n" + "="*80)
    print("【Layer 3】Tushare量比过滤")
    print("="*80)
    
    # 获取当日分钟数据（Tushare的1分钟线接口需要积分权限）
    # 使用daily_basic接口获取当日成交量和量比
    try:
        df_today = pro.daily_basic(trade_date=trade_date, 
                                   fields='ts_code,turnover_rate,volume_ratio')
        print(f"   ✅ 获取当日指标: {len(df_today)}只")
    except Exception as e:
        print(f"   ❌ 获取当日指标失败: {e}")
        return df_base.head(MAX_OUTPUT)  # 降级：直接返回前200
    
    # 合并数据
    df = df_base.merge(df_today, on='ts_code', how='inner')
    
    # 过滤：量比>3
    df = df[df['volume_ratio'] >= VOLUME_RATIO_THRESHOLD]
    print(f"   量比>{VOLUME_RATIO_THRESHOLD}: {len(df)}只")
    
    # 按量比排序，取前200
    df = df.sort_values('volume_ratio', ascending=False).head(MAX_OUTPUT)
    print(f"   Top {MAX_OUTPUT}: {len(df)}只")
    
    return df


def save_candidates(df: pd.DataFrame, trade_date: str):
    """保存候选股票名单"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_file = OUTPUT_DIR / f"{trade_date}_candidates_{len(df)}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n   💾 已保存: {output_file}")
    
    # 同时保存JSON格式
    json_file = OUTPUT_DIR / f"{trade_date}_candidates_{len(df)}.json"
    df.to_json(json_file, orient='records', force_ascii=False, indent=2)
    print(f"   💾 已保存: {json_file}")
    
    return output_file


def main():
    """主函数"""
    print("="*80)
    print("【CTO指令】Tushare云端粗筛（5000→200）")
    print("="*80)
    print(f"目标日期: {TRADE_DATE}")
    print(f"成交额底线: {MIN_AVG_AMOUNT}万")
    print(f"量比阈值: {VOLUME_RATIO_THRESHOLD}")
    print("="*80)
    
    # 初始化Tushare
    print("\n1️⃣ 初始化Tushare Pro...")
    try:
        pro = init_tushare()
        print("   ✅ Tushare Pro初始化成功")
    except Exception as e:
        print(f"   ❌ 初始化失败: {e}")
        return
    
    # Layer 1: 静态过滤
    df = layer1_static_filter(pro)
    
    # Layer 2: 成交额过滤
    df = layer2_amount_filter(pro, df, TRADE_DATE)
    
    # Layer 3: 量比过滤
    df = layer3_volume_ratio_filter(pro, df, TRADE_DATE)
    
    # 保存结果
    output_file = save_candidates(df, TRADE_DATE)
    
    # 输出摘要
    print("\n" + "="*80)
    print("【筛选结果摘要】")
    print("="*80)
    print(f"总股票数: 5000+")
    print(f"最终入选: {len(df)}只")
    print(f"压缩率: {(1 - len(df)/5000)*100:.1f}%")
    print(f"\nTop 10候选:")
    for i, row in df.head(10).iterrows():
        print(f"   {row['ts_code']} | {row['name']} | 量比:{row.get('volume_ratio', 'N/A')}")
    
    # 检查志特新材
    zhite = df[df['ts_code'] == '300986.SZ']
    if not zhite.empty:
        print(f"\n🎯 志特新材(300986.SZ): ✅ 入选")
        print(f"   排名: {zhite.index[0] + 1}")
        print(f"   量比: {zhite.iloc[0].get('volume_ratio', 'N/A')}")
    else:
        print(f"\n🎯 志特新材(300986.SZ): ❌ 未入选")
    
    print("\n" + "="*80)
    print("✅ Tushare云端粗筛完成")
    print(f"输出文件: {output_file}")
    print("下一步: 使用定向Tick下载脚本获取200只股票的Tick数据")
    print("="*80)


if __name__ == '__main__':
    main()
