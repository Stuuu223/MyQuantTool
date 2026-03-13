# -*- coding: utf-8 -*-
"""
【CTO V155 智猪效应与暴力便车研究】

研究目标：
1. 计算量比92th + MFE 90th的收益极值分布
2. 解剖志特新材6天198%的物理特征
3. 实现智猪效应策略

Author: CTO Research
Date: 2026-03-14
"""

import json
import numpy as np
import os

def main():
    # 加载样本
    json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'validation', 'violent_samples_full.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        samples = json.load(f)
    
    print("=" * 70)
    print("【CTO V155 智猪效应与暴力便车研究】")
    print("=" * 70)
    
    # ===== 第一问：收益极值分布 =====
    print("\n【第一问：量比92th + MFE 90th 收益极值】")
    print("-" * 70)
    
    # 计算5日收益
    all_5d_returns = []
    high_return_samples = []
    
    for s in samples:
        t0 = s.get('t0', {})
        post = s.get('post_days', {})
        t0_close = t0.get('close', 0)
        t5 = post.get('t_plus_5', {}).get('close', 0)
        
        if t0_close > 0 and t5 > 0:
            r = (t5 / t0_close - 1) * 100
            all_5d_returns.append(r)
            
            if r > 50:
                high_return_samples.append({
                    'code': s['stock_code'],
                    'date': s['date'],
                    't5_return': r,
                    't0_is_limit': t0.get('is_limit_up', False),
                    't0_turnover': t0.get('turnover_pct', 0) or 0
                })
    
    print(f"总样本数: {len(all_5d_returns)}")
    print(f"5日收益>50%样本: {len(high_return_samples)}个 ({len(high_return_samples)/len(all_5d_returns)*100:.1f}%)")
    
    # 收益分布
    print(f"\n全样本5日收益分布:")
    print(f"  中位数: {np.median(all_5d_returns):+.2f}%")
    print(f"  P75: {np.percentile(all_5d_returns, 75):+.2f}%")
    print(f"  P90: {np.percentile(all_5d_returns, 90):+.2f}%")
    print(f"  P95: {np.percentile(all_5d_returns, 95):+.2f}%")
    print(f"  MAX: {max(all_5d_returns):+.1f}%")
    
    # 高收益样本特征
    if high_return_samples:
        returns = [s['t5_return'] for s in high_return_samples]
        limit_ratio = sum(1 for s in high_return_samples if s['t0_is_limit']) / len(high_return_samples) * 100
        avg_turnover = np.mean([s['t0_turnover'] * 100 for s in high_return_samples])
        
        print(f"\n高收益(>50%)样本特征:")
        print(f"  收益中位数: {np.median(returns):+.1f}%")
        print(f"  收益P90: {np.percentile(returns, 90):+.1f}%")
        print(f"  T0涨停比例: {limit_ratio:.1f}%")
        print(f"  T0平均换手: {avg_turnover:.2f}%")
    
    # ===== 第二问：志特新材解剖 =====
    print("\n" + "=" * 70)
    print("【第二问：志特新材 6天198% 暴力解剖】")
    print("=" * 70)
    
    zhite_samples = [s for s in samples if '300986' in s['stock_code'] or '志特' in s.get('stock_name', '')]
    
    if zhite_samples:
        for s in zhite_samples[:5]:
            t0 = s.get('t0', {})
            post = s.get('post_days', {})
            print(f"\n日期: {s['date']}")
            print(f"  T0收盘: {t0.get('close', 0):.2f}")
            print(f"  T0涨停: {t0.get('is_limit_up', False)}")
            print(f"  T0换手: {(t0.get('turnover_pct', 0) or 0)*100:.2f}%")
            
            for day in ['t_plus_1', 't_plus_3', 't_plus_5']:
                if day in post and post[day].get('close'):
                    r = (post[day]['close'] / t0.get('close', 1) - 1) * 100
                    print(f"  {day}: 收益{r:+.1f}%")
    else:
        print("未找到志特新材样本")
    
    # ===== 第三问：智猪效应 =====
    print("\n" + "=" * 70)
    print("【第三问：智猪效应实现方案】")
    print("=" * 70)
    
    print("""
【智猪博弈法则】

在A股这个食槽里：
┌─────────────────────────────────────────────────────┐
│  大猪（主力）必须花钱按踏板：                        │
│  - 扫平上方套牢盘                                    │
│  - 克服摩擦力拉升                                    │
│  - 成本：真金白银                                    │
├─────────────────────────────────────────────────────┤
│  小猪（量化系统）死守食槽边：                        │
│  - 绝不左侧建仓（不按踏板）                          │
│  - 等待大猪出汗信号                                  │
│  - 信号：量比92th + MFE 90th                         │
│  - 动作：毫秒级抢食                                  │
├─────────────────────────────────────────────────────┤
│  撤退信号（大猪派发）：                              │
│  - 量比仍高但MFE暴跌                                 │
│  - 高位放量滞涨                                      │
│  - L1探针：增量换手<0.2%                             │
└─────────────────────────────────────────────────────┘

【物理阈值配置】
- 入场：量比 >= 92th 且 MFE >= 90th
- 持仓：MFE >= 50th 且 sustain_ratio >= 1.0
- 出场：MFE < 30th 或 sustain_ratio < 0.5
""")
    
    # 最暴力的TOP10
    print("\n【5日收益TOP10】")
    print("-" * 70)
    sorted_samples = sorted(high_return_samples, key=lambda x: x['t5_return'], reverse=True)[:10]
    for i, s in enumerate(sorted_samples, 1):
        print(f"{i:2d}. {s['code']} {s['date']} 5日{s['t5_return']:+.1f}% 涨停{s['t0_is_limit']}")


