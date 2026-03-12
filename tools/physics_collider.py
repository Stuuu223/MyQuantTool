# -*- coding: utf-8 -*-
"""
CTO V106 高能资金物理对撞机

【核心理念】
- 封单金额只是信号，板上成交额才是实打实的做功和动量
- 持续性 = 惯性的延续
- 缩量到物理临界点，力就不再支持运动

【功能模块】
1. extract_limit_up_work_done: 板上真实做功提取器
2. detect_inertia_depletion: 惯性衰竭探针
3. batch_collider_test: 批量样本对撞测试

【数据源】
- QMT本地Tick数据
- 日K数据用于涨停判断

运行方式：
    python tools/physics_collider.py --stock 300986.SZ --date 20260105
    python tools/physics_collider.py --batch  # 批量对撞测试
"""

import os
import sys
import argparse
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np

# 添加项目根目录到路径
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    import xtquant.xtdata as xtdata
except ImportError:
    print("[ERROR] 无法导入xtquant，请确保在venv_qmt环境中运行")
    sys.exit(1)


def get_limit_up_price(stock_code: str, prev_close: float) -> float:
    """
    计算涨停价
    
    Args:
        stock_code: 股票代码
        prev_close: 昨收价
        
    Returns:
        涨停价 (四舍五入到分)
    """
    # 主板/中小板10%，创业板/科创板20%，ST股5%
    if stock_code.startswith(('30', '68')):
        limit_pct = 0.20
    elif 'ST' in stock_code or 'st' in stock_code:
        limit_pct = 0.05
    else:
        limit_pct = 0.10
    
    limit_price = prev_close * (1 + limit_pct)
    # 四舍五入到分
    return round(limit_price * 100) / 100


