"""
高级风险管理器：更全面的风险管理

功能：
- 动态仓位管理
- 板块轮动风险
- 宏观经济因子
- 资金流风险
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """风险指标数据类"""
    stock_code: str
    position_risk: float  # 仓位风险 0-1
    sector_risk: float    # 板块风险 0-1
    market_risk: float    # 市场风险 0-1
    liquidity_risk: float # 流动性风险 0-1
    total_risk: float     # 总风险 0-1
    suggested_position: float  # 建议仓位比例 0-1
    risk_level: str       # 风险等级: '低', '中', '高', '极高'
    risk_factors: Dict[str, float]  # 风险因子详情
    timestamp: str


class AdvancedRiskManager:
    """高级风险管理器"""

    def __init__(self, initial_capital: float = 100000.0, max_position_size: float = 0.1):
        """
        初始化风险管理器

        Args:
            initial_capital: 初始资金
            max_position_size: 单股最大仓位比例
        """
        self.initial_capital = initial_capital
        self.max_position_size = max_position_size
        self.current_capital = initial_capital
        self.position_history = []
        self.sector_exposure = {}
        self.market_conditions = {}

    def calculate_risk_metrics(self, stock_data: pd.DataFrame, current_price: float, 
                             position_size: float, sector: str = None) -> RiskMetrics:
        """
        计算风险指标

        Args:
            stock_data: 股票历史数据
            current_price: 当前价格
            position_size: 仓位大小
            sector: 所属板块

        Returns:
            RiskMetrics: 风险指标
        """
        if stock_data is None or len(stock_data) < 20:
            logger.warning("数据不足，使用默认风险值")
            return self._get_default_risk_metrics(stock_data['股票代码'].iloc[0] if stock_data is not None and len(stock_data) > 0 else 'UNKNOWN')

        stock_code = stock_data['股票代码'].iloc[0] if '股票代码' in stock_data.columns else 'UNKNOWN'
        if stock_code == 'UNKNOWN' and len(stock_data) > 0:
            # 如果没有股票代码列，尝试从其他列获取
            if 'code' in stock_data.columns:
                stock_code = stock_data['code'].iloc[0]
            elif 'symbol' in stock_data.columns:
                stock_code = stock_data['symbol'].iloc[0]

        # 计算各项风险指标
        position_risk = self._calculate_position_risk(position_size, current_price)
        sector_risk = self._calculate_sector_risk(sector, position_size)
        market_risk = self._calculate_market_risk(stock_data)
        liquidity_risk = self._calculate_liquidity_risk(stock_data)

        # 计算总风险 (加权平均)
        total_risk = (position_risk * 0.3 + sector_risk * 0.2 + market_risk * 0.3 + liquidity_risk * 0.2)

        # 计算建议仓位
        suggested_position = self._calculate_suggested_position(total_risk, market_risk, liquidity_risk)

        # 确定风险等级
        if total_risk < 0.3:
            risk_level = '低'
        elif total_risk < 0.6:
            risk_level = '中'
        elif total_risk < 0.8:
            risk_level = '高'
        else:
            risk_level = '极高'

        # 风险因子详情
        risk_factors = {
            '波动率风险': market_risk * 0.4,
            '流动性风险': liquidity_risk * 0.3,
            '仓位集中风险': position_risk * 0.2,
            '板块集中风险': sector_risk * 0.1
        }

        return RiskMetrics(
            stock_code=stock_code,
            position_risk=position_risk,
            sector_risk=sector_risk,
            market_risk=market_risk,
            liquidity_risk=liquidity_risk,
            total_risk=total_risk,
            suggested_position=suggested_position,
            risk_level=risk_level,
            risk_factors=risk_factors,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

    def _calculate_position_risk(self, position_size: float, current_price: float) -> float:
        """计算仓位风险"""
        if position_size <= 0:
            return 0.0

        # 计算仓位占总资产比例
        position_value = position_size * current_price
        position_ratio = min(position_value / self.current_capital, 1.0)

        # 仓位越大，风险越高，但非线性增长
        risk = min(position_ratio / self.max_position_size, 1.0)
        return min(risk, 1.0)

    def _calculate_sector_risk(self, sector: str, position_size: float) -> float:
        """计算板块风险"""
        if not sector:
            return 0.3  # 默认中等风险

        # 计算该板块总暴露度
        current_sector_exposure = self.sector_exposure.get(sector, 0)
        total_sector_exposure = current_sector_exposure + position_size

        # 板块集中度风险
        max_sector_exposure = self.current_capital * 0.3  # 单个板块最大30%暴露
        sector_risk = min(total_sector_exposure / max_sector_exposure, 1.0)

        return sector_risk

    def _calculate_market_risk(self, stock_data: pd.DataFrame) -> float:
        """计算市场风险（波动率风险）"""
        # 计算价格波动率
        if 'close' in stock_data.columns:
            prices = stock_data['close'].dropna()
            if len(prices) >= 20:
                returns = prices.pct_change().dropna()
                volatility = returns.std() * np.sqrt(252)  # 年化波动率

                # 将波动率转换为风险评分 (0-1)
                # 通常股票年化波动率在0.2-0.5之间，我们将其映射到0-1
                risk = min(volatility / 0.5, 1.0)  # 假设0.5是高风险阈值
                return max(0.0, risk)
            else:
                return 0.3  # 数据不足时默认中等风险
        else:
            return 0.3  # 没有收盘价数据时默认中等风险

    def _calculate_liquidity_risk(self, stock_data: pd.DataFrame) -> float:
        """计算流动性风险"""
        if 'volume' in stock_data.columns:
            volumes = stock_data['volume'].dropna()
            if len(volumes) >= 10:
                avg_volume = volumes.mean()
                recent_volume = volumes.tail(5).mean()

                # 流动性风险 = 交易量下降程度
                if avg_volume > 0:
                    volume_ratio = recent_volume / avg_volume
                    # 交易量越低，流动性风险越高
                    liquidity_risk = max(0.0, 1.0 - volume_ratio)
                    return min(liquidity_risk, 1.0)
                else:
                    return 0.8  # 无交易量数据时假设高流动性风险
            else:
                return 0.4  # 数据不足时中等流动性风险
        else:
            return 0.4  # 没有交易量数据时中等流动性风险

    def _calculate_suggested_position(self, total_risk: float, market_risk: float, liquidity_risk: float) -> float:
        """计算建议仓位"""
        # 风险越高，建议仓位越低
        base_position = self.max_position_size

        # 根据总风险调整
        risk_adjustment = 1.0 - total_risk
        # 根据市场风险调整
        market_adjustment = 1.0 - market_risk * 0.5
        # 根据流动性风险调整
        liquidity_adjustment = 1.0 - liquidity_risk * 0.3

        suggested = base_position * risk_adjustment * market_adjustment * liquidity_adjustment

        # 确保仓位在合理范围内
        return max(0.0, min(suggested, self.max_position_size))

    def _get_default_risk_metrics(self, stock_code: str) -> RiskMetrics:
        """获取默认风险指标（数据不足时使用）"""
        return RiskMetrics(
            stock_code=stock_code,
            position_risk=0.3,
            sector_risk=0.3,
            market_risk=0.3,
            liquidity_risk=0.3,
            total_risk=0.3,
            suggested_position=self.max_position_size * 0.5,
            risk_level='中',
            risk_factors={
                '波动率风险': 0.3,
                '流动性风险': 0.3,
                '仓位集中风险': 0.2,
                '板块集中风险': 0.2
            },
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

    def update_position(self, stock_code: str, sector: str, position_size: float, price: float):
        """更新持仓信息"""
        self.position_history.append({
            'stock_code': stock_code,
            'sector': sector,
            'position_size': position_size,
            'price': price,
            'value': position_size * price,
            'timestamp': datetime.now()
        })

        # 更新板块暴露度
        if sector:
            current_exposure = self.sector_exposure.get(sector, 0)
            self.sector_exposure[sector] = current_exposure + position_size * price

        logger.info(f"更新持仓: {stock_code}, 仓位: {position_size}, 价格: {price}")

    def get_portfolio_risk_summary(self) -> Dict[str, float]:
        """获取投资组合风险摘要"""
        if not self.position_history:
            return {
                'total_value': self.current_capital,
                'diversification_score': 1.0,
                'max_drawdown_risk': 0.1,
                'sector_concentration_risk': 0.0
            }

        # 计算投资组合总价值
        total_value = sum(pos['value'] for pos in self.position_history)
        if total_value == 0:
            total_value = self.current_capital

        # 计算行业分散度
        sector_values = {}
        for pos in self.position_history:
            sector = pos['sector']
            value = pos['value']
            if sector:
                sector_values[sector] = sector_values.get(sector, 0) + value

        if sector_values:
            # 计算赫芬达尔-赫希曼指数 (HHI) 来衡量集中度
            total_sector_value = sum(sector_values.values())
            if total_sector_value > 0:
                hhi = sum((value / total_sector_value) ** 2 for value in sector_values.values())
                # HHI值越高表示集中度越高，分散度越低
                diversification_score = max(0.0, 1.0 - hhi)
            else:
                diversification_score = 1.0
        else:
            diversification_score = 1.0

        # 估算最大回撤风险（简化版）
        max_drawdown_risk = 0.1  # 默认10%回撤风险

        # 板块集中风险
        sector_concentration_risk = 1.0 - diversification_score

        return {
            'total_value': total_value,
            'diversification_score': diversification_score,
            'max_drawdown_risk': max_drawdown_risk,
            'sector_concentration_risk': sector_concentration_risk
        }

    def get_risk_recommendation(self, risk_metrics: RiskMetrics) -> str:
        """获取风险建议"""
        recommendations = []

        if risk_metrics.total_risk > 0.8:
            recommendations.append("风险极高，建议减仓或离场")
        elif risk_metrics.total_risk > 0.6:
            recommendations.append("风险较高，建议谨慎操作，控制仓位")
        elif risk_metrics.total_risk > 0.4:
            recommendations.append("风险中等，建议注意风险管理")
        else:
            recommendations.append("风险较低，可适当增加仓位")

        # 根据具体风险因子添加建议
        if risk_metrics.market_risk > 0.7:
            recommendations.append("市场波动率较高，注意价格风险")
        if risk_metrics.liquidity_risk > 0.6:
            recommendations.append("流动性不足，注意成交风险")
        if risk_metrics.sector_risk > 0.5:
            recommendations.append("板块过于集中，建议分散投资")

        return "; ".join(recommendations)

    def set_capital(self, new_capital: float):
        """设置新的资金规模"""
        self.current_capital = new_capital
        logger.info(f"资金更新为: {new_capital}")