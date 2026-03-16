# -*- coding: utf-8 -*-
"""
PaperTradeEngine - 零摩擦理想引擎 V2.0

【职责】
  作为「双引擎对照组」中的零摩擦引擎。
  假设每次都能以信号价格 100% 成交，无滑点、无排队、无涨停买不进。
  与 MockExecutionManager（真实摩擦引擎）的结果对比，量化摩擦损耗。

【方案B单仓模式】
  任何时刻只持 1 只股票（单吊）。
  入场条件由 TradeDecisionBrain 决定，PaperTradeEngine 无条件接受并执行。

【双引擎对比接口】
  compare_with_friction(friction_report) -> 返回摩擦损耗分析

Author: CTO Research Lab
Date: 2026-03-16
Version: V2.0
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class PaperOrder:
    """零摩擦订单记录"""
    order_id: str
    stock_code: str
    direction: str          # 'BUY' | 'SELL'
    price: float            # 成交价（无滑点）
    volume: float           # 股数
    amount: float           # 成交金额
    timestamp: str
    trigger_type: str = ""  # 触发信号类型（方案B记录）
    pnl_pct: float = 0.0    # 本次交易盈亏%（SELL 时计算）

    def to_dict(self) -> Dict:
        return asdict(self)


class PaperTradeEngine:
    """
    零摩擦理想引擎 V2.0

    假设：
      1. 每次 BUY 都能以信号价格 100% 成交（无涨停板限制）
      2. 每次 SELL 都能以信号价格 100% 成交（无跌停板限制）
      3. 无手续费、无滑点、无冲击成本
      4. 单仓（单吊）：任何时刻最多 1 只持仓
    """

    def __init__(self, initial_capital: float = 100000.0):
        """
        Args:
            initial_capital: 初始资金（元），默认 10 万
        """
        self.initial_capital = initial_capital
        self.available_cash = initial_capital
        self.positions: Dict[str, Dict] = {}   # {stock_code: {volume, cost_price, current_price}}
        self.orders: List[PaperOrder] = []
        self._order_seq = 0
        logger.info(
            f"[OK] PaperTradeEngine V2.0 初始化 | 初始资金: ¥{initial_capital:,.0f} | 单仓模式"
        )

    # ------------------------------------------------------------------
    # 核心交易接口
    # ------------------------------------------------------------------

    def place_order(
        self,
        stock_code: str,
        price: float,
        direction: str,
        trigger_type: str = None,
        timestamp: datetime = None
    ) -> Optional[PaperOrder]:
        """
        零摩擦下单（100% 成交）。

        Args:
            stock_code: 股票代码
            price: 成交价格（无滑点，直接使用信号价）
            direction: 'BUY' | 'SELL'
            trigger_type: 触发信号类型（方案B记录用）
            timestamp: 时间戳（默认 now）

        Returns:
            PaperOrder 成交记录，或 None（失败时）
        """
        ts = (timestamp or datetime.now()).strftime('%Y-%m-%d %H:%M:%S')

        if direction == 'BUY':
            return self._execute_buy(stock_code, price, trigger_type, ts)
        elif direction == 'SELL':
            return self._execute_sell(stock_code, price, ts)
        else:
            logger.error(f"[PaperTrade] 未知方向: {direction}")
            return None

    def _execute_buy(self, code: str, price: float, trigger_type: str, ts: str) -> Optional[PaperOrder]:
        """执行买入"""
        # 单仓保护：已有持仓则拒绝
        if self.positions:
            held = list(self.positions.keys())[0]
            logger.debug(
                f"[PaperTrade] 单仓保护: 已持有 {held}，拒绝买入 {code}"
            )
            return None

        if price <= 0:
            logger.error(f"[PaperTrade] 买入价格无效: {price}")
            return None

        if self.available_cash < price * 100:  # 至少能买 1 手
            logger.warning(f"[PaperTrade] 资金不足，无法买入 {code} @¥{price:.2f}")
            return None

        # 全仓买入（单吊模式：把所有可用资金全部投入）
        volume = int(self.available_cash / price / 100) * 100  # 取整到手
        # 【Bug#3修复】低价股(如0.5元)会导致volume爆炸，加50万股上限
        MAX_PAPER_VOLUME = 500000
        volume = min(volume, MAX_PAPER_VOLUME)
        if volume <= 0:
            return None

        amount = volume * price
        self.available_cash -= amount
        self.positions[code] = {
            'volume': volume,
            'cost_price': price,
            'current_price': price
        }

        self._order_seq += 1
        order = PaperOrder(
            order_id=f"P{self._order_seq:04d}",
            stock_code=code,
            direction='BUY',
            price=price,
            volume=volume,
            amount=amount,
            timestamp=ts,
            trigger_type=trigger_type or ''
        )
        self.orders.append(order)
        logger.info(
            f"[PaperTrade] BUY {code} | {volume}股 @¥{price:.2f} | "
            f"金额¥{amount:,.0f} | 剩余¥{self.available_cash:,.0f}"
        )
        return order

    def _execute_sell(self, code: str, price: float, ts: str) -> Optional[PaperOrder]:
        """执行卖出"""
        if code not in self.positions:
            logger.warning(f"[PaperTrade] 无持仓可卖: {code}")
            return None

        pos = self.positions[code]
        volume = pos['volume']
        cost_price = pos['cost_price']
        amount = volume * price
        pnl_pct = (price - cost_price) / cost_price * 100

        self.available_cash += amount
        del self.positions[code]

        self._order_seq += 1
        order = PaperOrder(
            order_id=f"P{self._order_seq:04d}",
            stock_code=code,
            direction='SELL',
            price=price,
            volume=volume,
            amount=amount,
            timestamp=ts,
            pnl_pct=pnl_pct
        )
        self.orders.append(order)
        logger.info(
            f"[PaperTrade] SELL {code} | {volume}股 @¥{price:.2f} | "
            f"盈亏:{pnl_pct:+.2f}% | 资金¥{self.available_cash:,.0f}"
        )
        return order

    # ------------------------------------------------------------------
    # 持仓更新
    # ------------------------------------------------------------------

    def update_position_price(self, stock_code: str, current_price: float):
        """更新持仓现价（用于计算浮盈）"""
        if stock_code in self.positions:
            self.positions[stock_code]['current_price'] = current_price

    def get_position_value(self) -> float:
        """返回当前持仓市值"""
        total = 0.0
        for code, pos in self.positions.items():
            total += pos['volume'] * pos.get('current_price', pos['cost_price'])
        return total

    def get_total_asset(self) -> float:
        """返回总资产 = 现金 + 持仓市值"""
        return self.available_cash + self.get_position_value()

    def get_unrealized_pnl_pct(self, stock_code: str) -> float:
        """返回指定持仓的未实现盈亏%"""
        pos = self.positions.get(stock_code)
        if not pos or pos['cost_price'] <= 0:
            return 0.0
        return (pos['current_price'] - pos['cost_price']) / pos['cost_price'] * 100

    # ------------------------------------------------------------------
    # 报告与双引擎对比
    # ------------------------------------------------------------------

    def get_performance_report(self) -> Dict:
        """返回零摩擦引擎绩效报告"""
        total_asset = self.get_total_asset()
        total_pnl_pct = (total_asset - self.initial_capital) / self.initial_capital * 100
        sell_orders = [o for o in self.orders if o.direction == 'SELL']
        win_orders = [o for o in sell_orders if o.pnl_pct > 0]
        return {
            'engine': 'PaperTradeEngine_V2.0',
            'initial_capital': self.initial_capital,
            'total_asset': round(total_asset, 2),
            'available_cash': round(self.available_cash, 2),
            'total_pnl_pct': round(total_pnl_pct, 3),
            'trade_count': len(sell_orders),
            'win_count': len(win_orders),
            'win_rate_pct': len(win_orders) / len(sell_orders) * 100 if sell_orders else 0.0,
            'avg_pnl_pct': (
                sum(o.pnl_pct for o in sell_orders) / len(sell_orders) if sell_orders else 0.0
            ),
            'orders': [o.to_dict() for o in self.orders]
        }

    def compare_with_friction(self, friction_report: Dict) -> Dict:
        """
        双引擎对比：零摩擦 vs 真实摩擦。

        Args:
            friction_report: MockExecutionManager.get_performance_report() 的返回值

        Returns:
            对比分析字典
        """
        paper_report = self.get_performance_report()
        paper_pnl = paper_report['total_pnl_pct']
        friction_pnl = friction_report.get('total_pnl_pct', 0.0)
        alpha_lost = paper_pnl - friction_pnl

        if abs(alpha_lost) < 0.5:
            verdict = '摩擦可控（损耗<0.5pp），真实摩擦与理想收益几乎一致'
        elif abs(alpha_lost) < 2.0:
            verdict = f'摩擦中等（损耗{alpha_lost:.2f}pp），建议优化滑点模型'
        else:
            verdict = (
                f'摩擦过大（损耗{alpha_lost:.2f}pp），严重警告：'
                f'实盘与理想差距过大，系统可能存在买入时机或价格判断问题'
            )

        return {
            'paper_pnl_pct': round(paper_pnl, 3),
            'friction_pnl_pct': round(friction_pnl, 3),
            'alpha_lost_to_friction': round(alpha_lost, 3),
            'verdict': verdict,
            'paper_trade_count': paper_report['trade_count'],
            'friction_trade_count': friction_report.get('trade_count', 0),
            'paper_win_rate_pct': paper_report['win_rate_pct'],
            'friction_win_rate_pct': friction_report.get('win_rate_pct', 0.0),
        }
