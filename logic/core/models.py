"""
DTO数据整流罩 - 统一数据模型与单位换算

【CTO绝对整流罩】
唯一职责：吸收QMT一切脏数据，吐出绝对干净、统一量纲的物理值！
任何业务引擎（V20等）只准接收此类，严禁直接读取原始字典！

Author: CTO
Date: 2026-02-28
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np


@dataclass
class QMTStockSnapshot:
    """
    【CTO绝对整流罩】QMT股票快照数据模型
    
    设计原则：
    1. 吸收一切QMT脏数据（NaN、Inf、空字符串、错误单位）
    2. 通过property自动清洗、纠偏、转换
    3. 输出绝对干净的float和单位统一的物理值
    """
    stock_code: str
    raw_price: float = 0.0
    raw_pre_close: float = 0.0
    raw_open: float = 0.0
    raw_high: float = 0.0
    raw_low: float = 0.0
    raw_volume: float = 0.0        # QMT原始成交量（手/股 混沌态）
    raw_amount: float = 0.0        # QMT原始成交额（元）
    raw_float_volume: float = 0.0  # QMT原始流通股本（混沌态：万股或股）
    raw_avg_vol_5d: float = 0.0    # 5日均量（混沌态）
    
    def _safe_float(self, val) -> float:
        """【CTO铁血清洗】：绝不允许NaN或Inf进入系统！"""
        if pd.isna(val) or np.isinf(val):
            return 0.0
        try:
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    @property
    def price(self) -> float:
        """当前价格（元）"""
        return self._safe_float(self.raw_price)
    
    @property
    def pre_close(self) -> float:
        """昨收价（元）"""
        return self._safe_float(self.raw_pre_close)
    
    @property
    def open_price(self) -> float:
        """开盘价（元），无效时 fallback 到昨收"""
        op = self._safe_float(self.raw_open)
        return op if op > 0 else self.pre_close
    
    @property
    def high(self) -> float:
        """最高价（元），无效时 fallback 到当前价"""
        h = self._safe_float(self.raw_high)
        return h if h > 0 else self.price
    
    @property
    def low(self) -> float:
        """最低价（元），无效时 fallback 到当前价"""
        l = self._safe_float(self.raw_low)
        return l if l > 0 else self.price
    
    @property
    def amount(self) -> float:
        """成交额（元）"""
        return self._safe_float(self.raw_amount)
    
    @property
    def turnover_rate(self) -> float:
        """
        【CTO单位自适应纠偏引擎】：彻底消灭0.08%的畸形换手率！
        
        返回：换手率百分比（0~100之间）
        """
        vol = self._safe_float(self.raw_volume)
        float_vol = self._safe_float(self.raw_float_volume)
        
        if float_vol <= 0 or vol <= 0:
            return 0.0
        
        # 暴力纠偏法则：真实A股单日换手率极大概率在0.5%~100%之间
        # 假设：volume是手（100股），float_vol是股
        t_rate = (vol * 100 / float_vol) * 100
        
        # 向上异常拦截（算太大了，可能float_vol单位是万股）
        if t_rate > 100.0:
            t_rate = t_rate / 10000.0
        
        # 向下异常拦截（消灭0.08%，可能volume单位直接是股）
        if 0 < t_rate < 0.5:
            # 假设volume单位是股，重新计算
            t_rate = (vol / float_vol) * 100
            
            # 如果还是小，再查一次float_vol是不是带了手
            if t_rate < 0.1:
                t_rate = t_rate * 100
        
        return max(0.0, min(t_rate, 100.0))  # 封死在0~100之间！
    
    @property
    def volume_ratio(self) -> float:
        """
        量比（当前成交量/5日均量）
        
        返回：量比值（0~100之间，正常值通常在0.5~50）
        """
        vol = self._safe_float(self.raw_volume)
        avg_vol = self._safe_float(self.raw_avg_vol_5d)
        
        if avg_vol <= 0 or vol <= 0:
            return 0.0
        
        # 同单位下直接相除
        ratio = vol / avg_vol
        
        return max(0.0, min(ratio, 100.0))
    
    @property
    def change_pct(self) -> float:
        """涨跌幅百分比"""
        if self.pre_close <= 0:
            return 0.0
        return ((self.price - self.pre_close) / self.pre_close) * 100
    
    @property
    def is_valid(self) -> bool:
        """【CTO系统级死票过滤器】判断是否为有效股票"""
        return (
            self.price > 0 and
            self.pre_close > 0 and
            self.turnover_rate > 0 and
            self.volume_ratio > 0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，供引擎使用"""
        return {
            'stock_code': self.stock_code,
            'price': self.price,
            'pre_close': self.pre_close,
            'open_price': self.open_price,
            'high': self.high,
            'low': self.low,
            'amount': self.amount,
            'turnover_rate': self.turnover_rate,
            'volume_ratio': self.volume_ratio,
            'change_pct': self.change_pct,
            'is_valid': self.is_valid
        }


@dataclass
class V20ScoreResult:
    """
    V20评分结果数据模型
    
    确保所有评分输出都是干净的float，无NaN/Inf
    """
    stock_code: str
    final_score: float = 0.0
    price: float = 0.0
    change_pct: float = 0.0
    inflow_ratio: float = 0.0
    ratio_stock: float = 0.0
    sustain_ratio: float = 0.0
    mfe: float = 0.0
    tag: str = "复盘"
    
    def __post_init__(self):
        """初始化后强制清洗所有数值"""
        self.final_score = self._safe_float(self.final_score)
        self.price = self._safe_float(self.price)
        self.change_pct = self._safe_float(self.change_pct)
        self.inflow_ratio = self._safe_float(self.inflow_ratio)
        self.ratio_stock = self._safe_float(self.ratio_stock)
        self.sustain_ratio = self._safe_float(self.sustain_ratio)
        self.mfe = self._safe_float(self.mfe)
    
    def _safe_float(self, val) -> float:
        """安全转换为float"""
        if pd.isna(val) or np.isinf(val):
            return 0.0
        try:
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'final_score': round(self.final_score, 2),
            'price': round(self.price, 2),
            'change_pct': round(self.change_pct, 2),
            'inflow_ratio': round(self.inflow_ratio, 2),
            'ratio_stock': round(self.ratio_stock, 2),
            'sustain_ratio': round(self.sustain_ratio, 2),
            'mfe': round(self.mfe, 2),
            'tag': self.tag
        }


# 便捷函数
def create_snapshot_from_qmt(stock_code: str, daily_df: pd.DataFrame, 
                             float_volume: float, avg_vol_5d: float) -> QMTStockSnapshot:
    """
    从QMT数据创建StockSnapshot
    
    Args:
        stock_code: 股票代码
        daily_df: 日K DataFrame
        float_volume: 流通股本
        avg_vol_5d: 5日均量
    
    Returns:
        QMTStockSnapshot实例
    """
    if daily_df is None or daily_df.empty:
        return QMTStockSnapshot(stock_code=stock_code)
    
    try:
        last_row = daily_df.iloc[-1]
        return QMTStockSnapshot(
            stock_code=stock_code,
            raw_price=last_row.get('close', 0),
            raw_pre_close=last_row.get('preClose', 0),
            raw_open=last_row.get('open', 0),
            raw_high=last_row.get('high', 0),
            raw_low=last_row.get('low', 0),
            raw_volume=last_row.get('volume', 0),
            raw_amount=last_row.get('amount', 0),
            raw_float_volume=float_volume,
            raw_avg_vol_5d=avg_vol_5d
        )
    except Exception:
        return QMTStockSnapshot(stock_code=stock_code)
