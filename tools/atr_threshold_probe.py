"""
ATR阈值探测工具 - 用实盘数据说话
用法: python tools/atr_threshold_probe.py [日期]
默认用今天，诊断振幅/ATR20的分布，找出天然分界点
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from xtquant import xtdata
from logic.utils.calendar_utils import get_nth_previous_trading_day, get_latest_completed_trading_day

def main():
    # 目标日期
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = get_latest_completed_trading_day()
    
    hist_start = get_nth_previous_trading_day(target_date, 25)
    
    print("=" * 60)
    print(f"ATR阈值探测 - {target_date}")
    print("=" * 60)
    
    # 连接QMT
    port = 58610
    xtdata.connect(port=port)
    
    # 获取股票列表
    stocks = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"全市场股票: {len(stocks)} 只")
    print(f"历史窗口: {hist_start} ~ {target_date}")
    print()
    
    rows = []
    errors = 0
    
    for i, stock in enumerate(stocks):
        try:
            d = xtdata.get_local_data(
                ['high', 'low', 'close', 'volume'],
                [stock], '1d', hist_start, target_date
            )
            if not d or stock not in d or d[stock].empty or len(d[stock]) < 6:
                continue
            
            df = d[stock].copy()
            hist = df.iloc[:-1]  # 历史数据（不含今天）
            pre_close = hist['close'].shift(1)
            
            # 计算20日ATR基准
            atr_20d = ((hist['high'] - hist['low']) / pre_close.replace(0, np.nan)).mean()
            
            today = df.iloc[-1]
            
            # 【Bug 6修复】验证日期：最后一行必须是target_date
            actual_date = str(df.index[-1])[:8]
            if actual_date != target_date:
                continue  # 跳过数据不完整的股票
            
            if today['close'] <= 0 or atr_20d <= 0 or np.isnan(atr_20d):
                continue
            
            # 今日振幅
            amplitude = (today['high'] - today['low']) / today['close']
            ratio = amplitude / atr_20d  # 核心：今日振幅/自身ATR
            
            # 量比
            avg_vol = df['volume'].iloc[-6:-1].mean()
            vol_ratio = today['volume'] / avg_vol if avg_vol > 0 else 0
            
            # 涨跌幅
            change_pct = (today['close'] - hist['close'].iloc[-1]) / hist['close'].iloc[-1] * 100
            
            rows.append({
                'stock': stock,
                'amplitude_pct': round(amplitude * 100, 2),
                'atr_20d_pct': round(atr_20d * 100, 2),
                'atr_ratio': round(ratio, 2),
                'vol_ratio': round(vol_ratio, 2),
                'change_pct': round(change_pct, 2),
            })
        except Exception as e:
            errors += 1
            continue
        
        # 进度显示
        if (i + 1) % 500 == 0:
            print(f"  处理进度: {i+1}/{len(stocks)}")
    
    df_all = pd.DataFrame(rows).sort_values('atr_ratio', ascending=False)
    
    print()
    print("=" * 60)
    print(f"有效样本: {len(df_all)} 只 | 错误: {errors}")
    print("=" * 60)
    
    # ── 分布统计 ──
    print(f"\n【振幅/ATR20 分位数分布】")
    for p in [50, 75, 90, 95, 99]:
        v = df_all['atr_ratio'].quantile(p/100)
        print(f"  {p:2d}分位: {v:.2f}x")
    
    # ── 涨跌停分布 ──
    zt = df_all[df_all['change_pct'] >= 9.8]
    dt = df_all[df_all['change_pct'] <= -9.8]
    normal = df_all[(df_all['change_pct'] > -9.8) & (df_all['change_pct'] < 9.8)]
    
    print(f"\n【涨跌停 ATR倍数统计】")
    print(f"  涨停({len(zt):3d}只): 均值={zt['atr_ratio'].mean():.2f}x  中位数={zt['atr_ratio'].median():.2f}x")
    print(f"  跌停({len(dt):3d}只): 均值={dt['atr_ratio'].mean():.2f}x  中位数={dt['atr_ratio'].median():.2f}x")
    print(f"  普通({len(normal):3d}只): 均值={normal['atr_ratio'].mean():.2f}x  中位数={normal['atr_ratio'].median():.2f}x")
    
    # ── 不同阈值下的筛选数量 ──
    print(f"\n【不同ATR倍数阈值筛选数量】")
    for threshold in [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]:
        count = len(df_all[df_all['atr_ratio'] >= threshold])
        print(f"  >= {threshold}x: {count:4d}只 ({count/len(df_all)*100:.1f}%)")
    
    # ── 量比分布 ──
    print(f"\n【量比分布】")
    for threshold in [1.5, 2.0, 3.0, 5.0]:
        count = len(df_all[df_all['vol_ratio'] >= threshold])
        print(f"  >= {threshold}x: {count:4d}只 ({count/len(df_all)*100:.1f}%)")
    
    # ── Top30 异动股 ──
    print(f"\n【Top30 ATR倍数最高】")
    print(df_all.head(30)[['stock','amplitude_pct','atr_20d_pct','atr_ratio','vol_ratio','change_pct']].to_string(index=False))
    
    # ── 石油板块样本 ──
    oil = ['600028.SH', '601857.SH', '000096.SZ', '600339.SH', '601808.SH', '000554.SZ']
    oil_df = df_all[df_all['stock'].isin(oil)]
    if len(oil_df) > 0:
        print(f"\n【石油板块样本】")
        print(oil_df[['stock','amplitude_pct','atr_20d_pct','atr_ratio','vol_ratio','change_pct']].to_string(index=False))
    
    # ── 建议阈值 ──
    p75 = df_all['atr_ratio'].quantile(0.75)
    p90 = df_all['atr_ratio'].quantile(0.90)
    print(f"\n【建议阈值】")
    print(f"  保守(捕获前25%异动): atr_ratio >= {p75:.1f}x")
    print(f"  激进(捕获前10%异动): atr_ratio >= {p90:.1f}x")
    
    # 保存完整结果
    out = Path(f'data/atr_probe_{target_date}.csv')
    out.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_csv(out, index=False, encoding='utf-8-sig')
    print(f"\n完整结果已保存: {out}")


if __name__ == '__main__':
    main()
