# logic/execution/mock_execution_manager.py
"""
L1 虚拟交易所 - 全息战场模拟器 (CTO收官战版)

【三大物理关卡】
1. 动态滑点惩罚：引力弹弓/阶梯突破场景滑点×2
2. 流动性拒绝：成交量不足时部分成交或废单
3. 微观防爆确认：买入后价格跌破触发价时止损

Author: CTO Research Lab
Date: 2026-03-14
"""
import logging
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """触发类型枚举"""
    VWAP_BOUNCE = "vwap_bounce"       # 引力弹弓
    STAIR_BREAKOUT = "stair_breakout" # 阶梯突破
    VACUUM_IGNITION = "vacuum_ignition"  # 真空点火
    STATIC_SCORE = "static_score"     # 静态打分（旧模式）
    UNKNOWN = "unknown"


class OrderStatus(Enum):
    """订单状态枚举"""
    FILLED = "filled"           # 完全成交
    PARTIAL = "partial"         # 部分成交
    REJECTED = "rejected"       # 拒绝
    CANCELLED = "cancelled"     # 取消


@dataclass
class MockOrder:
    """虚拟订单"""
    stock_code: str
    direction: str
    trigger_price: float
    trigger_type: TriggerType
    requested_volume: int
    filled_volume: int = 0
    filled_price: float = 0.0
    slippage: float = 0.0
    status: OrderStatus = OrderStatus.REJECTED
    rejection_reason: str = ""
    timestamp: str = ""
    
    # 关卡记录
    slippage_applied: float = 0.0
    liquidity_check_passed: bool = False
    micro_guard_triggered: bool = False


@dataclass
class MockPosition:
    """虚拟持仓"""
    stock_code: str
    volume: int
    entry_price: float
    entry_time: str
    entry_date: str = ""  # 【CTO V163】入场日期，用于跨日计算
    trigger_type: TriggerType = TriggerType.UNKNOWN
    entry_amount: float = 0.0  # 买入金额（含费用）
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    max_price: float = 0.0  # 持仓期间最高价
    stopped_out: bool = False
    holding_days: int = 0  # 【CTO V163】持仓天数


