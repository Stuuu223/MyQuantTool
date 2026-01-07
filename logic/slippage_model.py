"""
现实滑点模型 - A股真实滑点模拟
"""

import numpy as np
import pandas as pd
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class RealisticSlippage:
    """
    A 股真实滑点模型
    
    包含三部份成本:
    1. 买卖差价 (bid-ask spread) - 最小，最好估算
    2. 成交量冲击 (market impact)
    3. 时间成本 (execution delay)
    """
    
    @staticmethod
    def estimate_slippage(
        price: float,
        volume: float,
        order_size: float,
        order_type: str = 'market'
    ) -> Tuple[float, dict]:
        """
        估算实际滑点
        
        Args:
            price: 当前价格
            volume: 当前成交量 (手)
            order_size: 委托数量 (手)
            order_type: 'market' 或 'limit'
        
        Returns:
            (总滑点百分比, 详细分析字典)
        """
        
        # 1. 买卖差价 (Bid-Ask Spread)
        # A股 T0 时段 (9:30-11:30) 最小差价 1 个 tick
        # 价格越高 tick 越大
        if price < 10:
            tick = 0.01
        elif price < 100:
            tick = 0.01
        else:
            tick = 0.1
        
        spread_slippage = tick / price  # 买卖差价成本
        
        # 2. 成交量冲击 (Market Impact)
        # 委托量占当日成交量的比例越大，冲击越大
        daily_volume = volume * 240  # 一天大约 240 分钟
        order_impact_ratio = order_size / (daily_volume + 1e-6)
        
        # 平方根模型: 冲击成本 ~ sqrt(委托量 / 日成交量)
        # 例如: 5% 的日成交量 → 冲击约 0.7bps
        market_impact = 0.001 * np.sqrt(order_impact_ratio)
        
        # 3. 时间成本 (Execution Delay)
        # 市价单通常在 100ms 内成交
        # 大单可能需要 1-5 秒
        execution_time = min(1 + order_size / 1000, 5)  # 秒
        
        # 基于价格波动估算时间成本
        # 假设日波动率为 2%，一分钟波动约为 0.02% / 240 ≈ 0.008%
        daily_volatility = 0.02  # A股典型日波动
        time_cost = daily_volatility / 240 * execution_time / 100
        
        # 总滑点
        total_slippage = spread_slippage + market_impact + time_cost
        
        # 详细分析
        breakdown = {
            'spread_slippage': spread_slippage,
            'market_impact': market_impact,
            'time_cost': time_cost,
            'spread_bps': spread_slippage * 10000,
            'impact_bps': market_impact * 10000,
            'time_bps': time_cost * 10000,
            'total_bps': total_slippage * 10000,
        }
        
        logger.info(
            f"滑点估算 | "
            f"价格:{price:.2f} | "
            f"买卖差:{spread_slippage*10000:.1f}bps | "
            f"冲击:{market_impact*10000:.1f}bps | "
            f"时间:{time_cost*10000:.1f}bps | "
            f"总计:{total_slippage*10000:.1f}bps"
        )
        
        return total_slippage, breakdown


class DynamicSlippage:
    """
    A股特殊滑点估算
    
    A股需要 T+1 第二天才能卖出
    """
    
    @staticmethod
    def calculate_st_slippage(symbol: str, target_price: float) -> float:
        """
        计算 ST 股票滑点
        
        Args:
            symbol: 股票代码
            target_price: 目标价格
        
        Returns:
            滑点比例
        """
        # *ST 股票 第个涨停和跌停都是 5% (特殊)
        if symbol.startswith('*ST'):
            return 0.05  # 涨停或跌停
        
        # ST 股票
        if symbol.startswith('ST'):
            return 0.05
        
        # 一般股票
        return 0.10  # 涨停或跌停
    
    @staticmethod
    def calculate_limit_up_slippage(symbol: str) -> float:
        """
        计算涨停板滑点
        
        Args:
            symbol: 股票代码
        
        Returns:
            滑点比例
        """
        if symbol.startswith('*ST'):
            return 0.05  # *ST 涨停 5%
        elif symbol.startswith('ST'):
            return 0.05  # ST 涨停 5%
        else:
            return 0.10  # 一般股票涨停 10%
    
    @staticmethod
    def calculate_limit_down_slippage(symbol: str) -> float:
        """
        计算跌停板滑点
        
        Args:
            symbol: 股票代码
        
        Returns:
            滑点比例
        """
        if symbol.startswith('*ST'):
            return 0.05  # *ST 跌停 5%
        elif symbol.startswith('ST'):
            return 0.05  # ST 跌停 5%
        else:
            return 0.10  # 一般股票跌停 10%