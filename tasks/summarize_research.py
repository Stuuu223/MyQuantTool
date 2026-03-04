#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
换手率研究成果汇总
"""

import json
import pandas as pd
from pathlib import Path

VALIDATION_DIR = Path('C:/Users/pc/Desktop/Astock/MyQuantTool/data/validation')

# 汇总所有研究成果
summary = {
    'generated_at': '2026-03-05',
    'total_samples': {},
    'studies': {},
    'config_recommendations': {}
}

# 1. 正向验证
with open(VALIDATION_DIR / 'turnover_5d_avg_returns.json', 'r', encoding='utf-8') as f:
    forward_data = json.load(f)
    
summary['total_samples']['forward_validation'] = forward_data['total_events']
summary['studies']['forward_validation'] = {
    'description': '5日均换手率分档 vs 后续收益（1-10日）',
    'date_range': forward_data['date_range'],
    'buckets': forward_data['buckets'],
    'best_bucket': forward_data['best_bucket'],
    'worst_bucket': forward_data['worst_bucket'],
    'conclusion': '最佳换手区间3-5%，10日收益+1.68%，胜率50%。>70%为死亡换手线，10日亏损-14.67%。'
}

# 2. 反向验证
with open(VALIDATION_DIR / 'turnover_reverse_analysis.json', 'r', encoding='utf-8') as f:
    reverse_data = json.load(f)

total_reverse = sum(int(v) for v in reverse_data['total_samples'].values())
summary['total_samples']['reverse_validation'] = total_reverse
summary['studies']['reverse_validation'] = {
    'description': '最高收益股票的换手率分布（反推）',
    'key_findings': {
        '1d_top5': reverse_data['results']['1']['top_5%'],
        '5d_top5': reverse_data['results']['5']['top_5%'],
        '10d_top5': reverse_data['results']['10']['top_5%'],
        '30d_top5': reverse_data['results']['30']['top_5%']
    },
    'conclusion': '前5%高收益股（30日+59.52%）换手中位仅2.53%，主要分布在3-5%和1-2%区间。持有期越长，高收益股换手率越低。'
}

# 3. 极端高收益分析
with open(VALIDATION_DIR / 'turnover_extreme_analysis.json', 'r', encoding='utf-8') as f:
    extreme_data = json.load(f)

total_extreme = sum(d['sample_count'] for d in extreme_data['results'].values())
summary['total_samples']['extreme_analysis'] = total_extreme
summary['studies']['extreme_analysis'] = {
    'description': '极端高收益样本分析（右侧起爆哲学）',
    'key_findings': {
        '5d_80pct': extreme_data['results'].get('5天80%+', {}),
        '10d_150pct': extreme_data['results'].get('10天150%+', {}),
        '20d_200pct': extreme_data['results'].get('20天200%+', {}),
        '30d_300pct': extreme_data['results'].get('30天300%+', {})
    },
    'conclusion': '收益越高换手率越低。30天300%+样本换手中位仅1.54%，33%在1-2%区间。真正的右侧起爆特征是低换手率。'
}

# config建议
summary['config_recommendations'] = {
    'sweet_spot_min': {
        'current': 8.0,
        'recommended': 1.0,
        'reason': '极端高收益股（300%+）33%在1-2%区间'
    },
    'sweet_spot_max': {
        'current': 15.0,
        'recommended': 5.0,
        'reason': '正向验证最佳区间3-5%，反向验证高收益股中位数2.53%'
    },
    'turnover_rate_max': {
        'current': 150.0,
        'recommended': 70.0,
        'reason': '70%以上换手率10日亏损-14.67%，胜率仅23.3%'
    }
}

# 保存汇总JSON
with open(VALIDATION_DIR / 'turnover_research_summary.json', 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print('✅ JSON汇总已保存: turnover_research_summary.json')

# 生成CSV汇总
rows = []

# 正向验证数据
for bucket in forward_data['buckets']:
    rows.append({
        'study': '正向验证',
        'category': bucket['bucket'],
        'sample_count': bucket['sample_count'],
        'return_10d': bucket['returns'].get('10d'),
        'win_rate_3d': bucket.get('win_rate_3d'),
        'avg_turnover': None,
        'median_turnover': None,
        'note': f"换手率区间 {bucket['bucket']}"
    })

# 反向验证数据（关键结果）
for days in ['1', '5', '10', '30']:
    if days in reverse_data['results']:
        for pct in ['top_5%', 'top_10%']:
            if pct in reverse_data['results'][days]:
                d = reverse_data['results'][days][pct]
                rows.append({
                    'study': '反向验证',
                    'category': f"{days}日前{pct}",
                    'sample_count': None,
                    'return_10d': d['avg_return'],
                    'win_rate_3d': None,
                    'avg_turnover': d['avg_turnover'],
                    'median_turnover': d['median_turnover'],
                    'note': f"高收益股换手分布"
                })

# 极端分析数据
for desc, data in extreme_data['results'].items():
    bucket_str = ', '.join([f"{k}:{v}%" for k, v in list(data['bucket_distribution'].items())[:3]])
    rows.append({
        'study': '极端分析',
        'category': desc,
        'sample_count': data['sample_count'],
        'return_10d': data['avg_return'],
        'win_rate_3d': None,
        'avg_turnover': data['avg_turnover'],
        'median_turnover': data['median_turnover'],
        'note': bucket_str
    })

df = pd.DataFrame(rows)
df.to_csv(VALIDATION_DIR / 'turnover_research_summary.csv', index=False, encoding='utf-8-sig')
print('✅ CSV汇总已保存: turnover_research_summary.csv')

# 打印汇总
print('\n' + '='*80)
print('换手率研究成果汇总')
print('='*80)
print(f"正向验证样本: {forward_data['total_events']:,}")
print(f"反向验证样本: {total_reverse:,}")
print(f"极端分析样本: {total_extreme:,}")
print('='*80)
print("\n【核心发现】")
print("1. 最佳换手区间：1-5%（而非原config的8-15%）")
print("2. 死亡换手线：>70%（10日亏损-14.67%）")
print("3. 右侧起爆特征：低换手率（中位数1.54-2.53%）")
print("\n【config建议】")
print("  sweet_spot_min: 8 → 1")
print("  sweet_spot_max: 15 → 5")
print("  turnover_rate_max: 150 → 70")