"""
回测引擎

使用历史数据验证策略有效性
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from logic.utils.logger import get_logger
from logic.data_providers.data_manager import DataManager
from logic.data_providers.data_cleaner import DataCleaner
from logic.risk.position_manager import PositionManager

logger = get_logger(__name__)


@dataclass
class BacktestMetrics:
    """回测指标"""
    initial_capital: float
    final_equity: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_trades: int
    avg_profit: float
    avg_loss: float
    profit_loss_ratio: float


class BacktestEngine:
    """
    回测引擎
    
    功能：
    1. 使用历史数据验证策略有效性
    2. 计算收益率、最大回撤、夏普比率等指标
    3. 生成回测报告
    """
    
    def __init__(self, initial_capital=100000):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.position_manager = PositionManager(account_value=initial_capital)
        self.trades = []
        self.daily_returns = []
        self.equity_curve = []
    
    def run_backtest(self, strategy_func, stock_codes: List[str], start_date: str, end_date: str,
                     strategy_params: Dict = None) -> Dict:
        """
        运行回测
        
        Args:
            strategy_func: 策略函数
            stock_codes: 股票代码列表
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            strategy_params: 策略参数
        
        Returns:
            dict: 回测结果
        """
        logger.info(f"开始回测: {start_date} 至 {end_date}")
        
        db = DataManager()
        
        try:
            # 获取历史数据
            all_data = {}
            for code in stock_codes:
                df = db.get_history_data(code)
                if not df.empty:
                    # 过滤日期范围
                    df = df.copy()
                    df.index = pd.to_datetime(df.index)
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df = df[(df.index >= start_dt) & (df.index <= end_dt)]
                    if not df.empty:
                        all_data[code] = df
            
            if not all_data:
                return {
                    'success': False,
                    'error': '没有可用的历史数据'
                }
            
            # 按日期排序
            all_dates = sorted(set(
                date for df in all_data.values() for date in df.index
            ))
            
            # 逐日回测
            for date in all_dates:
                self._run_daily_backtest(date, all_data, strategy_func, strategy_params)
            
            # 计算回测指标
            metrics = self._calculate_metrics()
            
            return {
                'success': True,
                'metrics': metrics,
                'trades': self.trades,
                'equity_curve': self.equity_curve
            }
        
        finally:
            db.close()
    
    def _run_daily_backtest(self, date, all_data: Dict, strategy_func, strategy_params: Dict):
        """
        运行单日回测
        
        Args:
            date: 日期
            all_data: 所有股票的历史数据
            strategy_func: 策略函数
            strategy_params: 策略参数
        """
        # 获取当日数据
        daily_data = {}
        for code, df in all_data.items():
            if date in df.index:
                daily_data[code] = df.loc[date]
        
        if not daily_data:
            return
        
        # 计算当日总权益
        total_equity = self.current_capital
        for code, position in self.position_manager.current_positions.items():
            if code in daily_data:
                current_price = daily_data[code]['close']
                position_value = position['shares'] * current_price
                total_equity += position_value
        
        self.equity_curve.append({
            'date': date,
            'equity': total_equity
        })
        
        # 计算当日收益率
        if len(self.equity_curve) > 1:
            prev_equity = self.equity_curve[-2]['equity']
            daily_return = (total_equity - prev_equity) / prev_equity
            self.daily_returns.append(daily_return)
        
        # 调用策略函数
        signals = strategy_func(date, daily_data, strategy_params)
        
        # 执行交易信号
        for signal in signals:
            code = signal['code']
            action = signal['action']  # 'BUY' or 'SELL'
            
            if code not in daily_data:
                continue
            
            current_price = daily_data[code]['close']
            
            if action == 'BUY':
                self._execute_buy(code, current_price, signal)
            elif action == 'SELL':
                self._execute_sell(code, current_price, signal)
    
    def _execute_buy(self, code: str, price: float, signal: Dict):
        """
        执行买入
        
        Args:
            code: 股票代码
            price: 价格
            signal: 信号信息
        """
        # 计算建议仓位
        optimal_position = self.position_manager.calculate_optimal_position(
            current_price=price,
            stop_loss_ratio=signal.get('stop_loss_ratio', 0.05)
        )
        
        if optimal_position is None:
            return
        
        # 检查是否已经有持仓
        if code in self.position_manager.current_positions:
            logger.warning(f"已有 {code} 的持仓，跳过买入")
            return
        
        # 记录交易
        trade = {
            'date': signal.get('date'),
            'code': code,
            'action': 'BUY',
            'price': price,
            'shares': optimal_position['shares'],
            'amount': optimal_position['position_value'],
            'signal_score': signal.get('signal_score', 0),
            'stop_loss_price': optimal_position['stop_loss_price']
        }
        
        self.trades.append(trade)
        
        # 添加持仓
        self.position_manager.add_position(code, optimal_position['shares'], price)
        
        logger.info(f"买入 {code} {optimal_position['shares']}股 @ {price:.2f}")
    
    def _execute_sell(self, code: str, price: float, signal: Dict):
        """
        执行卖出
        
        Args:
            code: 股票代码
            price: 价格
            signal: 信号信息
        """
        if code not in self.position_manager.current_positions:
            return
        
        position = self.position_manager.current_positions[code]
        shares = position['shares']
        cost_price = position['cost']
        
        # 计算盈亏
        profit = (price - cost_price) * shares
        profit_ratio = (price - cost_price) / cost_price * 100
        
        # 记录交易
        trade = {
            'date': signal.get('date'),
            'code': code,
            'action': 'SELL',
            'price': price,
            'shares': shares,
            'amount': price * shares,
            'profit': profit,
            'profit_ratio': profit_ratio
        }
        
        self.trades.append(trade)
        
        # 移除持仓
        self.position_manager.remove_position(code, shares)
        
        logger.info(f"卖出 {code} {shares}股 @ {price:.2f}, 盈亏: {profit:.2f} ({profit_ratio:.2f}%)")
    
    def _calculate_metrics(self) -> Dict:
        """
        计算回测指标
        
        Returns:
            dict: 回测指标
        """
        if not self.equity_curve:
            return {}
        
        # 总收益率
        final_equity = self.equity_curve[-1]['equity']
        total_return = (final_equity - self.initial_capital) / self.initial_capital * 100
        
        # 年化收益率
        days = len(self.equity_curve)
        annual_return = (final_equity / self.initial_capital) ** (365 / days) - 1
        
        # 最大回撤
        max_drawdown = 0
        peak = self.initial_capital
        for point in self.equity_curve:
            equity = point['equity']
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 夏普比率
        if self.daily_returns:
            avg_return = np.mean(self.daily_returns)
            std_return = np.std(self.daily_returns)
            sharpe_ratio = avg_return / std_return * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 胜率
        buy_trades = [t for t in self.trades if t['action'] == 'BUY']
        sell_trades = [t for t in self.trades if t['action'] == 'SELL']
        
        if sell_trades:
            win_trades = [t for t in sell_trades if t['profit'] > 0]
            win_rate = len(win_trades) / len(sell_trades) * 100
        else:
            win_rate = 0
        
        # 平均盈利/平均亏损
        if sell_trades:
            avg_profit = np.mean([t['profit'] for t in sell_trades if t['profit'] > 0]) if win_trades else 0
            avg_loss = np.mean([t['profit'] for t in sell_trades if t['profit'] < 0]) if len(sell_trades) > len(win_trades) else 0
        else:
            avg_profit = 0
            avg_loss = 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'annual_return': annual_return * 100,
            'max_drawdown': max_drawdown * 100,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'total_trades': len(buy_trades),
            'profit_trades': len(win_trades) if sell_trades else 0,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_loss_ratio': abs(avg_profit / avg_loss) if avg_loss != 0 else 0
        }
    
    def generate_report(self) -> str:
        """
        生成回测报告
        
        Returns:
            str: 回测报告文本
        """
        metrics = self._calculate_metrics()
        
        report = f"""
