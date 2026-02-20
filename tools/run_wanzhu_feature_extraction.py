#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顽主票特征提取验证脚本
CTO指令：验证数据格式转换 + 资金流估算 + 特征提取

目标：确保历史数据能正确触发UnifiedWarfareCore并提取关键特征
"""

import sys
import os
import pandas as pd
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.strategies.unified_warfare_core import UnifiedWarfareCore


def estimate_flow_from_tick(tick_data):
    """
    从Tick数据估算资金流特征
    基于内外盘和成交额估算主力资金
    """
    # 基于价格和成交量估算主动性买卖
    if 'lastPrice' not in tick_data or 'volume' not in tick_data:
        return {
            'main_net_inflow': 0,
            'buy_volume': 0,
            'sell_volume': 0,
            'volume_ratio': 0,
            'current_ratio': 0
        }
    
    price = tick_data.get('lastPrice', 0)
    volume = tick_data.get('volume', 0)
    amount = tick_data.get('amount', 0)
    
    # 简化估算：基于价格相对于开盘/昨收的位置判断主动性
    open_price = tick_data.get('open', price)
    high_price = tick_data.get('high', price)
    low_price = tick_data.get('low', price)
    
    # 估算主动性买卖量（简化算法）
    if high_price != low_price:
        price_position = (price - low_price) / (high_price - low_price) if high_price != low_price else 0.5
        buy_volume = int(volume * price_position) if price_position > 0.5 else 0
        sell_volume = int(volume * (1 - price_position)) if price_position < 0.5 else 0
    else:
        buy_volume = sell_volume = volume // 2
    
    # 计算资金流入流出（简化）
    buy_amount = buy_volume * price
    sell_amount = sell_volume * price
    main_net_inflow = buy_amount - sell_amount
    
    # 估算比例
    total_amount = amount if amount > 0 else (buy_amount + sell_amount)
    current_ratio = (main_net_inflow / total_amount) if total_amount != 0 else 0
    
    return {
        'main_net_inflow': main_net_inflow,
        'buy_volume': buy_volume,
        'sell_volume': sell_volume,
        'volume_ratio': buy_volume / sell_volume if sell_volume > 0 else float('inf'),
        'current_ratio': current_ratio
    }


def test_feature_extraction(stock_code: str, date: str):
    """
    测试特征提取
    
    Args:
        stock_code: 股票代码 (如 '000066')
        date: 日期 (格式: '2026-01-29')
    """
    # 格式化股票代码
    if '.' not in stock_code:
        code = str(stock_code).zfill(6)
        if code.startswith(('00', '30')):
            stock_code = f"{code}.SZ"
        elif code.startswith(('60', '688', '689')):
            stock_code = f"{code}.SH"
        else:
            stock_code = f"{code}.SZ"  # 默认深圳
    
    print(f"🔍 特征提取测试: {stock_code} @ {date}")
    
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
    
    # 创建统一战法核心
    print(f"⚔️ 初始化UnifiedWarfareCore...")
    warfare_core = UnifiedWarfareCore()
    
    # 逐个tick处理并提取特征
    print(f"🔄 开始特征提取...")
    event_count = 0
    features_list = []
    
    for i, tick in enumerate(provider.iter_ticks()):
        # 估算资金流特征
        flow_features = estimate_flow_from_tick(tick)
        
        # 构建上下文，包含资金流信息
        context = {
            'stock_code': stock_code,
            'date': date,
            'tick_index': i,
            'main_net_inflow': flow_features['main_net_inflow'],
            'current_ratio': flow_features['current_ratio'],
            'volume_ratio': flow_features['volume_ratio'],
            'buy_volume': flow_features['buy_volume'],
            'sell_volume': flow_features['sell_volume']
        }
        
        # 处理tick
        events = warfare_core.process_tick(tick, context)
        
        # 检查是否有事件触发并提取特征
        for event in events:
            event_count += 1
            feature_snapshot = {
                'timestamp': tick.get('time', 'N/A'),
                'stock_code': stock_code,
                'event_type': event['event_type'],
                'confidence': event['confidence'],
                'price': tick.get('lastPrice', 0),
                'volume': tick.get('volume', 0),
                'amount': tick.get('amount', 0),
                # 资金流特征
                'main_net_inflow': flow_features['main_net_inflow'],
                'current_ratio': flow_features['current_ratio'],
                'volume_ratio': flow_features['volume_ratio'],
                'buy_volume': flow_features['buy_volume'],
                'sell_volume': flow_features['sell_volume'],
                # 价格特征
                'breakout_strength': event['data'].get('breakout_strength', 0) if 'breakout_strength' in event.get('data', {}) else 0,
                'volume_surge': event['data'].get('volume_surge', 0) if 'volume_surge' in event.get('data', {}) else 0,
                'price_position': event['data'].get('price_position', 0) if 'price_position' in event.get('data', {}) else 0,
                # 其他事件数据
                'event_description': event['description'],
                'event_data': event.get('data', {})
            }
            
            features_list.append(feature_snapshot)
            
            print(f"🎯 [{event['event_type']}] 触发!")
            print(f"   时间: {tick.get('time', 'N/A')}")
            print(f"   价格: {tick.get('lastPrice', 0):.2f}")
            print(f"   置信度: {event['confidence']:.3f}")
            print(f"   资金流入: {flow_features['main_net_inflow']:.0f}")
            print(f"   资金比例: {flow_features['current_ratio']:.3f}")
            print(f"   量比: {flow_features['volume_ratio']:.2f}")
            print(f"   突破强度: {feature_snapshot['breakout_strength']:.3f}")
            print(f"   量能放大: {feature_snapshot['volume_surge']:.3f}")
            print("-" * 60)
    
    print(f"✅ 特征提取完成: 共检测到 {event_count} 个事件")
    
    # 保存特征到CSV
    if features_list:
        df = pd.DataFrame(features_list)
        output_file = f"feature_snapshots_{stock_code.replace('.', '_')}_{date.replace('-', '')}.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"💾 特征数据已保存至: {output_file}")
        print(f"📊 特征列: {list(df.columns)}")
    else:
        print("⚠️ 未检测到任何事件，无特征数据保存")
    
    return features_list


def main():
    print("="*80)
    print("顽主票特征提取验证脚本")
    print("CTO指令：验证数据格式转换 + 资金流估算 + 特征提取")
    print("="*80)
    
    # 使用中国长城(000066)或欢乐家(300997)进行测试
    stock_code = "000066"  # 使用已确认有历史数据的股票
    date = "2026-01-29"    # 使用历史日期
    
    print(f"🎯 测试股票: {stock_code}")
    print(f"📅 测试日期: {date}")
    
    features = test_feature_extraction(stock_code, date)
    
    print("\n" + "="*80)
    print("特征提取验证完成")
    if features:
        print(f"提取了 {len(features)} 个事件的完整特征")
        print("特征包括: 资金流、量价关系、突破强度等")
    else:
        print("未检测到任何事件")
    print("="*80)


if __name__ == "__main__":
    main()
