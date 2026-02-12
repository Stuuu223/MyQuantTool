#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价快照系统监控脚本

功能：
1. 检查当前时间和竞价状态
2. 检查Redis中的竞价数据
3. 验证竞价数据的完整性

Author: MyQuantTool Team
Date: 2026-02-11
"""

import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from logic.database_manager import DatabaseManager
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def check_time_status():
    """检查当前时间和竞价状态"""
    print('=' * 80)
    print('🧪 项目总监监控 - 竞价快照系统')
    print('=' * 80)

    # 显示当前时间
    now = datetime.now()
    print(f'\n📅 当前时间: {now.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'   星期: {now.strftime("%A")}')

    # 检查是否在竞价时间
    current_hour = now.hour
    current_minute = now.minute

    print(f'\n⏰ 市场时间判断:')
    if 9 <= current_hour < 15:
        print('   ✅ 交易时间段')
        if 9 <= current_hour < 10:
            print('   🎯 竞价时间段 (9:15-9:25)')
            if current_hour == 9 and current_minute < 25:
                print('   🔥 当前在竞价时间内，应该有竞价数据')
            elif current_hour == 9 and 25 <= current_minute < 30:
                print('   🔥 竞价已结束，连续竞价即将开始')
            else:
                print('   ⚠️ 竞价时间已过')
        else:
            print('   ⚠️ 竞价时间已过')
    else:
        print('   ⚠️ 非交易时间')


def check_redis_auction_data():
    """检查Redis中的竞价数据"""
    print(f'\n📊 Redis竞价数据检查:')

    try:
        db_manager = DatabaseManager()
        db_manager._init_redis()

        today = datetime.now().strftime("%Y%m%d")
        pattern = f"auction:{today}:*"

        # 获取所有竞价快照键
        keys = db_manager._redis_client.keys(pattern)

        if not keys:
            print(f'   ❌ Redis中没有找到今日竞价快照数据')
            print(f'   🔑 查询模式: {pattern}')
            return False
        else:
            print(f'   ✅ 找到 {len(keys)} 条竞价快照记录')

            # 随机抽样检查几条数据
            sample_size = min(3, len(keys))
            import random
            sample_keys = random.sample(keys, sample_size)

            print(f'\n   📋 抽样检查 ({sample_size}条):')
            for key in sample_keys:
                stock_code = key.decode('utf-8').split(':')[-1]
                raw_data = db_manager._redis_client.get(key)

                if raw_data:
                    import json
                    try:
                        data = json.loads(raw_data)
                        volume = data.get('auction_volume', 0)
                        amount = data.get('auction_amount', 0)
                        last_price = data.get('last_price', 0)
                        timestamp = data.get('timestamp', 0)

                        print(f'      ✅ {stock_code}: 成交量={volume}, 成交额={amount:.0f}, 价格={last_price:.2f}')
                    except Exception as e:
                        print(f'      ❌ {stock_code}: 数据解析失败 - {e}')
                else:
                    print(f'      ❌ {stock_code}: 数据为空')

            return True

    except Exception as e:
        print(f'   ❌ Redis连接失败: {e}')
        return False


def check_auction_daemon_status():
    """检查竞价快照守护进程状态"""
    print(f'\n🔧 竞价快照守护进程检查:')

    # 检查定时任务是否已创建
    import subprocess

    try:
        # Windows任务计划程序
        result = subprocess.run(
            ['schtasks', '/query', '/tn', 'MyQuantTool_AuctionSnapshot'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print('   ✅ Windows计划任务已创建')
            print('   📋 任务名称: MyQuantTool_AuctionSnapshot')
            print('   ⏰ 执行时间: 每天上午9:15')
        else:
            print('   ⚠️ Windows计划任务未创建')
            print('   💡 请手动创建计划任务或运行: scripts/schedule_auction_daemon.bat')

    except Exception as e:
        print(f'   ⚠️ 无法检查计划任务状态: {e}')


def main():
    """主函数"""
    # 检查时间状态
    check_time_status()

    # 检查Redis数据
    check_redis_auction_data()

    # 检查守护进程
    check_auction_daemon_status()

    print('\n' + '=' * 80)
    print('✅ 监控检查完成')
    print('=' * 80)


if __name__ == "__main__":
    main()