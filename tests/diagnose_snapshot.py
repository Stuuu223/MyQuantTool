"""
盘后快照诊断 - 直接测试_snapshot_filter的数据流

【诊断目的】
验证盘后运行时快照数据的完整性

【运行方式】
E:\MyQuantTool\venv_qmt\Scripts\python.exe tests/diagnose_snapshot.py
"""

import sys
sys.path.insert(0, 'E:/MyQuantTool')
sys.path.insert(0, 'E:/MyQuantTool/xtquant')

from datetime import datetime
from logic.data_providers.true_dictionary import get_true_dictionary
from logic.core.config_manager import get_config_manager
from logic.data_providers.qmt_event_adapter import QMTEventAdapter
import pandas as pd

def main():
    print("=" * 60)
    print("🔬 盘后快照诊断")
    print("=" * 60)
    
    now = datetime.now()
    print(f"当前时间: {now.strftime('%H:%M:%S')}")
    
    # 1. 初始化Adapter
    print("\n【Step 1】初始化QMTEventAdapter...")
    adapter = QMTEventAdapter()
    if not adapter.initialize():
        print("❌ QMT初始化失败")
        return
    all_stocks = adapter.get_all_a_shares()
    print(f"全市场股票: {len(all_stocks)} 只")
    
    # 2. 获取快照
    print("\n【Step 2】获取全市场快照...")
    snapshot = adapter.get_full_tick_snapshot(all_stocks)
    print(f"快照数据: {len(snapshot)} 只")
    
    if not snapshot:
        print("❌ 快照为空，无法继续")
        return
    
    # 3. 转换为DataFrame
    print("\n【Step 3】转换为DataFrame...")
    
    # 先看看快照中有哪些字段
    first_code = list(snapshot.keys())[0]
    first_tick = snapshot[first_code]
    print(f"快照字段示例 ({first_code}): {list(first_tick.keys()) if isinstance(first_tick, dict) else dir(first_tick)}")
    
    df = pd.DataFrame([
        {
            'stock_code': code,
            'price': tick.get('lastPrice', 0) if isinstance(tick, dict) else getattr(tick, 'lastPrice', 0),
            'volume': tick.get('volume', 0) if isinstance(tick, dict) else getattr(tick, 'volume', 0),
            'amount': tick.get('amount', 0) if isinstance(tick, dict) else getattr(tick, 'amount', 0),
            'open': tick.get('open', 0) if isinstance(tick, dict) else getattr(tick, 'open', 0),
            'prev_close': tick.get('lastClose', 0) if isinstance(tick, dict) else getattr(tick, 'lastClose', 0),  # 修复：lastClose而非preClose
        }
        for code, tick in snapshot.items() if tick
    ])
    print(f"DataFrame行数: {len(df)}")
    
    # 4. 检查关键字段
    print("\n【Step 4】检查关键字段...")
    print(f"  volume > 0: {(df['volume'] > 0).sum()}/{len(df)}")
    print(f"  amount > 0: {(df['amount'] > 0).sum()}/{len(df)}")
    print(f"  price > 0: {(df['price'] > 0).sum()}/{len(df)}")
    print(f"  prev_close > 0: {(df['prev_close'] > 0).sum()}/{len(df)}")
    
    # 5. 竞价筛选（CTO第一斩）
    print("\n【Step 5】CTO第一斩（竞价筛选）...")
    df_auction = df.copy()
    df_auction = df_auction[df_auction['open'] > 0]
    df_auction = df_auction[df_auction['volume'] >= 1000]  # 竞价>=1000手
    df_auction = df_auction[df_auction['open'] >= df_auction['prev_close'] * 0.98]  # 不低开
    print(f"第一斩后: {len(df_auction)} 只")
    
    if df_auction.empty:
        print("❌ 第一斩后为空，跳过后续诊断")
        return
    
    # 6. TrueDictionary预热
    print("\n【Step 6】TrueDictionary预热...")
    today = now.strftime('%Y%m%d')
    true_dict = get_true_dictionary()
    true_dict.warmup(df_auction['stock_code'].tolist(), target_date=today, force=True)
    
    # 7. 计算量比
    print("\n【Step 7】计算量比...")
    df_auction['avg_volume_5d'] = df_auction['stock_code'].map(true_dict.get_avg_volume_5d)
    df_auction['avg_turnover_5d'] = df_auction['stock_code'].map(true_dict.get_avg_turnover_5d)
    df_auction['float_volume'] = df_auction['stock_code'].map(true_dict.get_float_volume)
    df_auction['prev_close'] = df_auction['stock_code'].map(true_dict.get_prev_close)
    
    print(f"  avg_volume_5d > 0: {(df_auction['avg_volume_5d'] > 0).sum()}/{len(df_auction)}")
    print(f"  avg_turnover_5d > 0: {(df_auction['avg_turnover_5d'] > 0).sum()}/{len(df_auction)}")
    print(f"  float_volume > 0: {(df_auction['float_volume'] > 0).sum()}/{len(df_auction)}")
    
    # 【诊断】检查volume单位
    print("\n📊 单位诊断（第一只股票）:")
    first_code = df_auction['stock_code'].iloc[0]
    print(f"  股票: {first_code}")
    print(f"  快照volume (原始): {df_auction['volume'].iloc[0]}")
    print(f"  快照volume单位: 手 (QMT快照)")
    print(f"  avg_volume_5d: {true_dict.get_avg_volume_5d(first_code)}")
    print(f"  avg_volume_5d单位: 手 (TrueDictionary)")
    
    # 计算量比
    df_auction['volume_gu'] = df_auction['volume'] * 100  # 手→股
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    raw_minutes = (now - market_open).total_seconds() / 60
    minutes_passed = max(5, min(raw_minutes, 240))
    
    print(f"\n  已交易分钟: {minutes_passed:.0f}")
    
    df_auction['estimated_full_day_volume'] = df_auction['volume_gu'] / minutes_passed * 240
    # 【CTO修复】avg_volume_5d单位是手，需要乘100转成股
    df_auction['avg_volume_5d_gu'] = df_auction['avg_volume_5d'] * 100
    df_auction['volume_ratio'] = df_auction['estimated_full_day_volume'] / df_auction['avg_volume_5d_gu'].replace(0, pd.NA)
    df_auction['current_turnover'] = (df_auction['volume_gu'] / df_auction['float_volume'].replace(0, pd.NA)) * 100
    df_auction['avg_amount_5d'] = df_auction['avg_volume_5d'] * df_auction['prev_close'] * 100
    
    print(f"  volume_ratio有效: {df_auction['volume_ratio'].notna().sum()}/{len(df_auction)}")
    print(f"  current_turnover有效: {df_auction['current_turnover'].notna().sum()}/{len(df_auction)}")
    print(f"  avg_amount_5d > 0: {(df_auction['avg_amount_5d'] > 0).sum()}/{len(df_auction)}")
    
    # 8. dropna检查
    print("\n【Step 8】dropna前检查...")
    pre_dropna = len(df_auction)
    df_auction = df_auction.dropna(subset=['volume_ratio', 'avg_turnover_5d', 'avg_amount_5d'])
    print(f"  dropna前: {pre_dropna} 只")
    print(f"  dropna后: {len(df_auction)} 只")
    
    if df_auction.empty:
        print("❌ dropna后为空！检查原因...")
        # 诊断哪列导致问题
        print("\n【诊断】逐列检查NaN...")
        for col in ['volume_ratio', 'avg_turnover_5d', 'avg_amount_5d']:
            nan_count = df_auction[col].isna().sum() if col in df_auction.columns else 'N/A'
            print(f"  {col}: NaN数量 = {nan_count}")
        return
    
    # 9. 多维过滤
    print("\n【Step 9】多维过滤...")
    
    # 先看量比分布
    print("\n📊 量比分布:")
    print(f"  最小值: {df_auction['volume_ratio'].min():.2f}")
    print(f"  25%分位: {df_auction['volume_ratio'].quantile(0.25):.2f}")
    print(f"  50%分位: {df_auction['volume_ratio'].quantile(0.50):.2f}")
    print(f"  75%分位: {df_auction['volume_ratio'].quantile(0.75):.2f}")
    print(f"  95%分位: {df_auction['volume_ratio'].quantile(0.95):.2f}")
    print(f"  最大值: {df_auction['volume_ratio'].max():.2f}")
    
    # 量比分档统计
    print("\n📊 量比分档:")
    for threshold in [1.0, 2.0, 3.0, 5.0, 10.0, 20.0]:
        count = (df_auction['volume_ratio'] >= threshold).sum()
        print(f"  >= {threshold}x: {count} 只 ({count/len(df_auction)*100:.1f}%)")
    
    min_volume_multiplier = 3.0
    min_avg_amount_5d = 30000000.0  # 3000万
    min_avg_turnover_5d = 1.0       # 1%
    max_open_turnover = 30.0
    
    print(f"  量比 >= {min_volume_multiplier}x")
    print(f"  5日均额 >= {min_avg_amount_5d/10000:.0f}万")
    print(f"  5日均换手 >= {min_avg_turnover_5d}%")
    print(f"  开盘换手 < {max_open_turnover}%")
    
    mask = (
        (df_auction['volume_ratio'] >= min_volume_multiplier) &
        (df_auction['avg_amount_5d'] >= min_avg_amount_5d) &
        (df_auction['avg_turnover_5d'] >= min_avg_turnover_5d) &
        (df_auction['current_turnover'] < max_open_turnover)
    )
    
    filtered = df_auction[mask]
    print(f"\n📊 最终筛选结果: {len(filtered)} 只")
    
    if len(filtered) > 0:
        print("\n前10只股票:")
        print(filtered[['stock_code', 'volume_ratio', 'avg_amount_5d', 'avg_turnover_5d', 'current_turnover']].head(10).to_string())
    
    print("\n" + "=" * 60)
    print("✅ 诊断完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
