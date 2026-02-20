#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
顽主150只58天Tick行为回放（Level1最小方案）

约束条件（严格遵守）：
- ❌ 不import任何资金provider
- ❌ 不写"净流入X万"
- ✅ attack_score只分档（弱/中/强）
- ✅ TrapDetector只用价量模式（surge/flash/wash）

输出格式（每只股票每天）：
{
  "code": "300017.SZ",
  "date": "2026-01-26",
  "signals": ["HALFWAY_BREAKOUT"],
  "attack_score": "STRONG",
  "is_trap": true,
  "trap_reasons": ["SURGE_VOLUME_PULLBACK"],
  "notes": "Level1-only proxy, no real capital flow numbers"
}

检查点（三件事）：
1. 哪几天有信号
2. 这些信号对应的攻击评分是弱/中/强
3. TrapDetector有没有把典型诱多挡住

Author: AI Project Director
Date: 2026-02-19
Version: V1.0 (Level1-only)
"""

import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ================= 配置 =================
CONFIG = {
    'wanzhu_csv': PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv',
    'start_date': '2025-11-21',
    'end_date': '2026-02-13',
    'time_windows': [
        ('09:45', '10:30'),  # 早盘窗口
        ('10:30', '13:30'),  # 中盘窗口
        ('13:30', '14:55'),  # 尾盘窗口
    ],
    'halfway_params': {
        'volatility_threshold': 0.03,      # 波动率阈值
        'volume_surge': 1.5,                # 量能放大倍数
        'breakout_strength': 0.01,          # 突破强度
    },
    'trap_params': {
        'surge_threshold': 0.03,           # 急速拉升阈值（3%）
        'flash_volume_ratio': 5.0,          # 瞬间放量倍数
        'wash_volatility': 0.02,            # 震荡洗盘波动率
    }
}

# ================= 数据加载 =================

def load_wanzhu_stocks(csv_path: Path) -> List[str]:
    """加载顽主150只股票"""
    df = pd.read_csv(csv_path)
    codes = []
    for _, row in df.iterrows():
        code = str(row['code']).zfill(6)
        market = 'SH' if code.startswith('6') else 'SZ'
        codes.append(f'{code}.{market}')
    logger.info(f"✅ 加载顽主榜单: {len(codes)} 只")
    return codes

def load_tick_data(stock_code: str, date_str: str) -> Optional[pd.DataFrame]:
    """加载单日Tick数据（Level1），带字段兜底映射和失败原因分类"""
    try:
        from xtquant import xtdata
        
        start_time = date_str.replace('-', '') + '093000'
        end_time = date_str.replace('-', '') + '150000'
        
        # 尝试获取tick数据
        tick_df = xtdata.get_market_data_ex(
            field_list=['time', 'lastPrice', 'volume', 'amount', 'bidPrice', 'askPrice'],
            stock_list=[stock_code],
            period='tick',
            start_time=start_time,
            end_time=end_time
        )
        
        # 情况1：股票不在返回结果中
        if stock_code not in tick_df:
            logger.warning(f"  ⚠️ {stock_code} {date_str} XTDATA_ERROR: 返回数据中不包含该股票")
            return None
        
        df = tick_df[stock_code]
        
        # 情况2：DataFrame为空（0行）
        if df.empty:
            logger.warning(f"  ⚠️ {stock_code} {date_str} NO_ROWS: DataFrame为空 (形状: {df.shape})")
            return None
        
        # 复制并重置索引
        df = df.copy()
        if 'index' in df.columns or df.index.name in ('time', 'stime'):
            df = df.reset_index()
        
        # 字段兜底映射和检查
        cols = df.columns.tolist()
        
        # 1) time字段检查
        if 'time' not in cols:
            logger.warning(f"  ⚠️ {stock_code} {date_str} MISSING_FIELDS: 缺少time字段")
            return None
        
        # 2) lastPrice字段兜底：如果没有lastPrice但有close，用close替代
        if 'lastPrice' not in cols:
            if 'close' in cols:
                df['lastPrice'] = df['close']
                logger.debug(f"  🔄 {stock_code} {date_str} 使用close字段替代lastPrice")
            else:
                logger.warning(f"  ⚠️ {stock_code} {date_str} MISSING_FIELDS: 缺少lastPrice/close字段")
                return None
        
        # 3) volume字段检查（必需）
        if 'volume' not in cols:
            logger.warning(f"  ⚠️ {stock_code} {date_str} MISSING_FIELDS: 缺少volume字段")
            return None
        
        # 创建时间戳列（支持整数毫秒时间戳和字符串格式）
        if 'timestamp' not in cols:
            try:
                # 尝试解析为整数毫秒时间戳
                if df['time'].dtype in (np.int64, np.float64, int, float):
                    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
                else:
                    # 尝试解析为字符串格式
                    df['timestamp'] = pd.to_datetime(df['time'].astype(str), format='%Y%m%d%H%M%S', errors='coerce')
            except Exception as e:
                logger.warning(f"  ⚠️ {stock_code} {date_str} 时间解析失败: {e}")
                # 如果解析失败，尝试混合格式
                df['timestamp'] = pd.to_datetime(df['time'].astype(str), errors='coerce')
        
        # 检查时间解析是否成功
        if df['timestamp'].isna().all():
            logger.warning(f"  ⚠️ {stock_code} {date_str} 时间解析全部失败，使用原始时间")
            df['timestamp'] = pd.to_datetime(df['time'].astype(str), errors='coerce')
        
        # 只保留有效成交Tick（lastPrice > 0）
        df = df[df['lastPrice'] > 0].copy()
        
        # 如果过滤后为空，返回None
        if df.empty:
            logger.warning(f"  ⚠️ {stock_code} {date_str} NO_ROWS: 过滤后无有效成交Tick")
            return None
        
        # 按时间排序
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        logger.debug(f"  ✅ {stock_code} {date_str} 加载成功: {len(df)} 条Tick数据")
        return df
        
    except Exception as e:
        logger.warning(f"  ⚠️ {stock_code} {date_str} XTDATA_ERROR: {e}")
        return None

# ================= Level1 攻击Proxy计算 =================

def calculate_price_strength(tick_df: pd.DataFrame) -> float:
    """
    计算价格强度（price_strength）
    
    公式：price_strength = (lastPrice - preClose) / preClose
    """
    if tick_df.empty:
        return 0.0
    
    # 使用第一条作为昨收价的proxy（实际应用中应该从日线获取）
    pre_close = tick_df['lastPrice'].iloc[0]
    last_price = tick_df['lastPrice'].iloc[-1]
    
    if pre_close <= 0:
        return 0.0
    
    return (last_price - pre_close) / pre_close

def calculate_bid_pressure(tick_df: pd.DataFrame) -> float:
    """
    计算买盘压强（bid_pressure）
    
    简化版本：统计"主动买单量 - 主动卖单量"的比例
    近似规则：涨价对应买主动、跌价对应卖主动
    """
    if tick_df.empty:
        return 0.0
    
    # 计算价格变化方向
    tick_df['price_change'] = tick_df['lastPrice'].diff().fillna(0)
    
    # 简化：价格上涨对应买主动，下跌对应卖主动
    buy_volume = tick_df[tick_df['price_change'] > 0]['volume'].sum()
    sell_volume = tick_df[tick_df['price_change'] < 0]['volume'].sum()
    total_volume = tick_df['volume'].sum()
    
    if total_volume <= 0:
        return 0.0
    
    # bid_pressure = (买单量 - 卖单量) / 总成交量
    return (buy_volume - sell_volume) / total_volume

def calculate_attack_score(price_strength: float, bid_pressure: float) -> str:
    """
    计算攻击评分（attack_score）
    
    只分档：弱 / 中 / 强
    不暴露内部公式
    
    规则：
    - price_strength和bid_pressure都在历史分布的上20% → 强
    - 只高一个 → 中
    - 都一般 → 弱
    
    简化实现（使用固定阈值）：
    - price_strength > 0.02 且 bid_pressure > 0.1 → 强
    - price_strength > 0.02 或 bid_pressure > 0.1 → 中
    - 其他 → 弱
    """
    if price_strength > 0.02 and bid_pressure > 0.1:
        return "STRONG"
    elif price_strength > 0.02 or bid_pressure > 0.1:
        return "MEDIUM"
    else:
        return "WEAK"

# ================= 信号检测（Halfway） =================

def detect_halfway_signal(tick_df: pd.DataFrame, params: Dict) -> bool:
    """
    检测Halfway信号（只用价量三条件，不引入资金阈值）
    
    三大条件：
    1. 波动率判断: volatility <= volatility_threshold
    2. 量能放大: volume_surge >= volume_surge_threshold
    3. 突破强度: breakout_strength >= breakout_strength_threshold
    """
    if tick_df.empty or len(tick_df) < 5:
        return False
    
    # 1. 计算波动率
    prices = tick_df['lastPrice'].values
    volatility = np.std(prices) / np.mean(prices) if np.mean(prices) > 0 else 0
    
    # 2. 计算量能放大（简单版本：使用成交量分布）
    volumes = tick_df['volume'].values
    volume_surge = np.max(volumes) / np.mean(volumes) if np.mean(volumes) > 0 else 1.0
    
    # 3. 计算突破强度
    breakout_strength = (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
    
    # 三个条件同时满足
    volatility_ok = volatility <= params['volatility_threshold']
    volume_ok = volume_surge >= params['volume_surge']
    breakout_ok = breakout_strength >= params['breakout_strength']
    
    return volatility_ok and volume_ok and breakout_ok

# ================= 诱多检测（TrapDetector - 价量模式） =================

def detect_trap_price_volume(tick_df: pd.DataFrame, params: Dict) -> List[str]:
    """
    检测诱多模式（只用价量模式，不使用真实资金数据）
    
    三种模式：
    1. SURGE_VOLUME_PULLBACK：急速拉升 + 冲高回落（拉高出货）
    2. FLASH_ATTACK：尾盘突然一根冲高
    3. WASH_TRADING：短时间内高频对倒痕迹
    """
    trap_reasons = []
    
    if tick_df.empty or len(tick_df) < 10:
        return trap_reasons
    
    prices = tick_df['lastPrice'].values
    volumes = tick_df['volume'].values
    timestamps = pd.to_datetime(tick_df['index'], format='%Y%m%d%H%M%S')
    
    # 模式1：SURGE_VOLUME_PULLBACK（急速拉升 + 冲高回落）
    # 检测：短时间内涨幅超过阈值，然后回落
    for i in range(5, len(prices) - 5):
        window_prices = prices[i-5:i+5]
        max_price = np.max(window_prices)
        last_price = prices[i+5]
        pre_price = prices[i-5]
        
        surge_strength = (max_price - pre_price) / pre_price if pre_price > 0 else 0
        pullback_strength = (max_price - last_price) / max_price if max_price > 0 else 0
        
        if surge_strength >= params['surge_threshold'] and pullback_strength >= params['surge_threshold']:
            trap_reasons.append("SURGE_VOLUME_PULLBACK")
            break
    
    # 模式2：FLASH_ATTACK（尾盘突然一根冲高）
    # 检测：最后5分钟内突然放量拉升
    if len(prices) >= 5:
        last_5_prices = prices[-5:]
        last_5_volumes = volumes[-5:]
        avg_volume = np.mean(volumes[:-5]) if len(volumes) > 5 else 1.0
        
        max_volume = np.max(last_5_volumes)
        flash_surge = (last_5_prices[-1] - last_5_prices[0]) / last_5_prices[0] if last_5_prices[0] > 0 else 0
        
        if max_volume >= avg_volume * params['flash_volume_ratio'] and flash_surge >= params['surge_threshold']:
            trap_reasons.append("FLASH_ATTACK")
    
    # 模式3：WASH_TRADING（短时间内高频对倒痕迹）
    # 检测：价格频繁波动，成交量放大
    if len(prices) >= 10:
        window_volatility = np.std(prices[-10:]) / np.mean(prices[-10:]) if np.mean(prices[-10:]) > 0 else 0
        avg_volume = np.mean(volumes[:-10]) if len(volumes) > 10 else 1.0
        surge_volume = np.mean(volumes[-10:]) / avg_volume if avg_volume > 0 else 1.0
        
        if window_volatility >= params['wash_volatility'] and surge_volume >= params['flash_volume_ratio']:
            trap_reasons.append("WASH_TRADING")
    
    return trap_reasons

# ================= 行为回放主流程 =================

def run_wanzhu_behavior_replay(stock_codes: List[str], start_date: str, end_date: str, 
                              max_stocks: int = None, max_days: int = None) -> Dict:
    """运行顽主150只58天Tick行为回放
    
    Args:
        stock_codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        max_stocks: 最大股票数量（取前N只）
        max_days: 每只股票最大天数（取最近N个交易日）
    """
    
    # 应用max_stocks限制
    if max_stocks is not None:
        stock_codes = stock_codes[:max_stocks]
    
    results = {
        'meta': {
            'version': 'V1.0 (Level1-only)',
            'generated_at': datetime.now().isoformat(),
            'total_stocks': len(stock_codes),
            'start_date': start_date,
            'end_date': end_date,
            'max_stocks': max_stocks,
            'max_days': max_days,
            'note': 'Level1-only proxy, no real capital flow numbers'
        },
        'summary': {
            'total_days': 0,
            'total_signals': 0,
            'strong_attack_days': 0,
            'medium_attack_days': 0,
            'weak_attack_days': 0,
            'trap_days': 0,
        },
        'daily_records': [],
        'stock_records': {},
        'stock_stats': {}  # 新增：每只股票的行为统计
    }
    
    # 日期范围
    date_range = pd.date_range(start_date, end_date, freq='D')
    results['summary']['total_days'] = len(date_range)
    
    # 统计数据
    signal_days_count = set()
    attack_score_counts = {'STRONG': 0, 'MEDIUM': 0, 'WEAK': 0}
    
    logger.info(f"🚀 开始行为回放: {len(stock_codes)} 只股票, {len(date_range)} 天")
    if max_stocks:
        logger.info(f"  限制: max_stocks={max_stocks}")
    if max_days:
        logger.info(f"  限制: max_days={max_days}")
    logger.info(f"{'='*60}")
    
    # 遍历每只股票
    for stock_idx, stock_code in enumerate(stock_codes, 1):
        logger.info(f"\n[{stock_idx}/{len(stock_codes)}] {stock_code}")
        
        stock_records = []
        
        # 收集该股票有数据的所有交易日
        available_dates = []
        for date in date_range:
            date_str = date.strftime('%Y-%m-%d')
            tick_df = load_tick_data(stock_code, date_str)
            if tick_df is not None and not tick_df.empty:
                available_dates.append(date)
        
        # 应用max_days限制（取最近N个交易日）
        if max_days is not None and len(available_dates) > max_days:
            available_dates = available_dates[-max_days:]
        
        if not available_dates:
            logger.warning(f"  ⚠️  {stock_code} 无可用Tick数据")
            continue
        
        # 遍历每个交易日（已按日期排序）
        stock_records = []
        stock_stats = {
            'signal_days': 0,
            'strong_days': 0,
            'medium_days': 0,
            'weak_days': 0,
            'trap_days': 0,
            'clean_strong_days': 0,  # 强攻击但没被TRAP拦住
            'total_tested_days': len(available_dates)
        }
        
        for date in available_dates:
            date_str = date.strftime('%Y-%m-%d')
            
            # 加载Tick数据
            tick_df = load_tick_data(stock_code, date_str)
            if tick_df is None or tick_df.empty:
                continue
            
            # 检查信号
            signals = []
            if detect_halfway_signal(tick_df, CONFIG['halfway_params']):
                signals.append('HALFWAY_BREAKOUT')
            
            # 计算攻击评分
            price_strength = calculate_price_strength(tick_df)
            bid_pressure = calculate_bid_pressure(tick_df)
            attack_score = calculate_attack_score(price_strength, bid_pressure)
            
            # CTO要求：无信号日attack_score设为WEAK
            if not signals:
                attack_score = 'WEAK'
            
            # 检测诱多（价量模式）
            trap_reasons = detect_trap_price_volume(tick_df, CONFIG['trap_params'])
            is_trap = len(trap_reasons) > 0
            
            # 记录结果
            record = {
                'code': stock_code,
                'date': date_str,
                'signals': signals,
                'attack_score': attack_score,
                'is_trap': is_trap,
                'trap_reasons': trap_reasons,
                'notes': 'Level1-only proxy, no real capital flow numbers'
            }
            
            # 更新股票统计
            if signals:
                stock_records.append(record)
                stock_stats['signal_days'] += 1
                stock_stats[f'{attack_score.lower()}_days'] += 1
                
                # 统计
                signal_days_count.add(date_str)
                attack_score_counts[attack_score] += 1
                
                if is_trap:
                    stock_stats['trap_days'] += 1
                    results['summary']['trap_days'] += 1
                elif attack_score == 'STRONG':
                    # 强攻击但没被TRAP拦住
                    stock_stats['clean_strong_days'] += 1
            else:
                # 无信号日，只统计attack_score（已经是WEAK）
                attack_score_counts[attack_score] += 1
            
            results['daily_records'].append(record)
        
        # 汇总股票记录
        if stock_records:
            results['stock_records'][stock_code] = {
                'total_signals': len(stock_records),
                'trap_count': sum(1 for r in stock_records if r['is_trap']),
                'signals': stock_records
            }
        
        # 保存股票统计
        results['stock_stats'][stock_code] = stock_stats
        
        # 显示进度
        if stock_idx % 10 == 0 or stock_idx == len(stock_codes):
            logger.info(f"  进度: {stock_idx}/{len(stock_codes)}")
    
    # 更新汇总统计
    results['summary']['total_signals'] = len(results['daily_records'])
    results['summary']['strong_attack_days'] = attack_score_counts['STRONG']
    results['summary']['medium_attack_days'] = attack_score_counts['MEDIUM']
    results['summary']['weak_attack_days'] = attack_score_counts['WEAK']
    
    # 计算头部大哥评分和排序
    alpha = 0.5  # TRAP扣分系数
    rankings = []
    
    for stock_code, stats in results['stock_stats'].items():
        if stats['total_tested_days'] == 0:
            continue
        
        # 头部大哥评分 = clean_strong_days - alpha * trap_days
        score = stats['clean_strong_days'] - alpha * stats['trap_days']
        
        # TRAP比例
        trap_ratio = stats['trap_days'] / stats['signal_days'] if stats['signal_days'] > 0 else 0
        
        rankings.append({
            'code': stock_code,
            'score': round(score, 2),
            'signal_days': stats['signal_days'],
            'clean_strong_days': stats['clean_strong_days'],
            'trap_days': stats['trap_days'],
            'trap_ratio': round(trap_ratio, 3),
            'total_tested_days': stats['total_tested_days']
        })
    
    # 按score降序排序（头部大哥）
    rankings.sort(key=lambda x: x['score'], reverse=True)
    results['top_stocks'] = rankings[:20]  # Top 20
    
    # 按trap_ratio降序排序（典型杂毛）
    rankings.sort(key=lambda x: x['trap_ratio'], reverse=True)
    results['junk_stocks'] = rankings[:20]  # Top 20 杂毛
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✅ 行为回放完成")
    logger.info(f"  总信号天数: {results['summary']['total_signals']}")
    logger.info(f"  强攻击: {results['summary']['strong_attack_days']}")
    logger.info(f"  中攻击: {results['summary']['medium_attack_days']}")
    logger.info(f"  弱攻击: {results['summary']['weak_attack_days']}")
    logger.info(f"  TRAP过滤: {results['summary']['trap_days']}")
    
    # 显示Top 5头部大哥
    logger.info(f"\n📊 Top 5 头部大哥（按评分排序）:")
    for i, stock in enumerate(results['top_stocks'][:5], 1):
        logger.info(f"  {i}. {stock['code']}: score={stock['score']}, "
                   f"clean_strong={stock['clean_strong_days']}, "
                   f"trap={stock['trap_days']} ({stock['trap_ratio']:.1%})")
    
    # 显示Top 5典型杂毛
    logger.info(f"\n⚠️  Top 5 典型杂毛（按TRAP比例排序）:")
    for i, stock in enumerate(results['junk_stocks'][:5], 1):
        logger.info(f"  {i}. {stock['code']}: trap_ratio={stock['trap_ratio']:.1%}, "
                   f"trap={stock['trap_days']}/{stock['signal_days']}")
    
    logger.info(f"{'='*60}")
    
    return results

# ================= 配置文件加载 =================

def load_hot_cases_config(config_path: Path) -> Dict:
    """加载必胜样本测试配置"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    logger.info(f"✅ 加载必胜样本配置: {config_path}")
    logger.info(f"  测试用例数: {len(config['test_cases'])}")
    
    return config

