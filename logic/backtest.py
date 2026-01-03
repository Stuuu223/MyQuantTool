"""
简单的回测模块
用于测试网格交易策略的历史表现
"""
import pandas as pd
import numpy as np

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
    
    def run_grid_strategy_backtest(self, df, atr_multiplier=0.5, grid_ratio=0.1, transaction_cost=0.001):
        """
        运行网格策略回测
        
        Args:
            df: 历史K线数据
            atr_multiplier: ATR倍数
            grid_ratio: 每次交易的比例
            transaction_cost: 交易手续费（默认0.1%）
        
        Returns:
            回测结果字典
        """
        # 计算ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # 计算网格线
        df['grid_center'] = df['close'].rolling(20).mean()
        df['grid_upper'] = df['grid_center'] + (df['atr'] * atr_multiplier)
        df['grid_lower'] = df['grid_center'] - (df['atr'] * atr_multiplier)
        
        # 初始化回测状态
        capital = self.initial_capital
        position = 0  # 持仓数量
        trades = []
        
        for i in range(20, len(df)):  # 从第20天开始，确保指标计算完成
            current_price = df.iloc[i]['close']
            grid_upper = df.iloc[i]['grid_upper']
            grid_lower = df.iloc[i]['grid_lower']
            
            # 买入信号：价格跌破下轨且没有持仓
            if current_price < grid_lower and position == 0:
                buy_amount = capital * grid_ratio
                shares = int(buy_amount / current_price)
                if shares > 0:
                    position = shares
                    capital -= shares * current_price * (1 + transaction_cost)
                    trades.append({
                        'date': df.iloc[i]['date'],
                        'type': '买入',
                        'price': current_price,
                        'shares': shares,
                        'capital': capital
                    })
            
            # 卖出信号：价格突破上轨且有持仓
            elif current_price > grid_upper and position > 0:
                capital += position * current_price * (1 - transaction_cost)
                trades.append({
                    'date': df.iloc[i]['date'],
                    'type': '卖出',
                    'price': current_price,
                    'shares': position,
                    'capital': capital
                })
                position = 0
        
        # 计算最终资产价值
        final_price = df.iloc[-1]['close']
        final_capital = capital + position * final_price
        
        # 计算收益
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100
        
        # 计算基准收益（买入持有）
        first_price = df.iloc[20]['close']
        benchmark_return = (final_price - first_price) / first_price * 100
        
        return {
            '初始资金': self.initial_capital,
            '最终资金': round(final_capital, 2),
            '总收益率': round(total_return, 2),
            '基准收益率': round(benchmark_return, 2),
            '超额收益': round(total_return - benchmark_return, 2),
            '交易次数': len(trades),
            '交易记录': pd.DataFrame(trades) if trades else pd.DataFrame()
        }
    
    def generate_backtest_report(self, backtest_result):
        """生成回测报告"""
        report = f"""
## 📊 回测报告

### 资金表现
- 初始资金：¥{backtest_result['初始资金']:,.2f}
- 最终资金：¥{backtest_result['最终资金']:,.2f}
- 总收益率：{backtest_result['总收益率']:.2f}%

### 策略对比
- 基准收益率（买入持有）：{backtest_result['基准收益率']:.2f}%
- 超额收益：{backtest_result['超额收益']:.2f}%

### 交易统计
- 总交易次数：{backtest_result['交易次数']} 次

### 结论
"""
        if backtest_result['超额收益'] > 0:
            report += "✅ 网格策略表现优于买入持有策略，超额收益为正。"
        else:
            report += "❌ 网格策略表现不如买入持有策略，建议优化参数或策略。"
        
        return report