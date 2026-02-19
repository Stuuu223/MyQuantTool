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
    """加载单日Tick数据（Level1）"""
    try:
        from xtquant import xtdata
        
        start_time = date_str.replace('-', '') + '093000'
        end_time = date_str.replace('-', '') + '150000'
        
        tick_df = xtdata.get_market_data_ex(
            field_list=['time', 'lastPrice', 'volume', 'amount', 'bidPrice', 'askPrice'],
            stock_list=[stock_code],
            period='tick',
            start_time=start_time,
            end_time=end_time
        )
        
        if stock_code in tick_df and not tick_df[stock_code].empty:
            df = tick_df[stock_code].copy()
            df = df.reset_index()
            df['timestamp'] = pd.to_datetime(df['index'], format='%Y%m%d%H%M%S')
            df = df[df['lastPrice'] > 0].copy()  # 只保留成交Tick
            df = df.sort_values('timestamp').reset_index(drop=True)
            return df
        
        return None
        
    except Exception as e:
        logger.warning(f"  ⚠️ {stock_code} {date_str} Tick数据加载失败: {e}")
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

def run_wanzhu_behavior_replay(stock_codes: List[str], start_date: str, end_date: str) -> Dict:
    """运行顽主150只58天Tick行为回放"""
    
    results = {
        'meta': {
            'version': 'V1.0 (Level1-only)',
            'generated_at': datetime.now().isoformat(),
            'total_stocks': len(stock_codes),
            'start_date': start_date,
            'end_date': end_date,
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
        'stock_records': {}
    }
    
    # 日期范围
    date_range = pd.date_range(start_date, end_date, freq='D')
    results['summary']['total_days'] = len(date_range)
    
    # 统计数据
    signal_days_count = set()
    attack_score_counts = {'STRONG': 0, 'MEDIUM': 0, 'WEAK': 0}
    
    logger.info(f"🚀 开始行为回放: {len(stock_codes)} 只股票, {len(date_range)} 天")
    logger.info(f"{'='*60}")
    
    # 遍历每只股票
    for stock_idx, stock_code in enumerate(stock_codes, 1):
        logger.info(f"\n[{stock_idx}/{len(stock_codes)}] {stock_code}")
        
        stock_records = []
        
        # 遍历每个交易日
        for date in date_range:
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
            
            # 检测诱多（价量模式）
            trap_reasons = detect_trap_price_volume(tick_df, CONFIG['trap_params'])
            is_trap = len(trap_reasons) > 0
            
            # 记录结果
            if signals:
                record = {
                    'code': stock_code,
                    'date': date_str,
                    'signals': signals,
                    'attack_score': attack_score,
                    'is_trap': is_trap,
                    'trap_reasons': trap_reasons,
                    'notes': 'Level1-only proxy, no real capital flow numbers'
                }
                
                results['daily_records'].append(record)
                stock_records.append(record)
                
                # 统计
                signal_days_count.add(date_str)
                attack_score_counts[attack_score] += 1
                if is_trap:
                    results['summary']['trap_days'] += 1
        
        # 汇总股票记录
        if stock_records:
            results['stock_records'][stock_code] = {
                'total_signals': len(stock_records),
                'trap_count': sum(1 for r in stock_records if r['is_trap']),
                'signals': stock_records
            }
        
        # 显示进度
        if stock_idx % 10 == 0 or stock_idx == len(stock_codes):
            logger.info(f"  进度: {stock_idx}/{len(stock_codes)}")
    
    # 更新汇总统计
    results['summary']['total_signals'] = len(results['daily_records'])
    results['summary']['strong_attack_days'] = attack_score_counts['STRONG']
    results['summary']['medium_attack_days'] = attack_score_counts['MEDIUM']
    results['summary']['weak_attack_days'] = attack_score_counts['WEAK']
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✅ 行为回放完成")
    logger.info(f"  总信号天数: {results['summary']['total_signals']}")
    logger.info(f"  强攻击: {results['summary']['strong_attack_days']}")
    logger.info(f"  中攻击: {results['summary']['medium_attack_days']}")
    logger.info(f"  弱攻击: {results['summary']['weak_attack_days']}")
    logger.info(f"  TRAP过滤: {results['summary']['trap_days']}")
    logger.info(f"{'='*60}")
    
    return results

# ================= 主函数 =================

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("顽主150只58天Tick行为回放（Level1最小方案）")
    logger.info("=" * 60)
    
    # 加载顽主股票列表
    stock_codes = load_wanzhu_stocks(CONFIG['wanzhu_csv'])
    if not stock_codes:
        logger.error("❌ 没有找到顽主股票列表")
        return
    
    # 运行行为回放
    results = run_wanzhu_behavior_replay(
        stock_codes=stock_codes,
        start_date=CONFIG['start_date'],
        end_date=CONFIG['end_date']
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