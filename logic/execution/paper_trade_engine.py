# -*- coding: utf-8 -*-
"""
零摩擦理想引擎（纸面完美模拟）

与 MockExecutionManager 接口对齐，可以无缝替换

【两个引擎的对比定位】
MockExecutionManager（真实摩擦）：
  - 滑点：0.1%（基准）～0.2%（活跃场景）
  - 流动性：买入金额 > 1/3 该分钟成交额则拒绝/部分成交
  - 印花税：卖出千分之一
  - 涨停买不进去

PaperTradeEngine（零摩擦理想）：
  - 滑点：0
  - 流动性：永远 100% 成交
  - 税费：只计最低佣金（模拟券商实际最低标准）
  - 涨停：假设能买进去（理论上限）
  - 用途：验证「策略本身有没有 alpha」，剥离执行摩擦的影响

Author: CTO Research Lab
Date: 2026-03-16
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class PaperPosition:
    """纸面持仓"""
    code: str
    volume: int
    entry_price: float
    entry_time: str
    current_price: float = 0.0
    trigger_type: str = ""
    entry_amount: float = 0.0  # 买入金额
    max_price: float = 0.0     # 持仓期间最高价


class PaperTradeEngine:
    """
    零摩擦理想引擎（纸面完美模拟）
    
    与 MockExecutionManager 接口对齐，可以无缝替换
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        """
        初始化零摩擦引擎
        
        Args:
            initial_capital: 初始本金
        """
        self.initial_capital = initial_capital
        self.available_cash = initial_capital
        self.positions: Dict[str, PaperPosition] = {}
        self.trades: List[Dict] = []
        self.orders: List[Dict] = []
        
        # 只收最低佣金，无滑点无税
        self.commission_rate = 0.00025  # 万2.5
        self.min_commission = 5.0       # 最低佣金5元
        
        logger.info(
            f"[OK] PaperTradeEngine初始化完成 | "
            f"零摩擦模式 | 资金池: ¥{self.initial_capital:,.2f}"
        )

    def place_order(
        self,
        stock_code: str,
        price: float,
        direction: str,
        trigger_type: str = None
    ) -> Tuple[bool, Dict]:
        """
        零摩擦撮合
        
        Args:
            stock_code: 股票代码
            price: 交易价格
            direction: 'BUY' | 'SELL'
            trigger_type: 触发类型（可选）
            
        Returns:
            (成功标志, 订单详情dict)
            
        规则：
        - BUY：以 price 精确成交，100% 仓位
        - SELL：以 price 精确成交
        - 不检查流动性
        - 不加滑点
        - 单吊约束：已有持仓则拒绝 BUY
        """
        order = {
            'stock_code': stock_code,
            'direction': direction,
            'trigger_price': price,
            'filled_price': price,
            'trigger_type': trigger_type or '',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'rejected',
            'filled_volume': 0,
            'rejection_reason': ''
        }
        
        if direction == 'BUY':
            return self._execute_buy(stock_code, price, trigger_type, order)
        elif direction == 'SELL':
            return self._execute_sell(stock_code, price, order)
        
        order['rejection_reason'] = f"无效方向: {direction}"
        self.orders.append(order)
        return False, order

    def _execute_buy(
        self, 
        stock_code: str, 
        price: float, 
        trigger_type: str,
        order: Dict
    ) -> Tuple[bool, Dict]:
        """执行买入（零摩擦）"""
        
        # 单吊约束：已有持仓拒绝
        if len(self.positions) >= 1:
            order['rejection_reason'] = f"已有持仓，单吊模式拒绝开新仓"
            self.orders.append(order)
            logger.debug(f"[拦截] {stock_code}: {order['rejection_reason']}")
            return False, order
        
        if price <= 0:
            order['rejection_reason'] = f"无效价格: {price}"
            self.orders.append(order)
            return False, order
        
        # 计算买入量（100%仓位）
        max_allocation = self.available_cash
        raw_shares = max_allocation / price
        hands = int(raw_shares // 100)
        volume = int(hands * 100)
        
        if volume < 100:
            order['rejection_reason'] = f"资金不足(剩余¥{self.available_cash:,.2f})"
            self.orders.append(order)
            return False, order
        
        # 零摩擦：精确成交，只有佣金
        total_cost = price * volume
        commission = max(self.min_commission, total_cost * self.commission_rate)
        total_with_commission = total_cost + commission
        
        if total_with_commission > self.available_cash:
            # 减少手数
            hands = int((self.available_cash - self.min_commission) / (price * 100 * (1 + self.commission_rate)))
            volume = int(hands * 100)
            if volume < 100:
                order['rejection_reason'] = "资金不足（扣除佣金后）"
                self.orders.append(order)
                return False, order
            total_cost = price * volume
            commission = max(self.min_commission, total_cost * self.commission_rate)
            total_with_commission = total_cost + commission
        
        # 扣款并创建持仓
        self.available_cash -= total_with_commission
        
        self.positions[stock_code] = PaperPosition(
            code=stock_code,
            volume=volume,
            entry_price=price,
            entry_time=order['timestamp'],
            current_price=price,
            trigger_type=trigger_type or '',
            entry_amount=total_with_commission,
            max_price=price
        )
        
        # 更新订单状态
        order['status'] = 'filled'
        order['filled_volume'] = volume
        order['filled_price'] = price
        
        # 记录交易
        self.trades.append({
            'time': order['timestamp'],
            'stock': stock_code,
            'direction': 'BUY',
            'price': price,
            'volume': volume,
            'fee': commission,
            'cash_flow': -total_with_commission
        })
        
        self.orders.append(order)
        
        logger.info(
            f"💵 [纸面开仓] {stock_code} | "
            f"价格:{price:.2f} | 规模:{volume}股 | "
            f"成本:¥{total_with_commission:,.2f}"
        )
        
        return True, order

    def _execute_sell(self, stock_code: str, price: float, order: Dict) -> Tuple[bool, Dict]:
        """执行卖出（零摩擦）"""
        
        pos = self.positions.get(stock_code)
        if not pos or pos.volume <= 0:
            order['rejection_reason'] = "无持仓"
            self.orders.append(order)
            return False, order
        
        # 零摩擦：精确成交，只有佣金（无印花税）
        gross_value = price * pos.volume
        commission = max(self.min_commission, gross_value * self.commission_rate)
        net_proceeds = gross_value - commission
        
        # 回血
        self.available_cash += net_proceeds
        
        # 更新订单状态
        order['status'] = 'filled'
        order['filled_volume'] = pos.volume
        order['filled_price'] = price
        
        # 计算盈亏
        pnl = net_proceeds - pos.entry_amount
        pnl_pct = pnl / pos.entry_amount * 100 if pos.entry_amount > 0 else 0
        
        # 记录交易
        self.trades.append({
            'time': order['timestamp'],
            'stock': stock_code,
            'direction': 'SELL',
            'price': price,
            'volume': pos.volume,
            'fee': commission,
            'cash_flow': net_proceeds,
            'entry_amount': pos.entry_amount,
            'pnl': pnl
        })
        
        del self.positions[stock_code]
        self.orders.append(order)
        
        logger.info(
            f"💵 [纸面平仓] {stock_code} | "
            f"价格:{price:.2f} | 回血:¥{net_proceeds:,.2f} | "
            f"盈亏:{pnl:+.2f}({pnl_pct:+.2f}%)"
        )
        
        return True, order

    def update_position_price(self, stock_code: str, current_price: float):
        """
        更新持仓当前价格
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
        """
        pos = self.positions.get(stock_code)
        if pos:
            pos.current_price = current_price
            if current_price > pos.max_price:
                pos.max_price = current_price

    # ==================== 接口对齐：与MockExecutionManager返回字段完全一致 ====================
    
    def get_portfolio_summary(self) -> Dict:
        """
        获取投资组合摘要
        
        与 MockExecutionManager.get_portfolio_summary() 返回字段完全相同
        """
        total_position_value = sum(
            pos.current_price * pos.volume for pos in self.positions.values()
        )
        
        return {
            'initial_capital': self.initial_capital,
            'available_cash': self.available_cash,
            'position_value': total_position_value,
            'total_value': self.available_cash + total_position_value,
            'positions': {
                k: {
                    'volume': v.volume, 
                    'entry_price': v.entry_price, 
                    'pnl_pct': (v.current_price - v.entry_price) / v.entry_price * 100 if v.entry_price > 0 else 0
                } 
                for k, v in self.positions.items()
            },
            'position_count': len(self.positions),
            'trade_count': len(self.trades),
            'order_count': len(self.orders),
            'total_fees': sum(t['fee'] for t in self.trades),
            'rejected_count': sum(1 for o in self.orders if o['status'] == 'rejected'),
            'partial_count': 0  # 零摩擦无部分成交
        }

    def get_performance_report(self) -> Dict:
        """
        获取绩效报告
        
        与 MockExecutionManager.get_performance_report() 返回字段完全相同
        """
        if not self.trades:
            return {'error': '无交易记录'}
        
        buy_trades = [t for t in self.trades if t['direction'] == 'BUY']
        sell_trades = [t for t in self.trades if t['direction'] == 'SELL']
        
        total_buy = sum(abs(t['cash_flow']) for t in buy_trades)
        total_sell = sum(t['cash_flow'] for t in sell_trades)
        total_fees = sum(t['fee'] for t in self.trades)
        
        pnl = total_sell - total_buy + self.available_cash - self.initial_capital + total_fees
        pnl_pct = pnl / self.initial_capital * 100
        
        # 用净利润判断盈亏
        win_count = sum(1 for t in sell_trades if t.get('pnl', 0) > 0)
        loss_count = sum(1 for t in sell_trades if t.get('pnl', 0) <= 0)
        
        return {
            'initial_capital': self.initial_capital,
            'final_cash': self.available_cash,
            'total_buy': total_buy,
            'total_sell': total_sell,
            'total_fees': total_fees,
            'realized_pnl': pnl,
            'realized_pnl_pct': pnl_pct,
            'trade_count': len(self.trades),
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_count / (win_count + loss_count) * 100 if (win_count + loss_count) > 0 else 0
        }

    def compare_with_friction(self, friction_report: Dict) -> Dict:
        """
        对比真实摩擦版的绩效报告
        
        Args:
            friction_report: MockExecutionManager.get_performance_report() 返回的报告
            
        Returns:
            差异分析字典
        """
        paper_report = self.get_performance_report()
        
        if 'error' in paper_report:
            return {
                'paper_pnl_pct': 0.0,
                'friction_pnl_pct': friction_report.get('realized_pnl_pct', 0),
                'alpha_lost_to_friction': 0.0,
                'friction_cost_estimate': 0.0,
                'verdict': 'PAPER_NO_TRADES'
            }
        
        paper_pnl_pct = paper_report['realized_pnl_pct']
        friction_pnl_pct = friction_report.get('realized_pnl_pct', 0)
        
        # alpha 被摩擦吃掉的量（百分点）
        alpha_lost = paper_pnl_pct - friction_pnl_pct
        
        # 摩擦成本估算
        friction_cost = friction_report.get('total_fees', 0) - paper_report.get('total_fees', 0)
        
        # 判定
        if abs(alpha_lost) < 1.5:
            verdict = 'FRICTION_ACCEPTABLE'
        else:
            verdict = 'FRICTION_TOO_HIGH'
        
        return {
            'paper_pnl_pct': paper_pnl_pct,
            'friction_pnl_pct': friction_pnl_pct,
            'alpha_lost_to_friction': alpha_lost,
            'friction_cost_estimate': friction_cost,
            'verdict': verdict
        }

    def get_total_value(self, price_dict: Dict[str, float] = None) -> float:
        """
        计算总资产价值
        
        Args:
            price_dict: 股票价格字典（可选）
            
        Returns:
            总资产价值 = 现金 + 持仓市值
        """
        total_position_value = 0.0
        for stock_code, pos in self.positions.items():
            price = pos.current_price
            if price_dict and stock_code in price_dict:
                price = price_dict[stock_code]
            total_position_value += price * pos.volume
        
        return self.available_cash + total_position_value

    def force_close_all_positions(self, price_dict: Dict[str, float], reason: str = "回测结束"):
        """
        强制平仓所有持仓
        
        Args:
            price_dict: 收盘价字典
            reason: 平仓原因
        """
        for stock_code, pos in list(self.positions.items()):
            if pos.volume <= 0:
                continue
            
            price = price_dict.get(stock_code, pos.current_price)
            
            # 零摩擦卖出
            gross_value = price * pos.volume
            commission = max(self.min_commission, gross_value * self.commission_rate)
            net_proceeds = gross_value - commission
            
            self.available_cash += net_proceeds
            pnl = net_proceeds - pos.entry_amount
            pnl_pct = pnl / pos.entry_amount * 100 if pos.entry_amount > 0 else 0
            
            self.trades.append({
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stock': stock_code,
                'direction': 'SELL',
                'price': price,
                'volume': pos.volume,
                'fee': commission,
                'cash_flow': net_proceeds,
                'entry_amount': pos.entry_amount,
                'pnl': pnl
            })
            
            del self.positions[stock_code]
            
            logger.info(
                f"🔔 [纸面强制平仓] {stock_code} | "
                f"原因:{reason} | 价格:{price:.2f} | "
                f"盈亏:{pnl:+.2f}({pnl_pct:+.2f}%)"
            )

    def get_positions(self) -> Dict[str, PaperPosition]:
        """获取所有持仓"""
        return self.positions.copy()

    def reset(self, initial_capital: float = None):
        """
        重置引擎状态
        
        Args:
            initial_capital: 新的初始本金（可选，默认使用原值）
        """
        if initial_capital is not None:
            self.initial_capital = initial_capital
        
        self.available_cash = self.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.orders.clear()
        
        logger.info(f"[OK] PaperTradeEngine已重置 | 资金池: ¥{self.initial_capital:,.2f}")
