"""
断点测试 - 逐层检查盘后粗筛流程

【运行方式】
E:\MyQuantTool\venv_qmt\Scripts\python.exe tests/breakpoint_test.py
"""

import sys
sys.path.insert(0, 'E:/MyQuantTool')
sys.path.insert(0, 'E:/MyQuantTool/xtquant')

from datetime import datetime
import pandas as pd
import numpy as np
import numpy as np

def main():
    print("=" * 60)
    print("🔬 断点测试 - 盘后粗筛流程")
    print("=" * 60)
    
    now = datetime.now()
    print(f"当前时间: {now.strftime('%Y%m%d %H:%M:%S')}")
    
    # ========== Step 0: 初始化QMT ==========
    print("\n【Step 0】初始化QMT...")
    from logic.data_providers.qmt_event_adapter import QMTEventAdapter
    adapter = QMTEventAdapter()
    if not adapter.initialize():
        print("❌ QMT初始化失败")
        return
    
    all_stocks = adapter.get_all_a_shares()
    print(f"全市场股票: {len(all_stocks)} 只")
    
    # ========== Step 1: 获取快照 ==========
    print("\n【Step 1】获取全市场快照...")
    snapshot = adapter.get_full_tick_snapshot(all_stocks)
    print(f"快照数据: {len(snapshot)} 只")
    
    # ========== Step 2: 第一斩过滤条件检查 ==========
    print("\n【Step 2】第一斩过滤条件检查...")
    df = pd.DataFrame([
        {
            'stock_code': code,
            'open': tick.get('open', 0) if isinstance(tick, dict) else getattr(tick, 'open', 0),
            'volume': tick.get('volume', 0) if isinstance(tick, dict) else getattr(tick, 'volume', 0),
            'amount': tick.get('amount', 0) if isinstance(tick, dict) else getattr(tick, 'amount', 0),
            'prev_close': tick.get('lastClose', 0) if isinstance(tick, dict) else getattr(tick, 'lastClose', 0),
        }
        for code, tick in snapshot.items() if tick
    ])
    print(f"DataFrame行数: {len(df)}")
    
    # 检查各字段分布
    print(f"\n字段分布:")
    print(f"  open > 0: {(df['open'] > 0).sum()}/{len(df)}")
    print(f"  volume > 0: {(df['volume'] > 0).sum()}/{len(df)}")
    print(f"  prev_close > 0: {(df['prev_close'] > 0).sum()}/{len(df)}")
    
    # 第一斩条件
    print(f"\n第一斩过滤条件:")
    
    # 条件1: open >= prev_close（非低开）
    cond1 = df['open'] >= df['prev_close']
    print(f"  非低开(open>=prev_close): {cond1.sum()}/{len(df)}")
    
    # 条件2: volume >= 1000（有量）
    cond2 = df['volume'] >= 1000
    print(f"  有量(volume>=1000手): {cond2.sum()}/{len(df)}")
    
    # 条件3: open > 0（有开盘价）
    cond3 = df['open'] > 0
    print(f"  有开盘价(open>0): {cond3.sum()}/{len(df)}")
    
    # 组合条件
    mask = cond1 & cond2 & cond3
    print(f"\n第一斩组合条件: {mask.sum()}/{len(df)}")
    
    df_auction = df[mask].copy()
    print(f"第一斩后: {len(df_auction)} 只")
    
    if df_auction.empty:
        print("❌ 第一斩后为空！检查原因...")
        print("\n【诊断】详细检查前10只股票:")
        sample = df.head(10)
        for _, row in sample.iterrows():
            print(f"  {row['stock_code']}: open={row['open']}, prev_close={row['prev_close']}, volume={row['volume']}")
            if row['open'] > 0 and row['prev_close'] > 0:
                change = (row['open'] - row['prev_close']) / row['prev_close'] * 100
                print(f"    → 涨幅={change:.2f}%")
        return
    
    # ========== Step 3: TrueDictionary预热 ==========
    print("\n【Step 3】TrueDictionary预热...")
    from logic.data_providers.true_dictionary import get_true_dictionary
    today = now.strftime('%Y%m%d')
    
    true_dict = get_true_dictionary()
    print(f"  prev_close_cache状态: {len(true_dict._prev_close_cache)} 只")
    
    if not true_dict._prev_close_cache:
        print("  预热中...")
        true_dict.warmup(all_stocks, target_date=today, force=False)
        print(f"  预热后: {len(true_dict._prev_close_cache)} 只")
    
    # ========== Step 4: 第二斩字段填充 ==========
    print("\n【Step 4】第二斩字段填充...")
    df_auction['avg_volume_5d'] = df_auction['stock_code'].map(true_dict.get_avg_volume_5d)
    df_auction['avg_turnover_5d'] = df_auction['stock_code'].map(true_dict.get_avg_turnover_5d)
    df_auction['float_volume'] = df_auction['stock_code'].map(true_dict.get_float_volume)
    # prev_close已从快照获取（Step 2），无需从TrueDictionary获取
    
    print(f"  avg_volume_5d > 0: {(df_auction['avg_volume_5d'] > 0).sum()}/{len(df_auction)}")
    print(f"  avg_turnover_5d > 0: {(df_auction['avg_turnover_5d'] > 0).sum()}/{len(df_auction)}")
    print(f"  float_volume > 0: {(df_auction['float_volume'] > 0).sum()}/{len(df_auction)}")
    print(f"  prev_close(快照) > 0: {(df_auction['prev_close'] > 0).sum()}/{len(df_auction)}")
    
    # ========== Step 5: 计算量比 ==========
    print("\n【Step 5】计算量比...")
    df_auction['volume_gu'] = df_auction['volume'] * 100
    
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    raw_minutes = (now - market_open).total_seconds() / 60
    minutes_passed = max(5, min(raw_minutes, 240))
    print(f"  已过分钟: {minutes_passed:.0f}")
    
    df_auction['estimated_full_day_volume'] = df_auction['volume_gu'] / minutes_passed * 240
    df_auction['avg_volume_5d_gu'] = df_auction['avg_volume_5d'] * 100
    df_auction['volume_ratio'] = df_auction['estimated_full_day_volume'] / df_auction['avg_volume_5d_gu'].replace(0, np.nan)
    
    print(f"  volume_ratio有效: {df_auction['volume_ratio'].notna().sum()}/{len(df_auction)}")
    print(f"  volume_ratio中位数: {df_auction['volume_ratio'].median():.2f}")
    
    # ========== Step 6: 计算换手率和成交额 ==========
    print("\n【Step 6】计算换手率和成交额...")
    df_auction['current_turnover'] = (df_auction['volume_gu'] / df_auction['float_volume'].replace(0, np.nan)) * 100
    
    # 【修复】直接使用快照的prev_close（已经在Step 2获取），不从TrueDictionary获取
    # prev_close已经在DataFrame中
    df_auction['avg_amount_5d'] = df_auction['avg_volume_5d'] * df_auction['prev_close'] * 100  # 手→股→元
    
    print(f"  current_turnover有效: {df_auction['current_turnover'].notna().sum()}/{len(df_auction)}")
    print(f"  prev_close(快照) > 0: {(df_auction['prev_close'] > 0).sum()}/{len(df_auction)}")
    print(f"  avg_amount_5d > 0: {(df_auction['avg_amount_5d'] > 0).sum()}/{len(df_auction)}")
    print(f"  avg_amount_5d中位数: {df_auction['avg_amount_5d'].median()/10000:.0f}万")
    
    # ========== Step 7: fillna处理 ==========
    print("\n【Step 7】fillna处理...")
    df_auction['volume_ratio'] = df_auction['volume_ratio'].fillna(1.0)
    df_auction['avg_turnover_5d'] = df_auction['avg_turnover_5d'].fillna(1.0)
    df_auction['avg_amount_5d'] = df_auction['avg_amount_5d'].fillna(0.0)
    df_auction['current_turnover'] = df_auction['current_turnover'].fillna(0.0)
    
    # ========== Step 8: 动态阈值 ==========
    print("\n【Step 8】动态阈值...")
    if minutes_passed >= 240:
        min_volume_multiplier = 1.5
        mode_tag = "盘后投影"
    elif minutes_passed >= 120:
        min_volume_multiplier = 2.0
        mode_tag = "午后修正"
    else:
        min_volume_multiplier = 3.0
        mode_tag = "早盘脉冲"
    
    min_avg_amount_5d = 30000000.0  # 3000万
    min_avg_turnover_5d = 1.0
    max_open_turnover = 30.0
    
    print(f"  运行模式: {mode_tag}")
    print(f"  量比阈值: {min_volume_multiplier}x")
    print(f"  5日均额阈值: {min_avg_amount_5d/10000:.0f}万")
    
    # ========== Step 9: 逐条件检查 ==========
    print("\n【Step 9】逐条件检查...")
    cond_vol_ratio = df_auction['volume_ratio'] >= min_volume_multiplier
    cond_amount = df_auction['avg_amount_5d'] >= min_avg_amount_5d
    cond_turnover = df_auction['avg_turnover_5d'] >= min_avg_turnover_5d
    cond_current = df_auction['current_turnover'] < max_open_turnover
    
    print(f"  量比>={min_volume_multiplier}x: {cond_vol_ratio.sum()}/{len(df_auction)}")
    print(f"  5日均额>=3000万: {cond_amount.sum()}/{len(df_auction)}")
    print(f"  5日均换手>=1%: {cond_turnover.sum()}/{len(df_auction)}")
    print(f"  开盘换手<30%: {cond_current.sum()}/{len(df_auction)}")
    
    # 组合条件
    mask_final = cond_vol_ratio & cond_amount & cond_turnover & cond_current
    print(f"\n组合条件: {mask_final.sum()}/{len(df_auction)}")
    
    filtered = df_auction[mask_final]
    print(f"\n📊 最终结果: {len(filtered)} 只")
    
    if len(filtered) > 0:
        print("\n前5只股票:")
        print(filtered[['stock_code', 'volume_ratio', 'avg_amount_5d', 'avg_turnover_5d', 'current_turnover']].head(5).to_string())
    else:
        print("\n❌ 最终结果为空！逐条件定位问题...")
        # 找出哪个条件最严格
        conditions = {
            f'量比>={min_volume_multiplier}x': cond_vol_ratio.sum(),
            f'5日均额>=3000万': cond_amount.sum(),
            f'5日均换手>=1%': cond_turnover.sum(),
            f'开盘换手<30%': cond_current.sum(),
        }
        print("\n各条件通过数量:")
        for name, count in sorted(conditions.items(), key=lambda x: x[1]):
            print(f"  {name}: {count}/{len(df_auction)}")
        
        # 找最严格的条件
        min_cond = min(conditions.items(), key=lambda x: x[1])
        print(f"\n最严格条件: {min_cond[0]} (只通过{min_cond[1]}只)")
    
    print("\n" + "=" * 60)
    print("✅ 断点测试完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
