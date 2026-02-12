"""
多股票对比分析模块
"""
import pandas as pd
import numpy as np
from logic.core.algo import QuantAlgo

class StockComparator:
    """股票对比分析器"""
    
    def __init__(self, data_manager):
        self.dm = data_manager
    
    def compare_stocks(self, symbols, start_date, end_date):
        """
        对比多只股票的技术指标
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            对比结果 DataFrame
        """
        comparison_data = []
        
        for symbol in symbols:
            try:
                df = self.dm.get_history_data(symbol, start_date=start_date, end_date=end_date)
                
                if df.empty or len(df) < 30:
                    continue
                
                current_price = df.iloc[-1]['close']
                prev_close = df.iloc[-2]['close']
                # 防止除以零
                if prev_close != 0:
                    change_pct = (current_price - prev_close) / prev_close * 100
                else:
                    change_pct = 0.0
                
                # 计算各项指标
                atr = QuantAlgo.calculate_atr(df)
                macd_data = QuantAlgo.calculate_macd(df)
                rsi_data = QuantAlgo.calculate_rsi(df)
                bollinger_data = QuantAlgo.calculate_bollinger_bands(df)
                
                comparison_data.append({
                    '股票代码': symbol,
                    '最新价格': round(current_price, 2),
                    '涨跌幅': round(change_pct, 2),
                    'ATR波动率': round(atr, 2),
                    'MACD趋势': macd_data['Trend'],
                    'RSI数值': rsi_data['RSI'],
                    'RSI信号': rsi_data['Signal'],
                    '布林位置': bollinger_data['解读']
                })
                
            except Exception as e:
                print(f"分析股票 {symbol} 失败: {e}")
                continue
        
        return pd.DataFrame(comparison_data)
    
    def get_performance_comparison(self, symbols, start_date, end_date):
        """
        获取股票表现对比（收益率）
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            收益率对比 DataFrame
        """
        performance_data = {}
        
        for symbol in symbols:
            try:
                df = self.dm.get_history_data(symbol, start_date=start_date, end_date=end_date)
                
                if df.empty or len(df) < 2:
                    continue
                
                # 计算累计收益率
                df['returns'] = df['close'].pct_change()
                df['cumulative_returns'] = (1 + df['returns']).cumprod() - 1
                
                performance_data[symbol] = df['cumulative_returns']
                
            except Exception as e:
                print(f"计算 {symbol} 收益率失败: {e}")
                continue
        
        return pd.DataFrame(performance_data)