#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V14路径修复验证 - 000547信号测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("V14路径修复验证 - 000547信号测试")
print("=" * 60)

# 1. 测试数据读取
print("\n【Step 1】测试数据读取...")
from logic.qmt_historical_provider import QMTHistoricalProvider

provider = QMTHistoricalProvider(
    stock_code='000547.SZ',
    start_time='20260204000000',
    end_time='20260204150000',
    period='tick'
)

tick_df = provider.get_raw_ticks()
print(f"Tick数据行数: {len(tick_df)}")

if len(tick_df) > 0:
    print(f"列名: {list(tick_df.columns)}")
    print(f"前3行:\n{tick_df.head(3)}")
    
    # 数据诊断
    valid_prices = tick_df[tick_df['lastPrice'] > 0]
    print(f"\n有效价格数据: {len(valid_prices)}/{len(tick_df)}")
    if len(valid_prices) > 0:
        print(f"价格范围: {valid_prices['lastPrice'].min():.2f} - {valid_prices['lastPrice'].max():.2f}")
        print(f"成交量范围: {valid_prices['volume'].min():.0f} - {valid_prices['volume'].max():.0f}")
        print(f"成交额范围: {valid_prices['amount'].min():.0f} - {valid_prices['amount'].max():.0f}")
    
    # 2. 测试信号生成
    print("\n【Step 2】测试信号生成...")
    from logic.strategies.halfway_breakout_detector import HalfwayBreakoutDetector
    from logic.rolling_metrics import RollingFlowCalculator
    
    # 初始化检测器
    detector = HalfwayBreakoutDetector()
    calc = RollingFlowCalculator()
    
    # ✅ 使用CTO定下的标准阈值（严禁修改）
    print(f"⚙️ 标准阈值: ratio_stock>=15, intensity>={detector.MIN_INTENSITY_SCORE}")
    
    # 设置昨收价
    if len(tick_df) > 0:
        pre_close = tick_df['lastPrice'].iloc[0] * 0.98
        calc.set_pre_close(pre_close)
    
    events = []
    tick_count = 0
    last_tick = None
    
    # 获取有效的昨收价 - 找第一个有效价格作为参考
    pre_close = None
    for _, row in tick_df.iterrows():
        if row['lastPrice'] > 0:
            pre_close = row['lastPrice'] * 0.98  # 估算昨收
            print(f"估算昨收价: {pre_close:.2f} (基于首笔有效价格 {row['lastPrice']:.2f})")
            break
    
    if pre_close is None:
        pre_close = 10.0  # 默认值
        print(f"无法估算昨收价，使用默认值: {pre_close}")
    
    calc.set_pre_close(pre_close)
    
    for _, tick in tick_df.iterrows():
        tick_dict = tick.to_dict()
        # 确保有pre_close和stock_code
        tick_dict['pre_close'] = pre_close
        tick_dict['stock_code'] = '000547.SZ'
        current_price = tick_dict.get('lastPrice', 0)
        
        # 添加到计算器
        metrics = calc.add_tick(tick_dict, last_tick)
        
        # 手动设置current_price用于ratio计算
        calc.current_price = current_price
        
        # 构建context
        context = {
            'metrics': metrics,
            'calc': calc,
            'stock_code': '000547.SZ',
            'pre_close': pre_close,
            'last_tick': last_tick
        }
        
        # 每100个tick打印一次ratio值
        if tick_count % 500 == 0 and tick_count > 0:
            try:
                ratios = calc.get_flow_ratios('000547.SZ')
                print(f"  Tick {tick_count}: ratio_stock={ratios['ratio_stock']:.2f}, sustain={ratios['sustain']:.2f}, response_eff={ratios['response_eff']:.4f}")
                print(f"    flow_5min={metrics.flow_5min.total_flow:.0f}, flow_15min={metrics.flow_15min.total_flow:.0f}")
            except Exception as e:
                print(f"  Tick {tick_count}: ratio计算失败: {e}")
        
        # 检测信号
        result = detector.detect(tick_dict, context)
        if result:
            events.append(result)
            print(f"  ✅ 检测到信号: {result.get('event_type')} @ tick {tick_count}")
        elif tick_count < 20:
            # 打印前20个tick的检测结果（调试用）
            print(f"  [DEBUG] Tick {tick_count}: 无信号")
        
        tick_count += 1
        last_tick = tick_dict
    
    print(f"\n处理Tick数: {tick_count}")
    print(f"检测事件数: {len(events)}")
    
    if events:
        print("\n事件详情:")
        for i, event in enumerate(events[:5]):
            print(f"  事件{i+1}: time={event.get('time')}, type={event.get('event_type')}, intensity={event.get('intensity_score', 0):.2f}")
    
    # 最终结果
    print("\n" + "=" * 60)
    if len(events) >= 2:
        print(f"✅ V14验证成功: 信号数={len(events)} >= 2")
    else:
        print(f"❌ V14验证失败: 信号数={len(events)} < 2")
    print("=" * 60)
else:
    print("❌ 无法读取Tick数据")
