# -*- coding: utf-8 -*-
"""
【CTO V158 跨日动能守恒定律：多元回归分析】

研究目的：
1. 推导真实的《跨日能量转换方程》
2. 找出物理临界值（Phase Transition Point）
3. 拟合真实常数，替代拍脑袋系数

核心问题：
- V157中的`log10(...) * 2.0`和`0.90`阈值是拍脑袋的！
- 需要用真实数据回归出物理定律

自变量：
- X1: 昨日量比分位数 (Yesterday_Vol_Ratio_Percentile)
- X2: 昨日做功效率 (Yesterday_MFE)

因变量：
- Y: 今日开盘溢价幅度 ((今日开盘价 / 昨日收盘价 - 1) * 100)

Author: CTO Research
Date: 2026-03-14
"""

import json
import numpy as np
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 尝试导入回归分析库
try:
    from scipy import stats
    from scipy.optimize import curve_fit
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("[警告] scipy未安装，将使用简化分析方法")


def load_samples() -> List[Dict]:
    """加载暴力样本库（CSV格式）"""
    import pandas as pd
    
    csv_path = Path(__file__).parent.parent / "data" / "validation" / "violent_samples_ohlcv.csv"
    
    if not csv_path.exists():
        print(f"[错误] 样本文件不存在: {csv_path}")
        return []
    
    df = pd.read_csv(csv_path)
    print(f"[加载] 样本数量: {len(df)}")
    
    # 转换为字典列表格式
    samples = []
    for _, row in df.iterrows():
        sample = {
            'stock_code': row['stock_code'],
            'date': str(row['date']),
            'period': row.get('period', '2d'),
            't_minus_1': {
                'open': row.get('t1_open', 0),
                'high': row.get('t1_high', 0),
                'low': row.get('t1_low', 0),
                'close': row.get('t1_close', 0),
                'volume': row.get('t1_volume', 0),
                'amount': row.get('t1_amount', 0),
                'turnover_pct': row.get('t1_turnover', 0) / 100 if pd.notna(row.get('t1_turnover')) else 0,
            },
            't0': {
                'open': row.get('t0_open', 0),
                'high': row.get('t0_high', 0),
                'low': row.get('t0_low', 0),
                'close': row.get('t0_close', 0),
                'preclose': row.get('t0_preclose', 0),
                'amplitude': row.get('t0_amplitude', 0),
            },
        }
        samples.append(sample)
    
    return samples


