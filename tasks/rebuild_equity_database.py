# -*- coding: utf-8 -*-
"""
全市场股权历史数据库重建脚本

功能：
- 拉取过去365天的全市场 daily_basic 数据
- 构建 {code: {date: {...}}} 时序数据结构
- 彻底解决数据缺失问题

执行时间：约 5-10 分钟（取决于网络速度）

Author: iFlow CLI
Version: V1.0
Date: 2026-02-09 10:00 AM
"""

import tushare as ts
import json
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置
TOKEN = '1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b'
OUTPUT_PATH = 'data/equity_info_tushare.json'
HISTORY_DAYS = 365
RATE_LIMIT = 0.3  # 每次请求间隔（秒）

def fetch_trade_cal(start_date, end_date):
    """获取交易日历"""
    try:
        df = pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)
        trade_dates = df[df['is_open'] == 1]['cal_date'].tolist()
        return trade_dates
    except Exception as e:
        print(f"❌ 获取交易日历失败: {e}")
        return []

def rebuild_database():
    """重建全市场历史数据库"""
    print("=" * 80)
    print("🚀 开始构建全市场历史数据库")
    print(f"📅 时间范围: 过去 {HISTORY_DAYS} 天")
    print("=" * 80)

    # 1. 初始化 Tushare
    try:
        ts.set_token(TOKEN)
        global pro
        pro = ts.pro_api()
        print("✅ Tushare 连接成功")
    except Exception as e:
        print(f"❌ Tushare 连接失败: {e}")
        return False

    # 2. 确定日期范围
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=HISTORY_DAYS)).strftime('%Y%m%d')

    print(f"📅 日期范围: {start_date} -> {end_date}")

    # 3. 获取交易日历
    trade_dates = fetch_trade_cal(start_date, end_date)
    trade_dates.sort(reverse=True)  # 倒序，优先拉最近的

    print(f"📅 交易日数量: {len(trade_dates)} 天")
    print("=" * 80)

    # 4. 准备数据结构: {code: {date: {...}}}
    full_data = {}

    # 5. 逐日拉取
    success_days = 0
    failed_days = 0
    total_stocks = 0

    for i, date in enumerate(trade_dates):
        print(f"📥 [{i+1}/{len(trade_dates)}] {date}...", end=" ", flush=True)

        try:
            # 限频，防封
            time.sleep(RATE_LIMIT)

            # 拉取 daily_basic
            df = pro.daily_basic(
                trade_date=date,
                fields='ts_code,circ_mv,total_mv,total_share,float_share,turnover_rate,pe,pb'
            )

            if df.empty:
                print("⚠️  无数据")
                failed_days += 1
                continue

            # 存入内存结构
            day_count = 0
            for _, row in df.iterrows():
                code = row['ts_code']
                if code not in full_data:
                    full_data[code] = {}

                # 单位转换：万元 -> 元
                full_data[code][date] = {
                    "circ_mv": row['circ_mv'] * 10000 if pd.notna(row['circ_mv']) else 0,
                    "total_mv": row['total_mv'] * 10000 if pd.notna(row['total_mv']) else 0,
                    "total_share": row['total_share'] * 10000 if pd.notna(row['total_share']) else 0,
                    "float_share": row['float_share'] * 10000 if pd.notna(row['float_share']) else 0,
                    "turnover_rate": row['turnover_rate'] if pd.notna(row['turnover_rate']) else 0,
                    "pe": row['pe'] if pd.notna(row['pe']) else 0,
                    "pb": row['pb'] if pd.notna(row['pb']) else 0
                }
                day_count += 1

            print(f"✅ {day_count} 条")
            success_days += 1
            total_stocks += day_count

            # 每10天显示一次进度
            if (i + 1) % 10 == 0:
                print(f"   📊 进度: 已处理 {i+1}/{len(trade_dates)} 天")

        except Exception as e:
            print(f"❌ 失败: {e}")
            failed_days += 1
            time.sleep(5)  # 报错多歇会儿

    print("=" * 80)
    print(f"📊 统计:")
    print(f"   成功: {success_days} 天")
    print(f"   失败: {failed_days} 天")
    print(f"   总记录: {total_stocks:,} 条")
    print(f"   股票数量: {len(full_data):,} 只")
    print("=" * 80)

    # 6. 保存
    print("💾 正在保存大文件...")

    # 包装 metadata
    final_json = {
        "latest_update": end_date,
        "history_days": HISTORY_DAYS,
        "data_structure": "{code: {date: {...}}}",
        "trade_date_count": len(trade_dates),
        "stock_count": len(full_data),
        "data": full_data
    }

    # 先备份
    if os.path.exists(OUTPUT_PATH):
        backup_path = f"{OUTPUT_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy2(OUTPUT_PATH, backup_path)
        print(f"💾 已备份: {backup_path}")

    # 保存新文件（不缩进，减小体积）
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False)

    file_size_mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
    print(f"✅ 数据库构建完成！")
    print(f"   文件大小: {file_size_mb:.2f} MB")
    print(f"   文件路径: {OUTPUT_PATH}")
    print("=" * 80)
    print("⚠️  重要提示：")
    print("   1. 数据结构已改变为 {code: {date: {...}}}")
    print("   2. 需要配合更新 equity_data_accessor.py")
    print("   3. 可以移除早上的 Hotfix 代码")
    print("=" * 80)

    return True

if __name__ == "__main__":
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    success = rebuild_database()

    print()
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    sys.exit(0 if success else 1)