# -*- coding: utf-8 -*-
"""
CTO 真龙解剖实验室 - 物理算子对照实验
对比志特新材(真龙) vs 杂毛的底层变量，找出权重畸变根因
"""
import sys
sys.path.insert(0, 'E:/MyQuantTool')
import math
import pandas as pd
from datetime import datetime, time, timezone, timedelta
from xtquant import xtdata
xtdata.enable_hello = False

# ============================================================
# 物理引擎核心算子（从V89提取，独立运行）
# ============================================================
def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except:
        return default

def calculate_physics_components(
    price, prev_close, high, low, open_price,
    amount, volume, float_volume_shares,
    flow_5min, flow_15min, flow_5min_median_stock,
    stock_code="UNKNOWN"
):
    """提取V89物理引擎的所有中间变量"""
    
    price = safe_float(price, 0.0)
    prev_close = safe_float(prev_close, 0.0)
    high = safe_float(high, 0.0)
    low = safe_float(low, 0.0)
    open_price = safe_float(open_price, 0.0)
    flow_5min = safe_float(flow_5min, 0.0)
    flow_15min = safe_float(flow_15min, 0.0)
    flow_5min_median_stock = safe_float(flow_5min_median_stock, 2_000_000)
    float_volume_shares = safe_float(float_volume_shares, 0.0)
    
    if price <= 0 or prev_close <= 0:
        return None
    
    float_market_cap = float_volume_shares * price
    if 0 < float_market_cap < 200_000_000:
        float_market_cap = float_market_cap * 10000.0
    
    change_pct = (price - prev_close) / prev_close * 100.0
    
    price_range = high - low
    if price_range > 0:
        purity = (price - low) / price_range
    else:
        purity = 1.0 if change_pct > 0 else 0.0
    purity_pct = purity * 100.0
    
    net_inflow = amount * 0.3
    if float_market_cap > 1000:
        raw_inflow_pct = (net_inflow / float_market_cap * 100.0)
        if abs(raw_inflow_pct) > 30.0:
            sign = 1.0 if raw_inflow_pct > 0 else -1.0
            inflow_ratio_pct = sign * (30.0 + 10.0 * math.log10(abs(raw_inflow_pct) - 29.0))
        else:
            inflow_ratio_pct = raw_inflow_pct
    else:
        inflow_ratio_pct = 0.0
    
    MIN_BASE_FLOW = 2_000_000
    safe_flow_5min = flow_5min if flow_5min > 0 else (flow_15min / 3.0 if flow_15min > 0 else 1.0)
    safe_median = flow_5min_median_stock if flow_5min_median_stock > 0 else MIN_BASE_FLOW
    raw_ratio_stock = safe_flow_5min / safe_median if safe_median > 0 else 1.0
    ratio_stock = 1.0 + 6.0 * math.tanh(raw_ratio_stock - 1.0)
    
    if inflow_ratio_pct <= 0.0:
        mfe = 0.0
    else:
        upward_thrust = ((price - low) + (high - open_price)) / 2
        price_range_pct = upward_thrust / prev_close * 100.0 if prev_close > 0 else 0.0
        mfe = price_range_pct / inflow_ratio_pct if inflow_ratio_pct > 0 else 0.0
    
    mass_potential = (inflow_ratio_pct / 100.0) * ratio_stock
    velocity = change_pct
    base_kinetic_energy = mass_potential * velocity
    friction_multiplier = min(max(purity, 0.0), 1.0) ** 2
    efficiency_multiplier = 3.0 / (1.0 + math.exp(-2.0 * (mfe - 1.2)))
    
    final_score_raw = base_kinetic_energy * friction_multiplier * efficiency_multiplier
    final_score = round(final_score_raw * 1000.0, 1)
    if final_score < 0:
        final_score = 0.0
    
    return {
        'stock_code': stock_code,
        'price': price,
        'prev_close': prev_close,
        'change_pct': round(change_pct, 2),
        'purity_pct': round(purity_pct, 1),
        'ratio_stock': round(ratio_stock, 2),
        'inflow_ratio_pct': round(inflow_ratio_pct, 2),
        'mfe': round(mfe, 2),
        'mass_potential': round(mass_potential, 4),
        'velocity': round(velocity, 4),
        'base_ke': round(base_kinetic_energy, 4),
        'friction': round(friction_multiplier, 3),
        'efficiency': round(efficiency_multiplier, 3),
        'final_score': final_score,
        'float_market_cap_yi': round(float_market_cap / 100_000_000, 2)
    }