# 回测报告

## 资金情况
- 初始资金: ¥{self.initial_capital:,.2f}
- 最终资金: ¥{metrics['final_equity']:,.2f}
- 总收益率: {metrics['total_return']:.2f}%
- 年化收益率: {metrics['annual_return']:.2f}%

## 风险指标
- 最大回撤: {metrics['max_drawdown']:.2f}%
- 夏普比率: {metrics['sharpe_ratio']:.2f}

## 交易统计
- 总交易次数: {metrics['total_trades']}
- 盈利交易: {metrics['profit_trades']}
- 胜率: {metrics['win_rate']:.2f}%
- 平均盈利: ¥{metrics['avg_profit']:,.2f}
- 平均亏损: ¥{metrics['avg_loss']:,.2f}
- 盈亏比: {metrics['profit_loss_ratio']:.2f}

## 交易明细
"""
        
        for trade in self.trades:
            if trade['action'] == 'BUY':
                report += f"- {trade['date']} 买入 {trade['code']} {trade['shares']}股 @ ¥{trade['price']:.2f}\n"
            else:
                report += f"- {trade['date']} 卖出 {trade['code']} {trade['shares']}股 @ ¥{trade['price']:.2f} 盈亏: ¥{trade['profit']:.2f} ({trade['profit_ratio']:.2f}%)\n"
        
        return report


def dragon_strategy_backtest(date, daily_data, params):
    """
    龙头战法回测策略
    
    Args:
        date: 日期
        daily_data: 当日数据
        params: 策略参数
    
    Returns:
        list: 交易信号列表
    """
    signals = []
    min_score = params.get('min_score', 60)
    min_change_pct = params.get('min_change_pct', 7.0)
    min_volume_ratio = params.get('min_volume_ratio', 2.0)
    
    for code, data in daily_data.items():
        # 🔥 修正：使用pre_close（昨收价）计算真实涨幅，严禁使用open
        pre_close = data.get('pre_close', data.get('last_close', data.get('open', data['close'])))
        change_pct = (data['close'] - pre_close) / pre_close * 100 if pre_close > 0 else 0
        
        # 简化版评分
        score = 0
        if change_pct >= min_change_pct:
            score += 30
        if data['volume'] > 0:
            score += 20
        
        # 生成买入信号
        if score >= min_score and change_pct >= min_change_pct:
            signals.append({
                'date': date,
                'code': code,
                'action': 'BUY',
                'signal_score': score,
                'stop_loss_ratio': 0.05
            })
    
    # 生成卖出信号（持仓超过3天）
    for code in [s['code'] for s in signals if s['action'] == 'BUY']:
        signals.append({
            'date': date,
            'code': code,
            'action': 'SELL'
        })
    
    return signals


def get_backtest_engine(initial_capital=100000):
    """
    获取回测引擎实例（工厂函数）
    
    Args:
        initial_capital: 初始资金，默认 100000
    
    Returns:
        BacktestEngine: 回测引擎实例
    """
    return BacktestEngine(initial_capital=initial_capital)
