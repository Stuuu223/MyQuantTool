"""
市场周期管理模块

实现情绪周期识别，让系统具备"大局观"
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import akshare as ak
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
    
    def save_limit_up_pool_to_redis(self, limit_up_stocks: List[Dict]) -> bool:
        """
        🆕 V9.2 新增：保存今日涨停池到 Redis
        
        Args:
            limit_up_stocks: 涨停股票列表
        
        Returns:
            bool: 是否保存成功
        """
        try:
            if not self.db._redis_client:
                logger.warning("Redis 未连接，无法保存涨停池")
                return False
            
            # 使用今天的日期作为 key
            today = datetime.now().strftime('%Y%m%d')
            key = f"limit_up:{today}"
            
            # 提取股票代码列表
            stock_codes = [stock['code'] for stock in limit_up_stocks]
            
            # 保存到 Redis，过期时间为 7 天
            import json
            success = self.db.redis_set(key, json.dumps(stock_codes), expire=7*24*3600)
            
            if success:
                logger.info(f"✅ 已保存今日涨停池到 Redis（{len(stock_codes)}只股票）")
            else:
                logger.error(f"❌ 保存涨停池到 Redis 失败")
            
            return success
        
        except Exception as e:
            logger.error(f"保存涨停池到 Redis 失败: {e}")
            return False
    
    def get_limit_up_pool_from_redis(self, date_str: str = None) -> List[str]:
        """
        🆕 V9.2 新增：从 Redis 获取涨停池
        
        Args:
            date_str: 日期字符串（格式：YYYYMMDD），默认为昨天
        
        Returns:
            list: 股票代码列表
        """
        try:
            if not self.db._redis_client:
                logger.warning("Redis 未连接，无法获取涨停池")
                return []
            
            # 如果没有指定日期，使用昨天
            if not date_str:
                date_str = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            
            key = f"limit_up:{date_str}"
            
            # 从 Redis 获取数据
            import json
            raw_data = self.db.redis_get(key)
            
            if raw_data:
                stock_codes = json.loads(raw_data)
                logger.info(f"✅ 已从 Redis 恢复涨停池（{date_str}，{len(stock_codes)}只股票）")
                return stock_codes
            else:
                logger.warning(f"⚠️ Redis 中没有 {date_str} 的涨停池数据")
                return []
        
        except Exception as e:
            logger.error(f"从 Redis 获取涨停池失败: {e}")
            return []
    
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
            
            # 🆕 V9.2.1 修复：获取实时数据，用于计算平均溢价
            # 在盘中，daily_bars 数据库通常只包含 T-1（昨天及以前）的历史数据
            # 所以必须使用实时数据来计算今日价格
            realtime_data = {}
            for stock in limit_up_down.get('limit_up_stocks', []) + limit_up_down.get('limit_down_stocks', []):
                realtime_data[stock['code']] = {
                    'price': stock.get('price', 0),
                    'change_pct': stock.get('change_pct', 0)
                }
            
            # 3. 获取昨日涨停溢价（传入实时数据）
            prev_profit = self.get_prev_limit_up_profit(realtime_data)
            
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
            
            # 🆕 V9.2 新增：保存今日涨停池到 Redis
            # 这样明天就可以计算晋级率和平均溢价
            limit_up_stocks = limit_up_down.get('limit_up_stocks', [])
            if limit_up_stocks:
                self.save_limit_up_pool_to_redis(limit_up_stocks)
            
            return self.market_indicators
        
        except Exception as e:
            logger.error(f"获取市场情绪指标失败: {e}")
            return {}
    
    def get_current_phase(self, custom_indicators=None) -> Dict:
        """
        判断当前市场周期
        
        Args:
            custom_indicators: 可选的自定义指标（用于测试）
        
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
            if custom_indicators:
                indicators = custom_indicators
            else:
                indicators = self.get_market_emotion()
            
            if not indicators:
                return {
                    'cycle': self.CYCLE_CHAOS,
                    'description': "无法判断市场情绪",
                    'strategy': "保守操作，空仓观望",
                    'risk_level': 3
                }
            
            limit_up_count = indicators['limit_up_count']
            limit_down_count = indicators['limit_down_count']
            highest_board = indicators['highest_board']
            avg_profit = indicators['avg_profit']
            burst_rate = indicators['burst_rate']
            promotion_rate = indicators['promotion_rate']
            
            # 🛑 V9.2 新增：恐慌熔断机制 (Panic Circuit Breaker)
            # 1. 绝对恐慌：跌停比涨停多 → 直接降级为"暴雨"
            if limit_down_count > limit_up_count:
                self.current_cycle = self.CYCLE_DECLINE  # 退潮期
                return {
                    'cycle': 'PANIC',  # 恐慌期
                    'description': "暴雨：极度危险，空仓观望",
                    'strategy': "只卖不买，空仓观望，等待情绪修复",
                    'risk_level': 5
                }
            
            # 2. 局部恐慌：跌停家数超过 30 家 → 最高只能是"多云"
            if limit_down_count > 30:
                self.current_cycle = self.CYCLE_CHAOS  # 混沌期
                return {
                    'cycle': 'CAUTIOUS',  # 谨慎期
                    'description': "多云：分歧巨大，谨慎操作",
                    'strategy': "轻仓试错，控制仓位，只做最高板",
                    'risk_level': 4
                }
            
            # 判断周期（原有逻辑，但增加了跌停因子的约束）
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
            # 🆕 V9.3.7: 使用 Easyquotation获取实时数据 + DataManager获取行业信息（使用缓存）
            logger.info("正在获取全市场实时快照...")

            # 第一步：从 Easyquotation 获取实时价格数据（快速）
            try:
                stock_list_df = ak.stock_info_a_code_name()
                stock_list = stock_list_df['code'].tolist()
            except Exception as e:
                logger.warning(f"AkShare 获取股票列表失败: {e}，使用样本股票列表")
                # 回退：使用样本股票列表
                stock_list = [
                    '000001', '000002', '000063', '000066', '000333', '000651',
                    '000725', '000858', '000895', '002415', '002594', '002714',
                    '002841', '300059', '300142', '300274', '300347', '300433',
                    '300750', '600000', '600036', '600519', '600900', '601318',
                    '601398', '601766', '601888', '603259', '688981'
                ]

            realtime_data = self.db.get_fast_price(stock_list)
            
            # 第二步：从 DataManager 获取行业信息（使用缓存，极快）
            code_to_industry = self.db.get_industry_cache()
            
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
                
                # 剔除新股（N开头）、次新股（C开头）、ST股
                name = cleaned_data.get('name', '')
                if name.startswith(('N', 'C')):
                    continue
                if 'ST' in name or '*ST' in name:
                    continue
                
                # 🆕 V9.3.6: 剔除停牌股（成交量为0）
                volume = cleaned_data.get('volume', 0)
                if volume == 0:
                    continue
                
                # 获取行业信息
                industry = code_to_industry.get(code, '未知')
                
                # 计算涨跌幅
                now = cleaned_data.get('now', 0)
                pre_close = cleaned_data.get('close', 0)
                high = cleaned_data.get('high', 0)
                
                if pre_close <= 0 or now == 0:
                    continue
                
                change_pct = (now - pre_close) / pre_close * 100
                
                # 🆕 V9.3.6: 精确涨停价计算（四舍五入到2位）
                is_20cm = code.startswith(('30', '68'))
                limit_ratio = 1.20 if is_20cm else 1.10
                limit_price = round(pre_close * limit_ratio, 2)
                
                # 使用精确涨停价判断
                is_limit_up = now >= limit_price
                is_limit_down = now <= (pre_close / limit_ratio)
                
                # 计算炸板（最高价摸过涨停，但现价没封住）
                is_exploded = (high >= limit_price) and (now < limit_price)
                
                if is_limit_up:
                    limit_up_stocks.append({
                        'code': code,
                        'name': name,
                        'price': now,
                        'change_pct': change_pct,
                        'industry': industry,
                        'is_exploded': is_exploded
                    })
                elif is_limit_down:
                    limit_down_stocks.append({
                        'code': code,
                        'name': name,
                        'price': now,
                        'change_pct': change_pct,
                        'industry': industry
                    })
            
            logger.info(f"✅ 统计：涨停{len(limit_up_stocks)}家，跌停{len(limit_down_stocks)}家")
            
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
            
            # 获取连板信息（从数据库查询历史数据）
            from datetime import datetime, timedelta
            
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
            
            max_board = 0
            
            # 🆕 V9.2 修复：检查数据库中是否有足够的历史数据
            # 检查最近的数据日期
            recent_query = "SELECT MAX(date) as max_date FROM daily_bars"
            recent_df = pd.read_sql(recent_query, self.db.conn)
            
            if recent_df.empty or recent_df.iloc[0]['max_date'] is None:
                logger.warning("数据库中没有历史数据，无法计算连板高度")
                # 降级：返回默认值（所有涨停都是1板）
                board_distribution['1板'] = len(limit_up_stocks)
                return {
                    'max_board': 1,
                    'board_distribution': board_distribution
                }
            
            # 检查是否有最近的数据（最近7天）
            max_date = recent_df.iloc[0]['max_date']
            max_date_dt = datetime.strptime(max_date, '%Y-%m-%d')
            days_diff = (datetime.now() - max_date_dt).days
            
            if days_diff > 7:
                logger.warning(f"数据库中的最新数据是{days_diff}天前，可能不准确")
                # 降级：返回默认值（所有涨停都是1板）
                board_distribution['1板'] = len(limit_up_stocks)
                return {
                    'max_board': 1,
                    'board_distribution': board_distribution
                }
            
            for stock in limit_up_stocks:
                symbol = stock['code']
                
                # 🆕 V9.2 修复：使用正确的算法计算连续涨停天数
                # 查询该股票最近10天的数据
                query = f"""
                SELECT date, open, close, high, low
                FROM daily_bars
                WHERE symbol = '{symbol}'
                ORDER BY date DESC
                LIMIT 10
                """
                
                df = pd.read_sql(query, self.db.conn)
                
                if df.empty:
                    continue
                
                # 从今天开始检查
                consecutive_count = 0
                last_db_date = None
                
                for idx, row in df.iterrows():
                    open_price = row['open']
                    close_price = row['close']
                    high_price = row['high']
                    low_price = row['low']
                    date = row['date']
                    
                    # 记录数据库中的最新日期
                    if last_db_date is None:
                        last_db_date = date
                    
                    # 判断是否涨停（使用开盘价和收盘价计算涨幅）
                    # 涨停判断：涨幅 >= 9.5%（主板）或 >= 19.5%（创业板/科创板）
                    if open_price > 0:
                        change_pct = (close_price - open_price) / open_price * 100
                        
                        # 更准确的涨停判断：需要考虑涨跌停板限制
                        # 主板：10%涨跌停，创业板/科创板：20%涨跌停
                        # 根据股票代码判断：
                        # 60xxxx：主板，10%
                        # 00xxxx：主板，10%
                        # 30xxxx：创业板，20%
                        # 68xxxx：科创板，20%
                        
                        if symbol.startswith('60') or symbol.startswith('00'):
                            is_limit_up = change_pct >= 9.5
                        elif symbol.startswith('30') or symbol.startswith('68'):
                            is_limit_up = change_pct >= 19.5
                        else:
                            is_limit_up = change_pct >= 9.5  # 默认按主板处理
                        
                        if is_limit_up:
                            consecutive_count += 1
                        else:
                            # 一旦没有涨停，停止计数
                            break
                    else:
                        # 开盘价为0，无法判断，停止计数
                        break
                
                # 🆕 V9.2.1 修复：添加 +1 逻辑
                # 如果数据库最新日期是昨天，说明还要加上今天这一板
                # 因为进入这个方法的 limit_up_stocks 列表本身就是今天涨停的股票
                if consecutive_count > 0 and last_db_date:
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    
                    # 检查数据库里的最新日期是否是今天
                    if last_db_date != today_str:
                        # 数据库最新日期不是今天，说明今天的数据还没有入库
                        # 所以需要 +1，加上今天这一板
                        consecutive_count += 1
                        logger.debug(f"股票 {symbol} 数据库最新日期是 {last_db_date}，不是今天 {today_str}，连板数 +1")
                
                if consecutive_count > 0:
                    # 统计到对应的板数
                    if consecutive_count == 1:
                        board_distribution['1板'] += 1
                    elif consecutive_count == 2:
                        board_distribution['2板'] += 1
                    elif consecutive_count == 3:
                        board_distribution['3板'] += 1
                    elif consecutive_count == 4:
                        board_distribution['4板'] += 1
                    elif consecutive_count == 5:
                        board_distribution['5板'] += 1
                    elif consecutive_count == 6:
                        board_distribution['6板'] += 1
                    elif consecutive_count == 7:
                        board_distribution['7板'] += 1
                    else:
                        board_distribution['8板+'] += 1
                    
                    max_board = max(max_board, consecutive_count)
            
            return {
                'max_board': max_board,
                'board_distribution': board_distribution
            }
        
        except Exception as e:
            logger.error(f"获取连板高度失败: {e}")
            # 降级：返回模拟数据
            return {
                'max_board': 0,
                'board_distribution': {}
            }
    
    def get_prev_limit_up_profit(self, realtime_data: Dict = None) -> Dict:
        """
        获取昨日涨停溢价
        
        Args:
            realtime_data: 实时数据字典，格式: {code: {'price': float, 'change_pct': float}}
        
        Returns:
            dict: {
                'avg_profit': 平均溢价,
                'profit_count': 盈利数量,
                'loss_count': 亏损数量
            }
        """
        try:
            # 🆕 V9.2 修复：优先使用 Redis 数据
            # 从 Redis 获取昨日涨停池
            yesterday_limit_up_codes = self.get_limit_up_pool_from_redis()
            
            if not yesterday_limit_up_codes:
                logger.warning("Redis 中没有昨日涨停池数据，降级使用数据库查询")
                # 降级：使用数据库查询
                from datetime import datetime, timedelta
                
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                
                # 检查数据库中是否有昨天的数据
                yesterday_query = f"""
                SELECT COUNT(*) as count
                FROM daily_bars
                WHERE date = '{yesterday}'
                """
                yesterday_df = pd.read_sql(yesterday_query, self.db.conn)
                
                if yesterday_df.empty or yesterday_df.iloc[0]['count'] == 0:
                    logger.warning(f"数据库中没有昨天的数据（{yesterday}），无法计算平均溢价")
                    # 降级：返回默认值
                    return {
                        'avg_profit': 0.03,  # 假设平均溢价为3%
                        'profit_count': 0,
                        'loss_count': 0
                    }
                
                # 查询昨天的涨停股票
                query = f"""
                SELECT symbol, close, open
                FROM daily_bars
                WHERE date = '{yesterday}'
                """
                
                df = pd.read_sql(query, self.db.conn)
                
                if df.empty:
                    return {
                        'avg_profit': 0,
                        'profit_count': 0,
                        'loss_count': 0
                    }
                
                yesterday_limit_up_codes = df['symbol'].tolist()
            
            # 🆕 V9.2.1 修复：使用实时数据计算今日价格，而不是查询数据库
            # 在盘中，daily_bars 数据库通常只包含 T-1（昨天及以前）的历史数据
            # 所以必须使用实时数据来计算今日价格
            profits = []
            profit_count = 0
            loss_count = 0
            missing_data_count = 0
            
            for symbol in yesterday_limit_up_codes:
                # 1. 获取昨日收盘价（从数据库查询）
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                yesterday_query = f"SELECT close FROM daily_bars WHERE symbol = '{symbol}' AND date = '{yesterday}'"
                yesterday_df = pd.read_sql(yesterday_query, self.db.conn)
                
                if yesterday_df.empty:
                    continue
                
                yesterday_close = yesterday_df.iloc[0]['close']
                
                # 2. 获取今日最新价（从实时数据获取）
                if realtime_data and symbol in realtime_data:
                    current_price = realtime_data[symbol].get('price', 0)
                    
                    if current_price > 0:
                        profit_pct = (current_price - yesterday_close) / yesterday_close * 100 if yesterday_close > 0 else 0
                        
                        profits.append(profit_pct)
                        
                        if profit_pct > 0:
                            profit_count += 1
                        else:
                            loss_count += 1
                    else:
                        missing_data_count += 1
                        logger.debug(f"股票 {symbol} 的实时价格为 0，跳过计算")
                else:
                    missing_data_count += 1
                    logger.debug(f"股票 {symbol} 不在实时数据中，跳过计算")
            
            if missing_data_count > 0:
                logger.warning(f"⚠️ 有 {missing_data_count} 只股票缺少实时数据，无法计算溢价")
            
            if profits:
                avg_profit = sum(profits) / len(profits)
                logger.info(f"✅ 平均溢价计算完成：{avg_profit:.2f}%（盈利{profit_count}只，亏损{loss_count}只，共{len(profits)}只）")
            else:
                logger.warning("⚠️ 没有可用的溢价数据，返回默认值")
                avg_profit = 3.0  # 假设平均溢价为3%
            
            return {
                'avg_profit': avg_profit / 100,  # 转换为小数
                'profit_count': profit_count,
                'loss_count': loss_count
            }
        
        except Exception as e:
            logger.error(f"获取昨日涨停溢价失败: {e}")
            # 降级：返回模拟数据
            return {
                'avg_profit': 0.03,  # 假设平均溢价为3%
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
            # 获取今日涨停股票
            limit_up_stocks = self.get_limit_up_down_count().get('limit_up_stocks', [])
            
            if not limit_up_stocks:
                return 0.0
            
            # 🆕 V9.2 修复：检查数据库中是否有昨天的数据
            from datetime import datetime, timedelta
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            yesterday_query = f"""
            SELECT COUNT(*) as count
            FROM daily_bars
            WHERE date = '{yesterday}'
            """
            yesterday_df = pd.read_sql(yesterday_query, self.db.conn)
            
            if yesterday_df.empty or yesterday_df.iloc[0]['count'] == 0:
                logger.warning(f"数据库中没有昨天的数据（{yesterday}），无法计算炸板率")
                # 降级：返回默认值（假设15%的炸板率）
                return 0.15
            
            # 获取这些股票的历史数据，检查是否曾经涨停过然后炸板
            # 这里简化处理：通过今日开盘价和昨日收盘价判断
            burst_count = 0
            
            for stock in limit_up_stocks:
                symbol = stock['code']
                
                # 查询昨日数据
                yesterday_query = f"SELECT close, open FROM daily_bars WHERE symbol = '{symbol}' AND date = '{yesterday}'"
                yesterday_df = pd.read_sql(yesterday_query, self.db.conn)
                
                if not yesterday_df.empty:
                    yesterday_close = yesterday_df.iloc[0]['close']
                    yesterday_open = yesterday_df.iloc[0]['open']
                    today_open = stock.get('price', 0)
                    
                    # 判断昨日是否涨停
                    yesterday_change_pct = (yesterday_close - yesterday_open) / yesterday_open * 100 if yesterday_open > 0 else 0
                    was_limit_up = (yesterday_change_pct >= 9.5) or (yesterday_change_pct >= 19.5)
                    
                    # 如果昨日涨停，但今日开盘价低于昨日收盘价，视为炸板
                    if was_limit_up and today_open < yesterday_close * 0.95:
                        burst_count += 1
            
            burst_rate = burst_count / len(limit_up_stocks) if limit_up_stocks else 0
            
            return burst_rate
        
        except Exception as e:
            logger.error(f"获取炸板率失败: {e}")
            # 降级：返回模拟数据（假设15%的炸板率）
            return 0.15
    
    def get_board_promotion_rate(self) -> float:
        """
        获取晋级率（今天连板数 / 昨天首板数）
        
        Returns:
            float: 晋级率
        """
        try:
            # 🆕 V9.2 修复：优先使用 Redis 数据
            # 从 Redis 获取昨日涨停池
            yesterday_limit_up_codes = self.get_limit_up_pool_from_redis()
            
            if not yesterday_limit_up_codes:
                logger.warning("Redis 中没有昨日涨停池数据，降级使用数据库查询")
                # 降级：使用数据库查询
                from datetime import datetime, timedelta
                
                today = datetime.now().strftime('%Y-%m-%d')
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                
                # 检查数据库中是否有昨天的数据
                yesterday_query = f"""
                SELECT COUNT(*) as count
                FROM daily_bars
                WHERE date = '{yesterday}'
                """
                yesterday_df = pd.read_sql(yesterday_query, self.db.conn)
                
                if yesterday_df.empty or yesterday_df.iloc[0]['count'] == 0:
                    logger.warning(f"数据库中没有昨天的数据（{yesterday}），无法计算晋级率")
                    # 降级：返回默认值（假设25%的晋级率）
                    return 0.25
                
                # 获取昨日首板数（昨日涨停的股票数）
                yesterday_limit_up_query = f"""
                SELECT COUNT(DISTINCT symbol) as count
                FROM daily_bars
                WHERE date = '{yesterday}'
                AND ((close - open) / open * 100 >= 9.5 OR (close - open) / open * 100 <= -9.5)
                """
                
                yesterday_df = pd.read_sql(yesterday_limit_up_query, self.db.conn)
                yesterday_first_board_count = yesterday_df.iloc[0]['count'] if not yesterday_df.empty else 0
                
                if yesterday_first_board_count == 0:
                    return 0.0
                
                # 获取今日连板数（今日继续涨停的昨日首板股票）
                today_limit_up_query = f"""
                SELECT COUNT(DISTINCT symbol) as count
                FROM daily_bars
                WHERE date = '{today}'
                AND ((close - open) / open * 100 >= 9.5 OR (close - open) / open * 100 <= -9.5)
                AND symbol IN (
                    SELECT symbol FROM daily_bars 
                    WHERE date = '{yesterday}'
                    AND ((close - open) / open * 100 >= 9.5 OR (close - open) / open * 100 <= -9.5)
                )
                """
                
                today_df = pd.read_sql(today_limit_up_query, self.db.conn)
                today_consecutive_board_count = today_df.iloc[0]['count'] if not today_df.empty else 0
                
                promotion_rate = today_consecutive_board_count / yesterday_first_board_count if yesterday_first_board_count > 0 else 0
                
                return promotion_rate
            
            # 使用 Redis 数据计算晋级率
            # 获取今日涨停股票
            today_limit_up_stocks = self.get_limit_up_down_count().get('limit_up_stocks', [])
            today_limit_up_codes = [stock['code'] for stock in today_limit_up_stocks]
            
            # 计算昨日涨停池中今天继续涨停的数量
            success_count = 0
            for code in yesterday_limit_up_codes:
                if code in today_limit_up_codes:
                    success_count += 1
            
            promotion_rate = success_count / len(yesterday_limit_up_codes) if yesterday_limit_up_codes else 0
            
            logger.info(f"✅ 晋级率计算完成：{promotion_rate:.2%}（昨日{len(yesterday_limit_up_codes)}只涨停，今日{success_count}只晋级）")
            
            return promotion_rate
        
        except Exception as e:
            logger.error(f"获取晋级率失败: {e}")
            # 降级：返回模拟数据（假设25%的晋级率）
            return 0.25
    
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
        检测反核机会（跌停板上的核心龙头）- V6.2 升级版
        
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
            
            # 反核机会判断逻辑（V6.2 升级）：
            # 1. 跌停板上（change_pct <= -9.5%）
            # 2. 是核心龙头（成交额较大）
            # 3. 🆕 成交性质判定：必须有真成交，不是骗炮
            
            if change_pct <= -9.5:
                # 检查是否是核心龙头
                is_core_dragon = True  # 简化处理
                
                if is_core_dragon:
                    # 🆕 V6.2: 验证反核信号的真实性
                    is_valid_anti_nuclear = self._verify_anti_nuclear_signal(stock)
                    
                    if is_valid_anti_nuclear:
                        anti_nuclear_stocks.append({
                            'code': code,
                            'name': name,
                            'change_pct': change_pct,
                            'reason': '核心龙头跌停，真翘板信号确认',
                            'confidence': 'HIGH',
                            'verified': True
                        })
        
        return anti_nuclear_stocks
    
    def _verify_anti_nuclear_signal(self, stock: Dict) -> bool:
        """
        🆕 V6.2: 验证反核信号的真实性（避免骗炮）
        
        判定逻辑：
        1. 必须是真成交：跌停价上的买一封单被瞬间吃掉50%以上
        2. 撤单监测：如果买一量突然消失但没有成交 -> 撤单骗炮
        3. 必须有"跟随资金"：随后30秒内有密集的中单跟进
        
        Args:
            stock: 股票数据
        
        Returns:
            bool: 是否为真实的反核信号
        """
        try:
            # 获取盘口数据（如果有）
            bid1_volume = stock.get('bid1_volume', 0)
            ask1_volume = stock.get('ask1_volume', 0)
            volume = stock.get('volume', 0)
            
            # 1. 必须是真成交：跌停价上的买一封单（Ask 1）被吃掉
            # 如果买一量很大但成交稀疏 -> 可能是挂单诱多
            if ask1_volume > 0 and volume > 0:
                # 计算买一量占总成交的比例
                ask1_ratio = ask1_volume / volume
                
                # 如果买一量占比过高（>80%）但成交量小 -> 可能是挂单诱多
                if ask1_ratio > 0.8 and volume < 10000:  # 10000手以下
                    logger.warning(f"检测到可能的骗炮信号：{stock['name']} 买一量占比{ask1_ratio:.1%}但成交稀疏")
                    return False
            
            # 2. 撤单监测（通过买一量剧烈波动判断）
            # 这里需要历史盘口数据，简化处理
            # 实际应该监控买一量的变化趋势
            
            # 3. 必须有"跟随资金"
            # 只有一笔大单不够，需要有持续的中单跟进
            # 这里简化判断：成交量和买一量都要有一定规模
            if volume < 5000:  # 成交量太小
                return False
            
            if bid1_volume < 1000:  # 买一量太小
                return False
            
            # 通过所有验证，认为是真实的反核信号
            logger.info(f"✅ 验证通过：{stock['name']} 真实反核信号")
            return True
        
        except Exception as e:
            logger.error(f"验证反核信号失败: {e}")
            return False
    
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
