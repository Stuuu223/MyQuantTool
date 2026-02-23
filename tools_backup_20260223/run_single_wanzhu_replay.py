#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顽主票单票单日回测验证脚本
CTO指令：验证QMT历史数据泵 + UnifiedWarfareCore集成

目标：用真实历史Tick数据验证UnifiedWarfareCore是否能正确检测起爆点
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.strategies.unified_warfare_core import UnifiedWarfareCore


def test_single_stock_replay(stock_code: str, date: str):
    """
    测试单只股票的Tick回放
    
    Args:
        stock_code: 股票代码 (如 '000066.SZ')
        date: 日期 (格式: '2026-01-29')
    """
    print(f"🔍 开始测试: {stock_code} @ {date}")
    
    # 确保股票代码格式正确
    if '.' not in stock_code:
        if stock_code.startswith('00') or stock_code.startswith('30'):
            stock_code = f"{stock_code}.SZ"
        elif stock_code.startswith('60') or stock_code.startswith('68'):
            stock_code = f"{stock_code}.SH"
    
    # 创建历史数据提供者
    start_time = f"{date.replace('-', '')}093000"
    end_time = f"{date.replace('-', '')}150000"
    
    print(f"📊 加载历史Tick数据...")
    provider = QMTHistoricalProvider(
        stock_code=stock_code,
        start_time=start_time,
        end_time=end_time,
        period='tick'
    )
    
    # 获取Tick数据
    ticks = []
    for i, tick in enumerate(provider.iter_ticks()):
        ticks.append(tick)
        if i % 1000 == 0:  # 每1000个tick打印一次进度
            print(f"   已加载 {i} 个tick...")
        
        # 限制加载数量以加快测试
        if i >= 10000:  # 限制为最多10000个tick，够用
            break
    
    print(f"✅ 共加载 {len(ticks)} 个tick")
    
    if len(ticks) == 0:
        print(f"❌ 无tick数据，无法测试")
        return
    
    # 创建统一战法核心
    print(f"⚔️ 初始化UnifiedWarfareCore...")
    warfare_core = UnifiedWarfareCore()
    
    # 逐个tick回放测试
    print(f"🔄 开始Tick回放测试...")
    event_count = 0
    
    for i, tick in enumerate(ticks):
        # 构建上下文
        context = {
            'stock_code': stock_code,
            'date': date,
            'tick_index': i,
            'total_ticks': len(ticks)
        }
        
        # 处理tick
        events = warfare_core.process_tick(tick, context)
        
        # 检查是否有事件触发
        for event in events:
            event_count += 1
            print(f"🎯 [{event['event_type']}] 触发! 时间: {tick.get('time', 'N/A')}, 价格: {tick.get('last_price', 0):.2f}, 置信度: {event['confidence']:.3f}")
    
    print(f"🏁 测试完成: 共检测到 {event_count} 个事件")


if __name__ == "__main__":
    print("="*60)
    print("顽主票单票单日回测验证脚本")
    print("CTO指令：验证历史数据泵 + UnifiedWarfareCore集成")
    print("="*60)
    
    # 使用中国长城(000066)作为测试样本
    test_single_stock_replay("000066", "2026-01-29")
    
    print("="*60)
    print("验证完成")
    print("="*60)