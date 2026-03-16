# -*- coding: utf-8 -*-
"""
全榜生命周期追踪器

记录所有曾经上榜（进入top_targets）的票的完整轨迹
无论是否被系统实际买入

【核心价值】
解决"只记录买卖了什么"vs"所有上榜票的命运"的信息不对称问题

Author: CTO Research Lab
Date: 2026-03-16
"""
import json
import csv
import os
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class StockLifecycle:
    """
    股票生命周期数据结构
    
    记录一只股票从上榜到追踪结束的完整轨迹
    """
    code: str
    first_appear_time: str = ""           # 第一次上榜时间
    last_appear_time: str = ""            # 最后一次上榜时间
    appear_count: int = 0                 # 上榜次数
    peak_score: float = 0.0               # 历史最高分
    first_appear_price: float = 0.0       # 首次上榜时价格
    peak_price: float = 0.0               # 上榜期间最高价
    final_price: float = 0.0              # 收盘/追踪结束时价格
    max_gain_pct: float = 0.0             # 从首次上榜到最高价的涨幅（%）
    final_gain_pct: float = 0.0           # 从首次上榜到结束的涨幅（%）
    was_bought: bool = False              # 是否被系统买入
    buy_price: float = 0.0                # 买入价（未买入为0）
    sell_price: float = 0.0               # 卖出价（未卖出为0）
    actual_pnl_pct: float = 0.0           # 实际盈亏%（未买入为0）
    missed_gain_pct: float = 0.0          # 错过的涨幅（was_bought=True时为0）
    peak_trigger_type: str = ""           # 最高分时的触发类型
    score_history: List[float] = field(default_factory=list)    # 每次上榜的分数列表
    price_history: List[float] = field(default_factory=list)    # 价格历史（最多300个点）
    trigger_types_history: List[str] = field(default_factory=list)  # 触发类型历史
    
    def to_dict(self) -> Dict:
        """转换为字典（用于JSON序列化）"""
        return asdict(self)


