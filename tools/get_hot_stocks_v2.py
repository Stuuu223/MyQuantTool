#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热门股票筛选器 V2（严格防封版）

核心改进：
1. 移除高风险的"热门概念板块"批量调用（容易触发封禁）
2. 聚焦最可靠的策略：成交额Top N（流动性最好的股票）
3. 增加随机延迟 + 缓存机制
4. Tushare 优先（Token认证，不受IP限制）
5. 更保守的速率限制：8秒间隔，确保不超过 7.5 req/min

Author: MyQuantTool Team
Date: 2026-02-10
"""

import sys
import os
import time
import random
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
import argparse

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from logic.rate_limiter import RateLimiter
    RATE_LIMITER = RateLimiter(
        max_requests_per_minute=7,      # 更保守：7 < 20/3
        max_requests_per_hour=80,       # 更保守：80 < 200/2
        min_request_interval=8,         # 8秒间隔
        enable_logging=True
    )
except ImportError:
    RATE_LIMITER = None

TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', '')
if not TUSHARE_TOKEN:
    config_file = project_root / 'config' / 'tushare_token.txt'
    if config_file.exists():
        TUSHARE_TOKEN = config_file.read_text().strip()

CACHE_DIR = project_root / 'data' / 'cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_cache(cache_key: str, expire_hours: int = 12) -> List[str] | None:
    """从缓存加载数据（避免重复调用API）"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cache_time = datetime.fromisoformat(data['timestamp'])
        if datetime.now() - cache_time < timedelta(hours=expire_hours):
            print(f"   📦 从缓存加载（{cache_key}），缓存时间: {cache_time.strftime('%H:%M:%S')}")
            return data['codes']
    except:
        pass
    
    return None


def save_cache(cache_key: str, codes: List[str]):
    """保存到缓存"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    data = {
        'timestamp': datetime.now().isoformat(),
        'codes': codes
    }
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    """随机延迟（避免机器人检测）"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def get_top_volume_stocks_tushare(top_n: int = 500, date: str = None) -> List[str]:
    """
    Tushare Pro：获取成交额 Top N（最可靠的方式）
    
    优势：
    - Token认证，不受IP限制
    - 高权限账户配额大
    - 数据稳定
    """
    print(f"\n💰 Tushare Pro：获取成交额 Top {top_n} 股票...")
    
    if not TUSHARE_TOKEN:
        print("   ⚠️  Tushare Token 未配置，跳过")
        return []
    
    cache_key = f"tushare_volume_top_{top_n}_{date or 'latest'}"
    cached = load_cache(cache_key, expire_hours=12)
    if cached:
        return cached
    
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
    
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        
        # 获取交易日
        if date:
            trade_date = date.replace('-', '')
        else:
            today = datetime.now()
            trade_date = today.strftime('%Y%m%d')
            
            # 尝试最近5个交易日
            for i in range(5):
                try:
                    df = pro.daily(
                        trade_date=trade_date,
                        fields='ts_code,amount'
                    )
                    if len(df) > 0:
                        break
                    trade_date = (today - timedelta(days=i+1)).strftime('%Y%m%d')
                except Exception as e:
                    print(f"   ⚠️  尝试日期 {trade_date} 失败: {e}")
                    trade_date = (today - timedelta(days=i+1)).strftime('%Y%m%d')
        
        if RATE_LIMITER:
            RATE_LIMITER.record_request()
        
        random_delay(1, 2)
        
        # 获取股票基本信息（剔除ST）
        df_basic = pro.stock_basic(
            exchange='',
            list_status='L',
            fields='ts_code,name,market'
        )
        
        df = df.merge(df_basic, on='ts_code', how='left')
        
        # 过滤
        df = df[~df['name'].str.contains('ST', na=False)]      # 剔除ST
        df = df[~df['ts_code'].str.match(r'^(8|4|9)')]         # 剔除北交所
        df = df[df['market'].isin(['主板', '创业板', '科创板'])]  # 只要主流市场
        
        # 按成交额排序
        df = df.nlargest(top_n, 'amount')
        
        codes = df['ts_code'].tolist()
        
        print(f"   ✅ 成功获取 {len(codes)} 只股票")
        print(f"   📊 交易日期: {trade_date}")
        print(f"   💵 最小成交额: {df['amount'].min():.2f} 万元")
        
        save_cache(cache_key, codes)
        return codes
        
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return []


