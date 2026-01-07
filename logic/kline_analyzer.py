"""
K线数据分析模块
属性：
- 实时获取股票K线数据
- 技术面指标计算 (MA, MACD, RSI, KDJ)
- 整体市场指数分析
- 游资股票集中度分析
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import akshare as ak
from dataclasses import dataclass


@dataclass
class KlineMetrics:
    """
    K线指标数据类
    """
    symbol: str
    current_price: float
    ma5: float
    ma10: float
    ma20: float
    macd: float
    macd_signal: float
    macd_histogram: float
    rsi14: float
    kdj_k: float
    kdj_d: float
    kdj_j: float
    volume_sma: float
    volatility: float
    trend_strength: str  # '强上', '强下', '中性'
    support_level: float
    resistance_level: float
    
    def get_technical_score(self) -> float:
        """
        根据技术指标计算综合技术评分 (0-100)
        """
        score = 0
        
        # MA题材 (20分)
        if self.ma5 > self.ma10 > self.ma20:
            score += 20
        elif self.ma5 > self.ma10:
            score += 10
        
        # MACD题材 (20分)
        if self.macd > self.macd_signal and self.macd_histogram > 0:
            score += 20
        elif self.macd > self.macd_signal:
            score += 10
        
        # RSI题材 (20分)
        if 50 < self.rsi14 < 70:
            score += 20
        elif 40 < self.rsi14 < 80:
            score += 10
        
        # KDJ题材 (20分)
        if self.kdj_k > self.kdj_d and 20 < self.kdj_k < 80:
            score += 20
        elif self.kdj_k > self.kdj_d:
            score += 10
        
        # 低位整理 (20分)
        if self.current_price > self.support_level * 1.02:
            score += 20
        elif self.current_price > self.support_level:
            score += 10
        
        return min(score, 100)


class KlineAnalyzer:
    """
    K线数据分析器
    """
    
    def __init__(self):
        self.cache = {}  # 临时缓存K线数据
        self.last_update = None
    
    def get_kline_data(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        period: str = 'daily'
    ) -> Optional[pd.DataFrame]:
        """
        获取K线数据
        
        Args:
            symbol: 股票代码 (e.g., '000001')
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 需要扩展汽了（'daily', 'weekly', 'monthly')
        
        Returns:
            pd.DataFrame with OHLCV data
        """
        try:
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            
            # 使用akshare获取数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust='qfq'  # 流通株抽攣除
            )
            
            if df.empty:
                return None
            
            # 数据预处理
            df = self._preprocess_data(df)
            
            # 缓存
            self.cache[symbol] = df
            self.last_update = datetime.now()
            
            return df
        
        except Exception as e:
            print(f"错误: 获取{symbol}K线数据失败 - {str(e)}")
            return None
    
    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        K线数据预处理
        """
        # 列名中文转换
        df = df.rename(columns={
            '日期': 'date',
            '开盘价': 'open',
            '收盘价': 'close',
            '最高价': 'high',
            '最低价': 'low',
            '成交量': 'volume',
            '成交额': 'amount'
        })
        
        # 确保数值类型
        for col in ['open', 'close', 'high', 'low', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        return df
    
    def calculate_technical_indicators(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        计算技术指标
        """
        df = df.copy()
        
        # MA
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi14'] = 100 - (100 / (1 + rs))
        
        # KDJ
        low_min = df['low'].rolling(window=9).min()
        high_max = df['high'].rolling(window=9).max()
        rsv = ((df['close'] - low_min) / (high_max - low_min)) * 100
        df['kdj_k'] = rsv.ewm(alpha=1/3).mean()
        df['kdj_d'] = df['kdj_k'].ewm(alpha=1/3).mean()
        df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
        
        # 整理位罪段
        df['support'] = df['low'].rolling(window=20).min()
        df['resistance'] = df['high'].rolling(window=20).max()
        
        # 波动率
        df['volatility'] = df['close'].pct_change().rolling(window=20).std() * 100
        
        # 成交量均线
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    def get_metrics(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None
    ) -> Optional[KlineMetrics]:
        """
        获取K线指标整体特征
        """
        df = self.get_kline_data(symbol, start_date, end_date)
        if df is None or len(df) == 0:
            return None
        
        # 计算技术指标
        df = self.calculate_technical_indicators(df)
        
        # 取最新一段数据
        last_row = df.iloc[-1]
        
        # 判断跌涨趋势
        if len(df) >= 3:
            if df['ma5'].iloc[-1] > df['ma10'].iloc[-1] > df['ma20'].iloc[-1]:
                trend = '强上'
            elif df['ma5'].iloc[-1] < df['ma10'].iloc[-1] < df['ma20'].iloc[-1]:
                trend = '强下'
            else:
                trend = '中性'
        else:
            trend = '中性'
        
        return KlineMetrics(
            symbol=symbol,
            current_price=float(last_row['close']),
            ma5=float(last_row['ma5']) if pd.notna(last_row['ma5']) else 0,
            ma10=float(last_row['ma10']) if pd.notna(last_row['ma10']) else 0,
            ma20=float(last_row['ma20']) if pd.notna(last_row['ma20']) else 0,
            macd=float(last_row['macd']) if pd.notna(last_row['macd']) else 0,
            macd_signal=float(last_row['macd_signal']) if pd.notna(last_row['macd_signal']) else 0,
            macd_histogram=float(last_row['macd_histogram']) if pd.notna(last_row['macd_histogram']) else 0,
            rsi14=float(last_row['rsi14']) if pd.notna(last_row['rsi14']) else 50,
            kdj_k=float(last_row['kdj_k']) if pd.notna(last_row['kdj_k']) else 50,
            kdj_d=float(last_row['kdj_d']) if pd.notna(last_row['kdj_d']) else 50,
            kdj_j=float(last_row['kdj_j']) if pd.notna(last_row['kdj_j']) else 50,
            volume_sma=float(last_row['volume_sma']) if pd.notna(last_row['volume_sma']) else 0,
            volatility=float(last_row['volatility']) if pd.notna(last_row['volatility']) else 0,
            trend_strength=trend,
            support_level=float(last_row['support']) if pd.notna(last_row['support']) else 0,
            resistance_level=float(last_row['resistance']) if pd.notna(last_row['resistance']) else 0
        )
    
    def get_market_overview(self) -> Dict:
        """
        获取整体市场指数分析
        """
        try:
            # 获取整体市场数据
            df = ak.stock_zh_a_spot_em()
            
            if df.empty:
                return {}
            
            return {
                'total_count': len(df),
                'up_count': (df['涨跌幅'] > 0).sum(),
                'down_count': (df['涨跌幅'] < 0).sum(),
                'limit_up_count': (df['涨跌幅'] >= 9.95).sum(),
                'limit_down_count': (df['涨跌幅'] <= -9.95).sum(),
                'avg_change': float(df['涨跌幅'].mean()),
                'total_volume': float(df['成交量'].sum()),
                'total_amount': float(df['成交额'].sum())
            }
        
        except Exception as e:
            print(f"错误: 获取市场指数失败 - {str(e)}")
            return {}
    
    def get_concentration_analysis(
        self,
        capital_name: str,
        df_lhb: pd.DataFrame
    ) -> Dict:
        """
        游资股票集中度分析
        
        Args:
            capital_name: 游资名称
            df_lhb: 龙虎榜数据
        
        Returns:
            集中度分析结果
        """
        # 筛选游资数据
        df_capital = df_lhb[df_lhb['游资名称'] == capital_name]
        
        if df_capital.empty:
            return {}
        
        # 股票分散度
        total_stocks = len(df_capital['股票代码'].unique())
        total_amount = df_capital['成交额'].sum()
        
        # 按股票箱附的成交额排序
        stock_amount = df_capital.groupby('股票代码')['成交额'].sum().sort_values(ascending=False)
        
        # HHI指数 (Herfindahl-Hirschman Index)
        hhi = ((stock_amount / total_amount) ** 2).sum() * 10000
        
        # 上刉5个股票集中度
        top5_concentration = stock_amount.head(5).sum() / total_amount
        
        return {
            'total_stocks': total_stocks,
            'total_amount': total_amount,
            'hhi_index': hhi,
            'top5_concentration': top5_concentration,
            'concentration_level': '高' if hhi > 3000 else '中' if hhi > 1500 else '低',
            'top_stocks': stock_amount.head(5).to_dict()
        }