def parse_tick_time(time_val):
    """解析Tick时间值 - Unix timestamp毫秒"""
    try:
        if isinstance(time_val, (int, float)):
            # Unix timestamp in milliseconds
            ts = int(time_val) / 1000
            dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8)))
            return dt.time()
    except:
        pass
    return None

def extract_tick_slice(tick_df, target_time):
    """提取指定时间点的Tick快照"""
    if tick_df is None or len(tick_df) == 0:
        return None
    
    tick_df = tick_df.copy()
    time_col = 'time' if 'time' in tick_df.columns else None
    
    if time_col is None:
        return None
    
    tick_df['parsed_time'] = tick_df[time_col].apply(parse_tick_time)
    tick_df = tick_df.dropna(subset=['parsed_time'])
    
    # 过滤掉lastPrice=0的tick（竞价期间）
    if 'lastPrice' in tick_df.columns:
        tick_df = tick_df[tick_df['lastPrice'] > 0]
    
    if len(tick_df) == 0:
        return None
    
    tick_df['time_diff'] = tick_df['parsed_time'].apply(
        lambda t: abs((t.hour * 3600 + t.minute * 60 + t.second) - 
                     (target_time.hour * 3600 + target_time.minute * 60 + target_time.second))
    )
    closest_idx = tick_df['time_diff'].idxmin()
    closest_tick = tick_df.loc[closest_idx]
    
    return closest_tick

def get_flow_at_time(tick_df, target_time):
    """计算到指定时间点的累计成交额"""
    if tick_df is None or len(tick_df) == 0:
        return 0.0, 0.0
    
    tick_df = tick_df.copy()
    time_col = 'time' if 'time' in tick_df.columns else None
    
    if time_col is None:
        return 0.0, 0.0
    
    tick_df['parsed_time'] = tick_df[time_col].apply(parse_tick_time)
    tick_df = tick_df.dropna(subset=['parsed_time'])
    
    if len(tick_df) == 0:
        return 0.0, 0.0
    
    before = tick_df[tick_df['parsed_time'] <= target_time]
    
    if len(before) == 0:
        return 0.0, 0.0
    
    flow_total = safe_float(before.iloc[-1].get('amount', 0), 0.0)
    
    return flow_total, flow_total