def get_top_volume_stocks_akshare(top_n: int = 500) -> List[str]:
    """
    AkShare 备选方案：获取成交额 Top N
    
    注意：
    - 只在 Tushare 失败时使用
    - 有IP封禁风险
    - 需要更长的延迟
    """
    print(f"\n💰 AkShare 备用：获取成交额 Top {top_n} 股票...")
    
    cache_key = f"akshare_volume_top_{top_n}_{datetime.now().strftime('%Y%m%d')}"
    cached = load_cache(cache_key, expire_hours=6)  # AkShare 缓存时间更短
    if cached:
        return cached
    
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
    
    try:
        import akshare as ak
        
        print("   ⏳ 正在获取实时行情（可能需要15-30秒）...")
        df = ak.stock_zh_a_spot_em()
        
        if RATE_LIMITER:
            RATE_LIMITER.record_request()
        
        random_delay(2, 4)  # AkShare 需要更长延迟
        
        # 过滤
        df = df[~df['名称'].str.contains('ST', na=False)]
        df = df[~df['代码'].str.match(r'^(8|4|9)')]
        
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
        
        print(f"   ✅ 成功获取 {len(codes)} 只股票")
        print(f"   💵 最小成交额: {df['成交额'].min():.2f} 元")
        
        save_cache(cache_key, codes)
        return codes
        
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return []


def get_stable_hot_stocks(
    top_n: int = 500,
    mode: str = 'tushare',
    date: str = None
) -> List[str]:
    """
    统一入口：优先 Tushare，失败时降级到 AkShare
    """
    print("\n" + "=" * 60)
    print("🔥 热门股票筛选器 V2（严格防封版）")
    print("=" * 60)
    print(f"\n📌 策略：成交额 Top {top_n}（流动性最好的股票）")
    print(f"📌 模式：{mode}")
    
    codes = []
    
    if mode in ['tushare', 'both']:
        codes = get_top_volume_stocks_tushare(top_n, date)
    
    if len(codes) == 0 and mode in ['akshare', 'both']:
        print("\n⚠️  Tushare 失败，切换到 AkShare 备用方案...")
        codes = get_top_volume_stocks_akshare(top_n)
    
    if len(codes) == 0:
        print("\n❌ 所有数据源均失败！")
        return []
    
    # 去重并排序
    codes = sorted(list(set(codes)))
    
    print(f"\n✅ 最终获得 {len(codes)} 只热门股票")
    print(f"   示例: {codes[:5]}")
    
    return codes


def main():
    parser = argparse.ArgumentParser(description='热门股票筛选器 V2（防封版）')
    parser.add_argument('--mode', type=str, default='tushare',
                        choices=['tushare', 'akshare', 'both'],
                        help='数据源：tushare（推荐） | akshare | both')
    parser.add_argument('--top', type=int, default=500,
                        help='股票数量（默认500）')
    parser.add_argument('--date', type=str, default=None,
                        help='指定日期（YYYY-MM-DD），默认最近交易日')
    parser.add_argument('--output', type=str, default='data/hot_stocks_v2.txt',
                        help='输出文件路径')
    args = parser.parse_args()
    
    # 获取股票列表
    codes = get_stable_hot_stocks(
        top_n=args.top,
        mode=args.mode,
        date=args.date
    )
    
    if len(codes) == 0:
        print("\n❌ 无法获取股票列表，程序退出")
        return
    
    # 保存到文件
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for code in codes:
            f.write(code + '\n')
    
    print(f"\n💾 已保存到: {output_path}")
    print("\n" + "=" * 60)
    print("✅ 完成！下一步：")
    print(f"   python tools/download_from_list.py --list {output_path} --days 90")
    print("=" * 60)


if __name__ == "__main__":
    main()