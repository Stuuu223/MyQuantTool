#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO Phase 4】统一战法核心 V18 - 实盘大脑重构

重构要点：
1. 物理植入换手率×100修正 (volume手→股)
2. 物理植入Ratio化指标 (摒弃绝对资金)
3. 物理植入ShortTermMemory跨日接力引擎
4. 挂载日线校验锚机制

Author: CTO
Version: V18.0.0
Date: 2026-02-22
"""

import json
import redis
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import pandas as pd
import numpy as np

from logic.strategies.event_detector import EventManager, BaseEventDetector, TradingEvent, EventType
from logic.utils.logger import get_logger

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

logger = get_logger(__name__)


@dataclass
class ShortTermMemory:
    """跨日接力记忆单元"""
    stock_code: str
    date: str
    close_price: float
    turnover_rate: float  # 全天换手率
    is_strong_momentum: bool  # 是否强势动能
    max_amount_window: str  # 最大资金窗口时间
    max_amount: float  # 最大窗口资金
    score: float  # 强度评分
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ShortTermMemory':
        return cls(**data)


class DailyVolumeAnchor:
    """日线校验锚 - 确保Tick累加与日线数据一致"""
    
    def __init__(self, max_error_pct: float = 10.0):
        self.max_error_pct = max_error_pct
        self.cache = {}
    
    def validate_tick_volume(
        self,
        stock_code: str,
        date: str,
        tick_total_amount: float,
        tick_total_volume: float
    ) -> Tuple[bool, Dict]:
        """
        校验Tick累加与日线数据
        
        Returns:
            (是否通过, 详细信息)
        """
        # 获取日线数据
        daily_data = self._get_daily_data(stock_code, date)
        if not daily_data:
            return False, {'error': '无法获取日线数据'}
        
        daily_amount = daily_data['amount']
        daily_volume = daily_data['volume']
        
        # 计算差异
        amount_error_pct = abs(tick_total_amount - daily_amount) / daily_amount * 100 if daily_amount > 0 else 0
        volume_error_pct = abs(tick_total_volume - daily_volume) / daily_volume * 100 if daily_volume > 0 else 0
        
        result = {
            'stock_code': stock_code,
            'date': date,
            'tick_amount': tick_total_amount,
            'daily_amount': daily_amount,
            'amount_error_pct': amount_error_pct,
            'tick_volume': tick_total_volume,
            'daily_volume': daily_volume,
            'volume_error_pct': volume_error_pct,
            'passed': amount_error_pct <= self.max_error_pct
        }
        
        if not result['passed']:
            logger.error(f"🚨 [日线校验锚] {stock_code} {date} 数据异常!")
            logger.error(f"   Tick累加: {tick_total_amount/10000:.1f}万")
            logger.error(f"   日线数据: {daily_amount/10000:.1f}万")
            logger.error(f"   误差: {amount_error_pct:.1f}% > {self.max_error_pct}%")
        
        return result['passed'], result
    
    def _get_daily_data(self, stock_code: str, date: str) -> Optional[Dict]:
        """从QMT获取日线数据"""
        if not QMT_AVAILABLE:
            return None
        
        try:
            result = xtdata.get_local_data(
                field_list=['open', 'close', 'high', 'low', 'volume', 'amount'],
                stock_list=[stock_code],
                period='1d',
                start_time=date,
                end_time=date
            )
            
            if result and stock_code in result and not result[stock_code].empty:
                row = result[stock_code].iloc[0]
                return {
                    'open': row['open'],
                    'close': row['close'],
                    'high': row['high'],
                    'low': row['low'],
                    'volume': row['volume'] * 100,  # 手→股
                    'amount': row['amount']
                }
        except Exception as e:
            logger.error(f"❌ [日线锚] 获取日线数据失败: {e}")
        
        return None


class CrossDayRelayEngine:
    """跨日接力追踪引擎"""
    
    def __init__(self, memory_file: str = "data/short_term_memory.json"):
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory: Dict[str, ShortTermMemory] = {}
        self.bonus_pct = 30.0  # 强势票隔日加分30%
        self._load_memory()
    
    def _load_memory(self):
        """加载历史记忆"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for code, mem_data in data.items():
                        self.memory[code] = ShortTermMemory.from_dict(mem_data)
                logger.info(f"📚 [接力引擎] 加载记忆: {len(self.memory)} 只票")
            except Exception as e:
                logger.error(f"❌ [接力引擎] 加载记忆失败: {e}")
    
    def _save_memory(self):
        """保存记忆到文件"""
        try:
            data = {code: mem.to_dict() for code, mem in self.memory.items()}
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ [接力引擎] 保存记忆失败: {e}")
    
    def analyze_day_end(
        self,
        stock_code: str,
        date: str,
        close_price: float,
        turnover_rate: float,
        windows: List[Dict]
    ) -> bool:
        """
        收盘分析，判断是否为强势动能
        
        Returns:
            是否为STRONG_MOMENTUM
        """
        # 找到最大资金窗口
        max_window = max(windows, key=lambda x: x.get('amount', 0))
        max_amount = max_window.get('amount', 0)
        max_time = max_window.get('time', '')
        
        # 评分标准
        score = 0.0
        is_strong = False
        
        # 条件1: 换手率 > 5% (真实换手率)
        if turnover_rate > 5.0:
            score += 40.0
        
        # 条件2: 收盘光头阳线 (涨幅 > 8%)
        day_change = windows[-1].get('change_pct', 0) if windows else 0
        if day_change > 8.0:
            score += 30.0
        
        # 条件3: 有集中资金脉冲 (>500万)
        if max_amount > 5000000:  # 500万
            score += 30.0
        
        # 总分 >= 70 判定为STRONG_MOMENTUM
        is_strong = score >= 70.0
        
        if is_strong:
            memory = ShortTermMemory(
                stock_code=stock_code,
                date=date,
                close_price=close_price,
                turnover_rate=turnover_rate,
                is_strong_momentum=True,
                max_amount_window=max_time,
                max_amount=max_amount,
                score=score
            )
            self.memory[stock_code] = memory
            self._save_memory()
            
            logger.info(f"🔥 [接力引擎] {stock_code} 标记为STRONG_MOMENTUM!")
            logger.info(f"   日期: {date}, 收盘: {close_price:.2f}")
            logger.info(f"   换手: {turnover_rate:.2f}%, 最强窗口: {max_time}")
            logger.info(f"   评分: {score:.1f}/100")
        
        return is_strong
    
    def get_relay_bonus(self, stock_code: str, current_date: str) -> float:
        """
        获取隔日接力加分
        
        Returns:
            加分百分比 (0.0 - 30.0)
        """
        if stock_code not in self.memory:
            return 0.0
        
        memory = self.memory[stock_code]
        
        # 只给昨天的强势票加分
        memory_date = datetime.strptime(memory.date, '%Y%m%d')
        current = datetime.strptime(current_date, '%Y%m%d')
        
        if (current - memory_date).days == 1 and memory.is_strong_momentum:
            logger.info(f"🚀 [接力引擎] {stock_code} 获得接力加分 +{self.bonus_pct}%")
            return self.bonus_pct
        
        return 0.0
    
    def clear_old_memory(self, days: int = 3):
        """清理过期记忆"""
        current = datetime.now()
        to_remove = []
        
        for code, mem in self.memory.items():
            mem_date = datetime.strptime(mem.date, '%Y%m%d')
            if (current - mem_date).days > days:
                to_remove.append(code)
        
        for code in to_remove:
            del self.memory[code]
        
        if to_remove:
            self._save_memory()
            logger.info(f"🧹 [接力引擎] 清理过期记忆: {len(to_remove)} 只票")