def verify_cross_day_momentum(samples):
    """验证跨日势能遗传效果"""
    print("\n" + "=" * 70)
    print("【CTO V156 跨日势能遗传验尸】")
    print("=" * 70)
    
    # 分组：昨日涨停 vs 昨日非涨停
    yesterday_limit = []  # T-1涨停，T0表现
    yesterday_normal = [] # T-1非涨停，T0表现
    
    for s in samples:
        t0 = s.get('t0', {})
        t_minus_1 = s.get('t_minus_1', {})
        post = s.get('post_days', {})
        
        if not t0 or not t_minus_1:
            continue
            
        t0_close = t0.get('close', 0)
        t1_close = post.get('t_plus_1', {}).get('close', 0)
        
        if t0_close <= 0 or t1_close <= 0:
            continue
            
        t1_return = (t1_close / t0_close - 1) * 100
        
        record = {
            'code': s['stock_code'],
            'date': s['date'],
            't1_return': t1_return,
            't0_limit': t0.get('is_limit_up', False)
        }
        
        if t_minus_1.get('is_limit_up', False):
            yesterday_limit.append(record)
        else:
            yesterday_normal.append(record)
    
    print(f"\n昨日涨停样本: {len(yesterday_limit)}个")
    print(f"昨日非涨停样本: {len(yesterday_normal)}个")
    
    if yesterday_limit:
        returns = [r['t1_return'] for r in yesterday_limit]
        print(f"\n【昨日涨停组】次日表现:")
        print(f"  次日收益中位数: {np.median(returns):+.2f}%")
        print(f"  次日收益均值: {np.mean(returns):+.2f}%")
        print(f"  次日正收益比例: {sum(1 for r in returns if r > 0)/len(returns)*100:.1f}%")
    
    if yesterday_normal:
        returns = [r['t1_return'] for r in yesterday_normal]
        print(f"\n【昨日非涨停组】次日表现:")
        print(f"  次日收益中位数: {np.median(returns):+.2f}%")
        print(f"  次日收益均值: {np.mean(returns):+.2f}%")
        print(f"  次日正收益比例: {sum(1 for r in returns if r > 0)/len(returns)*100:.1f}%")
    
    # 溢出乘数验证
    print("\n【溢出乘数公式验证】")
    print("公式: overflow_multiplier = 1.0 + log10(1 + yesterday_vol_ratio) * 2.0")
    print("-" * 50)
    for vol_ratio in [1.0, 2.0, 5.0, 10.0, 20.0]:
        mult = 1.0 + np.log10(1 + vol_ratio) * 2.0
        print(f"  昨日量比={vol_ratio}x → 溢出乘数={mult:.2f}x")


if __name__ == '__main__':
    json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'validation', 'violent_samples_full.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        samples = json.load(f)
    
    main()
    verify_cross_day_momentum(samples)
