#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据收割机性能测试脚本
测试 DataHarvester 的性能和正确性

Author: iFlow CLI
Version: V19.13
"""

import time
import sys
from logic.data_harvester import get_data_harvester
from logic.logger import get_logger

logger = get_logger(__name__)


def test_database_init():
    """测试数据库初始化"""
    print("=" * 60)
    print("🔍 测试1: 数据库初始化")
    print("=" * 60)

    try:
        harvester = get_data_harvester()
        print("✅ 数据库初始化成功")

        # 检查数据库文件是否存在
        import os
        if os.path.exists(harvester.db_path):
            print(f"✅ 数据库文件存在: {harvester.db_path}")
        else:
            print(f"❌ 数据库文件不存在: {harvester.db_path}")
            return False

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_stats():
    """测试数据库统计"""
    print("\n" + "=" * 60)
    print("🔍 测试2: 数据库统计")
    print("=" * 60)

    try:
        harvester = get_data_harvester()
        stats = harvester.get_database_stats()

        print(f"✅ 股票数量: {stats['stock_count']}")
        print(f"✅ 数据总量: {stats['total_records']}")
        print(f"✅ 最新日期: {stats['latest_date']}")
        print(f"✅ 最早日期: {stats['earliest_date']}")
        print(f"✅ 数据库大小: {stats['db_size_mb']} MB")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_stock_harvest():
    """测试单只股票收割"""
    print("\n" + "=" * 60)
    print("🔍 测试3: 单只股票收割")
    print("=" * 60)

    try:
        harvester = get_data_harvester()

        # 测试股票：贵州茅台
        test_code = "600519"

        print(f"📥 开始收割 {test_code} 的数据...")
        start_time = time.time()

        result = harvester.harvest_stock(test_code, days=60)

        elapsed = time.time() - start_time

        if result:
            print(f"✅ 收割成功！耗时: {elapsed:.2f}秒")

            # 检查数据是否真的存入数据库
            df = harvester.get_stock_data(test_code, days=60)
            if df is not None:
                print(f"✅ 数据验证成功，共 {len(df)} 条记录")
                print(f"📊 数据样本:")
                print(df.tail())
            else:
                print(f"❌ 数据验证失败，无法从数据库读取")
                return False
        else:
            print(f"❌ 收割失败")
            return False

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_incremental_update():
    """测试增量更新"""
    print("\n" + "=" * 60)
    print("🔍 测试4: 增量更新")
    print("=" * 60)

    try:
        harvester = get_data_harvester()

        # 测试股票：宁德时代
        test_code = "300750"

        print(f"📥 第一次收割 {test_code} 的数据...")
        result1 = harvester.harvest_stock(test_code, days=60)

        if result1:
            print(f"✅ 第一次收割成功")

            # 立即再次收割（应该跳过，因为数据已经是新的）
            print(f"📥 第二次收割 {test_code} 的数据（增量更新）...")
            start_time = time.time()

            result2 = harvester.harvest_stock(test_code, days=60)

            elapsed = time.time() - start_time

            if result2:
                print(f"✅ 第二次收割成功！耗时: {elapsed:.2f}秒")
                print(f"💡 增量更新应该很快（因为数据已是最新）")
            else:
                print(f"❌ 第二次收割失败")
                return False
        else:
            print(f"❌ 第一次收割失败")
            return False

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_small_batch_harvest():
    """测试小批量收割（5只股票）"""
    print("\n" + "=" * 60)
    print("🔍 测试5: 小批量收割（5只股票）")
    print("=" * 60)

    try:
        harvester = get_data_harvester()

        print(f"🚜 开始收割 5 只活跃股...")
        start_time = time.time()

        result = harvester.harvest_active_stocks(
            limit=5,
            days=60,
            force_update=False,
            delay=0.5
        )

        elapsed = time.time() - start_time

        print(f"✅ 收割完成！")
        print(f"📊 统计结果:")
        print(f"   总数: {result['total']}")
        print(f"   成功: {result['success']}")
        print(f"   失败: {result['failed']}")
        print(f"   跳过: {result['skipped']}")
        print(f"⏱️ 总耗时: {elapsed:.2f}秒")
        print(f"⚡ 平均每只: {elapsed/result['total']:.2f}秒")

        # 显示详情
        print(f"\n📋 详细结果:")
        for detail in result['details']:
            status_icon = "✅" if detail['status'] == 'success' else "❌"
            print(f"   {status_icon} {detail['code']} {detail['name']}: {detail['message']}")

        return result['success'] > 0

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n🚀 数据收割机性能测试开始\n")

    results = []

    # 测试1: 数据库初始化
    results.append(("数据库初始化", test_database_init()))

    # 测试2: 数据库统计
    results.append(("数据库统计", test_database_stats()))

    # 测试3: 单只股票收割
    results.append(("单只股票收割", test_single_stock_harvest()))

    # 测试4: 增量更新
    results.append(("增量更新", test_incremental_update()))

    # 测试5: 小批量收割
    results.append(("小批量收割", test_small_batch_harvest()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！数据收割机功能正常。")
    else:
        print("❌ 部分测试失败，请检查上述错误。")
    print("=" * 60 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
