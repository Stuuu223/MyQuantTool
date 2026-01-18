"""
V14.4 Signal Generator - 龙虎榜反制 (LHB Counter-Strike)
包含功能：
1. V13.1: 事实一票否决 (资金流出/趋势破位)
2. V14.2: 涨停豁免权 (强势封板无视利空)
3. V14.4: 龙虎榜反制 (陷阱识别 & 弱转强博弈)
"""

import numpy as np
import pandas as pd
import streamlit as st
from typing import Optional, Dict, Union
from logic.logger import get_logger
import config_system as config

logger = get_logger(__name__)


class SignalGeneratorVectorized:
    """向量化信号生成器 (保留用于基础技术指标计算)"""
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def generate_ma_signals(close, fast_window=5, slow_window=20):
        close_array = close.values if isinstance(close, pd.Series) else close
        sma_fast = pd.Series(close_array).rolling(window=fast_window).mean().values
        sma_slow = pd.Series(close_array).rolling(window=slow_window).mean().values
        return np.where(sma_fast > sma_slow, 1, 0)
    
    @staticmethod
    def generate_macd_signals(close, fast=12, slow=26, signal=9):
        # 简单MACD实现
        close_s = pd.Series(close)
        exp1 = close_s.ewm(span=fast, adjust=False).mean()
        exp2 = close_s.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return np.where(macd > signal_line, 1, 0)

    @staticmethod
    def generate_signals(df, signal_type, **kwargs):
        if 'close' not in df.columns:
            return np.zeros(len(df))
        return np.zeros(len(df)) # 占位符


