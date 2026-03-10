#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTO数据飞轮：参数寻优分析器 V2 (Physics-Constrained)
====================================================
职责：基于features.csv，通过物理学约束寻找最优分割面

CTO V2核心修正：
1. raw_sustain下限强制>=1.1（必须溢出历史均值，杜绝0.42弱智阈值）
2. MFE方向必须是>=（越大越好，代表抛压真空）
3. 使用阶梯分桶阻尼而非线性衰减（24样本不够统计显著性）
4. 多维交叉拦截：volume_ratio>3.0且mfe<1.2则一票否决

Author: AI开发专家团队 (CTO V2修正版)
Date: 2026-03-10
Version: V2.0.0
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
import logging
import json

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# CTO物理约束铁律 - 绝对不可违反
# ============================================================================
PHYSICS_CONSTRAINTS = {
    # raw_sustain必须溢出历史均值，下限1.1
    'raw_sustain_min': 1.1,
    
    # MFE方向：>=（越大越好，代表抛压真空）
    'mfe_direction': 'above',
    'mfe_min': 0.5,  # 最低效率底线
    
    # 市值阶梯阻尼（替代线性衰减）
    'cap_damping_buckets': {
        '<50亿': 1.0,    # 微盘无衰减
        '50-100亿': 0.9,  # 小盘轻微衰减
        '100-200亿': 0.8, # 中盘衰减
        '200-500亿': 0.7, # 大盘明显衰减
        '>500亿': 0.6,    # 超大盘强衰减
    },
    
    # 多维交叉拦截
    'cross_rejection': {
        'volume_ratio_max': 3.0,  # 量比>3.0且MFE<1.2=一票否决
        'mfe_warning': 1.2,
    },
}


def load_features(filepath: str = 'data/validation/features.csv') -> pd.DataFrame:
    """加载特征数据"""
    df = pd.read_csv(filepath)
    logger.info(f"[加载特征] 共{len(df)}个样本")
    return df


def analyze_distribution(df: pd.DataFrame) -> Dict:
    """
    分析特征分布，寻找真龙vs骗炮的分界线
    """
    true_dragons = df[df['label'] == 1]
    traps = df[df['label'] == 0]
    
    results = {}
    
    key_features = [
        'float_market_cap_yi',
        'inflow_ratio_pct', 
        'mfe',
        'raw_sustain',
        'volume_ratio',
        'amplitude_pct',
        'price_momentum',
        'flow_15min_pct'
    ]
    
    print("\n" + "=" * 70)
    print("特征分布分析 - 真龙 vs 骗炮")
    print("=" * 70)
    
    for feat in key_features:
        if feat not in df.columns:
            continue
            
        true_vals = true_dragons[feat].dropna()
        trap_vals = traps[feat].dropna()
        
        true_mean = true_vals.mean()
        true_std = true_vals.std()
        trap_mean = trap_vals.mean()
        trap_std = trap_vals.std()
        
        if true_std + trap_std > 0:
            separation = abs(true_mean - trap_mean) / (true_std + trap_std)
        else:
            separation = 0
        
        results[feat] = {
            'true_mean': true_mean,
            'true_std': true_std,
            'trap_mean': trap_mean,
            'trap_std': trap_std,
            'separation': separation
        }
        
        print(f"\n{feat}:")
        print(f"  真龙: {true_mean:.2f} ± {true_std:.2f}")
        print(f"  骗炮: {trap_mean:.2f} ± {trap_std:.2f}")
        print(f"  区分度: {separation:.2f}")
    
    return results


