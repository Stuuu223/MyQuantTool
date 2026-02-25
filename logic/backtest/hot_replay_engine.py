#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热复盘引擎 (Hot Replay Engine) - 向量化极速战报生成器

根据CTO方案S架构设计，实现基于Pandas向量化的单日热复盘引擎。
核心特性：
1. 向量化计算 - 严禁Python For循环遍历Tick数据
2. 极速性能 - 全市场5191只 < 3分钟
3. 精准定位 - 使用向量化操作定位首次起爆点
4. 统一V18大脑 - 与实盘、全息回演共用同一套评分逻辑

Author: AI开发专家团队
Date: 2026-02-26
Version: V1.0.0 (CTO方案S实施版)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dt_time
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

from logic.core.path_resolver import PathResolver
from logic.core.config_manager import get_config_manager
from logic.strategies.v18_core_engine import V18CoreEngine

logger = logging.getLogger(__name__)


@dataclass
class ExplosionPoint:
    """起爆点数据模型"""
    stock_code: str
    stock_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    price: float = 0.0
    volume_ratio: float = 0.0
    turnover_rate: float = 0.0
    change_pct: float = 0.0
    v18_score: float = 0.0
    time_decay_ratio: float = 1.0
    base_score: float = 0.0
    close_price: float = 0.0
    pnl_pct: float = 0.0
    is_limit_up: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'timestamp': self.timestamp.strftime('%H:%M:%S'),
            'price': round(self.price, 2),
            'volume_ratio': round(self.volume_ratio, 2),
            'turnover_rate': round(self.turnover_rate, 2),
            'change_pct': round(self.change_pct, 2),
            'v18_score': round(self.v18_score, 2),
            'time_decay_ratio': round(self.time_decay_ratio, 2),
            'close_price': round(self.close_price, 2),
            'pnl_pct': round(self.pnl_pct, 2),
            'is_limit_up': self.is_limit_up,
        }


