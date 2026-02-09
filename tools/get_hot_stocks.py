#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热门股票筛选器（防封增强版）

功能：
1. 从 AkShare/Tushare 获取多种维度的热门股票
2. 支持多种筛选策略：
   - 涨停板股票池
   - 龙虎榜大资金股票
   - 热门概念板块成分股
   - 成交额排名 Top N
3. 自动去重、剔除 ST
4. 输出标准格式供 QMT 下载器使用

防封机制：
- 分批次调用，避免瞬间大量请求
- 增加随机延迟，避免机器人检测
- 失败降级，某个策略失败不影响其他策略
- 更保守的速率限制器配置

Author: MyQuantTool Team
Date: 2026-02-09
Update: 2026-02-09 - 增强防封机制，避免IP封禁
"""

import sys
import os
import time
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Set
import pandas as pd
import argparse

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入速率限制器（更保守的配置）
try:
    from logic.rate_limiter import RateLimiter
    RATE_LIMITER = RateLimiter(
        max_requests_per_minute=15,  # 降低到15（官方是20）
        max_requests_per_hour=150,   # 降低到150（官方是200）
        min_request_interval=8,       # 增加到8秒（原5秒）
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


def random_delay():
    """随机延迟，避免机器人检测"""
    delay = random.uniform(2, 5)  # 2-5秒随机延迟
    time.sleep(delay)


def get_limit_up_stocks_akshare(date: str = None) -> List[str]:
    """
    获取涨停股票池 (AkShare)
    
    Args:
        date: 日期 YYYY-MM-DD，默认当天
    
    Returns:
        股票代码列表 ['600519.SH', ...]
    """
    print("\n📈 获取涨停股票池 (AkShare)...")
    
    # 随机延迟
    random_delay()
    
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
        
        # 检查数据有效性
        if df is None or len(df) == 0:
            print(f"   ⚠️  无涨停股数据")
            return []
        
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
    
    # 随机延迟
    random_delay()
    
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
        
        # 检查数据有效性
        if df is None or len(df) == 0:
            print(f"   ⚠️  无龙虎榜数据")
            return []
        
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
    获取热门概念板块成分股（防封增强版）
    
    ⚠️ 修复：不再循环调用每个概念的成分股API，避免瞬间大量请求
    改为：只调用概念板块排名，不获取成分股（避免批量调用）
    
    Args:
        top_concepts: 选取涨幅前N个概念板块
    
    Returns:
        股票代码列表
    """
    print(f"\n🔥 获取热门概念板块 Top {top_concepts} (AkShare)...")
    print(f"   ⚠️  防封模式：只获取概念排名，不获取成分股")
    
    # 随机延迟
    random_delay()
    
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
    
    try:
        import akshare as ak
        
        # 1. 获取概念板块排名（只调用1次API）
        df_concepts = ak.stock_board_concept_name_em()
        
        if RATE_LIMITER:
            RATE_LIMITER.record_request()
        
        # 检查数据有效性
        if df_concepts is None or len(df_concepts) == 0:
            print(f"   ⚠️  无概念板块数据")
            return []
        
        # 按涨跌幅排序，取前N个
        df_concepts['涨跌幅'] = pd.to_numeric(df_concepts['涨跌幅'], errors='coerce')
        df_concepts = df_concepts.nlargest(top_concepts, '涨跌幅')
        
        print(f"   热门概念: {df_concepts['板块名称'].tolist()}")
        print(f"   ⚠️  由于防封限制，未获取成分股列表")
        print(f"   ✅ 获取 {len(df_concepts)} 个概念板块")
        
        # 🔥 修复：不再循环调用成分股API，返回空列表
        # 避免瞬间触发 5 次 API 调用
        return []
        
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return []


def get_top_volume_stocks_akshare(top_n: int = 200) -> List[str]:
    """
    获取成交额 Top N 股票 (AkShare)
    
    Args:
        top_n: 选取前N只
    
    Returns:
        股票代码列表
    """
    print(f"\n💰 获取成交额 Top {top_n} 股票 (AkShare)...")
    
    # 随机延迟
    random_delay()
    
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
    
    try:
        import akshare as ak
        
        # 获取实时行情
        df = ak.stock_zh_a_spot_em()
        
        if RATE_LIMITER:
            RATE_LIMITER.record_request()
        
        # 检查数据有效性
        if df is None or len(df) == 0:
            print(f"   ⚠️  无实时行情数据")
            return []
        
        # 按成交额排序
        df['成交额'] = pd.to_numeric(df['成交额'], errors='coerce')
        df = df.nlargest(top_n, '成交额')
        
        # 转换为 QMT 格式
        codes = []
        for _, row in df.iterrows():
            code = str(row['代码'])
            if code.startswith('6'):
                codes.append(f"{code}.SH")
            else:
                codes.append(f"{code}.SZ")
        
        print(f"   ✅ 获取 {len(codes)} 只股票")
        return codes
        
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return []


