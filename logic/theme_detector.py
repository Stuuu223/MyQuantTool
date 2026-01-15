"""
主线识别模块

自动识别市场主线板块，让系统知道"为什么涨"
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.data_cleaner import DataCleaner

logger = get_logger(__name__)


class ThemeDetector:
    """
    主线识别器
    
    功能：
    1. 自动识别涨停股票的共性概念
    2. 计算板块热度
    3. 识别板块龙头
    4. 提供主线投资建议
    """
    
    # 概念关键词映射（简化版，实际应该从数据库或API获取）
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
        """初始化主线识别器"""
        self.db = DataManager()
        self.current_theme = None
        self.theme_history = []
    
    def analyze_main_theme(self, limit_up_stocks: List[Dict]) -> Dict:
        """
        分析主线板块
        
        Args:
            limit_up_stocks: 涨停股票列表
        
        Returns:
            dict: {
                'main_theme': 主线板块,
                'theme_heat': 主线热度,
                'theme_stocks': 主线板块股票,
                'leader': 龙头股票,
                'all_themes': 所有板块统计,
                'suggestion': 投资建议
            }
        """
        try:
            if not limit_up_stocks:
                return {
                    'main_theme': '未知',
                    'theme_heat': 0,
                    'theme_stocks': [],
                    'leader': None,
                    'all_themes': {},
                    'suggestion': '暂无涨停股票，无法识别主线'
                }
            
            # 1. 获取股票概念信息
            stock_concepts = self._get_stock_concepts(limit_up_stocks)
            
            # 2. 统计板块热度
            theme_stats = self._calculate_theme_heat(stock_concepts)
            
            if not theme_stats:
                return {
                    'main_theme': '未知',
                    'theme_heat': 0,
                    'theme_stocks': [],
                    'leader': None,
                    'all_themes': {},
                    'suggestion': '无法识别板块概念'
                }
            
            # 3. 找出主线板块
            main_theme = max(theme_stats, key=lambda x: theme_stats[x]['count'])
            main_theme_info = theme_stats[main_theme]
            
            # 4. 识别龙头
            leader = self._identify_leader(main_theme_info['stocks'])
            
            # 5. 生成投资建议
            suggestion = self._generate_suggestion(main_theme, main_theme_info, leader)
            
            result = {
                'main_theme': main_theme,
                'theme_heat': main_theme_info['heat'],
                'theme_stocks': main_theme_info['stocks'],
                'leader': leader,
                'all_themes': theme_stats,
                'suggestion': suggestion
            }
            
            # 记录主线历史
            self.current_theme = main_theme
            self._record_theme_history(result)
            
            return result
        
        except Exception as e:
            logger.error(f"分析主线板块失败: {e}")
            return {
                'main_theme': '未知',
                'theme_heat': 0,
                'theme_stocks': [],
                'leader': None,
                'all_themes': {},
                'suggestion': '分析主线失败'
            }
    
    def _get_stock_concepts(self, limit_up_stocks: List[Dict]) -> List[Dict]:
        """
        获取股票概念信息
        
        Args:
            limit_up_stocks: 涨停股票列表
        
        Returns:
            list: 包含概念信息的股票列表
        """
        stock_concepts = []
        
        for stock in limit_up_stocks:
            code = stock.get('code', '')
            name = stock.get('name', '')
            
            # 获取股票概念（简化处理，实际应该从数据库或API获取）
            concepts = self._get_concepts_from_name(name)
            
            stock_concepts.append({
                'code': code,
                'name': name,
                'concepts': concepts,
                'price': stock.get('price', 0),
                'change_pct': stock.get('change_pct', 0)
            })
        
        return stock_concepts
    
    def _get_concepts_from_name(self, name: str) -> List[str]:
        """
        从股票名称推断概念（简化版）
        
        Args:
            name: 股票名称
        
        Returns:
            list: 概念列表
        """
        concepts = []
        
        for theme, keywords in self.CONCEPT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name:
                    if theme not in concepts:
                        concepts.append(theme)
                    break
        
        # 如果没有匹配到概念，标记为"其他"
        if not concepts:
            concepts.append('其他')
        
        return concepts
    
    def _calculate_theme_heat(self, stock_concepts: List[Dict]) -> Dict:
        """
        计算板块热度
        
        Args:
            stock_concepts: 包含概念信息的股票列表
        
        Returns:
            dict: 板块热度统计
        """
        theme_stats = defaultdict(lambda: {
            'count': 0,
            'stocks': [],
            'total_count': 0  # 该板块在市场中的总股票数（简化处理）
        })
        
        # 统计每个板块的涨停股票
        for stock in stock_concepts:
            for concept in stock.get('concepts', []):
                theme_stats[concept]['count'] += 1
                theme_stats[concept]['stocks'].append(stock)
        
        # 计算板块热度（涨停家数 / 板块总家数）
        # 这里简化处理，假设每个板块有 100 只股票
        for theme, stats in theme_stats.items():
            stats['total_count'] = 100  # 简化
            stats['heat'] = stats['count'] / stats['total_count']
        
        return dict(theme_stats)
    
    def _identify_leader(self, theme_stocks: List[Dict]) -> Optional[Dict]:
        """
        识别板块龙头
        
        Args:
            theme_stocks: 板块股票列表
        
        Returns:
            dict: 龙头股票信息
        """
        if not theme_stocks:
            return None
        
        # 简化处理：选择涨幅最大的作为龙头
        # 实际应该考虑涨停时间、成交额、市值等因素
        leader = max(theme_stocks, key=lambda x: x.get('change_pct', 0))
        
        return {
            'code': leader['code'],
            'name': leader['name'],
            'price': leader['price'],
            'change_pct': leader['change_pct'],
            'type': '龙一'
        }
    
    def _generate_suggestion(self, main_theme: str, theme_info: Dict, leader: Optional[Dict]) -> str:
        """
        生成投资建议
        
        Args:
            main_theme: 主线板块
            theme_info: 板块信息
            leader: 龙头股票
        
        Returns:
            str: 投资建议
        """
        heat = theme_info['heat']
        count = theme_info['count']
        
        if heat > 0.1:  # 热度 > 10%
            suggestion = f"🔥【{main_theme}】主线爆发！涨停{count}只，热度{heat:.1%}。"
            if leader:
                suggestion += f"龙头：{leader['name']}（{leader['change_pct']:.1%}）。"
            suggestion += "建议：优先关注该板块前排，放弃其他板块。"
        elif heat > 0.05:  # 热度 > 5%
            suggestion = f"⚡【{main_theme}】主线活跃。涨停{count}只，热度{heat:.1%}。"
            if leader:
                suggestion += f"龙头：{leader['name']}（{leader['change_pct']:.1%}）。"
            suggestion += "建议：可适当关注该板块前排。"
        else:
            suggestion = f"📊【{main_theme}】主线较弱。涨停{count}只，热度{heat:.1%}。"
            suggestion += "建议：谨慎操作，观察板块持续性。"
        
        return suggestion
    
    def _record_theme_history(self, theme_info: Dict):
        """
        记录主线历史
        
        Args:
            theme_info: 主线信息
        """
        from datetime import datetime
        
        record = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'theme': theme_info['main_theme'],
            'heat': theme_info['theme_heat'],
            'leader': theme_info['leader']['name'] if theme_info['leader'] else None
        }
        
        self.theme_history.append(record)
        
        # 保留最近 90 天的历史
        if len(self.theme_history) > 90:
            self.theme_history = self.theme_history[-90:]
    
    def get_theme_history(self, days: int = 30) -> List[Dict]:
        """
        获取主线历史
        
        Args:
            days: 获取最近多少天的历史
        
        Returns:
            list: 主线历史列表
        """
        return self.theme_history[-days:]
    
    def get_theme_summary(self) -> str:
        """
        获取主线总结
        
        Returns:
            str: 主线总结文本
        """
        if not self.theme_history:
            return "暂无主线历史数据"
        
        # 统计各主线出现的次数
        theme_count = Counter([record['theme'] for record in self.theme_history])
        
        summary = f"## 主线统计（最近{len(self.theme_history)}天）\n\n"
        
        for theme, count in theme_count.most_common(10):
            summary += f"- {theme}: {count} 天\n"
        
        return summary
    
    def predict_rotation(self, 
                        current_theme: str, 
                        theme_heat: float, 
                        theme_sentiment: str = 'UNKNOWN',
                        theme_days: int = 1,
                        all_themes: Dict = None) -> Dict:
        """
        预测板块轮动（V6.2 升级版）
        
        功能：
        1. 高低切检测：当主线连续涨了3天且高标股出现炸板时，提示切换风险
        2. 资金流向预测：监控板块资金净流出，提示轮动方向
        3. 低位滞涨板块扫描：识别可能承接资金的低位板块
        4. 🆕 轮动确认窗口（Hysteresis Window）：避免假摔导致的踏空
        
        Args:
            current_theme: 当前主线板块
            theme_heat: 主线热度（0-1）
            theme_sentiment: 主线情绪（'STRONG', 'DIVERGENCE', 'WEAK'）
            theme_days: 主线持续天数
            all_themes: 所有板块的统计信息
        
        Returns:
            dict: {
                'rotation_signal': 'HOLD' | 'HOLD_AND_WATCH' | 'WATCH_LOW_SECTOR' | 'SWITCH_RISK' | 'ROTATE_NOW',
                'rotation_reason': '轮动原因',
                'target_sectors': ['目标板块1', '目标板块2'],
                'strategy': '操作建议',
                'hysteresis_days': int  # 观察期天数
            }
        """
        try:
            rotation_signal = 'HOLD'
            rotation_reason = ''
            target_sectors = []
            strategy = ''
            hysteresis_days = 0
            
            # 🆕 V6.2: 轮动确认窗口逻辑
            # 主线分歧的第一天，不急着切换，而是进入"观察期"
            if theme_days >= 3 and theme_sentiment == 'DIVERGENCE':
                # 检查是否是第一次分歧
                divergence_count = self._count_recent_divergence(current_theme)
                
                if divergence_count == 1:
                    # 第一次分歧：进入观察期，不要急着切
                    rotation_signal = 'HOLD_AND_WATCH'
                    rotation_reason = f"{current_theme}首次分歧，可能是'空中加油'，进入观察期"
                    strategy = f"锁仓观察，等待确认。如果次日龙头无法反包，则准备切换"
                    hysteresis_days = 1
                elif divergence_count >= 2:
                    # 连续2天分歧：确认切换
                    # 但还需要检查低位板块是否有承接
                    new_sector_strength = self._check_new_sector_strength(all_themes, current_theme)
                    
                    if new_sector_strength >= 2:  # 低位板块有2只以上首板
                        rotation_signal = 'ROTATE_NOW'
                        rotation_reason = f"{current_theme}连续{divergence_count}天分歧且无法修复，确认切换"
                        strategy = f"果断切换到低位板块，避免踏空"
                        
                        # 扫描低位滞涨板块
                        if all_themes:
                            low_sectors = self._find_low_sectors(all_themes, current_theme)
                            target_sectors = low_sectors[:3]
                    else:
                        rotation_signal = 'HOLD_AND_WATCH'
                        rotation_reason = f"{current_theme}分歧但低位板块无承接，继续观察"
                        strategy = f"低位板块未启动，继续持有主线，等待明确信号"
                        hysteresis_days = divergence_count
            
            # 2. 资金流向预测（模拟）
            # 实际实现需要获取资金流向数据
            elif theme_heat > 0.15 and theme_sentiment == 'STRONG':
                # 主线热度极高，高潮期风险
                rotation_signal = 'SWITCH_RISK'
                rotation_reason = f"{current_theme}进入高潮期（热度{theme_heat:.1%}），注意资金回流风险"
                strategy = f"只卖不买，等待{current_theme}分歧后的新机会"
            
            # 3. 主线刚启动，继续持有
            elif theme_days <= 2 and theme_sentiment == 'STRONG':
                rotation_signal = 'HOLD'
                rotation_reason = f"{current_theme}启动初期，情绪强势，继续持有"
                strategy = f"坚定持有{current_theme}前排，关注补涨机会"
            
            # 4. 主线弱势，观望
            elif theme_heat < 0.05 or theme_sentiment == 'WEAK':
                rotation_signal = 'WATCH_LOW_SECTOR'
                rotation_reason = f"{current_theme}热度不足（{theme_heat:.1%}），情绪弱势"
                strategy = f"控制仓位，观察新题材启动，避免接盘"
                
                # 扫描低位滞涨板块
                if all_themes:
                    low_sectors = self._find_low_sectors(all_themes, current_theme)
                    target_sectors = low_sectors[:3]
            
            return {
                'rotation_signal': rotation_signal,
                'rotation_reason': rotation_reason,
                'target_sectors': target_sectors,
                'strategy': strategy,
                'current_theme': current_theme,
                'theme_days': theme_days,
                'theme_heat': theme_heat,
                'theme_sentiment': theme_sentiment,
                'hysteresis_days': hysteresis_days
            }
        
        except Exception as e:
            logger.error(f"预测板块轮动失败: {e}")
            return {
                'rotation_signal': 'HOLD',
                'rotation_reason': '预测失败',
                'target_sectors': [],
                'strategy': '保持现有策略'
            }
    
    def _find_low_sectors(self, all_themes: Dict, exclude_theme: str) -> List[str]:
        """
        查找低位滞涨板块
        
        Args:
            all_themes: 所有板块统计信息
            exclude_theme: 要排除的主线板块
        
        Returns:
            list: 低位板块列表（按热度排序）
        """
        low_sectors = []
        
        for theme, info in all_themes.items():
            # 排除主线板块
            if theme == exclude_theme:
                continue
            
            # 排除"其他"板块
            if theme == '其他':
                continue
            
            heat = info.get('heat', 0)
            count = info.get('count', 0)
            
            # 低位板块定义：热度较低但有涨停股票
            if 0.01 <= heat <= 0.05 and count >= 1:
                low_sectors.append({
                    'theme': theme,
                    'heat': heat,
                    'count': count
                })
        
        # 按热度排序（取热度相对较高的低位板块）
        low_sectors.sort(key=lambda x: x['heat'], reverse=True)
        
        return [s['theme'] for s in low_sectors]
    
    def _count_recent_divergence(self, theme: str) -> int:
        """
        🆕 V6.2: 统计最近的主线分歧次数
        
        Args:
            theme: 主线板块名称
        
        Returns:
            int: 最近的分歧次数
        """
        if not self.theme_history:
            return 0
        
        # 查看最近3天的主线历史
        recent_history = self.theme_history[-3:]
        
        divergence_count = 0
        for record in recent_history:
            if record['theme'] == theme:
                # 简化判断：如果热度低于0.1，认为是分歧
                if record['heat'] < 0.1:
                    divergence_count += 1
        
        return divergence_count
    
    def _check_new_sector_strength(self, all_themes: Dict, exclude_theme: str) -> int:
        """
        🆕 V6.2: 检查新板块的强度（低位板块的首板数量）
        
        Args:
            all_themes: 所有板块统计信息
            exclude_theme: 要排除的主线板块
        
        Returns:
            int: 低位板块的首板数量
        """
        if not all_themes:
            return 0
        
        new_sector_count = 0
        
        for theme, info in all_themes.items():
            # 排除主线板块
            if theme == exclude_theme:
                continue
            
            # 排除"其他"板块
            if theme == '其他':
                continue
            
            count = info.get('count', 0)
            heat = info.get('heat', 0)
            
            # 新板块强度：低位板块有首板（热度0.01-0.05，涨停家数>=1）
            if 0.01 <= heat <= 0.05 and count >= 1:
                new_sector_count += 1
        
        return new_sector_count
    
    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()
