# -*- coding: utf-8 -*-
"""
交易决策大脑 - 单吊模式

职责：接收每帧打分结果，输出「买/卖/持仓/观望」决策
不负责撮合，只负责「该不该」

【单吊约束（硬红线）】
- 任何时刻最多持有 1 只股票
- 持仓期间不允许换仓（必须先平仓才能开新仓）
- 资金 100% 集中

Author: CTO Research Lab
Date: 2026-03-16
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class DecisionResult:
    """决策结果数据结构"""
    action: str              # 'BUY' | 'SELL' | 'HOLD' | 'WATCH'
    stock_code: str = ""     # BUY时有效
    price: float = 0.0       # 建议价格
    reason: str = ""         # 决策原因（用于战报）
    score: float = 0.0       # 触发分数
    trigger_type: str = ""   # 触发类型


class TradeDecisionBrain:
    """
    交易决策大脑 - 单吊模式
    
    职责：接收每帧打分结果，输出「买/卖/持仓/观望」决策
    不负责撮合，只负责「该不该」
    """
    
    def __init__(self, config: dict = None):
        """
        初始化决策大脑
        
        Args:
            config: 可配置参数字典，支持覆盖默认值
        """
        config = config or {}
        
        # 可配置参数（全部有默认值）
        self.entry_score_threshold: float = config.get('entry_score_threshold', 65.0)
        self.stop_loss_pct: float = config.get('stop_loss_pct', -0.03)      # -3%
        self.take_profit_pct: float = config.get('take_profit_pct', 0.08)    # +8%
        self.max_hold_minutes: int = config.get('max_hold_minutes', 120)     # 2小时
        self.replace_threshold: float = config.get('replace_threshold', 20.0) # 新票比持仓高20分才换
        
        # 内部状态
        self.current_position: Optional[Dict] = None   # 当前持仓信息
        self.entry_time: Optional[datetime] = None     # 入场时间
        self.entry_price: float = 0.0                  # 入场价格
        self.entry_score: float = 0.0                  # 入场时分数
        self.decision_log: List[Dict] = []             # 决策日志
        self.held_stock_code: str = ""                 # 持仓股票代码
        
        logger.info(
            f"[OK] TradeDecisionBrain初始化完成 | "
            f"入场门槛:{self.entry_score_threshold}分 | "
            f"止损:{self.stop_loss_pct*100:.1f}% | "
            f"止盈:{self.take_profit_pct*100:.1f}% | "
            f"最大持仓:{self.max_hold_minutes}分钟"
        )

    def on_new_frame(
        self,
        top_targets: List[Dict],
        current_time: datetime,
        held_stock_current_price: float = 0.0
    ) -> Dict:
        """
        每帧调用一次，返回决策字典
        
        Args:
            top_targets: 当前榜单（来自current_top_targets），字段包括：
                - code: str               # 股票代码
                - score: float            # 最终分数
                - price: float            # 当前价格
                - trigger_type: str|None  # 触发类型
                - trigger_confidence: float
                - ignition_prob: float
                - mfe: float
                - sustain_ratio: float
            current_time: 当前时间
            held_stock_current_price: 持仓股当前价格（无持仓传0）
            
        Returns:
            决策字典：
            {
                'action': 'BUY' | 'SELL' | 'HOLD' | 'WATCH',
                'stock_code': str,     # BUY时有效
                'price': float,        # 建议价格
                'reason': str,         # 决策原因（用于战报）
                'score': float,        # 触发分数
                'trigger_type': str    # 触发类型
            }
        """
        # 默认观望
        decision = DecisionResult(action='WATCH')
        
        # 1. 有持仓时，优先判断出场
        if self.current_position is not None:
            exit_decision = self._should_exit(held_stock_current_price, current_time)
            if exit_decision[0]:
                decision.action = 'SELL'
                decision.stock_code = self.held_stock_code
                decision.price = held_stock_current_price
                decision.reason = exit_decision[1]
                decision.score = self.entry_score
                
                # 记录决策日志
                self._log_decision(current_time, decision)
                
                logger.info(
                    f"🔔 [卖出信号] {decision.stock_code} | "
                    f"原因:{decision.reason} | "
                    f"价格:{decision.price:.2f} | "
                    f"盈亏:{(held_stock_current_price - self.entry_price) / self.entry_price * 100:+.2f}%"
                )
                
                return self._decision_to_dict(decision)
            
            # 持仓未触发出场，继续持有
            decision.action = 'HOLD'
            decision.stock_code = self.held_stock_code
            decision.price = held_stock_current_price
            decision.reason = f"持仓中，等待出场信号"
            decision.score = self.entry_score
            
            self._log_decision(current_time, decision)
            return self._decision_to_dict(decision)
        
        # 2. 无持仓时，判断入场
        entry_decision = self._should_enter(top_targets)
        if entry_decision is not None:
            decision.action = 'BUY'
            decision.stock_code = entry_decision['code']
            decision.price = entry_decision['price']
            decision.reason = f"分数{entry_decision['score']:.1f}>={self.entry_score_threshold}，触发入场"
            decision.score = entry_decision['score']
            decision.trigger_type = entry_decision.get('trigger_type', '')
            
            # 更新持仓状态
            self.current_position = entry_decision
            self.entry_time = current_time
            self.entry_price = entry_decision['price']
            self.entry_score = entry_decision['score']
            self.held_stock_code = entry_decision['code']
            
            # 记录决策日志
            self._log_decision(current_time, decision)
            
            logger.info(
                f"💰 [买入信号] {decision.stock_code} | "
                f"分数:{decision.score:.1f} | "
                f"价格:{decision.price:.2f} | "
                f"触发:{decision.trigger_type}"
            )
            
            return self._decision_to_dict(decision)
        
        # 3. 无入场信号，继续观望
        if top_targets:
            top1 = top_targets[0]
            decision.reason = f"最高分{top1['score']:.1f}<{self.entry_score_threshold}，未达入场门槛"
        else:
            decision.reason = "榜单为空，继续观望"
        
        self._log_decision(current_time, decision)
        return self._decision_to_dict(decision)

    def _should_enter(self, top_targets: List[Dict]) -> Optional[Dict]:
        """
        入场判断逻辑
        
        Args:
            top_targets: 当前榜单
            
        Returns:
            入场目标dict，或None（不入场）
            
        逻辑：
        1. 无持仓时：top_targets[0].score >= entry_score_threshold 且 trigger_type 不为 None
        2. 有持仓时：永远返回 None（单吊不换仓）
        """
        # 有持仓时不入场（单吊约束）
        if self.current_position is not None:
            return None
        
        if not top_targets:
            return None
        
        # 取榜首
        top1 = top_targets[0]
        
        # 检查分数门槛
        if top1.get('score', 0) < self.entry_score_threshold:
            return None
        
        # 检查是否有有效触发类型（防止无脑买入）
        trigger_type = top1.get('trigger_type')
        if trigger_type is None or trigger_type == '':
            # 允许高分无触发类型入场（旧模式兼容）
            pass
        
        return {
            'code': top1.get('code', ''),
            'score': top1.get('score', 0),
            'price': top1.get('price', 0),
            'trigger_type': trigger_type or '',
            'trigger_confidence': top1.get('trigger_confidence', 0),
            'ignition_prob': top1.get('ignition_prob', 0),
            'mfe': top1.get('mfe', 0),
            'sustain_ratio': top1.get('sustain_ratio', 0)
        }

    def _should_exit(self, current_price: float, current_time: datetime) -> Tuple[bool, str]:
        """
        出场判断逻辑（按优先级）
        
        Args:
            current_price: 当前价格
            current_time: 当前时间
            
        Returns:
            (是否出场, 原因)
            
        逻辑：
        1. 止损：(current_price - entry_price) / entry_price <= stop_loss_pct
        2. 止盈：(current_price - entry_price) / entry_price >= take_profit_pct
        3. 超时：持仓超过 max_hold_minutes 分钟
        4. 以上都不触发则返回 False
        """
        if self.entry_price <= 0:
            return False, ""
        
        # 计算盈亏比例
        pnl_ratio = (current_price - self.entry_price) / self.entry_price
        
        # 1. 止损检查
        if pnl_ratio <= self.stop_loss_pct:
            return True, f"止损触发: {pnl_ratio*100:.2f}% <= {self.stop_loss_pct*100:.1f}%"
        
        # 2. 止盈检查
        if pnl_ratio >= self.take_profit_pct:
            return True, f"止盈触发: {pnl_ratio*100:.2f}% >= {self.take_profit_pct*100:.1f}%"
        
        # 3. 超时检查
        if self.entry_time is not None:
            hold_minutes = (current_time - self.entry_time).total_seconds() / 60
            if hold_minutes >= self.max_hold_minutes:
                return True, f"持仓超时: {hold_minutes:.0f}分钟 >= {self.max_hold_minutes}分钟"
        
        return False, ""

    def clear_position(self):
        """
        清除持仓状态（卖出后调用）
        """
        self.current_position = None
        self.entry_time = None
        self.entry_price = 0.0
        self.entry_score = 0.0
        self.held_stock_code = ""

    def _log_decision(self, time: datetime, decision: DecisionResult):
        """
        记录决策日志
        
        Args:
            time: 决策时间
            decision: 决策结果
        """
        self.decision_log.append({
            'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'action': decision.action,
            'stock_code': decision.stock_code,
            'reason': decision.reason,
            'score': decision.score,
            'price': decision.price
        })

    def _decision_to_dict(self, decision: DecisionResult) -> Dict:
        """将DecisionResult转换为dict"""
        return {
            'action': decision.action,
            'stock_code': decision.stock_code,
            'price': decision.price,
            'reason': decision.reason,
            'score': decision.score,
            'trigger_type': decision.trigger_type
        }

    def get_decision_log(self) -> List[Dict]:
        """获取决策日志"""
        return self.decision_log.copy()

    def get_position_info(self) -> Optional[Dict]:
        """
        获取当前持仓信息
        
        Returns:
            持仓信息dict，或None（无持仓）
        """
        if self.current_position is None:
            return None
        
        return {
            'stock_code': self.held_stock_code,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.strftime('%Y-%m-%d %H:%M:%S') if self.entry_time else '',
            'entry_score': self.entry_score
        }

    def get_config(self) -> Dict:
        """获取当前配置"""
        return {
            'entry_score_threshold': self.entry_score_threshold,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'max_hold_minutes': self.max_hold_minutes,
            'replace_threshold': self.replace_threshold
        }

    def update_config(self, config: Dict):
        """
        更新配置
        
        Args:
            config: 新配置字典
        """
        if 'entry_score_threshold' in config:
            self.entry_score_threshold = config['entry_score_threshold']
        if 'stop_loss_pct' in config:
            self.stop_loss_pct = config['stop_loss_pct']
        if 'take_profit_pct' in config:
            self.take_profit_pct = config['take_profit_pct']
        if 'max_hold_minutes' in config:
            self.max_hold_minutes = config['max_hold_minutes']
        if 'replace_threshold' in config:
            self.replace_threshold = config['replace_threshold']
        
        logger.info(f"[OK] TradeDecisionBrain配置已更新: {config}")