def run_experiment():
    print("=" * 80)
    print("CTO 真龙解剖实验室 - 物理算子对照实验")
    print("=" * 80)
    
    print("\n[数据装载]")
    
    dragon_data = {}
    for d in ['20260105', '20260106']:
        tick = xtdata.get_local_data(stock_list=['300986.SZ'], period='tick', start_time=d, end_time=d)
        if tick and '300986.SZ' in tick:
            dragon_data[d] = tick['300986.SZ']
            print(f"  300986.SZ (真龙) {d}: {len(dragon_data[d])} ticks")
    
    tick = xtdata.get_local_data(stock_list=['000533.SZ'], period='tick', start_time='20260311', end_time='20260311')
    weed_data = tick['000533.SZ'] if tick and '000533.SZ' in tick else None
    print(f"  000533.SZ (杂毛) 20260311: {len(weed_data) if weed_data is not None else 0} ticks")
    
    # 解析时间验证
    if '20260105' in dragon_data and len(dragon_data['20260105']) > 0:
        sample = dragon_data['20260105'].iloc[100]  # 跳过竞价期
        parsed = parse_tick_time(sample['time'])
        print(f"\n[时间解析验证] time={sample['time']} -> {parsed}")
        print(f"  lastPrice={sample['lastPrice']}, lastClose={sample['lastClose']}")
    
    print("\n[流通股本]")
    dragon_float = 150_000_000
    weed_float = 450_000_000
    print(f"  300986.SZ (真龙): {dragon_float/100000000:.2f}亿股")
    print(f"  000533.SZ (杂毛): {weed_float/100000000:.2f}亿股")
    
    time_slices = [
        ('09:30', time(9, 30)),
        ('10:00', time(10, 0)),
        ('10:30', time(10, 30)),
        ('11:30', time(11, 30)),
        ('14:00', time(14, 0)),
        ('15:00', time(15, 0)),
    ]
    
    print("\n" + "=" * 80)
    print("对照解剖表格")
    print("=" * 80)
    
    results = []
    
    for slice_name, slice_time in time_slices:
        print(f"\n[{slice_name} 切片解剖]")
        print("-" * 80)
        print(f"{'标的':<12} | {'涨幅%':>7} | {'量比':>6} | {'纯度%':>6} | {'质量M':>8} | {'速度V':>7} | {'摩擦':>5} | {'MFE乘数':>7} | {'最终得分':>8}")
        print("-" * 80)
        
        # 真龙 20260105
        if '20260105' in dragon_data:
            tick_df = dragon_data['20260105']
            slice_tick = extract_tick_slice(tick_df, slice_time)
            if slice_tick is not None:
                flow_5min, flow_15min = get_flow_at_time(tick_df, slice_time)
                
                result = calculate_physics_components(
                    price=slice_tick.get('lastPrice', 0),
                    prev_close=slice_tick.get('lastClose', 0),
                    high=slice_tick.get('high', 0),
                    low=slice_tick.get('low', 0),
                    open_price=slice_tick.get('open', 0),
                    amount=slice_tick.get('amount', 0),
                    volume=slice_tick.get('volume', 0),
                    float_volume_shares=dragon_float,
                    flow_5min=flow_5min,
                    flow_15min=flow_15min,
                    flow_5min_median_stock=5_000_000,
                    stock_code='300986(真龙)'
                )
                if result:
                    results.append(('300986', '20260105', slice_name, result))
                    print(f"300986(真龙) | {result['change_pct']:>+7.2f}% | {result['ratio_stock']:>6.2f}x | {result['purity_pct']:>6.1f}% | {result['mass_potential']:>8.4f} | {result['velocity']:>7.4f} | {result['friction']:>5.3f} | {result['efficiency']:>7.3f} | {result['final_score']:>8.1f}")
        
        # 杂毛
        if weed_data is not None:
            slice_tick = extract_tick_slice(weed_data, slice_time)
            if slice_tick is not None:
                flow_5min, flow_15min = get_flow_at_time(weed_data, slice_time)
                
                result = calculate_physics_components(
                    price=slice_tick.get('lastPrice', 0),
                    prev_close=slice_tick.get('lastClose', 0),
                    high=slice_tick.get('high', 0),
                    low=slice_tick.get('low', 0),
                    open_price=slice_tick.get('open', 0),
                    amount=slice_tick.get('amount', 0),
                    volume=slice_tick.get('volume', 0),
                    float_volume_shares=weed_float,
                    flow_5min=flow_5min,
                    flow_15min=flow_15min,
                    flow_5min_median_stock=5_000_000,
                    stock_code='000533(杂毛)'
                )
                if result:
                    results.append(('000533', '20260311', slice_name, result))
                    print(f"000533(杂毛) | {result['change_pct']:>+7.2f}% | {result['ratio_stock']:>6.2f}x | {result['purity_pct']:>6.1f}% | {result['mass_potential']:>8.4f} | {result['velocity']:>7.4f} | {result['friction']:>5.3f} | {result['efficiency']:>7.3f} | {result['final_score']:>8.1f}")
    
    # 分析结论
    print("\n" + "=" * 80)
    print("CTO 诊断结论")
    print("=" * 80)
    
    if results:
        dragon_results = [r for r in results if r[0] == '300986']
        weed_results = [r for r in results if r[0] == '000533']
        
        if dragon_results and weed_results:
            dragon_final = [r for r in dragon_results if r[2] == '15:00']
            weed_final = [r for r in weed_results if r[2] == '15:00']
            
            if dragon_final and weed_final:
                d = dragon_final[0][3]
                w = weed_final[0][3]
                
                print(f"\n【收盘终局对比】")
                print(f"  真龙(300986): 涨幅{d['change_pct']:+.2f}% | 量比{d['ratio_stock']:.2f}x | 得分{d['final_score']:.1f}")
                print(f"  杂毛(000533): 涨幅{w['change_pct']:+.2f}% | 量比{w['ratio_stock']:.2f}x | 得分{w['final_score']:.1f}")
                
                print(f"\n【权重畸变诊断】")
                print(f"  1. 速度(涨幅)差异: 真龙{d['change_pct']:+.2f}% vs 杂毛{w['change_pct']:+.2f}%")
                print(f"     线性公式下，涨幅差异被线性化！实际能量差距应呈指数级！")
                print(f"  2. 质量(量比*流入)差异: 真龙{d['mass_potential']:.4f} vs 杂毛{w['mass_potential']:.4f}")
                print(f"  3. 摩擦(纯度)差异: 真龙{d['friction']:.3f} vs 杂毛{w['friction']:.3f}")
                
                print(f"\n【核心病灶】")
                print(f"  VELOCITY线性增长是杀死真龙的头号凶手！")
                print(f"  建议修复: velocity = sign(change_pct) * |change_pct|^3")

if __name__ == '__main__':
    run_experiment()
