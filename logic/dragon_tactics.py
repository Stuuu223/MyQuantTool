"""
龙头战法（Dragon Tactics）- A股顶级游资掠食者决策系统
专门用于捕捉市场最强龙头的加速段
核心思想：龙头多一条命、强者恒强、分歧是买点
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DragonTactics:
    """
    龙头战法分析器
    
    核心功能：
    1. 龙头辨识度分析（板块内唯一、最早、有伴）
    2. 资金微观结构分析（竞价爆量、弱转强、分时承接）
    3. 20cm/10cm 特判
    4. 决策矩阵输出
    """
    
    def __init__(self):
        """初始化龙头战法分析器"""
        pass
    
    def analyze_call_auction(self, 
                           current_open_volume: float,
                           prev_day_total_volume: float,
                           current_open_amount: float = None,
                           prev_day_total_amount: float = None) -> Dict[str, Any]:
        """
        分析竞价数据
        
        Args:
            current_open_volume: 当前开盘成交量
            prev_day_total_volume: 昨天全天成交量
            current_open_amount: 当前开盘成交额（可选）
            prev_day_total_amount: 昨天全天成交额（可选）
            
        Returns:
            竞价分析结果
        """
        results = {}
        
        # 计算竞价量比
        if prev_day_total_volume > 0:
            # 方法1：9:25成交量 / 昨天全天成交量
            call_auction_ratio = current_open_volume / prev_day_total_volume
            results['call_auction_ratio'] = call_auction_ratio
            
            # 方法2：9:25成交量 / (昨天成交量/240*5)  假设9:25是5分钟
            normalized_ratio = current_open_volume / (prev_day_total_volume / 240 * 5)
            results['normalized_call_auction_ratio'] = normalized_ratio
        
        # 计算竞价额比
        if current_open_amount and prev_day_total_amount and prev_day_total_amount > 0:
            call_auction_amount_ratio = current_open_amount / prev_day_total_amount
            results['call_auction_amount_ratio'] = call_auction_amount_ratio
        
        # 判断竞价强度（修正：降低阈值，更符合现实情况）
        if 'call_auction_ratio' in results:
            ratio = results['call_auction_ratio']
            if ratio > 0.05:  # 5% 以上：爆量高开
                results['auction_intensity'] = '极强'
                results['auction_score'] = 100
            elif ratio > 0.03:  # 3% 以上：强抢筹
                results['auction_intensity'] = '强'
                results['auction_score'] = 80
            elif ratio > 0.02:  # 2% 以上：中等抢筹
                results['auction_intensity'] = '中等'
                results['auction_score'] = 60
            elif ratio > 0.01:  # 1% 以上：弱抢筹
                results['auction_intensity'] = '弱'
                results['auction_score'] = 40
            else:
                results['auction_intensity'] = '极弱'
                results['auction_score'] = 20
        
        return results
    
    def analyze_sector_rank(self,
                          symbol: str,
                          sector: str,
                          current_change: float,
                          sector_stocks_data: Optional[pd.DataFrame] = None,
                          limit_up_count: int = 0) -> Dict[str, Any]:
        """
        分析板块地位
        
        Args:
            symbol: 股票代码
            sector: 板块名称
            current_change: 当前涨跌幅
            sector_stocks_data: 板块内所有股票数据（可选）
            limit_up_count: 板块内涨停数量
            
        Returns:
            板块地位分析结果
        """
        results = {
            'symbol': symbol,
            'sector': sector,
            'current_change': current_change
        }
        
        # 如果有板块数据，计算排名
        if sector_stocks_data is not None and not sector_stocks_data.empty:
            # 按涨跌幅排序
            sector_stocks_data = sector_stocks_data.sort_values('change_percent', ascending=False)
            
            # 计算排名
            rank = (sector_stocks_data['symbol'] == symbol).idxmax() if 'symbol' in sector_stocks_data.columns else 0
            total_stocks = len(sector_stocks_data)
            
            results['rank_in_sector'] = rank + 1
            results['total_stocks_in_sector'] = total_stocks
            results['rank_percentile'] = (total_stocks - rank) / total_stocks * 100
            
            # 判断地位
            if rank == 0:
                results['role'] = '龙头（龙一）'
                results['role_score'] = 100
            elif rank <= 2:
                results['role'] = '前排（龙二/龙三）'
                results['role_score'] = 80
            elif rank <= 5:
                results['role'] = '中军'
                results['role_score'] = 60
            elif rank <= 10:
                results['role'] = '跟风'
                results['role_score'] = 40
            else:
                results['role'] = '杂毛'
                results['role_score'] = 20
        else:
            # 没有板块数据，根据涨跌幅判断
            if current_change >= 9.9:
                results['role'] = '涨停（疑似龙头）'
                results['role_score'] = 80
            elif current_change >= 7.0:
                results['role'] = '前排'
                results['role_score'] = 60
            elif current_change >= 3.0:
                results['role'] = '中军'
                results['role_score'] = 40
            else:
                results['role'] = '跟风'
                results['role_score'] = 20
        
        # 板块热度
        results['limit_up_count'] = limit_up_count
        if limit_up_count >= 5:
            results['sector_heat'] = '极热'
            results['sector_heat_score'] = 100
        elif limit_up_count >= 3:
            results['sector_heat'] = '热'
            results['sector_heat_score'] = 80
        elif limit_up_count >= 1:
            results['sector_heat'] = '温'
            results['sector_heat_score'] = 60
        else:
            results['sector_heat'] = '冷'
            results['sector_heat_score'] = 40
        
        return results
    
    def check_code_prefix(self, symbol: str, name: str = '') -> Dict[str, Any]:
        """
        检查股票代码前缀，判断赛道

        Args:
            symbol: 股票代码
            name: 股票名称（可选，用于检测 ST 标志）

        Returns:
            代码前缀分析结果
        """
        results = {}

        # 检查是否为 ST（检查代码和名称）
        if 'ST' in symbol or '*ST' in symbol or 'ST' in name or '*ST' in name:
            results['is_st'] = True
            results['banned'] = True
            results['banned_reason'] = 'ST/退市风险股，禁止交易'
            return results

        results['is_st'] = False
        results['banned'] = False

        # 检查前缀
        if symbol.startswith('300') or symbol.startswith('688'):
            results['prefix_type'] = '20cm战队'
            results['limit_type'] = '创业板/科创板'
            results['max_limit'] = 20
            results['volatility'] = '极高'
        elif symbol.startswith('60') or symbol.startswith('00'):
            results['prefix_type'] = '10cm战队'
            results['limit_type'] = '主板'
            results['max_limit'] = 10
            results['volatility'] = '中等'
        else:
            results['prefix_type'] = '未知'
            results['limit_type'] = '未知'
            results['max_limit'] = 10
            results['volatility'] = '未知'

        return results
    
    def analyze_weak_to_strong(self,
                             df: pd.DataFrame,
                             lookback: int = 5) -> Dict[str, Any]:
        """
        分析弱转强形态
        
        Args:
            df: K线数据
            lookback: 回看天数
            
        Returns:
            弱转强分析结果
        """
        if len(df) < 2:
            return {'weak_to_strong': False, 'score': 0}
        
        results = {}
        
        # 获取昨天和今天的数据
        yesterday = df.iloc[-2]
        today = df.iloc[-1]
        
        # 昨天是否炸板或大阴线
        yesterday_change = (yesterday['close'] - yesterday['open']) / yesterday['open'] * 100
        if yesterday_change < -5:  # 昨天大跌
            results['yesterday_crash'] = True
        else:
            results['yesterday_crash'] = False
        
        # 昨天是否涨停（用于判断"强更强"）
        yesterday_is_limit_up = yesterday_change >= 9.8  # 涨停板（10cm）
        if yesterday_change >= 19.8:  # 20cm 涨停
            yesterday_is_limit_up = True
        
        # 今天是否高开
        today_open_change = (today['open'] - yesterday['close']) / yesterday['close'] * 100
        if today_open_change > 3:  # 今天高开超过3%
            results['today_high_open'] = True
        else:
            results['today_high_open'] = False
        
        # 判断弱转强
        is_weak_to_strong = False
        is_strong_to_strong = False
        
        if results.get('yesterday_crash', False) and results.get('today_high_open', False):
            results['weak_to_strong'] = True
            results['weak_to_strong_score'] = 100
            results['weak_to_strong_desc'] = '昨日大跌，今日高开，弱转强形态'
            is_weak_to_strong = True
        elif yesterday_change < 0 and today_open_change > 0:
            results['weak_to_strong'] = True
            results['weak_to_strong_score'] = 70
            results['weak_to_strong_desc'] = '昨日收阴，今日高开，有弱转强迹象'
            is_weak_to_strong = True
        elif yesterday_is_limit_up and today_open_change > 0:
            # ✅ 新增：强更强逻辑（昨天涨停 + 今天高开）
            results['weak_to_strong'] = True
            results['weak_to_strong_score'] = 90
            results['weak_to_strong_desc'] = '昨日涨停，今日高开，强更强形态（连板加速）'
            results['is_strong_to_strong'] = True
            is_strong_to_strong = True
        elif yesterday_is_limit_up:
            # 昨天涨停，今天平开或低开
            results['weak_to_strong'] = True
            results['weak_to_strong_score'] = 60
            results['weak_to_strong_desc'] = '昨日涨停，今日维持高位，连板形态'
            is_strong_to_strong = True
        else:
            results['weak_to_strong'] = False
            results['weak_to_strong_score'] = 0
            results['weak_to_strong_desc'] = '无明显弱转强或强更强'
        
        return results
    
    def analyze_intraday_support(self,
                                intraday_data: pd.DataFrame) -> Dict[str, Any]:
        """
        分析分时承接力度
        
        Args:
            intraday_data: 分时数据
            
        Returns:
            分时承接分析结果
        """
        if len(intraday_data) < 10:
            return {'intraday_support': False, 'score': 0}
        
        results = {}
        
        # 计算均线
        ma = intraday_data['price'].rolling(window=10).mean()
        
        # 判断价格是否在均线上方
        current_price = intraday_data['price'].iloc[-1]
        current_ma = ma.iloc[-1]
        
        if current_price > current_ma:
            results['above_ma'] = True
            results['above_ma_score'] = 80
        else:
            results['above_ma'] = False
            results['above_ma_score'] = 20
        
        # 判断下跌缩量、上涨放量
        volume_trend = intraday_data['volume'].diff().fillna(0)
        price_trend = intraday_data['price'].diff().fillna(0)
        
        # 下跌时缩量
        down_shrink = ((price_trend < 0) & (volume_trend < 0)).sum()
        # 上涨时放量
        up_expand = ((price_trend > 0) & (volume_trend > 0)).sum()
        
        total_changes = (price_trend != 0).sum()
        if total_changes > 0:
            support_ratio = (down_shrink + up_expand) / total_changes * 100
            results['support_ratio'] = support_ratio
            
            if support_ratio > 70:
                results['intraday_support'] = True
                results['intraday_support_score'] = 100
                results['intraday_support_desc'] = '分时承接极强'
            elif support_ratio > 50:
                results['intraday_support'] = True
                results['intraday_support_score'] = 70
                results['intraday_support_desc'] = '分时承接较强'
            else:
                results['intraday_support'] = False
                results['intraday_support_score'] = 30
                results['intraday_support_desc'] = '分时承接较弱'
        else:
            results['intraday_support'] = False
            results['intraday_support_score'] = 0
            results['intraday_support_desc'] = '数据不足'
        
        return results
    
    def check_dragon_criteria(self, stock_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查龙头战法标准（基于实时数据）
        
        Args:
            stock_info: 股票信息字典，包含：
                - code: 股票代码
                - name: 股票名称
                - price: 最新价
                - open: 开盘价
                - pre_close: 昨收价
                - high: 最高价
                - low: 最低价
                - bid_volume: 买一量
                - ask_volume: 卖一量
                - volume: 成交量
                - turnover: 换手率
                - volume_ratio: 量比
                - prev_pct_change: 昨日涨跌幅
                - is_20cm: 是否为20cm标的
                
        Returns:
            评分结果字典
        """
        # 1. 代码前缀检查
        code_check = self.check_code_prefix(stock_info.get('code', ''), stock_info.get('name', ''))
        if code_check.get('banned', False):
            return {
                'total_score': 0,
                'role': '杂毛',
                'signal': 'SELL',
                'action': '清仓/核按钮',
                'confidence': 'HIGH',
                'reason': f"{code_check.get('banned_reason', '禁止交易')}",
                'sector_role': '杂毛',
                'auction_intensity': '极弱',
                'weak_to_strong': False,
                'intraday_support': '弱'
            }
        
        # 2. 计算涨跌幅
        current_price = stock_info.get('price', 0)
        pre_close = stock_info.get('pre_close', 0)
        open_price = stock_info.get('open', 0)
        high_price = stock_info.get('high', 0)
        low_price = stock_info.get('low', 0)
        
        if pre_close == 0:
            return {
                'total_score': 0,
                'role': '杂毛',
                'signal': 'WAIT',
                'action': '观望',
                'confidence': 'LOW',
                'reason': '昨收价为0，无法计算涨跌幅',
                'sector_role': '杂毛',
                'auction_intensity': '极弱',
                'weak_to_strong': False,
                'intraday_support': '弱'
            }
        
        pct_change = (current_price - pre_close) / pre_close * 100
        
        # 3. 竞价分析（使用涨跌幅作为代理）
        if pct_change > 5:
            auction_score = 80
            auction_intensity = '强'
        elif pct_change > 3:
            auction_score = 60
            auction_intensity = '中等'
        elif pct_change > 1:
            auction_score = 40
            auction_intensity = '弱'
        elif pct_change > 0:
            auction_score = 20
            auction_intensity = '极弱'
        else:
            auction_score = 0
            auction_intensity = '极弱'
        
        # 4. 板块地位分析（使用涨跌幅作为代理）
        if pct_change > 7:
            sector_role_score = 80
            sector_role = '龙一（推断）'
        elif pct_change > 5:
            sector_role_score = 70
            sector_role = '前三（推断）'
        elif pct_change > 3:
            sector_role_score = 60
            sector_role = '中军（推断）'
        elif pct_change > 1:
            sector_role_score = 40
            sector_role = '跟风（推断）'
        elif pct_change > 0:
            sector_role_score = 20
            sector_role = '跟风（推断）'
        else:
            sector_role_score = 0
            sector_role = '杂毛'
        
        # 5. 弱转强分析（简化版，基于开盘价）
        prev_pct_change = stock_info.get('prev_pct_change', 0)
        if prev_pct_change < 0 and pct_change > 0:
            # 昨天跌，今天涨
            weak_to_strong_score = 100
            weak_to_strong = True
        elif prev_pct_change > 5 and pct_change > 3:
            # 昨天大涨，今天继续涨（强更强）
            weak_to_strong_score = 90
            weak_to_strong = True
        else:
            weak_to_strong_score = 0
            weak_to_strong = False
        
        # 6. 分时承接分析（使用 K 线数据作为代理）
        if current_price > open_price:
            intraday_support_score = 80
            intraday_support = '强'
        elif current_price >= open_price:
            intraday_support_score = 60
            intraday_support = '中等'
        elif current_price > low_price:
            intraday_support_score = 40
            intraday_support = '弱'
        else:
            intraday_support_score = 20
            intraday_support = '极弱'
        
        # 7. 决策矩阵
        is_20cm = stock_info.get('is_20cm', False)
        decision = self.make_decision_matrix(
            role_score=sector_role_score,
            auction_score=auction_score,
            weak_to_strong_score=weak_to_strong_score,
            intraday_support_score=intraday_support_score,
            current_change=pct_change,
            is_20cm=is_20cm
        )
        
        # 添加额外字段
        decision['sector_role'] = sector_role
        decision['auction_intensity'] = auction_intensity
        decision['weak_to_strong'] = weak_to_strong
        decision['intraday_support'] = intraday_support
        
        return decision
    
    def make_decision_matrix(self,
                           role_score: int,
                           auction_score: int,
                           weak_to_strong_score: int,
                           intraday_support_score: int,
                           current_change: float,
                           is_20cm: bool) -> Dict[str, Any]:
        """
        决策矩阵
        
        Args:
            role_score: 龙头地位评分
            auction_score: 竞价评分
            weak_to_strong_score: 弱转强评分
            intraday_support_score: 分时承接评分
            current_change: 当前涨跌幅
            is_20cm: 是否为20cm标的
            
        Returns:
            决策结果
        """
        # 综合评分
        total_score = (role_score * 0.4 + 
                      auction_score * 0.2 + 
                      weak_to_strong_score * 0.2 + 
                      intraday_support_score * 0.2)
        
        results = {
            'total_score': total_score,
            'role_score': role_score,
            'auction_score': auction_score,
            'weak_to_strong_score': weak_to_strong_score,
            'intraday_support_score': intraday_support_score
        }
        
        # 判断角色
        if role_score >= 80:
            role = '核心龙'
        elif role_score >= 60:
            role = '中军'
        elif role_score >= 40:
            role = '跟风'
        else:
            role = '杂毛'
        
        results['role'] = role
        
        # 决策逻辑（改进版，降低门槛）
        if role == '核心龙' and auction_score >= 60:
            # 核心龙 + 竞价抢筹
            if is_20cm and current_change > 10:
                results['signal'] = 'BUY_AGGRESSIVE'
                results['action'] = '扫板/排板'
                results['position'] = '满仓/重仓'
                results['confidence'] = 'HIGH'
                results['reason'] = '核心龙头，竞价抢筹，20cm突破平台，直接猛干'
            elif current_change > 5:
                results['signal'] = 'BUY_AGGRESSIVE'
                results['action'] = '扫板/排板'
                results['position'] = '满仓/重仓'
                results['confidence'] = 'HIGH'
                results['reason'] = '核心龙头，竞价抢筹，直接猛干'
            elif current_change > 3:
                results['signal'] = 'BUY'
                results['action'] = '打板/跟随'
                results['position'] = '半仓'
                results['confidence'] = 'MEDIUM'
                results['reason'] = '核心龙头，但涨幅一般，跟随买入'
            else:
                results['signal'] = 'WAIT'
                results['action'] = '观望'
                results['position'] = '0'
                results['confidence'] = 'MEDIUM'
                results['reason'] = '核心龙头，但涨幅不够，观望'
        
        elif role == '核心龙' and weak_to_strong_score >= 50:
            # 核心龙 + 弱转强（降低门槛从70到50）
            results['signal'] = 'BUY_DIP'
            results['action'] = '低吸博弈'
            results['position'] = '半仓'
            results['confidence'] = 'HIGH'
            results['reason'] = '核心龙头，弱转强形态，低吸博弈'
        
        elif role == '中军' and total_score >= 50:
            # 中军 + 综合评分高（降低门槛从70到50）
            if current_change > 5:
                results['signal'] = 'BUY'
                results['action'] = '打板/跟随'
                results['position'] = '半仓'
                results['confidence'] = 'MEDIUM'
                results['reason'] = '中军标的，涨幅较好，跟随买入'
            else:
                results['signal'] = 'WAIT'
                results['action'] = '观望'
                results['position'] = '0'
                results['confidence'] = 'MEDIUM'
                results['reason'] = '中军标的，但涨幅一般，观望'
        
        elif role == '跟风' and total_score >= 40:
            # 跟风 + 综合评分高（新增）
            if current_change > 3:
                results['signal'] = 'WAIT'
                results['action'] = '只看不买'
                results['position'] = '0'
                results['confidence'] = 'MEDIUM'
                results['reason'] = '跟风标的，涨幅较好，但只做套利，不做格局'
            else:
                results['signal'] = 'WAIT'
                results['action'] = '只看不买'
                results['position'] = '0'
                results['confidence'] = 'LOW'
                results['reason'] = '跟风标的，只做套利，不做格局'
        
        elif total_score >= 30:
            # 综合评分一般，观望
            results['signal'] = 'WAIT'
            results['action'] = '观望'
            results['position'] = '0'
            results['confidence'] = 'LOW'
            results['reason'] = '综合评分一般，观望'
        
        else:  # 杂毛
            results['signal'] = 'SELL'
            results['action'] = '清仓/核按钮'
            results['position'] = '0'
            results['confidence'] = 'HIGH'
            results['reason'] = '杂毛标的，清仓离场'
        
        return results