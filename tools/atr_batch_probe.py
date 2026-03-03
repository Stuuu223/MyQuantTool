"""
ATR批量探测 - 多日数据生成精准率×召回率曲线
用法: python tools/atr_batch_probe.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from xtquant import xtdata
from logic.utils.calendar_utils import get_trading_days_between

def probe_single_day(target_date: str) -> pd.DataFrame:
    """单日ATR探测"""
    from logic.utils.calendar_utils import get_nth_previous_trading_day
    
    hist_start = get_nth_previous_trading_day(target_date, 25)
    
    stocks = xtdata.get_stock_list_in_sector('沪深A股')
    rows = []
    
    for stock in stocks:
        try:
            d = xtdata.get_local_data(
                ['high', 'low', 'close', 'volume'],
                [stock], '1d', hist_start, target_date
            )
            if not d or stock not in d or d[stock].empty or len(d[stock]) < 6:
                continue
            
            df = d[stock].copy()
            hist = df.iloc[:-1]
            pre_close = hist['close'].shift(1)
            atr_20d = ((hist['high'] - hist['low']) / pre_close.replace(0, np.nan)).mean()
            
            today = df.iloc[-1]
            if today['close'] <= 0 or atr_20d <= 0 or np.isnan(atr_20d):
                continue
            
            amplitude = (today['high'] - today['low']) / today['close']
            atr_ratio = amplitude / atr_20d
            
            avg_vol = df['volume'].iloc[-6:-1].mean()
            vol_ratio = today['volume'] / avg_vol if avg_vol > 0 else 0
            
            change_pct = (today['close'] - hist['close'].iloc[-1]) / hist['close'].iloc[-1] * 100
            
            rows.append({
                'stock': stock,
                'date': target_date,
                'amplitude_pct': round(amplitude * 100, 2),
                'atr_20d_pct': round(atr_20d * 100, 2),
                'atr_ratio': round(atr_ratio, 2),
                'vol_ratio': round(vol_ratio, 2),
                'change_pct': round(change_pct, 2),
            })
        except:
            continue
    
    return pd.DataFrame(rows)


def main():
    # 接收用户参数
    if len(sys.argv) >= 3:
        start_date = sys.argv[1]  # 20260206
        end_date = sys.argv[2]    # 20260302
    else:
        print("Usage: python tools/atr_batch_probe.py 20260206 20260302")
        return
    
    xtdata.connect(port=58610)
    
    # 使用封装好的交易日历函数
    trading_days = get_trading_days_between(start_date, end_date)
    
    print(f"ATR批量探测: {len(trading_days)} 个交易日")
    print(f"日期范围: {trading_days[0]} ~ {trading_days[-1]}")
    print("=" * 60)
    
    all_rows = []
    
    for i, date in enumerate(trading_days):
        print(f"[{i+1}/{len(trading_days)}] {date}...", end=' ', flush=True)
        df = probe_single_day(date)
        all_rows.append(df)
        print(f"{len(df)}只")
    
    df_all = pd.concat(all_rows, ignore_index=True)
    
    # 保存
    out = Path('data/atr_batch_probe.csv')
    out.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_csv(out, index=False, encoding='utf-8-sig')
    print(f"\n总样本: {len(df_all)} 条")
    print(f"已保存: {out}")
    
    # ========== 回测分析 ==========
    print("\n" + "=" * 60)
    print("ATR阈值回测分析")
    print("=" * 60)
    
    # 按日期分组计算精准率和召回率
    results = []
    
    for threshold in np.arange(1.0, 3.1, 0.1):
        threshold = round(threshold, 1)
        
        precisions = []
        recalls = []
        
        for date in trading_days:
            df_day = df_all[df_all['date'] == date]
            if len(df_day) == 0:
                continue
            
            # ATR过滤后的股票
            filtered = df_day[df_day['atr_ratio'] >= threshold]
            
            # 大涨股票（change_pct >= 5%）
            big_up = df_day[df_day['change_pct'] >= 5]
            
            # 涨停股票
            limit_up = df_day[df_day['change_pct'] >= 9.8]
            
            # 命中：ATR >= threshold 且大涨
            hit_big_up = filtered[filtered['change_pct'] >= 5]
            hit_limit_up = filtered[filtered['change_pct'] >= 9.8]
            
            # 精准率：过滤后命中大涨的比例
            if len(filtered) > 0:
                precision_big = len(hit_big_up) / len(filtered)
                precision_limit = len(hit_limit_up) / len(filtered)
            else:
                precision_big = 0
                precision_limit = 0
            
            # 召回率：大涨股票被捕获的比例
            if len(big_up) > 0:
                recall_big = len(hit_big_up) / len(big_up)
            else:
                recall_big = 0
            
            if len(limit_up) > 0:
                recall_limit = len(hit_limit_up) / len(limit_up)
            else:
                recall_limit = 0
            
            precisions.append((precision_big, precision_limit))
            recalls.append((recall_big, recall_limit))
        
        # 计算均值
        avg_prec_big = np.mean([p[0] for p in precisions])
        avg_prec_limit = np.mean([p[1] for p in precisions])
        avg_recall_big = np.mean([r[0] for r in recalls])
        avg_recall_limit = np.mean([r[1] for r in recalls])
        
        # 平均过滤数量
        avg_filter = np.mean([len(df_all[(df_all['date'] == d) & (df_all['atr_ratio'] >= threshold)]) for d in trading_days])
        
        results.append({
            'threshold': threshold,
            'precision_big_up': round(avg_prec_big * 100, 1),
            'precision_limit_up': round(avg_prec_limit * 100, 1),
            'recall_big_up': round(avg_recall_big * 100, 1),
            'recall_limit_up': round(avg_recall_limit * 100, 1),
            'avg_filter_count': round(avg_filter),
        })
    
    df_results = pd.DataFrame(results)
    
    print("\n【精准率×召回率曲线】")
    print("阈值  | 大涨精准% | 涨停精准% | 大涨召回% | 涨停召回% | 平均过滤")
    print("-" * 65)
    for _, row in df_results.iterrows():
        print(f"{row['threshold']:.1f}x | {row['precision_big_up']:8.1f} | {row['precision_limit_up']:8.1f} | {row['recall_big_up']:8.1f} | {row['recall_limit_up']:8.1f} | {row['avg_filter_count']:6.0f}")
    
    # 最优阈值
    df_results['f1_big'] = 2 * df_results['precision_big_up'] * df_results['recall_big_up'] / (df_results['precision_big_up'] + df_results['recall_big_up'] + 0.01)
    df_results['f1_limit'] = 2 * df_results['precision_limit_up'] * df_results['recall_limit_up'] / (df_results['precision_limit_up'] + df_results['recall_limit_up'] + 0.01)
    
    best_big = df_results.loc[df_results['f1_big'].idxmax()]
    best_limit = df_results.loc[df_results['f1_limit'].idxmax()]
    
    print("\n【最优阈值】")
    print(f"捕获大涨(>=5%)最优: {best_big['threshold']:.1f}x (F1={best_big['f1_big']:.1f})")
    print(f"捕获涨停(>=9.8%)最优: {best_limit['threshold']:.1f}x (F1={best_limit['f1_limit']:.1f})")
    
    # ========== 周几效应 ==========
    print("\n" + "=" * 60)
    print("周几效应分析")
    print("=" * 60)
    
    df_all['weekday'] = pd.to_datetime(df_all['date']).dt.dayofweek
    weekday_names = ['周一', '周二', '周三', '周四', '周五']
    
    print("周几  | 样本数 | ATR中位数 | 涨停数 | 涨停ATR中位")
    print("-" * 55)
    for i in range(5):
        df_w = df_all[df_all['weekday'] == i]
        zt = df_w[df_w['change_pct'] >= 9.8]
        print(f"{weekday_names[i]} | {len(df_w):6d} | {df_w['atr_ratio'].median():.2f}x    | {len(zt):5d} | {zt['atr_ratio'].median():.2f}x")
    
    # 保存结果
    df_results.to_csv('data/atr_backtest_results.csv', index=False, encoding='utf-8-sig')
    print(f"\n回测结果已保存: data/atr_backtest_results.csv")


if __name__ == '__main__':
    main()
