"""
策略仲裁庭 (Strategy Orchestrator) - V7.0

解决策略打架问题，统一决策大脑

功能：
1. 一票否决权（Veto Power）：某些情况下强制拒绝交易
2. 加权打分（Weighted Scoring）：综合多个模块的信号
3. 动态仓位输出：根据综合得分输出最佳仓位
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from logic.logger import get_logger
from logic.market_cycle import MarketCycleManager
from logic.theme_detector import ThemeDetector
from logic.dragon_tactics import DragonTactics

logger = get_logger(__name__)


class DecisionType(Enum):
    """决策类型"""
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"
    REJECT = "REJECT"


class StrategyOrchestrator:
    """
    策略仲裁者
    
    功能：
    1. 统一裁决多个策略模块的冲突
    2. 实现一票否决权
    3. 加权打分输出最终决策
    """
    
    def __init__(self):
        """初始化策略仲裁者"""
        self.market_cycle_manager = MarketCycleManager()
        self.theme_detector = ThemeDetector()
        
        # 模块权重配置
        self.weights = {
            "market_cycle": 0.5,      # 大盘环境权重最大 (50%)
            "theme_status": 0.3,       # 板块地位 (30%)
            "individual_tech": 0.2     # 个股技术面 (20%)
        }
        
        # 一票否决权配置
        self.veto_rules = {
            "decline_phase": True,     # 退潮期一票否决（除非反核）
            "boom_phase": True,        # 高潮期一票否决打板
            "st_stocks": True,         # ST股票一票否决
        }
        
        logger.info("策略仲裁者初始化完成")
    
    def final_judgement(self, 
                       stock_signal: Dict[str, Any], 
                       market_status: Dict[str, Any],
                       theme_info: Dict[str, Any],
                       use_kelly: bool = True) -> Tuple[DecisionType, str, float]:
        """
        最终裁决
        
        Args:
            stock_signal: 个股信号（来自DragonStrategy等）
                {
                    'signal': 'BUY' | 'SELL' | 'WAIT',
                    'score': 0-100,
                    'is_limit_up': bool,
                    'is_anti_nuclear': bool,
                    'is_dragon': bool,
                    'strategy_type': 'MAIN_RISE' | 'ANTI_NUCLEAR' | 'DRAGON_RETURN'
                }
            market_status: 市场状态（来自MarketCycle）
                {
                    'cycle': 'BOOM' | 'MAIN_RISE' | 'CHAOS' | 'ICE' | 'DECLINE',
                    'risk_level': 1-5,
                    'limit_up_count': int,
                    'limit_down_count': int
                }
            theme_info: 板块信息（来自ThemeDetector）
                {
                    'main_theme': str,
                    'theme_heat': float,
                    'is_in_main_theme': bool,
                    'sector_rank': int
                }
            use_kelly: 是否使用凯利公式计算仓位
        
        Returns:
            tuple: (决策类型, 决策原因, 建议仓位)
        """
        try:
            # 1. 一票否决权检查（Veto Power）
            veto_result, veto_reason = self._check_veto_power(stock_signal, market_status)
            if veto_result:
                return DecisionType.REJECT, veto_reason, 0.0
            
            # 2. 加权打分（Weighted Scoring）
            total_score = self._calculate_weighted_score(stock_signal, market_status, theme_info)
            
            # 3. 根据得分输出决策
            if total_score >= 80:
                decision = DecisionType.BUY
                reason = f"综合得分{total_score:.1f}分，建议买入"
                
                # 计算仓位
                if use_kelly:
                    position = self._calculate_kelly_position(stock_signal, market_status)
                else:
                    position = self._calculate_fixed_position(total_score)
                
            elif total_score >= 60:
                decision = DecisionType.BUY
                reason = f"综合得分{total_score:.1f}分，建议轻仓买入"
                position = 0.3  # 固定30%仓位
                
            elif total_score >= 40:
                decision = DecisionType.WAIT
                reason = f"综合得分{total_score:.1f}分，建议观望"
                position = 0.0
            else:
                decision = DecisionType.REJECT
                reason = f"综合得分{total_score:.1f}分，建议放弃"
                position = 0.0
            
            return decision, reason, position
        
        except Exception as e:
            logger.error(f"最终裁决失败: {e}")
            return DecisionType.WAIT, "裁决失败，建议观望", 0.0
    
    def _check_veto_power(self, 
                          stock_signal: Dict[str, Any], 
                          market_status: Dict[str, Any]) -> Tuple[bool, str]:
        """
        一票否决权检查
        
        Args:
            stock_signal: 个股信号
            market_status: 市场状态
        
        Returns:
            tuple: (是否否决, 否决原因)
        """
        market_cycle = market_status.get('cycle', '')
        
        # 1. 退潮期一票否决（除非是反核模式）
        if self.veto_rules['decline_phase'] and market_cycle == 'DECLINE':
            is_anti_nuclear = stock_signal.get('is_anti_nuclear', False)
            
            if not is_anti_nuclear:
                return True, "🚫 退潮期严禁接力，除非是反核模式"
        
        # 2. 高潮期一票否决打板
        if self.veto_rules['boom_phase'] and market_cycle == 'BOOM':
            is_limit_up = stock_signal.get('is_limit_up', False)
            
            if is_limit_up:
                return True, "🚫 情绪高潮日，禁止打板接力，只卖不买"
        
        # 3. ST股票一票否决
        if self.veto_rules['st_stocks']:
            stock_code = stock_signal.get('code', '')
            if 'ST' in stock_code or '*ST' in stock_code:
                return True, "🚫 ST/退市风险股，一票否决"
        
        return False, ""
    
    def _calculate_weighted_score(self, 
                                  stock_signal: Dict[str, Any], 
                                  market_status: Dict[str, Any],
                                  theme_info: Dict[str, Any]) -> float:
        """
        加权打分
        
        Args:
            stock_signal: 个股信号
            market_status: 市场状态
            theme_info: 板块信息
        
        Returns:
            float: 综合得分 (0-100)
        """
        scores = {}
        
        # 1. 市场环境得分（权重50%）
        market_cycle = market_status.get('cycle', '')
        risk_level = market_status.get('risk_level', 3)
        
        if market_cycle == 'MAIN_RISE':
            market_score = 100
        elif market_cycle == 'ICE':
            market_score = 40
        elif market_cycle == 'CHAOS':
            market_score = 30
        elif market_cycle == 'BOOM':
            market_score = 20
        elif market_cycle == 'DECLINE':
            market_score = 10
        else:
            market_score = 30
        
        # 根据风险等级调整得分
        market_score = market_score * (5 - risk_level) / 5
        scores['market_cycle'] = market_score
        
        # 2. 板块地位得分（权重30%）
        is_in_main_theme = theme_info.get('is_in_main_theme', False)
        sector_rank = theme_info.get('sector_rank', 999)
        theme_heat = theme_info.get('theme_heat', 0)
        
        if is_in_main_theme:
            if sector_rank == 1:
                theme_score = 100
            elif sector_rank <= 3:
                theme_score = 85
            elif sector_rank <= 5:
                theme_score = 70
            else:
                theme_score = 50
        else:
            # 不在主线板块
            theme_score = 30
            # 但如果板块热度较高，可以适当加分
            if theme_heat > 0.1:
                theme_score = 40
        
        scores['theme_status'] = theme_score
        
        # 3. 个股技术面得分（权重20%）
        stock_score = stock_signal.get('score', 50)
        is_dragon = stock_signal.get('is_dragon', False)
        
        if is_dragon:
            stock_score = min(stock_score * 1.2, 100)  # 龙头股加成20%
        
        scores['individual_tech'] = stock_score
        
        # 4. 综合得分计算
        total_score = (
            scores['market_cycle'] * self.weights['market_cycle'] +
            scores['theme_status'] * self.weights['theme_status'] +
            scores['individual_tech'] * self.weights['individual_tech']
        )
        
        return total_score
    
    def _calculate_kelly_position(self, 
                                  stock_signal: Dict[str, Any], 
                                  market_status: Dict[str, Any]) -> float:
        """
        🆕 V7.0: 使用凯利公式计算最佳仓位
        
        Args:
            stock_signal: 个股信号
            market_status: 市场状态
        
        Returns:
            float: 建议仓位 (0.0-1.0)
        """
        strategy_type = stock_signal.get('strategy_type', 'MAIN_RISE')
        market_cycle = market_status.get('cycle', '')
        
        # 从历史数据获取胜率和赔率（这里简化处理，实际应该从数据库查询）
        # 反核战法：胜率低，赔率高
        if strategy_type == 'ANTI_NUCLEAR':
            win_rate = 0.35  # 35%胜率
            odds = 2.0       # 1:2赔率（地天板+20%）
        
        # 龙回头战法：胜率中等，赔率中等
        elif strategy_type == 'DRAGON_RETURN':
            win_rate = 0.55  # 55%胜率
            odds = 1.5       # 1:1.5赔率
        
        # 主升浪龙头：胜率高，赔率稳
        elif strategy_type == 'MAIN_RISE':
            if market_cycle == 'MAIN_RISE':
                win_rate = 0.70  # 70%胜率
                odds = 1.2       # 1:1.2赔率
            else:
                win_rate = 0.50  # 50%胜率
                odds = 1.0       # 1:1赔率
        
        else:
            win_rate = 0.50
            odds = 1.0
        
        # 凯利公式：f = (bp - q) / b
        # f = 仓位, b = 赔率, p = 胜率, q = 败率
        q = 1 - win_rate
        
        if odds > 0:
            kelly_position = (odds * win_rate - q) / odds
        else:
            kelly_position = 0
        
        # 实战通常打折使用（半凯利）
        real_position = kelly_position * 0.5
        
        # 限制仓位范围
        real_position = max(0.0, min(real_position, 0.8))
        
        return real_position
    
    def _calculate_fixed_position(self, total_score: float) -> float:
        """
        固定仓位计算（不使用凯利公式）
        
        Args:
            total_score: 综合得分
        
        Returns:
            float: 建议仓位 (0.0-1.0)
        """
        if total_score >= 90:
            return 0.8  # 满仓
        elif total_score >= 80:
            return 0.6  # 重仓
        elif total_score >= 70:
            return 0.4  # 中仓
        elif total_score >= 60:
            return 0.2  # 轻仓
        else:
            return 0.0
    
    def close(self):
        """关闭资源"""
        if self.market_cycle_manager:
            self.market_cycle_manager.close()
        if self.theme_detector:
            self.theme_detector.close()