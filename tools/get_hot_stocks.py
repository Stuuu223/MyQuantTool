#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热门股票筛选器

功能：
1. 从 AkShare/Tushare 获取多种维度的热门股票
2. 支持多种筛选策略：
   - 涨停板股票池
   - 龙虎榜大资金股票
   - 热门概念板块成分股
   - 成交额排名 Top N
3. 自动去重、剔除 ST
4. 输出标准格式供 QMT 下载器使用

Author: MyQuantTool Team
Date: 2026-02-09
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Set
import pandas as pd
import argparse

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入速率限制器
try:
    from logic.rate_limiter import RateLimiter
    RATE_LIMITER = RateLimiter(
        max_requests_per_minute=10,
        max_requests_per_hour=100,
        min_request_interval=5,
        enable_logging=True
    )
except ImportError:
    RATE_LIMITER = None

# Tushare Token 配置
TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', '')
if not TUSHARE_TOKEN:
    config_file = project_root / 'config' / 'tushare_token.txt'
    if config_file.exists():
        TUSHARE_TOKEN = config_file.read_text().strip()


def get_limit_up_stocks_akshare(date: str = None) -> List[str]:
    """
    获取涨停股票池 (AkShare)
    
    Args:
        date: 日期 YYYY-MM-DD，默认当天
    
    Returns:
        股票代码列表 ['600519.SH', ...]
    """
    print("\n📈 获取涨停股票池 (AkShare)...")
    
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
    
    try:
        import akshare as ak
        
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        else:
            date = date.replace('-', '')
        
        # 获取涨停股池
        df = ak.stock_zt_pool_em(date=date)
        
        if RATE_LIMITER:
            RATE_LIMITER.record_request()
        
        # 转换为 QMT 格式
        codes = []
        for _, row in df.iterrows():
            code = str(row['代码'])
            if code.startswith('6'):
                codes.append(f"{code}.SH")
            else:
                codes.append(f"{code}.SZ")
        
        print(f"   ✅ 获取 {len(codes)} 只涨停股")
        return codes
        
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return []


def get_dragon_tiger_stocks_akshare(days: int = 3) -> List[str]:
    """
    获取龙虎榜股票 (AkShare)
    
    Args:
        days: 最近N天的龙虎榜
    
    Returns:
        股票代码列表
    """
    print(f"\n🐉 获取最近 {days} 天龙虎榜股票 (AkShare)...")
    
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
    
    try:
        import akshare as ak
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # 获取龙虎榜详情
        df = ak.stock_lhb_detail_em(start_date=start_str, end_date=end_str)
        
        if RATE_LIMITER:
            RATE_LIMITER.record_request()
        
        # 提取股票代码
        codes = set()
        for _, row in df.iterrows():
            code = str(row['代码'])
            if code.startswith('6'):
                codes.add(f"{code}.SH")
            else:
                codes.add(f"{code}.SZ")
        
        print(f"   ✅ 获取 {len(codes)} 只龙虎榜股票")
        return list(codes)
        
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return []


def get_hot_concept_stocks_akshare(top_concepts: int = 5) -> List[str]:
    """
    获取热门概念板块成分股 (AkShare)
    
    Args:
        top_concepts: 选取涨幅前N个概念板块
    
    Returns:
        股票代码列表
    """
    print(f"\n🔥 获取热门概念板块 Top {top_concepts} 的成分股 (AkShare)...")
    
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
    
    try:
        import akshare as ak
        
        # 1. 获取概念板块排名
        df_concepts = ak.stock_board_concept_name_em()
        
        if RATE_LIMITER:
            RATE_LIMITER.record_request()
        
        # 按涨跌幅排序，取前N个
        df_concepts['涨跌幅'] = pd.to_numeric(df_concepts['涨跌幅'], errors='coerce')
        df_concepts = df_concepts.nlargest(top_concepts, '涨跌幅')
        
        print(f"   热门概念: {df_concepts['板块名称'].tolist()}")
        
        # 2. 获取每个概念的成分股
        all_codes = set()
        for _, row in df_concepts.iterrows():
            concept_name = row['板块名称']
            
            if RATE_LIMITER:
                RATE_LIMITER.wait_if_needed()
            
            try:
                df_cons = ak.stock_board_concept_cons_em(symbol=concept_name)
                
                if RATE_LIMITER:
                    RATE_LIMITER.record_request()
                
                for _, stock in df_cons.iterrows():
                    code = str(stock['代码'])
                    if code.startswith('6'):
                        all_codes.add(f"{code}.SH")
                    else:
                        all_codes.add(f"{code}.SZ")
            except:
                pass
        
        print(f"   ✅ 获取 {len(all_codes)} 只概念股")
        return list(all_codes)
        
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return []