def extract_limit_up_work_done(stock_code: str, date: str) -> Dict:
    """
    【板上做功提取器】
    
    遍历当天的全量Tick数据，精准计算：
    1. limit_up_turnover_amount: 严格在涨停价位上成交的总金额（真实做功）
    2. limit_up_acceleration: 封板瞬间前3分钟的资金流入加速度（爆发力）
    3. seal_time: 封板时间
    4. seal_duration_minutes: 封板持续时长
    
    Args:
        stock_code: 股票代码 (如 '300986.SZ')
        date: 日期 (如 '20260105')
        
    Returns:
        Dict: {
            'limit_up_turnover_amount': float,  # 板上成交额（元）
            'limit_up_turnover_volume': float,  # 板上成交量（股）
            'limit_up_acceleration': float,     # 封板前3分钟流入加速度
            'seal_time': str,                   # 封板时间
            'seal_duration_minutes': float,     # 封板持续时长（分钟）
            'total_amount': float,              # 全天成交额
            'limit_up_ratio': float,            # 板上成交占比
            'is_limit_up': bool,                # 是否涨停
            'prev_close': float,                # 昨收价
            'limit_price': float,               # 涨停价
        }
    """
    result = {
        'limit_up_turnover_amount': 0.0,
        'limit_up_turnover_volume': 0.0,
        'limit_up_acceleration': 0.0,
        'seal_time': None,
        'seal_duration_minutes': 0.0,
        'total_amount': 0.0,
        'limit_up_ratio': 0.0,
        'is_limit_up': False,
        'prev_close': 0.0,
        'limit_price': 0.0,
    }
    
    # 获取日K数据确定昨收价和涨停价
    try:
        daily_data = xtdata.get_local_data(
            field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
            stock_list=[stock_code],
            period='1d',
            start_time=date,
            end_time=date
        )
        
        if not daily_data or stock_code not in daily_data:
            print(f"[WARN] {stock_code} {date} 无日K数据")
            return result
            
        df_daily = daily_data[stock_code]
        if df_daily is None or len(df_daily) == 0:
            return result
            
        prev_close = float(df_daily['close'].iloc[0]) * 0.9  # 简化：用当日收盘估算
        today_high = float(df_daily['high'].iloc[0])
        today_close = float(df_daily['close'].iloc[0])
        total_amount = float(df_daily['amount'].iloc[0])
        
        result['total_amount'] = total_amount
        
    except Exception as e:
        print(f"[ERROR] 获取日K数据失败: {e}")
        return result
    
    # 获取Tick数据
    try:
        tick_data = xtdata.get_local_data(
            field_list=[],
            stock_list=[stock_code],
            period='tick',
            start_time=date,
            end_time=date
        )
        
        if not tick_data or stock_code not in tick_data:
            print(f"[WARN] {stock_code} {date} 无Tick数据")
            return result
            
        df_tick = tick_data[stock_code]
        if df_tick is None or len(df_tick) == 0:
            return result
            
    except Exception as e:
        print(f"[ERROR] 获取Tick数据失败: {e}")
        return result
    
    # 解析Tick数据
    # QMT Tick数据字段: time, price, volume, amount, etc.
    try:
        # 确定昨收价（从Tick的第一个价格或日K）
        if 'lastClose' in df_tick.columns:
            prev_close = float(df_tick['lastClose'].iloc[0])
        elif 'open' in df_tick.columns:
            # 用开盘价估算
            pass
        
        result['prev_close'] = prev_close
        limit_price = get_limit_up_price(stock_code, prev_close)
        result['limit_price'] = limit_price
        
        # 判断是否涨停（最高价接近涨停价）
        price_tolerance = limit_price * 0.005  # 0.5%容差
        is_limit_up = abs(today_high - limit_price) < price_tolerance or today_high >= limit_price
        result['is_limit_up'] = is_limit_up
        
        if not is_limit_up:
            return result
        
        # 遍历Tick计算板上做功
        limit_up_amount = 0.0
        limit_up_volume = 0.0
        seal_time = None
        last_limit_up_time = None
        
        # 封板前3分钟流入累计
        pre_seal_inflow = []
        
        prices = df_tick['price'] if 'price' in df_tick.columns else df_tick.get('lastPrice', df_tick.iloc[:, 1])
        volumes = df_tick['volume'] if 'volume' in df_tick.columns else df_tick.iloc[:, 2]
        amounts = df_tick['amount'] if 'amount' in df_tick.columns else df_tick.iloc[:, 3]
        
        for i in range(len(df_tick)):
            try:
                price = float(prices.iloc[i]) if hasattr(prices, 'iloc') else float(prices[i])
                volume = float(volumes.iloc[i]) if hasattr(volumes, 'iloc') else float(volumes[i])
                amount = float(amounts.iloc[i]) if hasattr(amounts, 'iloc') else float(amounts[i])
                
                # 判断是否在涨停价成交
                if abs(price - limit_price) < price_tolerance:
                    limit_up_amount += amount
                    limit_up_volume += volume
                    last_limit_up_time = i
                    
                    if seal_time is None:
                        seal_time = i  # 首次触及涨停
                else:
                    # 非涨停价成交，记录封板前流入
                    if seal_time is None:
                        pre_seal_inflow.append(amount)
                        
            except Exception:
                continue
        
        result['limit_up_turnover_amount'] = limit_up_amount
        result['limit_up_turnover_volume'] = limit_up_volume
        
        if total_amount > 0:
            result['limit_up_ratio'] = limit_up_amount / total_amount
        
        # 计算封板时长（简化：假设3秒一个Tick）
        if seal_time is not None and last_limit_up_time is not None:
            ticks_on_limit = last_limit_up_time - seal_time
            result['seal_duration_minutes'] = ticks_on_limit * 3 / 60
        
        # 计算封板前加速度
        if len(pre_seal_inflow) >= 10:
            # 取最后60个Tick（约3分钟）的流入
            recent_inflow = pre_seal_inflow[-60:] if len(pre_seal_inflow) >= 60 else pre_seal_inflow
            if len(recent_inflow) >= 2:
                # 计算流入速度的变化率
                inflow_series = pd.Series(recent_inflow)
                velocity = inflow_series.diff().dropna()
                if len(velocity) >= 2:
                    acceleration = velocity.diff().dropna().mean()
                    result['limit_up_acceleration'] = acceleration
        
    except Exception as e:
        print(f"[ERROR] 解析Tick数据失败: {e}")
        
    return result


