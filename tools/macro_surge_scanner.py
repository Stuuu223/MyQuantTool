# -*- coding: utf-8 -*-
"""
CTO V111 日K宏观物理降维对撞机

【背景】
QMT基础接口对1分钟线和Tick数据有近一个月的时间限制！
173样本库包含2025年数据，无法获取一年前的分K数据。
降维到日K级别进行宏观物理特征提取。

【核心物理量】
1. 宏观做功推力 (Macro MFE): 振幅% / 成交额(亿)
2. 宏观纯度 (Macro Purity): (Close-Low)/(High-Low)
3. 起爆放量倍数 (Vacuum Ratio): 当日成交额 / 5日均额
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    import xtquant.xtdata as xtdata
except ImportError:
    print("[ERROR] 无法导入xtquant，请确保在venv_qmt环境中运行")
    sys.exit(1)


def get_limit_up_price(stock_code: str, prev_close: float) -> float:
    """计算涨停价"""
    if stock_code.startswith(('30', '68')):
        limit_pct = 0.20
    elif 'ST' in stock_code or 'st' in stock_code:
        limit_pct = 0.05
    else:
        limit_pct = 0.10
    return round(prev_close * (1 + limit_pct) * 100) / 100


def analyze_macro_physics(stock: str, target_date: str, daily_df: pd.DataFrame) -> dict:
    """
    分析单只股票的日K宏观物理特征
    
    Args:
        stock: 股票代码
        target_date: 目标日期字符串
        daily_df: 日K数据DataFrame
        
    Returns:
        宏观物理特征字典
    """
    result = {
        'stock': stock,
        'date': target_date,
        'success': False,
        'macro_mfe': 0.0,
        'macro_purity': 0.0,
        'vacuum_ratio': 0.0,
        'change_pct': 0.0,
        'amplitude': 0.0,
        'amount_yi': 0.0,
        'is_sealed': False,
        'pre_volume_ratio': 0.0,
    }
    
    try:
        # 定位到起爆日
        if target_date not in daily_df.index:
            return result
            
        target_idx = daily_df.index.get_loc(target_date)
        
        # 提取起爆日当天的宏观物理特征
        target_row = daily_df.iloc[target_idx]
        pre_close = float(target_row['preClose'])
        high = float(target_row['high'])
        low = float(target_row['low'])
        close = float(target_row['close'])
        amount = float(target_row['amount'])
        volume = float(target_row['volume'])
        open_price = float(target_row['open'])
        
        if pre_close <= 0:
            return result
        
        # 基础指标
        change_pct = (close - pre_close) / pre_close * 100
        amplitude = (high - low) / pre_close * 100
        amount_yi = amount / 1e8
        
        # 涨停判断
        limit_price = get_limit_up_price(stock, pre_close)
        is_sealed = abs(close - limit_price) < 0.01
        
        # 1. 宏观做功推力 (Macro MFE)
        # 物理意义：每亿成交额推高了多少振幅
        if amount_yi > 0:
            macro_mfe = amplitude / amount_yi
        else:
            macro_mfe = 0.0
        
        # 2. 宏观纯度 (Macro Purity)
        # 物理意义：收盘价在日内振幅中的位置
        if high > low:
            macro_purity = (close - low) / (high - low) * 100
        else:
            macro_purity = 100.0 if change_pct > 0 else 0.0
        
        # 3. 起爆放量倍数 (Vacuum Ratio)
        # 物理意义：当日成交额相对于前5日均额的倍数
        if target_idx >= 5:
            avg_amount_5d = float(daily_df.iloc[target_idx-5:target_idx]['amount'].mean())
            vacuum_ratio = amount / avg_amount_5d if avg_amount_5d > 0 else 1.0
        else:
            vacuum_ratio = 1.0
        
        # 4. 起爆前量比
        # 物理意义：起爆日之前5天的平均成交量与再前20天的比值
        if target_idx >= 25:
            pre_5d_vol = float(daily_df.iloc[target_idx-5:target_idx]['volume'].mean())
            pre_20d_vol = float(daily_df.iloc[target_idx-25:target_idx-5]['volume'].mean())
            pre_volume_ratio = pre_5d_vol / pre_20d_vol if pre_20d_vol > 0 else 1.0
        else:
            pre_volume_ratio = 1.0
        
        result.update({
            'success': True,
            'macro_mfe': macro_mfe,
            'macro_purity': macro_purity,
            'vacuum_ratio': vacuum_ratio,
            'change_pct': change_pct,
            'amplitude': amplitude,
            'amount_yi': amount_yi,
            'is_sealed': is_sealed,
            'pre_volume_ratio': pre_volume_ratio,
        })
        
    except Exception as e:
        pass
    
    return result


def main():
    print("="*70)
    print("CTO V111 日K宏观物理降维对撞机")
    print("="*70)
    
    # 读取暴力真龙样本
    samples_path = os.path.join(ROOT, 'data', 'validation', 'recent_samples_2025_2026.csv')
    df = pd.read_csv(samples_path)
    surge_samples = df[df['label'] == 1].copy()
    
    print(f"\n[样本库] 总计提取待测真龙样本: {len(surge_samples)} 只")
    
    # 获取所有唯一股票代码
    all_stocks = surge_samples['stock_code'].unique().tolist()
    print(f"[股票池] 唯一股票数: {len(all_stocks)} 只")
    
    # 批量下载日K数据（日K没有时间限制）
    print("\n[下载] 批量下载日K数据...")
    for i, stock in enumerate(all_stocks):
        try:
            xtdata.download_history_data(stock, '1d', start_time='20241001', end_time='20260315')
        except Exception:
            pass
        if i % 50 == 0:
            print(f"  下载进度: {i}/{len(all_stocks)}")
    print("[下载] 日K数据下载完成")
    
    # 分析每只股票
    results = []
    
    for idx, row in surge_samples.iterrows():
        stock = row['stock_code']
        target_date = str(row['date'])
        
        if idx % 20 == 0:
            print(f"\n[进度] 处理 {idx}/{len(surge_samples)}...")
        
        try:
            # 获取日K数据
            daily_data = xtdata.get_local_data(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount', 'preClose'],
                stock_list=[stock],
                period='1d',
                start_time='20241001',
                end_time='20260315'
            )
            
            if not daily_data or stock not in daily_data:
                continue
            
            df_d = daily_data[stock]
            if df_d is None or len(df_d) < 10:
                continue
            
            # 分析宏观物理特征
            result = analyze_macro_physics(stock, target_date, df_d)
            if result['success']:
                results.append(result)
                
        except Exception as e:
            continue
    
    # 统计学输出
    print("\n" + "="*70)
    print("【真龙宏观物理光谱结论】")
    print("="*70)
    
    if results:
        res_df = pd.DataFrame(results)
        
        print(f"\n【有效样本数】: {len(res_df)}")
        print(f"\n【宏观物理特征】")
        print(f"  宏观做功推力(Macro MFE)中位数: {res_df['macro_mfe'].median():.4f}")
        print(f"  宏观纯度(Macro Purity)中位数: {res_df['macro_purity'].median():.1f}%")
        print(f"  起爆放量倍数(Vacuum Ratio)中位数: {res_df['vacuum_ratio'].median():.2f}x")
        print(f"  起爆前量比中位数: {res_df['pre_volume_ratio'].median():.2f}x")
        
        print(f"\n【日内特征】")
        print(f"  平均涨幅: {res_df['change_pct'].mean():.2f}%")
        print(f"  平均振幅: {res_df['amplitude'].mean():.2f}%")
        print(f"  平均成交额: {res_df['amount_yi'].mean():.2f}亿")
        print(f"  封板率: {res_df['is_sealed'].sum()}/{len(res_df)} = {res_df['is_sealed'].mean()*100:.1f}%")
        
        # 分组统计
        sealed = res_df[res_df['is_sealed']]
        not_sealed = res_df[~res_df['is_sealed']]
        
        if len(sealed) > 0:
            print(f"\n【封板样本({len(sealed)}只)】")
            print(f"  Macro MFE中位数: {sealed['macro_mfe'].median():.4f}")
            print(f"  宏观纯度中位数: {sealed['macro_purity'].median():.1f}%")
            print(f"  放量倍数中位数: {sealed['vacuum_ratio'].median():.2f}x")
        
        if len(not_sealed) > 0:
            print(f"\n【未封板样本({len(not_sealed)}只)】")
            print(f"  Macro MFE中位数: {not_sealed['macro_mfe'].median():.4f}")
            print(f"  宏观纯度中位数: {not_sealed['macro_purity'].median():.1f}%")
            print(f"  放量倍数中位数: {not_sealed['vacuum_ratio'].median():.2f}x")
        
        # 保存结果
        output_dir = os.path.join(ROOT, 'data', 'research_lab')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'macro_surge_scanner_result.csv')
        res_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存至: {output_path}")
        
    else:
        print("\n【警告】数据提取失败！")


if __name__ == '__main__':
    main()
