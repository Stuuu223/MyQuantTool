#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块共振计算器 - Leaders + Breadth 双指标触发机制

核心功能：
1. 计算板块内涨停股数量（Leaders）
2. 计算板块内上涨股票比例（Breadth）
3. 判断板块是否满足共振条件

使用方式：
    from logic.sectors.sector_resonance import SectorResonanceCalculator
    calculator = SectorResonanceCalculator()
    result = calculator.calculate(sector_stocks)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SectorResonanceResult:
    """板块共振结果"""
    sector_name: str           # 板块名称
    sector_code: str           # 板块代码
    leaders: int               # 涨停股数量（20日新高）
    breadth: float            # 上涨股票比例（%）
    is_resonant: bool         # 是否满足共振条件
    total_stocks: int         # 板块总股票数
    up_stocks: int            # 上涨股票数
    reason: str               # 共振判断原因


class SectorResonanceCalculator:
    """
    板块共振计算器

    共振条件：
    - Leaders ≥ 3：板块内涨停股数量 ≥ 3
    - Breadth ≥ 35%：板块内上涨比例 ≥ 35%
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化板块共振计算器

        Args:
            config: 配置字典，包含阈值设置
        """
        self.config = config or self._default_config()

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            # 涨停判断阈值
            "limit_up_pct": 9.8,              # 涨停涨幅阈值（9.8%以上）
            "is_20d_high_threshold": True,    # 是否使用20日新高判断

            # 共振条件阈值
            "min_leaders": 3,                 # 最少涨停股数量
            "min_breadth": 35.0,              # 最小上涨比例（%）

            # 上涨判断阈值
            "up_threshold": 0.0,              # 涨幅 > 0% 算上涨
        }

    def calculate(
        self,
        sector_stocks: List[Dict],
        sector_name: str = "",
        sector_code: str = ""
    ) -> SectorResonanceResult:
        """
        计算板块共振指标

        Args:
            sector_stocks: 板块内所有股票的实时数据列表
                每个股票数据应包含：
                - pct_chg: 涨跌幅（%）
                - is_limit_up: 是否涨停（可选）
                - is_20d_high: 是否20日新高（可选）
            sector_name: 板块名称
            sector_code: 板块代码

        Returns:
            SectorResonanceResult: 板块共振结果
        """
        if not sector_stocks:
            return SectorResonanceResult(
                sector_name=sector_name,
                sector_code=sector_code,
                leaders=0,
                breadth=0.0,
                is_resonant=False,
                total_stocks=0,
                up_stocks=0,
                reason="板块内无股票数据"
            )

        # 1. 计算 Leaders（涨停股数量）
        leaders = self._calculate_leaders(sector_stocks)

        # 2. 计算 Breadth（上涨股票比例）
        breadth, up_stocks = self._calculate_breadth(sector_stocks)

        # 3. 判断是否满足共振条件
        is_resonant = self._check_resonance(leaders, breadth)

        # 4. 生成判断原因
        reason = self._generate_reason(leaders, breadth, is_resonant)

        # 记录日志
        logger.info(f"📊 [{sector_name}] 板块共振分析:")
        logger.info(f"   Leaders: {leaders}/{self.config['min_leaders']}")
        logger.info(f"   Breadth: {breadth:.1f}%/{self.config['min_breadth']:.1f}%")
        logger.info(f"   结果: {'✅ 共振' if is_resonant else '⏸️ 未共振'}")

        return SectorResonanceResult(
            sector_name=sector_name,
            sector_code=sector_code,
            leaders=leaders,
            breadth=breadth,
            is_resonant=is_resonant,
            total_stocks=len(sector_stocks),
            up_stocks=up_stocks,
            reason=reason
        )

    def _calculate_leaders(self, sector_stocks: List[Dict]) -> int:
        """
        计算涨停股数量

        判断逻辑：
        - 优先使用 is_limit_up 字段
        - 其次使用 pct_chg >= 9.8%
        - 最后使用 is_20d_high 字段
        """
        leaders = 0

        for stock in sector_stocks:
            # 优先使用涨停标记
            if stock.get('is_limit_up'):
                leaders += 1
            # 其次使用涨幅判断
            elif stock.get('pct_chg', 0) >= self.config['limit_up_pct']:
                leaders += 1
            # 最后使用20日新高判断
            elif self.config['is_20d_high_threshold'] and stock.get('is_20d_high'):
                leaders += 1

        return leaders

    def _calculate_breadth(self, sector_stocks: List[Dict]) -> tuple:
        """
        计算上涨股票比例

        Returns:
            (breadth, up_stocks)
            breadth: 上涨比例（%）
            up_stocks: 上涨股票数
        """
        up_stocks = 0
        total_stocks = len(sector_stocks)

        for stock in sector_stocks:
            pct_chg = stock.get('pct_chg', 0)
            if pct_chg > self.config['up_threshold']:
                up_stocks += 1

        breadth = (up_stocks / total_stocks * 100) if total_stocks > 0 else 0.0

        return breadth, up_stocks

    def _check_resonance(self, leaders: int, breadth: float) -> bool:
        """
        检查是否满足共振条件

        条件：
        - Leaders ≥ min_leaders
        - Breadth ≥ min_breadth
        """
        leaders_ok = leaders >= self.config['min_leaders']
        breadth_ok = breadth >= self.config['min_breadth']

        return leaders_ok and breadth_ok

    def _generate_reason(self, leaders: int, breadth: float, is_resonant: bool) -> str:
        """生成判断原因"""
        if is_resonant:
            return f"✅ 板块共振：Leaders={leaders}（≥{self.config['min_leaders']}），Breadth={breadth:.1f}%（≥{self.config['min_breadth']:.1f}%）"
        else:
            leaders_status = f"Leaders={leaders}（需≥{self.config['min_leaders']}）" if leaders < self.config['min_leaders'] else f"Leaders={leaders}✅"
            breadth_status = f"Breadth={breadth:.1f}%（需≥{self.config['min_breadth']:.1f}%）" if breadth < self.config['min_breadth'] else f"Breadth={breadth:.1f}%✅"
            return f"⏸️ 板块未共振：{leaders_status}，{breadth_status}"

    def check_stock_resonance(
        self,
        stock_data: Dict,
        sector_stocks: List[Dict],
        sector_name: str = "",
        sector_code: str = ""
    ) -> tuple:
        """
        检查单只股票是否可以入场（板块共振检查）

        Args:
            stock_data: 股票数据
            sector_stocks: 板块内所有股票数据
            sector_name: 板块名称
            sector_code: 板块代码

        Returns:
            (can_enter, resonance_result, reason)
            can_enter: 是否允许入场
            resonance_result: 板块共振结果
            reason: 拒绝原因或允许原因
        """
        # 计算板块共振
        resonance_result = self.calculate(sector_stocks, sector_name, sector_code)

        # 检查是否满足共振条件
        if not resonance_result.is_resonant:
            return False, resonance_result, resonance_result.reason

        # 通过检查
        return True, resonance_result, f"✅ 板块共振满足，允许入场"


