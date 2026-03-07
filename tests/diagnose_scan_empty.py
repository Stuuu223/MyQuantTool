# -*- coding: utf-8 -*-
"""
CTO V39 诊断脚本：打分引擎输出诊断
"""
import sys
sys.path.insert(0, 'E:/MyQuantTool')

def diagnose_scoring():
    print("=" * 60)
    print("🔍 CTO V39 打分引擎输出诊断")
    print("=" * 60)
    
    from logic.utils.calendar_utils import get_latest_completed_trading_day
    from logic.data_providers.universe_builder import UniverseBuilder
    from logic.data_providers.true_dictionary import get_true_dictionary
    from logic.strategies.kinetic_core_engine import 动能打分引擎CoreEngine
    from xtquant import xtdata
    import pandas as pd
    from datetime import datetime, timedelta, time as time_type
    
    # 获取粗筛底池
    target_date = get_latest_completed_trading_day()
    print(f"目标日期: {target_date}")
    
    builder = UniverseBuilder(target_date=target_date)
    base_pool, _ = builder.build()
    print(f"粗筛底池: {len(base_pool)} 只")
    
    # 预热
    true_dict = get_true_dictionary()
    true_dict.warmup(base_pool[:100], target_date=target_date)
    
    # 读取日K数据
    start_date = (datetime.strptime(target_date, '%Y%m%d') - timedelta(days=10)).strftime('%Y%m%d')
    local_data = xtdata.get_local_data(
        field_list=['open', 'high', 'low', 'close', 'volume', 'amount', 'preClose'],
        stock_list=base_pool[:100],  # 只测试前100只
        period='1d',
        start_time=start_date,
        end_time=target_date
    )
    
    # 检测实际日期
    sample_df = pd.DataFrame(local_data[base_pool[0]])
    actual_date = str(sample_df.index[-1]) if not sample_df.empty else target_date
    print(f"实际数据日期: {actual_date}")
    
    # 打分
    core_engine = 动能打分引擎CoreEngine()
    from datetime import datetime as dt_class
    
    # 分数分布
    score_dist = {
        'raw_0': 0, 'raw_1_30': 0, 'raw_31_50': 0, 'raw_51_80': 0, 'raw_81_plus': 0,
        'final_0': 0, 'final_1_30': 0, 'final_31_50': 0, 'final_51_80': 0, 'final_81_plus': 0,
        'sustain_kill': 0, 'purity_kill': 0, 'exception': 0
    }
    
    samples = []
    
    for stock in base_pool[:100]:
        if stock not in local_data or local_data[stock] is None:
            continue
        
        df = pd.DataFrame(local_data[stock])
        if df.empty:
            continue
        
        row = df.iloc[-1]
        current_price = float(row.get('close', 0))
        current_amount = float(row.get('amount', 0))
        pre_close = float(row.get('preClose', 0))
        
        if current_price <= 0 or current_amount <= 0 or pre_close <= 0:
            continue
        
        tick_high = float(row.get('high', current_price))
        tick_low = float(row.get('low', current_price))
        open_price = float(row.get('open', current_price))
        
        # 计算指标
        price_position = (current_price - tick_low) / (tick_high - tick_low) if tick_high > tick_low else 0.5
        change_pct = (current_price - pre_close) / pre_close
        
        acceleration_factor = 1.0 + (price_position - 0.5) * 1.0 + change_pct * 3.0
        acceleration_factor = max(0.3, min(acceleration_factor, 3.0))
        
        flow_5min = current_amount / 240.0 * 5
        flow_15min = current_amount / 240.0 * 15 * acceleration_factor
        
        fv = true_dict.get_float_volume(stock)
        if not fv or fv <= 0:
            fv = 1000000000.0
        elif fv < 10000000:
            fv *= 10000
        
        price_range = tick_high - tick_low
        if price_range > 0:
            raw_purity = (current_price - pre_close) / price_range
        else:
            raw_purity = 1.0 if current_price > pre_close else -1.0
        quant_purity = min(max(raw_purity, -1.0), 1.0) * 100
        
        # sustain_ratio
        if flow_5min > 0:
            sustain_ratio = (flow_15min - flow_5min) / flow_5min
        else:
            sustain_ratio = -1.0
        
        try:
            frozen_time = dt_class.combine(dt_class.today(), time_type(15, 0, 0))
            
            score_data = core_engine.calculate_true_dragon_score(
                net_inflow=(current_amount / 240.0 * 15) * raw_purity,
                price=current_price,
                prev_close=pre_close,
                high=tick_high,
                low=tick_low,
                open_price=open_price,
                flow_5min=flow_5min,
                flow_15min=flow_15min,
                flow_5min_median_stock=1.0,
                space_gap_pct=0.5,
                float_volume_shares=fv,
                current_time=frozen_time
            )
            
            raw_score = score_data.get('raw_score', score_data.get('final_score', 0))
            final_score = score_data.get('final_score', 0)
            actual_sustain = score_data.get('sustain_ratio', sustain_ratio)
            
            # 统计raw_score分布
            if raw_score == 0:
                score_dist['raw_0'] += 1
            elif raw_score <= 30:
                score_dist['raw_1_30'] += 1
            elif raw_score <= 50:
                score_dist['raw_31_50'] += 1
            elif raw_score <= 80:
                score_dist['raw_51_80'] += 1
            else:
                score_dist['raw_81_plus'] += 1
            
            # 统计final_score分布
            if final_score == 0:
                score_dist['final_0'] += 1
            elif final_score <= 30:
                score_dist['final_1_30'] += 1
            elif final_score <= 50:
                score_dist['final_31_50'] += 1
            elif final_score <= 80:
                score_dist['final_51_80'] += 1
            else:
                score_dist['final_81_plus'] += 1
            
            # 统计绞杀
            if actual_sustain < 1.0:
                score_dist['sustain_kill'] += 1
            if quant_purity <= -50.0:
                score_dist['purity_kill'] += 1
            
            # 收集样本
            if final_score >= 50 and len(samples) < 5:
                samples.append({
                    'stock': stock,
                    'raw': raw_score,
                    'final': final_score,
                    'sustain': actual_sustain,
                    'purity': quant_purity,
                    'change': change_pct * 100
                })
                
        except Exception as e:
            score_dist['exception'] += 1
            if score_dist['exception'] <= 3:
                print(f"   {stock}: 异常 {e}")
    
    print(f"\n📊 Raw Score分布:")
    print(f"   0分: {score_dist['raw_0']}")
    print(f"   1-30分: {score_dist['raw_1_30']}")
    print(f"   31-50分: {score_dist['raw_31_50']}")
    print(f"   51-80分: {score_dist['raw_51_80']}")
    print(f"   81+分: {score_dist['raw_81_plus']}")
    
    print(f"\n📊 Final Score分布:")
    print(f"   0分: {score_dist['final_0']}")
    print(f"   1-30分: {score_dist['final_1_30']}")
    print(f"   31-50分: {score_dist['final_31_50']}")
    print(f"   51-80分: {score_dist['final_51_80']}")
    print(f"   81+分: {score_dist['final_81_plus']}")
    
    print(f"\n📊 绞杀统计:")
    print(f"   sustain < 1.0: {score_dist['sustain_kill']}")
    print(f"   purity <= -50%: {score_dist['purity_kill']}")
    print(f"   异常: {score_dist['exception']}")
    
    if samples:
        print(f"\n📊 通过防线的样本:")
        for s in samples:
            print(f"   {s['stock']}: raw={s['raw']:.1f}, final={s['final']:.1f}, sustain={s['sustain']:.2f}x, change={s['change']:.2f}%")

if __name__ == "__main__":
    diagnose_scoring()