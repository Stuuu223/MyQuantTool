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
                               circulating_market_cap: float = None,
                               market_sentiment_score: float = 50,
                               market_status: str = "震荡") -> Dict[str, Union[str, float, str]]:
        """
        计算最终交易信号 (V16 完整版 - 环境熔断)
        
        参数:
        - yesterday_lhb_net_buy: 昨日龙虎榜净买入额 (V14.4 新增)
        - open_pct_change: 今日开盘涨幅 (V14.4 新增)
        - market_sentiment_score: 市场情绪分数 (0-100) (V16 新增)
        - market_status: 市场状态 ('主升', '退潮', '震荡', '冰点') (V16 新增)
        """
        
        signal = "WAIT"
        final_score = 0.0
        reason = ""
        risk_level = "NORMAL"

        # =========================================================
        # 0. [V16] 环境熔断 (Market Veto) - 最高优先级（除了涨停豁免）
        # =========================================================
        
        # 冰点熔断：市场情绪 < 20，禁止开仓
        if market_sentiment_score < 20:
            # 除非个股触发涨停豁免（只有真龙能穿越冰点）
            if current_pct_change > 9.5:
                # 涨停股可以穿越冰点
                reason = f"❄️ [环境熔断-豁免] 市场冰点({market_sentiment_score})，但{stock_code}强势封板({current_pct_change}%)，真龙穿越"
                logger.info(f"{stock_code} {reason}")
                # 继续执行后续逻辑
            else:
                reason = f"❄️ [环境熔断] 市场情绪冰点({market_sentiment_score})，禁止开仓，防守为主"
                logger.warning(f"{stock_code} {reason}")
                return {
                    "signal": "WAIT", 
                    "score": 0, 
                    "reason": reason, 
                    "risk": "HIGH",
                    "market_sentiment_score": market_sentiment_score,
                    "market_status": market_status
                }
        
        # 退潮减权：市场退潮期，所有 BUY 信号的 AI 分数权重 x 0.5
        if market_status == "退潮":
            reason = f"🌊 [退潮期] 市场正在退潮，这种票可能是补涨或诱多，评分降级"
            logger.info(f"{stock_code} {reason}")
            # 继续执行后续逻辑，但会在最终评分时乘以 0.5
        
        # =========================================================
        # 0.5 [V16.3] 内部人防御盾 (Insider Shield) - 防止被内部人收割
        # =========================================================
        try:
            from logic.iron_rule_monitor import IronRuleMonitor
            
            iron_monitor = IronRuleMonitor()
            insider_risk = iron_monitor.check_insider_selling(stock_code, days=90)
            
            # 如果存在内部人减持风险，强制一票否决
            if insider_risk['has_risk']:
                reason = f"🚫 [内部人熔断] {insider_risk['reason']}，拒绝接盘"
                logger.warning(f"{stock_code} {reason}")
                return {
                    "signal": "WAIT", 
                    "score": 0, 
                    "reason": reason, 
                    "risk": "HIGH",
                    "insider_risk": insider_risk,
                    "market_sentiment_score": market_sentiment_score,
                    "market_status": market_status
                }
        except Exception as e:
            logger.warning(f"⚠️ [内部人检查失败] {stock_code} {e}")
            # 检查失败不影响其他逻辑，继续执行
        
        # =========================================================
        # 0.6 [V16.3] 生态看门人 (Ecological Watchdog) - 识别"德不配位"的流动性异常
        # =========================================================
        try:
            from logic.iron_rule_monitor import IronRuleMonitor
            
            iron_monitor = IronRuleMonitor()
            
            # 从真实数据接口获取实时数据（避免硬编码）
            real_time_data_full = iron_monitor.data_manager.get_realtime_data(stock_code)
            
            # 构建实时数据字典（使用真实数据）
            real_time_data = {
                'turnover': real_time_data_full.get('turnover_rate', 0) if real_time_data_full else 0,  # 真实换手率（%）
                'pct_chg': real_time_data_full.get('change_percent', current_pct_change) if real_time_data_full else current_pct_change,  # 真实涨幅（%）
                'amount': real_time_data_full.get('volume', 0) * real_time_data_full.get('price', 0) if real_time_data_full else 0,  # 真实成交额（估算）
                'volume': real_time_data_full.get('volume', 0) if real_time_data_full else 0,  # 真实成交量
                'price': real_time_data_full.get('price', 0) if real_time_data_full else 0  # 真实价格
            }
            
            # 检查价值扭曲和生态异常
            eco_risk = iron_monitor.check_value_distortion(stock_code, real_time_data)
            
            # 根据风险等级进行处理
            if eco_risk['risk_level'] == 'DANGER':
                # 强制一票否决
                reason = f"🔥 [生态熔断] {eco_risk['reason']}"
                logger.warning(f"{stock_code} {reason}")
                return {
                    "signal": "WAIT", 
                    "score": 0, 
                    "reason": reason, 
                    "risk": "HIGH",
                    "eco_risk": eco_risk,
                    "market_sentiment_score": market_sentiment_score,
                    "market_status": market_status
                }
            elif eco_risk['risk_level'] == 'WARNING':
                # 降权处理
                ai_score *= 0.5
                reason = f"🌪️ [生态降权] {eco_risk['reason']}，AI 评分降级"
                logger.info(f"{stock_code} {reason}")
                # 继续执行后续逻辑，但 AI 分数已经降级
        except Exception as e:
            logger.warning(f"⚠️ [生态看门人检查失败] {stock_code} {e}")
            # 检查失败不影响其他逻辑，继续执行
        
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
            
            # 检查是否已经有环境熔断豁免信息
            if "环境熔断-豁免" in reason:
                # 保留环境熔断豁免信息
                reason = f"🚀 [涨停豁免] {reason}，强势封板({current_pct_change}%)"
            else:
                reason = f"🚀 [涨停豁免] 强势封板({current_pct_change}%)，无视背离与陷阱"
            
            logger.info(f"{stock_code} {reason}")
            return {
                "signal": "BUY", 
                "score": min(final_score, 100), 
                "reason": reason, 
                "risk": risk_level,
                "market_sentiment_score": market_sentiment_score,
                "market_status": market_status
            }

        # =========================================================
        # 2. [V13.1] 事实熔断 (Fact Veto) - 物理定律
        # =========================================================
        # 资金大逃亡
        if capital_flow < self.CAPITAL_VETO_THRESHOLD:
            reason = f"🚨 [资金熔断] 主力巨额流出 {-capital_flow/10000:.0f}万"
            logger.warning(f"{stock_code} {reason}")
            return {
                "signal": "SELL", 
                "score": 0, 
                "reason": reason, 
                "risk": "HIGH",
                "market_sentiment_score": market_sentiment_score,
                "market_status": market_status
            }
        
        # 小盘股失血 (流出超流通盘1%)
        if circulating_market_cap and circulating_market_cap > 0:
            if (capital_flow / circulating_market_cap) < -0.01:
                reason = f"🩸 [失血熔断] 流出占比过大 ({-capital_flow/10000:.0f}万)"
                return {
                    "signal": "SELL", 
                    "score": 0, 
                    "reason": reason, 
                    "risk": "HIGH",
                    "market_sentiment_score": market_sentiment_score,
                    "market_status": market_status
                }

        # 趋势破位
        if trend == 'DOWN':
            return {
                "signal": "WAIT", 
                "score": 0, 
                "reason": "📉 [趋势熔断] 空头排列", 
                "risk": "HIGH",
                "market_sentiment_score": market_sentiment_score,
                "market_status": market_status
            }

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
                return {
                    "signal": "WAIT", 
                    "score": 10.0, 
                    "reason": reason, 
                    "risk": "HIGH",
                    "market_sentiment_score": market_sentiment_score,
                    "market_status": market_status
                }
            
            # 场景 B: 加速观察区（灰色死区） - 豪华榜 + 高开加速 (+3%~+6%)
            elif 3.0 < open_pct_change <= 6.0:
                lhb_modifier = 0.9 # 不加分，也不扣分，但标记为观察区
                lhb_msg = f"⚠️ [观察区] 豪华榜+高开加速({open_pct_change}%)，需换手确认，RISK_WARNING"
                risk_level = "HIGH"  # 标记为高风险
            
            # 场景 C: 弱转强 (Weak-to-Strong) - 豪华榜 + 平开/微红
            elif -2.0 <= open_pct_change <= 3.0:
                lhb_modifier = 1.3 # 给予 30% 溢价
                lhb_msg = f"🚀 [弱转强] 豪华榜+平开({open_pct_change}%)，主力承接有力"
                
            # 场景 D: 不及预期 - 豪华榜 + 低开
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
        
        # =========================================================
        # 5. [V16] 环境调整 (Market Adjustment)
        # =========================================================
        
        # 退潮减权：市场退潮期，所有 BUY 信号的 AI 分数权重 x 0.5
        if market_status == "退潮":
            final_score = final_score * 0.5
            if not reason.startswith("🌊"):
                reason = f"🌊 [退潮期] {reason}"
        
        # 共振加强：市场情绪高昂 + 股票趋势向上 → 最终评分 +10分
        if market_sentiment_score > 60 and trend == 'UP':
            final_score = final_score + 10
            if not reason.startswith("🌊"):
                reason = f"🌊 [共振加强] 市场情绪高昂({market_sentiment_score}) + 趋势向上，顺势而为"
        
        # =========================================================
        # 6. 最终门槛
        # =========================================================
        if final_score >= 80:
            signal = "BUY"
        else:
            signal = "WAIT"
        
        # =========================================================
        # 7. [V17] 时间策略 (Time-Lord) - 分时段策略
        # =========================================================
        try:
            from logic.time_strategy_manager import get_time_strategy_manager
            
            time_manager = get_time_strategy_manager()
            filtered_signal, time_reason = time_manager.should_filter_signal(signal)
            
            if time_reason:
                # 时间策略过滤了信号
                reason = f"{reason} | {time_reason}"
                logger.info(f"{stock_code} {time_reason}")
                signal = filtered_signal
                
                # 如果被过滤为 WAIT，将评分设为 0
                if signal == "WAIT":
                    final_score = 0
        except Exception as e:
            logger.warning(f"⚠️ [时间策略检查失败] {stock_code} {e}")

        return {
            "signal": signal, 
            "score": min(final_score, 100), 
            "reason": reason, 
            "risk": risk_level,
            "market_sentiment_score": market_sentiment_score,
            "market_status": market_status
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
        V14.4 新增：获取昨日龙虎榜数据（修复版）
        
        使用 stock_lhb_stock_detail_date_em 和 stock_lhb_stock_detail_em 接口
        
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
            
            # 获取昨天的日期（修复周一效应）
            now = datetime.now()
            # 周一(0)取上周五(3天前)，周日(6)取上周五(2天前)，其他取昨日(1天前)
            days_back = 3 if now.weekday() == 0 else (2 if now.weekday() == 6 else 1)
            target_date = now - timedelta(days=days_back)
            date_str = target_date.strftime("%Y%m%d")  # 格式：20260116
            
            # 获取龙虎榜数据（修复：使用正确的接口）
            try:
                # 步骤1：获取该股票有龙虎榜数据的日期列表
                date_list_df = ak.stock_lhb_stock_detail_date_em(symbol=stock_code)
                
                if date_list_df is None or date_list_df.empty:
                    logger.debug(f"{stock_code} 无龙虎榜记录")
                    return 0, 0
                
                logger.info(f"找到 {stock_code} 的龙虎榜记录，共 {len(date_list_df)} 天")
                
                # 步骤2：查找昨天的日期是否在列表中
                # 修复：使用正确的列名 '交易日'
                yesterday_records = date_list_df[date_list_df['交易日'] == date_str]
                
                if yesterday_records.empty:
                    logger.debug(f"{stock_code} 在 {date_str} 无龙虎榜记录")
                    return 0, 0
                
                # 步骤3：获取昨天的龙虎榜详情
                # 尝试买入和卖出两个方向
                net_buy = 0
                
                for flag in ['买入', '卖出']:
                    try:
                        detail_df = ak.stock_lhb_stock_detail_em(
                            symbol=stock_code,
                            date=date_str,
                            flag=flag
                        )
                        
                        if detail_df is not None and not detail_df.empty:
                            # 计算净买入额
                            if '净买入额' in detail_df.columns:
                                flag_net_buy = detail_df['净买入额'].sum()
                                if flag == '卖出':
                                    flag_net_buy = -flag_net_buy  # 卖出为负
                                net_buy += flag_net_buy
                                logger.info(f"{stock_code} {date_str} {flag}净买入: {flag_net_buy/10000:.2f}万元")
                    except Exception as e:
                        logger.warning(f"获取 {stock_code} {date_str} {flag}详情失败: {e}")
                
                # AkShare 返回的单位通常是万元，需要转换为元
                net_buy = net_buy * 10000  # 万元 → 元
                
                logger.info(f"{stock_code} {date_str} 总净买入: {net_buy/10000:.2f}万元")
                
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
            import traceback
            traceback.print_exc()
            return 0, 0


# 全局实例
_signal_generator_v14_4 = None

def get_signal_generator_v14_4():
    global _signal_generator_v14_4
    if _signal_generator_v14_4 is None:
        _signal_generator_v14_4 = SignalGenerator()
    return _signal_generator_v14_4