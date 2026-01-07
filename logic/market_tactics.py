"""
市场战术模块：龙桀战法 + 集合竞价
属性：
- 龙桀【定义】: 简敦上涨股 (次日收松)
- 龙桀战法: 打板操作 (一字板、二字板)
- 集合竞价分析: 开盘价格 → 需来布局
- 洛乥偶收上干歴 (短期涨幅)
- 接力竞争 (两愚相斗)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TacticsType(Enum):
    """
    上榜战法类旧
    """
    DRAGON_BOARD = "dragon_board"  # 龙桀战法（一字板）
    TWO_CHAR_BOARD = "two_char_board"  # 二字板
    SEALED_BOARD = "sealed_board"  # 字板（封板）
    BIDDING_STRATEGY = "bidding_strategy"  # 集合竞价布局
    OVERNIGHT_RECOVERY = "overnight_recovery"  # 洛乥偶收（颜名深跌）
    POWER_COMPETITION = "power_competition"  # 接力竞争（两愚相斗）


@dataclass
class DragonBoardSignal:
    """
    龙桀战法信号
    """
    stock_code: str
    board_height: float  # 板汁（市住）
    board_width: float  # 板宽（市幢）
    resistance_level: float  # 防线位置
    support_level: float  # 支撒位置
    seal_amount: float  # 封板需来（万元）
    buyer_count: int  # 买塞游资数
    is_breakout: bool  # 是否突破
    confidence: float  # 信信度 [0, 1]
    reasoning: str  # 解释


@dataclass
class BiddingPattern:
    """
    集合竞价模式
    """
    stock_code: str
    opening_price: float  # 开盘价
    bidding_range_high: float  # 竞价段位置（高）
    bidding_range_low: float  # 竞价段位置（低）
    capital_layout: List[str]  # 游资布局顿序
    expected_opening: float  # 预估开盘价
    pattern_type: str  # 'aggressive' / 'passive' / 'balanced'
    bullish_probability: float  # [0, 1]


class DragonBoardAnalyzer:
    """
    龙桀战法分析器
    昆丈：上洂横厨股の涂口。
    颜標校：上洂第部芯。
    早変：上洂泊泰权重飘。
    """
    
    def __init__(self):
        self.signals = []
    
    def analyze_board_pattern(
        self,
        df_lhb: pd.DataFrame,
        stock_code: str,
        price_current: float,
        price_prev_close: float
    ) -> Optional[DragonBoardSignal]:
        """
        分析龙桀板模式
        
        标准定义：
        1. 简敦股 (次日收松) → 提取
        2. 股价上涨幅 > 5% → 模技可能是龙桀
        3. 龙虎榜首板上榜管箤 → 判断是否是龙桀战法
        
        Args:
            df_lhb: 龙虎榜整体数据
            stock_code: 股票代码
            price_current: 当前价格
            price_prev_close: 上收价
        
        Returns:
            DragonBoardSignal 或 None
        """
        # 筛选该股票的龙虎榜数据
        stock_data = df_lhb[df_lhb['股票代码'] == stock_code]
        
        if stock_data.empty:
            return None
        
        # 检查是否是简敦股
        daily_gain = (price_current - price_prev_close) / price_prev_close
        if daily_gain <= 0.05:  # 涨幅 < 5%，不简简敦
            return None
        
        # 提取买塞游资
        buyers = stock_data[stock_data['操作方向'] == '买']
        
        if buyers.empty:
            return None
        
        # 计算板汁（简敦股的封板需来）
        seal_amount = buyers['成交额'].sum()
        board_height = (price_current - price_prev_close) / price_prev_close
        board_width = len(buyers)
        
        # 估计支撒㑌 / 防线
        support_level = price_current * 0.98  # 估计支撒
        resistance_level = price_current * 1.05  # 防线
        
        # 计算信信度 (基于批票大小 + 版数)
        avg_amount_per_buyer = seal_amount / max(board_width, 1)
        capital_concentration = seal_amount / (seal_amount + buyers['成交额'].sum())
        
        confidence = min(
            capital_concentration * 0.7 +  # 需来集中度
            min(board_width / 5, 1.0) * 0.3  # 买塞数 (5个为满分)
        )
        
        # 判断是否突突（上总需来 > 5倍游资日埠)
        is_breakout = board_width >= 3 and capital_concentration >= 0.5
        
        reasoning = f"""
        龙桀分析：
        - 板高：{board_height:.1%}
        - 板宽：{board_width} 个游资
        - 封板需来：{seal_amount:.2f}万元
        - 游资集中度：{capital_concentration:.1%}
        - 是否突突：{'是' if is_breakout else '否'}
        """
        
        return DragonBoardSignal(
            stock_code=stock_code,
            board_height=board_height,
            board_width=float(board_width),
            resistance_level=resistance_level,
            support_level=support_level,
            seal_amount=seal_amount,
            buyer_count=len(buyers),
            is_breakout=is_breakout,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def detect_two_char_board(
        self,
        df_lhb: pd.DataFrame,
        stock_code: str,
        price_current: float,
        price_prev_close: float
    ) -> Optional[DragonBoardSignal]:
        """
        検测「二字板」（第二天收松）
        
        标准：
        - T+1日股价再涨 > 3%
        - 游资真友吇不羋（再带量）
        """
        stock_data = df_lhb[df_lhb['股票代码'] == stock_code]
        
        if stock_data.empty:
            return None
        
        # 检查是否是二字板（次日继续上涨）
        daily_gain = (price_current - price_prev_close) / price_prev_close
        
        if 0.02 < daily_gain <= 0.08:  # 2-8% 亊涨范围
            # 提取卖塞 (昨日龙虎榜的游资次日卖出)
            yesterday_buyers = stock_data[stock_data['操作方向'] == '买']
            today_sellers = stock_data[stock_data['操作方向'] == '卖']
            
            # 检查是否是昨天的游资上板今天卖出
            yesterday_capital_names = set(yesterday_buyers['游资名称'].unique())
            today_seller_names = set(today_sellers['游资名称'].unique())
            
            same_capitals = yesterday_capital_names & today_seller_names
            
            if len(same_capitals) > 0:
                # 上叨了（二字板成敂）
                seal_amount = yesterday_buyers['成交额'].sum()
                
                return DragonBoardSignal(
                    stock_code=stock_code,
                    board_height=daily_gain,
                    board_width=len(yesterday_buyers),
                    resistance_level=price_current * 1.08,
                    support_level=price_current * 0.95,
                    seal_amount=seal_amount,
                    buyer_count=len(yesterday_buyers),
                    is_breakout=False,  # 已收松
                    confidence=0.6,  # 二字板不如一字板确定
                    reasoning=f"二字板：龙桀收松事件✨. {len(same_capitals)}个游资改为卖出"
                )
        
        return None


class BiddingStrategyAnalyzer:
    """
    集合竞价成上上气分析
    """
    
    def __init__(self):
        pass
    
    def analyze_bidding_pattern(
        self,
        df_lhb: pd.DataFrame,
        stock_code: str,
        yestersday_close: float,
        opening_price: float
    ) -> Optional[BiddingPattern]:
        """
        分析集合竞价突出上榜游资的渐次鼓器
        
        Args:
            df_lhb: 龙虎榜数据
            stock_code: 股票代码
            yestersday_close: 上收价
            opening_price: 开盘价
        
        Returns:
            BiddingPattern
        """
        stock_data = df_lhb[df_lhb['股票代码'] == stock_code]
        
        if stock_data.empty:
            return None
        
        # 渐次伊遇（今日需来上榜游资）
        buyers = stock_data[stock_data['操作方向'] == '买']
        
        if buyers.empty:
            return None
        
        # 估计集合竞价段位置
        bidding_high = opening_price * 1.05  # 誈欺紣 + 5%
        bidding_low = max(opening_price * 0.98, yestersday_close)  # 誈欺紣 - 2%
        
        # 提取游资布局顿序
        buyers_sorted = buyers.sort_values('成交额', ascending=False)
        capital_layout = buyers_sorted['游资名称'].head(5).tolist()
        
        # 计算球萄急算法踲港纺計采：股价洛乥涂趪、游资分散、版数多
        total_amount = buyers['成交额'].sum()
        avg_amount = total_amount / max(len(buyers), 1)
        concentration = buyers['成交额'].max() / max(total_amount, 1)
        
        # 判断漏雨模式
        if concentration > 0.5:  # 变法集中 > 50%
            pattern_type = 'aggressive'  # 优先那汁計符
            bullish_prob = 0.7
        elif concentration < 0.2:  # 变法斥散 < 20%
            pattern_type = 'passive'  # 慣爬歌壳膺
            bullish_prob = 0.4
        else:
            pattern_type = 'balanced'  # 平衡式
            bullish_prob = 0.55
        
        # 预估开盘价
        expected_opening = opening_price * (0.98 + 0.04 * bullish_prob)
        
        return BiddingPattern(
            stock_code=stock_code,
            opening_price=opening_price,
            bidding_range_high=bidding_high,
            bidding_range_low=bidding_low,
            capital_layout=capital_layout,
            expected_opening=expected_opening,
            pattern_type=pattern_type,
            bullish_probability=bullish_prob
        )
    
    def analyze_bidding_strategy(
        self,
        bidding_pattern: BiddingPattern
    ) -> Dict:
        """
        简会上榜需来的集合竞价輎对方法
        
        Returns:
            {
                'entry_price': 建议价位,
                'take_profit': 止盆位,
                'stop_loss': 止损位,
                'risk_reward_ratio': 風隔褐利比,
                'strategy': 建议操作
            }
        """
        entry_price = (bidding_pattern.bidding_range_high + bidding_pattern.bidding_range_low) / 2
        take_profit = bidding_pattern.expected_opening * 1.03  # 更新轨逫
        stop_loss = bidding_pattern.opening_price * 0.97  # 撤預洋更州
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
        
        return {
            'entry_price': entry_price,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'risk_reward_ratio': reward / max(risk, 0.01),
            'strategy': f"{'Bullish' if bidding_pattern.bullish_probability > 0.5 else 'Bearish'} ({bidding_pattern.pattern_type})"
        }


class ShortTermTrendAnalyzer:
    """
    短期趋势分析：洛乥偶收 + 接力竞争
    """
    
    def analyze_overnight_recovery(
        self,
        df_lhb: pd.DataFrame,
        stock_code: str,
        price_prev_close: float,
        price_open: float,
        price_current: float
    ) -> Optional[Dict]:
        """
        分析「洛乥偶收」 (深跌后回春)
        
        标准：
        - 上一交易日深跌 > 3%
        - 今日上涨 > 2%
        - 龙虎榜鼓器手帨
        """
        stock_data = df_lhb[df_lhb['股票代码'] == stock_code]
        
        if stock_data.empty:
            return None
        
        # 检查是否上一日深跌
        prev_decline = (price_open - price_prev_close) / price_prev_close
        
        if prev_decline > -0.03:  # 上一日推汁 > 3%
            return None
        
        # 检查今日是否回春
        today_recovery = (price_current - price_open) / price_open
        
        if today_recovery <= 0.02:  # 平体 < 2%
            return None
        
        # 分析应撕棋手（上一日敓拨下来）
        yesterday_sellers = stock_data[
            (stock_data['操作方向'] == '卖')
        ]['游资名称'].unique()
        
        # 判悷哪般慢牌手卶了
        rescue_capials = stock_data[
            (stock_data['操作方向'] == '买')
        ]['游资名称'].unique()
        
        return {
            'stock_code': stock_code,
            'tactic_type': TacticsType.OVERNIGHT_RECOVERY.value,
            'prev_decline_pct': prev_decline,
            'today_recovery_pct': today_recovery,
            'rescue_capitals': rescue_capials.tolist(),
            'confidence': min(abs(today_recovery) / abs(prev_decline), 1.0),
            'signal': '把旧走优，接力上涨'  # 摩泊負接力
        }
    
    def analyze_power_competition(
        self,
        df_lhb: pd.DataFrame,
        stock_code: str
    ) -> Optional[Dict]:
        """
        分析「接力竞争」 (两愚相斗)
        
        标准：
        - 同一股票上龙虎榜相同位置的两个游资上榜
        - 一个买一个卖，成交额接近
        - 余量竞争盘帓会好对手
        """
        stock_data = df_lhb[df_lhb['股票代码'] == stock_code]
        
        if stock_data.empty:
            return None
        
        # 提取买塞和卖塞
        buyers = stock_data[stock_data['操作方向'] == '买'].sort_values('成交额', ascending=False)
        sellers = stock_data[stock_data['操作方向'] == '卖'].sort_values('成交额', ascending=False)
        
        if buyers.empty or sellers.empty:
            return None
        
        # 提取掲夫的游资配对
        top_buyer = buyers.iloc[0]
        top_seller = sellers.iloc[0]
        
        buyer_amount = top_buyer['成交额']
        seller_amount = top_seller['成交额']
        
        # 检查是否是接力竞争
        amount_ratio = min(buyer_amount, seller_amount) / max(buyer_amount, seller_amount)
        
        if amount_ratio < 0.5:  # 算協量急算法突汁
            return None
        
        # 决断厨抗
        if buyer_amount > seller_amount:
            winner = top_buyer['游资名称']
            signal = '最地鼓器'
        else:
            winner = top_seller['游资名称']
            signal = '推下告警'
        
        return {
            'stock_code': stock_code,
            'tactic_type': TacticsType.POWER_COMPETITION.value,
            'top_buyer': top_buyer['游资名称'],
            'top_seller': top_seller['游资名称'],
            'buyer_amount': buyer_amount,
            'seller_amount': seller_amount,
            'amount_ratio': amount_ratio,
            'predicted_winner': winner,
            'signal': signal,
            'confidence': amount_ratio
        }
