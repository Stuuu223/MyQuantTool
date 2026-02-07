#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
同步流通市值数据（多日期白名单模式）

功能：
1. 从Tushare daily_basic接口获取指定股票的每日指标
2. 支持多日期同步，只同步快照中出现的股票
3. 针对2026-02-05 ~ 2026-02-06的股票进行定向同步

Author: iFlow CLI
Version: V2.2
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    print("⚠️  警告: Tushare未安装，请运行: pip install tushare")

# 配置
DATA_FILE = Path("data/equity_info_tushare.json")
RETENTION_DAYS = 30
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"  # 直接使用token
WHITELIST_FILE = "pending_equity_codes_multi_date.txt"
TRADE_DATES = ["20260205", "20260206"]  # 要同步的日期

# 初始化tushare
if TUSHARE_AVAILABLE and TOKEN:
    pro = ts.pro_api(TOKEN)
else:
    pro = None

def load_whitelist():
    """加载白名单股票代码"""
    if not Path(WHITELIST_FILE).exists():
        print(f"❌ 白名单文件不存在: {WHITELIST_FILE}")
        return []
    
    with open(WHITELIST_FILE, 'r', encoding='utf-8') as f:
        codes = [line.strip() for line in f if line.strip()]
    
    print(f"✅ 加载白名单: {len(codes)} 只股票")
    return codes

def load_equity_info():
    """加载现有的流通市值数据"""
    if not DATA_FILE.exists():
        return {
            "latest_update": None,
            "retention_days": RETENTION_DAYS,
            "data": {}
        }
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_equity_info(equity_data):
    """保存流通市值数据"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(equity_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 数据已保存到: {DATA_FILE}")

def fetch_daily_basic(trade_date, whitelist=None):
    """
    从tushare获取指定日期的每日指标数据
    
    Args:
        trade_date: 交易日期，格式 YYYYMMDD
        whitelist: 白名单股票代码列表，只获取这些股票的数据
    
    Returns:
        dict: {ts_code: {float_mv, total_mv, ...}}
    """
    if not pro:
        print("❌ Tushare未正确初始化，请检查 TUSHARE_TOKEN 环境变量")
        return {}
    
    print(f"📊 正在获取 {trade_date} 的每日指标数据...")
    
    try:
        df = pro.daily_basic(
            trade_date=trade_date,
            fields='ts_code,trade_date,close,turnover_rate,volume_ratio,pe,pb,ps,total_mv,circ_mv'
        )
        
        if df.empty:
            print(f"⚠️  {trade_date} 无数据（可能是非交易日）")
            return {}
        
        # 如果有白名单，只保留白名单中的股票
        if whitelist:
            df = df[df['ts_code'].isin(whitelist)]
            if df.empty:
                print(f"⚠️  {trade_date} 在白名单中无数据")
                return {}
            print(f"📋 白名单匹配: {len(df)} 只股票")
        
        # 转换为字典格式
        result = {}
        for _, row in df.iterrows():
            ts_code = row['ts_code']
            result[ts_code] = {
                'float_mv': row['circ_mv'] * 10000 if row['circ_mv'] else 0,  # 万元→元
                'total_mv': row['total_mv'] * 10000 if row['total_mv'] else 0,
                'close': row['close'],
                'turnover_rate': row['turnover_rate'],
                'pe': row['pe'],
                'pb': row['pb'],
                'ps': row['ps']
            }
        
        return result
    
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        return {}

def sync_multi_date():
    """
    多日期白名单模式同步：只同步白名单中的股票
    """
    if not TUSHARE_AVAILABLE:
        print("❌ Tushare不可用，无法同步数据")
        return
    
    print("=" * 60)
    print("开始多日期白名单模式同步")
    print("=" * 60)
    
    # 1. 加载白名单
    whitelist = load_whitelist()
    if not whitelist:
        print("❌ 白名单为空，无法同步")
        return
    
    # 2. 加载现有数据
    equity_data = load_equity_info()
    
    # 3. 对每个日期获取数据
    all_daily_data = {}
    for trade_date in TRADE_DATES:
        print(f"\n{'=' * 60}")
        print(f"同步日期: {trade_date}")
        print('=' * 60)
        
        daily_data = fetch_daily_basic(trade_date, whitelist)
        
        if daily_data:
            all_daily_data[trade_date] = daily_data
            print(f"✅ {trade_date} 同步成功: {len(daily_data)} 只股票")
        else:
            print(f"⚠️  {trade_date} 未获取到数据")
    
    # 4. 更新并保存数据
    if all_daily_data:
        if "data" not in equity_data:
            equity_data["data"] = {}
        
        # 合并数据
        for trade_date, daily_data in all_daily_data.items():
            equity_data["data"][trade_date] = daily_data
        
        # 更新最后更新时间
        latest_date = max(all_daily_data.keys())
        equity_data["latest_update"] = latest_date
        
        # 保存数据
        save_equity_info(equity_data)
        
        # 5. 统计信息
        print("\n" + "=" * 60)
        print("同步完成")
        print("=" * 60)
        print(f"📅 同步日期范围：{TRADE_DATES[0]} ~ {TRADE_DATES[-1]}")
        print(f"📊 白名单股票数：{len(whitelist)}")
        print(f"📋 成功同步的日期数：{len(all_daily_data)}")
        for trade_date, daily_data in all_daily_data.items():
            print(f"   - {trade_date}: {len(daily_data)} 只股票")
        
        # 6. 统计失败的股票
        all_synced_codes = set()
        for daily_data in all_daily_data.values():
            all_synced_codes.update(daily_data.keys())
        
        failed_codes = set(whitelist) - all_synced_codes
        if failed_codes:
            print(f"\n⚠️  完全同步失败的股票 ({len(failed_codes)} 只):")
            for code in sorted(failed_codes)[:10]:
                print(f"   - {code}")
            if len(failed_codes) > 10:
                print(f"   ... 还有 {len(failed_codes) - 10} 只")
    else:
        print("❌ 未获取到任何数据")

if __name__ == '__main__':
    sync_multi_date()