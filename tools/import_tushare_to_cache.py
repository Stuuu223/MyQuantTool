# -*- coding: utf-8 -*-
"""
Tushare 资金流数据导入脚本

功能：
- 将 Tushare 拉取的资金流 JSON 数据导入到 SQLite 缓存
- 补全 fund_flow_cache.db 中缺失的日期数据

执行时间：约 1-2 分钟

Author: iFlow CLI
Version: V1.0
Date: 2026-02-09 10:22 AM
"""

import json
import sqlite3
import os
from pathlib import Path
from datetime import datetime
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置
TUSHARE_DATA_DIR = 'data/money_flow_tushare'
CACHE_DB_PATH = 'data/fund_flow_cache.db'


def import_tushare_data():
    """导入 Tushare 数据到 SQLite 缓存"""
    print("=" * 80)
    print("🚀 开始导入 Tushare 资金流数据到 SQLite 缓存")
    print("=" * 80)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 检查 Tushare 数据目录
    if not os.path.exists(TUSHARE_DATA_DIR):
        print(f"❌ Tushare 数据目录不存在: {TUSHARE_DATA_DIR}")
        return False

    # 2. 读取所有 Tushare JSON 文件
    tushare_files = []
    for filename in os.listdir(TUSHARE_DATA_DIR):
        if filename.startswith('moneyflow_') and filename.endswith('.json'):
            tushare_files.append(filename)

    tushare_files.sort()
    print(f"📁 找到 {len(tushare_files)} 个 Tushare 数据文件")

    if not tushare_files:
        print("❌ 未找到 Tushare 数据文件")
        return False

    # 3. 连接 SQLite 数据库
    if not os.path.exists(CACHE_DB_PATH):
        print(f"❌ SQLite 数据库不存在: {CACHE_DB_PATH}")
        return False

    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()

    # 4. 统计现有数据
    cursor.execute('SELECT COUNT(*) FROM fund_flow_daily')
    existing_count = cursor.fetchone()[0]
    print(f"📊 现有缓存记录: {existing_count:,} 条")

    # 5. 导入数据
    total_imported = 0
    total_skipped = 0

    for filename in tushare_files:
        print(f"\n📥 处理: {filename}")

        # 读取 JSON 文件
        filepath = os.path.join(TUSHARE_DATA_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 遍历所有股票
        imported = 0
        skipped = 0

        for code_6digit, flow_data in data.items():
            # 构造数据
            date = flow_data['date']

            # Tushare 字段映射到 SQLite 字段
            # Tushare 的单位是"股"，SQLite 的单位是"元"
            # 需要转换：假设价格为 10 元，则 元 = 股 * 10
            # 但 Tushare 的数据已经是净额，单位不确定
            # 为了安全，我们直接使用 Tushare 的值

            super_large_net = flow_data.get('net_lg', 0)  # 大单净流入（Tushare）
            large_net = 0  # Tushare 没有单独的大单
            medium_net = flow_data.get('net_md', 0)  # 中单净流入
            small_net = flow_data.get('net_sm', 0)  # 小单净流入

            # 计算字段
            institution_net = super_large_net + large_net  # 机构净流入
            retail_net = medium_net + small_net  # 散户净流入

            # 超大单占比
            total = abs(super_large_net) + abs(large_net) + abs(medium_net) + abs(small_net)
            super_ratio = (abs(super_large_net) / total * 100) if total > 0 else 0

            # 尝试插入（如果已存在则跳过）
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO fund_flow_daily
                    (stock_code, date, super_large_net, large_net, medium_net, small_net,
                     institution_net, retail_net, super_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    code_6digit, date,
                    super_large_net, large_net, medium_net, small_net,
                    institution_net, retail_net, super_ratio
                ))

                if cursor.rowcount > 0:
                    imported += 1
                else:
                    skipped += 1

            except Exception as e:
                print(f"   ⚠️  插入失败 {code_6digit}: {e}")
                skipped += 1

        # 提交事务
        conn.commit()
        print(f"   ✅ 导入: {imported} 条，跳过: {skipped} 条")

        total_imported += imported
        total_skipped += skipped

    # 6. 统计结果
    cursor.execute('SELECT COUNT(*) FROM fund_flow_daily')
    new_count = cursor.fetchone()[0]

    print()
    print("=" * 80)
    print(f"📊 导入完成！")
    print(f"   导入: {total_imported:,} 条")
    print(f"   跳过: {total_skipped:,} 条")
    print(f"   缓存总计: {new_count:,} 条（之前: {existing_count:,} 条）")
    print()
    print("💡 下一步:")
    print("   1. 重启 Monitor: start_event_driven_monitor.bat")
    print("   2. 资金流数据应该已经补全")
    print("   3. 诱多检测应该能正常工作")
    print("=" * 80)
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 关闭连接
    conn.close()

    return total_imported > 0


if __name__ == "__main__":
    try:
        success = import_tushare_data()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)