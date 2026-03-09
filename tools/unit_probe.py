# -*- coding: utf-8 -*-
"""
CTO量纲探针脚本 - 验证float_volume_shares的真实单位
用途: 用已知市值的票反推，确认QMT各接口返回的volume单位

运行方式:
    python tools/unit_probe.py
"""

import sys
sys.path.insert(0, r'C:\Users\pc\Desktop\Astock\MyQuantTool')

from xtquant import xtdata
import pandas as pd

# 测试标的: 选择几只市值已知的股票
TEST_STOCKS = [
    ("000001.SZ", "平安银行", "约2500亿市值"),
    ("600000.SH", "浦发银行", "约2200亿市值"),
    ("002261.SZ", "拓维信息", "约300亿市值"),
    ("600227.SH", "赤天化", "约50亿市值"),
]

def probe_get_full_tick():
    """探针1: get_full_tick返回的volume单位"""
    print("\n" + "="*80)
    print("【探针1】get_full_tick() 接口量纲检测")
    print("="*80)
    
    stocks = [s[0] for s in TEST_STOCKS]
    tick_data = xtdata.get_full_tick(stocks)
    
    for stock, name, expected_cap in TEST_STOCKS:
        if stock in tick_data:
            tick = tick_data[stock]
            volume = tick.get('volume', 0)
            amount = tick.get('amount', 0)
            last_price = tick.get('lastPrice', 0)
            
            print(f"\n{name} ({stock}):")
            print(f"  volume (原始值): {volume:,.0f}")
            print(f"  amount (成交额): {amount:,.0f} 元")
            print(f"  lastPrice: {last_price:.2f} 元")
            
            # 反推volume单位
            if volume > 0 and last_price > 0:
                # 假设volume是手(100股)
                shares_from_hand = volume * 100
                calculated_amount_hand = shares_from_hand * last_price
                
                # 假设volume是股
                calculated_amount_shares = volume * last_price
                
                print(f"  若volume是手(100股): 推算成交额 = {calculated_amount_hand:,.0f} 元")
                print(f"  若volume是股: 推算成交额 = {calculated_amount_shares:,.0f} 元")
                print(f"  实际amount: {amount:,.0f} 元")
                
                # 判断哪个更匹配
                if abs(calculated_amount_hand - amount) / amount < 0.1:
                    print(f"  ✅ 结论: volume单位是【手】(100股)")
                elif abs(calculated_amount_shares - amount) / amount < 0.1:
                    print(f"  ✅ 结论: volume单位是【股】")
                else:
                    print(f"  ⚠️ 警告: 无法确定volume单位，差异过大")

def probe_get_local_data():
    """探针2: get_local_data返回的volume单位"""
    print("\n" + "="*80)
    print("【探针2】get_local_data(period='1d') 接口量纲检测")
    print("="*80)
    
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    
    for stock, name, expected_cap in TEST_STOCKS[:2]:  # 只测前2只避免太慢
        try:
            local_data = xtdata.get_local_data(
                field_list=['volume', 'amount', 'close'],
                stock_list=[stock],
                period='1d',
                start_time=start_date,
                end_time=end_date
            )
            
            if local_data and stock in local_data:
                df = local_data[stock]
                if len(df) > 0:
                    row = df.iloc[-1]
                    volume = row.get('volume', 0)
                    amount = row.get('amount', 0)
                    close = row.get('close', 0)
                    
                    print(f"\n{name} ({stock}) - 最新日K:")
                    print(f"  volume (原始值): {volume:,.0f}")
                    print(f"  amount (成交额): {amount:,.0f} 元")
                    print(f"  close: {close:.2f} 元")
                    
                    # 反推
                    if volume > 0 and close > 0:
                        calculated_amount = volume * close
                        ratio = calculated_amount / amount if amount > 0 else 0
                        print(f"  volume * close = {calculated_amount:,.0f}")
                        print(f"  与amount比值: {ratio:.4f}")
                        
                        if 0.9 < ratio < 1.1:
                            print(f"  ✅ 结论: volume单位是【股】")
                        elif 0.009 < ratio < 0.011:
                            print(f"  ✅ 结论: volume单位是【手】(100股)")
                        else:
                            print(f"  ⚠️ 警告: 单位不明确，ratio={ratio}")
        except Exception as e:
            print(f"\n{name} ({stock}): 获取失败 - {e}")

