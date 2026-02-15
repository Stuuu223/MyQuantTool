"""
全市场情绪雷达模块 - V9.11

功能：
1. 全市场情绪扫描（基于快照数据）
2. 涨跌停统计
3. 赚钱效应评估
4. 市场温度计算

Author: iFlow CLI
Version: V9.11
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from logic.utils.logger import get_logger
from logic.sentiment.market_status import get_market_status_checker
from logic.analyzers.technical_analyzer import TechnicalAnalyzer

logger = get_logger(__name__)


class StrategyMapper:
    """
    🆕 V9.13.1 游资战术映射器
    
    根据股票的身位（连板数）和竞价表现，映射到对应的游资战术和 AI 指令。
    这是 V10.0 AI 决策的核心"战术手册"。
    """
    
    # 战术映射表
    STRATEGY_MAP = {
        # 首板策略
        '首板_高开': {
            'tactic': '试错/排板',
            'ai_hint': '新周期起点，建议轻仓博弈',
            'risk': '中',
            'position': '1-2成'
        },
        '首板_平开': {
            'tactic': '观察',
            'ai_hint': '等待确认，暂不介入',
            'risk': '高',
            'position': '空仓'
        },
        '首板_低开': {
            'tactic': '放弃',
            'ai_hint': '不及预期，避免接盘',
            'risk': '极高',
            'position': '空仓'
        },
        
        # 2板策略
        '2板_弱转强': {
            'tactic': '接力/龙头',
            'ai_hint': '气质最佳，核心买点，建议重仓',
            'risk': '中低',
            'position': '3-5成'
        },
        '2板_高开': {
            'tactic': '加速',
            'ai_hint': '强势延续，可适当参与',
            'risk': '中',
            'position': '2-3成'
        },
        '2板_低开': {
            'tactic': '核按钮/止损',
            'ai_hint': '不及预期，防止A杀，建议离场',
            'risk': '高',
            'position': '空仓'
        },
        
        # 3板策略
        '3板_缩量一字': {
            'tactic': '加速/锁仓',
            'ai_hint': '持筹者盛宴，通道党战场，排队碰运气',
            'risk': '中高',
            'position': '1-2成'
        },
        '3板_放量': {
            'tactic': '换手',
            'ai_hint': '充分换手，关注承接力度',
            'risk': '中',
            'position': '2-3成'
        },
        '3板_低开': {
            'tactic': '核按钮/止损',
            'ai_hint': '不及预期，防止A杀，建议离场',
            'risk': '极高',
            'position': '空仓'
        },
        
        # 高位策略（5板+）
        '高位_爆量分歧': {
            'tactic': '妖股博弈',
            'ai_hint': '只做总龙头，非龙勿碰',
            'risk': '极高',
            'position': '1-2成'
        },
        '高位_缩量加速': {
            'tactic': '锁仓',
            'ai_hint': '持筹盛宴，新仓不接',
            'risk': '高',
            'position': '空仓'
        },
        '高位_低开': {
            'tactic': '核按钮/止损',
            'ai_hint': 'A杀风险极高，坚决离场',
            'risk': '极高',
            'position': '空仓'
        }
    }
    
    @staticmethod
    def get_strategy_key(lianban_count: int, auction_pct: float, is_weak_to_strong: bool = False) -> str:
        """
        根据连板数、竞价涨幅、弱转强状态，生成策略键
        
        Args:
            lianban_count: 连板数
            auction_pct: 竞价涨幅（%）
            is_weak_to_strong: 是否弱转强
        
        Returns:
            str: 策略键，用于查找 STRATEGY_MAP
        """
        # 1. 判断身位
        if lianban_count >= 5:
            status = '高位'
        elif lianban_count >= 3:
            status = '3板'
        elif lianban_count == 2:
            status = '2板'
        else:
            status = '首板'
        
        # 2. 判断竞价表现
        if status == '首板' and is_weak_to_strong:
            auction = '高开'
        elif auction_pct > 2:
            auction = '高开'
        elif auction_pct > -2:
            auction = '平开'
        else:
            auction = '低开'
        
        # 3. 特殊情况：缩量一字
        if status in ['3板', '高位'] and auction_pct > 9.5:
            auction = '缩量一字'
        
        # 4. 特殊情况：爆量分歧
        if status == '高位' and auction_pct > 0 and auction_pct < 5:
            auction = '爆量分歧'
        
        # 5. 特殊情况：弱转强
        if status == '2板' and is_weak_to_strong:
            auction = '弱转强'
        
        return f"{status}_{auction}"
    
    @staticmethod
    def get_strategy(lianban_count: int, auction_pct: float, is_weak_to_strong: bool = False) -> Dict[str, Any]:
        """
        获取游资战术建议
        
        Args:
            lianban_count: 连板数
            auction_pct: 竞价涨幅（%）
            is_weak_to_strong: 是否弱转强
        
        Returns:
            dict: 战术建议
        """
        strategy_key = StrategyMapper.get_strategy_key(lianban_count, auction_pct, is_weak_to_strong)
        
        # 从映射表中查找
        strategy = StrategyMapper.STRATEGY_MAP.get(strategy_key, {
            'tactic': '观察',
            'ai_hint': '暂无明确策略，建议观察',
            'risk': '未知',
            'position': '空仓'
        })
        
        # 添加策略键
        strategy['strategy_key'] = strategy_key
        
        return strategy


class SentimentAnalyzer:
    """
    全市场情绪分析器
    
    基于快照数据，通过 Pandas 向量化计算（性能极快），
    0.01秒算出全市场情绪。
    """
    
    def __init__(self, data_manager):
        """
        初始化情绪分析器
        
        Args:
            data_manager: 数据管理器实例
        """
        self.dm = data_manager
        self.checker = get_market_status_checker()
        self.cache = None
        self.cache_timestamp = None
        # 🔥 新增初始化
        self.ta = TechnicalAnalyzer()
    
    def get_market_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        🆕 V18.8 修复：获取全市场快照数据（使用新的数据提供者架构）
        
        Returns:
            全市场快照数据字典
        """
        try:
            # 🆕 V15.0 修复：使用 QMT适配器获取全市场快照
            # 绕过 DataManager 的代理层，直接使用 QMT适配器
            from logic.data_providers.easyquotation_adapter import get_easyquotation_adapter
            
            # 初始化行情接口
            quotation = get_easyquotation_adapter()
            
            # 获取全市场快照
            snapshot = quotation.market_snapshot(prefix=False)
            
            if not snapshot or len(snapshot) == 0:
                logger.warning("获取到的市场快照为空")
                return None
            
            logger.info(f"✅ 获取全市场快照成功: {len(snapshot)} 只股票")
            
            return snapshot
        except Exception as e:
            logger.error(f"获取市场快照失败: {e}")
            return None
    
    def analyze_market_mood(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        📊 全市场情绪扫描（基于内存快照，耗时<0.1s）
        
        Args:
            force_refresh: 是否强制刷新缓存
        
        Returns:
            市场情绪指标字典
        """
        try:
            # 检查缓存
            if not force_refresh and self.cache is not None:
                import time
                cache_age = time.time() - self.cache_timestamp
                if cache_age < 10:  # 缓存10秒
                    return self.cache
            
            # 1. 获取全市场快照
            snapshot = self.get_market_snapshot()
            
            if snapshot is None or len(snapshot) == 0:
                logger.warning("无法获取市场快照数据")
                return None
            
            # 2. 转换为 DataFrame 进行极速计算
            # snapshot 是字典格式，需要转换为 DataFrame
            df = pd.DataFrame.from_dict(snapshot, orient='index')
            
            if df.empty:
                return None
            
            # 数据清洗：确保数值列是浮点型
            numeric_cols = ['now', 'close', 'open', 'high', 'low']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                else:
                    df[col] = 0.0
            
            # 剔除无效数据（停牌或未开盘）
            df = df[df['now'] > 0]
            
            if len(df) == 0:
                return None
            
            # 3. 核心指标计算
            total_stocks = len(df)
            
            # 计算涨跌幅
            df['pct'] = (df['now'] - df['close']) / df['close'] * 100
            
            # 🆕 V9.12 修复：添加股票名称列（用于ST股识别）
            if 'name' not in df.columns:
                df['name'] = ''
            
            # 🆕 V9.12 修复：识别ST股
            df['is_st'] = df['name'].str.contains('ST', case=False, na=False)
            
            # 🆕 V10.0 新增：计算涨停价（用于炸板统计）
            # 主板：10%涨停，双创：20%涨停，ST：5%涨停
            df['limit_up_price'] = df['close'] * 1.10  # 默认主板10%
            df.loc[df.index.str.startswith(('30', '68')), 'limit_up_price'] = df.loc[df.index.str.startswith(('30', '68')), 'close'] * 1.20  # 双创20%
            df.loc[df['is_st'], 'limit_up_price'] = df.loc[df['is_st'], 'close'] * 1.05  # ST股5%
            
            # 🆕 V10.0 新增：炸板统计（深化版：区分良性炸板和恶性炸板）
            # 炸板条件：最高价触及涨停，但现价 < 涨停价
            df['is_zhaban'] = (df['high'] >= df['limit_up_price'] * 0.99) & (df['now'] < df['limit_up_price'] * 0.99)
            zhaban_count = df['is_zhaban'].sum()
            
            # 🆕 V10.0 深化：计算回撤深度，区分良性炸板和恶性炸板
            # 提取炸板股票
            zhaban_df = df[df['is_zhaban']].copy()
            
            if not zhaban_df.empty:
                # 计算回撤幅度：(涨停价 - 现价) / 涨停价
                zhaban_df['drop_pct'] = (zhaban_df['limit_up_price'] - zhaban_df['now']) / zhaban_df['limit_up_price'] * 100
                
                # 分类炸板类型
                # 良性炸板：回撤 < 2%（烂板/高位震荡）
                # 恶性炸板：回撤 >= 2%（炸板回落）
                zhaban_df['zhaban_type'] = zhaban_df['drop_pct'].apply(
                    lambda x: '良性炸板' if x < 2 else '恶性炸板'
                )
                
                # 统计各类炸板数量
                benign_zhaban_count = (zhaban_df['zhaban_type'] == '良性炸板').sum()
                malignant_zhaban_count = (zhaban_df['zhaban_type'] == '恶性炸板').sum()
                
                # 计算平均回撤
                avg_drop_pct = zhaban_df['drop_pct'].mean()
            else:
                benign_zhaban_count = 0
                malignant_zhaban_count = 0
                avg_drop_pct = 0.0
            
            # 涨停/跌停统计（粗略估算：主板10%，双创20%）
            # 使用 9.0% 作为涨停阈值（近似值）
            limit_up = df[df['pct'] > 9.0].shape[0]
            limit_down = df[df['pct'] < -9.0].shape[0]
            
            # 🆕 V9.12 修复：ST股单独统计（5%涨停）
            st_limit_up = df[(df['is_st']) & (df['pct'] > 4.5)].shape[0]
            st_limit_down = df[(df['is_st']) & (df['pct'] < -4.5)].shape[0]
            
            # 🆕 V9.12 修复：北交所单独统计（30%涨停）
            # 北交所代码以8或4开头
            df['is_bj'] = df.index.str.startswith(('8', '4'))
            bj_limit_up = df[(df['is_bj']) & (df['pct'] > 29.0)].shape[0]
            bj_limit_down = df[(df['is_bj']) & (df['pct'] < -29.0)].shape[0]
            
            # 上涨/下跌家数
            up_count = df[df['pct'] > 0].shape[0]
            down_count = df[df['pct'] < 0].shape[0]
            flat_count = df[df['pct'] == 0].shape[0]
            
            # 赚钱效应（上涨家数占比）
            sentiment_score = int((up_count / total_stocks) * 100)
            
            # 平均涨跌幅
            avg_pct = df['pct'].mean()
            
            # 中位数涨跌幅（更稳健的指标）
            median_pct = df['pct'].median()
            
            # 强势股占比（涨幅>5%）
            strong_up = df[df['pct'] > 5.0].shape[0]
            strong_up_ratio = int((strong_up / total_stocks) * 100)
            
            # 弱势股占比（跌幅<-5%）
            weak_down = df[df['pct'] < -5.0].shape[0]
            weak_down_ratio = int((weak_down / total_stocks) * 100)
            
            # 🆕 V10.0 新增：计算炸板率
            # 炸板率 = 炸板数 / (涨停数 + 炸板数) * 100%
            limit_up_total = limit_up + zhaban_count
            zhaban_rate = (zhaban_count / limit_up_total * 100) if limit_up_total > 0 else 0.0
            
            result = {
                "total": total_stocks,
                "limit_up": limit_up,
                "limit_down": limit_down,
                # 🆕 V9.12 修复：ST股单独统计
                "st_limit_up": st_limit_up,
                "st_limit_down": st_limit_down,
                # 🆕 V9.12 修复：北交所单独统计
                "bj_limit_up": bj_limit_up,
                "bj_limit_down": bj_limit_down,
                "up": up_count,
                "down": down_count,
                "flat": flat_count,
                "score": sentiment_score,
                "avg_pct": round(avg_pct, 2),
                "median_pct": round(median_pct, 2),
                "strong_up_ratio": strong_up_ratio,
                "weak_down_ratio": weak_down_ratio,
                # 🆕 V10.0 新增：炸板统计
                "zhaban_count": int(zhaban_count),
                "zhaban_rate": round(zhaban_rate, 2),
                # 🆕 V10.0 深化：炸板类型统计
                "benign_zhaban_count": int(benign_zhaban_count),
                "malignant_zhaban_count": int(malignant_zhaban_count),
                "avg_drop_pct": round(avg_drop_pct, 2),
                "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")
            }
            
            # 更新缓存
            import time
            self.cache = result
            self.cache_timestamp = time.time()
            
            logger.info(f"✅ 市场情绪分析完成: {total_stocks}只股票，得分{sentiment_score}分")
            
            return result
            
        except Exception as e:
            logger.error(f"市场情绪分析失败: {e}")
            return None
    
    def get_market_temperature(self) -> str:
        """
        获取市场温度描述
        
        Returns:
            市场温度描述
        """
        mood = self.analyze_market_mood()
        
        if mood is None:
            return "未知"
        
        score = mood['score']
        
        if score >= 80:
            return "🔥 极热"
        elif score >= 60:
            return "🌡️ 温暖"
        elif score >= 40:
            return "😐 平衡"
        elif score >= 20:
            return "❄️ 偏冷"
        else:
            return "🧊 冰点"
    
    def get_trading_advice(self) -> str:
        """
        根据市场情绪给出交易建议
        
        Returns:
            交易建议
        """
        mood = self.analyze_market_mood()
        
        if mood is None:
            return "数据不足，无法给出建议"
        
        score = mood['score']
        limit_up = mood['limit_up']
        limit_down = mood['limit_down']
        
        advice = []
        
        # 基于得分的建议
        if score >= 80:
            advice.append("市场极热，建议谨慎追高")
        elif score >= 60:
            advice.append("市场温暖，适合积极操作")
        elif score >= 40:
            advice.append("市场平衡，可适度参与")
        elif score >= 20:
            advice.append("市场偏冷，建议轻仓观望")
        else:
            advice.append("市场冰点，建议空仓等待")
        
        # 基于涨跌停数的建议
        if limit_up > 50:
            advice.append(f"涨停{limit_up}家，赚钱效应强")
        elif limit_up < 10:
            advice.append(f"涨停仅{limit_up}家，赚钱效应弱")
        
        if limit_down > 30:
            advice.append(f"跌停{limit_down}家，风险较高")
        
        return "；".join(advice) if advice else "暂无建议"
    
    def generate_ai_context(self, include_stock_pool: bool = True, 
                           stock_pool_size: int = 20,
                           is_review_mode: bool = False) -> Dict[str, Any]:
        """
        🆕 V9.11.2 修复：生成AI专用数据包
        
        为AI（如LLM）生成结构化的市场数据包，便于智能分析和决策。
        
        Args:
            include_stock_pool: 是否包含股票池数据
            stock_pool_size: 股票池大小（默认前20只）
            is_review_mode: 复盘模式开关（V9.12.1新增）
        
        Returns:
            AI专用数据包字典
        """
        try:
            # 1. 获取市场情绪数据
            mood = self.analyze_market_mood(force_refresh=True)
            
            if mood is None:
                return {"error": "无法获取市场情绪数据"}
            
            # 2. 获取市场状态
            current_time = self.checker.get_current_time()
            
            # 🆕 V9.11.2 修复：判断市场状态
            market_state = "未知"
            if self.checker.is_trading_time():
                market_state = "交易中"
            elif self.checker.is_noon_break():
                market_state = "午间休盘"
            elif self.checker.is_call_auction_gap():
                market_state = "等待开盘"
            else:
                market_state = "非交易时间"
            
            # 3. 获取交易时段
            trading_period = "非交易时间"
            if self.checker.is_call_auction_gap():
                trading_period = "集合竞价"
            elif self.checker.is_trading_time():
                trading_period = "交易时间"
            elif self.checker.is_noon_break():
                trading_period = "午间休盘"
            
            # 🆕 V9.12 修复：预判市场阶段（简单的规则引擎）
            score = mood['score']
            limit_up = mood['limit_up']
            limit_down = mood['limit_down']
            st_limit_up = mood.get('st_limit_up', 0)
            
            market_phase = "震荡期"
            if score > 80 and limit_up > 100:
                market_phase = "🔥 主升浪 (高潮)"
            elif score < 20 and limit_up < 10:
                market_phase = "❄️ 冰点期 (杀跌)"
            elif limit_down > 20:
                market_phase = "⚠️ 退潮期 (亏钱效应显著)"
            elif st_limit_up > 20:
                market_phase = "🚫 垃圾股狂欢 (风险预警)"
            elif limit_up > 50 and score > 60:
                market_phase = "📈 强势期 (赚钱效应)"
            
            # 4. 构建AI数据包
            ai_context = {
                "meta": {
                    "version": "V9.12",
                    "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "market_state": market_state,
                    "trading_period": trading_period,
                    "current_time": current_time.strftime("%H:%M:%S"),
                    # 🆕 V9.12 修复：市场阶段预判
                    "market_phase": market_phase
                },
                "market_sentiment": {
                    "score": mood['score'],
                    "temperature": self.get_market_temperature(),
                    "total_stocks": mood['total'],
                    "limit_up_count": mood['limit_up'],
                    "limit_down_count": mood['limit_down'],
                    # 🆕 V9.12 修复：ST股单独统计
                    "st_limit_up_count": mood.get('st_limit_up', 0),
                    "st_limit_down_count": mood.get('st_limit_down', 0),
                    # 🆕 V9.12 修复：北交所单独统计
                    "bj_limit_up_count": mood.get('bj_limit_up', 0),
                    "bj_limit_down_count": mood.get('bj_limit_down', 0),
                    "up_count": mood['up'],
                    "down_count": mood['down'],
                    "flat_count": mood['flat'],
                    "avg_pct": mood['avg_pct'],
                    "median_pct": mood['median_pct'],
                    "strong_up_ratio": mood['strong_up_ratio'],
                    "weak_down_ratio": mood['weak_down_ratio'],
                    # 🆕 V10.0 新增：炸板统计
                    "zhaban_count": mood.get('zhaban_count', 0),
                    "zhaban_rate": mood.get('zhaban_rate', 0),
                    # 🆕 V10.0 深化：炸板类型统计
                    "benign_zhaban_count": mood.get('benign_zhaban_count', 0),
                    "malignant_zhaban_count": mood.get('malignant_zhaban_count', 0),
                    "avg_drop_pct": mood.get('avg_drop_pct', 0)
                },
                "trading_advice": self.get_trading_advice(),
                "risk_assessment": {
                    "level": "高" if mood['score'] < 30 else "中" if mood['score'] < 70 else "低",
                    "limit_up_risk": "高" if mood['limit_up'] > 100 else "中" if mood['limit_up'] > 50 else "低",
                    "limit_down_risk": "高" if mood['limit_down'] > 50 else "中" if mood['limit_down'] > 20 else "低"
                }
            }
            
            # 5. 获取股票池数据（可选）
            if include_stock_pool:
                try:
                    from logic.core.algo import QuantAlgo
                    snapshot = self.get_market_snapshot()
                    
                    if snapshot is not None:
                        # 获取昨日收盘价
                        last_closes = {}
                        for code, data in snapshot.items():
                            last_closes[code] = data.get('close', 0)
                        
                        # 批量分析竞价强度
                        auction_results = QuantAlgo.batch_analyze_auction(snapshot, last_closes, is_review_mode, self.dm)
                        
                        # 🆕 V10.0 优化：按评分排序，取前N只（限制为 Top 10，避免 Token 爆炸）
                        max_pool_size = min(stock_pool_size, 10)  # 最多 10 只
                        sorted_stocks = sorted(
                            auction_results.items(),
                            key=lambda x: x[1].get('score', 0),
                            reverse=True
                        )[:max_pool_size]
                        
                        # 构建股票池数据
                        stock_pool = []
                        for code, result in sorted_stocks:
                            stock_data = snapshot.get(code, {})
                            pct = result.get('pct', 0)
                            
                            # 🆕 V9.13 修复：使用真实连板数据
                            lianban_count = result.get('lianban_count', 0)
                            is_weak_to_strong = result.get('is_weak_to_strong', False)
                            yesterday_status = result.get('yesterday_status', '未知')
                            
                            # 生成连板状态描述
                            if lianban_count >= 5:
                                lianban_status = f"{lianban_count}连板 (妖股)"
                            elif lianban_count >= 3:
                                lianban_status = f"{lianban_count}连板 (成妖)"
                            elif lianban_count >= 2:
                                lianban_status = f"{lianban_count}连板 (确认)"
                            elif lianban_count >= 1:
                                lianban_status = f"{lianban_count}连板 (首板)"
                            elif pct > 9.5:
                                lianban_status = "1板候选"
                            elif pct > 4.5 and 'ST' in stock_data.get('name', ''):
                                lianban_status = "ST涨停"
                            else:
                                lianban_status = "非涨停"
                            
                            # 🆕 V9.13.1 修复：获取游资战术建议
                            strategy = StrategyMapper.get_strategy(lianban_count, pct, is_weak_to_strong)
                            
                            # 🆕 V10.0 新增：获取板块和概念信息
                            concepts_data = self.dm.get_stock_concepts(code)
                            concepts_str = ', '.join(concepts_data.get('concepts', [])) if concepts_data.get('concepts') else ''
                            
                            stock_pool.append({
                                "code": code,
                                "name": stock_data.get('name', '未知'),
                                "price": result.get('price', 0),
                                "pct": pct,
                                "score": result.get('score', 0),
                                "lianban_status": lianban_status,
                                "lianban_count": lianban_count,
                                "is_weak_to_strong": is_weak_to_strong,
                                "strategy_tactic": strategy.get('tactic', '观察'),
                                "strategy_hint": strategy.get('ai_hint', '暂无建议'),
                                "strategy_risk": strategy.get('risk', '未知'),
                                # 🆕 V10.0 新增：板块和概念信息
                                "industry": concepts_data.get('industry', '未知'),
                                "concepts": concepts_str
                            })
                        
                        # ==========================================
                        # 🔥 V10.1.9 [新增] K线视野 (Technical Vision)
                        # ==========================================
                        print("🔍 正在启动多线程扫描 K 线形态...") 
                        # 并发获取技术形态
                        tech_results = self.ta.analyze_batch(stock_pool)
                        
                        # 注入到 stock 对象中
                        for stock in stock_pool:
                            code = stock['code']
                            # 获取分析结果，如果没有(8名以后)则显示未分析
                            kline_info = tech_results.get(code, "⚪ 排名靠后未分析")
                            stock['kline_trend'] = kline_info
                        # ==========================================
                        
                        ai_context["stock_pool"] = {
                            "size": len(stock_pool),
                            "stocks": stock_pool
                        }
                except Exception as e:
                    logger.warning(f"获取股票池数据失败: {e}")
                    ai_context["stock_pool"] = {"error": str(e)}
            
            logger.info(f"✅ AI数据包生成成功，包含{len(ai_context)}个模块")
            
            return ai_context
            
        except Exception as e:
            logger.error(f"生成AI数据包失败: {e}")
            return {"error": str(e)}
    
    def format_ai_context_for_llm(self, ai_context: Dict[str, Any]) -> str:
        """
        🆕 V9.11.2 修复：将AI数据包格式化为LLM友好的文本
        
        Args:
            ai_context: AI数据包字典
        
        Returns:
            LLM友好的文本格式
        """
        try:
            if "error" in ai_context:
                return f"错误：{ai_context['error']}"
            
            # 构建LLM提示词
            prompt_parts = []
            
            # 1. 元信息
            meta = ai_context.get('meta', {})
            prompt_parts.append(f"📅 时间: {meta.get('timestamp', 'N/A')}")
            prompt_parts.append(f"🕐 时段: {meta.get('trading_period', 'N/A')}")
            prompt_parts.append(f"📊 状态: {meta.get('market_state', 'N/A')}")
            prompt_parts.append("")
            
            # 2. 市场情绪
            sentiment = ai_context.get('market_sentiment', {})
            prompt_parts.append("🌡️ 市场情绪:")
            prompt_parts.append(f"- 温度: {sentiment.get('temperature', 'N/A')} (得分: {sentiment.get('score', 0)})")
            prompt_parts.append(f"- 总数: {sentiment.get('total_stocks', 0)}只")
            prompt_parts.append(f"- 涨停: {sentiment.get('limit_up_count', 0)}家")
            prompt_parts.append(f"- 跌停: {sentiment.get('limit_down_count', 0)}家")
            prompt_parts.append(f"- 上涨: {sentiment.get('up_count', 0)}家")
            prompt_parts.append(f"- 下跌: {sentiment.get('down_count', 0)}家")
            prompt_parts.append(f"- 平盘: {sentiment.get('flat_count', 0)}家")
            prompt_parts.append(f"- 均涨: {sentiment.get('avg_pct', 0)}%")
            prompt_parts.append(f"- 中位: {sentiment.get('median_pct', 0)}%")
            prompt_parts.append(f"- 强势占比: {sentiment.get('strong_up_ratio', 0)}%")
            prompt_parts.append(f"- 弱势占比: {sentiment.get('weak_down_ratio', 0)}%")
            # 🆕 V10.0 新增：炸板统计
            prompt_parts.append(f"- 炸板: {sentiment.get('zhaban_count', 0)}家 (炸板率: {sentiment.get('zhaban_rate', 0)}%)")
            # 🆕 V10.0 深化：炸板类型
            if sentiment.get('zhaban_count', 0) > 0:
                prompt_parts.append(f"  - 良性炸板: {sentiment.get('benign_zhaban_count', 0)}家 (烂板/高位震荡)")
                prompt_parts.append(f"  - 恶性炸板: {sentiment.get('malignant_zhaban_count', 0)}家 (炸板回落)")
                prompt_parts.append(f"  - 平均回撤: {sentiment.get('avg_drop_pct', 0)}%")
            prompt_parts.append("")
            
            # 3. 交易建议
            advice = ai_context.get('trading_advice', '')
            if advice:
                prompt_parts.append("💡 交易建议:")
                prompt_parts.append(f"- {advice}")
                prompt_parts.append("")
            
            # 4. 风险评估
            risk = ai_context.get('risk_assessment', {})
            prompt_parts.append("⚠️ 风险评估:")
            prompt_parts.append(f"- 整体风险: {risk.get('level', 'N/A')}")
            prompt_parts.append(f"- 涨停风险: {risk.get('limit_up_risk', 'N/A')}")
            prompt_parts.append(f"- 跌停风险: {risk.get('limit_down_risk', 'N/A')}")
            prompt_parts.append("")
            
            # 5. 股票池（如果有）
            stock_pool = ai_context.get('stock_pool', {})
            if 'stocks' in stock_pool:
                prompt_parts.append("📋 精选股票池 (前20强):")
                for i, stock in enumerate(stock_pool['stocks'], 1):
                    # 🆕 V10.0 新增：添加板块和概念信息
                    concept_str = f", 板块: {stock.get('industry', '未知')}, 概念: {stock.get('concepts', '')}" if stock.get('industry') or stock.get('concepts') else ""
                    
                    prompt_parts.append(
                        f"{i}. {stock['name']} ({stock['code']}) - "
                        f"价格: {stock['price']}, 涨幅: {stock['pct']}%, "
                        f"评分: {stock['score']}, 状态: {stock['status']}"
                        f"{concept_str}"
                    )
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"格式化AI数据包失败: {e}")
            return f"错误：{e}"