def find_optimal_threshold_with_constraints(
    df: pd.DataFrame, 
    feature: str,
    min_value: Optional[float] = None,
    direction: Optional[str] = None
) -> Dict:
    """
    【CTO V2】带物理约束的阈值寻优
    
    Args:
        df: 特征数据
        feature: 特征名
        min_value: 最小阈值下限（物理约束）
        direction: 方向约束 'above' 或 'below'
    """
    if feature not in df.columns:
        return {}
    
    values = df[feature].dropna()
    labels = df.loc[values.index, 'label']
    
    # 应用物理约束下限
    if min_value is not None:
        search_min = max(values.min(), min_value)
    else:
        search_min = values.min()
    
    # 网格搜索
    thresholds = np.linspace(search_min, values.max(), 100)
    best_threshold = None
    best_f1 = 0
    best_direction = direction if direction else 'above'
    
    # 如果方向已约束，只搜索该方向
    directions = [best_direction] if direction else ['above', 'below']
    
    for threshold in thresholds:
        for dir_test in directions:
            if dir_test == 'above':
                preds = (values >= threshold).astype(int)
            else:
                preds = (values <= threshold).astype(int)
            
            tp = ((preds == 1) & (labels == 1)).sum()
            fp = ((preds == 1) & (labels == 0)).sum()
            fn = ((preds == 0) & (labels == 1)).sum()
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold
                best_direction = dir_test
    
    return {
        'feature': feature,
        'threshold': best_threshold,
        'direction': best_direction,
        'f1_score': best_f1,
        'physics_constrained': min_value is not None or direction is not None
    }


def apply_cap_damping(row: pd.Series) -> float:
    """
    【CTO V2】应用阶梯市值阻尼
    
    替代线性衰减，因为24个样本不够统计显著性
    """
    cap = row.get('float_market_cap_yi', 0)
    raw_sustain = row.get('raw_sustain', 0)
    
    if cap <= 0 or raw_sustain <= 0:
        return 0
    
    buckets = PHYSICS_CONSTRAINTS['cap_damping_buckets']
    
    if cap < 50:
        damper = buckets['<50亿']
    elif cap < 100:
        damper = buckets['50-100亿']
    elif cap < 200:
        damper = buckets['100-200亿']
    elif cap < 500:
        damper = buckets['200-500亿']
    else:
        damper = buckets['>500亿']
    
    return raw_sustain * damper


def apply_cross_rejection(row: pd.Series) -> Tuple[bool, str]:
    """
    【CTO V2】多维交叉拦截
    
    返回: (是否拦截, 拦截原因)
    """
    volume_ratio = row.get('volume_ratio', 0)
    mfe = row.get('mfe', 0)
    inflow_ratio = row.get('inflow_ratio_pct', 0)
    
    cross = PHYSICS_CONSTRAINTS['cross_rejection']
    
    # 规则1: 天量滞涨陷阱
    if volume_ratio > cross['volume_ratio_max'] and mfe < cross['mfe_warning']:
        return True, f"天量滞涨陷阱: volume_ratio={volume_ratio:.2f} > {cross['volume_ratio_max']} 且 mfe={mfe:.2f} < {cross['mfe_warning']}"
    
    # 规则2: 虚假流入陷阱（高流入但低效率）
    if inflow_ratio > 10.0 and mfe < 0.8:
        return True, f"虚假流入陷阱: inflow={inflow_ratio:.2f}% 但 mfe={mfe:.2f} < 0.8"
    
    return False, ""


