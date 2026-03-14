# -*- coding: utf-8 -*-
"""
【CTO周末曼哈顿计划】深度研究脚本

课题一：1m净流入算法真实度校验
课题二：智猪退出非线性边界研究

Author: CTO Research Lab
Date: 2026-03-14
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

print("=" * 70)
print("【CTO周末曼哈顿计划】深度研究 - 拒绝快餐研究")
print("=" * 70)

# ============== 课题一：1m净流入算法真实度校验 ==============
print("\n" + "=" * 70)
print("【课题一】1m净流入算法真实度校验 - 验证地基是否是沙子")
print("=" * 70)

def calc_flow_from_1m_v67(open_price, close_price, high, low, amount):
    """
    【V67近似算法】用1m K线模拟净流入
    
    公式：power_ratio = (close - open) / (high - low)
    净流入 = amount * power_ratio
    
    问题：如果前50秒主力出货，最后10秒散户拉升收红，
          系统会把全天量算成主力流入！这是致命的！
    """
    price_range = high - low
    if price_range <= 0:
        return 0.0
    
    power_ratio = (close_price - open_price) / price_range
    power_ratio = max(-1.0, min(1.0, power_ratio))
    
    return amount * power_ratio


def calc_flow_from_tick_approximation(tick_df):
    """
    【Tick精确算法】用逐笔数据计算真实净流入
    
    如果有Tick数据，用价格变动方向判断买卖方向
    ΔPrice > 0 → 买入
    ΔPrice < 0 → 卖出
    ΔPrice = 0 → 用盘口失衡判断
    """
    if tick_df is None or len(tick_df) < 10:
        return 0.0, 0.0
    
    # 用价格变动判断方向
    tick_df = tick_df.copy()
    tick_df['delta_price'] = tick_df['lastPrice'].diff()
    tick_df['delta_amount'] = tick_df['amount'].diff()
    
    # 正向流入（价格上涨）
    buy_amount = tick_df.loc[tick_df['delta_price'] > 0, 'delta_amount'].sum()
    # 负向流出（价格下跌）
    sell_amount = tick_df.loc[tick_df['delta_price'] < 0, 'delta_amount'].sum()
    
    net_inflow = buy_amount - sell_amount
    total_amount = tick_df['amount'].iloc[-1]
    
    return net_inflow, total_amount


def analyze_flow_accuracy():
    """
    分析1m K线估算的净流入与真实净流入的相关性
    """
    print("\n[分析] 净流入算法准确性验证")
    print("-" * 50)
    
    # 加载样本数据
    samples_path = ROOT / "data" / "validation" / "violent_samples_ohlcv.csv"
    
    if not samples_path.exists():
        print("⚠️ 样本数据文件不存在，使用模拟数据")
        return simulate_flow_analysis()
    
    df = pd.read_csv(samples_path)
    print(f"✅ 加载样本: {len(df)} 条")
    
    # 提取T0日数据
    results = []
    
    for idx, row in df.head(100).iterrows():  # 先分析100个样本
        try:
            stock_code = row['stock_code']
            date = str(row['date'])
            
            # T0日的OHLCV
            t0_open = row.get('t0_open', 0)
            t0_close = row.get('t0_close', 0)
            t0_high = row.get('t0_high', 0)
            t0_low = row.get('t0_low', 0)
            t0_amount = row.get('t0_amount', 0)
            
            if t0_high <= t0_low or t0_amount <= 0:
                continue
            
            # V67近似算法
            flow_v67 = calc_flow_from_1m_v67(t0_open, t0_close, t0_high, t0_low, t0_amount)
            
            # 假设真实流入（用涨幅*amount估算，这是另一个近似）
            t0_preclose = row.get('t0_preclose', t0_open)
            if t0_preclose > 0:
                true_change = (t0_close - t0_preclose) / t0_preclose
                flow_approx_true = t0_amount * true_change
            else:
                flow_approx_true = 0
            
            results.append({
                'stock_code': stock_code,
                'date': date,
                'flow_v67': flow_v67,
                'flow_approx_true': flow_approx_true,
                'amount': t0_amount,
                'change_pct': true_change * 100 if t0_preclose > 0 else 0,
            })
            
        except Exception as e:
            continue
    
    if not results:
        print("⚠️ 无有效数据")
        return
    
    results_df = pd.DataFrame(results)
    
    # 计算相关性
    from research_lab.shannon_validator import ShannonValidator
    validator = ShannonValidator()
    
    result = validator.validate_factor(
        results_df['flow_v67'].tolist(),
        results_df['flow_approx_true'].tolist(),
        "flow_v67_vs_approx_true"
    )
    
    print(f"\n📊 相关性分析结果:")
    print(f"   V67近似 vs 真实流入相关系数: {result.correlation:.4f}")
    print(f"   R²: {result.r_squared:.4f}")
    print(f"   样本数: {result.sample_count}")
    
    # 分析问题案例
    print(f"\n🔍 问题案例分析:")
    # 找出V67估算与真实方向相反的案例
    opposite = results_df[
        (results_df['flow_v67'] > 0) & (results_df['flow_approx_true'] < 0) |
        (results_df['flow_v67'] < 0) & (results_df['flow_approx_true'] > 0)
    ]
    
    if len(opposite) > 0:
        print(f"   ⚠️ 发现 {len(opposite)} 个方向相反案例!")
        print(f"   方向相反比例: {len(opposite)/len(results_df)*100:.1f}%")
        
        # 展示前3个案例
        for _, case in opposite.head(3).iterrows():
            print(f"   - {case['stock_code']} {case['date']}: "
                  f"V67={case['flow_v67']/1e8:.2f}亿 vs 真实={case['flow_approx_true']/1e8:.2f}亿 "
                  f"(涨幅{case['change_pct']:.1f}%)")
    
    return result


def simulate_flow_analysis():
    """
    模拟数据分析（当真实数据不可用时）
    """
    print("\n[模拟分析] 使用模拟数据演示问题")
    print("-" * 50)
    
    np.random.seed(42)
    n = 1000
    
    # 模拟1m K线场景
    results = []
    
    for i in range(n):
        # 场景1：正常上涨（V67估算准确）
        if i < 400:
            open_p = 10.0
            close_p = 10.3
            high = 10.5
            low = 9.9
            amount = 1000000
            true_flow = 300000  # 正流入
        
        # 场景2：正常下跌（V67估算准确）
        elif i < 700:
            open_p = 10.0
            close_p = 9.7
            high = 10.1
            low = 9.5
            amount = 1000000
            true_flow = -300000  # 负流入
        
        # 场景3：⚠️ 假阳性！前50秒出货，后10秒拉升
        # K线收红但实际是派发
        elif i < 900:
            open_p = 10.0
            close_p = 10.05  # 微涨
            high = 10.2
            low = 9.6
            amount = 5000000  # 天量
            true_flow = -2000000  # 实际出货！
        
        # 场景4：⚠️ 假阴性！洗盘后拉升
        else:
            open_p = 10.0
            close_p = 9.95  # 微跌
            high = 10.3
            low = 9.8
            amount = 800000
            true_flow = 400000  # 实际吸筹
        
        # V67估算
        flow_v67 = calc_flow_from_1m_v67(open_p, close_p, high, low, amount)
        
        results.append({
            'flow_v67': flow_v67,
            'true_flow': true_flow,
            'amount': amount,
            'scenario': i // 300,
        })
    
    results_df = pd.DataFrame(results)
    
    # 计算整体相关性
    from research_lab.shannon_validator import ShannonValidator
    validator = ShannonValidator()
    
    result = validator.validate_factor(
        results_df['flow_v67'].tolist(),
        results_df['true_flow'].tolist(),
        "flow_v67_simulation"
    )
    
    print(f"\n📊 模拟分析结果:")
    print(f"   V67近似 vs 真实流入相关系数: {result.correlation:.4f}")
    print(f"   R²: {result.r_squared:.4f}")
    
    # 分场景分析
    print(f"\n🔍 分场景分析:")
    for scenario in results_df['scenario'].unique():
        subset = results_df[results_df['scenario'] == scenario]
        corr = np.corrcoef(subset['flow_v67'], subset['true_flow'])[0, 1]
        print(f"   场景{scenario}: 相关系数 {corr:.4f}")
    
    # 问题案例
    opposite = results_df[
        (results_df['flow_v67'] > 0) & (results_df['true_flow'] < 0) |
        (results_df['flow_v67'] < 0) & (results_df['true_flow'] > 0)
    ]
    
    print(f"\n⚠️ 问题案例统计:")
    print(f"   方向相反案例: {len(opposite)} / {len(results_df)} ({len(opposite)/len(results_df)*100:.1f}%)")
    
    if result.correlation < 0.7:
        print(f"\n🚨【CTO红线警告】")
        print(f"   相关系数 {result.correlation:.4f} < 0.7")
        print(f"   V67近似算法存在严重失真！")
        print(f"   建议：引入多周期成交额分布斜率修正")
    
    return result


# ============== 课题二：智猪退出非线性边界 ==============
print("\n" + "=" * 70)
print("【课题二】智猪退出非线性边界 - 拯救真空滑行真龙")
print("=" * 70)


def analyze_smart_pig_exit():
    """
    分析真龙在高位的MFE和Sustain分布
    验证：缩量一字板/秒板被误判的问题
    """
    print("\n[分析] 真龙高位物理特征分布")
    print("-" * 50)
    
    # 加载样本数据
    samples_path = ROOT / "data" / "validation" / "violent_samples_ohlcv.csv"
    
    if not samples_path.exists():
        print("⚠️ 样本数据文件不存在，使用模拟分析")
        return simulate_smart_pig_analysis()
    
    df = pd.read_csv(samples_path)
    
    # 筛选高收益样本（5日收益>20%）
    high_return = df[df['return_pct'] > 20].copy()
    print(f"✅ 高收益样本(>20%): {len(high_return)} 条")
    
    # 分析T0日特征
    results = []
    
    for idx, row in high_return.iterrows():
        try:
            t0_close = row.get('t0_close', 0)
            t0_open = row.get('t0_open', 0)
            t0_high = row.get('t0_high', 0)
            t0_low = row.get('t0_low', 0)
            t0_amount = row.get('t0_amount', 0)
            t0_preclose = row.get('t0_preclose', t0_open)
            t0_volume = row.get('t0_volume', 0)
            
            if t0_preclose <= 0:
                continue
            
            # 涨幅
            change_pct = (t0_close - t0_preclose) / t0_preclose * 100
            
            # 振幅
            amplitude = (t0_high - t0_low) / t0_preclose * 100
            
            # 估算MFE（简化版）
            # MFE = 振幅 / (amount/流通市值)
            # 假设流通市值用amount估算
            if t0_amount > 0:
                # 简化：用涨幅估算流入
                flow_ratio = change_pct  # 粗略估算
                mfe = amplitude / max(abs(flow_ratio), 0.1)
            else:
                mfe = 0
            
            # 判断是否涨停
            is_limit_up = change_pct >= 9.5
            
            # 判断是否缩量（用振幅小作为代理）
            is_low_amplitude = amplitude < 3.0
            
            results.append({
                'stock_code': row['stock_code'],
                'return_pct': row['return_pct'],
                'change_pct': change_pct,
                'amplitude': amplitude,
                'mfe': mfe,
                'is_limit_up': is_limit_up,
                'is_low_amplitude': is_low_amplitude,
                'amount': t0_amount,
            })
            
        except Exception as e:
            continue
    
    if not results:
        print("⚠️ 无有效数据")
        return
    
    results_df = pd.DataFrame(results)
    
    # 分析涨停股 vs 非涨停股
    print(f"\n📊 涨停 vs 非涨停对比:")
    
    limit_up = results_df[results_df['is_limit_up']]
    non_limit = results_df[~results_df['is_limit_up']]
    
    if len(limit_up) > 0:
        print(f"\n   涨停股 ({len(limit_up)}只):")
        print(f"      平均MFE: {limit_up['mfe'].mean():.2f}")
        print(f"      平均振幅: {limit_up['amplitude'].mean():.2f}%")
        print(f"      平均收益: {limit_up['return_pct'].mean():.2f}%")
        print(f"      缩量(振幅<3%): {len(limit_up[limit_up['is_low_amplitude']])}只")
    
    if len(non_limit) > 0:
        print(f"\n   非涨停股 ({len(non_limit)}只):")
        print(f"      平均MFE: {non_limit['mfe'].mean():.2f}")
        print(f"      平均振幅: {non_limit['amplitude'].mean():.2f}%")
        print(f"      平均收益: {non_limit['return_pct'].mean():.2f}%")
    
    # 关键发现
    print(f"\n🔍 关键发现:")
    
    # 检查涨停但MFE低的情况
    low_mfe_limit = limit_up[limit_up['mfe'] < 1.0] if len(limit_up) > 0 else pd.DataFrame()
    if len(low_mfe_limit) > 0:
        print(f"   ⚠️ 涨停但MFE<1.0: {len(low_mfe_limit)}只")
        print(f"      这些真龙会被旧版退出逻辑误杀！")
    
    # 物理定律推演
    print(f"\n📜 物理定律推演:")
    print(f"   真龙真空滑行特征：")
    print(f"   - 量比极低（封单锁仓）")
    print(f"   - 振幅极小（一字板）")
    print(f"   - MFE看似低，实际是真空无摩擦")
    print(f"   ")
    print(f"   真正危险的派发特征：")
    print(f"   - 量比维持高位（持续换手）")
    print(f"   - MFE断崖式跌破20th")
    print(f"   - 价格滞涨或回落")
    
    return results_df


def simulate_smart_pig_analysis():
    """
    模拟智猪退出分析
    """
    print("\n[模拟分析] 真龙高位特征模拟")
    print("-" * 50)
    
    np.random.seed(42)
    n = 500
    
    results = []
    
    # 模拟不同类型的股票
    for i in range(n):
        # 场景1：一字板真龙（真空滑行）
        if i < 150:
            change_pct = np.random.uniform(9.5, 10.5)
            amplitude = np.random.uniform(0.5, 3.0)  # 极小振幅
            mfe = amplitude / 10  # MFE看起来很低
            return_5d = np.random.uniform(20, 50)
            is_true_dragon = True
        
        # 场景2：放量涨停（正常接力）
        elif i < 300:
            change_pct = np.random.uniform(9.5, 10.5)
            amplitude = np.random.uniform(5, 15)  # 较大振幅
            mfe = amplitude / 8
            return_5d = np.random.uniform(10, 30)
            is_true_dragon = True
        
        # 场景3：烂板派发（应该退出）
        elif i < 400:
            change_pct = np.random.uniform(5, 9)
            amplitude = np.random.uniform(8, 20)
            mfe = np.random.uniform(0.2, 0.5)  # MFE低且有量
            volume_ratio = np.random.uniform(5, 15)  # 高量比
            return_5d = np.random.uniform(-10, 5)
            is_true_dragon = False
        
        # 场景4：高位滞涨（大猪派发）
        else:
            change_pct = np.random.uniform(0, 3)
            amplitude = np.random.uniform(3, 10)
            mfe = np.random.uniform(0.1, 0.3)
            volume_ratio = np.random.uniform(8, 20)
            return_5d = np.random.uniform(-15, 0)
            is_true_dragon = False
        
        results.append({
            'change_pct': change_pct,
            'amplitude': amplitude,
            'mfe': mfe,
            'return_5d': return_5d,
            'is_true_dragon': is_true_dragon,
        })
    
    results_df = pd.DataFrame(results)
    
    # 分析旧版退出逻辑的误杀率
    print(f"\n📊 旧版退出逻辑分析:")
    print(f"   退出条件: MFE < 30th 或 sustain < 0.5")
    
    mfe_30th = results_df['mfe'].quantile(0.30)
    
    # 会被误杀的真龙
    true_dragons = results_df[results_df['is_true_dragon']]
    killed_dragons = true_dragons[true_dragons['mfe'] < mfe_30th]
    
    print(f"\n   ⚠️ 误杀统计:")
    print(f"      真龙总数: {len(true_dragons)}只")
    print(f"      被误杀的真龙: {len(killed_dragons)}只")
    print(f"      误杀率: {len(killed_dragons)/len(true_dragons)*100:.1f}%")
    
    if len(killed_dragons) > 0:
        print(f"\n      被误杀真龙平均收益: {killed_dragons['return_5d'].mean():.1f}%")
        print(f"      这些是真龙最暴利的真空滑行段！")
    
    # 新版退出逻辑建议
    print(f"\n💡 新版退出逻辑建议:")
    print(f"   不要看MFE绝对值，要看：")
    print(f"   1. 量比是否维持高位（派发特征）")
    print(f"   2. MFE是否断崖式下跌（不是缓慢下降）")
    print(f"   3. 价格是否滞涨或回落")
    print(f"\n   真空滑行特征：")
    print(f"   - 量比 < 1.0（锁仓）")
    print(f"   - 振幅 < 3%（一字）")
    print(f"   - 价格维持高位（不破关键位）")
    print(f"   → 这种情况MFE低是正常的，不应触发退出！")
    
    return results_df


# ============== 执行分析 ==============
if __name__ == "__main__":
    print("\n开始执行深度研究...\n")
    
    # 课题一
    flow_result = analyze_flow_accuracy()
    
    # 课题二
    pig_result = analyze_smart_pig_exit()
    
    print("\n" + "=" * 70)
    print("【深度研究完成】")
    print("=" * 70)
    print("\n下一步行动：")
    print("1. 如果flow_result.correlation < 0.7，需要设计修正算法")
    print("2. 如果误杀率 > 10%，需要修改退出逻辑")
    print("3. 用真实Tick数据验证上述发现")
