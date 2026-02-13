#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价数据查看工具

功能：
1. 查看Redis中的竞价数据
2. 查看SQLite中的竞价数据
3. 导出竞价数据到CSV

使用方法：
    python tools/view_auction_data.py
    python tools/view_auction_data.py --code 600519.SH
    python tools/view_auction_data.py --export auction_export.csv
"""

import sys
import json
import csv
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.database_manager import DatabaseManager
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def view_redis_auction_data(date=None, code=None, limit=10):
    """
    查看Redis中的竞价数据

    Args:
        date: 日期（格式：YYYYMMDD），默认为今天
        code: 股票代码（如：600519.SH），None表示查看所有
        limit: 显示数量限制
    """
    print("\n" + "=" * 80)
    print("Redis竞价数据查看")
    print("=" * 80)

    if date is None:
        date = datetime.now().strftime("%Y%m%d")

    db_manager = DatabaseManager()

    try:
        db_manager._init_redis()

        if not db_manager._redis_client:
            print("❌ Redis未连接")
            return

        # 构建key模式
        if code:
            pattern = f"auction:{date}:{code}"
            print(f"📊 查询股票: {code}")
        else:
            pattern = f"auction:{date}:*"
            print(f"📊 查询日期: {date}")

        # 获取所有keys
        keys = db_manager._redis_client.keys(pattern)

        if not keys:
            print(f"❌ 未找到竞价数据")
            return

        print(f"✅ 找到 {len(keys)} 条记录")
        print()

        # 显示数据
        print(f"{'股票代码':<15} {'价格':<10} {'昨收':<10} {'成交量':<15} {'时间戳'}")
        print("-" * 80)

        for i, key in enumerate(keys[:limit]):
            try:
                raw_data = db_manager._redis_client.get(key)
                data = json.loads(raw_data)

                stock_code = data.get('code', '')
                last_price = data.get('last_price', 0)
                last_close = data.get('last_close', 0)
                volume = data.get('volume', 0)
                timestamp = data.get('timestamp', '')

                print(f"{stock_code:<15} {last_price:<10.2f} {last_close:<10.2f} {volume:<15} {timestamp}")

            except Exception as e:
                print(f"❌ 解析失败: {key} - {e}")

        if len(keys) > limit:
            print(f"\n... 还有 {len(keys) - limit} 条记录")

    except Exception as e:
        print(f"❌ Redis查询失败: {e}")


def view_sqlite_auction_data(date=None, code=None, limit=10):
    """
    查看SQLite中的竞价数据

    Args:
        date: 日期（格式：YYYY-MM-DD），默认为今天
        code: 股票代码（如：600519.SH），None表示查看所有
        limit: 显示数量限制
    """
    print("\n" + "=" * 80)
    print("SQLite竞价数据查看")
    print("=" * 80)

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    db_path = project_root / "data" / "auction_snapshots.db"

    try:
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 构建查询
        if code:
            query = """
                SELECT code, auction_price, auction_volume, auction_change, auction_time
                FROM auction_snapshots
                WHERE date = ? AND code = ?
                LIMIT ?
            """
            cursor.execute(query, (date, code, limit))
            print(f"📊 查询股票: {code}")
        else:
            query = """
                SELECT code, auction_price, auction_volume, auction_change, auction_time
                FROM auction_snapshots
                WHERE date = ?
                ORDER BY auction_change DESC
                LIMIT ?
            """
            cursor.execute(query, (date, limit))
            print(f"📊 查询日期: {date}（按涨幅排序）")

        rows = cursor.fetchall()

        if not rows:
            print(f"❌ 未找到竞价数据")
            conn.close()
            return

        print(f"✅ 找到 {len(rows)} 条记录")
        print()

        # 显示数据
        print(f"{'股票代码':<15} {'竞价价格':<12} {'成交量':<15} {'涨跌幅':<12} {'时间'}")
        print("-" * 80)

        for row in rows:
            code, price, volume, change, auction_time = row
            change_pct = change * 100 if change else 0

            # 涨跌幅颜色标记
            if change_pct > 0:
                change_str = f"+{change_pct:.2f}%"
            elif change_pct < 0:
                change_str = f"{change_pct:.2f}%"
            else:
                change_str = "0.00%"

            print(f"{code:<15} {price:<12.2f} {volume:<15} {change_str:<12} {auction_time}")

        conn.close()

    except Exception as e:
        print(f"❌ SQLite查询失败: {e}")


def export_auction_data(date=None, output_file="auction_export.csv", source='redis'):
    """
    导出竞价数据到CSV

    Args:
        date: 日期（格式：YYYY-MM-DD），默认为今天
        output_file: 输出文件路径
        source: 数据源（redis/sqlite/both）
    """
    print("\n" + "=" * 80)
    print(f"导出竞价数据到CSV（来源: {source}）")
    print("=" * 80)

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    output_path = project_root / output_file

    try:
        # 如果是both，优先使用Redis
        if source == 'both':
            source = 'redis'

        if source == 'redis':
            # 从Redis导出
            db_manager = DatabaseManager()
            db_manager._init_redis()

            if not db_manager._redis_client:
                print("❌ Redis未连接")
                return

            # 获取所有keys
            pattern = f"auction:{date}:*"
            keys = db_manager._redis_client.keys(pattern)

            if not keys:
                print(f"❌ Redis中未找到竞价数据")
                return

            # 写入CSV
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    '日期', '股票代码', '竞价价格', '昨收价格', '成交量', '成交额', '时间戳'
                ])

                for key in keys:
                    try:
                        raw_data = db_manager._redis_client.get(key)
                        data = json.loads(raw_data)

                        # 计算涨跌幅
                        last_price = data.get('last_price', 0)
                        last_close = data.get('last_close', 0)
                        if last_close > 0:
                            change = (last_price - last_close) / last_close
                        else:
                            change = 0.0

                        writer.writerow([
                            date,
                            data.get('code', ''),
                            last_price,
                            last_close,
                            data.get('volume', 0),
                            data.get('amount', 0),
                            data.get('timestamp', '')
                        ])
                    except Exception as e:
                        print(f"⚠️ 跳过数据: {key} - {e}")

            print(f"✅ 已从Redis导出 {len(keys)} 条记录到: {output_path}")

        else:
            # 从SQLite导出
            db_path = project_root / "data" / "auction_snapshots.db"

            import sqlite3

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            query = """
                SELECT date, code, name, auction_price, auction_volume, auction_amount,
                       auction_change, volume_ratio, bid_vol_1, ask_vol_1, auction_time
                FROM auction_snapshots
                WHERE date = ?
                ORDER BY auction_change DESC
            """

            cursor.execute(query, (date,))
            rows = cursor.fetchall()

            if not rows:
                print(f"❌ SQLite中未找到竞价数据")
                conn.close()
                return

            # 写入CSV
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    '日期', '股票代码', '股票名称', '竞价价格', '成交量', '成交额',
                    '涨跌幅', '量比', '买一量', '卖一量', '竞价时间'
                ])

                for row in rows:
                    writer.writerow(row)

            print(f"✅ 已从SQLite导出 {len(rows)} 条记录到: {output_path}")
            conn.close()

    except Exception as e:
        print(f"❌ 导出失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='竞价数据查看工具')
    parser.add_argument('--date', type=str, help='日期（格式：YYYYMMDD或YYYY-MM-DD）')
    parser.add_argument('--code', type=str, help='股票代码（如：600519.SH）')
    parser.add_argument('--limit', type=int, default=10, help='显示数量限制')
    parser.add_argument('--export', type=str, help='导出到CSV文件')
    parser.add_argument('--source', choices=['redis', 'sqlite', 'both'], default='both',
                        help='数据源：redis/sqlite/both')

    args = parser.parse_args()

    # 导出模式
    if args.export:
        export_auction_data(args.date, args.export, args.source)
        return

    # 查看模式
    if args.source in ['redis', 'both']:
        view_redis_auction_data(args.date, args.code, args.limit)

    if args.source in ['sqlite', 'both']:
        view_sqlite_auction_data(args.date, args.code, args.limit)

    # 使用说明
    print("\n" + "=" * 80)
    print("Redis数据访问方法")
    print("=" * 80)
    print("\n1. 使用redis-cli命令行工具：")
    print("   redis-cli")
    print("   KEYS auction:20260213:*")
    print("   GET auction:20260213:600519.SH")
    print("\n2. 使用Python代码：")
    print("   import redis")
    print("   r = redis.Redis(host='localhost', port=6379)")
    print("   data = r.get('auction:20260213:600519.SH')")
    print("   import json; print(json.loads(data))")
    print("\n3. 使用本工具查看：")
    print("   python tools/view_auction_data.py --source redis")
    print("   python tools/view_auction_data.py --source sqlite")
    print("   python tools/view_auction_data.py --code 600519.SH")
    print("   python tools/view_auction_data.py --export auction_export.csv")
    print("=" * 80)


if __name__ == "__main__":
    main()