#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTO数据飞轮：参数寻优分析器 (Parameter Tuner)
==========================================
职责：基于features.csv，通过统计学分布寻找最优分割面

设计原则：
1. 严禁主观假设（废除log10等硬编码公式）
2. 根据真实样本簇群计算衰减斜率
3. 测算最大化F1-Score时的阈值

Author: AI开发专家团队 (CTO架构指令)
Date: 2026-03-10
Version: V1.0.0
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple
import logging

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


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
    
    # 关键特征分析
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
        
        # 计算区分度
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


def find_optimal_threshold(df: pd.DataFrame, feature: str) -> Dict:
    """
    寻找最优分割阈值
    
    使用网格搜索找到最大化F1-Score的阈值
    """
    if feature not in df.columns:
        return {}
    
    values = df[feature].dropna()
    labels = df.loc[values.index, 'label']
    
    # 网格搜索
    thresholds = np.linspace(values.min(), values.max(), 100)
    best_threshold = None
    best_f1 = 0
    best_direction = 'above'  # above: 真龙在阈值之上, below: 真龙在阈值之下
    
    for threshold in thresholds:
        # 尝试两种方向
        for direction in ['above', 'below']:
            if direction == 'above':
                preds = (values >= threshold).astype(int)
            else:
                preds = (values <= threshold).astype(int)
            
            # 计算F1
            tp = ((preds == 1) & (labels == 1)).sum()
            fp = ((preds == 1) & (labels == 0)).sum()
            fn = ((preds == 0) & (labels == 1)).sum()
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold
                best_direction = direction
    
    return {
        'feature': feature,
        'threshold': best_threshold,
        'direction': best_direction,
        'f1_score': best_f1
    }


def analyze_market_cap_damping(df: pd.DataFrame) -> Dict:
    """
    分析市值与sustain的关系，计算真实的衰减斜率
    
    这是CTO要求的：废除log10硬编码，用真实数据说话
    """
    print("\n" + "=" * 70)
    print("市值引力阻尼分析 - 废除log10硬编码")
    print("=" * 70)
    
    # 按市值分桶
    df['cap_bucket'] = pd.cut(
        df['float_market_cap_yi'], 
        bins=[0, 50, 100, 200, 500, 2000],
        labels=['<50亿', '50-100亿', '100-200亿', '200-500亿', '>500亿']
    )
    
    # 按桶统计raw_sustain
    bucket_stats = df.groupby('cap_bucket').agg({
        'raw_sustain': ['mean', 'std', 'count'],
        'label': 'mean'  # 真龙比例
    }).round(2)
    
    print("\n市值分桶统计:")
    print(bucket_stats)
    
    # 计算真实衰减斜率
    # 使用线性回归计算市值每增加10亿，sustain应该衰减多少
    from scipy import stats
    
    valid_data = df[df['raw_sustain'] > 0].copy()
    if len(valid_data) > 5:
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            valid_data['float_market_cap_yi'],
            valid_data['raw_sustain']
        )
        
        print(f"\n线性回归结果:")
        print(f"  斜率(slope): {slope:.6f} (每增加1亿市值，sustain变化)")
        print(f"  截距(intercept): {intercept:.4f}")
        print(f"  R²: {r_value**2:.4f}")
        print(f"  p-value: {p_value:.4f}")
        
        # 转换为每10亿的衰减率
        slope_per_10yi = slope * 10
        print(f"\n  每增加10亿市值，sustain变化: {slope_per_10yi:.4f}")
        
        # 计算建议的damping_factor
        # 如果斜率为负，说明市值越大sustain越低
        if slope < 0:
            # 衰减因子 = -slope / intercept (相对于基准的衰减比例)
            damping_factor_per_10yi = -slope_per_10yi / intercept if intercept != 0 else 0
            print(f"\n  建议的damping_factor_per_billion: {damping_factor_per_10yi/10:.4f}")
        
        return {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_value**2,
            'slope_per_10yi': slope_per_10yi
        }
    
    return {}


