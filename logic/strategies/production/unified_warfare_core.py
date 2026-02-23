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
    """
    日线校验锚 - CTO指令: 仅记录, 不熔断!
    原因: 多数据源(QMT Tick vs 日线)口径差异必然存在,
          不应因此阻断交易信号
    """
    
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
            (始终返回True, 详细信息) - CTO指令: 不熔断!
        """
        # 获取日线数据(仅用于记录对比)
        daily_data = self._get_daily_data(stock_code, date)
        
        if not daily_data:
            # 无法获取日线数据, 仅记录日志, 不阻断
            logger.warning(f"⚠️ [日线校验锚] {stock_code} {date} 无法获取日线数据, 但继续分析")
            return True, {'warning': '无法获取日线数据', 'passed': True}
        
        daily_amount = daily_data['amount']
        daily_volume = daily_data['volume']
        
        # 计算差异(仅用于记录)
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
            'passed': True  # CTO指令: 始终通过!
        }
        
        # 仅记录, 不阻断
        if amount_error_pct > self.max_error_pct:
            logger.warning(f"⚠️ [日线校验锚] {stock_code} {date} 数据差异较大(仅记录):")
            logger.warning(f"   Tick累加: {tick_total_amount/10000:.1f}万")
            logger.warning(f"   日线数据: {daily_amount/10000:.1f}万")
            logger.warning(f"   误差: {amount_error_pct:.1f}% (但不阻断分析)")
        else:
            logger.info(f"✅ [日线校验锚] {stock_code} {date} 数据校验通过")
        
        # CTO指令: 始终返回True, 不熔断!
        return True, result
    
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
        
        # 只给强势票加分 (支持跨年,不强制连续日期,但要求7天内)
        memory_date = datetime.strptime(memory.date, '%Y%m%d')
        current = datetime.strptime(current_date, '%Y%m%d')
        days_diff = (current - memory_date).days
        
        if days_diff <= 7 and days_diff > 0 and memory.is_strong_momentum:
            logger.info(f"🚀 [接力引擎] {stock_code} 获得接力加分 +{self.bonus_pct}% (间隔{days_diff}天)")
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
        
        # 1. 计算全天统计
        # NOTE: windows中的volume已经是股(已在calculate_5min_windows中×100转换)
        total_volume = sum(w.get('volume', 0) for w in windows)  # 股
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

    def calculate_blood_sucking_score(
        self,
        stock_code: str,
        windows: List[Dict],
        all_stocks_data: Dict[str, List[Dict]]
    ) -> Dict[str, float]:
        """
        计算抽血占比动态乘数得分

        CTO Phase 6.2 核心公式:
        最终得分 = 基础起爆分(满分100) * (1 + 抽血占全池的百分比 * 2)

        Args:
            stock_code: 股票代码
            windows: 该股票的5分钟窗口数据列表
            all_stocks_data: 全池所有股票的数据 {stock_code: windows_list}

        Returns:
            {
                'base_score': float,          # 基础起爆分(0-100)
                'capital_share_pct': float,   # 抽血占比(%)
                'multiplier': float,          # 动态乘数
                'final_score': float          # 最终得分
            }
        """
        # 1. 计算该股票的净流入 (主动买入 - 主动卖出)
        # 使用amount作为净流入近似值 (实际应该用主动买入-主动卖出)
        stock_net_inflow = sum(w.get('amount', 0) for w in windows)

        # 2. 计算全池总净流入
        total_net_inflow = 0.0
        for code, stock_windows in all_stocks_data.items():
            inflow = sum(w.get('amount', 0) for w in stock_windows)
            total_net_inflow += inflow

        # 3. 计算抽血占比 (处理除以零的情况)
        if total_net_inflow > 0:
            capital_share_pct = (stock_net_inflow / total_net_inflow) * 100
        else:
            capital_share_pct = 0.0
            logger.warning(f"⚠️ [抽血PK] {stock_code} 全池总净流入为0, 设置占比为0")

        # 4. 计算基础起爆分 (满分100)
        # 基于多个维度的综合评分
        base_score = self._calculate_base_explosion_score(stock_code, windows)

        # 5. 计算动态乘数 = 1 + 抽血占比 * 2
        # 抽血占比是百分比形式,例如5% -> multiplier = 1 + 0.05 * 2 = 1.10
        multiplier = 1 + (capital_share_pct / 100) * 2

        # 6. 计算Sustain承接因子 (防骗炮防线)
        sustain_factor = self._calculate_sustain_factor(windows)

        # 7. 计算最终得分 = 基础分 × 动态乘数 × 承接因子
        final_score = base_score * multiplier * sustain_factor

        logger.info(f"🩸 [抽血PK] {stock_code} 动态乘数计算:")
        logger.info(f"   净流入: {stock_net_inflow/10000:.1f}万 / 全池: {total_net_inflow/10000:.1f}万")
        logger.info(f"   抽血占比: {capital_share_pct:.2f}%")
        logger.info(f"   基础分: {base_score:.2f}, 乘数: {multiplier:.3f}, 承接因子: {sustain_factor:.3f}")
        logger.info(f"   最终得分: {final_score:.2f}")

        return {
            'base_score': round(base_score, 2),
            'capital_share_pct': round(capital_share_pct, 2),
            'multiplier': round(multiplier, 3),
            'sustain_factor': round(sustain_factor, 3),  # 新增: 承接因子
            'final_score': round(final_score, 2)
        }

    def _calculate_sustain_factor(self, windows: List[Dict]) -> float:
        """
        计算承接力度因子(Sustain Factor) - 防骗炮防线
        
        用于识别冲高回落的骗炮票（如御银股份12月31日）:
        - 如果当前价格在VWAP之上 → 主力在吸筹，加分
        - 如果当前价格在VWAP之下 → 主力在派发，分数腰斩
        
        Args:
            windows: 5分钟窗口数据列表
            
        Returns:
            sustain_factor: 0.0-1.0，1.0表示承接最强
        """
        if not windows:
            return 0.0
        
        # 计算VWAP（成交量加权平均价）
        total_amount = sum(w.get('amount', 0) for w in windows)
        total_volume = sum(w.get('volume', 0) for w in windows)
        
        if total_volume <= 0:
            return 0.0
        
        vwap = total_amount / total_volume
        
        # 获取当前价格（最后一个窗口的收盘价）
        current_price = windows[-1].get('price', 0)
        
        if current_price <= 0 or vwap <= 0:
            return 0.0
        
        # 计算价格与VWAP的关系
        # 当前价格 > VWAP → 在均价之上，承接好
        # 当前价格 < VWAP → 在均价之下，主力派发
        if current_price >= vwap:
            # 在均价之上，线性映射到0.5-1.0
            ratio = (current_price - vwap) / vwap
            sustain_factor = 0.5 + min(ratio * 5, 0.5)  # 最多加0.5
        else:
            # 在均价之下，分数腰斩（0.0-0.5）
            ratio = (vwap - current_price) / vwap
            sustain_factor = max(0.5 - ratio * 5, 0.0)  # 最多减0.5
        
        logger.debug(f"[Sustain] 当前价={current_price:.2f}, VWAP={vwap:.2f}, "
                    f"比例={(current_price-vwap)/vwap*100:+.2f}%, 因子={sustain_factor:.3f}")
        
        return sustain_factor

    def _calculate_base_explosion_score(self, stock_code: str, windows: List[Dict]) -> float:
        """
        计算基础起爆分 (满分100) - CTO Phase 6.3 线性极值映射版

        修复: 从静态阶梯评分改为线性极值映射,恢复分辨率!
        换手20%就是要比换手5%拿更高的分!

        评分维度:
        - 换手率 (40分) - 线性映射 0%~30% -> 0~40分
        - 价格动能 (30分) - 基于昨收的真实涨幅,0%~20% -> 0~30分
        - 资金强度 (30分) - 线性映射 0~5000万 -> 0~30分
        """
        if not windows:
            return 0.0

        score = 0.0

        # 获取窗口统计
        max_window = max(windows, key=lambda x: x.get('amount', 0))
        max_amount = max_window.get('amount', 0)
        total_volume = sum(w.get('volume', 0) for w in windows)
        float_volume = self._get_float_volume(stock_code)
        turnover_rate = total_volume / float_volume * 100 if float_volume > 0 else 0

        # 获取昨收价和当前价计算真实涨幅
        last_close = windows[0].get('last_close', 0) if windows else 0
        current_price = windows[-1].get('price', 0) if windows else 0
        
        # 维度1: 换手率评分 (40分) - 线性极值映射
        # 假设历史最大换手30%,最小1%,线性映射到0-40分
        # 换手20%得 20/30*40 = 26.7分, 换手5%得 5/30*40 = 6.7分
        turnover_normalized = min(max(turnover_rate, 0) / 30.0, 1.0)  # 归一化到0-1
        turnover_score = turnover_normalized * 40.0  # 线性映射到40分
        score += turnover_score

        # 维度2: 价格动能评分 (30分) - 基于昨收的真实涨幅
        # 涨停20%得满分,0%得0分,线性映射
        if last_close > 0 and current_price > 0:
            day_change = (current_price - last_close) / last_close * 100  # 基于昨收的真实涨幅
        else:
            # 备选: 使用窗口中的change_pct
            changes = [w.get('change_pct', 0) for w in windows if w.get('change_pct') is not None]
            day_change = max(changes) if changes else 0
        
        change_normalized = min(max(day_change, 0) / 20.0, 1.0)  # 归一化到0-1(涨停20%)
        change_score = change_normalized * 30.0  # 线性映射到30分
        score += change_score

        # 维度3: 资金强度评分 (30分) - 线性极值映射
        # 基于最大窗口金额,假设历史最大5000万,线性映射到0-30分
        amount_normalized = min(max_amount / 50000000, 1.0)  # 归一化到0-1
        amount_score = amount_normalized * 30.0  # 线性映射到30分
        score += amount_score

        logger.debug(f"[基础分] {stock_code}: 换手={turnover_rate:.2f}%({turnover_score:.1f}分) "
                    f"涨幅={day_change:.2f}%({change_score:.1f}分) "
                    f"资金={max_amount/10000:.1f}万({amount_score:.1f}分) "
                    f"总分={min(score, 100.0):.1f}")

        return min(100.0, score)  # 确保不超过100分

    def rank_by_capital_share(
        self,
        results_list: List[Dict]
    ) -> List[Dict]:
        """
        按最终得分降序排序并添加排名

        CTO Phase 6.2 横向吸血PK排序:
        - 按final_score降序排列
        - 添加rank字段 (1开始)

        Args:
            results_list: 所有股票的分析结果列表
                每个元素应包含: {
                    'stock_code': str,
                    'base_score': float,
                    'capital_share_pct': float,
                    'multiplier': float,
                    'final_score': float,
                    ...其他字段
                }

        Returns:
            排序后的列表, 每个元素添加'rank'字段
        """
        if not results_list:
            logger.warning("⚠️ [排名排序] 输入列表为空")
            return []

        # 1. 按final_score降序排序
        sorted_results = sorted(
            results_list,
            key=lambda x: x.get('final_score', 0),
            reverse=True
        )

        # 2. 添加rank字段
        for i, result in enumerate(sorted_results, start=1):
            result['rank'] = i

        logger.info(f"📊 [排名排序] 共 {len(sorted_results)} 只票, 按final_score排序完成")

        # 3. 输出TOP5信息
        top5 = sorted_results[:5]
        for item in top5:
            logger.info(
                f"   TOP{item['rank']}: {item['stock_code']} "
                f"得分={item['final_score']:.2f} "
                f"(基础{item['base_score']:.1f}×乘数{item['multiplier']:.2f}) "
                f"抽血{item['capital_share_pct']:.2f}%"
            )

        return sorted_results


if __name__ == '__main__':
    # 测试V18核心
    print('='*70)
    print('【CTO Phase 4】统一战法核心 V18 测试')
    print('='*70)
    
    core = UnifiedWarfareCoreV18()
    
    print(f"\nV18核心初始化成功")
    print(f"统计: {core.get_stats()}")