def probe_true_dictionary():
    """探针3: TrueDictionary返回的FloatVolume单位"""
    print("\n" + "="*80)
    print("【探针3】TrueDictionary.get_float_volume() 量纲检测")
    print("="*80)
    
    from logic.data_providers.true_dictionary import get_true_dictionary
    
    true_dict = get_true_dictionary()
    
    for stock, name, expected_cap in TEST_STOCKS:
        try:
            float_volume = true_dict.get_float_volume(stock)
            print(f"\n{name} ({stock}):")
            print(f"  FloatVolume (原始值): {float_volume:,.0f}")
            print(f"  预期市值: {expected_cap}")
            
            if float_volume:
                # 假设是股，计算市值
                # 需要获取当前价格
                tick = xtdata.get_full_tick([stock])
                if stock in tick:
                    price = tick[stock].get('lastPrice', 0)
                    if price > 0:
                        cap_assume_shares = float_volume * price
                        cap_assume_wan_gu = float_volume * 10000 * price
                        cap_assume_shou = float_volume * 100 * price
                        
                        print(f"  当前价格: {price:.2f}")
                        print(f"  若FloatVolume是股: 市值 = {cap_assume_shares/1e8:.2f}亿")
                        print(f"  若FloatVolume是万股: 市值 = {cap_assume_wan_gu/1e8:.2f}亿")
                        print(f"  若FloatVolume是手: 市值 = {cap_assume_shou/1e8:.2f}亿")
                        
                        # 与预期比较
                        expected_yi = float(expected_cap.replace("约", "").replace("亿市值", ""))
                        if abs(cap_assume_shares/1e8 - expected_yi) / expected_yi < 0.3:
                            print(f"  ✅ 结论: FloatVolume单位是【股】")
                        elif abs(cap_assume_wan_gu/1e8 - expected_yi) / expected_yi < 0.3:
                            print(f"  ✅ 结论: FloatVolume单位是【万股】")
                        elif abs(cap_assume_shou/1e8 - expected_yi) / expected_yi < 0.3:
                            print(f"  ✅ 结论: FloatVolume单位是【手】")
                        else:
                            print(f"  ⚠️ 警告: 无法确定单位")
        except Exception as e:
            print(f"\n{name} ({stock}): 获取失败 - {e}")

def probe_inflow_calculation():
    """探针4: 净流入计算链路验证"""
    print("\n" + "="*80)
    print("【探针4】净流入计算链路验证")
    print("="*80)
    
    stock = "000001.SZ"  # 用平安银行测试
    
    try:
        # 获取Tick数据
        local_data = xtdata.get_local_data(
            field_list=['volume', 'amount', 'lastPrice', 'lastClose', 'high', 'low'],
            stock_list=[stock],
            period='tick',
            start_time='20260306',
            end_time='20260306'
        )
        
        if local_data and stock in local_data:
            df = local_data[stock]
            if len(df) > 0:
                tick = df.iloc[-1]
                volume = float(tick.get('volume', 0))
                amount = float(tick.get('amount', 0))
                price = float(tick.get('lastPrice', 0))
                pre_close = float(tick.get('lastClose', 0))
                high = float(tick.get('high', price))
                low = float(tick.get('low', price))
                
                print(f"\n股票: {stock}")
                print(f"  Tick累计volume: {volume:,.0f}")
                print(f"  Tick累计amount: {amount:,.0f} 元")
                print(f"  当前价: {price:.2f}")
                print(f"  昨收: {pre_close:.2f}")
                
                # 模拟计算
                if high > low and price > 0:
                    raw_purity = (price - pre_close) / (high - low)
                    raw_purity = max(-1.0, min(1.0, raw_purity))
                    
                    # 方式1: 用amount * purity
                    net_inflow_v1 = amount * raw_purity * 0.5
                    
                    # 方式2: 用volume * price * purity (假设volume是股)
                    net_inflow_v2_assume_shares = volume * price * raw_purity * 0.5
                    
                    # 方式3: 用volume * 100 * price * purity (假设volume是手)
                    net_inflow_v3_assume_shou = volume * 100 * price * raw_purity * 0.5
                    
                    print(f"\n  raw_purity: {raw_purity:.4f}")
                    print(f"  净流入计算方式1 (amount*purity): {net_inflow_v1:,.0f} 元")
                    print(f"  净流入计算方式2 (volume*price*purity, assume股): {net_inflow_v2_assume_shares:,.0f} 元")
                    print(f"  净流入计算方式3 (volume*100*price*purity, assume手): {net_inflow_v3_assume_shou:,.0f} 元")
                    
                    # 获取流通股本计算流入比
                    from logic.data_providers.true_dictionary import get_true_dictionary
                    true_dict = get_true_dictionary()
                    float_volume = true_dict.get_float_volume(stock) or 1e10
                    
                    print(f"\n  FloatVolume (来自TrueDictionary): {float_volume:,.0f}")
                    
                    # 计算流通市值
                    float_cap = float_volume * price
                    print(f"  计算流通市值 (FV*price): {float_cap/1e8:.2f}亿")
                    
                    # 计算流入比
                    inflow_ratio_v1 = net_inflow_v1 / float_cap * 100
                    inflow_ratio_v2 = net_inflow_v2_assume_shares / float_cap * 100
                    inflow_ratio_v3 = net_inflow_v3_assume_shou / float_cap * 100
                    
                    print(f"\n  流入比 (方式1): {inflow_ratio_v1:.2f}%")
                    print(f"  流入比 (方式2): {inflow_ratio_v2:.2f}%")
                    print(f"  流入比 (方式3): {inflow_ratio_v3:.2f}%")
                    
                    print(f"\n  ✅ 物理合理的流入比应在 0.1%-20% 区间")
                    if 0.1 < inflow_ratio_v1 < 20:
                        print(f"  ✅ 方式1(amount)物理合理")
                    if 0.1 < inflow_ratio_v2 < 20:
                        print(f"  ✅ 方式2(volume*price, assume股)物理合理")
                    if 0.1 < inflow_ratio_v3 < 20:
                        print(f"  ✅ 方式3(volume*100*price, assume手)物理合理")
    except Exception as e:
        print(f"验证失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("CTO量纲探针 - 验证QMT数据单位一致性")
    print("="*80)
    
    # 运行所有探针
    probe_get_full_tick()
    probe_get_local_data()
    probe_true_dictionary()
    probe_inflow_calculation()
    
    print("\n" + "="*80)
    print("探针执行完成")
    print("="*80)
