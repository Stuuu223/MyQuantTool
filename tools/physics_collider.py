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
            field_list=['open', 'high', 'low', 'close', 'volume', 'amount', 'preClose'],
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
            
        # 【CTO V107修复】用preClose字段获取昨收价，不要用当日收盘价*0.9估算
        if 'preClose' in df_daily.columns:
            prev_close = float(df_daily['preClose'].iloc[0])
        else:
            # 如果没有preClose，尝试从前一天的数据获取
            prev_close = 0.0
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
        # 【CTO V107修复】使用极小容差(0.01元)避免误判接近涨停的价格
        price_tolerance = 0.01  # 固定0.01元容差
        is_limit_up = abs(today_high - limit_price) < price_tolerance or today_high >= limit_price
        result['is_limit_up'] = is_limit_up
        
        if not is_limit_up:
            return result
        
        # 遍历Tick计算板上做功
        # 【CTO修复】QMT Tick的amount/volume是累计值，必须用差分计算增量
        limit_up_amount = 0.0
        limit_up_volume = 0.0
        seal_time = None
        last_limit_up_time = None
        
        # 封板前3分钟流入累计（使用增量）
        pre_seal_inflow = []
        
        prices = df_tick['price'] if 'price' in df_tick.columns else df_tick.get('lastPrice', df_tick.iloc[:, 1])
        volumes = df_tick['volume'] if 'volume' in df_tick.columns else df_tick.iloc[:, 2]
        amounts = df_tick['amount'] if 'amount' in df_tick.columns else df_tick.iloc[:, 3]
        
        prev_amount = 0.0
        prev_volume = 0.0
        
        # 【CTO V107】修复板上成交计算：lastPrice是快照当前价不是成交价
        # 正确方法：首次触及涨停后的所有增量成交都是"板上做功"
        
        for i in range(len(df_tick)):
            try:
                price = float(prices.iloc[i]) if hasattr(prices, 'iloc') else float(prices[i])
                volume = float(volumes.iloc[i]) if hasattr(volumes, 'iloc') else float(volumes[i])
                amount = float(amounts.iloc[i]) if hasattr(amounts, 'iloc') else float(amounts[i])
                
                # 计算增量而非累计
                delta_amount = amount - prev_amount
                delta_volume = volume - prev_volume
                prev_amount = amount
                prev_volume = volume
                
                # 过滤异常增量（负数或超大值）
                if delta_amount < 0 or delta_amount > 1e9:
                    delta_amount = 0
                if delta_volume < 0 or delta_volume > 1e8:
                    delta_volume = 0
                
                # 【CTO V107】正确判断封板：首次触及涨停价
                if seal_time is None:
                    # 封板前，记录流入
                    pre_seal_inflow.append(delta_amount)
                    
                    # 检查是否首次触及涨停
                    if abs(price - limit_price) < price_tolerance:
                        seal_time = i
                        last_limit_up_time = i
                else:
                    # 封板后，所有增量都是板上做功
                    limit_up_amount += delta_amount
                    limit_up_volume += delta_volume
                    last_limit_up_time = i
                        
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


