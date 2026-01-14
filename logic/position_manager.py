"""
资金管理模块

基于凯利公式和波动率的仓位管理
实现科学的风险控制
"""

import numpy as np
from logic.logger import get_logger

logger = get_logger(__name__)


class PositionManager:
    """
    仓位管理器
    
    功能：
    1. 基于最大单笔亏损的仓位计算
    2. 基于波动率的仓位调整
    3. 凯利公式实现
    4. 止损点自动计算
    """
    
    # 风险控制参数
    MAX_SINGLE_LOSS_RATIO = 0.02    # 单笔交易最大亏损比例（2%）
    MAX_TOTAL_POSITION = 0.8        # 最大总仓位（80%）
    DEFAULT_STOP_LOSS_RATIO = 0.05  # 默认止损比例（5%）
    
    def __init__(self, account_value=100000):
        """
        初始化仓位管理器
        
        Args:
            account_value: 账户总资金
        """
        self.account_value = account_value
        self.current_positions = {}  # 当前持仓 {code: {'shares': 数量, 'cost': 成本价}}
        self.total_position_value = 0  # 当前总持仓市值
    
    def calculate_position_size_by_risk(self, current_price, stop_loss_price=None, stop_loss_ratio=None):
        """
        基于最大单笔亏损的仓位计算
        
        Args:
            current_price: 当前价格
            stop_loss_price: 止损价格（可选）
            stop_loss_ratio: 止损比例（可选，如果没有提供止损价格）
        
        Returns:
            dict: {
                'shares': 建议股数,
                'position_value': 仓位市值,
                'position_ratio': 仓位比例,
                'stop_loss_price': 止损价格,
                'max_loss': 最大亏损金额
            }
        """
        # 计算止损价格
        if stop_loss_price is None:
            if stop_loss_ratio is None:
                stop_loss_ratio = self.DEFAULT_STOP_LOSS_RATIO
            stop_loss_price = current_price * (1 - stop_loss_ratio)
        
        # 计算每股风险
        risk_per_share = current_price - stop_loss_price
        
        if risk_per_share <= 0:
            logger.warning(f"止损价格 {stop_loss_price} 不低于当前价格 {current_price}")
            return None
        
        # 计算最大可承受亏损
        max_loss_amount = self.account_value * self.MAX_SINGLE_LOSS_RATIO
        
        # 计算建议股数
        shares = int(max_loss_amount / risk_per_share)
        
        # 计算仓位市值
        position_value = shares * current_price
        
        # 计算仓位比例
        position_ratio = position_value / self.account_value
        
        return {
            'shares': shares,
            'position_value': position_value,
            'position_ratio': position_ratio,
            'stop_loss_price': stop_loss_price,
            'max_loss': max_loss_amount,
            'risk_per_share': risk_per_share
        }
    
    def calculate_position_size_by_volatility(self, current_price, volatility, confidence_level=2.0):
        """
        基于波动率的仓位调整
        
        Args:
            current_price: 当前价格
            volatility: 波动率（标准差）
            confidence_level: 置信水平（默认2，即2倍标准差）
        
        Returns:
            dict: 仓位信息
        """
        # 计算止损价格（基于波动率）
        stop_loss_price = current_price * (1 - confidence_level * volatility)
        
        # 使用风险控制方法计算仓位
        return self.calculate_position_size_by_risk(current_price, stop_loss_price=stop_loss_price)
    
    def calculate_kelly_position(self, win_rate, avg_win, avg_loss):
        """
        凯利公式计算最优仓位比例
        
        Args:
            win_rate: 胜率（0-1）
            avg_win: 平均盈利（比例）
            avg_loss: 平均亏损（比例，正数）
        
        Returns:
            float: 最优仓位比例
        """
        if avg_loss == 0:
            return 0
        
        # 凯利公式：f = (bp - q) / b
        # f = 最优仓位比例
        # b = 盈亏比（平均盈利/平均亏损）
        # p = 胜率
        # q = 败率（1-p）
        
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - p
        
        kelly_ratio = (b * p - q) / b
        
        # 凯利公式结果可能为负，限制在0-1之间
        kelly_ratio = max(0, min(1, kelly_ratio))
        
        # 通常使用半凯利或四分之一凯利，以降低风险
        conservative_kelly = kelly_ratio * 0.5
        
        return {
            'kelly_ratio': kelly_ratio,
            'conservative_kelly': conservative_kelly,
            'win_rate': win_rate,
            'profit_loss_ratio': b
        }
    
    def calculate_optimal_position(self, current_price, stop_loss_price=None, volatility=None, 
                                  win_rate=None, avg_win=None, avg_loss=None, max_position_ratio=None):
        """
        综合计算最优仓位
        
        Args:
            current_price: 当前价格
            stop_loss_price: 止损价格（可选）
            volatility: 波动率（可选）
            win_rate: 胜率（可选，用于凯利公式）
            avg_win: 平均盈利（可选，用于凯利公式）
            avg_loss: 平均亏损（可选，用于凯利公式）
            max_position_ratio: 最大仓位比例限制（可选）
        
        Returns:
            dict: 最优仓位信息
        """
        # 1. 基于风险控制的仓位
        risk_position = self.calculate_position_size_by_risk(current_price, stop_loss_price)
        
        if risk_position is None:
            return None
        
        # 2. 基于波动率的仓位（如果提供了波动率）
        if volatility is not None:
            volatility_position = self.calculate_position_size_by_volatility(current_price, volatility)
            # 取两者的较小值
            if volatility_position['position_ratio'] < risk_position['position_ratio']:
                risk_position = volatility_position
        
        # 3. 基于凯利公式的仓位（如果提供了胜率等数据）
        if win_rate is not None and avg_win is not None and avg_loss is not None:
            kelly_result = self.calculate_kelly_position(win_rate, avg_win, avg_loss)
            kelly_position_value = self.account_value * kelly_result['conservative_kelly']
            kelly_shares = int(kelly_position_value / current_price)
            
            # 取两者的较小值
            if kelly_shares < risk_position['shares']:
                risk_position['shares'] = kelly_shares
                risk_position['position_value'] = kelly_position_value
                risk_position['position_ratio'] = kelly_result['conservative_kelly']
                risk_position['kelly_ratio'] = kelly_result['conservative_kelly']
        
        # 4. 检查总仓位限制
        available_ratio = self.MAX_TOTAL_POSITION - self.get_total_position_ratio()
        
        if risk_position['position_ratio'] > available_ratio:
            # 调整仓位以不超过总仓位限制
            risk_position['position_ratio'] = available_ratio
            risk_position['position_value'] = self.account_value * available_ratio
            risk_position['shares'] = int(risk_position['position_value'] / current_price)
            risk_position['adjusted'] = True
            risk_position['adjust_reason'] = '总仓位限制'
        
        # 5. 检查最大仓位限制
        if max_position_ratio is not None and risk_position['position_ratio'] > max_position_ratio:
            risk_position['position_ratio'] = max_position_ratio
            risk_position['position_value'] = self.account_value * max_position_ratio
            risk_position['shares'] = int(risk_position['position_value'] / current_price)
            risk_position['adjusted'] = True
            risk_position['adjust_reason'] = '最大仓位限制'
        
        return risk_position
    
    def add_position(self, code, shares, cost_price):
        """
        添加持仓
        
        Args:
            code: 股票代码
            shares: 股数
            cost_price: 成本价
        """
        if code in self.current_positions:
            # 已有持仓，更新
            old_shares = self.current_positions[code]['shares']
            old_cost = self.current_positions[code]['cost']
            
            # 计算新的成本价
            total_shares = old_shares + shares
            total_cost = old_shares * old_cost + shares * cost_price
            new_cost = total_cost / total_shares
            
            self.current_positions[code] = {
                'shares': total_shares,
                'cost': new_cost
            }
        else:
            # 新增持仓
            self.current_positions[code] = {
                'shares': shares,
                'cost': cost_price
            }
        
        # 更新总持仓市值
        self._update_total_position_value()
    
    def remove_position(self, code, shares=None):
        """
        移除持仓
        
        Args:
            code: 股票代码
            shares: 卖出股数（如果不提供，则全部卖出）
        """
        if code not in self.current_positions:
            return
        
        if shares is None:
            # 全部卖出
            del self.current_positions[code]
        else:
            # 部分卖出
            current_shares = self.current_positions[code]['shares']
            if shares >= current_shares:
                del self.current_positions[code]
            else:
                self.current_positions[code]['shares'] = current_shares - shares
        
        # 更新总持仓市值
        self._update_total_position_value()
    
    def _update_total_position_value(self):
        """更新总持仓市值"""
        self.total_position_value = 0
        for code, position in self.current_positions.items():
            # 这里需要获取当前价格，简化版暂时用成本价
            self.total_position_value += position['shares'] * position['cost']
    
    def get_total_position_ratio(self):
        """
        获取当前总仓位比例
        
        Returns:
            float: 总仓位比例
        """
        return self.total_position_value / self.account_value
    
    def get_available_cash(self):
        """
        获取可用资金
        
        Returns:
            float: 可用资金
        """
        return self.account_value - self.total_position_value
    
    def get_risk_exposure(self):
        """
        获取风险敞口
        
        Returns:
            dict: 风险信息
        """
        return {
            'total_position_ratio': self.get_total_position_ratio(),
            'available_cash': self.get_available_cash(),
            'cash_ratio': self.get_available_cash() / self.account_value,
            'position_count': len(self.current_positions)
        }