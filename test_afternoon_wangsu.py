#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网宿科技（300017）2026-01-26 14:19 起爆点验证脚本
专门测试下午14:19附近的起爆特征
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


def estimate_flow_from_tick(tick, last_tick):
    """极简版资金流估算：用内外盘差值估算主买主卖差额"""
    if not last_tick:
        return 0
    price_diff = tick['lastPrice'] - last_tick['lastPrice']
    volume_diff = tick['volume'] - last_tick['volume']
    
    # 价格上涨，这笔算主买流入；价格下跌，算主卖流出
    if price_diff > 0:
        return volume_diff * tick['lastPrice'] * 100 # 大致流入金额
    elif price_diff < 0:
        return -volume_diff * tick['lastPrice'] * 100
    return 0


def analyze_wangsu_afternoon():
    """
    专门分析网宿科技下午时段
    """
    print("="*80)
    print("网宿科技（300017）2026-01-26 下午起爆点验证")
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
    
    # 存储last_tick用于计算资金流
    last_tick = None
    accumulated_net_inflow = 0
    event_count = 0
    
    print(f"🔄 开始特征提取与分析...")
    print("开始遍历 Tick 数据，重点关注下午13:30-14:30时段...")
    
    tick_counter = 0
    for tick in provider.iter_ticks():
        tick_counter += 1
        
        # 获取时间
        time_str = tick['time']
        readable_time = datetime.fromtimestamp(int(time_str) / 1000).strftime('%H:%M:%S')
        
        # 只关注下午时段
        if '13:30' <= readable_time <= '14:30':
            # 估算累积净流入
            net_flow = estimate_flow_from_tick(tick, last_tick)
            accumulated_net_inflow += net_flow
            
            # 组装 Context
            context = {
                'stock_code': formatted_code,
                'date': date,
                'main_net_inflow': accumulated_net_inflow,
            }

            # 送入实盘战法核心引擎
            events = warfare_core.process_tick(tick, context)

            if events:
                for event in events:
                    event_count += 1
                    print(f"🎯 [触发时刻: {readable_time}] 事件: {event['event_type']}")
                    print(f"    当前价格: {tick['lastPrice']:.2f}")
                    print(f"    当前总成交量: {tick['volume']:.0f}")
                    print(f"    估算净流入: {accumulated_net_inflow / 10000:.2f} 万元")
                    
                    if 'data' in event:
                        print(f"    量能放大倍数: {event['data'].get('volume_surge', 'N/A')}")
                        print(f"    突破强度: {event['data'].get('breakout_strength', 'N/A')}")
                    print(f"    置信度: {event['confidence']:.3f}")
                    print(f"    描述: {event.get('description', 'N/A')}")
                    print("-" * 60)
        
        last_tick = tick
        
        # 每100个tick输出一次进度
        if tick_counter % 100 == 0 and '13:30' <= readable_time <= '14:30':
            print(f"📈 [{readable_time}] 当前价格: {tick['lastPrice']:.2f}, 成交量: {tick['volume']:.0f}")

    print(f"✅ 下午时段分析完成: 总共处理 {tick_counter} 个tick，检测到 {event_count} 个事件")
    
    if event_count == 0:
        print("❌ 下午时段未触发任何事件。")
        # 尝试更详细的分析
        print("\n🔍 重新分析，包含更多调试信息...")
        # 重新遍历，但只看14:15-14:25时段
        for tick in provider.iter_ticks():
            time_str = tick['time']
            readable_time = datetime.fromtimestamp(int(time_str) / 1000).strftime('%H:%M:%S')
            if '14:15' <= readable_time <= '14:25':
                print(f"📊 [{readable_time}] 价格: {tick['lastPrice']:.2f}, 量: {tick['volume']:.0f}, 五档买: {tick['bidPrice'][:2]}, 五档卖: {tick['askPrice'][:2]}")
    
    print("="*80)
    print("网宿科技下午时段分析完成")
    print("="*80)


def main():
    analyze_wangsu_afternoon()


if __name__ == "__main__":
    main()