def calc_energy_center_of_mass(stock_code: str, date: str, limit_price: float, prev_close: float) -> Dict:
    """
    【CTO V108 高位承接厚度探测器】
    
    计算全天成交额的"能量重心"，判断是"偷袭"还是"高位维持"。
    
    物理定义：
    - 偷袭：全天水下/低位横盘，尾盘突然拉涨停（无换手，次日易爆头）
    - 高位维持：早盘拉升到高位(10%-15%)，在涨停板下方构筑引力托盘，高位横盘洗盘
    
    判定标准：
    - 能量重心在涨停价80%-95%区间 + 持续>60分钟 = 高位强承接
    - 能量重心在水下或0轴附近 = 偷袭
    
    Args:
        stock_code: 股票代码
        date: 日期
        limit_price: 涨停价
        prev_close: 昨收价
        
    Returns:
        Dict: {
            'energy_center_price': float,      # 能量重心价格
            'energy_center_ratio': float,      # 能量重心相对涨停价位置(0-1)
            'high_altitude_ratio': float,      # 高位区(+10%~涨停)成交占比
            'low_altitude_ratio': float,       # 低位区(水下~+5%)成交占比
            'sustain_type': str,               # '高位强承接' / '偷袭' / '中性'
            'dominant_zone': str,              # 主要做功区域描述
            'zone_distribution': Dict,         # 价格区间成交分布
        }
    """
    result = {
        'energy_center_price': 0.0,
        'energy_center_ratio': 0.0,
        'high_altitude_ratio': 0.0,
        'low_altitude_ratio': 0.0,
        'sustain_type': '未知',
        'dominant_zone': '',
        'zone_distribution': {},
    }
    
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
            return result
            
        df = tick_data[stock_code]
        if df is None or len(df) == 0:
            return result
            
    except Exception as e:
        print(f"[ERROR] 获取Tick数据失败: {e}")
        return result
    
    try:
        # 计算增量成交
        prices = df['lastPrice'] if 'lastPrice' in df.columns else df.get('price', df.iloc[:, 1])
        amounts = df['amount'] if 'amount' in df.columns else df.iloc[:, 3]
        
        # 转换为增量
        prev_amount = 0.0
        price_amount_list = []  # [(price, delta_amount), ...]
        
        for i in range(len(df)):
            try:
                price = float(prices.iloc[i]) if hasattr(prices, 'iloc') else float(prices[i])
                amount = float(amounts.iloc[i]) if hasattr(amounts, 'iloc') else float(amounts[i])
                
                if price <= 0:
                    continue
                    
                delta_amount = amount - prev_amount
                prev_amount = amount
                
                if delta_amount > 0:
                    price_amount_list.append((price, delta_amount))
            except Exception:
                continue
        
        if not price_amount_list:
            return result
        
        # 计算能量重心 (加权平均价格)
        total_amount = sum(amt for _, amt in price_amount_list)
        if total_amount <= 0:
            return result
            
        weighted_sum = sum(price * amt for price, amt in price_amount_list)
        energy_center = weighted_sum / total_amount
        result['energy_center_price'] = energy_center
        result['energy_center_ratio'] = (energy_center - prev_close) / (limit_price - prev_close) if limit_price != prev_close else 0
        
        # 计算价格区间分布
        zones = {
            '水下(<=0%)': (0, prev_close),
            '低位(+0%~+5%)': (prev_close, prev_close * 1.05),
            '中位(+5%~+10%)': (prev_close * 1.05, prev_close * 1.10),
            '高位(+10%~+15%)': (prev_close * 1.10, prev_close * 1.15),
            '超高位(+15%~涨停)': (prev_close * 1.15, limit_price),
            '涨停价': (limit_price, limit_price * 1.01),
        }
        
        zone_amounts = {k: 0.0 for k in zones.keys()}
        
        for price, amt in price_amount_list:
            for zone_name, (low, high) in zones.items():
                if low <= price < high:
                    zone_amounts[zone_name] += amt
                    break
        
        result['zone_distribution'] = {k: v/total_amount*100 for k, v in zone_amounts.items()}
        
        # 计算高位区占比
        high_altitude = zone_amounts['高位(+10%~+15%)'] + zone_amounts['超高位(+15%~涨停)'] + zone_amounts['涨停价']
        result['high_altitude_ratio'] = high_altitude / total_amount * 100
        
        # 计算低位区占比
        low_altitude = zone_amounts['水下(<=0%)'] + zone_amounts['低位(+0%~+5%)']
        result['low_altitude_ratio'] = low_altitude / total_amount * 100
        
        # 判断类型
        energy_ratio = result['energy_center_ratio']
        
        if energy_ratio >= 0.80 and result['high_altitude_ratio'] > 50:
            result['sustain_type'] = '高位强承接'
            result['dominant_zone'] = f'能量重心在涨停价{energy_ratio*100:.0f}%处，高位区成交{result["high_altitude_ratio"]:.1f}%'
        elif energy_ratio <= 0.30 and result['low_altitude_ratio'] > 50:
            result['sustain_type'] = '偷袭'
            result['dominant_zone'] = f'能量重心在涨停价{energy_ratio*100:.0f}%处，低位区成交{result["low_altitude_ratio"]:.1f}%'
        else:
            result['sustain_type'] = '中性'
            result['dominant_zone'] = f'能量重心在涨停价{energy_ratio*100:.0f}%处'
        
    except Exception as e:
        print(f"[ERROR] 计算能量重心失败: {e}")
        
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


