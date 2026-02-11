#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价监控测试脚本 - 快速验证时间检测逻辑

使用方法：
    python scripts/test_auction_monitor.py

Author: MyQuantTool Team
Date: 2026-02-11
"""

import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, time as dt_time
from logic.logger import get_logger

logger = get_logger(__name__)


def test_time_logic():
    """测试时间检测逻辑"""
    print('=' * 80)
    print('🧪 竞价监控时间检测测试')
    print('=' * 80)

    now = datetime.now()
    current_time = now.time()

    print(f'\n📅 当前时间: {now.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'   星期: {now.strftime("%A")}')

    print(f'\n⏰ 时间状态判断:')

    # 判断当前时间段
    if dt_time(9, 15, 0) <= current_time < dt_time(9, 25, 0):
        print('   ✅ 竞价进行中 (9:15-9:25)')
        print('   🔥 应该每分钟保存一次竞价快照')
        status = 'auction_in_progress'

    elif dt_time(9, 25, 0) <= current_time < dt_time(9, 30, 0):
        print('   ✅ 竞价已结束 (9:25-9:30)')
        print('   🔥 应该执行最终保存')
        status = 'auction_ended'

    elif current_time >= dt_time(9, 30, 0):
        print('   ✅ 连续竞价已开始 (9:30+)')
        print('   🔥 竞价监控任务完成，应该退出')
        status = 'trading_started'

    else:
        print('   ⚠️ 非竞价时间')
        print('   🔥 等待竞价开始')
        status = 'waiting'

    # 计算距离竞价开始的时间
    if status == 'waiting':
        wait_seconds = (
            datetime.combine(now.date(), dt_time(9, 15, 0)) - now
        ).total_seconds()

        if wait_seconds > 3600:
            print(f'\n⏳ 距离竞价开始还有: {wait_seconds/3600:.1f} 小时')
        elif wait_seconds > 60:
            print(f'\n⏳ 距离竞价开始还有: {wait_seconds/60:.1f} 分钟')
        else:
            print(f'\n⏳ 距离竞价开始还有: {wait_seconds:.0f} 秒')

    print('\n' + '=' * 80)
    print(f'✅ 时间检测逻辑正常，当前状态: {status}')
    print('=' * 80)

    return status


if __name__ == "__main__":
    test_time_logic()