class UniversalTracker:
    """
    全榜生命周期追踪器
    
    记录所有曾经上榜（进入top_targets）的票的完整轨迹
    无论是否被系统实际买入
    """
    
    # 价格历史上限，防止内存泄漏
    MAX_PRICE_HISTORY = 300
    MAX_SCORE_HISTORY = 30
    
    def __init__(self, session_id: str = None):
        """
        初始化追踪器
        
        Args:
            session_id: 会话ID（默认使用当前日期时间）
        """
        self.session_id = session_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        self.registry: Dict[str, StockLifecycle] = {}
        self._bought_codes: set = set()    # 已买入股票代码集合
        self._sold_codes: Dict[str, float] = {}  # {code: sell_price} 已卖出股票价格
        
        logger.info(f"[OK] UniversalTracker初始化完成 | 会话ID: {self.session_id}")

    def on_frame(
        self, 
        top_targets: List[Dict], 
        current_time: datetime,
        executed_trade: Dict = None
    ):
        """
        每帧调用，传入当前榜单和当帧是否有实际成交
        
        Args:
            top_targets: 当前榜单（current_top_targets）
            current_time: 当前时间
            executed_trade: 当帧成交信息，格式：
                {'action': 'BUY'|'SELL', 'stock_code': str, 'price': float, 'reason': str}
                或 None（无成交）
        """
        time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # 处理成交信息
        if executed_trade:
            self._process_trade(executed_trade, time_str)
        
        # 更新榜单中的股票状态
        for target in top_targets:
            code = target.get('code', '')
            if not code:
                continue
            
            score = target.get('score', 0)
            price = target.get('price', 0)
            trigger_type = target.get('trigger_type', '') or ''
            
            self._update_stock_on_appear(code, score, price, trigger_type, time_str)

    def _process_trade(self, trade: Dict, time_str: str):
        """
        处理成交信息
        
        Args:
            trade: 成交字典
            time_str: 时间字符串
        """
        action = trade.get('action', '')
        code = trade.get('stock_code', '')
        price = trade.get('price', 0)
        
        if not code:
            return
        
        if action == 'BUY':
            self._bought_codes.add(code)
            lifecycle = self._get_or_create(code)
            lifecycle.was_bought = True
            lifecycle.buy_price = price
            logger.info(f"📊 [追踪] {code} 买入记录 @¥{price:.2f}")
        
        elif action == 'SELL':
            self._sold_codes[code] = price
            lifecycle = self.registry.get(code)
            if lifecycle:
                lifecycle.sell_price = price
                if lifecycle.buy_price > 0:
                    lifecycle.actual_pnl_pct = (price - lifecycle.buy_price) / lifecycle.buy_price * 100
                logger.info(
                    f"📊 [追踪] {code} 卖出记录 @¥{price:.2f} | "
                    f"盈亏:{lifecycle.actual_pnl_pct:+.2f}%"
                )

    def _get_or_create(self, code: str) -> StockLifecycle:
        """获取或创建股票生命周期记录"""
        if code not in self.registry:
            self.registry[code] = StockLifecycle(code=code)
        return self.registry[code]

    def _update_stock_on_appear(
        self, 
        code: str, 
        score: float, 
        price: float, 
        trigger_type: str,
        time_str: str
    ):
        """
        更新股票上榜状态
        
        Args:
            code: 股票代码
            score: 当前分数
            price: 当前价格
            trigger_type: 触发类型
            time_str: 时间字符串
        """
        lifecycle = self._get_or_create(code)
        
        # 首次上榜
        if lifecycle.appear_count == 0:
            lifecycle.first_appear_time = time_str
            lifecycle.first_appear_price = price
            lifecycle.peak_price = price
            lifecycle.peak_score = score
        
        # 更新上榜次数
        lifecycle.appear_count += 1
        lifecycle.last_appear_time = time_str
        
        # 更新最高分
        if score > lifecycle.peak_score:
            lifecycle.peak_score = score
            lifecycle.peak_trigger_type = trigger_type
        
        # 更新最高价
        if price > lifecycle.peak_price:
            lifecycle.peak_price = price
        
        # 更新最终价格
        lifecycle.final_price = price
        
        # 计算涨幅
        if lifecycle.first_appear_price > 0:
            lifecycle.max_gain_pct = (lifecycle.peak_price - lifecycle.first_appear_price) / lifecycle.first_appear_price * 100
            lifecycle.final_gain_pct = (price - lifecycle.first_appear_price) / lifecycle.first_appear_price * 100
        
        # 记录分数历史（限制长度）
        lifecycle.score_history.append(score)
        if len(lifecycle.score_history) > self.MAX_SCORE_HISTORY:
            lifecycle.score_history = lifecycle.score_history[-self.MAX_SCORE_HISTORY:]
        
        # 记录价格历史（限制长度）
        lifecycle.price_history.append(price)
        if len(lifecycle.price_history) > self.MAX_PRICE_HISTORY:
            lifecycle.price_history = lifecycle.price_history[-self.MAX_PRICE_HISTORY:]
        
        # 记录触发类型历史
        lifecycle.trigger_types_history.append(trigger_type)

    def on_price_update(self, stock_code: str, current_price: float, current_time: datetime):
        """
        持续更新已上榜票的价格（用于计算错过收益）
        即使该票已离榜，仍需持续更新直到收盘
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            current_time: 当前时间
        """
        lifecycle = self.registry.get(stock_code)
        if not lifecycle:
            return
        
        # 更新价格
        lifecycle.final_price = current_price
        
        # 更新最高价
        if current_price > lifecycle.peak_price:
            lifecycle.peak_price = current_price
        
        # 重新计算涨幅
        if lifecycle.first_appear_price > 0:
            lifecycle.max_gain_pct = (lifecycle.peak_price - lifecycle.first_appear_price) / lifecycle.first_appear_price * 100
            lifecycle.final_gain_pct = (current_price - lifecycle.first_appear_price) / lifecycle.first_appear_price * 100
        
        # 计算错过收益（未买入时）
        if not lifecycle.was_bought and lifecycle.first_appear_price > 0:
            lifecycle.missed_gain_pct = lifecycle.max_gain_pct

    def get_full_report(self) -> Dict:
        """
        返回完整战报
        
        Returns:
            战报字典，包含摘要和所有股票详情
        """
        all_stocks = list(self.registry.values())
        bought_stocks = [s for s in all_stocks if s.was_bought]
        missed_stocks = [s for s in all_stocks if not s.was_bought]
        
        # 找出最可惜的错过（涨幅最大的未买入票）
        best_missed = None
        if missed_stocks:
            best_missed = max(missed_stocks, key=lambda x: x.max_gain_pct)
        
        # 找出最差的买入
        worst_bought = None
        if bought_stocks:
            worst_bought = min(bought_stocks, key=lambda x: x.actual_pnl_pct)
        
        return {
            'session_id': self.session_id,
            'summary': {
                'total_appeared': len(all_stocks),
                'bought_count': len(bought_stocks),
                'missed_count': len(missed_stocks),
                'best_missed': self._lifecycle_to_summary(best_missed) if best_missed else None,
                'worst_bought': self._lifecycle_to_summary(worst_bought) if worst_bought else None,
                'avg_bought_pnl': sum(s.actual_pnl_pct for s in bought_stocks) / len(bought_stocks) if bought_stocks else 0,
                'avg_missed_gain': sum(s.max_gain_pct for s in missed_stocks) / len(missed_stocks) if missed_stocks else 0,
            },
            'all_stocks': [s.to_dict() for s in sorted(all_stocks, key=lambda x: x.peak_score, reverse=True)]
        }

    def _lifecycle_to_summary(self, lifecycle: StockLifecycle) -> Dict:
        """将StockLifecycle转换为摘要字典"""
        return {
            'code': lifecycle.code,
            'peak_score': lifecycle.peak_score,
            'first_appear_price': lifecycle.first_appear_price,
            'max_gain_pct': lifecycle.max_gain_pct,
            'actual_pnl_pct': lifecycle.actual_pnl_pct,
            'was_bought': lifecycle.was_bought
        }

    def get_missed_opportunities(self) -> List[StockLifecycle]:
        """
        获取错过的机会
        
        Returns:
            was_bought=False 且 max_gain_pct>3.0 的列表，按 max_gain_pct 降序
        """
        missed = [
            s for s in self.registry.values() 
            if not s.was_bought and s.max_gain_pct > 3.0
        ]
        return sorted(missed, key=lambda x: x.max_gain_pct, reverse=True)

    def get_bought_stocks(self) -> List[StockLifecycle]:
        """获取已买入的股票列表"""
        return [s for s in self.registry.values() if s.was_bought]

    def export_to_json(self, filepath: str):
        """
        导出到 JSON 文件
        
        Args:
            filepath: 输出文件路径
        """
        report = self.get_full_report()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[OK] 全榜追踪战报已导出JSON: {filepath}")

    def export_to_csv(self, filepath: str):
        """
        导出 CSV，每行一只股票
        
        Args:
            filepath: 输出文件路径
        """
        all_stocks = list(self.registry.values())
        
        if not all_stocks:
            logger.warning("[WARN] 无追踪数据可导出")
            return
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        fieldnames = [
            'code', 'first_appear_time', 'last_appear_time', 'appear_count',
            'peak_score', 'first_appear_price', 'peak_price', 'final_price',
            'max_gain_pct', 'final_gain_pct', 'was_bought', 'buy_price',
            'sell_price', 'actual_pnl_pct', 'missed_gain_pct', 'peak_trigger_type'
        ]
        
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for stock in all_stocks:
                writer.writerow(asdict(stock))
        
        logger.info(f"[OK] 全榜追踪战报已导出CSV: {filepath}")

    def get_stats(self) -> Dict:
        """
        获取统计摘要
        
        Returns:
            统计字典
        """
        all_stocks = list(self.registry.values())
        bought = [s for s in all_stocks if s.was_bought]
        missed = [s for s in all_stocks if not s.was_bought]
        
        return {
            'session_id': self.session_id,
            'total_tracked': len(all_stocks),
            'bought_count': len(bought),
            'missed_count': len(missed),
            'win_rate': len([s for s in bought if s.actual_pnl_pct > 0]) / len(bought) * 100 if bought else 0,
            'avg_score': sum(s.peak_score for s in all_stocks) / len(all_stocks) if all_stocks else 0
        }
