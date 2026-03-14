# -*- coding: utf-8 -*-
"""
【MyQuantLab 模块一】多维时空切片器 (Data Collider Engine)

核心功能：
- 将日K的宏观引力、分K的中观阶梯、Tick的微观尖刺，在同一时间戳下对齐
- 打包成"全息数据舱（Holographic Data Pod）"

设计哲学：
- 香农降维：多源数据统一归一化
- 边界条件：自动处理数据缺失情况

Author: CTO
Date: 2026-03-14
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class HolographicSample:
    """
    全息数据舱 - 三维时空对齐的数据结构
    
    Attributes:
        stock_code: 股票代码
        date: 样本日期
        macro_daily: 过去60天的日K数据（宏观引力、空间差）
        meso_minute: T-1和T0的1m分K数据（量比、MFE）
        micro_tick: 关键拉升段的Tick数据（非牛顿流体粘滞度）
        t_plus_n_return: T+N的真实收益（终极裁判）
        metadata: 元数据（流通市值、行业等）
    """
    stock_code: str
    date: str
    macro_daily: Optional[pd.DataFrame] = None
    meso_minute: Optional[pd.DataFrame] = None
    micro_tick: Optional[pd.DataFrame] = None
    t_plus_n_return: Optional[Dict[int, float]] = None  # {1: +2.5%, 3: +5.1%, 5: +3.2%}
    metadata: Dict = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """检查样本数据是否有效"""
        return (
            self.macro_daily is not None and len(self.macro_daily) >= 20 and
            self.meso_minute is not None and len(self.meso_minute) >= 100
        )
    
    def get_summary(self) -> Dict:
        """获取样本摘要信息"""
        return {
            'stock_code': self.stock_code,
            'date': self.date,
            'daily_bars': len(self.macro_daily) if self.macro_daily is not None else 0,
            'minute_bars': len(self.meso_minute) if self.meso_minute is not None else 0,
            'tick_bars': len(self.micro_tick) if self.micro_tick is not None else 0,
            't_plus_5': self.t_plus_n_return.get(5) if self.t_plus_n_return else None,
        }


class DataCollider:
    """
    数据对撞机 - 自动加载并对齐多维度数据
    
    使用示例:
        collider = DataCollider()
        sample = collider.load_sample('600519.SH', '20260105')
        if sample.is_valid():
            features = extract_features(sample)
    """
    
    def __init__(self, qmt_data_path: Optional[str] = None):
        """
        初始化数据对撞机
        
        Args:
            qmt_data_path: QMT数据路径（可选，默认自动探测）
        """
        self.qmt_data_path = qmt_data_path
        self._cache: Dict[str, HolographicSample] = {}
    
    def load_sample(
        self,
        stock_code: str,
        date: str,
        lookback_days: int = 60,
        include_tick: bool = False
    ) -> HolographicSample:
        """
        加载单个全息样本
        
        Args:
            stock_code: 股票代码
            date: 样本日期 (YYYYMMDD)
            lookback_days: 日K回溯天数
            include_tick: 是否包含Tick数据
        
        Returns:
            HolographicSample: 全息数据舱
        """
        cache_key = f"{stock_code}_{date}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        sample = HolographicSample(stock_code=stock_code, date=date)
        
        try:
            # 1. 加载日K数据（宏观）
            sample.macro_daily = self._load_daily_klines(
                stock_code, date, lookback_days
            )
            
            # 2. 加载分K数据（中观）
            sample.meso_minute = self._load_minute_klines(
                stock_code, date
            )
            
            # 3. 加载Tick数据（微观）- 可选
            if include_tick:
                sample.micro_tick = self._load_tick_data(
                    stock_code, date
                )
            
            # 4. 计算T+N收益
            sample.t_plus_n_return = self._calculate_t_plus_n_return(
                stock_code, date, [1, 3, 5]
            )
            
        except Exception as e:
            logger.error(f"[DataCollider] 加载样本失败 {stock_code} {date}: {e}")
        
        self._cache[cache_key] = sample
        return sample
    
    def load_batch(
        self,
        samples: List[Dict],
        include_tick: bool = False
    ) -> List[HolographicSample]:
        """
        批量加载样本
        
        Args:
            samples: 样本列表 [{'stock_code': 'xxx', 'date': 'yyy'}, ...]
            include_tick: 是否包含Tick数据
        
        Returns:
            List[HolographicSample]: 全息数据舱列表
        """
        results = []
        for s in samples:
            sample = self.load_sample(
                s['stock_code'], 
                s['date'],
                include_tick=include_tick
            )
            if sample.is_valid():
                results.append(sample)
        return results
    
    def _load_daily_klines(
        self, 
        stock_code: str, 
        date: str, 
        lookback_days: int
    ) -> Optional[pd.DataFrame]:
        """加载日K数据"""
        try:
            from xtquant import xtdata
            
            # 计算开始日期
            date_obj = datetime.strptime(date, '%Y%m%d')
            start_date = (date_obj - pd.Timedelta(days=lookback_days * 1.5)).strftime('%Y%m%d')
            
            data = xtdata.get_local_data(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=[stock_code],
                period='1d',
                start_time=start_date,
                end_time=date
            )
            
            if data and stock_code in data:
                df = data[stock_code]
                if df is not None and len(df) > 0:
                    return df.tail(lookback_days)
            
            return None
            
        except Exception as e:
            logger.debug(f"[DataCollider] 日K加载失败: {e}")
            return None
    
    def _load_minute_klines(
        self, 
        stock_code: str, 
        date: str
    ) -> Optional[pd.DataFrame]:
        """加载分K数据"""
        try:
            from xtquant import xtdata
            
            # 加载T-1和T0两天的分K
            date_obj = datetime.strptime(date, '%Y%m%d')
            prev_date = (date_obj - pd.Timedelta(days=3)).strftime('%Y%m%d')  # 往前3天找交易日
            
            data = xtdata.get_local_data(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=[stock_code],
                period='1m',
                start_time=prev_date,
                end_time=date
            )
            
            if data and stock_code in data:
                return data[stock_code]
            
            return None
            
        except Exception as e:
            logger.debug(f"[DataCollider] 分K加载失败: {e}")
            return None
    
    def _load_tick_data(
        self, 
        stock_code: str, 
        date: str
    ) -> Optional[pd.DataFrame]:
        """加载Tick数据"""
        try:
            from xtquant import xtdata
            
            data = xtdata.get_local_data(
                field_list=[],
                stock_list=[stock_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if data and stock_code in data:
                return data[stock_code]
            
            return None
            
        except Exception as e:
            logger.debug(f"[DataCollider] Tick加载失败: {e}")
            return None
    
    def _calculate_t_plus_n_return(
        self,
        stock_code: str,
        date: str,
        n_days: List[int]
    ) -> Optional[Dict[int, float]]:
        """计算T+N收益"""
        try:
            from xtquant import xtdata
            
            date_obj = datetime.strptime(date, '%Y%m%d')
            end_date = (date_obj + pd.Timedelta(days=max(n_days) * 2)).strftime('%Y%m%d')
            
            data = xtdata.get_local_data(
                field_list=['close'],
                stock_list=[stock_code],
                period='1d',
                start_time=date,
                end_time=end_date
            )
            
            if not data or stock_code not in data:
                return None
            
            df = data[stock_code]
            if df is None or len(df) < 2:
                return None
            
            base_close = df['close'].iloc[0]
            returns = {}
            
            for n in n_days:
                if len(df) > n:
                    future_close = df['close'].iloc[n]
                    returns[n] = (future_close - base_close) / base_close * 100
            
            return returns if returns else None
            
        except Exception as e:
            logger.debug(f"[DataCollider] T+N收益计算失败: {e}")
            return None
