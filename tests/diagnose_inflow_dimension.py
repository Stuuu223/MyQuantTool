# -*- coding: utf-8 -*-
"""
深度诊断：inflow_ratio量纲问题
目标：走真实入口，断点验证量纲

问题现象：
- 大屏显示 INFLOW% = 742.96%
- 但诊断脚本显示 inflow = 7.43%

诊断步骤：
1. 直接从QMT获取float_volume原始值
2. 从TrueDictionary获取float_volume
3. 对比两者单位
4. 验证引擎计算过程
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from xtquant import xtdata
from logic.data_providers.true_dictionary import get_true_dictionary
from logic.strategies.kinetic_core_engine import 动能打分引擎CoreEngine

def diagnose_inflow_dimension():
    """深度诊断inflow_ratio量纲"""
    print("=" * 70)
    print("[深度诊断] inflow_ratio量纲问题")
    print("=" * 70)
    
    # 1. 连接QMT
    print("\n[Step 1] 连接QMT...")
    xtdata.enable_hello = False
    print("[OK] QMT连接成功")
    
    # 2. 测试股票（从大屏TOP10选取）
    test_stocks = ['001696.SZ', '000862.SZ', '000545.SZ', '600545.SH', '002470.SZ']
    print(f"\n[Step 2] 测试股票: {test_stocks}")
    
    # 3. 获取TrueDictionary并预热
    print("\n[Step 3] 获取TrueDictionary...")
    true_dict = get_true_dictionary()
    print(f"[OK] TrueDictionary股票数: {len(true_dict._float_volume)}")
    
    # 预热
    print("\n[Step 3.5] 预热TrueDictionary...")
    from logic.utils.calendar_utils import get_nth_previous_trading_day
    today = datetime.now().strftime('%Y%m%d')
    target_date = get_nth_previous_trading_day(today, 1)
    result = true_dict.warmup(test_stocks, target_date=target_date)
    print(f"[OK] 预热完成: 涨停价{result['qmt'].get('success', 0)}只")
    print(f"[OK] TrueDictionary股票数(预热后): {len(true_dict._float_volume)}")
    
    # 4. 获取Tick数据
    print("\n[Step 4] 获取Tick数据...")
    now = datetime.now()
    print(f"当前时间: {now.strftime('%H:%M:%S')}")
    
    # 5. 创建引擎
    core_engine = 动能打分引擎CoreEngine()
    
    # 6. 对每只股票深度诊断
    for stock in test_stocks:
        print(f"\n{'='*70}")
        print(f"[深度诊断] {stock}")
        print("=" * 70)
        
        # 6.1 获取Tick
        try:
            tick = xtdata.get_full_tick([stock])
            if not tick or stock not in tick:
                print(f"  [SKIP] 无Tick数据")
                continue
            tick = tick[stock]
        except Exception as e:
            print(f"  [SKIP] Tick获取失败: {e}")
            continue
        
        # 6.2 提取基础数据
        current_price = tick.get('lastPrice', 0)
        current_volume = tick.get('volume', 0)  # 手
        current_amount = tick.get('amount', 0)  # 元
        pre_close = tick.get('lastClose', 0)
        tick_high = tick.get('high', current_price)
        tick_low = tick.get('low', current_price)
        
        print(f"\n[基础数据]")
        print(f"  current_price: {current_price}")
        print(f"  current_volume: {current_volume} 手")
        print(f"  current_amount: {current_amount} 元")
        print(f"  pre_close: {pre_close}")
        print(f"  tick_high: {tick_high}, tick_low: {tick_low}")
        
        # 6.3 从TrueDictionary获取float_volume
        float_volume_td = true_dict.get_float_volume(stock)
        print(f"\n[TrueDictionary]")
        print(f"  float_volume: {float_volume_td}")
        print(f"  单位判断: {'万股' if float_volume_td < 10000000 else '股'}")
        
        # 6.4 直接从QMT获取float_volume
        print(f"\n[QMT原始数据]")
        try:
            detail = xtdata.get_instrument_detail(stock)
            if detail:
                qmt_float_volume = detail.get('FloatVolume', 0)
                print(f"  QMT FloatVolume: {qmt_float_volume}")
                print(f"  对比: TD={float_volume_td}, QMT={qmt_float_volume}")
                print(f"  比例: TD/QMT = {float_volume_td / qmt_float_volume if qmt_float_volume else 'N/A'}")
            else:
                print(f"  [WARN] 无法获取QMT instrument_detail")
        except Exception as e:
            print(f"  [ERR] QMT获取失败: {e}")
        
        # 6.5 应用量纲修复
        float_volume_fixed = float_volume_td
        if float_volume_td and float_volume_td < 10000000:
            float_volume_fixed = float_volume_td * 10000
            print(f"\n[量纲修复] {float_volume_td} -> {float_volume_fixed} (放大10000倍)")
        else:
            print(f"\n[量纲修复] 无需修复，已经是正确单位")
        
        # 6.6 计算换手率验证
        volume_gu = current_volume * 100  # 手→股
        turnover_raw = (volume_gu / float_volume_td * 100) if float_volume_td else 0
        turnover_fixed = (volume_gu / float_volume_fixed * 100) if float_volume_fixed else 0
        print(f"\n[换手率验证]")
        print(f"  换手率(原始): {turnover_raw:.2f}%")
        print(f"  换手率(修复): {turnover_fixed:.2f}%")
        print(f"  物理判断: {'合理(5-30%)' if 5 <= turnover_fixed <= 30 else '异常'}")
        
        # 6.7 计算流通市值
        float_market_cap_td = float_volume_td * pre_close
        float_market_cap_fixed = float_volume_fixed * pre_close
        print(f"\n[流通市值]")
        print(f"  市值(原始): {float_market_cap_td/1e8:.2f} 亿元")
        print(f"  市值(修复): {float_market_cap_fixed/1e8:.2f} 亿元")
        print(f"  物理判断: {'合理(10-1000亿)' if 10 <= float_market_cap_fixed/1e8 <= 1000 else '异常'}")
        
        # 6.8 计算power_ratio和净流入
        price_range = tick_high - tick_low
        if price_range > 0:
            power_ratio = (current_price - pre_close) / price_range
            power_ratio = max(-1.0, min(power_ratio, 1.0))
        else:
            power_ratio = 1.0 if current_price > pre_close else -1.0
        
        net_inflow_est = current_amount * power_ratio * 0.5
        print(f"\n[净流入估算]")
        print(f"  power_ratio: {power_ratio:.2f}")
        print(f"  net_inflow_est: {net_inflow_est/1e8:.2f} 亿元")
        
        # 6.9 计算inflow_ratio（百分比形式）
        inflow_ratio_td = (net_inflow_est / float_market_cap_td * 100) if float_market_cap_td > 0 else 0
        inflow_ratio_fixed = (net_inflow_est / float_market_cap_fixed * 100) if float_market_cap_fixed > 0 else 0
        print(f"\n[inflow_ratio计算]")
        print(f"  inflow_ratio(原始): {inflow_ratio_td:.2f}%")
        print(f"  inflow_ratio(修复): {inflow_ratio_fixed:.2f}%")
        print(f"  物理判断: {'合理(0-15%)' if 0 <= inflow_ratio_fixed <= 15 else '异常'}")
        
        # 6.10 调用引擎验证
        print(f"\n[引擎调用验证]")
        try:
            # 准备参数
            minutes_elapsed = 240  # 盘后
            acceleration_factor = 1.8  # 涨停股
            flow_5min = current_amount / minutes_elapsed * 5
            flow_15min = current_amount / minutes_elapsed * 15 * acceleration_factor
            
            final_score, sustain_ratio, inflow_ratio_engine, ratio_stock, mfe = core_engine.calculate_true_dragon_score(
                net_inflow=net_inflow_est,
                price=current_price,
                prev_close=pre_close,
                high=tick_high,
                low=tick_low,
                open_price=tick.get('open', current_price),
                flow_5min=flow_5min,
                flow_15min=flow_15min,
                flow_5min_median_stock=1.0,
                space_gap_pct=0.5,
                float_volume_shares=float_volume_fixed,  # 使用修复后的float_volume
                current_time=now
            )
            print(f"  final_score: {final_score:.2f}")
            print(f"  sustain_ratio: {sustain_ratio:.2f}x")
            print(f"  inflow_ratio(引擎返回): {inflow_ratio_engine:.2f}%")
            print(f"  mfe: {mfe:.2f}")
            
            # 对比
            print(f"\n[最终对比]")
            print(f"  手动计算inflow_ratio(修复): {inflow_ratio_fixed:.2f}%")
            print(f"  引擎返回inflow_ratio: {inflow_ratio_engine:.2f}%")
            print(f"  差异: {abs(inflow_ratio_fixed - inflow_ratio_engine):.2f}%")
            
        except Exception as e:
            print(f"  [ERR] 引擎调用失败: {e}")
    
    print("\n" + "=" * 70)
    print("[诊断完成]")
    print("=" * 70)

if __name__ == '__main__':
    diagnose_inflow_dimension()
