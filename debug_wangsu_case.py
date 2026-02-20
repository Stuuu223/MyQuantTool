#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网宿科技（300017）2026-01-26 关键时段突破测试
专门测试14:19左右的起爆点检测
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.strategies.unified_warfare_core import UnifiedWarfareCore


def analyze_wangsu_key_time():
    """
    分析网宿科技关键时段
    """
    print("="*80)
    print("网宿科技（300017）2026-01-26 关键时段突破测试")
    print("="*80)
    
    # 网宿科技是创业板，必定是 .SZ
    formatted_code = "300017.SZ"
    date = "2026-01-26"
    
    # 创建历史数据提供者
    start_time = f"{date.replace('-', '')}093000"
    end_time = f"{date.replace('-', '')}150000"
    
    print(f"📊 加载历史Tick数据...")
    provider = QMTHistoricalProvider(
        stock_code=formatted_code,
        start_time=start_time,
        end_time=end_time,
        period='tick'
    )
    
    # 创建统一战法核心
    print(f"⚔️ 初始化UnifiedWarfareCore...")
    warfare_core = UnifiedWarfareCore()
    
    # 简单测试，专门看14:18:50到14:20:00之间的tick
    print("🔍 重点关注14:18:50到14:20:00之间的数据...")
    event_count = 0
    
    for tick in provider.iter_ticks():
        time_str = tick['time']
        readable_time = datetime.fromtimestamp(int(time_str) / 1000).strftime('%H:%M:%S')
        
        # 重点关注14:18:50到14:20:00之间的tick
        if '14:18:50' <= readable_time <= '14:20:00':
            print(f'[{readable_time}] 价格: {tick["lastPrice"]:.2f}, 成交量: {tick["volume"]:.0f}, 五档买: {tick["bidPrice"][:2]}, 五档卖: {tick["askPrice"][:2]}')
            
            # 送入战法核心测试
            context = {
                'stock_code': formatted_code,
                'date': date,
                'main_net_inflow': 0,  # 暂时设置为0
            }
            
            events = warfare_core.process_tick(tick, context)
            if events:
                for event in events:
                    event_count += 1
                    print(f'  🎯 检测到事件: {event["event_type"]}, 置信度: {event["confidence"]:.3f}')
                    if 'data' in event:
                        print(f'    数据: {event["data"]}')
    
    print(f"✅ 关键时段分析完成，共检测到 {event_count} 个事件")
    print("="*80)


def main():
    analyze_wangsu_key_time()


if __name__ == "__main__":
    main()