# -*- coding: utf-8 -*-
"""
CapitalAllocator - 账户级资金调度器

核心目标：
- 账户曲线向上 > 单笔收益故事
- 机会成本最小化 > 死守某只股票
- 哪里赚钱最优去哪里

核心逻辑：
1. 实时重新评分（不看历史标签）
2. 换仓决策（持仓 vs 候选池实时PK）
3. 动态仓位分配（1只/2只/3只）
4. T+1约束处理

版本：V17.0.0
创建日期：2026-02-16
作者：MyQuantTool Team
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import json

from logic.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Position:
    """持仓信息"""
    code: str  # 股票代码
    name: str  # 股票名称
    shares: int  # 持仓数量
    cost_price: float  # 成本价
    current_price: float  # 当前价格
    buy_time: datetime  # 买入时间
    sell_time: Optional[datetime] = None  # 卖出时间
    is_sold_today: bool = False  # 是否今日卖出
    
    @property
    def market_value(self) -> float:
        """市值"""
        return self.shares * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        """浮动盈亏"""
        return (self.current_price - self.cost_price) * self.shares
    
    @property
    def return_pct(self) -> float:
        """收益率"""
        return (self.current_price - self.cost_price) / self.cost_price
    
    @property
    def hold_days(self) -> int:
        """持有天数"""
        return (datetime.now() - self.buy_time).days
    
    def update_price(self, price: float):
        """更新价格"""
        self.current_price = price
    
    def close(self, sell_price: float, sell_time: datetime):
        """平仓"""
        self.current_price = sell_price
        self.sell_time = sell_time
        # 检查是否今日卖出（用于T+1约束）
        self.is_sold_today = (sell_time.date() == self.buy_time.date())


class CapitalAllocator:
    """
    账户级资金调度器
    
    核心功能：
    1. 实时重新评分（不看历史标签）
    2. 换仓决策（持仓 vs 候选池实时PK）
    3. 动态仓位分配（1只/2只/3只）
    4. T+1约束处理
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化资金调度器
        
        Args:
            config_path: 配置文件路径（可选）
        """
        # 加载配置
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / 'config' / 'portfolio_config.json'
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # 提取关键参数
        self.max_positions = self.config['position_allocation']['max_positions']  # 最多3只
        self.single_threshold = self.config['position_allocation']['single_position_threshold']  # 1.5倍
        self.weights = self.config['position_allocation']['concentration_weights']
        
        self.max_drawdown = self.config['exit_rules']['max_drawdown']  # -12%
        self.risk_score_threshold = self.config['exit_rules']['risk_score_threshold']  # 0.3
        self.capital_outflow_threshold = self.config['exit_rules']['capital_outflow_threshold']  # -5000万
        self.min_hold_days = self.config['exit_rules']['min_hold_days_for_rebalance']  # 1天
        self.opportunity_cost_days = self.config['exit_rules']['opportunity_cost_days']  # 5天
        self.opportunity_cost_min_return = self.config['exit_rules']['opportunity_cost_min_return']  # 3%
        
        self.scoring_weights = self.config['scoring_weights']
        
        # 持仓管理
        self.positions: Dict[str, Position] = {}
        self.account_value = self.config['backtest']['initial_capital']
        self.peak_value = self.account_value  # 历史最高净值
        
        logger.info(f"✅ CapitalAllocator初始化成功")
        logger.info(f"   - 最大持仓数: {self.max_positions}")
        logger.info(f"   - 最大回撤: {self.max_drawdown:.2%}")
        logger.info(f"   - 断层优势阈值: {self.single_threshold}倍")
    
    def update_opportunity_pool(self, opportunities: List[Dict]):
        """
        更新机会池（从三漏斗输出）
        
        Args:
            opportunities: 候选机会列表，每个机会包含：
                - code: 股票代码
                - name: 股票名称
                - price: 当前价格
                - ratio: 资金推动力（主力净流入/流通市值）
                - sector_resonance: 板块共振信息
                - risk_score: 风险评分
                - confidence: 置信度
        """
        self.opportunity_pool = opportunities
        logger.debug(f"📊 机会池更新: {len(opportunities)}个机会")
    
    def make_rebalance_decision(self, current_positions: Dict, opportunity_pool: List[Dict]) -> Dict:
        """
        换仓决策：基于实时优势对比
        
        Args:
            current_positions: 当前持仓 {code: position_dict}
            opportunity_pool: 候选机会池
        
        Returns:
            决策字典 {'SELL': [...], 'BUY': [...], 'HOLD': [...]}
        """
        decisions = {
            'SELL': [],  # 需要卖出的持仓
            'BUY': [],   # 需要买入的机会
            'HOLD': []   # 继续持有的持仓
        }
        
        # 1. 实时重新计算所有持仓的当前评分（不看历史标签）
        current_scores = {}
        for code, position_dict in current_positions.items():
            # 🔥 关键：用最新数据重新计算评分
            current_score = self._calculate_comprehensive_score({
                'code': code,
                'ratio': position_dict.get('ratio', 0),
                'sector_resonance': position_dict.get('sector_resonance', {}),
                'risk_score': position_dict.get('risk_score', 0.5),
                'confidence': position_dict.get('confidence', 0.5)
            })
            
            current_scores[code] = {
                'score': current_score,
                'hold_days': position_dict.get('hold_days', 0),
                'profit_rate': position_dict.get('profit_rate', 0)
            }
        
        # 2. 计算候选池的实时评分
        opportunity_scores = []
        for opp in opportunity_pool:
            score = self._calculate_comprehensive_score(opp)
            opportunity_scores.append({
                'code': opp['code'],
                'score': score,
                'confidence': opp.get('confidence', 0.5)
            })
        
        # 3. 换仓决策：持仓 vs 候选池
        for code, current_data in current_scores.items():
            # T+1约束：今天买的不能今天卖
            if current_data['hold_days'] < self.min_hold_days:
                decisions['HOLD'].append(code)
                continue
            
            # 找出候选池中评分最高的机会
            best_opportunity = max(opportunity_scores, key=lambda x: x['score']) if opportunity_scores else None
            
            # 🔥 关键：实时对比，不看历史标签
            if best_opportunity and best_opportunity['score'] > current_data['score'] * 1.2:
                # 候选池有明显更优机会，换仓
                decisions['SELL'].append({
                    'code': code,
                    'reason': f'换仓到{best_opportunity["code"]}',
                    'current_score': current_data['score'],
                    'new_score': best_opportunity['score']
                })
                decisions['BUY'].append(best_opportunity['code'])
            else:
                # 持仓仍然是最优，继续持有
                decisions['HOLD'].append(code)
        
        # 4. 检查现有持仓是否需要退出（风险信号）
        for code, position_dict in current_positions.items():
            if code in decisions['SELL']:
                continue  # 已经决定卖出
            
            # 检查风险信号
            should_exit, reason = self._check_position_exit(position_dict)
            if should_exit:
                # 从HOLD移除，加入SELL
                if code in decisions['HOLD']:
                    decisions['HOLD'].remove(code)
                decisions['SELL'].append({
                    'code': code,
                    'reason': reason,
                    'profit_rate': position_dict.get('profit_rate', 0)
                })
        
        logger.info(f"📊 换仓决策: SELL={len(decisions['SELL'])}, BUY={len(decisions['BUY'])}, HOLD={len(decisions['HOLD'])}")
        
        return decisions
    
    def allocate_capital(self, opportunities: List[Dict], available_capital: float) -> List[Dict]:
        """
        动态仓位分配
        
        Args:
            opportunities: 候选机会列表
            available_capital: 可用资金
        
        Returns:
            仓位分配列表 [{'code': xxx, 'capital': xxx}, ...]
        """
        if not opportunities or available_capital <= 0:
            return []
        
        # 1. 计算综合评分并排序
        scored_opps = []
        for opp in opportunities:
            score = self._calculate_comprehensive_score(opp)
            scored_opps.append({
                'code': opp['code'],
                'score': score
            })
        
        sorted_opps = sorted(scored_opps, key=lambda x: x['score'], reverse=True)
        
        # 2. 最多取前max_positions只
        top_opps = sorted_opps[:self.max_positions]
        
        # 3. 识别断层优势
        if len(top_opps) == 1:
            # 只有1个机会，直接80%仓位
            return [{
                'code': top_opps[0]['code'],
                'capital': available_capital * self.weights['single']
            }]
        
        top1_score = top_opps[0]['score']
        top2_score = top_opps[1]['score']
        
        if top1_score > top2_score * self.single_threshold:
            # 断层优势：单吊（90%仓位）
            logger.info(f"🎯 断层优势识别: {top_opps[0]['code']} (Top1={top1_score:.2f}, Top2={top2_score:.2f})")
            return [{
                'code': top_opps[0]['code'],
                'capital': available_capital * self.weights['single']
            }]
        
        # 4. 正常分散：2-3只
        if len(top_opps) >= 3:
            # 3只分散（50% + 30% + 20%）
            return [
                {'code': top_opps[0]['code'], 'capital': available_capital * self.weights['triple'][0]},
                {'code': top_opps[1]['code'], 'capital': available_capital * self.weights['triple'][1]},
                {'code': top_opps[2]['code'], 'capital': available_capital * self.weights['triple'][2]}
            ]
        else:  # len == 2
            # 2只分散（60% + 40%）
            return [
                {'code': top_opps[0]['code'], 'capital': available_capital * self.weights['dual'][0]},
                {'code': top_opps[1]['code'], 'capital': available_capital * self.weights['dual'][1]}
            ]
    
    def _check_position_exit(self, position: Dict) -> Tuple[bool, str]:
        """
        检查持仓是否需要退出
        
        Args:
            position: 持仓信息
        
        Returns:
            (是否退出, 退出原因)
        """
        # 1. T+1约束
        hold_days = position.get('hold_days', 0)
        if hold_days < self.min_hold_days:
            return False, 'T+1约束'
        
        # 2. 风险信号
        main_net_inflow = position.get('main_net_inflow', 0)
        if main_net_inflow < self.capital_outflow_threshold:
            return True, '主力出逃'
        
        risk_score = position.get('risk_score', 0)
        if risk_score > self.risk_score_threshold:
            return True, '风险恶化'
        
        # 3. 极限回撤保护
        profit_rate = position.get('profit_rate', 0)
        if profit_rate < self.max_drawdown:
            return True, f'极限回撤保护({profit_rate:.2%})'
        
        # 4. 持有时间过长但无进展
        if hold_days > self.opportunity_cost_days and profit_rate < self.opportunity_cost_min_return:
            return True, f'机会成本过高(持有{hold_days}天, 收益{profit_rate:.2%})'
        
        return False, '继续持有'
    
    def _calculate_comprehensive_score(self, opportunity: Dict) -> float:
        """
        综合评分：识别断层优势
        
        Args:
            opportunity: 机会信息
        
        Returns:
            综合评分（0-1）
        """
        score = 0.0
        
        # 1. 资金推动力（权重40%）
        ratio = opportunity.get('ratio', 0)
        if ratio > 0.03:  # ratio > 3%
            score += 0.4
        elif ratio > 0.015:  # ratio > 1.5%
            score += 0.25
        elif ratio > 0.01:  # ratio > 1%
            score += 0.15
        
        # 2. 板块共振（权重30%）
        sector_resonance = opportunity.get('sector_resonance', {})
        if sector_resonance.get('is_resonance', False):
            resonance_score = sector_resonance.get('score', 0.5)
            score += 0.3 * resonance_score
        
        # 3. 风险评分（权重20%）
        risk_score = opportunity.get('risk_score', 0.5)
        if risk_score < 0.1:
            score += 0.2
        elif risk_score < 0.2:
            score += 0.1
        
        # 4. 置信度（权重10%）
        confidence = opportunity.get('confidence', 0.5)
        if confidence > 0.8:
            score += 0.1
        elif confidence > 0.6:
            score += 0.05
        
        return score