# 便捷函数
def calculate_sector_resonance(sector_stocks: List[Dict], sector_name: str = "") -> SectorResonanceResult:
    """
    便捷函数：计算板块共振

    Args:
        sector_stocks: 板块内所有股票的实时数据列表
        sector_name: 板块名称

    Returns:
        SectorResonanceResult: 板块共振结果
    """
    calculator = SectorResonanceCalculator()
    return calculator.calculate(sector_stocks, sector_name)


if __name__ == "__main__":
    # 测试用例
    test_stocks = [
        {'code': '000001', 'pct_chg': 10.0, 'is_limit_up': True},   # 涨停
        {'code': '000002', 'pct_chg': 9.9, 'is_limit_up': True},    # 涨停
        {'code': '000003', 'pct_chg': 9.8, 'is_limit_up': True},    # 涨停
        {'code': '000004', 'pct_chg': 5.0},                         # 上涨
        {'code': '000005', 'pct_chg': 3.0},                         # 上涨
        {'code': '000006', 'pct_chg': 2.0},                         # 上涨
        {'code': '000007', 'pct_chg': 1.0},                         # 上涨
        {'code': '000008', 'pct_chg': -1.0},                        # 下跌
        {'code': '000009', 'pct_chg': -2.0},                        # 下跌
        {'code': '000010', 'pct_chg': -3.0},                        # 下跌
    ]

    print("=" * 60)
    print("测试板块共振计算器")
    print("=" * 60)

    calculator = SectorResonanceCalculator()
    result = calculator.calculate(test_stocks, sector_name="测试板块")

    print(f"\n板块: {result.sector_name}")
    print(f"Leaders: {result.leaders}")
    print(f"Breadth: {result.breadth:.1f}%")
    print(f"共振: {'✅ 是' if result.is_resonant else '❌ 否'}")
    print(f"原因: {result.reason}")

    print("=" * 60)