"""
向量化信号生成器 - 高性能技术指标计算
"""

import numpy as np
import pandas as pd
import streamlit as st
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SignalGeneratorVectorized:
    """向量化信号生成器"""
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def generate_ma_signals(close, fast_window=5, slow_window=20):
        """
        向量化 MA 跨越信号
        
        Args:
            close: 收盘价数据 (Series 或 array)
            fast_window: 快线窗口
            slow_window: 慢线窗口
        
        Returns:
            信号数组 (1=做多, 0=空仓)
        """
        close_array = close.values if isinstance(close, pd.Series) else close
        sma_fast = pd.Series(close_array).rolling(window=fast_window).mean().values
        sma_slow = pd.Series(close_array).rolling(window=slow_window).mean().values
        
        signals = np.where(sma_fast > sma_slow, 1, 0)
        return signals
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def generate_macd_signals(close, fast=12, slow=26, signal=9):
        """
        向量化 MACD 信号
        
        Args:
            close: 收盘价数据
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
        
        Returns:
            信号数组
        """
        close_array = close.values if isinstance(close, pd.Series) else close
        
        # MACD 计算
        ema_fast = pd.Series(close_array).ewm(span=fast).mean().values
        ema_slow = pd.Series(close_array).ewm(span=slow).mean().values
        macd = ema_fast - ema_slow
        
        # 信号线
        signal_line = pd.Series(macd).ewm(span=signal).mean().values
        
        # 信号: MACD > 信号线 = 买入
        signals = np.where(macd > signal_line, 1, 0)
        
        return signals
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def generate_rsi_signals(close, period=14, overbought=70, oversold=30):
        """
        向量化 RSI 信号
        
        Args:
            close: 收盘价数据
            period: RSI 周期
            overbought: 超买阈值
            oversold: 超卖阈值
        
        Returns:
            信号数组
        """
        close_array = close.values if isinstance(close, pd.Series) else close
        
        # 计算价格变化
        delta = np.diff(close_array)
        
        # 分离涨跌
        gains = np.where(delta > 0, delta, 0)
        losses = np.where(delta < 0, -delta, 0)
        
        # 平均涨跌幅
        avg_gains = pd.Series(gains).rolling(window=period).mean().values
        avg_losses = pd.Series(losses).rolling(window=period).mean().values
        
        # RSI 计算
        rs = np.where(avg_losses != 0, avg_gains / avg_losses, 0)
        rsi = 100 - (100 / (1 + rs))
        
        # 信号: RSI < 超卖 = 买入, RSI > 超买 = 卖出
        signals = np.where(rsi < oversold, 1, np.where(rsi > overbought, -1, 0))
        
        return signals
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def generate_bollinger_signals(close, window=20, std_dev=2):
        """
        向量化布林带信号
        
        Args:
            close: 收盘价数据
            window: 移动平均窗口
            std_dev: 标准差倍数
        
        Returns:
            信号数组
        """
        close_array = close.values if isinstance(close, pd.Series) else close
        
        # 布林带计算
        sma = pd.Series(close_array).rolling(window=window).mean().values
        std = pd.Series(close_array).rolling(window=window).std().values
        
        upper_band = sma + std_dev * std
        lower_band = sma - std_dev * std
        
        # 信号: 价格跌破下轨 = 买入, 突破上轨 = 卖出
        signals = np.where(close_array < lower_band, 1, np.where(close_array > upper_band, -1, 0))
        
        return signals
    
    @staticmethod
    def generate_signals(df, signal_type, **kwargs):
        """
        统一信号生成接口
        
        Args:
            df: 数据 DataFrame
            signal_type: 信号类型 ('MA', 'MACD', 'RSI', 'BOLL')
            **kwargs: 其他参数
        
        Returns:
            信号数组
        """
        if 'close' not in df.columns:
            raise ValueError("数据中缺少 'close' 列")
        
        close = df['close']
        
        if signal_type == 'MA':
            return SignalGeneratorVectorized.generate_ma_signals(
                close, 
                kwargs.get('fast_window', 5),
                kwargs.get('slow_window', 20)
            )
        elif signal_type == 'MACD':
            return SignalGeneratorVectorized.generate_macd_signals(
                close,
                kwargs.get('fast', 12),
                kwargs.get('slow', 26),
                kwargs.get('signal', 9)
            )
        elif signal_type == 'RSI':
            return SignalGeneratorVectorized.generate_rsi_signals(
                close,
                kwargs.get('period', 14),
                kwargs.get('overbought', 70),
                kwargs.get('oversold', 30)
            )
        elif signal_type == 'BOLL':
            return SignalGeneratorVectorized.generate_bollinger_signals(
                close,
                kwargs.get('window', 20),
                kwargs.get('std_dev', 2)
            )
        else:
            raise ValueError(f"不支持的信号类型: {signal_type}")