def analyze_with_physics_constraints(df: pd.DataFrame) -> Dict:
    """
    【CTO V2】带物理约束的综合分析
    """
    print("\n" + "=" * 70)
    print("CTO V2 物理约束寻优")
    print("=" * 70)
    
    print(f"\n[物理约束铁律]")
    print(f"  raw_sustain下限: >= {PHYSICS_CONSTRAINTS['raw_sustain_min']}")
    print(f"  MFE方向: {PHYSICS_CONSTRAINTS['mfe_direction']} (越大越好)")
    print(f"  市值阶梯阻尼: {PHYSICS_CONSTRAINTS['cap_damping_buckets']}")
    print(f"  交叉拦截: volume_ratio>{PHYSICS_CONSTRAINTS['cross_rejection']['volume_ratio_max']} 且 mfe<{PHYSICS_CONSTRAINTS['cross_rejection']['mfe_warning']} = 一票否决")
    
    results = {}
    
    # 1. raw_sustain - 带下限约束
    print("\n[1] raw_sustain 阈值寻优（下限约束>=1.1）")
    result = find_optimal_threshold_with_constraints(
        df, 'raw_sustain',
        min_value=PHYSICS_CONSTRAINTS['raw_sustain_min'],
        direction='above'  # 必须>=方向
    )
    results['raw_sustain'] = result
    print(f"    最优阈值: >= {result['threshold']:.2f}, F1={result['f1_score']:.2f}")
    
    # 2. MFE - 带方向约束
    print("\n[2] MFE 阈值寻优（方向约束：越大越好）")
    result = find_optimal_threshold_with_constraints(
        df, 'mfe',
        min_value=PHYSICS_CONSTRAINTS['mfe_min'],
        direction='above'  # 必须>=方向
    )
    results['mfe'] = result
    print(f"    最优阈值: >= {result['threshold']:.2f}, F1={result['f1_score']:.2f}")
    
    # 3. volume_ratio - 天量警示（<=方向，量比太高是坏事）
    print("\n[3] volume_ratio 阈值寻优（方向约束：<=更好）")
    result = find_optimal_threshold_with_constraints(
        df, 'volume_ratio',
        direction='below'  # 量比太高是天量陷阱
    )
    results['volume_ratio'] = result
    print(f"    最优阈值: <= {result['threshold']:.2f}, F1={result['f1_score']:.2f}")
    
    # 4. 应用阶梯阻尼后的sustain
    print("\n[4] 应用阶梯市值阻尼后的效果")
    df['adjusted_sustain'] = df.apply(apply_cap_damping, axis=1)
    result = find_optimal_threshold_with_constraints(
        df, 'adjusted_sustain',
        min_value=PHYSICS_CONSTRAINTS['raw_sustain_min'] * 0.8,  # 阻尼后略微放宽
        direction='above'
    )
    results['adjusted_sustain'] = result
    print(f"    阻尼后最优阈值: >= {result['threshold']:.2f}, F1={result['f1_score']:.2f}")
    
    # 5. 多维交叉拦截验证
    print("\n[5] 多维交叉拦截验证")
    rejected = 0
    for idx, row in df.iterrows():
        is_rejected, reason = apply_cross_rejection(row)
        if is_rejected:
            rejected += 1
            label = '真龙' if row['label'] == 1 else '骗炮'
            print(f"    [{label}] {row.get('stock_code', 'N/A')} 被拦截: {reason}")
    print(f"    共拦截 {rejected} 个样本")
    
    return results


def generate_physics_constrained_config(df: pd.DataFrame, results: Dict) -> Dict:
    """
    【CTO V2】生成带物理约束的配置建议
    """
    print("\n" + "=" * 70)
    print("CTO V2 配置建议 - 基于物理约束")
    print("=" * 70)
    
    recommendations = {
        'kinetic_physics': {
            'raw_sustain_min': results.get('raw_sustain', {}).get('threshold', 1.1),
            'mfe_min': results.get('mfe', {}).get('threshold', 0.5),
            'volume_ratio_max': results.get('volume_ratio', {}).get('threshold', 5.0),
            'adjusted_sustain_min': results.get('adjusted_sustain', {}).get('threshold', 0.9),
        },
        'cap_damping': PHYSICS_CONSTRAINTS['cap_damping_buckets'],
        'cross_rejection': PHYSICS_CONSTRAINTS['cross_rejection'],
        'warnings': [
            "24样本不够统计显著性，使用阶梯阻尼而非线性衰减",
            "raw_sustain阈值必须>=1.1（必须溢出历史均值）",
            "MFE方向必须是>=（越大越好，代表抛压真空）",
        ]
    }
    
    return recommendations