class UnifiedWarfareCoreV18:
    """
    统一战法核心 V18 - 重构版
    
    新特性:
    1. 换手率×100修正 (volume手→股)
    2. Ratio化指标 (摒弃绝对资金)
    3. 日线校验锚 (数据熔断机制)
    4. 跨日接力引擎 (ShortTermMemory)
    """
    
    # Ratio化阈值配置
    THRESHOLDS = {
        'turnover_5min_min': 0.01,  # 5分钟换手率 > 0.01%
        'money_efficiency_min': 50.0,  # 资金驱动效率 > 50
        'historical_ratio_min': 10.0,  # 历史Ratio > 10
        'confidence_min': 0.6,  # 置信度 > 60%
    }
    
    def __init__(self):
        """初始化V18核心"""
        self.daily_anchor = DailyVolumeAnchor(max_error_pct=10.0)
        self.relay_engine = CrossDayRelayEngine()
        
        # 统计
        self._total_ticks = 0
        self._total_events = 0
        self._data_corruptions = 0
        
        logger.info("✅ [统一战法核心 V18] 初始化完成")
        logger.info(f"   - 日线校验锚: 误差阈值 {self.daily_anchor.max_error_pct}%")
        logger.info(f"   - 跨日接力引擎: 加分 +{self.relay_engine.bonus_pct}%")
        logger.info(f"   - Ratio阈值: {self.THRESHOLDS}")
    
    def process_tick(
        self,
        stock_code: str,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[Dict]:
        """
        处理单个Tick数据
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
            context: 上下文
            
        Returns:
            检测到的事件，或None
        """
        self._total_ticks += 1
        
        # TODO: 实现Tick级检测逻辑
        # 这里需要接入真实的Tick数据流
        
        return None
    
    def analyze_day(
        self,
        stock_code: str,
        date: str,
        windows: List[Dict]
    ) -> Dict:
        """
        分析全天数据
        
        Args:
            stock_code: 股票代码
            date: 日期
            windows: 5分钟窗口数据列表
            
        Returns:
            分析结果
        """
        if not windows:
            return {'error': '无数据'}
        
        # 1. 计算全天统计 (CTO修正: ×100转万股)
        total_volume_shou = sum(w.get('volume', 0) for w in windows)  # 手
        total_volume = total_volume_shou * 100  # 股
        total_amount = sum(w.get('amount', 0) for w in windows)  # 元
        
        # 获取流通股本
        float_volume = self._get_float_volume(stock_code)
        turnover_rate = total_volume / float_volume * 100 if float_volume > 0 else 0
        
        # 2. 日线校验锚
        passed, anchor_result = self.daily_anchor.validate_tick_volume(
            stock_code, date, total_amount, total_volume
        )
        
        if not passed:
            self._data_corruptions += 1
            logger.error(f"🚨 [V18] {stock_code} {date} 数据校验失败，拒绝分析")
            return {
                'error': 'DATA_CORRUPTED',
                'anchor_result': anchor_result
            }
        
        # 3. 找到最强窗口
        strongest_window = max(windows, key=lambda x: x.get('intensity_score', 0))
        
        # 4. 跨日接力分析
        is_strong = self.relay_engine.analyze_day_end(
            stock_code, date,
            windows[-1].get('price', 0),
            turnover_rate,
            windows
        )
        
        result = {
            'stock_code': stock_code,
            'date': date,
            'total_amount': total_amount,
            'total_volume': total_volume,
            'turnover_rate': turnover_rate,
            'strongest_window': strongest_window,
            'is_strong_momentum': is_strong,
            'anchor_passed': True
        }
        
        logger.info(f"📊 [V18] {stock_code} {date} 分析完成")
        logger.info(f"   成交额: {total_amount/10000:.1f}万, 换手: {turnover_rate:.2f}%")
        logger.info(f"   强势动能: {'✅' if is_strong else '❌'}")
        
        return result
    
    def _get_float_volume(self, stock_code: str) -> float:
        """获取流通股本"""
        # TODO: 从配置或数据库获取
        default_volumes = {
            '300986.SZ': 246000000,  # 志特新材
            '300017.SZ': 2306141629,  # 网宿科技
            '301005.SZ': 836269091,  # 超捷股份
        }
        return default_volumes.get(stock_code, 1e9)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_ticks': self._total_ticks,
            'total_events': self._total_events,
            'data_corruptions': self._data_corruptions,
            'memory_count': len(self.relay_engine.memory)
        }


if __name__ == '__main__':
    # 测试V18核心
    print('='*70)
    print('【CTO Phase 4】统一战法核心 V18 测试')
    print('='*70)
    
    core = UnifiedWarfareCoreV18()
    
    print(f"\nV18核心初始化成功")
    print(f"统计: {core.get_stats()}")