def detect_inertia_depletion(stock_code: str, date: str, prev_work_done: float) -> Dict:
    """
    【惯性衰竭探针】
    
    提取全天分钟级成交量分布，测算动量维持率。
    
    Args:
        stock_code: 股票代码
        date: 日期
        prev_work_done: 昨日板上做功金额
        
    Returns:
        Dict: {
            'momentum_maintenance_rate': float,  # 动量维持率 (当日流入/昨日做功)
            'turnover_ratio_vs_5d': float,       # 换手率 vs 5日均换手
            'volume_acceleration': float,        # 成交量加速度
            'is_depleted': bool,                 # 是否惯性衰竭
            'depletion_signal': str,             # 衰竭信号描述
            'morning_amount': float,             # 早盘成交额
            'afternoon_amount': float,           # 午后成交额
            'morning_afternoon_ratio': float,    # 早盘/午后比值
        }
    """
    result = {
        'momentum_maintenance_rate': 0.0,
        'turnover_ratio_vs_5d': 0.0,
        'volume_acceleration': 0.0,
        'is_depleted': False,
        'depletion_signal': '',
        'morning_amount': 0.0,
        'afternoon_amount': 0.0,
        'morning_afternoon_ratio': 0.0,
    }
    
    # 获取分钟级数据
    try:
        minute_data = xtdata.get_local_data(
            field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
            stock_list=[stock_code],
            period='1m',
            start_time=date,
            end_time=date
        )
        
        if not minute_data or stock_code not in minute_data:
            return result
            
        df = minute_data[stock_code]
        if df is None or len(df) == 0:
            return result
            
    except Exception as e:
        print(f"[ERROR] 获取分钟数据失败: {e}")
        return result
    
    try:
        total_amount = float(df['amount'].sum())
        
        # 动量维持率
        if prev_work_done > 0:
            result['momentum_maintenance_rate'] = total_amount / prev_work_done
        
        # 分时段成交额
        # 假设时间索引或顺序
        n = len(df)
        morning_end = n // 2  # 简化：前一半为早盘
        
        morning_amount = float(df['amount'].iloc[:morning_end].sum())
        afternoon_amount = float(df['amount'].iloc[morning_end:].sum())
        
        result['morning_amount'] = morning_amount
        result['afternoon_amount'] = afternoon_amount
        
        if afternoon_amount > 0:
            result['morning_afternoon_ratio'] = morning_amount / afternoon_amount
        
        # 成交量加速度
        volumes = df['volume'].values.astype(float)
        if len(volumes) >= 3:
            velocity = np.diff(volumes)
            acceleration = np.diff(velocity)
            result['volume_acceleration'] = float(np.mean(acceleration))
        
        # 惯性衰竭判定
        depletion_signals = []
        
        # 信号1：动量维持率过低
        if result['momentum_maintenance_rate'] < 0.3:
            depletion_signals.append(f"动量维持率{result['momentum_maintenance_rate']:.2f}<0.3")
        
        # 信号2：午后成交急剧萎缩
        if result['morning_afternoon_ratio'] > 3.0:
            depletion_signals.append(f"早盘/午后比{result['morning_afternoon_ratio']:.1f}>3.0")
        
        # 信号3：成交量加速度为负且持续
        if result['volume_acceleration'] < -1000:
            depletion_signals.append(f"成交量加速度{result['volume_acceleration']:.0f}<0")
        
        if depletion_signals:
            result['is_depleted'] = True
            result['depletion_signal'] = '; '.join(depletion_signals)
            
    except Exception as e:
        print(f"[ERROR] 计算惯性衰竭指标失败: {e}")
        
    return result


