#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试事件记录器

测试内容：
1. 记录模拟事件
2. 更新后续数据
3. 导出为Excel/CSV
4. 统计分析

Author: iFlow CLI
Version: V2.0
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logic.event_recorder import get_event_recorder
from logic.event_detector import EventType, TradingEvent
from logic.logger import get_logger

logger = get_logger(__name__)


def test_event_recorder():
    """测试事件记录器"""
    print("\n" + "=" * 80)
    print("🧪 测试事件记录器")
    print("=" * 80)
    
    # 获取事件记录器
    recorder = get_event_recorder()
    
    # 创建模拟事件
    print("\n📋 创建模拟事件...")
    
    events = [
        TradingEvent(
            event_type=EventType.OPENING_WEAK_TO_STRONG,
            stock_code='000592.SZ',
            timestamp=datetime.now(),
            data={'gap_pct': 0.06, 'volume_ratio': 2.0},
            confidence=0.85,
            description='竞价弱转强：高开6.00%，量比2.00'
        ),
        TradingEvent(
            event_type=EventType.HALFWAY_BREAKOUT,
            stock_code='300502.SZ',
            timestamp=datetime.now(),
            data={'change_pct': 0.125, 'breakout_gain': 0.015},
            confidence=0.78,
            description='半路平台突破：涨幅12.50%，突破1.50%'
        ),
        TradingEvent(
            event_type=EventType.LEADER_CANDIDATE,
            stock_code='600519.SH',
            timestamp=datetime.now(),
            data={'change_pct': 0.075, 'sector_rank': 1},
            confidence=0.82,
            description='板块龙头候选：涨幅7.50%，板块排名第1'
        ),
        TradingEvent(
            event_type=EventType.DIP_BUY_CANDIDATE,
            stock_code='000001.SZ',
            timestamp=datetime.now(),
            data={'dip_pct': 0.015, 'volume_ratio': 0.7},
            confidence=0.89,
            description='5日均线低吸：回踩1.50%，缩量70.0%'
        )
    ]
    
    # 模拟Tick数据
    tick_data_list = [
        {'close': 10.00, 'open': 10.60, 'now': 10.60},
        {'close': 20.00, 'open': 22.00, 'now': 22.50},
        {'close': 50.00, 'open': 53.00, 'now': 53.75},
        {'close': 15.00, 'open': 14.50, 'now': 14.78}
    ]
    
    # 记录事件
    record_ids = []
    for event, tick_data in zip(events, tick_data_list):
        try:
            record_id = recorder.record_event(event, tick_data)
            record_ids.append(record_id)
            print(f"✅ 记录事件: {event.stock_code} - {event.description} (ID: {record_id})")
        except Exception as e:
            print(f"❌ 记录失败: {e}")
    
    # 模拟更新后续数据
    print("\n📋 模拟更新后续数据...")
    
    # 更新收盘价
    for i, record_id in enumerate(record_ids):
        day_close = tick_data_list[i]['now'] * (1 + 0.02 if i % 2 == 0 else 1 - 0.01)
        recorder.update_day_close(record_id, day_close)
    
    # 更新次日开盘
    for i, record_id in enumerate(record_ids):
        next_day_open = tick_data_list[i]['now'] * (1 + 0.03 if i % 2 == 0 else 1 + 0.01)
        recorder.update_next_day_open(record_id, next_day_open)
    
    # 更新3天表现
    for i, record_id in enumerate(record_ids):
        max_gain = 0.15 if i % 2 == 0 else 0.08
        max_loss = -0.03 if i % 2 == 0 else -0.05
        is_profitable = i % 2 == 0
        profit_amount = 15000 if i % 2 == 0 else -5000
        recorder.update_3days_performance(record_id, max_gain, max_loss, is_profitable, profit_amount)
    
    # 显示统计信息
    print("\n📊 统计信息:")
    recorder.print_statistics()
    
    # 导出为CSV
    print("\n📋 导出为CSV...")
    recorder.export_to_csv("data/test_event_records.csv")
    
    # 导出为Excel
    print("\n📋 导出为Excel...")
    try:
        recorder.export_to_excel("data/test_event_records.xlsx")
    except Exception as e:
        print(f"⚠️  Excel导出失败（需要pandas和openpyxl）: {e}")
    
    # 查询记录
    print("\n📋 查询记录:")
    records = recorder.get_records(limit=5)
    
    if records:
        print(f"\n找到 {len(records)} 条记录:")
        for record in records:
            print(f"   {record.event_time[:19]} - {record.stock_code} - {record.description}")
    else:
        print("   未找到记录")
    
    print("\n" + "=" * 80)
    print("✅ 事件记录器测试完成")
    print("=" * 80)
    print("\n生成的文件:")
    print("   - data/event_records.db (数据库)")
    print("   - data/test_event_records.csv (CSV表格)")
    print("   - data/test_event_records.xlsx (Excel表格，如果安装了pandas)")
    print("=" * 80 + "\n")
    
    # 关闭数据库连接
    recorder.close()


if __name__ == "__main__":
    test_event_recorder()