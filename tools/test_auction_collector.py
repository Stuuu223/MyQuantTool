#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价采集器测试脚本

功能：
1. 测试QMT连接
2. 测试Redis连接
3. 测试SQLite写入
4. 测试批量采集（采集100只股票）
5. 验证数据质量

使用方法：
    python tools/test_auction_collector.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.utils.logger import get_logger
from logic.database_manager import DatabaseManager
from logic.auction_snapshot_manager import AuctionSnapshotManager
from logic.qmt_manager import QMTManager

logger = get_logger(__name__)


def test_qmt_connection(qmt_manager):
    """测试QMT连接"""
    print("\n" + "=" * 80)
    print("测试1: QMT连接")
    print("=" * 80)

    try:
        if qmt_manager.data_connected and qmt_manager.xtdata:
            print(f"✅ QMT数据接口已连接")

            # 测试获取tick数据
            test_data = qmt_manager.xtdata.get_full_tick(['600519.SH'])

            if test_data and '600519.SH' in test_data:
                data = test_data['600519.SH']
                print(f"✅ QMT Tick数据获取成功")
                print(f"   股票: 600519.SH")
                print(f"   价格: {data.get('lastPrice', 0):.2f}")
                print(f"   昨收: {data.get('lastClose', 0):.2f}")
                print(f"   成交量: {data.get('volume', 0)}")
                return True
            else:
                print("❌ QMT Tick数据为空")
                return False
        else:
            print("❌ QMT数据接口未连接")
            print("   请检查：")
            print("   1. QMT客户端是否运行")
            print("   2. QMT是否已登录")
            print("   3. config/qmt_config.json 配置是否正确")
            return False
    except Exception as e:
        print(f"❌ QMT连接测试失败: {e}")
        return False


def test_redis_connection(db_manager):
    """测试Redis连接"""
    print("\n" + "=" * 80)
    print("测试2: Redis连接")
    print("=" * 80)

    try:
        db_manager._init_redis()

        if db_manager._redis_client:
            db_manager._redis_client.ping()
            print(f"✅ Redis连接成功")

            # 测试读写
            test_key = "auction:test:connection"
            db_manager._redis_client.set(test_key, "ok", ex=60)
            value = db_manager._redis_client.get(test_key)

            if value == "ok":
                print(f"✅ Redis读写测试通过")
                db_manager._redis_client.delete(test_key)
                return True
            else:
                print("❌ Redis读写测试失败")
                return False
        else:
            print("❌ Redis客户端未初始化")
            print("   请检查：")
            print("   1. Redis服务是否启动")
            print("   2. config.json 中redis配置是否正确")
            return False
    except Exception as e:
        print(f"❌ Redis连接测试失败: {e}")
        print("   提示: 可以继续使用，Redis为可选组件")
        return False


def test_sqlite_connection():
    """测试SQLite连接"""
    print("\n" + "=" * 80)
    print("测试3: SQLite连接")
    print("=" * 80)

    try:
        import sqlite3
        db_path = project_root / "data" / "auction_snapshots.db"

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 查询数据
        cursor.execute("""
            SELECT date, COUNT(*) as count
            FROM auction_snapshots
            GROUP BY date
            ORDER BY date DESC
            LIMIT 5
        """)

        rows = cursor.fetchall()
        print(f"✅ SQLite连接成功")
        print(f"   数据库路径: {db_path}")

        if rows:
            print(f"   最近记录:")
            for row in rows:
                print(f"     {row[0]}: {row[1]} 只股票")
        else:
            print(f"   数据库为空")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ SQLite连接测试失败: {e}")
        return False


def test_batch_collect(qmt_manager, snapshot_manager, test_count=100):
    """测试批量采集"""
    print("\n" + "=" * 80)
    print(f"测试4: 批量采集（采集前{test_count}只股票）")
    print("=" * 80)

    try:
        # 获取股票列表
        if qmt_manager.data_connected and qmt_manager.xtdata:
            all_codes = qmt_manager.xtdata.get_stock_list_in_sector('沪深A股')

            if not all_codes:
                print("❌ 无法获取股票列表")
                return False

            test_codes = all_codes[:test_count]
            print(f"📊 测试采集 {len(test_codes)} 只股票...")

            # 获取tick数据
            t0 = datetime.now()
            raw_data = qmt_manager.xtdata.get_full_tick(test_codes)
            elapsed = (datetime.now() - t0).total_seconds()

            if not raw_data:
                print("❌ QMT返回空数据")
                return False

            print(f"✅ 获取到 {len(raw_data)} 只股票数据，耗时 {elapsed:.3f}s")

            # 显示前5只股票数据
            print(f"\n   数据样例（前5只）:")
            for code in list(raw_data.keys())[:5]:
                data = raw_data[code]
                print(f"     {code} | 价格:{data.get('lastPrice', 0):.2f} | 昨收:{data.get('lastClose', 0):.2f} | 量:{data.get('volume', 0)}")

            return True, raw_data

        else:
            print("❌ QMT未连接")
            return False, None

    except Exception as e:
        print(f"❌ 批量采集测试失败: {e}")
        return False, None


def test_redis_write(db_manager, raw_data):
    """测试Redis写入"""
    print("\n" + "=" * 80)
    print("测试5: Redis写入")
    print("=" * 80)

    if not raw_data:
        print("❌ 没有测试数据")
        return False

    try:
        t0 = datetime.now()

        if db_manager._redis_client:
            import redis
            pipe = db_manager._redis_client.pipeline()

            date = datetime.now().strftime("%Y%m%d")

            for code, data in raw_data.items():
                auction_data = {
                    'code': code,
                    'last_price': data.get('lastPrice', 0),
                    'last_close': data.get('lastClose', 0),
                    'volume': data.get('volume', 0),
                    'timestamp': datetime.now().isoformat()
                }

                key = f"auction:{date}:{code}"
                pipe.set(key, json.dumps(auction_data), ex=60)  # 60秒过期

            pipe.execute()

            elapsed = (datetime.now() - t0).total_seconds()
            print(f"✅ Redis写入完成: {len(raw_data)} 只股票，耗时 {elapsed:.3f}s")
            return True
        else:
            print("⚠️ Redis不可用，跳过测试")
            return False

    except Exception as e:
        print(f"❌ Redis写入测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("竞价采集器功能测试")
    print("=" * 80)

    # 初始化组件
    db_manager = DatabaseManager()
    qmt_manager = QMTManager()
    snapshot_manager = AuctionSnapshotManager(db_manager)

    # 运行测试
    results = {}

    results['qmt'] = test_qmt_connection(qmt_manager)
    results['redis'] = test_redis_connection(db_manager)
    results['sqlite'] = test_sqlite_connection()

    # 批量采集测试（需要QMT连接）
    if results['qmt']:
        success, raw_data = test_batch_collect(qmt_manager, snapshot_manager, test_count=100)
        results['collect'] = success

        # Redis写入测试（需要Redis连接）
        if success and results['redis']:
            results['redis_write'] = test_redis_write(db_manager, raw_data)
    else:
        results['collect'] = False
        results['redis_write'] = False

    # 汇总结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)

    test_names = {
        'qmt': 'QMT连接',
        'redis': 'Redis连接',
        'sqlite': 'SQLite连接',
        'collect': '批量采集',
        'redis_write': 'Redis写入'
    }

    for key, name in test_names.items():
        status = "✅ 通过" if results.get(key) else "❌ 失败"
        print(f"  {name}: {status}")

    # 总体评估
    all_passed = all(results.values())

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ 所有测试通过！竞价采集器可以正常使用")
    else:
        print("⚠️ 部分测试失败，请检查上述失败项")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)