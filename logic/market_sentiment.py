"""
市场环境感知模块

判断市场情绪，动态调整策略参数
实现"看天吃饭"功能
"""

import pandas as pd
from datetime import datetime, timedelta
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.data_cleaner import DataCleaner

logger = get_logger(__name__)


class MarketSentiment:
    """
    市场情绪分析器
    
    功能：
    1. 获取涨停家数/跌停家数
    2. 计算连板高度
    3. 计算昨日涨停溢价
    4. 判断市场情绪（进攻/防守/震荡）
    5. 动态调整策略参数
    """
    
    # 市场情绪阈值
    BULL_LIMIT_UP_COUNT = 50      # 牛市涨停家数阈值
    BEAR_LIMIT_UP_COUNT = 20      # 熊市涨停家数阈值
    BULL_PREV_PROFIT = 0.02       # 牛市昨日涨停溢价阈值
    BEAR_PREV_PROFIT = -0.01      # 熊市昨日涨停溢价阈值
    
    # 市场状态
    REGIME_BULL_ATTACK = "BULL_ATTACK"      # 进攻模式
    REGIME_BEAR_DEFENSE = "BEAR_DEFENSE"    # 防守模式
    REGIME_CHAOS = "CHAOS"                  # 震荡模式
    
    def __init__(self):
        self.db = DataManager()
        self.current_regime = None
        self.market_data = {}
    
    def get_limit_up_down_count(self):
        """
        获取今日涨停和跌停家数
        
        Returns:
            dict: {'limit_up_count': 涨停家数, 'limit_down_count': 跌停家数}
        """
        try:
            import akshare as ak
            
            # 获取A股实时行情
            stock_list_df = ak.stock_info_a_code_name()
            stock_list = stock_list_df['code'].tolist()
            
            # 获取实时数据
            realtime_data = self.db.get_fast_price(stock_list)
            
            limit_up_count = 0
            limit_down_count = 0
            
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
                    limit_up_count += 1
                elif limit_status.get('is_limit_down', False):
                    limit_down_count += 1
            
            return {
                'limit_up_count': limit_up_count,
                'limit_down_count': limit_down_count,
                'total_count': len(realtime_data)
            }
        
        except Exception as e:
            logger.error(f"获取涨跌停家数失败: {e}")
            return {
                'limit_up_count': 0,
                'limit_down_count': 0,
                'total_count': 0
            }
    
    def get_consecutive_board_height(self):
        """
        获取连板高度（最高板数）
        
        Returns:
            dict: {'max_board': 最高板数, 'board_distribution': 板数分布}
        """
        try:
            # 这里需要从数据库获取历史涨停数据
            # 简化版：假设我们有一个涨停记录表
            # 实际实现需要查询数据库，计算连续涨停天数
            
            # TODO: 实现真正的连板高度计算
            # 这里先返回模拟数据
            return {
                'max_board': 3,
                'board_distribution': {
                    '2板': 10,
                    '3板': 5,
                    '4板': 2,
                    '5板': 1
                }
            }
        
        except Exception as e:
            logger.error(f"获取连板高度失败: {e}")
            return {
                'max_board': 0,
                'board_distribution': {}
            }
    
    def get_prev_limit_up_profit(self):
        """
        计算昨日涨停溢价
        
        Returns:
            dict: {
                'avg_profit': 平均溢价,
                'profit_count': 盈利家数,
                'loss_count': 亏损家数
            }
        """
        try:
            # 这里需要获取昨日涨停的股票，计算今日的平均涨幅
            # 简化版：假设我们有一个涨停记录表
            
            # TODO: 实现真正的昨日涨停溢价计算
            # 这里先返回模拟数据
            return {
                'avg_profit': 0.03,  # 3%
                'profit_count': 30,
                'loss_count': 10
            }
        
        except Exception as e:
            logger.error(f"计算昨日涨停溢价失败: {e}")
            return {
                'avg_profit': 0.0,
                'profit_count': 0,
                'loss_count': 0
            }
    
    def get_market_regime(self):
        """
        判断市场情绪（进攻/防守/震荡）
        
        Returns:
            dict: {
                'regime': 市场状态,
                'description': 状态描述,
                'strategy': 策略建议
            }
        """
        try:
            # 获取市场数据
            limit_up_down = self.get_limit_up_down_count()
            prev_profit = self.get_prev_limit_up_profit()
            
            limit_up_count = limit_up_down.get('limit_up_count', 0)
            avg_profit = prev_profit.get('avg_profit', 0)
            
            # 判断市场状态
            if limit_up_count >= self.BULL_LIMIT_UP_COUNT and avg_profit >= self.BULL_PREV_PROFIT:
                # 进攻模式
                regime = self.REGIME_BULL_ATTACK
                description = "市场情绪火热，适合进攻"
                strategy = "参数放宽，敢于追高"
            
            elif limit_up_count <= self.BEAR_LIMIT_UP_COUNT or avg_profit <= self.BEAR_PREV_PROFIT:
                # 防守模式
                regime = self.REGIME_BEAR_DEFENSE
                description = "市场情绪低迷，适合防守"
                strategy = "参数收紧，禁止打板，只做低吸"
            
            else:
                # 震荡模式
                regime = self.REGIME_CHAOS
                description = "市场情绪震荡，谨慎操作"
                strategy = "只做首板，控制仓位"
            
            self.current_regime = regime
            self.market_data = {
                'limit_up_count': limit_up_count,
                'limit_down_count': limit_up_down.get('limit_down_count', 0),
                'prev_profit': avg_profit,
                'max_board': self.get_consecutive_board_height().get('max_board', 0)
            }
            
            return {
                'regime': regime,
                'description': description,
                'strategy': strategy,
                'market_data': self.market_data
            }
        
        except Exception as e:
            logger.error(f"判断市场情绪失败: {e}")
            return {
                'regime': self.REGIME_CHAOS,
                'description': "无法判断市场情绪",
                'strategy': "保守操作",
                'market_data': {}
            }
    
    def get_strategy_parameters(self, regime=None):
        """
        根据市场状态获取策略参数
        
        Args:
            regime: 市场状态（如果不提供，使用当前状态）
        
        Returns:
            dict: 策略参数
        """
        if regime is None:
            regime = self.current_regime
        
        if regime == self.REGIME_BULL_ATTACK:
            # 进攻模式：参数放宽
            return {
                'dragon': {
                    'min_score': 50,          # 降低评分门槛
                    'min_change_pct': 5.0,    # 降低涨幅要求
                    'min_volume_ratio': 1.5,  # 降低量比要求
                    'max_position': 0.8       # 允许大仓位
                },
                'trend': {
                    'min_score': 55,
                    'min_change_pct': 1.5,
                    'min_volume_ratio': 1.0,
                    'max_position': 0.7
                },
                'halfway': {
                    'min_score': 60,
                    'min_change_pct': 10.0,
                    'min_volume_ratio': 3.0,
                    'max_position': 0.6
                }
            }
        
        elif regime == self.REGIME_BEAR_DEFENSE:
            # 防守模式：参数收紧
            return {
                'dragon': {
                    'min_score': 80,          # 提高评分门槛
                    'min_change_pct': 9.0,    # 提高涨幅要求
                    'min_volume_ratio': 3.0,  # 提高量比要求
                    'max_position': 0.2       # 限制仓位
                },
                'trend': {
                    'min_score': 75,
                    'min_change_pct': 3.0,
                    'min_volume_ratio': 2.0,
                    'max_position': 0.3
                },
                'halfway': {
                    'min_score': 85,          # 禁止半路战法
                    'min_change_pct': 15.0,
                    'min_volume_ratio': 5.0,
                    'max_position': 0.1
                }
            }
        
        else:  # CHAOS
            # 震荡模式：中等参数
            return {
                'dragon': {
                    'min_score': 60,
                    'min_change_pct': 7.0,
                    'min_volume_ratio': 2.0,
                    'max_position': 0.5
                },
                'trend': {
                    'min_score': 65,
                    'min_change_pct': 2.0,
                    'min_volume_ratio': 1.5,
                    'max_position': 0.5
                },
                'halfway': {
                    'min_score': 70,
                    'min_change_pct': 12.0,
                    'min_volume_ratio': 4.0,
                    'max_position': 0.4
                }
            }
    
    def get_market_weather_icon(self):
        """
        获取市场天气图标
        
        Returns:
            str: 天气图标和描述
        """
        if self.current_regime == self.REGIME_BULL_ATTACK:
            return "☀️ 晴天（进攻）"
        elif self.current_regime == self.REGIME_BEAR_DEFENSE:
            return "🌧️ 暴雨（防守）"
        else:
            return "☁️ 多云（震荡）"
    
    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()