# logic/execution/mock_execution_manager.py
import logging
import math
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MockExecutionManager:
    def __init__(self, initial_capital: float = 100000.0, max_position_ratio: float = 1.0):
        """
        L1 虚拟交易所与资金状态机 (集中火力版)
        
        :param initial_capital: 初始本金池 (例如 10 万)
        :param max_position_ratio: 仓位超参。
            - 1.0 代表单吊全仓
            - 0.5 代表分2只
            - 0.33 代表分3只
        """
        self.initial_capital = initial_capital
        self.available_cash = initial_capital
        self.max_position_ratio = max_position_ratio
        
        self.positions: Dict[str, int] = {}  # 结构: {stock_code: volume_in_shares}
        self.trades: List[Dict] = []         # 交割单流水
        
        # 物理摩擦力模型 (不可绕过)
        self.commission_rate = 0.00025       # 佣金 万2.5
        self.tax_rate_sell = 0.001           # 印花税 千1 (仅卖出收取)
        self.slippage_rate = 0.001           # 单边滑点 千1 

        mode_str = "单吊绝对集中" if max_position_ratio == 1.0 else f"最高限购 {int(1/max_position_ratio)} 只"
        logger.info(f"[OK] L1 虚拟交易所启动 | 资金池: ¥{self.initial_capital:,.2f} | 攻击模式: {mode_str}")

    def calculate_position_size(self, last_price: float) -> int:
        """资金切片：计算合法买入股数，强制 1手=100股"""
        if last_price <= 0:
            return 0
            
        # 单票理论最大动用资金
        max_allocation = self.initial_capital * self.max_position_ratio
        # 实际购买力受限于当前剩余子弹
        actual_allocation = min(max_allocation, self.available_cash)
        
        # 剥离摩擦力（滑点+佣金预留）
        estimated_cost_ratio = 1.0 + self.commission_rate + self.slippage_rate
        purchasing_power = actual_allocation / estimated_cost_ratio
        
        # 量子化为 100 的整数倍
        raw_shares = purchasing_power / last_price
        hands = math.floor(raw_shares / 100)
        return int(hands * 100)

    def place_mock_order(self, stock_code: str, last_price: float, direction: str = 'BUY') -> bool:
        """触发虚拟状态机撮合"""
        if direction == 'BUY':
            volume = self.calculate_position_size(last_price)
            if volume < 100:
                logger.warning(f"[拦截] {stock_code} 剩余子弹(¥{self.available_cash:,.2f})不足以建立最低底仓(1手)！")
                return False
                
            # 施加物理滑点与手续费攻击
            executed_price = last_price * (1.0 + self.slippage_rate)
            gross_value = executed_price * volume
            commission = max(5.0, gross_value * self.commission_rate) # 最低收费 5 元
            total_cost = gross_value + commission
            
            # 状态机边界检查
            if total_cost > self.available_cash:
                logger.error(f"[FATAL] {stock_code} 预估耗资 ¥{total_cost:,.2f} 大于现金池，系统拒绝透支！")
                return False
                
            # 扣款与发货
            self.available_cash -= total_cost
            self.positions[stock_code] = self.positions.get(stock_code, 0) + volume
            self._record_trade(stock_code, 'BUY', executed_price, volume, commission, total_cost)
            
            logger.info(f"💥 [开仓] {stock_code} | 均价: {executed_price:.2f} | 规模: {volume}股 | 耗资: ¥{total_cost:,.2f} | 剩余: ¥{self.available_cash:,.2f}")
            return True
            
        elif direction == 'SELL':
            volume = self.positions.get(stock_code, 0)
            if volume <= 0:
                logger.warning(f"[拦截] {stock_code} 物理仓位为 0，拒绝做空！")
                return False
                
            executed_price = last_price * (1.0 - self.slippage_rate)
            gross_value = executed_price * volume
            commission = max(5.0, gross_value * self.commission_rate)
            tax = gross_value * self.tax_rate_sell
            net_proceeds = gross_value - commission - tax
            
            # 回血与清仓
            self.available_cash += net_proceeds
            del self.positions[stock_code]
            self._record_trade(stock_code, 'SELL', executed_price, volume, commission + tax, net_proceeds)
            
            logger.info(f"🔪 [平仓] {stock_code} | 均价: {executed_price:.2f} | 规模: {volume}股 | 回血: ¥{net_proceeds:,.2f} | 剩余: ¥{self.available_cash:,.2f}")
            return True
        
        return False

    def _record_trade(self, stock_code: str, direction: str, price: float, volume: int, fee: float, cash_flow: float):
        """交割单固化持久记录"""
        self.trades.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stock': stock_code,
            'direction': direction,
            'price': price,
            'volume': volume,
            'fee': fee,
            'cash_flow': cash_flow
        })

    def get_portfolio_summary(self) -> Dict:
        """获取当前投资组合摘要"""
        return {
            'initial_capital': self.initial_capital,
            'available_cash': self.available_cash,
            'positions': dict(self.positions),
            'position_count': len(self.positions),
            'trade_count': len(self.trades),
            'total_fees': sum(t['fee'] for t in self.trades)
        }

    def export_trades_to_csv(self, filepath: str):
        """导出交割单到CSV"""
        import pandas as pd
        if not self.trades:
            logger.warning("[WARN] 无交易记录可导出")
            return
        
        df = pd.DataFrame(self.trades)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"[OK] 交割单已导出: {filepath}")