def calculate_energy_center_of_mass(stock_code: str, date: str) -> Dict:
    """
    【CTO V108 能量重心探测器】
    
    核心理念：不能只看封板时间，必须看资金在哪个水位做了最大的功！
    - 最大做功区在水下/0轴附近 + 尾盘拉板 = 偷袭（散户词汇，严禁使用）
    - 最大做功区在涨停价80%-95%区间 + 持续>60分钟 = 高位强承接（真空破防）
    
    Args:
        stock_code: 股票代码
        date: 日期
        
    Returns:
        Dict: {
            'energy_center_price': float,      # 能量重心价格
            'energy_center_ratio': float,      # 能量重心相对涨停价比例
            'high_altitude_amount': float,     # 高位(+10%以上)成交额
            'high_altitude_ratio': float,      # 高位成交占比
            'high_altitude_duration_min': float, # 高位停留时间(分钟)
            'sustain_type': str,               # '高位强承接' / '偷袭' / '正常'
            'price_distribution': Dict,        # 价格区间成交分布
        }
    """
    result = {
        'energy_center_price': 0.0,
        'energy_center_ratio': 0.0,
        'high_altitude_amount': 0.0,
        'high_altitude_ratio': 0.0,
        'high_altitude_duration_min': 0.0,
        'sustain_type': '未知',
        'price_distribution': {},
    }
    
    # 获取日K数据
    try:
        daily_data = xtdata.get_local_data(
            field_list=['open', 'high', 'low', 'close', 'volume', 'amount', 'preClose'],
            stock_list=[stock_code],
            period='1d',
            start_time=date,
            end_time=date
        )
        
        if not daily_data or stock_code not in daily_data:
            return result
            
        df_daily = daily_data[stock_code]
        if df_daily is None or len(df_daily) == 0:
            return result
            
        prev_close = float(df_daily['preClose'].iloc[0]) if 'preClose' in df_daily.columns else 0.0
        if prev_close <= 0:
            return result
            
        limit_price = get_limit_up_price(stock_code, prev_close)
        total_amount = float(df_daily['amount'].iloc[0])
        
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
            return result
            
        df_tick = tick_data[stock_code]
        if df_tick is None or len(df_tick) == 0:
            return result
            
    except Exception as e:
        print(f"[ERROR] 获取Tick数据失败: {e}")
        return result
    
    try:
        # 计算增量
        df_tick['delta_amount'] = df_tick['amount'].diff().fillna(0)
        
        # 过滤有效数据
        valid = df_tick[(df_tick['lastPrice'] > 0) & (df_tick['delta_amount'] > 0)].copy()
        
        if len(valid) == 0:
            return result
        
        # 计算价格区间成交分布
        price_bins = {}
        high_altitude_amount = 0.0
        high_altitude_ticks = []
        
        for idx, row in valid.iterrows():
            price = row['lastPrice']
            delta_amt = row['delta_amount']
            
            # 相对昨收涨幅
            if prev_close > 0:
                change_pct = (price - prev_close) / prev_close * 100
            else:
                change_pct = 0
            
            # 按涨幅区间分组
            bin_key = f"{int(change_pct)}%~{int(change_pct)+1}%"
            if bin_key not in price_bins:
                price_bins[bin_key] = {'amount': 0.0, 'count': 0, 'time_spent': 0}
            price_bins[bin_key]['amount'] += delta_amt
            price_bins[bin_key]['count'] += 1
            
            # 高位区间 (+10%以上)
            if change_pct >= 10.0:
                high_altitude_amount += delta_amt
                high_altitude_ticks.append(idx)
        
        # 计算能量重心（加权平均价格）
        if valid['delta_amount'].sum() > 0:
            energy_center_price = (valid['lastPrice'] * valid['delta_amount']).sum() / valid['delta_amount'].sum()
            result['energy_center_price'] = energy_center_price
            result['energy_center_ratio'] = energy_center_price / limit_price if limit_price > 0 else 0
        
        # 高位成交统计
        result['high_altitude_amount'] = high_altitude_amount
        result['high_altitude_ratio'] = high_altitude_amount / total_amount if total_amount > 0 else 0
        
        # 高位停留时间（简化：计算高位区间的Tick数量*3秒）
        if high_altitude_ticks:
            result['high_altitude_duration_min'] = len(high_altitude_ticks) * 3 / 60
        
        result['price_distribution'] = {k: {'amount': v['amount']/1e8, 'count': v['count']} for k, v in price_bins.items()}
        
        # 判定类型
        # 高位强承接：能量重心在涨停价80%-95%，高位成交>50%，停留>60分钟
        if 0.80 <= result['energy_center_ratio'] <= 0.95 and result['high_altitude_ratio'] > 0.5:
            result['sustain_type'] = '高位强承接'
        elif result['energy_center_ratio'] < 0.5:
            result['sustain_type'] = '偷袭'
        else:
            result['sustain_type'] = '正常'
            
    except Exception as e:
        print(f"[ERROR] 计算能量重心失败: {e}")
        
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