def batch_collider_test(sample_stocks: List[Dict]) -> pd.DataFrame:
    """
    【批量样本对撞测试】
    
    Args:
        sample_stocks: [{'stock': '300986.SZ', 'dates': ['20260105', '20260106', ...]}, ...]
        
    Returns:
        DataFrame: 对撞结果
    """
    results = []
    
    for sample in sample_stocks:
        stock_code = sample['stock']
        dates = sample['dates']
        label = sample.get('label', '')  # '连板' or '断板'
        
        prev_work_done = 0.0
        
        for date in dates:
            print(f"\n{'='*60}")
            print(f"[对撞测试] {stock_code} {date} ({label})")
            print('='*60)
            
            # 提取板上做功
            work_done = extract_limit_up_work_done(stock_code, date)
            
            print(f"  昨收价: {work_done['prev_close']:.2f}")
            print(f"  涨停价: {work_done['limit_price']:.2f}")
            print(f"  是否涨停: {work_done['is_limit_up']}")
            print(f"  板上成交额: {work_done['limit_up_turnover_amount']/100000000:.4f}亿")
            print(f"  板上成交占比: {work_done['limit_up_ratio']*100:.2f}%")
            print(f"  封板加速度: {work_done['limit_up_acceleration']:.2f}")
            print(f"  封板持续: {work_done['seal_duration_minutes']:.1f}分钟")
            
            # 惯性衰竭检测
            inertia = detect_inertia_depletion(stock_code, date, prev_work_done)
            
            print(f"  动量维持率: {inertia['momentum_maintenance_rate']:.2f}")
            print(f"  早盘/午后比: {inertia['morning_afternoon_ratio']:.2f}")
            print(f"  成交加速度: {inertia['volume_acceleration']:.0f}")
            
            if inertia['is_depleted']:
                print(f"  ⚠️ 惯性衰竭信号: {inertia['depletion_signal']}")
            
            # 记录结果
            results.append({
                'stock': stock_code,
                'date': date,
                'label': label,
                'is_limit_up': work_done['is_limit_up'],
                'limit_up_amount_yi': work_done['limit_up_turnover_amount'] / 100000000,
                'limit_up_ratio': work_done['limit_up_ratio'],
                'seal_acceleration': work_done['limit_up_acceleration'],
                'seal_duration_min': work_done['seal_duration_minutes'],
                'momentum_rate': inertia['momentum_maintenance_rate'],
                'morning_afternoon_ratio': inertia['morning_afternoon_ratio'],
                'volume_acceleration': inertia['volume_acceleration'],
                'is_depleted': inertia['is_depleted'],
                'depletion_signal': inertia['depletion_signal'],
            })
            
            # 更新昨日做功
            prev_work_done = work_done['limit_up_turnover_amount']
    
    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description='CTO V106 高能资金物理对撞机')
    parser.add_argument('--stock', type=str, help='股票代码 (如 300986.SZ)')
    parser.add_argument('--date', type=str, help='日期 (如 20260105)')
    parser.add_argument('--batch', action='store_true', help='批量对撞测试')
    
    args = parser.parse_args()
    
    print("="*60)
    print("CTO V106 高能资金物理对撞机")
    print("封单是信号，板上成交才是做功！")
    print("="*60)
    
    if args.batch:
        # 批量对撞测试样本
        sample_stocks = [
            # 志特新材连板期
            {
                'stock': '300986.SZ',
                'dates': ['20260105', '20260106', '20260107', '20260108', '20260109', '20260110'],
                'label': '连板真龙'
            },
            # 顺钠断板
            {
                'stock': '000533.SZ',
                'dates': ['20260311'],
                'label': '断板杂毛'
            },
        ]
        
        df = batch_collider_test(sample_stocks)
        
        print("\n" + "="*60)
        print("【对撞结果汇总】")
        print("="*60)
        print(df.to_string())
        
        # 保存结果
        output_path = os.path.join(ROOT, 'data', 'research_lab', 'physics_collider_result.csv')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存至: {output_path}")
        
    elif args.stock and args.date:
        # 单股票测试
        print(f"\n[单股测试] {args.stock} {args.date}")
        work_done = extract_limit_up_work_done(args.stock, args.date)
        
        print(f"\n板上做功结果:")
        for k, v in work_done.items():
            print(f"  {k}: {v}")
            
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