def extract_regression_data(samples: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    提取回归分析所需数据
    
    返回:
        X1: 昨日量比
        X2: 昨日MFE
        Y: 今日开盘溢价
    """
    X1_list = []  # 昨日量比
    X2_list = []  # 昨日MFE（用振幅/换手率近似）
    Y_list = []   # 今日开盘溢价
    
    for s in samples:
        t0 = s.get('t0', {})
        t_minus_1 = s.get('t_minus_1', {})
        
        if not t0 or not t_minus_1:
            continue
        
        # 提取T-1日数据
        t1_close = t_minus_1.get('close', 0)
        t1_high = t_minus_1.get('high', 0)
        t1_low = t_minus_1.get('low', 0)
        t1_volume = t_minus_1.get('volume', 0)
        t1_turnover = t_minus_1.get('turnover_pct', 0) or 0
        
        # 提取T0日数据
        t0_open = t0.get('open', 0)
        t0_close = t0.get('close', 0)
        
        if t1_close <= 0 or t0_open <= 0:
            continue
        
        # 计算昨日量比（用换手率近似，假设正常换手率2%）
        if t1_turnover > 0:
            vol_ratio = t1_turnover / 0.02  # 相对于正常换手率的倍数
        else:
            vol_ratio = 1.0
        
        # 计算昨日MFE（振幅/换手率，turnover_pct已经是小数形式）
        if t1_turnover > 0 and t1_close > 0:
            amplitude = (t1_high - t1_low) / t1_close * 100
            mfe = amplitude / (t1_turnover * 100)  # 换手率转成百分比
        else:
            mfe = 1.0
        
        # 计算今日开盘溢价
        opening_gap = (t0_open / t1_close - 1) * 100
        
        X1_list.append(vol_ratio)
        X2_list.append(mfe)
        Y_list.append(opening_gap)
    
    return np.array(X1_list), np.array(X2_list), np.array(Y_list)


def calculate_percentile(value: float, distribution: np.ndarray) -> float:
    """计算一个值在分布中的分位数"""
    return np.searchsorted(np.sort(distribution), value) / len(distribution)


def find_critical_threshold(X1: np.ndarray, X2: np.ndarray, Y: np.ndarray) -> Dict:
    """
    寻找物理临界值（Phase Transition Point）
    
    遍历不同分位数阈值，观察Y的期望值变化
    """
    results = []
    
    # 计算每个样本的综合物理当量
    # 物理当量 = 量比 * MFE
    physics_equivalent = X1 * X2
    
    # 计算物理当量的分位数
    pe_sorted = np.sort(physics_equivalent)
    
    for percentile in range(50, 100, 5):
        threshold_idx = int(len(pe_sorted) * percentile / 100)
        threshold = pe_sorted[threshold_idx]
        
        # 筛选超过阈值的样本
        mask = physics_equivalent >= threshold
        Y_above = Y[mask]
        Y_below = Y[~mask]
        
        if len(Y_above) < 10:
            continue
        
        result = {
            'percentile': percentile,
            'threshold': threshold,
            'n_above': len(Y_above),
            'n_below': len(Y_below),
            'y_mean_above': np.mean(Y_above),
            'y_mean_below': np.mean(Y_below) if len(Y_below) > 0 else 0,
            'y_std_above': np.std(Y_above),
            'y_median_above': np.median(Y_above),
            'y_positive_ratio_above': np.sum(Y_above > 0) / len(Y_above) * 100,
        }
        results.append(result)
    
    return results


def regression_analysis(X1: np.ndarray, X2: np.ndarray, Y: np.ndarray) -> Dict:
    """
    多元回归分析
    
    拟合模型: Y = a + b1*log(1+X1) + b2*X2
    """
    if not HAS_SCIPY:
        return {'error': 'scipy未安装'}
    
    # 过滤有效数据
    valid_mask = (X1 > 0) & (X2 > 0) & np.isfinite(Y)
    X1_valid = X1[valid_mask]
    X2_valid = X2[valid_mask]
    Y_valid = Y[valid_mask]
    
    if len(Y_valid) < 100:
        return {'error': f'有效样本不足: {len(Y_valid)}'}
    
    # 构造特征矩阵
    # 模型: Y = a + b1*log(1+X1) + b2*X2
    log_X1 = np.log10(1 + X1_valid)
    
    # 使用numpy最小二乘法
    X_matrix = np.column_stack([
        np.ones(len(Y_valid)),  # 截距
        log_X1,                  # log10(1+量比)
        X2_valid                 # MFE
    ])
    
    # 求解回归系数
    try:
        coeffs, residuals, rank, s = np.linalg.lstsq(X_matrix, Y_valid, rcond=None)
        
        # 计算R²
        Y_pred = X_matrix @ coeffs
        ss_res = np.sum((Y_valid - Y_pred) ** 2)
        ss_tot = np.sum((Y_valid - np.mean(Y_valid)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        
        # 计算相关系数
        corr_matrix = np.corrcoef(np.column_stack([log_X1, X2_valid, Y_valid]).T)
        corr_vol_gap = corr_matrix[0, 2] if corr_matrix.shape[0] > 2 else 0
        corr_mfe_gap = corr_matrix[1, 2] if corr_matrix.shape[0] > 2 else 0
        
        return {
            'intercept': coeffs[0],
            'coef_log_vol_ratio': coeffs[1],
            'coef_mfe': coeffs[2],
            'r_squared': r_squared,
            'corr_vol_gap': corr_vol_gap,
            'corr_mfe_gap': corr_mfe_gap,
            'n_samples': len(Y_valid),
            'y_mean': np.mean(Y_valid),
            'y_std': np.std(Y_valid),
            'equation': f"开盘溢价 = {coeffs[0]:.3f} + {coeffs[1]:.3f}*log10(1+量比) + {coeffs[2]:.3f}*MFE"
        }
    except Exception as e:
        return {'error': str(e)}


def analyze_threshold_sensitivity(X1: np.ndarray, X2: np.ndarray, Y: np.ndarray) -> List[Dict]:
    """
    分析不同阈值下的表现
    
    遍历不同的写入记忆阈值，观察对Y的区分度
    """
    results = []
    
    # 计算分位数
    X1_sorted = np.sort(X1)
    X2_sorted = np.sort(X2)
    
    for pct in [0.70, 0.75, 0.80, 0.85, 0.88, 0.90, 0.92, 0.95, 0.97, 0.99]:
        # 获取阈值
        idx = int(len(X1_sorted) * pct)
        vol_threshold = X1_sorted[idx]
        mfe_threshold = X2_sorted[idx]
        
        # 筛选满足条件的样本
        mask = (X1 >= vol_threshold) & (X2 >= mfe_threshold)
        Y_filtered = Y[mask]
        
        if len(Y_filtered) < 10:
            continue
        
        result = {
            'percentile': pct,
            'vol_threshold': vol_threshold,
            'mfe_threshold': mfe_threshold,
            'n_samples': len(Y_filtered),
            'y_mean': np.mean(Y_filtered),
            'y_median': np.median(Y_filtered),
            'y_std': np.std(Y_filtered),
            'y_positive_ratio': np.sum(Y_filtered > 0) / len(Y_filtered) * 100,
            'y_above_2pct': np.sum(Y_filtered > 2) / len(Y_filtered) * 100,
        }
        results.append(result)
    
    return results


def main():
    print("=" * 70)
    print("【CTO V158 跨日动能守恒定律：多元回归分析】")
    print("=" * 70)
    
    # 1. 加载样本
    samples = load_samples()
    if not samples:
        return
    
    # 2. 提取回归数据
    print("\n[Step 1] 提取回归分析数据...")
    X1, X2, Y = extract_regression_data(samples)
    print(f"  有效样本数: {len(Y)}")
    print(f"  昨日量比范围: [{X1.min():.2f}, {X1.max():.2f}]")
    print(f"  昨日MFE范围: [{X2.min():.4f}, {X2.max():.4f}]")
    print(f"  开盘溢价范围: [{Y.min():.2f}%, {Y.max():.2f}%]")
    
    # 3. 寻找物理临界值
    print("\n[Step 2] 寻找物理临界值（Phase Transition Point）...")
    threshold_results = find_critical_threshold(X1, X2, Y)
    
    print("\n  分位数 | 阈值 | 样本数 | 开盘溢价均值 | 正溢价比例")
    print("  " + "-" * 60)
    for r in threshold_results:
        print(f"  {r['percentile']}th | {r['threshold']:.2f} | {r['n_above']} | "
              f"{r['y_mean_above']:+.2f}% | {r['y_positive_ratio_above']:.1f}%")
    
    # 4. 阈值敏感性分析
    print("\n[Step 3] 阈值敏感性分析...")
    sensitivity = analyze_threshold_sensitivity(X1, X2, Y)
    
    print("\n  分位数 | 量比阈值 | MFE阈值 | 样本数 | 溢价均值 | 溢价>2%比例")
    print("  " + "-" * 70)
    for s in sensitivity:
        print(f"  {s['percentile']:.0%} | {s['vol_threshold']:.2f}x | {s['mfe_threshold']:.3f} | "
              f"{s['n_samples']} | {s['y_mean']:+.2f}% | {s['y_above_2pct']:.1f}%")
    
    # 5. 多元回归分析
    print("\n[Step 4] 多元回归分析...")
    regression_result = regression_analysis(X1, X2, Y)
    
    if 'error' in regression_result:
        print(f"  回归失败: {regression_result['error']}")
    else:
        print(f"\n  【拟合方程】")
        print(f"  {regression_result['equation']}")
        print(f"\n  【统计指标】")
        print(f"  R² = {regression_result['r_squared']:.4f}")
        print(f"  量比与溢价相关系数 = {regression_result['corr_vol_gap']:.4f}")
        print(f"  MFE与溢价相关系数 = {regression_result['corr_mfe_gap']:.4f}")
        print(f"  样本数 = {regression_result['n_samples']}")
        
        # 6. 给出建议
        print("\n" + "=" * 70)
        print("【CTO结论与建议】")
        print("=" * 70)
        
        # 分析最佳阈值
        if sensitivity:
            best = max(sensitivity, key=lambda x: x['y_mean'])
            print(f"\n  最佳记忆写入阈值: {best['percentile']:.0%}")
            print(f"  对应量比阈值: {best['vol_threshold']:.2f}x")
            print(f"  对应MFE阈值: {best['mfe_threshold']:.3f}")
            print(f"  该阈值下开盘溢价均值: {best['y_mean']:+.2f}%")
        
        # 分析回归系数
        if 'coef_log_vol_ratio' in regression_result:
            print(f"\n  真实溢出乘数系数: {regression_result['coef_log_vol_ratio']:.3f}")
            print(f"  (V157拍的脑袋系数是2.0，差异: {abs(regression_result['coef_log_vol_ratio'] - 2.0):.3f})")
            
            if regression_result['r_squared'] < 0.1:
                print("\n  ⚠️ R²极低，说明当前因子解释力不足，需要寻找更强的物理因子！")
            elif regression_result['r_squared'] < 0.3:
                print("\n  ⚠️ R²较低，建议继续寻找更好的物理因子组合。")
            else:
                print(f"\n  ✅ R²={regression_result['r_squared']:.2f}，模型有一定解释力。")
    
    # 7. 保存结果
    output_path = Path(__file__).parent.parent / "data" / "research_lab" / "cross_day_regression_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'threshold_results': threshold_results,
            'sensitivity': sensitivity,
            'regression': regression_result,
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n[保存] 结果已保存到: {output_path}")


if __name__ == '__main__':
    main()
