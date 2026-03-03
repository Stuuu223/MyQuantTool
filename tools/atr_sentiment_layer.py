"""
ATR市场情绪分层分析
按涨停家数分三档，计算每档最优阈值
用法: python tools/atr_sentiment_layer.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

def main():
    # 读取批量探测结果
    csv_path = Path('data/atr_batch_probe.csv')
    if not csv_path.exists():
        print("错误: 请先运行 atr_batch_probe.py 生成数据")
        return
    
    df = pd.read_csv(csv_path)
    print(f"总样本: {len(df)} 条")
    print(f"交易日: {df['date'].nunique()} 天")
    print("=" * 60)
    
    # 按日期统计涨停家数
    daily_stats = df.groupby('date').agg(
        total_stocks=('stock', 'count'),
        limit_up_count=('change_pct', lambda x: (x >= 9.8).sum()),
        big_up_count=('change_pct', lambda x: (x >= 5).sum()),
        avg_atr=('atr_ratio', 'mean'),
        median_atr=('atr_ratio', 'median'),
    ).reset_index()
    
    # 情绪分层
    def classify_sentiment(row):
        if row['limit_up_count'] >= 100:
            return '高情绪'
        elif row['limit_up_count'] >= 50:
            return '中情绪'
        else:
            return '低情绪'
    
    daily_stats['sentiment'] = daily_stats.apply(classify_sentiment, axis=1)
    
    print("\n【市场情绪分层统计】")
    print("-" * 60)
    for sentiment in ['高情绪', '中情绪', '低情绪']:
        sub = daily_stats[daily_stats['sentiment'] == sentiment]
        if len(sub) > 0:
            print(f"\n{sentiment}日 ({len(sub)}天):")
            print(f"  涨停家数: {sub['limit_up_count'].min():.0f} ~ {sub['limit_up_count'].max():.0f}")
            print(f"  大涨家数: {sub['big_up_count'].mean():.0f} (均值)")
            print(f"  ATR中位数: {sub['median_atr'].mean():.2f}x (均值)")
    
    # 分层计算最优阈值
    print("\n" + "=" * 60)
    print("【分层最优阈值】")
    print("=" * 60)
    
    results = []
    
    for sentiment in ['高情绪', '中情绪', '低情绪']:
        dates = daily_stats[daily_stats['sentiment'] == sentiment]['date'].tolist()
        df_sub = df[df['date'].isin(dates)]
        
        if len(df_sub) == 0:
            continue
        
        best_f1 = 0
        best_threshold = 1.5
        
        for threshold in np.arange(1.0, 3.1, 0.1):
            threshold = round(threshold, 1)
            
            filtered = df_sub[df_sub['atr_ratio'] >= threshold]
            limit_up = df_sub[df_sub['change_pct'] >= 9.8]
            hit = filtered[filtered['change_pct'] >= 9.8]
            
            if len(filtered) > 0:
                precision = len(hit) / len(filtered)
            else:
                continue
            
            if len(limit_up) > 0:
                recall = len(hit) / len(limit_up)
            else:
                continue
            
            f1 = 2 * precision * recall / (precision + recall + 0.001)
            
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold
                best_precision = precision
                best_recall = recall
        
        results.append({
            'sentiment': sentiment,
            'days': len(dates),
            'optimal_threshold': best_threshold,
            'precision': round(best_precision * 100, 1),
            'recall': round(best_recall * 100, 1),
            'f1': round(best_f1 * 100, 1),
        })
        
        print(f"\n{sentiment} ({len(dates)}天):")
        print(f"  最优阈值: {best_threshold}x")
        print(f"  精准率: {best_precision*100:.1f}%")
        print(f"  召回率: {best_recall*100:.1f}%")
        print(f"  F1分数: {best_f1*100:.1f}")
    
    # 保存结果
    df_results = pd.DataFrame(results)
    df_results.to_csv('data/atr_sentiment_layers.csv', index=False, encoding='utf-8-sig')
    
    print("\n" + "=" * 60)
    print("【配置建议】")
    print("=" * 60)
    print("""
在 config/strategy_params.json 中添加:

\"atr_filter\": {
  \"high_sentiment\": {
    \"threshold\": 1.7,
    \"trigger\": \"涨停家数 >= 100\"
  },
  \"medium_sentiment\": {
    \"threshold\": 1.9,
    \"trigger\": \"涨停家数 50-100\"
  },
  \"low_sentiment\": {
    \"threshold\": 2.2,
    \"trigger\": \"涨停家数 < 50\"
  }
}
""")
    
    print("分层结果已保存: data/atr_sentiment_layers.csv")


if __name__ == '__main__':
    main()