def get_top_volume_stocks_akshare(top_n: int = 100) -> List[str]:
    """
    获取成交额 Top N 股票 (AkShare)
    
    Args:
        top_n: 成交额排名前N
    
    Returns:
        股票代码列表
    """
    print(f"\n💰 获取成交额 Top {top_n} 股票 (AkShare)...")
    
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
    
    try:
        import akshare as ak
        
        # 获取实时行情
        df = ak.stock_zh_a_spot_em()
        
        if RATE_LIMITER:
            RATE_LIMITER.record_request()
        
        # 剔除 ST
        df = df[~df['名称'].str.contains('ST', na=False)]
        
        # 剔除北交所
        df = df[~df['代码'].str.match(r'^(8|4|9)')]
        
        # 按成交额排序
        df['成交额'] = pd.to_numeric(df['成交额'], errors='coerce')
        df = df.nlargest(top_n, '成交额')
        
        # 转换格式
        codes = []
        for _, row in df.iterrows():
            code = str(row['代码'])
            if code.startswith('6'):
                codes.append(f"{code}.SH")
            else:
                codes.append(f"{code}.SZ")
        
        print(f"   ✅ 获取 {len(codes)} 只高成交额股票")
        return codes
        
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return []


def get_hot_stocks_tushare(top_n: int = 100) -> List[str]:
    """
    使用 Tushare Pro 获取热门股票（成交额 Top N）
    
    Args:
        top_n: 成交额排名前N
    
    Returns:
        股票代码列表
    """
    print(f"\n💰 获取成交额 Top {top_n} 股票 (Tushare Pro)...")
    
    if not TUSHARE_TOKEN:
        print("   ❌ Tushare Token 未配置")
        return []
    
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
    
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        
        # 获取最近交易日
        today = datetime.now()
        trade_date = today.strftime('%Y%m%d')
        
        # 尝试获取数据
        for i in range(5):
            try:
                df = pro.daily(
                    trade_date=trade_date,
                    fields='ts_code,amount'
                )
                if len(df) > 0:
                    break
                trade_date = (today - timedelta(days=i+1)).strftime('%Y%m%d')
            except:
                trade_date = (today - timedelta(days=i+1)).strftime('%Y%m%d')
        
        if RATE_LIMITER:
            RATE_LIMITER.record_request()
        
        # 获取股票名称（用于剔除ST）
        df_name = pro.stock_basic(fields='ts_code,name')
        df = df.merge(df_name, on='ts_code', how='left')
        
        # 剔除 ST
        df = df[~df['name'].str.contains('ST', na=False)]
        
        # 剔除北交所
        df = df[~df['ts_code'].str.match(r'^(8|4|9)')]
        
        # 按成交额排序
        df = df.nlargest(top_n, 'amount')
        
        codes = df['ts_code'].tolist()
        
        print(f"   ✅ 获取 {len(codes)} 只高成交额股票")
        return codes
        
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return []


def merge_and_deduplicate(stock_lists: List[List[str]]) -> List[str]:
    """
    合并多个股票列表并去重
    """
    all_codes = set()
    for stocks in stock_lists:
        all_codes.update(stocks)
    
    # 剔除 ST（如果之前漏掉了）
    final_codes = [code for code in all_codes if 'ST' not in code]
    
    return sorted(final_codes)


def main():
    parser = argparse.ArgumentParser(description='热门股票筛选器')
    parser.add_argument('--mode', type=str, default='akshare', 
                        choices=['akshare', 'tushare', 'both'],
                        help='数据源：akshare | tushare | both')
    parser.add_argument('--strategy', type=str, default='all',
                        choices=['all', 'limit_up', 'dragon_tiger', 'hot_concept', 'volume'],
                        help='筛选策略')
    parser.add_argument('--top', type=int, default=300,
                        help='输出股票数量（默认300）')
    parser.add_argument('--output', type=str, default='data/hot_stocks.txt',
                        help='输出文件路径')
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔥 热门股票筛选器")
    print("=" * 60)
    
    all_stocks = []
    
    if args.mode in ['akshare', 'both']:
        print("\n📡 使用 AkShare 获取热门股票...")
        
        if args.strategy in ['all', 'limit_up']:
            all_stocks.append(get_limit_up_stocks_akshare())
        
        if args.strategy in ['all', 'dragon_tiger']:
            all_stocks.append(get_dragon_tiger_stocks_akshare(days=3))
        
        if args.strategy in ['all', 'hot_concept']:
            all_stocks.append(get_hot_concept_stocks_akshare(top_concepts=5))
        
        if args.strategy in ['all', 'volume']:
            all_stocks.append(get_top_volume_stocks_akshare(top_n=200))
    
    if args.mode in ['tushare', 'both']:
        print("\n📡 使用 Tushare Pro 获取热门股票...")
        
        if args.strategy in ['all', 'volume']:
            all_stocks.append(get_hot_stocks_tushare(top_n=200))
    
    # 合并去重
    print("\n🔄 合并并去重...")
    final_stocks = merge_and_deduplicate(all_stocks)
    
    # 限制数量
    if len(final_stocks) > args.top:
        final_stocks = final_stocks[:args.top]
    
    print(f"   最终获得 {len(final_stocks)} 只热门股票")
    
    # 保存到文件
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for code in final_stocks:
            f.write(code + '\n')
    
    print(f"\n💾 已保存到: {output_path}")
    print("\n" + "=" * 60)
    print("✅ 完成！现在可以使用以下命令下载数据：")
    print(f"   python tools/download_from_list.py --list {output_path} --days 30")
    print("=" * 60)


if __name__ == "__main__":
    main()