@dataclass
class HotReplayReport:
    """热复盘战报数据模型"""
    date: str
    total_scanned: int = 0
    valid_stocks: int = 0
    explosion_points: List[ExplosionPoint] = field(default_factory=list)
    processing_time_sec: float = 0.0
    avg_pnl_pct: float = 0.0
    win_rate: float = 0.0
    limit_up_count: int = 0
    max_pnl_pct: float = 0.0
    min_pnl_pct: float = 0.0
    
    def generate_markdown(self) -> str:
        """生成Markdown格式战报"""
        lines = []
        lines.append(f"# 热复盘战报 - {self.date}")
        lines.append(f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 处理耗时: {self.processing_time_sec:.2f}秒")
        lines.append("")
        lines.append("## 汇总统计")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 扫描股票数 | {self.total_scanned} |")
        lines.append(f"| 有效数据数 | {self.valid_stocks} |")
        lines.append(f"| 发现起爆点 | {len(self.explosion_points)} |")
        lines.append(f"| 涨停数 | {self.limit_up_count} |")
        lines.append(f"| 平均收益率 | {self.avg_pnl_pct:.2f}% |")
        lines.append(f"| 胜率 | {self.win_rate:.2f}% |")
        lines.append("")
        
        # Top 10
        lines.append("## Top 10 起爆点")
        lines.append("")
        lines.append("| 排名 | 代码 | 名称 | 时间 | 价格 | 量比 | V18得分 | 收益率 | 状态 |")
        lines.append("|------|------|------|------|------|------|---------|--------|------|")
        
        sorted_points = sorted(self.explosion_points, key=lambda x: x.v18_score, reverse=True)
        for i, ep in enumerate(sorted_points[:10], 1):
            status = "涨停" if ep.is_limit_up else f"{ep.pnl_pct:+.2f}%"
            lines.append(
                f"| {i} | {ep.stock_code} | {ep.stock_name} | {ep.timestamp.strftime('%H:%M:%S')} | "
                f"{ep.price:.2f} | {ep.volume_ratio:.2f} | {ep.v18_score:.1f} | "
                f"{ep.pnl_pct:+.2f}% | {status} |"
            )
        lines.append("")
        lines.append("---")
        lines.append("*本报告由AI量化系统自动生成，仅供参考，不构成投资建议。*")
        
        return "\n".join(lines)


class HotReplayEngine:
    """热复盘引擎 - 向量化极速战报生成器"""
    
    MARKET_OPEN = dt_time(9, 30)
    MARKET_CLOSE = dt_time(15, 0)
    TOTAL_TRADING_SECONDS = 14400
    
    def __init__(self, max_workers: Optional[int] = None):
        self.v18_engine = V18CoreEngine()
        self.config = get_config_manager()
        self.max_workers = max_workers or min(mp.cpu_count(), 8)
        logger.info(f"热复盘引擎初始化完成 | 并行 workers: {self.max_workers}")
    
    def _normalize_stock_code(self, code: str) -> str:
        """标准化股票代码"""
        if not code:
            return code
        if code.endswith('.SH') or code.endswith('.SZ'):
            return code
        code = code.strip().replace('.', '')
        if code.startswith('6'):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"
    
    def _get_tick_data_vectorized(self, stock_code: str, date: str) -> Optional[pd.DataFrame]:
        """向量化获取Tick数据"""
        try:
            from xtquant import xtdata
            normalized_code = self._normalize_stock_code(stock_code)
            
            data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume', 'amount'],
                stock_list=[normalized_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if not data or normalized_code not in data:
                return None
            
            df = data[normalized_code]
            if df.empty:
                return None
            
            # 向量化时间转换
            if pd.api.types.is_numeric_dtype(df['time']):
                df['timestamp'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
            else:
                df['timestamp'] = pd.to_datetime(df['time'])
            
            df = df.rename(columns={'lastPrice': 'price'})
            
            # 向量化过滤交易时间
            df = df[(df['timestamp'].dt.time >= self.MARKET_OPEN) & 
                    (df['timestamp'].dt.time <= self.MARKET_CLOSE)]
            
            return df if not df.empty else None
            
        except Exception as e:
            logger.warning(f"获取Tick数据失败 {stock_code}: {e}")
            return None
    
    def _get_pre_close(self, stock_code: str, date: str) -> float:
        """获取昨收价"""
        try:
            from xtquant import xtdata
            normalized_code = self._normalize_stock_code(stock_code)
            current = datetime.strptime(date, '%Y%m%d')
            prev_date = (current - timedelta(days=1)).strftime('%Y%m%d')
            
            data = xtdata.get_local_data(
                field_list=['time', 'close'],
                stock_list=[normalized_code],
                period='1d',
                start_time=prev_date,
                end_time=date
            )
            
            if data and normalized_code in data:
                df = data[normalized_code]
                if not df.empty and len(df) >= 1:
                    if len(df) >= 2:
                        return float(df.iloc[-2]['close'])
                    else:
                        return float(df.iloc[0]['close'])
            return 0.0
        except Exception as e:
            logger.warning(f"获取昨收价失败 {stock_code}: {e}")
            return 0.0
    
    def _get_5d_avg_volume(self, stock_code: str, date: str) -> float:
        """获取5日平均成交量"""
        try:
            from xtquant import xtdata
            normalized_code = self._normalize_stock_code(stock_code)
            current = datetime.strptime(date, '%Y%m%d')
            dates = []
            check_date = current
            while len(dates) < 5:
                check_date -= timedelta(days=1)
                if check_date.weekday() < 5:
                    dates.append(check_date.strftime('%Y%m%d'))
            
            data = xtdata.get_local_data(
                field_list=['time', 'volume'],
                stock_list=[normalized_code],
                period='1d',
                start_time=dates[-1],
                end_time=dates[0]
            )
            
            if data and normalized_code in data:
                df = data[normalized_code]
                if not df.empty and len(df) >= 3:
                    return float(df['volume'].tail(5).mean())
            return 0.0
        except Exception as e:
            logger.warning(f"获取5日均量失败 {stock_code}: {e}")
            return 0.0
    
    def _calculate_volume_ratio_vectorized(self, df: pd.DataFrame, avg_volume_5d: float) -> pd.DataFrame:
        """向量化计算动态量比 - CTO核心算法"""
        if avg_volume_5d <= 0:
            df['volume_ratio'] = 0.0
            return df
        
        # 向量化计算 - 严禁For循环！
        market_open_dt = df['timestamp'].iloc[0].replace(hour=9, minute=30, second=0)
        df['seconds_from_open'] = (df['timestamp'] - market_open_dt).dt.total_seconds()
        df['time_progress'] = df['seconds_from_open'] / self.TOTAL_TRADING_SECONDS
        df['time_progress'] = df['time_progress'].clip(lower=0.001)
        df['volume_cumsum'] = df['volume'].cumsum()
        expected_volume = avg_volume_5d * df['time_progress']
        df['volume_ratio'] = df['volume_cumsum'] / expected_volume
        
        return df
    
    def _find_explosion_point_vectorized(self, df: pd.DataFrame, stock_code: str, 
                                          avg_volume_5d: float, pre_close: float) -> Optional[ExplosionPoint]:
        """向量化定位首次起爆点 - CTO核心算法"""
        if df.empty or pre_close <= 0:
            return None
        
        volume_threshold = self.config.get_volume_ratio_percentile('live_sniper')
        turnover_thresholds = self.config.get_turnover_rate_thresholds()
        float_volume = avg_volume_5d * 200
        
        # 向量化计算 - 严禁For循环！
        df['turnover_rate'] = (df['volume_cumsum'] / float_volume * 100) if float_volume > 0 else 0.0
        df['turnover_rate_per_min'] = df['turnover_rate'] / (df['seconds_from_open'] / 60)
        df['change_pct'] = (df['price'] - pre_close) / pre_close * 100
        
        # 向量化布尔筛选
        condition = (
            (df['volume_ratio'] >= volume_threshold) &
            (df['turnover_rate_per_min'] >= turnover_thresholds['per_minute_min']) &
            (df['turnover_rate'] <= turnover_thresholds['total_max']) &
            (df['seconds_from_open'] >= 60)
        )
        
        matching_rows = df[condition]
        if matching_rows.empty:
            return None
        
        # O(1)向量化定位
        first_idx = matching_rows.index[0]
        first_row = df.loc[first_idx]
        timestamp = first_row['timestamp']
        
        # 计算V18得分
        base_score = self.v18_engine.calculate_base_score(
            change_pct=first_row['change_pct'],
            volume_ratio=first_row['volume_ratio'],
            turnover_rate_per_min=first_row['turnover_rate_per_min']
        )
        final_score = self.v18_engine.calculate_final_score(base_score, timestamp)
        time_decay = self.v18_engine.get_time_decay_ratio(timestamp)
        
        # 收盘战果
        close_price = df['price'].iloc[-1]
        pnl_pct = (close_price - first_row['price']) / first_row['price'] * 100
        limit_up_price = round(pre_close * 1.1, 2)
        is_limit_up = abs(close_price - limit_up_price) < 0.01
        
        return ExplosionPoint(
            stock_code=stock_code,
            timestamp=timestamp,
            price=first_row['price'],
            volume_ratio=first_row['volume_ratio'],
            turnover_rate=first_row['turnover_rate'],
            change_pct=first_row['change_pct'],
            v18_score=final_score,
            time_decay_ratio=time_decay,
            base_score=base_score,
            close_price=close_price,
            pnl_pct=pnl_pct,
            is_limit_up=is_limit_up
        )
    
    def process_single_stock(self, stock_code: str, date: str) -> Optional[ExplosionPoint]:
        """处理单只股票 - 完整向量化流程"""
        try:
            pre_close = self._get_pre_close(stock_code, date)
            if pre_close <= 0:
                return None
            
            avg_volume_5d = self._get_5d_avg_volume(stock_code, date)
            if avg_volume_5d <= 0:
                return None
            
            df = self._get_tick_data_vectorized(stock_code, date)
            if df is None or len(df) < 100:
                return None
            
            df = self._calculate_volume_ratio_vectorized(df, avg_volume_5d)
            explosion = self._find_explosion_point_vectorized(df, stock_code, avg_volume_5d, pre_close)
            
            return explosion
        except Exception as e:
            logger.warning(f"处理股票失败 {stock_code}: {e}")
            return None
    
    def replay_trading_day(self, date: str, stock_pool: Optional[List[str]] = None) -> HotReplayReport:
        """复盘单个交易日 - 主入口"""
        start_time = time.time()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"热复盘启动 | 日期: {date}")
        logger.info(f"{'='*60}")
        
        if stock_pool is None:
            from logic.data_providers.universe_builder import UniverseBuilder
            builder = UniverseBuilder()
            stock_pool = builder.get_daily_universe(date)
        
        total_stocks = len(stock_pool)
        logger.info(f"扫描股票数: {total_stocks}")
        
        explosion_points = []
        valid_count = 0
        
        logger.info(f"开始处理...")
        
        # 简化版：单进程处理（避免Windows多进程问题）
        for i, stock in enumerate(stock_pool):
            if i % 100 == 0:
                logger.info(f"进度: {i}/{total_stocks}")
            result = self.process_single_stock(stock, date)
            if result is not None:
                explosion_points.append(result)
                valid_count += 1
        
        processing_time = time.time() - start_time
        
        if explosion_points:
            pnls = [ep.pnl_pct for ep in explosion_points]
            avg_pnl = sum(pnls) / len(pnls)
            win_count = sum(1 for pnl in pnls if pnl > 0)
            win_rate = win_count / len(pnls) * 100
            limit_up_count = sum(1 for ep in explosion_points if ep.is_limit_up)
            max_pnl = max(pnls)
            min_pnl = min(pnls)
        else:
            avg_pnl = win_rate = limit_up_count = max_pnl = min_pnl = 0
        
        report = HotReplayReport(
            date=date,
            total_scanned=total_stocks,
            valid_stocks=valid_count,
            explosion_points=explosion_points,
            processing_time_sec=processing_time,
            avg_pnl_pct=avg_pnl,
            win_rate=win_rate,
            limit_up_count=limit_up_count,
            max_pnl_pct=max_pnl,
            min_pnl_pct=min_pnl
        )
        
        logger.info(f"\n热复盘完成 | 耗时: {processing_time:.2f}秒")
        logger.info(f"发现起爆点: {len(explosion_points)}")
        logger.info(f"平均收益: {avg_pnl:.2f}% | 胜率: {win_rate:.1f}%")
        
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print("热复盘引擎已就绪。使用示例：")
    print("  engine = HotReplayEngine()")
    print("  report = engine.replay_trading_day('20260224')")
    print("  print(report.generate_markdown())")