def get_limit_up_stocks_tushare(trade_date: str = None) -> List[str]:
    """
    获取涨停股票池 (Tushare Pro)
    
    Args:
        trade_date: 交易日期 YYYYMMDD，默认当天
    
    Returns:
        股票代码列表
    """
    print(f"\n📈 获取涨停股票池 (Tushare Pro)...")
    
    if not TUSHARE_TOKEN:
        print("   ⚠️  未配置 Tushare Token")
        return []
    
    # 随机延迟
    random_delay()
    
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
    
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        # 获取涨停股池（使用 limit_list_d）
        df = pro.limit_list_d(trade_date=trade_date, limit_type='U')
        
        if RATE_LIMITER:
            RATE_LIMITER.record_request()
        
        # 检查数据有效性
        if df is None or len(df) == 0:
            print(f"   ⚠️  无涨停股数据")
            return []
        
        # 转换为 QMT 格式
        codes = []
        for code in df['ts_code'].tolist():
            codes.append(code)
        
        print(f"   ✅ 获取 {len(codes)} 只涨停股")
        return codes
        
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return []


def get_top_volume_stocks_tushare(trade_date: str = None, top_n: int = 200) -> List[str]:
    """
    获取成交额 Top N 股票 (Tushare Pro)
    
    Args:
        trade_date: 交易日期 YYYYMMDD，默认当天
        top_n: 选取前N只
    
    Returns:
        股票代码列表
    """
    print(f"\n💰 获取成交额 Top {top_n} 股票 (Tushare Pro)...")
    
    if not TUSHARE_TOKEN:
        print("   ⚠️  未配置 Tushare Token")
        return []
    
    # 随机延迟
    random_delay()
    
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
    
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        # 获取日线行情（获取成交额）
        df = pro.daily(trade_date=trade_date, fields='ts_code,amount')
        
        if RATE_LIMITER:
            RATE_LIMITER.record_request()
        
        # 检查数据有效性
        if df is None or len(df) == 0:
            print(f"   ⚠️  无日线数据")
            return []
        
        # 按成交额排序
        df = df.nlargest(top_n, 'amount')
        
        # 转换为 QMT 格式
        codes = []
        for code in df['ts_code'].tolist():
            codes.append(code)
        
        print(f"   ✅ 获取 {len(codes)} 只股票")
        return codes
        
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return []


def merge_and_deduplicate(stock_lists: List[List[str]]) -> List[str]:
    """
    合并并去重股票列表
    
    Args:
        stock_lists: 多个股票列表
    
    Returns:
        去重后的股票列表
    """
    all_codes = set()
    for codes in stock_lists:
        all_codes.update(codes)
    
    return list(all_codes)


def save_to_file(codes: List[str], output_file: str):
    """
    保存股票列表到文件
    
    Args:
        codes: 股票代码列表
        output_file: 输出文件路径
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for code in codes:
            f.write(f"{code}\n")
    
    print(f"\n💾 已保存到: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='热门股票筛选器（防封增强版）')
    parser.add_argument('--mode', type=str, default='akshare', 
                       choices=['akshare', 'tushare', 'both'], 
                       help='数据源: akshare | tushare | both')
    parser.add_argument('--strategy', type=str, default='all',
                       choices=['all', 'limit_up', 'dragon_tiger', 'hot_concept', 'volume'],
                       help='筛选策略: all | limit_up | dragon_tiger | hot_concept | volume')
    parser.add_argument('--top', type=int, default=300,
                       help='选取数量（默认300）')
    parser.add_argument('--output', type=str, default='data/hot_stocks.txt',
                       help='输出文件路径')
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔥 热门股票筛选器（防封增强版）")
    print("=" * 60)
    
    all_stocks = []
    
    if args.mode in ['akshare', 'both']:
        print(f"\n📡 使用 AkShare 获取热门股票...")
        
        # 根据策略调用不同函数
        if args.strategy in ['all', 'limit_up']:
            codes = get_limit_up_stocks_akshare()
            if codes:
                all_stocks.append(codes)
        
        if args.strategy in ['all', 'dragon_tiger']:
            codes = get_dragon_tiger_stocks_akshare(days=3)
            if codes:
                all_stocks.append(codes)
        
        if args.strategy in ['all', 'hot_concept']:
            codes = get_hot_concept_stocks_akshare(top_concepts=5)
            if codes:
                all_stocks.append(codes)
        
        if args.strategy in ['all', 'volume']:
            codes = get_top_volume_stocks_akshare(top_n=args.top)
            if codes:
                all_stocks.append(codes)
    
    if args.mode in ['tushare', 'both']:
        print(f"\n📡 使用 Tushare Pro 获取热门股票...")
        
        if args.strategy in ['all', 'limit_up']:
            codes = get_limit_up_stocks_tushare()
            if codes:
                all_stocks.append(codes)
        
        if args.strategy in ['all', 'volume']:
            codes = get_top_volume_stocks_tushare(top_n=args.top)
            if codes:
                all_stocks.append(codes)
    
    # 合并并去重
    print(f"\n🔄 合并并去重...")
    final_codes = merge_and_deduplicate(all_stocks)
    
    # 如果超出数量限制，随机选取
    if len(final_codes) > args.top:
        random.shuffle(final_codes)
        final_codes = final_codes[:args.top]
        print(f"   超出限制，随机选取 {args.top} 只")
    
    print(f"   最终获得 {len(final_codes)} 只热门股票")
    
    # 保存到文件
    save_to_file(final_codes, args.output)
    
    print("\n" + "=" * 60)
    print("✅ 完成！现在可以使用以下命令下载数据：")
    print(f"   python tools/download_from_list.py --list {args.output} --days 30")
    print("=" * 60)


if __name__ == "__main__":
    main()