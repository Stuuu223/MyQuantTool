# -*- coding: utf-8 -*-
"""
紧急全市场股本数据更新脚本 - 9:47 AM 极速版

功能：
- 一次性拉取全市场 daily_basic 数据
- 更新 equity_info_tushare.json
- 补充 circ_mv, total_mv, float_share 等关键字段

Author: iFlow CLI
Version: Emergency V1.0
"""

import tushare as ts
import json
import pandas as pd
from datetime import datetime
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Tushare Token
TOKEN = '1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b'

OUTPUT_PATH = 'data/equity_info_tushare.json'

def run_emergency_update():
    """执行紧急数据更新"""
    print("🚀 [9:47 AM] 开始紧急更新全市场股本数据...")
    print("=" * 80)

    # 1. 初始化 Tushare
    try:
        ts.set_token(TOKEN)
        pro = ts.pro_api()
        print("✅ Tushare 连接成功")
    except Exception as e:
        print(f"❌ Tushare 连接失败: {e}")
        return False

    # 2. 确定目标日期（使用最近交易日 20260206）
    target_date = '20260206'
    print(f"📅 目标日期: {target_date}")
    print("=" * 80)

    # 3. 拉取每日指标 (Daily Basic) - 全市场
    print("📥 拉取 daily_basic (全市场)...")

    try:
        df = pro.daily_basic(
            ts_code='',
            trade_date=target_date,
            fields='ts_code,trade_date,turnover_rate,volume_ratio,pe,pb,float_share,total_share,total_mv,circ_mv'
        )
    except Exception as e:
        print(f"❌ 拉取数据失败: {e}")
        return False

    if df.empty:
        print(f"❌ {target_date} 数据为空！")
        print("   可能原因：")
        print("   1. 今天未收盘，daily_basic 未生成")
        print("   2. 网络连接问题")
        print("   3. Token 权限不足")
        return False

    print(f"✅ 获取到 {len(df)} 条数据")
    print("=" * 80)

    # 4. 转换为需要的结构
    data_dict = {}
    success_count = 0
    error_count = 0

    for _, row in df.iterrows():
        try:
            code = row['ts_code']

            # Tushare 单位是万元，转为元 (* 10000)
            circ_mv = row['circ_mv'] * 10000 if pd.notna(row['circ_mv']) else 0
            total_mv = row['total_mv'] * 10000 if pd.notna(row['total_mv']) else 0
            float_share = row['float_share'] * 10000 if pd.notna(row['float_share']) else 0
            total_share = row['total_share'] * 10000 if pd.notna(row['total_share']) else 0

            # 构建股票数据
            data_dict[code] = {
                "circ_mv": circ_mv,      # 流通市值（元）
                "total_mv": total_mv,    # 总市值（元）
                "total_share": total_share,    # 总股本（股）
                "float_share": float_share,    # 流通股本（股）
                "float_mv": circ_mv,     # 别名（兼容 Hotfix）
                "turnover_rate": row['turnover_rate'] if pd.notna(row['turnover_rate']) else 0,
                "volume_ratio": row['volume_ratio'] if pd.notna(row['volume_ratio']) else 0,
                "pe": row['pe'] if pd.notna(row['pe']) else 0,
                "pb": row['pb'] if pd.notna(row['pb']) else 0
            }

            success_count += 1

        except Exception as e:
            error_count += 1
            if error_count <= 3:  # 只打印前3个错误
                print(f"⚠️  处理股票数据失败: {e}")

    print(f"✅ 成功处理: {success_count} 只股票")
    print(f"⚠️  失败: {error_count} 只股票")
    print("=" * 80)

    # 5. 构建最终 JSON
    final_json = {
        "latest_update": target_date,
        "retention_days": 30,
        "data": {
            target_date: data_dict
        }
    }

    # 6. 保存
    try:
        # 先备份旧文件
        backup_path = f"{OUTPUT_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if os.path.exists(OUTPUT_PATH):
            import shutil
            shutil.copy2(OUTPUT_PATH, backup_path)
            print(f"💾 已备份旧文件至: {backup_path}")

        # 保存新文件
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(final_json, f, ensure_ascii=False, indent=2)

        file_size = os.path.getsize(OUTPUT_PATH) / 1024
        print(f"✅ 已保存至: {OUTPUT_PATH} ({file_size:.2f} KB)")

    except Exception as e:
        print(f"❌ 保存文件失败: {e}")
        return False

    print("=" * 80)
    print("✅ [9:47 AM] 紧急更新完成！")
    print("🚀 请立即重启 Monitor: start_event_driven_monitor.bat")
    print("=" * 80)

    return True

if __name__ == "__main__":
    success = run_emergency_update()
    sys.exit(0 if success else 1)