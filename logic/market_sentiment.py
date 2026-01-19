"""
市场环境感知模块

判断市场情绪，动态调整策略参数
实现"看天吃饭"功能
"""

import pandas as pd
from datetime import datetime, timedelta
from collections import Counter
from typing import List, Dict, Optional, Tuple, Union
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.data_cleaner import DataCleaner
from logic.review_manager import ReviewManager
import config_system as config

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
    6. 🆕 V10.1：自动挖掘今日主线题材
    7. 🆕 V10.1.1：概念库过期提醒 + 主线聚焦度分析
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
    
    # 🆕 V10.1：概念关键词映射
    CONCEPT_KEYWORDS = {
        'AI': ['人工智能', 'AI', '大模型', 'ChatGPT', '算力', 'CPO', '光模块', '智能', '机器人'],
        '医药': ['医药', '医疗', '生物', '疫苗', '创新药', 'CRO', '医疗器械', '健康'],
        '华为': ['华为', '鸿蒙', '麒麟', '昇腾', '鲲鹏', '海思'],
        '新能源': ['新能源', '光伏', '风电', '储能', '锂电池', '动力电池', '充电桩'],
        '芯片': ['芯片', '半导体', '集成电路', '存储', '晶圆', '封测'],
        '汽车': ['汽车', '新能源车', '智能驾驶', '自动驾驶', '车联网', '汽车电子'],
        '军工': ['军工', '航空', '航天', '雷达', '导弹', '无人机'],
        '消费': ['消费', '白酒', '食品', '饮料', '家电', '零售', '电商'],
        '金融': ['银行', '证券', '保险', '金融', '期货', '信托'],
        '房地产': ['房地产', '地产', '物业', '建筑', '建材'],
        '化工': ['化工', '化学', '石化', '化纤', '聚氨酯'],
        '有色': ['有色', '金属', '铜', '铝', '锂', '稀土', '黄金'],
        '软件': ['软件', '云计算', '大数据', 'SaaS', 'ERP', '互联网'],
        '传媒': ['传媒', '游戏', '影视', '广告', '出版'],
        '教育': ['教育', '培训', '在线教育', '学校'],
        '农业': ['农业', '种业', '农机', '农产品'],
        '环保': ['环保', '水务', '固废', '大气', '节能'],
        '通信': ['通信', '5G', '6G', '光纤', '基站'],
        '电力': ['电力', '电网', '发电', '输电', '配电'],
        '纺织': ['纺织', '服装', '面料', '家纺'],
        '造纸': ['造纸', '纸业', '包装', '印刷'],
    }
    
    def __init__(self):
        self.db = DataManager()
        self.rm = ReviewManager()  # ✅ V11 接入复盘管理器
        self.current_regime = None
        self.market_data = {}
        self.hot_themes = []  # 🆕 V10.1：今日主线
        self.hot_themes_detailed = []  # 🆕 V10.1.1：今日主线（带分数）
        self.concept_map_expired = False  # 🆕 V10.1.1：概念库是否过期
        
        # 🆕 V10.1.1：加载真实的概念映射表
        self.concept_map = self._load_concept_map()
    
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
        [V11 修复] 获取真实的市场最高连板高度
        
        Returns:
            dict: {'max_board': 最高板数, 'date': 日期}
        """
        try:
            stats = self.rm.get_yesterday_stats()
            if stats:
                logger.info(f"✅ 从复盘库获取连板高度: {stats['highest_board']}")
                return {
                    'max_board': stats['highest_board'],
                    'date': stats['date']
                }
            
            # 如果库里没有，尝试紧急运行一次复盘(默认昨天)
            logger.info("🔄 复盘库无数据，尝试紧急运行复盘...")
            self.rm.run_daily_review()
            stats = self.rm.get_yesterday_stats()
            
            if stats:
                logger.info(f"✅ 紧急复盘成功，获取连板高度: {stats['highest_board']}")
                return {'max_board': stats['highest_board'], 'date': stats['date']}
                
            logger.warning("⚠️ 无法获取连板高度数据")
            return {'max_board': 0, 'date': '未知'}
        
        except Exception as e:
            logger.error(f"获取连板高度异常: {e}")
            return {'max_board': 0, 'date': '异常'}
    
    def get_prev_limit_up_profit(self):
        """
        [V11 修复] 计算真实的昨日涨停溢价 (赚钱效应)
        
        Returns:
            dict: {
                'avg_profit': 平均溢价,
                'profit_count': 盈利家数,
                'loss_count': 亏损家数
            }
            或 None（数据不足时）
        """
        try:
            # 🆕 V11.1 检查是否在可靠时间之后（避免竞价时段溢价跳变）
            from logic.market_status import get_market_status_checker
            market_checker = get_market_status_checker()
            current_time = market_checker.get_current_time()
            current_time_minutes = current_time.hour * 60 + current_time.minute
            
            # 如果在 9:25 之前，返回 None（数据不可靠）
            if current_time_minutes < config.MIN_RELIABLE_TIME:
                logger.info(f"⏰ 当前时间 {current_time} 未到 9:25，溢价数据不可靠，返回 None")
                return None
            
            stats = self.rm.get_yesterday_stats()
            if not stats or not stats.get('limit_up_list'):
                logger.warning("⚠️ 昨日涨停溢价数据未实现，返回 None")
                return None
            
            # 1. 获取昨日涨停股代码
            yesterday_codes = stats['limit_up_list'][:50]  # 样本取前50只即可
            
            # 2. 获取这些股票的实时行情
            # 💡 这里复用 DataManager 的极速接口
            prices = self.db.get_fast_price(yesterday_codes)
            
            if not prices:
                logger.warning("⚠️ 无法获取昨日涨停股的实时行情")
                return None
                
            # 3. 计算平均涨幅
            total_pct = 0
            count = 0
            profit_count = 0
            loss_count = 0
            
            for code, data in prices.items():
                price = data.get('now', 0)
                pre_close = data.get('close', 0)
                if pre_close > 0:
                    pct = (price - pre_close) / pre_close * 100
                    total_pct += pct
                    count += 1
                    
                    if pct > 0:
                        profit_count += 1
                    elif pct < 0:
                        loss_count += 1
            
            if count == 0:
                logger.warning("⚠️ 无法计算昨日涨停溢价（没有有效价格数据）")
                return None
            
            avg_profit = total_pct / count
            logger.info(f"✅ 真实昨日涨停溢价计算完成: {avg_profit:.2f}% (样本数: {count})")
            
            return {
                'avg_profit': round(avg_profit, 2),
                'profit_count': profit_count,
                'loss_count': loss_count
            }
            
        except Exception as e:
            logger.error(f"计算昨日涨停溢价异常: {e}")
            return None
    
    def get_market_regime(self, top_stocks: Optional[List[Dict]] = None):
        """
        判断市场情绪（进攻/防守/震荡）
        
        Args:
            top_stocks: 强势股列表（可选，用于主线挖掘）
        
        Returns:
            dict: {
                'regime': 市场状态,
                'description': 状态描述,
                'strategy': 策略建议,
                'market_data': 市场数据,
                'hot_themes': 今日主线（V10.1新增）
            }
        """
        try:
            # 获取市场数据
            limit_up_down = self.get_limit_up_down_count()
            prev_profit = self.get_prev_limit_up_profit()
            
            limit_up_count = limit_up_down.get('limit_up_count', 0)
            limit_down_count = limit_up_down.get('limit_down_count', 0)
            avg_profit = prev_profit.get('avg_profit', 0) if prev_profit else 0
            
            # 🛑 V9.2 新增：恐慌熔断机制 (Panic Circuit Breaker)
            # 1. 绝对恐慌：跌停比涨停多 → 直接降级为"防守模式"
            if limit_down_count > limit_up_count:
                regime = self.REGIME_BEAR_DEFENSE
                description = "暴雨：极度危险，空仓观望"
                strategy = "只卖不买，空仓观望，等待情绪修复"
            
            # 2. 局部恐慌：跌停家数超过 30 家 → 最高只能是"震荡模式"
            elif limit_down_count > 30:
                regime = self.REGIME_CHAOS
                description = "多云：分歧巨大，谨慎操作"
                strategy = "轻仓试错，控制仓位，只做最高板"
            
            # 3. 正常判断：根据涨停家数和昨日溢价判断市场状态
            elif limit_up_count >= self.BULL_LIMIT_UP_COUNT and avg_profit >= self.BULL_PREV_PROFIT:
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
            
            # 🆕 V10.1：挖掘今日主线
            hot_themes = []
            hot_themes_detailed = []
            if top_stocks:
                hot_themes_detailed = self._analyze_hot_themes(top_stocks)
                hot_themes = [theme for theme, score in hot_themes_detailed]
                self.hot_themes = hot_themes
                self.hot_themes_detailed = hot_themes_detailed
            
            self.market_data = {
                'limit_up_count': limit_up_count,
                'limit_down_count': limit_down_count,
                'prev_profit': avg_profit,
                'max_board': self.get_consecutive_board_height().get('max_board', 0) if self.get_consecutive_board_height() else 0,
                'hot_themes': hot_themes,  # 🆕 V10.1
                'hot_themes_detailed': hot_themes_detailed  # 🆕 V10.1.1：带分数
            }
            
            # ==========================================
            # 🔥 V10.1.7 [新增] 静态风险预警 (Static Warning)
            # ==========================================
            static_warning = ""
            
            # 计算市场情绪分数（基于涨停家数和昨日溢价）
            # 分数范围：0-100
            score = 0
            if limit_up_count > 0:
                # 涨停家数贡献（最高50分）
                score += min(limit_up_count / 2, 50)
            # 昨日溢价贡献（最高50分）
            score += min(avg_profit * 1000, 50)
            score = min(score, 100)
            
            # 计算恶性炸板率
            mal_rate = 0
            try:
                from logic.market_cycle import MarketCycle
                mc = MarketCycle()
                limit_data = mc.get_limit_up_down_count()
                limit_up_stocks = limit_data.get('limit_up_stocks', [])
                
                benign_count = 0
                malignant_count = 0
                
                for stock in limit_up_stocks:
                    if stock.get('is_exploded', False):
                        change_pct = stock.get('change_pct', 0)
                        # 恶性炸板：回撤超过 5%（A杀风险）
                        if change_pct < 5:
                            malignant_count += 1
                        else:
                            benign_count += 1
                
                total_zhaban = benign_count + malignant_count
                if total_zhaban > 0:
                    mal_rate = malignant_count / total_zhaban
                
                mc.close()
            except Exception as e:
                logger.warning(f"计算恶性炸板率失败: {e}")
                mal_rate = 0
            
            # 场景1: 高位分歧 (最危险) -> 市场过热 + 炸板率高
            if score > 70 and mal_rate > config.THRESHOLD_HIGH_MALIGNANT_RATE:
                static_warning = "⚠️ 警惕：市场过热且炸板率高，防止退潮！"
            
            # 场景2: 冰点杀跌 -> 市场极冷 + 炸板率高
            elif score < 30 and mal_rate > config.THRESHOLD_MALIGNANT_RATE:
                static_warning = "❄️ 警惕：冰点期且亏钱效应剧烈，严禁试错！"
            
            # 场景3: 普涨高潮 -> 市场极热 + 炸板率低 (安全)
            elif score > 80 and mal_rate < config.THRESHOLD_LOW_MALIGNANT_RATE:
                static_warning = "🔥 提示：情绪一致性高潮，持筹盛宴。"
            
            # 注入到数据包
            self.market_data['static_warning'] = static_warning
            self.market_data['score'] = score
            self.market_data['malignant_zhaban_rate'] = mal_rate
            
            return {
                'regime': regime,
                'description': description,
                'strategy': strategy,
                'market_data': self.market_data,
                'hot_themes': hot_themes,  # 🆕 V10.1
                'hot_themes_detailed': hot_themes_detailed  # 🆕 V10.1.1：带分数
            }
        
        except Exception as e:
            logger.error(f"判断市场情绪失败: {e}")
            return {
                'regime': self.REGIME_CHAOS,
                'description': "无法判断市场情绪",
                'strategy': "保守操作",
                'market_data': {},
                'hot_themes': [],
                'hot_themes_detailed': []
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
        # 🆕 V9.2 更新：根据市场数据返回更准确的天气图标
        if not self.market_data:
            return "❓ 未知"
        
        limit_up_count = self.market_data.get('limit_up_count', 0)
        limit_down_count = self.market_data.get('limit_down_count', 0)
        
        # 绝对恐慌：跌停比涨停多 → 暴雨
        if limit_down_count > limit_up_count:
            return "⛈️ 暴雨（极度危险）"
        
        # 局部恐慌：跌停家数超过 30 家 → 多云
        elif limit_down_count > 30:
            return "🌥️ 多云（分歧巨大）"
        
        # 正常判断
        elif self.current_regime == self.REGIME_BULL_ATTACK:
            return "☀️ 晴天（进攻）"
        elif self.current_regime == self.REGIME_BEAR_DEFENSE:
            return "🌧️ 雨天（防守）"
        else:
            return "☁️ 多云（震荡）"
    
    def generate_ai_context(self, top_stocks: Optional[List[Dict]] = None) -> Dict:
        """
        🆕 V10.1：生成 AI 上下文，让 AI 能够读取今日主线
        🆕 V10.1.1：包含主线聚焦度信息（带分数）
        
        Args:
            top_stocks: 强势股列表（可选）
        
        Returns:
            dict: AI 上下文信息
        """
        try:
            # 获取市场情绪
            regime_info = self.get_market_regime(top_stocks)
            
            # 🆕 V10.1.1：格式化带分数的主线信息
            hot_themes_detailed = regime_info.get('hot_themes_detailed', [])
            if hot_themes_detailed:
                # 格式化成 AI 易读的字符串
                themes_str = ", ".join([f"{t[0]}({t[1]}分)" for t in hot_themes_detailed])
                
                # 🆕 V10.1.1：判断主线聚焦度
                if len(hot_themes_detailed) >= 2:
                    top_score = hot_themes_detailed[0][1]
                    second_score = hot_themes_detailed[1][1]
                    score_gap = top_score - second_score
                    
                    # 分数差距小且分数高 → 合力强
                    if score_gap < 10 and top_score >= 30:
                        focus_level = "主线明确，合力强"
                    # 分数差距大 → 单一主线
                    elif score_gap >= 20:
                        focus_level = "单一主线，聚焦度高"
                    # 分数低且分散 → 合力弱
                    elif top_score < 20:
                        focus_level = "主线分散，合力弱"
                    else:
                        focus_level = "主线一般"
                else:
                    focus_level = "主线不明确"
                
                themes_with_focus = f"{themes_str}（{focus_level}）"
            else:
                themes_with_focus = "无明显主线"
            
            # ==========================================
            # 🔥 V10.1.6 [新增] 龙头身份认证协议 (Leader Identification)
            # ==========================================
            
            # 1. 建立主线秩序：找到每个概念下的"最高板"
            # 格式: {'新能源': {'name': '天龙集团', 'height': 3}, ...}
            theme_leaders = {} 
            
            if top_stocks:
                for stock in top_stocks:
                    concepts = stock.get('concept_tags', [])
                    # 解析连板高度 (如 "3连板" -> 3, "首板" -> 1)
                    status = stock.get('lianban_status', '首板')
                    try:
                        if '连板' in status:
                            height = int(status[0])
                        else:
                            height = 1
                    except:
                        height = 1
                        
                    for c in concepts:
                        # 记录该概念下的最高身位
                        current_leader = theme_leaders.get(c, {'height': -1})
                        if height > current_leader['height']:
                            theme_leaders[c] = {'name': stock['name'], 'height': height}
                        # 如果高度一样，优先选封单额大的或者竞价强的 (此处简化为选涨幅大的)
                        elif height == current_leader['height']:
                            change_pct = stock.get('change_pct', 0) or stock.get('涨跌幅', 0)
                            if change_pct > 9.5: # 涨停优先
                                theme_leaders[c] = {'name': stock['name'], 'height': height}
                
                # 2. 标记个股身份：你是龙，还是虫？
                for stock in top_stocks:
                    concepts = stock.get('concept_tags', [])
                    is_leader = False
                    my_leader = "无"
                    
                    # 只要它是任何一个概念的最高板，它就是龙头
                    for c in concepts:
                        leader_info = theme_leaders.get(c)
                        if leader_info:
                            if stock['name'] == leader_info['name']:
                                is_leader = True
                            else:
                                my_leader = leader_info['name']
                    
                    # 注入身份字段
                    if is_leader:
                        stock['role'] = "🐲 龙头 (真龙)"
                    else:
                        stock['role'] = f"🐕 跟风 (大哥是: {my_leader})"
            
            # ==========================================
            # 🔥 V10.1.6 逻辑结束
            # ==========================================
            
            # 构建上下文
            context = {
                'market_weather': self.get_market_weather_icon(),
                'regime': regime_info.get('regime', ''),
                'description': regime_info.get('description', ''),
                'strategy': regime_info.get('strategy', ''),
                'market_data': regime_info.get('market_data', {}),
                'hot_themes': regime_info.get('hot_themes', []),  # 🆕 V10.1：今日主线（仅名称）
                'hot_themes_detailed': themes_with_focus,  # 🆕 V10.1.1：今日主线（带分数 + 聚焦度）
                'concept_map_expired': self.concept_map_expired,  # 🆕 V10.1.1：概念库是否过期
                'theme_leaders': theme_leaders  # 🆕 V10.1.6：龙头信息
            }
            
            return context
        
        except Exception as e:
            logger.error(f"生成 AI 上下文失败: {e}")
            return {
                'market_weather': '未知',
                'regime': self.REGIME_CHAOS,
                'description': '无法判断市场情绪',
                'strategy': '保守操作',
                'market_data': {},
                'hot_themes': [],
                'hot_themes_detailed': '无明显主线',
                'concept_map_expired': False
            }
    
    def _load_concept_map(self) -> Dict:
        """
        🆕 V10.1.1：加载概念映射表（包含过期提醒）
        
        Returns:
            dict: 股票代码 -> 概念列表的映射
        """
        import os
        import json
        import time
        
        concept_map_path = "data/concept_map.json"
        
        if os.path.exists(concept_map_path):
            try:
                # 🆕 V10.1.1：检查文件龄期
                file_time = os.path.getmtime(concept_map_path)
                days_old = (time.time() - file_time) / (24 * 3600)
                
                if days_old > 7:
                    self.concept_map_expired = True
                    logger.warning(f"⚠️ [警告] 概念库已过期 {int(days_old)} 天！建议运行 `python scripts/generate_concept_map.py` 更新。")
                else:
                    self.concept_map_expired = False
                
                with open(concept_map_path, 'r', encoding='utf-8') as f:
                    concept_map = json.load(f)
                logger.info(f"✅ 加载概念映射表成功，覆盖 {len(concept_map)} 只股票（{int(days_old)} 天前更新）")
                return concept_map
            except Exception as e:
                logger.warning(f"读取概念映射表失败: {e}")
        
        self.concept_map_expired = True
        logger.warning("⚠️ 概念映射表不存在，将使用名称推断法")
        return {}
    
    def _get_concept_coverage(self) -> Dict:
        """
        🆕 V10.1.5：获取概念库覆盖率信息
        
        Returns:
            dict: 包含覆盖率信息的字典
                - covered_count: 已覆盖股票数量
                - total_count: 市场总股票数量
                - coverage_rate: 覆盖率（百分比）
                - uncovered_count: 未覆盖股票数量
        """
        try:
            import akshare as ak
            
            # 获取概念库覆盖的股票数量
            covered_count = len(self.concept_map)
            
            # 获取市场总股票数量
            stock_list_df = ak.stock_info_a_code_name()
            total_count = len(stock_list_df)
            
            # 计算覆盖率
            coverage_rate = (covered_count / total_count * 100) if total_count > 0 else 0
            uncovered_count = total_count - covered_count
            
            result = {
                'covered_count': covered_count,
                'total_count': total_count,
                'coverage_rate': round(coverage_rate, 2),
                'uncovered_count': uncovered_count
            }
            
            logger.info(f"📊 概念库覆盖率: {coverage_rate:.2f}% ({covered_count}/{total_count})")
            return result
            
        except Exception as e:
            logger.warning(f"获取概念库覆盖率失败: {e}")
            return {
                'covered_count': len(self.concept_map),
                'total_count': 0,
                'coverage_rate': 0,
                'uncovered_count': 0
            }
    
    def _analyze_hot_themes(self, top_stocks: List[Dict]) -> List[Tuple[str, int]]:
        """
        🔥 [V10.1.1 深化逻辑] 挖掘今日主线题材（加权评分版）
        使用加权评分替代简单计数，优先识别涨停/连板股票的概念
        
        Args:
            top_stocks: 强势股列表（涨停或高涨幅股票）
            
        Returns:
            list: 今日主线题材列表（Top 3），格式为 [(概念, 分数), ...]
        """
        if not top_stocks:
            return []
        
        # 🆕 V10.1.1：使用加权评分
        theme_scores = {}
        
        for stock in top_stocks:
            code = stock.get('code', '')
            name = stock.get('name', '')
            
            # 获取该股票的概念列表
            concepts = self.get_stock_concepts(code, name)
            
            if concepts:
                # 同时把概念注入到 stock 对象里，方便 UI 显示
                stock['concept_tags'] = concepts[:3]  # 只取前3个核心概念
                
                # 🔥 核心权重算法：
                # 涨停板/连板 = 10分
                # 涨幅 > 7% = 5分
                # 涨幅 > 3% = 1分
                weight = 1
                
                # 判断是否涨停
                change_pct = stock.get('change_pct', 0)
                is_limit_up = change_pct >= 9.5
                
                # 判断是否连板
                lianban_count = stock.get('lianban_count', 0)
                
                if is_limit_up or lianban_count > 0:
                    weight = 10  # 涨停板或连板
                elif change_pct > 7.0:
                    weight = 5   # 强势股
                elif change_pct > 3.0:
                    weight = 1   # 普通上涨
                
                for concept in concepts:
                    # 过滤掉太宽泛的概念
                    exclude_concepts = ['融资融券', '深股通', '标准普尔', 'MSCI', '富时罗素', '标普道琼斯', '沪股通']
                    if concept in exclude_concepts:
                        continue
                    
                    # 累加权重
                    theme_scores[concept] = theme_scores.get(concept, 0) + weight
        
        # 按分数排序，而不是按数量排序
        if not theme_scores:
            return []
        
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 🆕 V10.1.1：返回 (名字, 分数) 而不只是名字
        return sorted_themes[:3]
    
    def get_stock_concepts(self, code: str, name: str) -> List[str]:
        """
        🆕 V10.1.1：获取股票概念（优先查表，兜底推断）
        
        Args:
            code: 股票代码
            name: 股票名称
            
        Returns:
            list: 概念列表
        """
        # 1. 优先查表（使用真实的 concept_map.json）
        if code in self.concept_map:
            concepts = self.concept_map[code]
            # 过滤掉太宽泛的概念
            exclude_concepts = ['融资融券', '深股通', '标准普尔', 'MSCI', '富时罗素', '标普道琼斯', '沪股通']
            filtered_concepts = [c for c in concepts if c not in exclude_concepts]
            return filtered_concepts if filtered_concepts else []
        
        # 2. 兜底：使用名称推断法
        concepts = []
        for theme, keywords in self.CONCEPT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name:
                    if theme not in concepts:
                        concepts.append(theme)
                    break
        
        # 如果没有匹配到概念，返回空列表（不再返回"其他"）
        return concepts
    
    def get_market_sentiment_score(self, top_stocks: Optional[List[Dict]] = None) -> Dict[str, Union[int, str]]:
        """
        [V16 新增] 获取市场情绪分数和状态，用于环境熔断
        
        Args:
            top_stocks: 强势股列表（可选，用于主线挖掘）
        
        Returns:
            dict: {
                'score': 市场情绪分数 (0-100),
                'status': 市场状态 ('主升', '退潮', '震荡', '冰点'),
                'description': 状态描述,
                'limit_up_count': 涨停家数,
                'limit_down_count': 跌停家数,
                'prev_profit': 昨日涨停溢价,
                'malignant_zhaban_rate': 恶性炸板率
            }
        """
        try:
            # 获取市场状态
            regime_info = self.get_market_regime(top_stocks)
            market_data = regime_info.get('market_data', {})
            regime = regime_info.get('regime', self.REGIME_CHAOS)
            
            # 获取市场情绪分数
            score = market_data.get('score', 50)
            
            # 映射 regime 到 V16 需要的状态
            status_mapping = {
                self.REGIME_BULL_ATTACK: '主升',
                self.REGIME_BEAR_DEFENSE: '退潮',
                self.REGIME_CHAOS: '震荡'
            }
            
            # 特殊处理：如果分数 < 20，强制设为"冰点"
            if score < 20:
                status = '冰点'
            else:
                status = status_mapping.get(regime, '震荡')
            
            return {
                'score': score,
                'status': status,
                'description': regime_info.get('description', '未知'),
                'limit_up_count': market_data.get('limit_up_count', 0),
                'limit_down_count': market_data.get('limit_down_count', 0),
                'prev_profit': market_data.get('prev_profit', 0),
                'malignant_zhaban_rate': market_data.get('malignant_zhaban_rate', 0)
            }
        
        except Exception as e:
            logger.error(f"获取市场情绪分数失败: {e}")
            # 返回默认值
            return {
                'score': 50,
                'status': '震荡',
                'description': '无法判断市场情绪',
                'limit_up_count': 0,
                'limit_down_count': 0,
                'prev_profit': 0,
                'malignant_zhaban_rate': 0
            }
    
    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()


# 别名，保持向后兼容
MarketSentimentIndexCalculator = MarketSentiment