def plot_scatter(df: pd.DataFrame, output_dir: str = 'data/validation/'):
    """绘制散点图"""
    print("\n" + "=" * 70)
    print("绘制散点图")
    print("=" * 70)
    
    true_dragons = df[df['label'] == 1]
    traps = df[df['label'] == 0]
    
    # 图1: 市值 vs raw_sustain
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    # 市值 vs raw_sustain
    ax1 = axes[0, 0]
    ax1.scatter(true_dragons['float_market_cap_yi'], true_dragons['raw_sustain'], 
                c='green', label='真龙', alpha=0.7, s=100)
    ax1.scatter(traps['float_market_cap_yi'], traps['raw_sustain'], 
                c='red', label='骗炮', alpha=0.7, s=100, marker='x')
    ax1.set_xlabel('流通市值(亿元)')
    ax1.set_ylabel('raw_sustain')
    ax1.set_title('市值 vs sustain (真龙sustain更高)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 市值 vs MFE
    ax2 = axes[0, 1]
    ax2.scatter(true_dragons['float_market_cap_yi'], true_dragons['mfe'], 
                c='green', label='真龙', alpha=0.7, s=100)
    ax2.scatter(traps['float_market_cap_yi'], traps['mfe'], 
                c='red', label='骗炮', alpha=0.7, s=100, marker='x')
    ax2.set_xlabel('流通市值(亿元)')
    ax2.set_ylabel('MFE')
    ax2.set_title('市值 vs MFE')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # volume_ratio vs raw_sustain
    ax3 = axes[1, 0]
    ax3.scatter(true_dragons['volume_ratio'], true_dragons['raw_sustain'], 
                c='green', label='真龙', alpha=0.7, s=100)
    ax3.scatter(traps['volume_ratio'], traps['raw_sustain'], 
                c='red', label='骗炮', alpha=0.7, s=100, marker='x')
    ax3.set_xlabel('volume_ratio')
    ax3.set_ylabel('raw_sustain')
    ax3.set_title('量比 vs sustain')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # inflow_ratio vs raw_sustain
    ax4 = axes[1, 1]
    ax4.scatter(true_dragons['inflow_ratio_pct'], true_dragons['raw_sustain'], 
                c='green', label='真龙', alpha=0.7, s=100)
    ax4.scatter(traps['inflow_ratio_pct'], traps['raw_sustain'], 
                c='red', label='骗炮', alpha=0.7, s=100, marker='x')
    ax4.set_xlabel('流入比(%)')
    ax4.set_ylabel('raw_sustain')
    ax4.set_title('流入比 vs sustain')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'feature_scatter.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"图表已保存: {output_path}")
    plt.close()


def generate_config_recommendations(df: pd.DataFrame, analysis_results: Dict) -> Dict:
    """
    生成配置建议
    
    根据真实数据统计，生成strategy_params.json的配置建议
    """
    print("\n" + "=" * 70)
    print("配置建议 - 基于真实数据统计")
    print("=" * 70)
    
    # 寻找各特征的最优阈值
    key_features = ['raw_sustain', 'mfe', 'volume_ratio', 'inflow_ratio_pct']
    
    recommendations = {
        'kinetic_physics': {}
    }
    
    print("\n最优分割阈值:")
    for feat in key_features:
        if feat not in df.columns:
            continue
        result = find_optimal_threshold(df, feat)
        if result and result['threshold'] is not None:
            print(f"  {feat}: 阈值={result['threshold']:.2f}, 方向={result['direction']}, F1={result['f1_score']:.2f}")
            recommendations['kinetic_physics'][f'{feat}_threshold'] = round(result['threshold'], 2)
    
    # 市值基准
    median_cap = df['float_market_cap_yi'].median()
    recommendations['kinetic_physics']['market_cap_base'] = int(median_cap * 100000000)  # 转为元
    print(f"\n市值基准(中位数): {median_cap:.2f}亿元")
    
    return recommendations


def main():
    """主函数"""
    print("=" * 70)
    print("CTO数据飞轮：参数寻优分析器启动")
    print("=" * 70)
    
    # 加载特征
    df = load_features()
    
    if df.empty:
        logger.error("[错误] 没有特征数据")
        return
    
    # 分析分布
    analysis_results = analyze_distribution(df)
    
    # 分析市值引力阻尼
    damping_results = analyze_market_cap_damping(df)
    
    # 绘制散点图
    plot_scatter(df)
    
    # 生成配置建议
    recommendations = generate_config_recommendations(df, analysis_results)
    
    print("\n" + "=" * 70)
    print("建议的strategy_params.json配置:")
    print("=" * 70)
    import json
    print(json.dumps(recommendations, indent=2, ensure_ascii=False))
    
    # 保存配置建议
    with open('data/validation/config_recommendations.json', 'w', encoding='utf-8') as f:
        json.dump(recommendations, f, indent=2, ensure_ascii=False)
    print("\n配置建议已保存: data/validation/config_recommendations.json")


if __name__ == '__main__':
    main()