# 全局实例
_signal_generator = None


def get_signal_generator() -> SignalGeneratorVectorized:
    """获取信号生成器实例（单例）"""
    global _signal_generator
    if _signal_generator is None:
        _signal_generator = SignalGeneratorVectorized()
    return _signal_generator# V13.1 Reality Priority - Dynamic Thresholds + Divergence Detection
class SignalGenerator:
    '''
    V13.1 终极形态：事实一票否决制 (Reality Priority)
    特性：
    1. 动态阈值：基于流通市值的资金流出判定
    2. 背离识别：上涨趋势中的资金流出预警
    '''
    
    CAPITAL_OUT_THRESHOLD = -50000000  # 绝对阈值：5000万
    FLOW_RATIO_THRESHOLD = -0.01  # 相对阈值：流出占市值1%
    
    def calculate_final_signal(self, stock_code, ai_narrative_score, capital_flow_data, trend_status, circulating_market_cap=None, current_pct_change=None):
        '''
        计算最终交易信号 (V14.2)
        
        参数:
        - stock_code: 股票代码
        - ai_narrative_score: LLM基于新闻/基本面吹出来的分数 (0-100)
        - capital_flow_data: DDE净额 (float, 单位: 元)
        - trend_status: 技术面趋势 ('UP', 'DOWN', 'SIDEWAY')
        - circulating_market_cap: 流通市值 (float, 单位: 元), V13.1新增
        - current_pct_change: 当前涨幅 (float, 百分比), V14.2新增
        
        返回:
        - dict: {
            'signal': 'BUY' | 'SELL' | 'WAIT',
            'final_score': float,
            'reason': str,
            'fact_veto': bool,
            'risk_level': str,
            'limit_up_immunity': bool  # V14.2新增: 是否触发涨停豁免
        }
        '''
        
        # ---------------------------------------------------------
        # V14.2 涨停豁免权检查 (Limit Up Immunity)
        # ---------------------------------------------------------
        
        limit_up_immunity = False
        immunity_reason = ""
        
        # 如果涨幅接近或达到涨停（主板9.5%，创业板/科创板19.5%），触发豁免
        if current_pct_change is not None:
            if current_pct_change >= 9.5:  # 主板接近涨停
                limit_up_immunity = True
                immunity_reason = f"强势封板 (+{current_pct_change:.1f}%), 涨停豁免权生效"
                logger.info(f"Limit Up Immunity: {stock_code} {immunity_reason}")
            elif current_pct_change >= 19.5:  # 创业板/科创板涨停
                limit_up_immunity = True
                immunity_reason = f"20cm涨停 (+{current_pct_change:.1f}%), 涨停豁免权生效"
                logger.info(f"Limit Up Immunity: {stock_code} {immunity_reason}")
        
        # ---------------------------------------------------------
        # 第一层：一级事实熔断 (Fact Veto - The Physics)
        # V14.2: 涨停豁免权可屏蔽部分熔断
        # ---------------------------------------------------------
        
        # 1. 资金测谎仪 (Capital Flow Veto) - V13.1 动态阈值升级
        # V14.2: 如果触发涨停豁免，资金流出惩罚降级
        
        is_capital_fleeing = False
        fleeing_reason = ""
        
        # 绝对阈值检查
        if capital_flow_data < self.CAPITAL_OUT_THRESHOLD:
            # V14.2: 涨停豁免权下的资金流出处理
            if limit_up_immunity:
                # 涨停板上，资金流出可能是主力锁仓或游资接力，降低惩罚
                logger.info(f"Limit Up Immunity: {stock_code} 资金流出 {-capital_flow_data/10000:.0f}W 被豁免")
                is_capital_fleeing = False
            else:
                is_capital_fleeing = True
                fleeing_reason = f"Absolute outflow {-capital_flow_data/10000:.0f}W"
            
        # 相对阈值检查 (如果有市值数据)
        elif circulating_market_cap and circulating_market_cap > 0:
            flow_ratio = capital_flow_data / circulating_market_cap
            if flow_ratio < self.FLOW_RATIO_THRESHOLD:  # 流出超1%
                # V14.2: 涨停豁免权下的相对流出处理
                if limit_up_immunity:
                    logger.info(f"Limit Up Immunity: {stock_code} 相对流出 {flow_ratio*100:.2f}% 被豁免")
                    is_capital_fleeing = False
                else:
                    is_capital_fleeing = True
                    fleeing_reason = f"Relative outflow {flow_ratio*100:.2f}% (exceeds 1% warning line)"
        
        if is_capital_fleeing:
            logger.warning(f"Fact Veto: {stock_code} capital fleeing ({fleeing_reason}), AI narrative invalid.")
            return {
                'signal': 'SELL',
                'final_score': 0,
                'reason': f"Capital fleeing ({fleeing_reason}), AI narrative invalid",
                'fact_veto': True,
                'risk_level': 'HIGH',
                'limit_up_immunity': False
            }
        
        # 2. 趋势铁律 (Trend Veto)
        # V14.2: 涨停豁免权可屏蔽趋势熔断
        if trend_status == 'DOWN':
            if limit_up_immunity:
                # 涨停板上，趋势向下可能是弱转强，豁免
                logger.info(f"Limit Up Immunity: {stock_code} 趋势DOWN被豁免")
            else:
                logger.warning(f"Fact Veto: {stock_code} trend DOWN, no flying knife.")
                return {
                    'signal': 'WAIT',
                    'final_score': 0,
                    'reason': 'Trend DOWN, no flying knife',
                    'fact_veto': True,
                    'risk_level': 'HIGH',
                    'limit_up_immunity': False
                }
        
        # ---------------------------------------------------------
        # 第二层：顺势加权 (Trend Confirmation - The Boost)
        # V14.2: 涨停豁免权下的权重调整
        # ---------------------------------------------------------
        
        final_score = 0
        log_reason = ''
        risk_level = 'MEDIUM'
        
        # V14.2: 涨停豁免权处理
        if limit_up_immunity:
            # 涨停板上，强制给予AI分数1.0-1.1倍权重
            if current_pct_change >= 19.5:
                # 20cm涨停，给予更高权重
                final_score = ai_narrative_score * 1.1
                log_reason = f'Limit Up Immunity: 20cm涨停 (+{current_pct_change:.1f}%), 强势看多'
                risk_level = 'MEDIUM'  # 涨停板风险中等
            else:
                # 10cm涨停，给予正常权重
                final_score = ai_narrative_score * 1.0
                log_reason = f'Limit Up Immunity: 涨停 (+{current_pct_change:.1f}%), 强势看多'
                risk_level = 'MEDIUM'  # 涨停板风险中等
            
            logger.info(f'{stock_code} score: {final_score:.1f} | {log_reason}')
            
        # 情况 A：资金流入 + 趋势向上 (完美共振)
        elif capital_flow_data > 0 and trend_status == 'UP':
            final_score = ai_narrative_score * 1.2  # 给予20%的溢价奖励
            log_reason = 'Resonance Attack: Capital + Trend + AI'
            risk_level = 'LOW'
            
        # 情况 B：资金流入 + 趋势震荡 (潜伏/吸筹)
        elif capital_flow_data > 0:
            final_score = ai_narrative_score * 0.9
            log_reason = 'Observation: Capital inflow but trend not up'
            risk_level = 'MEDIUM'
            
        # 情况 C：资金流出/微流出 + 趋势向上 (背离/虚拉) - V13.1 严防诱多
        elif trend_status == 'UP':
            # V13.1: 如果股价涨但资金流出，视为"背离"
            # 这里 capital_flow_data 是负数（但未触及熔断线）
            final_score = ai_narrative_score * 0.4  # 极度打折，比V13更狠
            log_reason = 'Divergence: Price UP but capital outflow, potential bull trap'
            risk_level = 'HIGH'
            logger.warning(f"Divergence detected: {stock_code} price UP but capital outflow {-capital_flow_data/10000:.0f}W")
            
        # 情况 D：其他 (垃圾时间)
        else:
            final_score = 0
            log_reason = 'Invalid time: No capital no trend'
            risk_level = 'LOW'
        
        logger.info(f'{stock_code} score: {final_score:.1f} | {log_reason}')
        
        # ---------------------------------------------------------
        # 第三层：最终裁决
        # V14.2: 涨停豁免权下的阈值调整
        # ---------------------------------------------------------
        
        # V14.2: 涨停豁免权下的阈值调整
        if limit_up_immunity:
            # 涨停板上，降低买入阈值到75分（因为已经经过市场筛选）
            if final_score >= 75:
                signal = 'BUY'
            else:
                signal = 'WAIT'
        else:
            # V13 门槛提高：只有共振或极强逻辑才能开仓
            if final_score >= 85:
                signal = 'BUY'
            else:
                signal = 'WAIT'
        
        return {
            'signal': signal,
            'final_score': final_score,
            'reason': log_reason,
            'fact_veto': False,
            'risk_level': risk_level,
            'limit_up_immunity': limit_up_immunity
        }
    
    def get_trend_status(self, df, window=20):
        if len(df) < window:
            return 'SIDEWAY'
        
        ma = df['close'].rolling(window=window).mean()
        current_price = df['close'].iloc[-1]
        current_ma = ma.iloc[-1]
        
        recent_ma = ma.tail(5)
        slope = (recent_ma.iloc[-1] - recent_ma.iloc[0]) / len(recent_ma)
        
        if slope > 0 and current_price > current_ma:
            return 'UP'
        elif slope < 0 and current_price < current_ma:
            return 'DOWN'
        else:
            return 'SIDEWAY'
    
    def get_capital_flow(self, stock_code, data_manager):
        '''
        获取资金流向数据（DDE净额）和流通市值
        
        参数:
        - stock_code: 股票代码
        - data_manager: 数据管理器实例
        
        返回:
        - tuple: (dde_net_flow, circulating_market_cap)
        '''
        try:
            realtime_data = data_manager.get_realtime_data(stock_code)
            
            dde_net_flow = 0
            circulating_market_cap = 0
            
            if realtime_data:
                if 'dde_net_flow' in realtime_data:
                    dde_net_flow = realtime_data['dde_net_flow']
                else:
                    logger.warning(f'Cannot get DDE net flow for {stock_code}')
                
                if 'circulating_market_cap' in realtime_data:
                    circulating_market_cap = realtime_data['circulating_market_cap']
                else:
                    logger.debug(f'Cannot get circulating market cap for {stock_code}')
            
            return dde_net_flow, circulating_market_cap
        except Exception as e:
            logger.error(f'Get capital flow for {stock_code} failed: {e}')
            return 0, 0


_signal_generator_v13 = None

def get_signal_generator_v13():
    global _signal_generator_v13
    if _signal_generator_v13 is None:
        _signal_generator_v13 = SignalGenerator()
    return _signal_generator_v13
