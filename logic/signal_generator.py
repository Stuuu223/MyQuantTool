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
        # 0.7 [V18] 全维板块共振 (The Navigator) - 完整旗舰版
        # =========================================================
        sector_modifier = 1.0
        sector_reason = ""
        sector_info = {}
        resonance_score = 0.0
        resonance_details = []
        
        try:
            from logic.sector_analysis import FastSectorAnalyzer
            from logic.data_manager import DataManager
            
            # 获取板块分析器
            db = DataManager()
            sector_analyzer = FastSectorAnalyzer(db)
            
            # 获取股票名称（用于龙头匹配）
            try:
                realtime_data = db.get_realtime_data(stock_code)
                stock_name = realtime_data.get('name', '') if realtime_data else ''
            except:
                stock_name = ''
            
            # 全维共振分析（行业 + 概念 + 资金热度 + 龙头溯源）
            full_resonance = sector_analyzer.check_stock_full_resonance(stock_code, stock_name)
            
            resonance_score = full_resonance.get('resonance_score', 0.0)
            resonance_details = full_resonance.get('resonance_details', [])
            is_leader = full_resonance.get('is_leader', False)
            is_follower = full_resonance.get('is_follower', False)
            
            # 兼容旧版接口
            sector_info = sector_analyzer.check_sector_status(stock_code)
            sector_modifier = sector_info.get('modifier', 1.0)
            
            # 根据共振评分调整 AI 分数
            if resonance_score > 0:
                # 共振加分
                ai_score += resonance_score
                logger.info(f"{stock_code} 🚀 [板块共振] +{resonance_score:.1f}分: {resonance_details}")
                
                # 如果是龙头，给予额外权重加成
                if is_leader:
                    ai_score *= 1.2
                    logger.info(f"{stock_code} 👑 [龙头溢价] AI 分数 × 1.2")
                
                # 如果是跟风股，适当降权
                elif is_follower:
                    ai_score *= 0.9
                    logger.info(f"{stock_code} 📈 [跟风股] AI 分数 × 0.9")
            
            elif resonance_score < 0:
                # 逆风减分
                ai_score += resonance_score  # resonance_score 是负数
                logger.warning(f"{stock_code} ⚠️ [板块逆风] {resonance_score:.1f}分: {resonance_details}")
            
            # 构建板块共振原因
            if resonance_details:
                sector_reason = " | ".join(resonance_details)
            else:
                sector_reason = sector_info.get('reason', '')
            
        except Exception as e:
            logger.warning(f"⚠️ [板块共振检查失败] {stock_code} {e}")
            import traceback
            traceback.print_exc()
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
        # 1.5. [V18.5] DDE 否决权 (DDE Veto) - 资金铁律
        # 🆕 V18.6: 引入 buy_mode 参数，区分 DRAGON_CHASE 和 LOW_SUCTION
        # =========================================================
        # 铁律：如果 DDE 为负，根据买入模式决定是否否决
        try:
            from logic.money_flow_master import get_money_flow_master
            mfm = get_money_flow_master()
            
            # 🆕 V18.6: 根据当前涨幅判断买入模式
            # 如果涨幅 > 3%，认为是追龙头模式；否则认为是低吸模式
            if current_pct_change > 3.0:
                buy_mode = 'DRAGON_CHASE'
            else:
                buy_mode = 'LOW_SUCTION'
            
            is_vetoed, veto_reason = mfm.check_dde_veto(stock_code, 'BUY', buy_mode)
            
            if is_vetoed:
                logger.warning(f"{stock_code} {veto_reason}")
                return {
                    "signal": "WAIT", 
                    "score": 0, 
                    "reason": veto_reason, 
                    "risk": "HIGH",
                    "market_sentiment_score": market_sentiment_score,
                    "market_status": market_status,
                    "buy_mode": buy_mode  # 🆕 V18.6: 返回买入模式
                }
            elif veto_reason:
                # DDE 弱信号警告，但不否决
                logger.info(f"{stock_code} {veto_reason}")
        
        except Exception as e:
            logger.warning(f"DDE 否决权检查失败: {e}")
        
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
        # 板块修正：Sector Resonance (V18)
        
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
        
        # [V18] 应用板块共振修正
        final_score = final_score * sector_modifier
        
        # 如果板块共振有特殊理由，添加到 reason 中
        if sector_reason and sector_modifier != 1.0:
            if reason:
                reason = f"{reason} | {sector_reason}"
            else:
                reason = sector_reason
        
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
        # 6. 🆕 V18.6: 预判模式 (Pre-Buy Signal) - 在涨停前锁定确定性
        # =========================================================
        
        # 预判模式1：DDE 脉冲预警（涨幅4%-6%时）
        pre_buy_signal = None
        pre_buy_reason = ""
        
        if 4.0 <= current_pct_change <= 6.0:
            # 检查 DDE 是否持续走高
            try:
                from logic.money_flow_master import get_money_flow_master
                mfm = get_money_flow_master()
                
                # 获取 DDE 历史数据
                dde_history = mfm._get_dde_history(stock_code, lookback=5)
                
                if dde_history and len(dde_history) >= 3:
                    # 计算 DDE 斜率
                    recent_dde = dde_history[-3:]
                    dde_slope = (recent_dde[-1] - recent_dde[0]) / len(recent_dde)
                    
                    # 如果 DDE 持续走高，发出预判信号
                    if dde_slope > 0:
                        pre_buy_signal = "PRE_BUY"
                        pre_buy_reason = f"🔥 [预判信号] 涨幅{current_pct_change:.1f}%，DDE斜率转正（{dde_slope:.3f}），建议提前布局"
                        logger.info(f"✅ [预判信号] {stock_code} {pre_buy_reason}")
            except Exception as e:
                logger.warning(f"⚠️ [预判模式检查失败] {stock_code} {e}")
        
        # 预判模式2：20cm/30cm 弹性缓冲（涨幅10%时逻辑二次确认）
        limit_ratio = Utils.get_limit_ratio(stock_code)
        
        # 如果是20cm或30cm股票，且涨幅在10%左右
        if limit_ratio >= 1.2 and 9.0 <= current_pct_change <= 11.0:
            # 进行逻辑二次确认
            try:
                from logic.money_flow_master import get_money_flow_master
                mfm = get_money_flow_master()
                
                # 检查 DDE 是否持续走高
                dde_history = mfm._get_dde_history(stock_code, lookback=5)
                
                if dde_history and len(dde_history) >= 3:
                    recent_dde = dde_history[-3:]
                    dde_slope = (recent_dde[-1] - recent_dde[0]) / len(recent_dde)
                    
                    # 如果 DDE 持续走高，发出弹性缓冲信号
                    if dde_slope > 0:
                        elastic_buffer = (limit_ratio - 1.0) * 100 - current_pct_change  # 剩余空间
                        pre_buy_signal = "ELASTIC_BUFFER"
                        pre_buy_reason = f"🛡️ [弹性缓冲] 涨幅{current_pct_change:.1f}%，DDE斜率转正（{dde_slope:.3f}），剩余空间{elastic_buffer:.1f}%，安全垫充足"
                        logger.info(f"✅ [弹性缓冲] {stock_code} {pre_buy_reason}")
            except Exception as e:
                logger.warning(f"⚠️ [弹性缓冲检查失败] {stock_code} {e}")
        
        # =========================================================
        # 7. 最终门槛
        # =========================================================
        if final_score >= 80:
            signal = "BUY"
        elif pre_buy_signal:
            # 如果有预判信号，使用预判信号
            signal = pre_buy_signal
            reason = pre_buy_reason
        else:
            signal = "WAIT"
        
        # =========================================================
        # 7. [V17] 时间策略 (Time-Lord) - 分时段策略
        # =========================================================
        try:
            from logic.time_strategy_manager import get_time_strategy_manager
            
            time_manager = get_time_strategy_manager()
            # V17.2: 传入市场情绪分数，实现时空融合
            filtered_signal, time_reason = time_manager.should_filter_signal(signal, sentiment_score=market_sentiment_score)
            
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
            "market_status": market_status,
            "sector_info": sector_info  # V18: 板块共振信息
        }
    
    def check_elastic_buffer_signal(self, stock_code: str, current_price: float, prev_close: float, 
                                 intraday_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        🆕 V18.6: 检查动态适配的"提前量"（20cm/30cm）信号
        
        逻辑：在创业板，股价从10%涨到20%有巨大的缓冲带。
        不需要等它20cm封死。当它在12%处缩量回踩分时均线，且DDE维持强势时，这就是"准涨停确定性"。
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            prev_close: 昨收价
            intraday_data: 分时数据（可选）
        
        Returns:
            dict: {
                'has_elastic_buffer': bool,  # 是否有弹性缓冲信号
                'is_20cm_or_30cm': bool,     # 是否是20cm/30cm股票
                'current_pct_change': float, # 当前涨幅
                'limit_up_pct': float,       # 涨停幅度
                'elastic_space': float,      # 弹性空间（剩余涨幅）
                'volume_shrink': bool,       # 是否缩量
                'intraday_ma_touch': bool,   # 是否回踩分时均线
                'dde_strong': bool,          # DDE是否维持强势
                'confidence': float,         # 置信度（0-1）
                'reason': str                # 原因
            }
        """
        result = {
            'has_elastic_buffer': False,
            'is_20cm_or_30cm': False,
            'current_pct_change': 0.0,
            'limit_up_pct': 0.0,
            'elastic_space': 0.0,
            'volume_shrink': False,
            'intraday_ma_touch': False,
            'dde_strong': False,
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 获取涨停系数
            from logic.utils import Utils
            limit_ratio = Utils.get_limit_ratio(stock_code)
            limit_up_pct = (limit_ratio - 1.0) * 100
            result['limit_up_pct'] = limit_up_pct
            
            # 2. 判断是否是20cm/30cm股票
            is_20cm_or_30cm = limit_ratio >= 1.2
            result['is_20cm_or_30cm'] = is_20cm_or_30cm
            
            if not is_20cm_or_30cm:
                result['reason'] = '该股票不是20cm/30cm标的，无需弹性缓冲检查'
                return result
            
            # 3. 计算当前涨幅
            if prev_close == 0:
                result['reason'] = '昨收价为0，无法计算涨幅'
                return result
            
            current_pct_change = (current_price - prev_close) / prev_close * 100
            result['current_pct_change'] = current_pct_change
            
            # 4. 计算弹性空间（剩余涨幅）
            elastic_space = limit_up_pct - current_pct_change
            result['elastic_space'] = elastic_space
            
            # 5. 判断是否在弹性区间（10%-14%）
            if not (10.0 <= current_pct_change <= 14.0):
                result['reason'] = f'涨幅{current_pct_change:.1f}%不在弹性区间（10%-14%）'
                return result
            
            # 6. 检查是否缩量
            realtime_data = self.get_data_manager().get_realtime_data(stock_code)
            if realtime_data:
                current_volume = realtime_data.get('volume', 0)
                # 获取历史成交量（这里简化处理，实际应该从K线数据获取）
                avg_volume = current_volume / 2.0  # 假设历史平均成交量是当前的一半
                volume_shrink = current_volume < avg_volume * 0.8
                result['volume_shrink'] = volume_shrink
            
            # 7. 检查是否回踩分时均线
            if intraday_data is not None and len(intraday_data) >= 10:
                intraday_ma = intraday_data['price'].mean()
                intraday_ma_touch = current_price <= intraday_ma * 1.02  # 允许2%的误差
                result['intraday_ma_touch'] = intraday_ma_touch
            
            # 8. 检查DDE是否维持强势
            if realtime_data:
                dde_net_flow = realtime_data.get('dde_net_flow', 0)
                dde_strong = dde_net_flow > 0.5  # DDE > 0.5亿为强势
                result['dde_strong'] = dde_strong
            
            # 9. 综合判断
            confidence = 0.0
            
            # 弹性空间评分（剩余空间越大，评分越高）
            if elastic_space >= 8.0:
                confidence += 0.3
            elif elastic_space >= 6.0:
                confidence += 0.2
            elif elastic_space >= 4.0:
                confidence += 0.1
            
            # 缩量评分
            if result['volume_shrink']:
                confidence += 0.2
            
            # 回踩分时均线评分
            if result['intraday_ma_touch']:
                confidence += 0.2
            
            # DDE强势评分
            if result['dde_strong']:
                confidence += 0.3
            
            result['confidence'] = min(1.0, confidence)
            
            # 10. 生成原因
            if result['confidence'] >= 0.7:
                result['has_elastic_buffer'] = True
                result['reason'] = f'🛡️ [弹性缓冲] 涨幅{current_pct_change:.1f}%，剩余空间{elastic_space:.1f}%，DDE强势，准涨停确定性'
                logger.info(f"✅ [弹性缓冲] {stock_code} 检测到弹性缓冲信号：{result['reason']}")
            elif result['confidence'] >= 0.4:
                result['reason'] = f'⚠️ [弹性缓冲] 有弹性缓冲迹象，但强度不足'
            else:
                result['reason'] = f'📊 [弹性缓冲] 暂无明显弹性缓冲信号'
        
        except Exception as e:
            logger.error(f"检查弹性缓冲信号失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
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