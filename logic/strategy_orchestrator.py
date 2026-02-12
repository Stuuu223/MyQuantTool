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
from logic.utils.logger import get_logger
from logic.market_cycle import MarketCycleManager
from logic.theme_detector import ThemeDetector
from logic.dragon_tactics import DragonTactics
from logic.monitors.intraday_turnaround_detector import IntradayTurnaroundDetector  # 🆕 V9.0

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
        self.turnaround_detector = IntradayTurnaroundDetector()  # 🆕 V9.0: 日内弱转强探测器
        
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
            
            # 🆕 V9.0: 日内弱转强检测（修正评分）
            turnaround_score = 0.0
            turnaround_reason = ""
            if self._should_check_turnaround(stock_signal, market_status, theme_info):
                is_turnaround, turnaround_reason, turnaround_score = self._check_turnaround(
                    stock_signal, market_status, theme_info
                )
                if is_turnaround:
                    logger.info(f"检测到日内弱转强: {turnaround_reason}")
            
            # 2. 加权打分（Weighted Scoring）
            total_score = self._calculate_weighted_score(stock_signal, market_status, theme_info)
            
            # 🆕 V9.0: 应用日内弱转强修正评分
            if turnaround_score > 0:
                total_score += turnaround_score
                logger.info(f"应用日内弱转强修正: 原始得分{total_score-turnaround_score:.1f}分 + 修正{turnaround_score:.1f}分 = {total_score:.1f}分")
            
            # 3. 根据得分输出决策
            if total_score >= 80:
                decision = DecisionType.BUY
                reason = f"综合得分{total_score:.1f}分，建议买入"
                if turnaround_score > 0:
                    reason += f"（{turnaround_reason}）"
                
                # 计算仓位
                if use_kelly:
                    position = self._calculate_kelly_position(stock_signal, market_status)
                else:
                    position = self._calculate_fixed_position(total_score)
                
            elif total_score >= 60:
                decision = DecisionType.BUY
                reason = f"综合得分{total_score:.1f}分，建议轻仓买入"
                if turnaround_score > 0:
                    reason += f"（{turnaround_reason}）"
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
                {
                    'code': str,
                    'is_anti_nuclear': bool,
                    'is_limit_up': bool,
                    'turnover': float,  # 成交额（万元）
                    'auction_ratio': float,  # 竞价抢筹度
                    'liquidity_trap': bool,  # 流动性陷阱标记
                    'dragon_type': str  # 真龙类型
                }
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
        
        # 🆕 V8.1: 流动性不足一票否决
        turnover = stock_signal.get('turnover', 0)  # 成交额（万元）
        auction_ratio = stock_signal.get('auction_ratio', 0)  # 竞价抢筹度
        liquidity_trap = stock_signal.get('liquidity_trap', False)  # 流动性陷阱标记
        liquidity_trap_reason = stock_signal.get('liquidity_trap_reason', '')  # 流动性陷阱原因
        dragon_type = stock_signal.get('dragon_type', '')  # 真龙类型
        
        # 流动性陷阱一票否决（但豁免一字板龙头）
        if liquidity_trap:
            # 🆕 V8.2: 检查是否是一字板龙头豁免
            if "豁免" in liquidity_trap_reason:
                # 一字板龙头或次新股豁免，不否决
                pass
            else:
                return True, f"🚫 流动性陷阱：缩量拉升，大资金进出困难"
        
        # 杂毛一票否决（成交额<500万或竞价抢筹度<1%）
        if dragon_type == "🐛 杂毛":
            return True, f"🚫 杂毛股：成交额{turnover:.0f}万<500万或竞价抢筹度{auction_ratio*100:.2f}%<1%，不具备操作价值"
        
        # 弱跟风一票否决（成交额<2000万或竞价抢筹度<1%）
        if dragon_type == "🦆 弱跟风":
            return True, f"🚫 弱跟风：成交额{turnover:.0f}万<2000万或竞价抢筹度{auction_ratio*100:.2f}%<1%，跟风价值低"
        
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
    
    def get_hedging_advice(self, 
                          current_positions: List[Dict[str, Any]], 
                          market_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        🆕 V7.1: 获取对冲建议
        
        功能：
        1. 检测当前持仓的行业集中度
        2. 检测市场过热程度
        3. 建议配置防御性资产
        
        Args:
            current_positions: 当前持仓列表
                [{
                    'code': '股票代码',
                    'name': '股票名称',
                    'sector': '所属板块',
                    'weight': '仓位权重'
                }]
            market_status: 市场状态
        
        Returns:
            dict: {
                'need_hedging': bool,
                'hedging_type': 'ETF' | 'SECTOR' | 'NONE',
                'hedging_weight': float,
                'hedging_targets': ['目标1', '目标2'],
                'reason': '对冲原因'
            }
        """
        try:
            # 1. 检测行业集中度
            sector_exposure = {}
            total_weight = 0
            
            for pos in current_positions:
                sector = pos.get('sector', '其他')
                weight = pos.get('weight', 0)
                sector_exposure[sector] = sector_exposure.get(sector, 0) + weight
                total_weight += weight
            
            # 找出最大暴露的行业
            max_sector = max(sector_exposure, key=sector_exposure.get) if sector_exposure else None
            max_exposure = sector_exposure.get(max_sector, 0) if max_sector else 0
            
            # 2. 检测市场过热程度
            market_cycle = market_status.get('cycle', '')
            risk_level = market_status.get('risk_level', 3)
            
            # 3. 判断是否需要对冲
            need_hedging = False
            hedging_type = 'NONE'
            hedging_weight = 0.0
            hedging_targets = []
            reason = ""
            
            # 判断逻辑
            if market_cycle == 'BOOM':
                # 高潮期：情绪极度高涨，风险极大
                need_hedging = True
                hedging_type = 'ETF'
                hedging_weight = 0.2  # 20%对冲
                hedging_targets = ['510300', '510500']  # 沪深300ETF、中证500ETF
                reason = "高潮期情绪过热，建议配置20%宽基ETF对冲系统性风险"
            
            elif max_exposure > 0.8:
                # 单一行业暴露超过80%
                need_hedging = True
                hedging_type = 'SECTOR'
                hedging_weight = 0.15  # 15%对冲
                hedging_targets = self._get_defensive_sectors(max_sector)
                reason = f"{max_sector}板块暴露过高({max_exposure*100:.1f}%)，建议配置15%防御性板块"
            
            elif market_cycle == 'DECLINE' and risk_level >= 4:
                # 退潮期且高风险
                need_hedging = True
                hedging_type = 'ETF'
                hedging_weight = 0.3  # 30%对冲
                hedging_targets = ['510880', '159915']  # 红利低波ETF、国债ETF
                reason = "退潮期高风险，建议配置30%红利低波ETF作为压舱石"
            
            elif market_cycle == 'MAIN_RISE' and max_exposure > 0.6:
                # 主升期但行业集中度较高
                need_hedging = True
                hedging_type = 'SECTOR'
                hedging_weight = 0.1  # 10%对冲
                hedging_targets = self._get_defensive_sectors(max_sector)
                reason = f"主升期但{max_sector}暴露较高({max_exposure*100:.1f}%)，建议配置10%防御性板块"
            
            return {
                'need_hedging': need_hedging,
                'hedging_type': hedging_type,
                'hedging_weight': hedging_weight,
                'hedging_targets': hedging_targets,
                'reason': reason,
                'sector_exposure': sector_exposure,
                'max_sector': max_sector,
                'max_exposure': max_exposure
            }
        
        except Exception as e:
            logger.error(f"获取对冲建议失败: {e}")
            return {
                'need_hedging': False,
                'hedging_type': 'NONE',
                'hedging_weight': 0.0,
                'hedging_targets': [],
                'reason': '获取对冲建议失败'
            }
    
    def _get_defensive_sectors(self, aggressive_sector: str) -> List[str]:
        """
        获取防御性板块（用于对冲攻击性板块）
        
        Args:
            aggressive_sector: 攻击性板块名称
        
        Returns:
            list: 防御性板块ETF代码列表
        """
        # 防御性板块映射
        defensive_mapping = {
            'AI': ['512880', '159915'],  # 证券ETF、红利低波ETF
            '科技': ['512880', '159915'],
            '医药': ['512880', '159915'],
            '新能源': ['512880', '159915'],
            '芯片': ['512880', '159915'],
            '汽车': ['512880', '159915'],
            '军工': ['512880', '159915'],
            '消费': ['512880', '159915'],
            '软件': ['512880', '159915'],
            '传媒': ['512880', '159915'],
            '其他': ['512880', '159915']
        }
        
        return defensive_mapping.get(aggressive_sector, ['512880', '159915'])
    
    # 🆕 V9.0: 日内弱转强检测方法
    
    def _should_check_turnaround(
        self,
        stock_signal: Dict[str, Any],
        market_status: Dict[str, Any],
        theme_info: Dict[str, Any]
    ) -> bool:
        """
        判断是否应该检测日内弱转强
        
        Args:
            stock_signal: 个股信号
            market_status: 市场状态
            theme_info: 板块信息
        
        Returns:
            bool: 是否应该检测
        """
        # 1. 检查是否有竞价数据
        auction_data = stock_signal.get('auction_data', {})
        if not auction_data:
            return False
        
        # 2. 检查是否有日内数据
        intraday_data = stock_signal.get('intraday_data', None)
        if intraday_data is None or (isinstance(intraday_data, pd.DataFrame) and intraday_data.empty):
            return False
        
        # 3. 检查市场环境（只在主升期或高潮期检测弱转强）
        market_cycle = market_status.get('cycle', '')
        if market_cycle not in ['MAIN_RISE', 'BOOM']:
            return False
        
        # 4. 检查主线热度（主线热度>60才检测）
        theme_heat = theme_info.get('theme_heat', 0)
        if theme_heat < 60:
            return False
        
        # 5. 检查是否是竞价弱（竞价金额<500万 或 竞价抢筹度<2%）
        auction_amount = auction_data.get('auction_amount', 0)
        auction_ratio = auction_data.get('auction_ratio', 0)
        if auction_amount >= 500 and auction_ratio >= 0.02:
            return False
        
        return True
    
    def _check_turnaround(
        self,
        stock_signal: Dict[str, Any],
        market_status: Dict[str, Any],
        theme_info: Dict[str, Any]
    ) -> Tuple[bool, str, float]:
        """
        检测日内弱转强
        
        Args:
            stock_signal: 个股信号
            market_status: 市场状态
            theme_info: 板块信息
        
        Returns:
            tuple: (是否弱转强, 原因, 修正评分)
        """
        try:
            # 获取数据
            auction_data = stock_signal.get('auction_data', {})
            intraday_data = stock_signal.get('intraday_data', None)
            main_theme = theme_info.get('main_theme', '')
            theme_heat = theme_info.get('theme_heat', 0)
            symbol = stock_signal.get('code', '')
            
            # 使用IntradayTurnaroundDetector检测
            return self.turnaround_detector.detect_turnaround(
                symbol,
                auction_data,
                intraday_data,
                main_theme,
                theme_heat
            )
        
        except Exception as e:
            logger.error(f"检测日内弱转强失败: {e}", exc_info=True)
            return False, f"检测失败: {e}", 0.0
    
    def close(self):
        """关闭资源"""
        if self.market_cycle_manager:
            self.market_cycle_manager.close()
        if self.theme_detector:
            self.theme_detector.close()