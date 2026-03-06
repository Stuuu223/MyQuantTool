# -*- coding: utf-8 -*-
"""
雷达漏斗诊断脚本 - 定位问题节点

问题现象：
- 粗筛池: 91只 -> 活跃: 0只 -> 过细筛: 0只
- 但日志显示"观察池最终状态: 9只"

诊断目标：
1. 定位股票在哪个节点被过滤
2. 检查细筛逻辑是否正确
3. 检查pool_stats统计逻辑
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, time as time_type
from xtquant import xtdata
from logic.data_providers.true_dictionary import get_true_dictionary
from logic.strategies.kinetic_core_engine import 动能打分引擎CoreEngine

def diagnose_radar():
    """诊断雷达漏斗"""
    print("=" * 60)
    print("[诊断] 雷达漏斗断点测试")
    print("=" * 60)
    
    # 1. 连接QMT
    print("\n[Step 1] 连接QMT...")
    try:
        xtdata.enable_hello = False
        print("[OK] QMT连接成功")
    except Exception as e:
        print(f"[ERR] QMT连接失败: {e}")
        return
    
    # 2. 获取TrueDictionary
    print("\n[Step 2] 获取TrueDictionary...")
    true_dict = get_true_dictionary()
    print(f"[OK] TrueDictionary股票数: {len(true_dict._float_volume)}")
    
    # 3. 模拟watchlist（取几只测试）
    test_stocks = ['600744.SH', '001696.SZ', '000862.SZ', '001282.SZ', '002986.SZ']
    print(f"\n[Step 3] 测试股票: {test_stocks}")
    
    # 2.5 预热TrueDictionary
    print("\n[Step 2.5] 预热TrueDictionary...")
    try:
        from logic.utils.calendar_utils import get_nth_previous_trading_day
        today = datetime.now().strftime('%Y%m%d')
        target_date = get_nth_previous_trading_day(today, 1)
        result = true_dict.warmup(test_stocks, target_date=target_date)
        print(f"[OK] 预热完成: 涨停价{result['qmt'].get('success', 0)}只")
        print(f"[OK] TrueDictionary股票数(预热后): {len(true_dict._float_volume)}")
    except Exception as e:
        print(f"[ERR] 预热失败: {e}")
    
    # 4. 获取tick数据
    print("\n[Step 4] 获取Tick数据...")
    now = datetime.now()
    minutes_elapsed = (now.hour * 60 + now.minute) - (9 * 60 + 30)
    minutes_elapsed = max(1, min(minutes_elapsed, 240))
    print(f"当前时间: {now.strftime('%H:%M:%S')}")
    print(f"已过分钟: {minutes_elapsed}")
    
    pool_stats = {
        'total': len(test_stocks),
        'active': 0,
        'up': 0,
        'down': 0,
        'passed_fine_filter': 0,
        'filtered': 0
    }
    
    core_engine = 动能打分引擎CoreEngine()
    
    for stock in test_stocks:
        print(f"\n--- 诊断 {stock} ---")
        
        # 获取tick
        try:
            tick = xtdata.get_full_tick([stock])
            if not tick or stock not in tick:
                print(f"  [SKIP] 无Tick数据")
                continue
            tick = tick[stock]
        except Exception as e:
            print(f"  [SKIP] Tick获取失败: {e}")
            continue
        
        # 检查tick内容
        current_price = tick.get('lastPrice', 0)
        current_volume = tick.get('volume', 0)
        pre_close = tick.get('lastClose', 0)
        current_amount = tick.get('amount', 0)
        
        print(f"  current_price: {current_price}")
        print(f"  current_volume: {current_volume} 手")
        print(f"  pre_close: {pre_close}")
        print(f"  current_amount: {current_amount} 元")
        
        # 检查volume是否为0
        if current_volume == 0:
            print(f"  [SKIP] volume=0，剔除")
            pool_stats['filtered'] += 1
            continue
        
        pool_stats['active'] += 1
        
        # 检查涨跌
        if current_price >= pre_close:
            pool_stats['up'] += 1
        else:
            pool_stats['down'] += 1
        
        # 获取流通股本
        float_volume = true_dict.get_float_volume(stock)
        print(f"  float_volume: {float_volume} 股")
        
        if float_volume <= 0:
            print(f"  [SKIP] float_volume<=0，剔除")
            continue
        
        # 计算换手率
        volume_gu = current_volume * 100  # 手→股
        current_turnover = (volume_gu / float_volume * 100)
        print(f"  current_turnover: {current_turnover:.2f}%")
        
        # 时间加权预估全天换手率
        est_full_day_turnover = current_turnover / minutes_elapsed * 240
        print(f"  est_full_day_turnover: {est_full_day_turnover:.2f}%")
        
        # 检查死亡防线
        if current_turnover >= 70.0 or est_full_day_turnover > 100.0:
            print(f"  [SKIP] 死亡换手/绞肉机")
            continue
        
        if minutes_elapsed <= 30 and current_turnover > 15.0:
            print(f"  [SKIP] 极速派发")
            continue
        
        # 通过细筛
        pool_stats['passed_fine_filter'] += 1
        print(f"  [PASS] 通过细筛!")
        
        # 尝试打分
        change_pct = (current_price - pre_close) / pre_close if pre_close > 0 else 0
        float_market_cap = float_volume * pre_close if float_volume else 1.0
        
        inflow_ratio_est = change_pct * 0.5
        inflow_ratio_est = max(-0.3, min(inflow_ratio_est, 0.3))
        net_inflow_est = current_amount * inflow_ratio_est
        
        tick_high = tick.get('high', current_price)
        tick_low = tick.get('low', current_price)
        
        print(f"  tick_high: {tick_high}, tick_low: {tick_low}")
        
        # CTO V13修复：acceleration_factor避免sustain_ratio=2.0数学必然
        price_position = (current_price - tick_low) / (tick_high - tick_low) if tick_high > tick_low else 0.5
        change_pct_for_sustain = (current_price - pre_close) / pre_close if pre_close > 0 else 0
        acceleration_factor = 1.0 + (price_position - 0.5) * 1.0 + change_pct_for_sustain * 3.0
        acceleration_factor = max(0.3, min(acceleration_factor, 3.0))
        print(f"  price_position: {price_position:.2f}, acceleration_factor: {acceleration_factor:.2f}")
        
        try:
            final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe = core_engine.calculate_true_dragon_score(
                net_inflow=net_inflow_est,
                price=current_price,
                prev_close=pre_close,
                high=tick_high,
                low=tick_low,
                open_price=tick.get('open', current_price),
                flow_5min=current_amount / 240 * 5,
                flow_15min=current_amount / 240 * 15 * acceleration_factor,  # CTO V13修复
                flow_5min_median_stock=1.0,
                space_gap_pct=0.5,
                float_volume_shares=float_volume,
                current_time=now  # CTO V13修复：传入datetime而非datetime.time
            )
            print(f"  [SCORE] final={final_score:.2f}, sustain={sustain_ratio:.2f}, inflow={inflow_ratio:.4f}, mfe={mfe:.2f}")
            
            # CTO V14验证：inflow_ratio物理卡控
            if abs(inflow_ratio) > 0.30:
                print(f"  [WARN] inflow_ratio={inflow_ratio:.4f} 超过物理限制30%!")
        except Exception as e:
            print(f"  [ERR] 打分失败: {e}")
    
    print("\n" + "=" * 60)
    print("[诊断结果]")
    print(f"  总数: {pool_stats['total']}")
    print(f"  活跃: {pool_stats['active']}")
    print(f"  红盘: {pool_stats['up']}")
    print(f"  绿盘: {pool_stats['down']}")
    print(f"  过细筛: {pool_stats['passed_fine_filter']}")
    print(f"  剔除: {pool_stats['filtered']}")
    print("=" * 60)

if __name__ == '__main__':
    diagnose_radar()
