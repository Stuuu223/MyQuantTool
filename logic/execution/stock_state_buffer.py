# -*- coding: utf-8 -*-
"""
StockStateBuffer - 股票滚动历史状态缓冲区

【CTO V213 架构迁移】
从 tools/mock_live_runner.py 迁移到 logic/execution/
支持 TriggerValidator 所需的历史数据维护

Author: CTO架构组
Date: 2026-03-18
Version: 1.0.0
"""

from typing import List, Dict
from datetime import datetime
import bisect


class StockStateBuffer:
    """
    单只股票的滚动历史状态缓冲区。

    TriggerValidator.check_all_triggers() 需要：
      - price_history        最近N分钟价格序列
      - recent_mfe_list      最近N分钟MFE序列
      - recent_volume_ratios 最近N分钟量比序列
      - vwap                 当前成本均价（累计额/累计量）
    """
    WINDOW = 30  # 保留30分钟历史

    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self.price_history: List[float] = []
        self.mfe_history: List[float] = []
        self.volume_ratio_history: List[float] = []
        self.last_price: float = 0.0
        self.last_mfe: float = 0.0

    def update(self, price: float, mfe: float, sustain_ratio: float):
        """每分钟调用一次，推入最新数据"""
        self.price_history.append(price)
        self.mfe_history.append(mfe)
        self.volume_ratio_history.append(sustain_ratio)
        self.last_price = price
        self.last_mfe = mfe

        if len(self.price_history) > self.WINDOW:
            self.price_history.pop(0)
            self.mfe_history.pop(0)
            self.volume_ratio_history.pop(0)

    def get_vwap(self, tick_list: List[Dict], current_time: datetime, parse_fn,
                 time_index: List = None) -> float:
        """
        计算当日截止当前时刻的VWAP（成交额加权均价）。
        QMT amount 是累计值，取最新快照即可。
        使用 bisect 二分查找替代线性扫描（O(log n) vs O(n)）
        """
        if not tick_list:
            return self.last_price

        if time_index:
            # 使用预解析时间索引 + bisect
            idx = bisect.bisect_right(time_index, current_time) - 1
            if idx >= 0:
                total_amount = tick_list[idx]['amount']
                total_volume = tick_list[idx].get('volume', 0)
                if total_volume > 0:
                    return total_amount / total_volume
        else:
            # 回退到线性扫描（兼容旧调用）
            total_amount = 0.0
            total_volume = 0
            for tick in tick_list:
                try:
                    if parse_fn(tick['time']) <= current_time:
                        total_amount = tick['amount']
                        total_volume = tick.get('volume', 0)
                except Exception:
                    continue
            if total_volume > 0:
                return total_amount / total_volume
        return self.last_price

    def get_current_slope(self) -> float:
        """最近3分钟价格斜率"""
        if len(self.price_history) < 3:
            return 0.0
        base = self.price_history[-3]
        if base <= 0:
            return 0.0
        return (self.price_history[-1] - base) / base