def run_hot_cases_replay(config: Dict) -> Dict:
    """运行必胜样本测试"""
    
    test_cases = config['test_cases']
    
    results = {
        'meta': {
            'version': config['meta']['version'],
            'description': config['meta']['description'],
            'generated_at': datetime.now().isoformat(),
            'total_test_cases': len(test_cases),
            'note': config['meta']['note']
        },
        'summary': {
            'total_test_dates': 0,
            'total_signals': 0,
            'strong_attack_days': 0,
            'medium_attack_days': 0,
            'weak_attack_days': 0,
            'trap_days': 0,
        },
        'test_results': []
    }
    
    logger.info(f"🚀 开始必胜样本测试: {len(test_cases)} 只股票")
    logger.info(f"{'='*60}")
    
    # 统计数据
    attack_score_counts = {'STRONG': 0, 'MEDIUM': 0, 'WEAK': 0}
    
    # 遍历每个测试用例
    for case_idx, case in enumerate(test_cases, 1):
        stock_code = case['code']
        stock_name = case['name']
        stock_type = case['type']
        test_dates = case['test_dates']
        expected = case.get('expected_behavior', {})
        
        logger.info(f"\n[{case_idx}/{len(test_cases)}] {stock_code} {stock_name} ({stock_type})")
        
        # 遍历每个测试日期
        for date_str in test_dates:
            if date_str.startswith('YYYY'):
                logger.info(f"  ⏭️  跳过占位日期: {date_str}")
                continue
            
            # 加载Tick数据
            tick_df = load_tick_data(stock_code, date_str)
            if tick_df is None or tick_df.empty:
                logger.warning(f"  ⚠️  {date_str} 无Tick数据")
                continue
            
            # 检查信号
            signals = []
            if detect_halfway_signal(tick_df, CONFIG['halfway_params']):
                signals.append('HALFWAY_BREAKOUT')
            
            # 计算攻击评分
            price_strength = calculate_price_strength(tick_df)
            bid_pressure = calculate_bid_pressure(tick_df)
            attack_score = calculate_attack_score(price_strength, bid_pressure)
            
            # CTO要求：无信号日attack_score设为WEAK
            if not signals:
                attack_score = 'WEAK'
            
            # 检测诱多（价量模式）
            trap_reasons = detect_trap_price_volume(tick_df, CONFIG['trap_params'])
            is_trap = len(trap_reasons) > 0
            
            # 记录结果
            result = {
                'code': stock_code,
                'name': stock_name,
                'type': stock_type,
                'date': date_str,
                'signals': signals,
                'attack_score': attack_score,
                'is_trap': is_trap,
                'trap_reasons': trap_reasons,
                'expected_behavior': expected,
                'notes': 'Level1-only proxy, no real capital flow numbers'
            }
            
            results['test_results'].append(result)
            
            # 统计
            attack_score_counts[attack_score] += 1
            if is_trap:
                results['summary']['trap_days'] += 1
            if signals:
                results['summary']['total_signals'] += 1
            
            # 显示单条结果
            logger.info(f"  {date_str}: signals={signals}, attack={attack_score}, trap={is_trap}")
        
        results['summary']['total_test_dates'] = len(results['test_results'])
    
    # 更新汇总统计
    results['summary']['strong_attack_days'] = attack_score_counts['STRONG']
    results['summary']['medium_attack_days'] = attack_score_counts['MEDIUM']
    results['summary']['weak_attack_days'] = attack_score_counts['WEAK']
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✅ 必胜样本测试完成")
    logger.info(f"  总测试日期: {results['summary']['total_test_dates']}")
    logger.info(f"  总信号数: {results['summary']['total_signals']}")
    logger.info(f"  强攻击: {results['summary']['strong_attack_days']}")
    logger.info(f"  中攻击: {results['summary']['medium_attack_days']}")
    logger.info(f"  弱攻击: {results['summary']['weak_attack_days']}")
    logger.info(f"  TRAP过滤: {results['summary']['trap_days']}")
    logger.info(f"{'='*60}")
    
    return results