class MockExecutionManager:
    """L1 虚拟交易所 - 全息战场模拟器"""
    
    def __init__(
        self, 
        initial_capital: float = 100000.0, 
        max_position_ratio: float = 1.0
    ):
        """
        初始化虚拟交易所
        
        Args:
            initial_capital: 初始本金
            max_position_ratio: 单票最大仓位比例 (1.0=单吊)
        """
        self.initial_capital = initial_capital
        self.available_cash = initial_capital
        self.max_position_ratio = max_position_ratio
        
        # 持仓管理
        self.positions: Dict[str, MockPosition] = {}
        self.trades: List[Dict] = []
        self.orders: List[MockOrder] = []
        
        # 物理摩擦力模型 (基准值)
        self.commission_rate = 0.00025    # 佣金 万2.5
        self.tax_rate_sell = 0.001        # 印花税 千1
        self.base_slippage_rate = 0.001   # 基准滑点 千1
        
        # ==================== 【CTO收官战】三大物理关卡 ====================
        
        # 关卡1：动态滑点惩罚
        # 引力弹弓/阶梯突破场景，盘口活跃抢筹，滑点翻倍
        self.active_trigger_slippage = 0.002  # 千2（活跃场景）
        
        # 关卡2：流动性拒绝
        # 想买入金额 > 该分钟成交额的1/3时，部分成交或拒绝
        self.liquidity_ratio_threshold = 0.33
        
        # 关卡3：微观防爆确认
        # 买入后3分钟内价格跌破触发价且MFE<0.5，判定点火失败
        self.micro_guard_window_sec = 180
        self.micro_guard_mfe_threshold = 0.5
        
        mode_str = "单吊绝对集中" if max_position_ratio == 1.0 else f"最高限购 {int(1/max_position_ratio)} 只"
        logger.info(f"[OK] L1 全息战场模拟器启动 | 资金池: ¥{self.initial_capital:,.2f} | 攻击模式: {mode_str}")
        logger.info(f"[关卡1] 动态滑点: 基准{self.base_slippage_rate*1000:.1f}‰ → 活跃场景{self.active_trigger_slippage*1000:.1f}‰")
        logger.info(f"[关卡2] 流动性拒绝: 买入金额 > {self.liquidity_ratio_threshold*100:.0f}%该分钟成交额时拒绝")
        logger.info(f"[关卡3] 微观防爆: {self.micro_guard_window_sec}秒内破位+MFE<{self.micro_guard_mfe_threshold}触发止损")

    # ==================== 核心交易接口 ====================
    
    def place_mock_order(
        self, 
        stock_code: str, 
        last_price: float, 
        direction: str = 'BUY',
        trigger_type: TriggerType = TriggerType.STATIC_SCORE,
        tick_data: Dict = None,
        minute_volume: float = 0.0  # 该分钟成交额
    ) -> Tuple[bool, MockOrder]:
        """
        触发虚拟状态机撮合（带回测数据）
        
        Args:
            stock_code: 股票代码
            last_price: 触发价格
            direction: 方向 'BUY'/'SELL'
            trigger_type: 触发类型
            tick_data: Tick数据（用于关卡判断）
            minute_volume: 该分钟成交额（用于流动性检查）
            
        Returns:
            (是否成功, 订单详情)
        """
        if direction == 'BUY':
            return self._execute_buy(stock_code, last_price, trigger_type, tick_data, minute_volume)
        elif direction == 'SELL':
            return self._execute_sell(stock_code, last_price)
        
        return False, MockOrder(
            stock_code=stock_code,
            direction=direction,
            trigger_price=last_price,
            trigger_type=trigger_type,
            requested_volume=0,
            status=OrderStatus.REJECTED,
            rejection_reason="无效方向"
        )

    def _execute_buy(
        self,
        stock_code: str,
        last_price: float,
        trigger_type: TriggerType,
        tick_data: Dict,
        minute_volume: float
    ) -> Tuple[bool, MockOrder]:
        """执行买入（三大关卡）"""
        
        order = MockOrder(
            stock_code=stock_code,
            direction='BUY',
            trigger_price=last_price,
            trigger_type=trigger_type,
            requested_volume=0,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        # 前置检查：单吊模式已有持仓
        if len(self.positions) >= 1:
            order.rejection_reason = f"已有持仓({len(self.positions)}只)，单吊模式拒绝开新仓"
            order.status = OrderStatus.REJECTED
            self.orders.append(order)
            logger.debug(f"[拦截] {stock_code}: {order.rejection_reason}")
            return False, order
        
        # 计算理论买入量
        requested_volume = self._calculate_position_size(last_price)
        if requested_volume < 100:
            order.rejection_reason = f"资金不足(剩余¥{self.available_cash:,.2f})"
            order.status = OrderStatus.REJECTED
            self.orders.append(order)
            logger.debug(f"[拦截] {stock_code}: {order.rejection_reason}")
            return False, order
        
        order.requested_volume = requested_volume
        
        # ==================== 关卡1：动态滑点惩罚 ====================
        slippage_rate = self._get_dynamic_slippage(trigger_type)
        order.slippage_applied = slippage_rate
        executed_price = last_price * (1.0 + slippage_rate)
        
        # ==================== 关卡2：流动性拒绝 ====================
        estimated_cost = executed_price * requested_volume
        liquidity_ok, actual_volume = self._check_liquidity(
            estimated_cost, minute_volume, trigger_type
        )
        order.liquidity_check_passed = liquidity_ok
        
        if not liquidity_ok:
            # 流动性不足，部分成交或拒绝
            if actual_volume < 100:
                order.rejection_reason = f"流动性不足: 该分钟成交额¥{minute_volume:,.0f} < 买入需求{estimated_cost*self.liquidity_ratio_threshold:,.0f}"
                order.status = OrderStatus.REJECTED
                self.orders.append(order)
                logger.info(f"🚫 [流动性拒绝] {stock_code}: {order.rejection_reason}")
                return False, order
            else:
                # 部分成交
                order.status = OrderStatus.PARTIAL
                order.filled_volume = actual_volume
                executed_price = last_price * (1.0 + slippage_rate)
        else:
            order.status = OrderStatus.FILLED
            order.filled_volume = requested_volume
        
        # ==================== 执行交易 ====================
        actual_cost = executed_price * order.filled_volume
        commission = max(5.0, actual_cost * self.commission_rate)
        total_cost = actual_cost + commission
        
        if total_cost > self.available_cash:
            order.rejection_reason = f"预估耗资¥{total_cost:,.2f}大于现金池"
            order.status = OrderStatus.REJECTED
            self.orders.append(order)
            logger.error(f"[FATAL] {stock_code}: {order.rejection_reason}")
            return False, order
        
        # 扣款与创建持仓
        self.available_cash -= total_cost
        order.filled_price = executed_price
        order.slippage = (executed_price - last_price) / last_price * 100
        
        self.positions[stock_code] = MockPosition(
            stock_code=stock_code,
            volume=order.filled_volume,
            entry_price=executed_price,
            entry_time=order.timestamp,
            entry_date=order.timestamp[:10] if order.timestamp else "",  # 【CTO V163】入场日期
            trigger_type=trigger_type,
            entry_amount=total_cost,
            current_price=executed_price,
            max_price=executed_price
        )
        
        self._record_trade(stock_code, 'BUY', executed_price, order.filled_volume, commission, total_cost)
        self.orders.append(order)
        
        logger.info(
            f"💥 [开仓] {stock_code} | 触发:{trigger_type.value} | "
            f"均价:{executed_price:.2f} | 规模:{order.filled_volume}股 | "
            f"滑点:{order.slippage:.2f}% | 耗资:¥{total_cost:,.2f}"
        )
        
        return True, order

    def _execute_sell(self, stock_code: str, last_price: float) -> Tuple[bool, MockOrder]:
        """执行卖出"""
        
        order = MockOrder(
            stock_code=stock_code,
            direction='SELL',
            trigger_price=last_price,
            trigger_type=TriggerType.UNKNOWN,
            requested_volume=0,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        pos = self.positions.get(stock_code)
        if not pos or pos.volume <= 0:
            order.rejection_reason = "无持仓"
            order.status = OrderStatus.REJECTED
            self.orders.append(order)
            logger.warning(f"[拦截] {stock_code}: 无持仓，拒绝做空")
            return False, order
        
        order.requested_volume = pos.volume
        
        # 卖出滑点
        executed_price = last_price * (1.0 - self.base_slippage_rate)
        gross_value = executed_price * pos.volume
        commission = max(5.0, gross_value * self.commission_rate)
        tax = gross_value * self.tax_rate_sell
        net_proceeds = gross_value - commission - tax
        
        # 回血
        self.available_cash += net_proceeds
        order.filled_volume = pos.volume
        order.filled_price = executed_price
        order.status = OrderStatus.FILLED
        
        # 记录盈亏
        pnl = net_proceeds - pos.entry_amount
        pnl_pct = pnl / pos.entry_amount * 100 if pos.entry_amount > 0 else 0
        
        # 【CTO V166修复】传入entry_amount和pnl用于真实胜率计算
        self._record_trade(
            stock_code, 'SELL', executed_price, pos.volume, 
            commission + tax, net_proceeds, 
            entry_amount=pos.entry_amount, pnl=pnl
        )
        del self.positions[stock_code]
        self.orders.append(order)
        
        logger.info(
            f"🔪 [平仓] {stock_code} | 均价:{executed_price:.2f} | "
            f"规模:{pos.volume}股 | 回血:¥{net_proceeds:,.2f} | "
            f"盈亏:{pnl:+.2f}({pnl_pct:+.2f}%)"
        )
        
        return True, order

    # ==================== 三大关卡实现 ====================
    
    def _get_dynamic_slippage(self, trigger_type: TriggerType) -> float:
        """
        关卡1：动态滑点惩罚
        
        - 引力弹弓/阶梯突破：盘口活跃抢筹，滑点翻倍
        - 真空点火/静态打分：使用基准滑点
        """
        if trigger_type in [TriggerType.VWAP_BOUNCE, TriggerType.STAIR_BREAKOUT]:
            return self.active_trigger_slippage  # 千2
        return self.base_slippage_rate  # 千1

    def _check_liquidity(
        self, 
        estimated_cost: float, 
        minute_volume: float,
        trigger_type: TriggerType
    ) -> Tuple[bool, int]:
        """
        关卡2：流动性拒绝
        
        Args:
            estimated_cost: 预估买入金额
            minute_volume: 该分钟成交额
            trigger_type: 触发类型
            
        Returns:
            (是否通过, 实际可成交量)
        """
        # 真空点火场景：无量空涨，流动性检查更严格
        if trigger_type == TriggerType.VACUUM_IGNITION:
            # 需要该分钟成交额至少是买入金额的5倍
            liquidity_threshold = 5.0
        else:
            liquidity_threshold = 1.0 / self.liquidity_ratio_threshold  # 约3倍
        
        if minute_volume <= 0:
            # 无数据时，保守起见拒绝
            return False, 0
        
        max_buy_amount = minute_volume / liquidity_threshold
        
        if estimated_cost <= max_buy_amount:
            return True, 0  # 通过，返回0表示使用原请求量
        else:
            # 部分成交
            partial_volume = int(max_buy_amount / estimated_cost * 100) * 100
            return False, partial_volume

    def check_micro_guard(
        self,
        stock_code: str,
        current_price: float,
        current_mfe: float,
        minutes_elapsed: int
    ) -> Tuple[bool, str]:
        """
        关卡3：微观防爆确认
        
        买入后检查价格走势，如果破位则触发止损
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            current_mfe: 当前MFE
            minutes_elapsed: 持仓分钟数
            
        Returns:
            (是否触发止损, 原因)
        """
        pos = self.positions.get(stock_code)
        if not pos or pos.stopped_out:
            return False, ""
        
        # 更新持仓状态
        pos.current_price = current_price
        if current_price > pos.max_price:
            pos.max_price = current_price
        
        # 计算盈亏
        pnl_pct = (current_price - pos.entry_price) / pos.entry_price * 100
        pos.unrealized_pnl = pnl_pct
        
        # 持仓时间窗口内检查
        if minutes_elapsed > self.micro_guard_window_sec / 60:
            return False, ""  # 超过窗口期，不再监控
        
        # 检查条件：价格跌破买入价 + MFE极低
        if current_price < pos.entry_price and current_mfe < self.micro_guard_mfe_threshold:
            reason = f"微观防爆: 价格{current_price:.2f}<{pos.entry_price:.2f} + MFE{current_mfe:.2f}<{self.micro_guard_mfe_threshold}"
            pos.stopped_out = True
            logger.warning(f"[WARN] [微观防爆] {stock_code}: {reason}")
            return True, reason
        
        return False, ""

    # ==================== 辅助方法 ====================
    
    def _calculate_position_size(self, last_price: float) -> int:
        """计算合法买入股数，强制100股整数倍"""
        if last_price <= 0:
            return 0
        
        max_allocation = self.initial_capital * self.max_position_ratio
        actual_allocation = min(max_allocation, self.available_cash)
        
        # 预留滑点+佣金
        estimated_cost_ratio = 1.0 + self.commission_rate + self.active_trigger_slippage
        purchasing_power = actual_allocation / estimated_cost_ratio
        
        raw_shares = purchasing_power / last_price
        hands = math.floor(raw_shares / 100)
        return int(hands * 100)

    def _record_trade(self, stock_code: str, direction: str, price: float, volume: int, fee: float, cash_flow: float, entry_amount: float = 0.0, pnl: float = 0.0):
        """
        记录交割单
        
        【CTO V166修复】添加entry_amount和pnl字段，用于真实胜率计算
        """
        self.trades.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stock': stock_code,
            'direction': direction,
            'price': price,
            'volume': volume,
            'fee': fee,
            'cash_flow': cash_flow,
            'entry_amount': entry_amount,  # 【CTO V166】买入成本
            'pnl': pnl  # 【CTO V166】净利润
        })

    # ==================== 状态查询 ====================
    
    def get_portfolio_summary(self) -> Dict:
        """获取投资组合摘要"""
        total_position_value = sum(
            pos.current_price * pos.volume for pos in self.positions.values()
        )
        
        return {
            'initial_capital': self.initial_capital,
            'available_cash': self.available_cash,
            'position_value': total_position_value,
            'total_value': self.available_cash + total_position_value,
            'positions': {k: {'volume': v.volume, 'entry_price': v.entry_price, 'pnl_pct': v.unrealized_pnl} for k, v in self.positions.items()},
            'position_count': len(self.positions),
            'trade_count': len(self.trades),
            'order_count': len(self.orders),
            'total_fees': sum(t['fee'] for t in self.trades),
            'rejected_count': sum(1 for o in self.orders if o.status == OrderStatus.REJECTED),
            'partial_count': sum(1 for o in self.orders if o.status == OrderStatus.PARTIAL)
        }

    def get_performance_report(self) -> Dict:
        """获取绩效报告"""
        if not self.trades:
            return {'error': '无交易记录'}
        
        buy_trades = [t for t in self.trades if t['direction'] == 'BUY']
        sell_trades = [t for t in self.trades if t['direction'] == 'SELL']
        
        total_buy = sum(t['cash_flow'] for t in buy_trades)
        total_sell = sum(t['cash_flow'] for t in sell_trades)
        total_fees = sum(t['fee'] for t in self.trades)
        
        pnl = total_sell - total_buy + self.available_cash - self.initial_capital + total_fees
        pnl_pct = pnl / self.initial_capital * 100
        
        # 【CTO V166修复】用净利润(pnl)判断真实盈亏
        # 盈利 = 卖出净收入 > 买入成本 (pnl > 0)
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

    def export_trades_to_csv(self, filepath: str):
        """导出交割单"""
        import pandas as pd
        if not self.trades:
            logger.warning("[WARN] 无交易记录可导出")
            return
        
        df = pd.DataFrame(self.trades)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"[OK] 交割单已导出: {filepath}")

    # ==================== 【CTO V163】多日连续回测支持 ====================
    
    def get_overnight_positions(self) -> Dict[str, MockPosition]:
        """获取隔夜持仓（收盘时仍持有的仓位）"""
        return {k: v for k, v in self.positions.items() if not v.stopped_out}
    
    def update_position_price(self, stock_code: str, current_price: float):
        """
        更新持仓当前价格（用于日内和隔日估值）
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
        """
        pos = self.positions.get(stock_code)
        if pos:
            pos.current_price = current_price
            if current_price > pos.max_price:
                pos.max_price = current_price
            # 更新未实现盈亏
            pos.unrealized_pnl = (current_price - pos.entry_price) / pos.entry_price * 100
    
    def carry_positions_to_next_day(self, new_date: str):
        """
        【CTO V163核心】将持仓跨日继承到下一个交易日
        
        Args:
            new_date: 新交易日期 (YYYY-MM-DD格式)
        """
        for stock_code, pos in self.positions.items():
            if not pos.stopped_out:
                pos.holding_days += 1
                logger.info(f"📅 [隔夜继承] {stock_code}: 持仓{pos.volume}股@{pos.entry_price:.2f} → 第{pos.holding_days}天")
    
    def get_total_value(self, price_dict: Dict[str, float] = None) -> float:
        """
        计算总资产价值
        
        Args:
            price_dict: 股票价格字典 {stock_code: price}
            
        Returns:
            总资产价值 = 现金 + 持仓市值
        """
        total_position_value = 0.0
        for stock_code, pos in self.positions.items():
            if pos.stopped_out:
                continue
            price = pos.current_price
            if price_dict and stock_code in price_dict:
                price = price_dict[stock_code]
            total_position_value += price * pos.volume
        
        return self.available_cash + total_position_value
    
    def get_daily_snapshot(self, date_str: str, price_dict: Dict[str, float] = None) -> Dict:
        """
        获取每日快照（用于多日资金曲线）
        
        Args:
            date_str: 日期字符串
            price_dict: 收盘价字典
            
        Returns:
            每日快照字典
        """
        total_value = self.get_total_value(price_dict)
        daily_pnl = total_value - self.initial_capital
        daily_pnl_pct = daily_pnl / self.initial_capital * 100
        
        # 统计持仓
        position_details = []
        for stock_code, pos in self.positions.items():
            if pos.stopped_out:
                continue
            price = pos.current_price
            if price_dict and stock_code in price_dict:
                price = price_dict[stock_code]
            pos_value = price * pos.volume
            pos_pnl = (price - pos.entry_price) / pos.entry_price * 100
            position_details.append({
                'code': stock_code,
                'volume': pos.volume,
                'entry_price': pos.entry_price,
                'current_price': price,
                'value': pos_value,
                'pnl_pct': pos_pnl,
                'holding_days': pos.holding_days
            })
        
        return {
            'date': date_str,
            'cash': self.available_cash,
            'position_value': total_value - self.available_cash,
            'total_value': total_value,
            'pnl': daily_pnl,
            'pnl_pct': daily_pnl_pct,
            'position_count': len([p for p in self.positions.values() if not p.stopped_out]),
            'positions': position_details,
            'trade_count': len(self.trades)
        }
    
    def force_close_all_positions(self, price_dict: Dict[str, float], reason: str = "回测结束"):
        """
        强制平仓所有持仓（用于回测结束）
        
        Args:
            price_dict: 收盘价字典
            reason: 平仓原因
        """
        for stock_code, pos in list(self.positions.items()):
            if pos.stopped_out or pos.volume <= 0:
                continue
            
            price = price_dict.get(stock_code, pos.current_price)
            executed_price = price * (1.0 - self.base_slippage_rate)
            gross_value = executed_price * pos.volume
            commission = max(5.0, gross_value * self.commission_rate)
            tax = gross_value * self.tax_rate_sell
            net_proceeds = gross_value - commission - tax
            
            self.available_cash += net_proceeds
            pnl = net_proceeds - pos.entry_amount
            pnl_pct = pnl / pos.entry_amount * 100 if pos.entry_amount > 0 else 0
            
            self._record_trade(stock_code, 'SELL', executed_price, pos.volume, commission + tax, net_proceeds)
            del self.positions[stock_code]
            
            logger.info(
                f"[TRADE-SELL] [强制平仓] {stock_code} | 原因:{reason} | "
                f"均价:{executed_price:.2f} | 盈亏:{pnl:+.2f}({pnl_pct:+.2f}%)"
            )
