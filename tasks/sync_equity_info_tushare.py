#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
同步全A股流通市值数据（Tushare版本）

功能：
1. 从 Tushare daily_basic 接口获取每日指标
2. 按 trade_date 索引存储历史数据
3. 支持增量更新（只获取缺失日期）
4. 自动清理超过30天的过期数据
5. 提供查询接口供 intraday 扫描使用

Author: iFlow CLI
Version: V2.0
"""

import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    print("⚠️ 警告: Tushare未安装，请运行: pip install tushare")

# 配置
DATA_FILE = Path("data/equity_info_tushare.json")
RETENTION_DAYS = 30  # 保留最近30天的数据
TOKEN = os.getenv('TUSHARE_TOKEN')  # 从环境变量读取

# 初始化 tushare
if TUSHARE_AVAILABLE and TOKEN:
    pro = ts.pro_api(TOKEN)
else:
    pro = None

def load_equity_info():
    """
    加载现有的流通市值数据

    Returns:
        dict: {
            "latest_update": "20250813",
            "retention_days": 30,
            "data": {
                "20250813": {
                    "603607.SH": {"float_mv": 1000000000, "total_mv": 2000000000, ...},
                    ...
                },
                ...
            }
        }
    """
    if not DATA_FILE.exists():
        return {
            "latest_update": None,
            "retention_days": RETENTION_DAYS,
            "data": {}
        }

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_equity_info(equity_data):
    """
    保存流通市值数据

    Args:
        equity_data: 数据字典
    """
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(equity_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 数据已保存到: {DATA_FILE}")

def clean_old_data(equity_data):
    """
    清理超过保留期的数据

    Args:
        equity_data: 数据字典

    Returns:
        dict: 清理后的数据字典
    """
    if not equity_data.get("data"):
        return equity_data

    # 计算截止日期
    cutoff_date = (datetime.now() - timedelta(days=RETENTION_DAYS)).strftime("%Y%m%d")

    # 过滤数据
    cleaned_data = {
        date: data 
        for date, data in equity_data["data"].items() 
        if date >= cutoff_date
    }

    removed_count = len(equity_data["data"]) - len(cleaned_data)
    if removed_count > 0:
        print(f"🗑️  清理了 {removed_count} 个过期日期的数据")

    equity_data["data"] = cleaned_data
    return equity_data

def fetch_daily_basic(trade_date):
    """
    从 tushare 获取指定日期的每日指标数据

    Args:
        trade_date: 交易日期，格式 YYYYMMDD，如 '20250812'

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
                'pb': row['pb']
            }

        print(f"✅ 获取成功：{len(result)} 只股票")
        return result

    except Exception as e:
        print(f"❌ 获取数据失败：{e}")
        return {}

def get_missing_dates(equity_data, days=5):
    """
    获取需要补充的交易日期列表

    Args:
        equity_data: 现有数据
        days: 向前查找的天数

    Returns:
        list: 缺失的日期列表，格式 ['20250812', '20250813', ...]
    """
    existing_dates = set(equity_data.get("data", {}).keys())

    # 生成最近 N 天的日期列表
    date_list = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        if date not in existing_dates:
            date_list.append(date)

    return sorted(date_list)

def sync_equity_info(incremental=True):
    """
    同步流通市值数据

    Args:
        incremental: 是否增量更新（只获取缺失日期）
    """
    if not TUSHARE_AVAILABLE:
        print("❌ Tushare不可用，无法同步数据")
        return

    print("=" * 60)
    print("开始同步流通市值数据")
    print("=" * 60)

    # 1. 加载现有数据
    equity_data = load_equity_info()

    # 2. 确定需要获取的日期
    if incremental:
        dates_to_fetch = get_missing_dates(equity_data, days=5)
        if not dates_to_fetch:
            print("✅ 数据已是最新，无需更新")
            return
        print(f"📅 需要更新的日期：{dates_to_fetch}")
    else:
        # 全量更新：只获取今天
        dates_to_fetch = [datetime.now().strftime("%Y%m%d")]
        print(f"📅 全量更新模式：{dates_to_fetch}")

    # 3. 逐日获取数据
    for trade_date in dates_to_fetch:
        daily_data = fetch_daily_basic(trade_date)
        if daily_data:
            equity_data["data"][trade_date] = daily_data
            equity_data["latest_update"] = trade_date

    # 4. 清理过期数据
    equity_data = clean_old_data(equity_data)

    # 5. 保存数据
    save_equity_info(equity_data)

    # 6. 统计信息
    print("\n" + "=" * 60)
    print("同步完成")
    print("=" * 60)
    print(f"📊 数据日期范围：{len(equity_data['data'])} 天")
    print(f"📅 最新日期：{equity_data.get('latest_update', 'N/A')}")
    if equity_data['data']:
        latest_date = max(equity_data['data'].keys())
        print(f"📈 最新数据股票数：{len(equity_data['data'][latest_date])}")

def get_circ_mv(ts_code, trade_date=None):
    """
    查询指定股票在指定日期的流通市值

    Args:
        ts_code: 股票代码，如 '603607.SH'
        trade_date: 交易日期，格式 YYYYMMDD。如不指定，使用最新日期

    Returns:
        float: 流通市值（元），如果未找到返回 0
    """
    equity_data = load_equity_info()

    # 如果未指定日期，使用最新日期
    if trade_date is None:
        trade_date = equity_data.get("latest_update")
        if not trade_date:
            return 0

    # 查询数据
    daily_data = equity_data.get("data", {}).get(trade_date, {})
    stock_data = daily_data.get(ts_code, {})

    return stock_data.get('float_mv', 0)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='同步股票流通市值数据')
    parser.add_argument('--full', action='store_true', help='全量更新（默认为增量更新）')
    parser.add_argument('--query', type=str, help='查询指定股票的流通市值，格式：股票代码')
    parser.add_argument('--date', type=str, help='指定查询日期，格式：YYYYMMDD')

    args = parser.parse_args()

    if args.query:
        # 查询模式
        circ_mv = get_circ_mv(args.query, args.date)
        print(f"\n股票代码：{args.query}")
        print(f"交易日期：{args.date or '最新'}")
        print(f"流通市值：{circ_mv:,.0f} 元 ({circ_mv/100000000:.2f} 亿)")
    else:
        # 同步模式
        sync_equity_info(incremental=not args.full)
