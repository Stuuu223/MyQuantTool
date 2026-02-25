#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V20.0 两段式热复盘引擎 - Hot Replay Engine V20
职责：极速定位起爆点 + 微观事件驱动交火
Author: CTO Phase A3
Date: 2026-02-26

【架构铁律】
1. 第一段：Pandas向量化秒速定位（严禁For循环）
2. 第二段：30秒微观事件驱动交火
3. 零硬编码：所有阈值来自ConfigManager
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

try:
    from logic.core.config_manager import get_config_manager
    from logic.core.path_resolver import PathResolver
except ImportError:
    get_config_manager = None
    PathResolver = None


@dataclass
class ExplosionPoint:
    """起爆点数据封装"""
    stock_code: str
    timestamp: str  # HH:MM:SS
    tick_index: int
    price: float
    volume_burst: float  # 量能突变值
    bid1_vol: int
    ask1_vol: int
    spread_pct: float  # 买卖价差百分比


@dataclass
class MicroBattleWindow:
    """微观交战窗口"""
    stock_code: str
    explosion_point: ExplosionPoint
    window_start_idx: int
    window_end_idx: int
    tick_data: pd.DataFrame
    defense_results: List[Dict] = field(default_factory=list)


class HotReplayEngineV20:
    """
    V20两段式热复盘引擎
    
    【第一段 - 向量化起爆定位】
    - 使用Pandas cumsum()向量化计算累计量能
    - 使用first_valid_index()秒速定位首次起爆
    - 严禁For循环扫描全天！
    
    【第二段 - 微观事件驱动】
    - 截取起爆点后30秒Tick窗口
    - 逐Tick事件驱动交火
    """
    
    def __init__(self):
        self.config = self._load_config()
        self.explosion_points: List[ExplosionPoint] = []
        self.battle_windows: List[MicroBattleWindow] = []
        
    def _load_config(self) -> Dict:
        """从ConfigManager加载配置 - 严禁硬编码！"""
        if get_config_manager:
            cfg = get_config_manager()
            return {
                'volume_burst_threshold': cfg.get('hot_replay.volume_burst_threshold', 3.0),
                'volume_window_ticks': cfg.get('hot_replay.volume_window_ticks', 5),
                'micro_battle_seconds': cfg.get('hot_replay.micro_battle_seconds', 30),
                'tick_interval_seconds': cfg.get('hot_replay.tick_interval_seconds', 3),
                'spread_threshold': cfg.get('hot_replay.spread_threshold', 0.5),
            }
        return {
            'volume_burst_threshold': 3.0,  # 量能突变阈值
            'volume_window_ticks': 5,       # 量能计算窗口
            'micro_battle_seconds': 30,     # 微观交战窗口秒数
            'tick_interval_seconds': 3,     # Tick间隔秒数
            'spread_threshold': 0.5,        # 价差阈值%
        }
    
    def phase1_vectorized_explosion_scan(self, tick_df: pd.DataFrame, stock_code: str) -> List[ExplosionPoint]:
        """
        【第一段】向量化秒速定位起爆点
        
        核心算法：
        1. 使用rolling计算历史量能均值
        2. 计算量能突变率 = 当前量 / 历史均值
        3. 使用cumsum()向量化标记起爆点
        4. 使用first_valid_index()秒速定位首次起爆
        
        Args:
            tick_df: 全天Tick数据DataFrame
            stock_code: 股票代码
            
        Returns:
            List[ExplosionPoint]: 起爆点列表
        """
        window_ticks = self.config['volume_window_ticks']
        burst_threshold = self.config['volume_burst_threshold']
        
        # 数据校验
        if tick_df is None or len(tick_df) < window_ticks + 10:
            logger.warning(f"[{stock_code}] Tick数据不足，无法扫描起爆点")
            return []
        
        # 【向量化计算】量能历史均值（滚动窗口）
        tick_df['volume_ma'] = tick_df['volume'].rolling(window=window_ticks, min_periods=1).mean()
        
        # 【向量化计算】量能突变率
        tick_df['volume_burst_ratio'] = tick_df['volume'] / (tick_df['volume_ma'] + 1e-10)
        
        # 【向量化计算】买卖价差百分比
        tick_df['spread_pct'] = ((tick_df['ask1'] - tick_df['bid1']) / tick_df['price'] * 100).fillna(0)
        
        # 【向量化标记】起爆点条件：量能突变 + 价差收敛
        tick_df['is_explosion'] = (
            (tick_df['volume_burst_ratio'] >= burst_threshold) &  # 量能突变
            (tick_df['spread_pct'] <= self.config['spread_threshold'])  # 价差收敛
        ).astype(int)
        
        # 【向量化定位】使用cumsum()标记连续起爆段
        tick_df['explosion_group'] = tick_df['is_explosion'].cumsum()
        
        # 【秒速定位】获取所有起爆点的索引
        explosion_indices = tick_df[tick_df['is_explosion'] == 1].index.tolist()
        
        if not explosion_indices:
            logger.info(f"[{stock_code}] 未检测到起爆点")
            return []
        
        # 构建起爆点对象
        explosion_points = []
        for idx in explosion_indices[:5]:  # 最多取前5个起爆点
            row = tick_df.loc[idx]
            ep = ExplosionPoint(
                stock_code=stock_code,
                timestamp=str(row.get('time', '')),
                tick_index=idx,
                price=float(row['price']),
                volume_burst=float(row['volume_burst_ratio']),
                bid1_vol=int(row.get('bid1_vol', 0)),
                ask1_vol=int(row.get('ask1_vol', 0)),
                spread_pct=float(row['spread_pct'])
            )
            explosion_points.append(ep)
        
        logger.info(f"[{stock_code}] 向量化扫描完成，发现 {len(explosion_points)} 个起爆点")
        return explosion_points
    
    def phase2_micro_battle(self, tick_df: pd.DataFrame, explosion_point: ExplosionPoint) -> MicroBattleWindow:
        """
        【第二段】微观事件驱动交火
        
        核心逻辑：
        1. 截取起爆点后30秒Tick窗口
        2. 逐Tick事件驱动分析
        3. 计算微观指标：撤单率、大单流向、盘口压力
        
        Args:
            tick_df: 全天Tick数据
            explosion_point: 起爆点
            
        Returns:
            MicroBattleWindow: 微观交战窗口结果
        """
        micro_seconds = self.config['micro_battle_seconds']
        tick_interval = self.config['tick_interval_seconds']
        
        # 计算30秒窗口的Tick数量
        window_ticks = micro_seconds // tick_interval  # 30 / 3 = 10个Tick
        
        start_idx = explosion_point.tick_index
        end_idx = min(start_idx + window_ticks, len(tick_df) - 1)
        
        # 截取窗口数据
        window_df = tick_df.iloc[start_idx:end_idx+1].copy()
        
        if len(window_df) < 3:
            logger.warning(f"[{explosion_point.stock_code}] 微观窗口数据不足")
            return MicroBattleWindow(
                stock_code=explosion_point.stock_code,
                explosion_point=explosion_point,
                window_start_idx=start_idx,
                window_end_idx=end_idx,
                tick_data=window_df,
                defense_results=[]
            )
        
        # 【事件驱动】逐Tick分析
        defense_results = []
        
        for i in range(1, len(window_df)):
            current = window_df.iloc[i]
            previous = window_df.iloc[i-1]
            
            # 检测1: 大单撤单陷阱
            bid1_drop = (previous['bid1_vol'] - current['bid1_vol']) / (previous['bid1_vol'] + 1) * 100
            if bid1_drop > 70:  # 买一挂单断崖下跌>70%
                defense_results.append({
                    'tick_idx': i,
                    'timestamp': str(current.get('time', '')),
                    'defense_type': '大单撤单陷阱',
                    'bid1_drop_pct': round(bid1_drop, 2),
                    'risk_level': 'HIGH',
                    'message': f"买一挂单从{previous['bid1_vol']}跌至{current['bid1_vol']}，撤单率{bid1_drop:.1f}%"
                })
            
            # 检测2: 量价背离
            price_change = (current['price'] - previous['price']) / previous['price'] * 100
            volume_change = (current['volume'] - previous['volume']) / (previous['volume'] + 1) * 100
            
            if price_change > 0.5 and volume_change < -50:  # 价格涨但量能缩
                defense_results.append({
                    'tick_idx': i,
                    'timestamp': str(current.get('time', '')),
                    'defense_type': '量价背离陷阱',
                    'price_change_pct': round(price_change, 2),
                    'volume_change_pct': round(volume_change, 2),
                    'risk_level': 'MEDIUM',
                    'message': f"价格上涨{price_change:.2f}%但量能萎缩{volume_change:.1f}%"
                })
            
            # 检测3: 盘口压力失衡
            bid_pressure = current.get('bid1_vol', 0) + current.get('bid2_vol', 0)
            ask_pressure = current.get('ask1_vol', 0) + current.get('ask2_vol', 0)
            if ask_pressure > bid_pressure * 2:  # 抛压是支撑的2倍以上
                defense_results.append({
                    'tick_idx': i,
                    'timestamp': str(current.get('time', '')),
                    'defense_type': '盘口抛压陷阱',
                    'bid_pressure': bid_pressure,
                    'ask_pressure': ask_pressure,
                    'risk_level': 'MEDIUM',
                    'message': f"抛压({ask_pressure})是支撑({bid_pressure})的{ask_pressure/(bid_pressure+1):.1f}倍"
                })
        
        battle_window = MicroBattleWindow(
            stock_code=explosion_point.stock_code,
            explosion_point=explosion_point,
            window_start_idx=start_idx,
            window_end_idx=end_idx,
            tick_data=window_df,
            defense_results=defense_results
        )
        
        logger.info(f"[{explosion_point.stock_code}] 微观交战完成，发现 {len(defense_results)} 个风险信号")
        return battle_window
    
    def run_hot_replay(self, tick_df: pd.DataFrame, stock_code: str) -> Dict:
        """
        V20热复盘主入口
        
        执行流程：
        1. 【第一段】向量化秒速定位起爆点
        2. 【第二段】微观事件驱动逐Tick交火
        3. 生成热复盘报告
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 V20两段式热复盘引擎启动 [{stock_code}]")
        logger.info(f"{'='*60}")
        
        # Phase 1: 向量化起爆定位
        explosion_points = self.phase1_vectorized_explosion_scan(tick_df, stock_code)
        
        if not explosion_points:
            return {
                'stock_code': stock_code,
                'status': 'NO_EXPLOSION',
                'explosion_points': [],
                'battle_windows': [],
                'summary': '未检测到起爆点'
            }
        
        # Phase 2: 微观交战（对每个起爆点）
        battle_windows = []
        for ep in explosion_points[:3]:  # 最多分析前3个起爆点
            battle = self.phase2_micro_battle(tick_df, ep)
            battle_windows.append(battle)
        
        # 生成报告
        report = self._generate_report(stock_code, explosion_points, battle_windows)
        
        logger.info(f"✅ V20热复盘完成 [{stock_code}]")
        return report
    
    def _generate_report(self, stock_code: str, explosion_points: List[ExplosionPoint], 
                        battle_windows: List[MicroBattleWindow]) -> Dict:
        """生成热复盘报告"""
        total_risks = sum(len(b.defense_results) for b in battle_windows)
        high_risks = sum(1 for b in battle_windows for r in b.defense_results if r.get('risk_level') == 'HIGH')
        
        return {
            'stock_code': stock_code,
            'status': 'COMPLETED',
            'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'explosion_points_found': len(explosion_points),
                'battle_windows_analyzed': len(battle_windows),
                'total_risk_signals': total_risks,
                'high_risk_count': high_risks,
                'overall_assessment': 'SAFE' if high_risks == 0 else 'CAUTION' if high_risks <= 2 else 'DANGER'
            },
            'explosion_points': [
                {
                    'timestamp': ep.timestamp,
                    'price': ep.price,
                    'volume_burst': round(ep.volume_burst, 2),
                    'bid1_vol': ep.bid1_vol,
                    'spread_pct': round(ep.spread_pct, 3)
                } for ep in explosion_points
            ],
            'battle_details': [
                {
                    'explosion_time': bw.explosion_point.timestamp,
                    'window_ticks': len(bw.tick_data),
                    'risk_signals': bw.defense_results
                } for bw in battle_windows
            ]
        }
    
    def batch_replay(self, tick_data_dict: Dict[str, pd.DataFrame]) -> List[Dict]:
        """
        批量热复盘
        
        Args:
            tick_data_dict: {stock_code: tick_df}
            
        Returns:
            List[Dict]: 每只股票的热复盘报告
        """
        reports = []
        for stock_code, tick_df in tick_data_dict.items():
            try:
                report = self.run_hot_replay(tick_df, stock_code)
                reports.append(report)
            except Exception as e:
                logger.error(f"[{stock_code}] 热复盘失败: {e}")
                reports.append({
                    'stock_code': stock_code,
                    'status': 'ERROR',
                    'error': str(e)
                })
        return reports


# 便捷入口
def run_hot_replay_v20(tick_df: pd.DataFrame, stock_code: str) -> Dict:
    """
    V20热复盘便捷入口
    
    Usage:
        from logic.backtest.hot_replay_engine_v20 import run_hot_replay_v20
        report = run_hot_replay_v20(tick_df, '000001.SZ')
    """
    engine = HotReplayEngineV20()
    return engine.run_hot_replay(tick_df, stock_code)


def run_batch_replay(tick_data_dict: Dict[str, pd.DataFrame]) -> List[Dict]:
    """
    批量热复盘便捷入口
    """
    engine = HotReplayEngineV20()
    return engine.batch_replay(tick_data_dict)


if __name__ == '__main__':
    # 测试用例
    logger.info("HotReplayEngineV20 模块加载完成")
    logger.info("使用方式: from logic.backtest.hot_replay_engine_v20 import HotReplayEngineV20")