class SignalGenerator:
    """
    V14.4 终极裁判：博弈论核心
    集成：资金熔断 + 涨停豁免 + 龙虎榜反制
    """
    
    # 核心阈值配置
    CAPITAL_VETO_THRESHOLD = -50000000  # 资金流出 > 5000万 熔断
    LHB_LUXURY_THRESHOLD = 50000000     # 龙虎榜净买入 > 5000万 视为豪华榜
    
    def calculate_final_signal(self, 
                               stock_code: str, 
                               ai_score: float, 
                               capital_flow: float, 
                               trend: str, 
                               current_pct_change: float = 0.0,
                               yesterday_lhb_net_buy: float = 0.0,
                               open_pct_change: float = 0.0,
                               circulating_market_cap: float = None) -> Dict[str, Union[str, float, str]]:
        """
        计算最终交易信号 (V14.4 完整版)
        
        参数:
        - yesterday_lhb_net_buy: 昨日龙虎榜净买入额 (V14.4 新增)
        - open_pct_change: 今日开盘涨幅 (V14.4 新增)
        """
        
        signal = "WAIT"
        final_score = 0.0
        reason = ""
        risk_level = "NORMAL"

        # =========================================================
        # 1. [V14.2] 涨停豁免权 (Limit Up Immunity) - 最高优先级
        # =========================================================
        is_limit_up = False
        # 主板 > 9.5%, 科创/创业 > 19.5%
        if current_pct_change > 9.5: 
            is_limit_up = True
            risk_level = "MEDIUM" # 涨停板虽然豁免，但本身有炸板风险
            final_score = ai_score
            
            # 20cm 给更高溢价
            if current_pct_change > 19.0:
                final_score = max(ai_score, 85) * 1.1
            else:
                final_score = max(ai_score, 80) * 1.0
                
            reason = f"🚀 [涨停豁免] 强势封板({current_pct_change}%)，无视背离与陷阱"
            logger.info(f"{stock_code} {reason}")
            return {"signal": "BUY", "score": min(final_score, 100), "reason": reason, "risk": risk_level}

        # =========================================================
        # 2. [V13.1] 事实熔断 (Fact Veto) - 物理定律
        # =========================================================
        # 资金大逃亡
        if capital_flow < self.CAPITAL_VETO_THRESHOLD:
            reason = f"🚨 [资金熔断] 主力巨额流出 {-capital_flow/10000:.0f}万"
            logger.warning(f"{stock_code} {reason}")
            return {"signal": "SELL", "score": 0, "reason": reason, "risk": "HIGH"}
        
        # 小盘股失血 (流出超流通盘1%)
        if circulating_market_cap and circulating_market_cap > 0:
            if (capital_flow / circulating_market_cap) < -0.01:
                reason = f"🩸 [失血熔断] 流出占比过大 ({-capital_flow/10000:.0f}万)"
                return {"signal": "SELL", "score": 0, "reason": reason, "risk": "HIGH"}

        # 趋势破位
        if trend == 'DOWN':
            return {"signal": "WAIT", "score": 0, "reason": "📉 [趋势熔断] 空头排列", "risk": "HIGH"}

        # =========================================================
        # 3. [V14.4] 龙虎榜反制 (LHB Counter-Strike) - 博弈核心
        # =========================================================
        lhb_modifier = 1.0
        lhb_msg = ""
        
        # 只有在昨日有"豪华榜"时才触发此逻辑
        if yesterday_lhb_net_buy > self.LHB_LUXURY_THRESHOLD:
            
            # 场景 A: 陷阱 (The Trap) - 豪华榜 + 大高开
            if open_pct_change > 6.0:
                lhb_modifier = 0.0 # 直接废掉 AI 分数
                reason = f"⚠️ [榜单陷阱] 豪华榜净买{yesterday_lhb_net_buy/10000:.0f}万 + 高开{open_pct_change}% -> 警惕兑现"
                # 这里我们不直接返回 SELL (因为资金可能还没流出)，但给予极大惩罚，让它变 WAIT
                return {"signal": "WAIT", "score": 10.0, "reason": reason, "risk": "HIGH"}
            
            # 场景 B: 弱转强 (Weak-to-Strong) - 豪华榜 + 平开/微红
            elif -2.0 <= open_pct_change <= 3.0:
                lhb_modifier = 1.3 # 给予 30% 溢价
                lhb_msg = f"🚀 [弱转强] 豪华榜+平开({open_pct_change}%)，主力承接有力"
                
            # 场景 C: 不及预期 - 豪华榜 + 低开
            elif open_pct_change < -3.0:
                lhb_modifier = 0.5 # 只有 50% 信心
                lhb_msg = f"📉 [不及预期] 豪华榜被核({open_pct_change}%)"
        
        # =========================================================
        # 4. 最终评分计算
        # =========================================================
        
        # 基础分：AI (逻辑)
        # 修正分：DDE (资金)
        
        # 如果非涨停，且资金流出 (背离识别)
        if capital_flow < 0 and trend == 'UP':
            final_score = ai_score * 0.4 # [V13.1] 缩量诱多打折
            reason = "⚠️ [量价背离] 缩量/流出上涨"
        else:
            # 正常情况：资金流入 或 震荡
            final_score = ai_score * lhb_modifier
            if lhb_msg:
                reason = lhb_msg
            elif capital_flow > 0:
                reason = "✅ [共振] 逻辑+资金双强"
        
        # 最终门槛
        if final_score >= 80:
            signal = "BUY"
        else:
            signal = "WAIT"

        return {
            "signal": signal, 
            "score": min(final_score, 100), 
            "reason": reason, 
            "risk": risk_level
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
    
    def get_yesterday_lhb_data(self, stock_code, data_manager):
        '''
        V14.4 新增：获取昨日龙虎榜数据
        
        参数:
        - stock_code: 股票代码
        - data_manager: 数据管理器实例
        
        返回:
        - tuple: (yesterday_lhb_net_buy, open_pct_change)
        '''
        try:
            # 尝试从 akshare 获取龙虎榜数据
            import akshare as ak
            from datetime import datetime, timedelta
            
            # 获取昨天的日期
            yesterday = datetime.now() - timedelta(days=1)
            date_str = yesterday.strftime("%Y%m%d")
            
            # 获取龙虎榜数据
            try:
                lhb_data = ak.stock_lhb_detail_em(date=date_str)
                
                if lhb_data is not None and not lhb_data.empty:
                    # 查找该股票的龙虎榜数据
                    stock_lhb = lhb_data[lhb_data['代码'] == stock_code]
                    
                    if not stock_lhb.empty:
                        # 获取净买入额
                        net_buy = stock_lhb['净买入'].iloc[0] if '净买入' in stock_lhb.columns else 0
                        
                        # 获取今日开盘涨幅
                        realtime_data = data_manager.get_realtime_data(stock_code)
                        open_pct = realtime_data.get('open_pct_change', 0) if realtime_data else 0
                        
                        return net_buy, open_pct
            except Exception as e:
                logger.warning(f"获取龙虎榜数据失败: {e}")
            
            # 如果获取失败，返回默认值
            return 0, 0
            
        except ImportError:
            logger.warning("akshare 未安装，无法获取龙虎榜数据")
            return 0, 0
        except Exception as e:
            logger.error(f"获取龙虎榜数据失败: {e}")
            return 0, 0


# 全局实例
_signal_generator_v14_4 = None

def get_signal_generator_v14_4():
    global _signal_generator_v14_4
    if _signal_generator_v14_4 is None:
        _signal_generator_v14_4 = SignalGenerator()
    return _signal_generator_v14_4