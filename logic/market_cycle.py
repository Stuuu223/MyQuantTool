"""
市场周期管理模块

实现情绪周期识别，让系统具备"大局观"
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.data_cleaner import DataCleaner

logger = get_logger(__name__)


class MarketCycleManager:
    """
    市场周期管理器
    
    功能：
    1. 识别市场情绪周期（高潮期/冰点期/主升期/混沌期）
    2. 计算核心情绪指标
    3. 提供周期切换信号
    4. 作为所有策略的"总开关"
    """
    
    # 市场周期定义
    CYCLE_BOOM = "BOOM"              # 高潮期：情绪高潮，危险
    CYCLE_MAIN_RISE = "MAIN_RISE"    # 主升期：主升浪，满仓猛干
    CYCLE_CHAOS = "CHAOS"            # 混沌期：震荡，空仓或轻仓套利
    CYCLE_ICE = "ICE"                # 冰点期：冰点，试错首板
    CYCLE_DECLINE = "DECLINE"        # 退潮期：退潮，只卖不买
    
    # 周期阈值
    BOOM_LIMIT_UP_COUNT = 100        # 高潮期涨停家数阈值
    BOOM_HIGHEST_BOARD = 7          # 高潮期最高板数阈值
    ICE_LIMIT_UP_COUNT = 20          # ICE期涨停家数阈值
    ICE_HIGHEST_BOARD = 3            # ICE期最高板数阈值
    MAIN_RISE_PROFIT_EFFECT = 0.05  # 主升期昨日溢价阈值
    DECLINE_BURST_RATE = 0.3       # 退潮期炸板率阈值
    
    def __init__(self):
        """初始化市场周期管理器"""
        self.db = DataManager()
        self.current_cycle = None
        self.cycle_history = []
        self.market_indicators = {}
    
    def get_market_emotion(self) -> Dict:
        """
        获取市场情绪指标
        
        Returns:
            dict: 市场情绪指标
        """
        try:
            # 1. 获取涨跌停家数
            limit_up_down = self.get_limit_up_down_count()
            
            # 2. 获取连板高度
            board_info = self.get_consecutive_board_height()
            
            # 3. 获取昨日涨停溢价
            prev_profit = self.get_prev_limit_up_profit()
            
            # 4. 获取炸板率
            burst_rate = self.get_limit_up_burst_rate()
            
            # 5. 获取晋级率
            promotion_rate = self.get_board_promotion_rate()
            
            self.market_indicators = {
                'limit_up_count': limit_up_down['limit_up_count'],
                'limit_down_count': limit_up_down['limit_down_count'],
                'highest_board': board_info['max_board'],
                'avg_profit': prev_profit['avg_profit'],
                'burst_rate': burst_rate,
                'promotion_rate': promotion_rate,
                'limit_up_stocks': limit_up_down.get('limit_up_stocks', []),
                'limit_down_stocks': limit_up_down.get('limit_down_stocks', [])
            }
            
            return self.market_indicators
        
        except Exception as e:
            logger.error(f"获取市场情绪指标失败: {e}")
            return {}
    
    def get_current_phase(self) -> Dict:
        """
        判断当前市场周期
        
        Returns:
            dict: {
                'cycle': 周期类型,
                'description': 周期描述,
                'strategy': 策略建议,
                'risk_level': 风险等级 (1-5)
            }
        """
        try:
            # 获取市场情绪指标
            indicators = self.get_market_emotion()
            
            if not indicators:
                return {
                    'cycle': self.CYCLE_CHAOS,
                    'description': "无法判断市场情绪",
                    'strategy': "保守操作，空仓观望",
                    'risk_level': 3
                }
            
            limit_up_count = indicators['limit_up_count']
            highest_board = indicators['highest_board']
            avg_profit = indicators['avg_profit']
            burst_rate = indicators['burst_rate']
            promotion_rate = indicators['promotion_rate']
            
            # 判断周期
            if limit_up_count >= self.BOOM_LIMIT_UP_COUNT and highest_board >= self.BOOM_HIGHEST_BOARD:
                # 高潮期：情绪高潮，危险
                self.current_cycle = self.CYCLE_BOOM
                return {
                    'cycle': self.CYCLE_BOOM,
                    'description': "高潮期：情绪极度高涨，风险极大",
                    'strategy': "只卖不买，果断止盈，落袋为安",
                    'risk_level': 5
                }
            
            elif limit_up_count <= self.ICE_LIMIT_UP_COUNT and highest_board <= self.ICE_HIGHEST_BOARD:
                # 冰点期：情绪冰点，机会
                self.current_cycle = self.CYCLE_ICE
                return {
                    'cycle': self.CYCLE_ICE,
                    'description': "冰点期：情绪冰点，试错首板",
                    'strategy': "试错首板，做新题材，小仓位试探",
                    'risk_level': 2
                }
            
            elif avg_profit >= self.MAIN_RISE_PROFIT_EFFECT and burst_rate < 0.2:
                # 主升期：主升浪，满仓猛干
                self.current_cycle = self.CYCLE_MAIN_RISE
                return {
                    'cycle': self.CYCLE_MAIN_RISE,
                    'description': "主升期：主升浪启动，满仓猛干",
                    'strategy': "龙头战法，重仓出击，不要怂",
                    'risk_level': 3
                }
            
            elif burst_rate >= self.DECLINE_BURST_RATE or avg_profit < -0.01:
                # 退潮期：退潮，只卖不买
                self.current_cycle = self.CYCLE_DECLINE
                return {
                    'cycle': self.CYCLE_DECLINE,
                    'description': "退潮期：退潮明显，只卖不买",
                    'strategy': "只卖不买，清仓观望，等待周期切换",
                    'risk_level': 4
                }
            
            else:
                # 混沌期：震荡，空仓或轻仓套利
                self.current_cycle = self.CYCLE_CHAOS
                return {
                    'cycle': self.CYCLE_CHAOS,
                    'description': "混沌期：情绪震荡，谨慎操作",
                    'strategy': "空仓或轻仓套利，控制仓位",
                    'risk_level': 3
                }
        
        except Exception as e:
            logger.error(f"判断市场周期失败: {e}")
            return {
                'cycle': self.CYCLE_CHAOS,
                'description': "无法判断市场周期",
                'strategy': "保守操作",
                'risk_level': 3
            }
    
    def get_limit_up_down_count(self) -> Dict:
        """
        获取今日涨停和跌停家数
        
        Returns:
            dict: {
                'limit_up_count': 涨停家数,
                'limit_down_count': 跌停家数,
                'limit_up_stocks': 涨停股票列表,
                'limit_down_stocks': 跌停股票列表
            }
        """
        try:
            import akshare as ak
            
            # 获取A股实时行情
            stock_list_df = ak.stock_info_a_code_name()
            stock_list = stock_list_df['code'].tolist()
            
            # 获取实时数据
            realtime_data = self.db.get_fast_price(stock_list)
            
            limit_up_stocks = []
            limit_down_stocks = []
            
            for full_code, data in realtime_data.items():
                # 清洗股票代码
                code = DataCleaner.clean_stock_code(full_code)
                if not code:
                    continue
                
                # 清洗数据
                cleaned_data = DataCleaner.clean_realtime_data(data)
                if not cleaned_data:
                    continue
                
                # 检查涨跌停状态
                limit_status = cleaned_data.get('limit_status', {})
                
                if limit_status.get('is_limit_up', False):
                    limit_up_stocks.append({
                        'code': code,
                        'name': cleaned_data.get('name', ''),
                        'price': cleaned_data.get('now', 0),
                        'change_pct': cleaned_data.get('change_pct', 0)
                    })
                elif limit_status.get('is_limit_down', False):
                    limit_down_stocks.append({
                        'code': code,
                        'name': cleaned_data.get('name', ''),
                        'price': cleaned_data.get('now', 0),
                        'change_pct': cleaned_data.get('change_pct', 0)
                    })
            
            return {
                'limit_up_count': len(limit_up_stocks),
                'limit_down_count': len(limit_down_stocks),
                'limit_up_stocks': limit_up_stocks,
                'limit_down_stocks': limit_down_stocks
            }
        
        except Exception as e:
            logger.error(f"获取涨跌停家数失败: {e}")
            return {
                'limit_up_count': 0,
                'limit_down_count': 0,
                'limit_up_stocks': [],
                'limit_down_stocks': []
            }
    
    def get_consecutive_board_height(self) -> Dict:
        """
        获取连板高度
        
        Returns:
            dict: {
                'max_board': 最高板数,
                'board_distribution': 连板分布
            }
        """
        try:
            limit_up_stocks = self.get_limit_up_down_count().get('limit_up_stocks', [])
            
            if not limit_up_stocks:
                return {
                    'max_board': 0,
                    'board_distribution': {}
                }
            
            # 获取连板信息（这里简化处理，实际应该从数据库查询历史数据）
            board_distribution = {
                '1板': 0,
                '2板': 0,
                '3板': 0,
                '4板': 0,
                '5板': 0,
                '6板': 0,
                '7板': 0,
                '8板+': 0
            }
            
            # 简化：假设所有涨停都是首板（实际应该查询历史数据）
            board_distribution['1板'] = len(limit_up_stocks)
            
            max_board = 1  # 简化处理
            
            return {
                'max_board': max_board,
                'board_distribution': board_distribution
            }
        
        except Exception as e:
            logger.error(f"获取连板高度失败: {e}")
            return {
                'max_board': 0,
                'board_distribution': {}
            }
    
    def get_prev_limit_up_profit(self) -> Dict:
        """
        获取昨日涨停溢价
        
        Returns:
            dict: {
                'avg_profit': 平均溢价,
                'profit_count': 盈利数量,
                'loss_count': 亏损数量
            }
        """
        try:
            # 获取昨天的涨停股票
            # 这里简化处理，实际应该从数据库查询昨天的涨停数据
            # 返回模拟数据
            return {
                'avg_profit': 0.03,
                'profit_count': 10,
                'loss_count': 5
            }
        
        except Exception as e:
            logger.error(f"获取昨日涨停溢价失败: {e}")
            return {
                'avg_profit': 0,
                'profit_count': 0,
                'loss_count': 0
            }
    
    def get_limit_up_burst_rate(self) -> float:
        """
        获取炸板率
        
        Returns:
            float: 炸板率
        """
        try:
            # 简化处理，返回模拟数据
            return 0.15
        
        except Exception as e:
            logger.error(f"获取炸板率失败: {e}")
            return 0.0
    
    def get_board_promotion_rate(self) -> float:
        """
        获取晋级率（今天连板数 / 昨天首板数）
        
        Returns:
            float: 晋级率
        """
        try:
            # 简化处理，返回模拟数据
            return 0.25
        
        except Exception as e:
            logger.error(f"获取晋级率失败: {e}")
            return 0.0
    
    def get_cycle_history(self, days: int = 30) -> List[Dict]:
        """
        获取周期历史
        
        Args:
            days: 获取最近多少天的历史
        
        Returns:
            list: 周期历史列表
        """
        return self.cycle_history[-days:]
    
    def record_cycle(self, cycle_info: Dict):
        """
        记录周期信息
        
        Args:
            cycle_info: 周期信息
        """
        cycle_info['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cycle_history.append(cycle_info)
        
        # 保留最近 90 天的历史
        if len(self.cycle_history) > 90:
            self.cycle_history = self.cycle_history[-90:]
    
    def get_cycle_summary(self) -> str:
        """
        获取周期总结
        
        Returns:
            str: 周期总结文本
        """
        if not self.cycle_history:
            return "暂无周期历史数据"
        
        # 统计各周期出现的次数
        cycle_count = {}
        for cycle_info in self.cycle_history:
            cycle = cycle_info.get('cycle', 'UNKNOWN')
            cycle_count[cycle] = cycle_count.get(cycle, 0) + 1
        
        summary = f"## 市场周期统计（最近{len(self.cycle_history)}天）\n\n"
        
        for cycle, count in sorted(cycle_count.items(), key=lambda x: x[1], reverse=True):
            summary += f"- {cycle}: {count} 天\n"
        
        return summary
    
    def get_risk_warning(self) -> Optional[str]:
        """
        获取风险警告
        
        Returns:
            str: 风险警告信息，如果没有风险则返回 None
        """
        cycle_info = self.get_current_phase()
        
        if cycle_info['risk_level'] >= 4:
            return f"⚠️ 高风险警告：{cycle_info['description']}，建议{cycle_info['strategy']}"
        elif cycle_info['risk_level'] >= 3:
            return f"⚠️ 中等风险：{cycle_info['description']}，建议{cycle_info['strategy']}"
        else:
            return None
    
    def detect_special_operations(self) -> Dict:
        """
        检测特种作战机会（V6.1 新增）
        
        功能：
        1. 反核模式：监控跌停板上的核心龙头，检测大单翘板信号
        2. 龙回头模式：检测真龙首阴低吸机会
        3. 地天板模式：检测地天板博弈机会
        
        Returns:
            dict: {
                'has_special_opportunity': bool,
                'operation_type': 'ANTI_NUCLEAR' | 'DRAGON_RETURN' | 'GROUND_TO_SKY' | None,
                'target_stocks': [股票列表],
                'operation_strategy': '操作建议',
                'confidence': 'HIGH' | 'MEDIUM' | 'LOW'
            }
        """
        try:
            cycle_info = self.get_current_phase()
            current_cycle = cycle_info['cycle']
            
            # 只在 ICE 和 DECLINE 周期检测特种作战机会
            if current_cycle not in [self.CYCLE_ICE, self.CYCLE_DECLINE]:
                return {
                    'has_special_opportunity': False,
                    'operation_type': None,
                    'target_stocks': [],
                    'operation_strategy': f"当前周期为{current_cycle}，不适合特种作战",
                    'confidence': 'LOW'
                }
            
            # 获取跌停股票列表
            limit_down_stocks = self.market_indicators.get('limit_down_stocks', [])
            
            if not limit_down_stocks:
                return {
                    'has_special_opportunity': False,
                    'operation_type': None,
                    'target_stocks': [],
                    'operation_strategy': "当前无跌停股票，无特种作战机会",
                    'confidence': 'LOW'
                }
            
            special_opportunities = []
            
            # 1. 检测反核机会（跌停板上的核心龙头）
            anti_nuclear_stocks = self._detect_anti_nuclear_opportunity(limit_down_stocks)
            if anti_nuclear_stocks:
                special_opportunities.extend([{
                    'type': 'ANTI_NUCLEAR',
                    'stock': stock,
                    'strategy': '博弈地天板，关注大单翘板信号'
                } for stock in anti_nuclear_stocks])
            
            # 2. 检测龙回头机会（首阴低吸）
            dragon_return_stocks = self._detect_dragon_return_opportunity(limit_down_stocks)
            if dragon_return_stocks:
                special_opportunities.extend([{
                    'type': 'DRAGON_RETURN',
                    'stock': stock,
                    'strategy': '首阴低吸博弈，关注均线支撑'
                } for stock in dragon_return_stocks])
            
            # 3. 检测地天板机会
            ground_to_sky_stocks = self._detect_ground_to_sky_opportunity(limit_down_stocks)
            if ground_to_sky_stocks:
                special_opportunities.extend([{
                    'type': 'GROUND_TO_SKY',
                    'stock': stock,
                    'strategy': '地天板博弈，关注盘口变化'
                } for stock in ground_to_sky_stocks])
            
            if special_opportunities:
                # 按优先级排序：ANTI_NUCLEAR > GROUND_TO_SKY > DRAGON_RETURN
                priority_order = {'ANTI_NUCLEAR': 3, 'GROUND_TO_SKY': 2, 'DRAGON_RETURN': 1}
                special_opportunities.sort(key=lambda x: priority_order.get(x['type'], 0), reverse=True)
                
                top_opportunity = special_opportunities[0]
                
                return {
                    'has_special_opportunity': True,
                    'operation_type': top_opportunity['type'],
                    'target_stocks': [opp['stock'] for opp in special_opportunities],
                    'operation_strategy': f"🎯 {top_opportunity['type']}特种作战：{top_opportunity['strategy']}",
                    'confidence': 'HIGH' if top_opportunity['type'] == 'ANTI_NUCLEAR' else 'MEDIUM',
                    'all_opportunities': special_opportunities
                }
            else:
                return {
                    'has_special_opportunity': False,
                    'operation_type': None,
                    'target_stocks': [],
                    'operation_strategy': "当前无特种作战机会",
                    'confidence': 'LOW'
                }
        
        except Exception as e:
            logger.error(f"检测特种作战机会失败: {e}")
            return {
                'has_special_opportunity': False,
                'operation_type': None,
                'target_stocks': [],
                'operation_strategy': '检测失败',
                'confidence': 'LOW'
            }
    
    def _detect_anti_nuclear_opportunity(self, limit_down_stocks: List[Dict]) -> List[Dict]:
        """
        检测反核机会（跌停板上的核心龙头）
        
        Args:
            limit_down_stocks: 跌停股票列表
        
        Returns:
            list: 具备反核机会的股票列表
        """
        anti_nuclear_stocks = []
        
        for stock in limit_down_stocks:
            code = stock['code']
            name = stock['name']
            change_pct = stock['change_pct']
            
            # 反核机会判断逻辑：
            # 1. 跌停板上（change_pct <= -9.5%）
            # 2. 是核心龙头（这里简化判断：成交额较大）
            # 3. 有大单翘板迹象（需要实时盘口数据，这里简化处理）
            
            if change_pct <= -9.5:
                # 检查是否是核心龙头（这里简化：假设成交额 > 1亿）
                # 实际应该从数据库获取成交额数据
                is_core_dragon = True  # 简化处理
                
                if is_core_dragon:
                    anti_nuclear_stocks.append({
                        'code': code,
                        'name': name,
                        'change_pct': change_pct,
                        'reason': '核心龙头跌停，关注大单翘板信号'
                    })
        
        return anti_nuclear_stocks
    
    def _detect_dragon_return_opportunity(self, limit_down_stocks: List[Dict]) -> List[Dict]:
        """
        检测龙回头机会（首阴低吸）
        
        Args:
            limit_down_stocks: 跌停股票列表
        
        Returns:
            list: 具备龙回头机会的股票列表
        """
        dragon_return_stocks = []
        
        for stock in limit_down_stocks:
            code = stock['code']
            name = stock['name']
            change_pct = stock['change_pct']
            
            # 龙回头机会判断逻辑：
            # 1. 龙头股首日断板大跌（-5% ~ -10%）
            # 2. 未破 10 日线（需要历史数据，这里简化处理）
            # 3. 成交量萎缩（需要历史数据，这里简化处理）
            
            if -10 <= change_pct <= -5:
                # 检查是否是龙头股（这里简化处理）
                is_dragon = True  # 简化处理
                
                if is_dragon:
                    dragon_return_stocks.append({
                        'code': code,
                        'name': name,
                        'change_pct': change_pct,
                        'reason': '龙头首阴大跌，关注均线支撑和低吸机会'
                    })
        
        return dragon_return_stocks
    
    def _detect_ground_to_sky_opportunity(self, limit_down_stocks: List[Dict]) -> List[Dict]:
        """
        检测地天板机会
        
        Args:
            limit_down_stocks: 跌停股票列表
        
        Returns:
            list: 具备地天板机会的股票列表
        """
        ground_to_sky_stocks = []
        
        for stock in limit_down_stocks:
            code = stock['code']
            name = stock['name']
            change_pct = stock['change_pct']
            
            # 地天板机会判断逻辑：
            # 1. 跌停板上（change_pct <= -9.5%）
            # 2. 有大单翘板迹象（Order Imbalance 剧烈变化）
            # 3. 是核心龙头或热门股
            
            if change_pct <= -9.5:
                # 检查是否是热门股（这里简化处理）
                is_hot = True  # 简化处理
                
                if is_hot:
                    ground_to_sky_stocks.append({
                        'code': code,
                        'name': name,
                        'change_pct': change_pct,
                        'reason': '跌停板热门股，关注地天板博弈机会'
                    })
        
        return ground_to_sky_stocks
    
    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()
