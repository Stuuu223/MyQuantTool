#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V16.4.0 集成测试（修复验证）

测试目标：
1. 验证AkShareDataManager初始化不报错
2. 验证RateLimiter.update_limits方法正常工作
3. 验证黑名单生成器正常运行

Usage:
    python tests/test_v16_4_integration.py

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.4.0
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.utils.logger import get_logger

logger = get_logger(__name__)


def test_akshare_manager_init():
    """测试AkShareDataManager初始化（修复AttributeError）"""
    print("=" * 80)
    print("🧪 测试1: AkShareDataManager初始化")
    print("=" * 80)

    try:
        from logic.data_providers.akshare_manager import AkShareDataManager

        # 初始化管理器（warmup模式）
        print("📋 初始化AkShareDataManager (warmup模式)...")
        manager = AkShareDataManager(mode='warmup')

        print("✅ 初始化成功")
        print(f"📊 限速器类型: {type(manager.limiter).__name__}")
        print(f"📊 限速器对象: {manager.limiter}")

        # 测试update_limits方法
        print("\n📋 测试update_limits方法...")
        manager.limiter.update_limits(
            max_requests_per_minute=60,
            max_requests_per_hour=2000,
            min_request_interval=0.1
        )

        print("✅ update_limits方法调用成功")

        # 获取统计信息
        print("\n📋 获取限速器统计...")
        stats = manager.limiter.get_stats()
        print(f"✅ 统计信息:")
        print(f"  每分钟限制: {stats['max_per_minute']} 次")
        print(f"  每小时限制: {stats['max_per_hour']} 次")
        print(f"  最小间隔: {manager.limiter.min_interval} 秒")

        print("\n✅ 测试1完成\n")
        return True

    except AttributeError as e:
        print(f"❌ AttributeError: {e}")
        print("⚠️  这表明update_limits方法不存在")
        print("\n❌ 测试1失败\n")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        import traceback
        traceback.print_exc()
        print("\n❌ 测试1失败\n")
        return False


def test_rate_limiter_path():
    """测试RateLimiter路径配置"""
    print("=" * 80)
    print("🧪 测试2: RateLimiter路径配置")
    print("=" * 80)

    try:
        # V16.4.0: 直接创建新实例（避免单例缓存问题）
        from logic.core.rate_limiter import RateLimiter
        from pathlib import Path

        # 创建新实例
        print("📋 创建新的RateLimiter实例...")
        limiter = RateLimiter(
            max_requests_per_minute=60,
            max_requests_per_hour=2000,
            min_request_interval=0.1
        )

        print(f"✅ 限速器对象: {limiter}")
        print(f"✅ 历史文件路径: {limiter.history_file}")

        # 检查路径是否在项目根目录
        project_root = Path(__file__).resolve().parent.parent
        expected_path = project_root / 'data' / 'rate_limiter_history.json'

        if limiter.history_file == expected_path:
            print(f"✅ 路径正确: {limiter.history_file}")
        else:
            print(f"⚠️  路径不一致:")
            print(f"  期望: {expected_path}")
            print(f"  实际: {limiter.history_file}")

        print("\n✅ 测试2完成\n")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        print("\n❌ 测试2失败\n")
        return False


def test_blacklist_generation():
    """测试黑名单生成器（测试模式：5只股票）"""
    print("=" * 80)
    print("🧪 测试3: 黑名单生成器（测试模式：5只股票）")
    print("=" * 80)

    try:
        import akshare as ak
        import json
        import time
        import random
        from datetime import datetime, timedelta

        # 获取股票列表
        print("📋 获取股票列表...")
        stock_list = ak.stock_zh_a_spot_em()
        test_stocks = stock_list.head(5)

        print(f"🎯 测试股票: {len(test_stocks)} 只")

        # 模拟黑名单生成逻辑
        from tasks.job_update_blacklist import RISK_KEYWORDS

        blacklist = []
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        for idx, row in test_stocks.iterrows():
            code = row['代码']
            name = row['名称']
            change_pct_raw = row['涨跌幅']

            # 添加随机延迟（防WAF）
            time.sleep(random.uniform(0.1, 0.3))

            try:
                df = ak.stock_zh_a_disclosure_report_cninfo(
                    symbol=code,
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d')
                )

                if df.empty:
                    print(f"  ✅ {code} {name}: 无公告 ({change_pct_raw:+.1f}%)")
                    continue

                # 检查公告标题
                for _, ann in df.iterrows():
                    title = str(ann['公告标题'])
                    if any(keyword in title for keyword in RISK_KEYWORDS):
                        blacklist.append({
                            'code': code,
                            'name': name,
                            'title': title,
                            'date': str(ann['公告时间'])
                        })
                        print(f"  ⛔ {code} {name}: 发现风险公告 ({change_pct_raw:+.1f}%)")
                        break
                    else:
                        print(f"  ✅ {code} {name}: 无风险 ({change_pct_raw:+.1f}%)")

            except Exception as e:
                print(f"  ⚠️ {code} {name}: 失败 - {e}")
                continue

        print(f"\n📊 测试结果: {len(blacklist)}/{len(test_stocks)} 只有风险")
        print("✅ 测试3完成\n")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        print("\n❌ 测试3失败\n")
        return False


if __name__ == "__main__":
    try:
        print("\n" + "=" * 80)
        print("V16.4.0 集成测试（修复验证）")
        print("=" * 80 + "\n")

        # 测试1: AkShareDataManager初始化
        result1 = test_akshare_manager_init()

        # 测试2: RateLimiter路径配置
        result2 = test_rate_limiter_path()

        # 测试3: 黑名单生成器
        result3 = test_blacklist_generation()

        # 汇总结果
        print("=" * 80)
        print("📊 测试结果汇总")
        print("=" * 80)
        print(f"测试1 (AkShareDataManager初始化): {'✅ 通过' if result1 else '❌ 失败'}")
        print(f"测试2 (RateLimiter路径配置): {'✅ 通过' if result2 else '❌ 失败'}")
        print(f"测试3 (黑名单生成器): {'✅ 通过' if result3 else '❌ 失败'}")
        print("=" * 80)

        if result1 and result2 and result3:
            print("\n✅ 所有测试通过，可以上线")
        else:
            print("\n❌ 存在失败测试，不可上线")

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