def plot_scatter_v2(df: pd.DataFrame, output_dir: str = 'data/validation/'):
    """【CTO V2】绘制散点图，标注物理约束边界"""
    print("\n" + "=" * 70)
    print("绘制散点图（含物理约束边界）")
    print("=" * 70)
    
    true_dragons = df[df['label'] == 1]
    traps = df[df['label'] == 0]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    # 图1: 市值 vs raw_sustain（标注下限1.1）
    ax1 = axes[0, 0]
    ax1.axhline(y=PHYSICS_CONSTRAINTS['raw_sustain_min'], color='red', 
                linestyle='--', label=f'物理下限={PHYSICS_CONSTRAINTS["raw_sustain_min"]}')
    ax1.scatter(true_dragons['float_market_cap_yi'], true_dragons['raw_sustain'], 
                c='green', label='真龙', alpha=0.7, s=100)
    ax1.scatter(traps['float_market_cap_yi'], traps['raw_sustain'], 
                c='red', label='骗炮', alpha=0.7, s=100, marker='x')
    ax1.set_xlabel('流通市值(亿元)')
    ax1.set_ylabel('raw_sustain')
    ax1.set_title('市值 vs sustain（红线=物理下限1.1）')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 图2: 市值 vs MFE（标注下限0.5）
    ax2 = axes[0, 1]
    ax2.axhline(y=PHYSICS_CONSTRAINTS['mfe_min'], color='red', 
                linestyle='--', label=f'物理下限={PHYSICS_CONSTRAINTS["mfe_min"]}')
    ax2.scatter(true_dragons['float_market_cap_yi'], true_dragons['mfe'], 
                c='green', label='真龙', alpha=0.7, s=100)
    ax2.scatter(traps['float_market_cap_yi'], traps['mfe'], 
                c='red', label='骗炮', alpha=0.7, s=100, marker='x')
    ax2.set_xlabel('流通市值(亿元)')
    ax2.set_ylabel('MFE')
    ax2.set_title('市值 vs MFE（越大越好，红线=物理下限）')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 图3: volume_ratio vs MFE（交叉拦截区域）
    ax3 = axes[1, 0]
    ax3.axvline(x=PHYSICS_CONSTRAINTS['cross_rejection']['volume_ratio_max'], 
                color='orange', linestyle='--', label='volume_ratio上限')
    ax3.axhline(y=PHYSICS_CONSTRAINTS['cross_rejection']['mfe_warning'], 
                color='orange', linestyle='--', label='MFE警告线')
    ax3.scatter(true_dragons['volume_ratio'], true_dragons['mfe'], 
                c='green', label='真龙', alpha=0.7, s=100)
    ax3.scatter(traps['volume_ratio'], traps['mfe'], 
                c='red', label='骗炮', alpha=0.7, s=100, marker='x')
    ax3.set_xlabel('volume_ratio')
    ax3.set_ylabel('MFE')
    ax3.set_title('交叉拦截：右上区域=天量滞涨陷阱')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 图4: 阻尼后sustain分布
    ax4 = axes[1, 1]
    df['adjusted_sustain'] = df.apply(apply_cap_damping, axis=1)
    ax4.axhline(y=PHYSICS_CONSTRAINTS['raw_sustain_min'] * 0.8, color='red', 
                linestyle='--', label='阻尼后下限')
    ax4.scatter(true_dragons['float_market_cap_yi'], 
                true_dragons.apply(apply_cap_damping, axis=1), 
                c='green', label='真龙', alpha=0.7, s=100)
    ax4.scatter(traps['float_market_cap_yi'], 
                traps.apply(apply_cap_damping, axis=1), 
                c='red', label='骗炮', alpha=0.7, s=100, marker='x')
    ax4.set_xlabel('流通市值(亿元)')
    ax4.set_ylabel('adjusted_sustain（阻尼后）')
    ax4.set_title('阶梯阻尼后：大市值衰减，小市值保持')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'feature_scatter_v2.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"图表已保存: {output_path}")
    plt.close()


def main():
    """主函数"""
    print("=" * 70)
    print("CTO V2 物理约束参数寻优分析器启动")
    print("=" * 70)
    
    # 加载特征
    df = load_features()
    
    if df.empty:
        logger.error("[错误] 没有特征数据")
        return
    
    # 分析分布
    analysis_results = analyze_distribution(df)
    
    # 带物理约束的寻优
    constrained_results = analyze_with_physics_constraints(df)
    
    # 绘制散点图
    plot_scatter_v2(df)
    
    # 生成配置建议
    recommendations = generate_physics_constrained_config(df, constrained_results)
    
    print("\n" + "=" * 70)
    print("CTO V2 建议的strategy_params.json配置:")
    print("=" * 70)
    print(json.dumps(recommendations, indent=2, ensure_ascii=False))
    
    # 保存配置建议
    with open('data/validation/config_recommendations_v2.json', 'w', encoding='utf-8') as f:
        json.dump(recommendations, f, indent=2, ensure_ascii=False)
    print("\n配置建议已保存: data/validation/config_recommendations_v2.json")
    
    print("\n" + "=" * 70)
    print("CTO V2 核心警告")
    print("=" * 70)
    print("1. 24样本不够统计显著性，严禁写入正式配置")
    print("2. 当前参数仅供参考，需扩大样本量后验证")
    print("3. 物理约束（下限、方向）已强制执行，防止弱智阈值出现")


if __name__ == '__main__':
    main()