# ================= 主函数 =================

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='顽主行为回放（Level1最小方案）')
    parser.add_argument('--config', type=str, help='必胜样本测试配置文件路径')
    parser.add_argument('--max-stocks', type=int, default=None, help='最大股票数量（取前N只）')
    parser.add_argument('--max-days', type=int, default=None, help='每只股票最大天数（取最近N个交易日）')
    args = parser.parse_args()
    
    logger.info("=" * 60)
    if args.config:
        logger.info("必胜样本测试（Level1最小方案）")
    else:
        logger.info("顽主150只58天Tick行为回放（Level1最小方案）")
    logger.info("=" * 60)
    
    if args.config:
        # 必胜样本测试模式
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"❌ 配置文件不存在: {config_path}")
            return
        
        config = load_hot_cases_config(config_path)
        results = run_hot_cases_replay(config)
        
        # 保存报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = PROJECT_ROOT / 'backtest' / 'results' / f'hot_cases_5stocks_{timestamp}.json'
    else:
        # 全量回放模式
        stock_codes = load_wanzhu_stocks(CONFIG['wanzhu_csv'])
        if not stock_codes:
            logger.error("❌ 没有找到顽主股票列表")
            return
        
        results = run_wanzhu_behavior_replay(
            stock_codes=stock_codes,
            start_date=CONFIG['start_date'],
            end_date=CONFIG['end_date'],
            max_stocks=args.max_stocks,
            max_days=args.max_days
        )
        
        # 保存报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = PROJECT_ROOT / 'backtest' / 'results' / f'wanzhu_behavior_replay_{timestamp}.json'
    
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"\n💾 报告已保存: {report_path}")

if __name__ == '__main__':
    main()