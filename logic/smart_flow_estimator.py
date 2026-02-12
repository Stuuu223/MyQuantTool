#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能资金流估算器（QMT免费版增强）

核心方法：四维交叉验证 (QPST)
- Quantity: 成交量脉冲分析
- Price: 价格走势形态
- Space: 换手率/流通性
- Time: 持续时间验证

反诱多检测：
- 对倒识别：成交量异常但买卖盘挂单不变
- 尾盘拉升：最后30分钟突然异动
- 连板风险：连续涨停后的首次开板

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 1 (单股票监控版)
"""

import time
import json
import sqlite3
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics
from pathlib import Path

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

from logic.utils.logger import get_logger

logger = get_logger(__name__)


class SmartFlowEstimator:
    """
    智能资金流估算器（QMT免费版增强）
    
    核心方法：四维交叉验证 (QPST)
    - Quantity: 成交量脉冲分析
    - Price: 价格走势形态
    - Space: 换手率/流通性
    - Time: 持续时间验证
    
    反诱多检测：
    - 对倒识别：成交量异常但买卖盘挂单不变
    - 尾盘拉升：最后30分钟突然异动
    - 连板风险：连续涨停后的首次开板
    """
    
    def __init__(self, 
                 tick_window=20,      # Tick级别窗口（秒）
                 day_window=5,        # 日线级别窗口（天）
                 enable_persistence=True):  # 是否启用持久化
        """
        初始化智能资金流估算器
        
        Args:
            tick_window: Tick级别滑动窗口大小
            day_window: 日线级别滑动窗口大小
            enable_persistence: 是否启用SQLite持久化（避免内存溢出）
        """
        if not QMT_AVAILABLE:
            raise RuntimeError("⚠️ xtquant 未安装，SmartFlowEstimator 不可用")
        
        # Tick级别历史（内存缓存）
        self.tick_history = {}  # {code: deque([{volume, price, time, bid_ask}, ...])}
        self.tick_window = tick_window
        
        # 日线级别历史
        self.day_window = day_window
        
        # 持久化配置
        self.enable_persistence = enable_persistence
        if enable_persistence:
            self._init_persistence()
        
        # 加载本地股本信息
        self.equity_info = self._load_equity_info()
        
        logger.info("✅ SmartFlowEstimator 初始化完成")
        logger.info(f"   - Tick窗口: {tick_window} 秒")
        logger.info(f"   - 日线窗口: {day_window} 天")
        logger.info(f"   - 持久化: {'启用' if enable_persistence else '禁用'}")
    
    def _init_persistence(self):
        """初始化SQLite持久化存储"""
        db_path = Path('data/tick_history.db')
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.db_conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db_conn.execute('''
            CREATE TABLE IF NOT EXISTS tick_history (
                code TEXT,
                timestamp INTEGER,
                volume REAL,
                price REAL,
                amount REAL,
                bid_total REAL,
                ask_total REAL,
                PRIMARY KEY (code, timestamp)
            )
        ''')
        self.db_conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_code_time 
            ON tick_history(code, timestamp DESC)
        ''')
        self.db_conn.commit()
        logger.debug("✅ Tick历史持久化存储已初始化")
    
    def _load_equity_info(self) -> dict:
        """加载本地股本信息"""
        try:
            with open('data/equity_info.json', 'r', encoding='utf-8') as f:
                equity_info = json.load(f)
            logger.debug(f"✅ 加载股本信息: {len(equity_info)} 只股票")
            return equity_info
        except Exception as e:
            logger.warning(f"⚠️ 加载股本信息失败: {e}，将使用QMT实时获取")
            return {}
    
    def estimate_flow_multi_dim(self, code: str) -> dict:
        """
        多维度资金流估算
        
        Args:
            code: 股票代码（如 '300997.SZ'）
        
        Returns:
            {
                'final_signal': 'STRONG_INFLOW' | 'WEAK_INFLOW' | 'NEUTRAL' | 'WEAK_OUTFLOW' | 'STRONG_OUTFLOW' | 'TRAP_WARNING',
                'confidence': 0.0-1.0,  # 置信度
                'dimensions': {
                    'quantity': {...},  # 成交量维度
                    'price': {...},     # 价格维度
                    'space': {...},     # 换手率维度
                    'time': {...}       # 时间维度
                },
                'trap_signals': [...],  # 诱多预警
                'reason': str,
                'timestamp': str
            }
        """
        # 初始化该股票的历史记录
        if code not in self.tick_history:
            self.tick_history[code] = deque(maxlen=self.tick_window)
        
        # 获取最新 Tick
        tick = xtdata.get_full_tick([code])
        if code not in tick:
            return self._empty_result('Tick数据缺失')
        
        current_tick = tick[code]
        
        # 记录历史
        tick_record = {
            'volume': current_tick.get('volume', 0),
            'price': current_tick.get('lastPrice', 0),
            'amount': current_tick.get('amount', 0),
            'time': time.time(),
            'bid': current_tick.get('bidPrice', []),  # 买盘
            'ask': current_tick.get('askPrice', []),  # 卖盘
            'bid_volume': current_tick.get('bidVol', []),  # 买盘量
            'ask_volume': current_tick.get('askVol', []),  # 卖盘量
        }
        
        self.tick_history[code].append(tick_record)
        
        # 持久化到SQLite
        if self.enable_persistence:
            self._save_tick_to_db(code, tick_record)
        
        # 需要足够数据点
        if len(self.tick_history[code]) < 10:
            return self._empty_result(f'数据积累中 ({len(self.tick_history[code])}/10)')
        
        # ===== 维度1：成交量分析 =====
        quantity_dim = self._analyze_quantity(code)
        
        # ===== 维度2：价格形态分析 =====
        price_dim = self._analyze_price(code)
        
        # ===== 维度3：换手率/流通性分析 =====
        space_dim = self._analyze_space(code)
        
        # ===== 维度4：时间持续性分析 =====
        time_dim = self._analyze_time(code)
        
        # ===== 反诱多检测 =====
        trap_signals = self._detect_traps(code, current_tick)
        
        # ===== 综合判断 =====
        final_signal, confidence, reason = self._synthesize_signal(
            quantity_dim, price_dim, space_dim, time_dim, trap_signals
        )
        
        return {
            'final_signal': final_signal,
            'confidence': confidence,
            'dimensions': {
                'quantity': quantity_dim,
                'price': price_dim,
                'space': space_dim,
                'time': time_dim
            },
            'trap_signals': trap_signals,
            'reason': reason,
            'timestamp': time.strftime('%H:%M:%S')
        }
    
    def _save_tick_to_db(self, code: str, tick_record: dict):
        """保存Tick到SQLite"""
        try:
            # 计算买卖盘总量
            bid_total = sum(tick_record.get('bid_volume', []))
            ask_total = sum(tick_record.get('ask_volume', []))
            
            self.db_conn.execute('''
                INSERT OR REPLACE INTO tick_history 
                (code, timestamp, volume, price, amount, bid_total, ask_total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                code,
                int(tick_record['time']),
                tick_record['volume'],
                tick_record['price'],
                tick_record['amount'],
                bid_total,
                ask_total
            ))
            self.db_conn.commit()
        except Exception as e:
            logger.debug(f"⚠️ 保存Tick到数据库失败: {e}")
    
    def _analyze_quantity(self, code: str) -> dict:
        """
        维度1：成交量分析
        
        检测：
        - 成交量脉冲（突然放量）
        - 成交量趋势（持续放量 vs 单次放量）
        - 量价背离（放量但价格不涨）
        """
        history = list(self.tick_history[code])
        volumes = [h['volume'] for h in history]
        
        # 当前成交量 vs 平均成交量
        current_vol = volumes[-1]
        avg_vol = statistics.mean(volumes[:-1]) if len(volumes) > 1 else 1
        volume_surge = current_vol / avg_vol if avg_vol > 0 else 1.0
        
        # 成交量趋势（最近5个 vs 之前的平均）
        if len(volumes) >= 10:
            recent_avg = statistics.mean(volumes[-5:])
            earlier_avg = statistics.mean(volumes[:-5])
            volume_trend = (recent_avg - earlier_avg) / earlier_avg if earlier_avg > 0 else 0
        else:
            volume_trend = 0
        
        # 成交量波动率（剔除单次异常）
        volume_std = statistics.stdev(volumes) if len(volumes) > 1 else 0
        volume_volatility = volume_std / avg_vol if avg_vol > 0 else 0
        
        return {
            'volume_surge': volume_surge,           # 当前量比
            'volume_trend': volume_trend,           # 量能趋势
            'volume_volatility': volume_volatility, # 量能波动率
            'signal': self._quantity_signal(volume_surge, volume_trend, volume_volatility)
        }
    
    def _quantity_signal(self, surge: float, trend: float, volatility: float) -> str:
        """成交量信号判断"""
        if surge > 2.5 and trend > 0.2 and volatility < 1.0:
            return 'STRONG_VOLUME'  # 持续放量，非单次异常
        elif surge > 2.0 and volatility > 2.0:
            return 'ABNORMAL_SPIKE'  # 单次异常放量（可能是对倒）
        elif surge > 1.5 and trend > 0.1:
            return 'MODERATE_VOLUME'  # 温和放量
        elif surge < 0.8:
            return 'SHRINKING_VOLUME'  # 缩量
        else:
            return 'NORMAL_VOLUME'
    
    def _analyze_price(self, code: str) -> dict:
        """
        维度2：价格形态分析
        
        检测：
        - 价格走势（上涨/下跌/横盘）
        - 价格波动率（急涨急跌 vs 稳步上涨）
        - 量价配合（放量上涨 vs 放量横盘）
        """
        history = list(self.tick_history[code])
        prices = [h['price'] for h in history if h['price'] > 0]
        
        if len(prices) < 2:
            return {'signal': 'INSUFFICIENT_DATA'}
        
        # 价格变化
        price_change = (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
        
        # 价格波动率
        price_std = statistics.stdev(prices)
        price_volatility = price_std / statistics.mean(prices)
        
        # 价格动量（最近5个 vs 之前）
        if len(prices) >= 10:
            recent_avg_price = statistics.mean(prices[-5:])
            earlier_avg_price = statistics.mean(prices[:-5])
            price_momentum = (recent_avg_price - earlier_avg_price) / earlier_avg_price if earlier_avg_price > 0 else 0
        else:
            price_momentum = 0
        
        return {
            'price_change': price_change,
            'price_volatility': price_volatility,
            'price_momentum': price_momentum,
            'signal': self._price_signal(price_change, price_volatility, price_momentum)
        }
    
    def _price_signal(self, change: float, volatility: float, momentum: float) -> str:
        """价格信号判断"""
        if change > 0.02 and volatility < 0.01 and momentum > 0.01:
            return 'STEADY_RISE'  # 稳步上涨（机构特征）
        elif change > 0.03 and volatility > 0.02:
            return 'VIOLENT_RISE'  # 暴力拉升（散户追涨）
        elif abs(change) < 0.005 and volatility < 0.005:
            return 'SIDEWAYS'  # 横盘整理
        elif change < -0.02:
            return 'DECLINE'  # 下跌
        else:
            return 'NORMAL_FLUCTUATION'
    
    def _analyze_space(self, code: str) -> dict:
        """
        维度3：换手率/流通性分析
        
        通过获取5日K线数据，计算：
        - 平均换手率
        - 换手率趋势
        - 与历史换手率对比
        """
        try:
            # 获取最近5日K线
            kline = xtdata.get_market_data_ex(
                field_list=['volume', 'amount'],
                stock_list=[code],
                period='1d',
                count=self.day_window,
                dividend_type='none'
            )
            
            if code not in kline or len(kline[code]) < 3:
                return {'signal': 'INSUFFICIENT_DATA'}
            
            df = kline[code]
            
            # 获取流通股本（从本地缓存）
            float_shares = self._get_float_shares(code)
            if float_shares == 0:
                return {'signal': 'NO_EQUITY_DATA'}
            
            # 计算换手率
            turnovers = []
            for idx, row in df.iterrows():
                volume = row.get('volume', 0)
                turnover = volume / float_shares
                turnovers.append(turnover)
            
            if not turnovers:
                return {'signal': 'NO_TURNOVER_DATA'}
            
            avg_turnover = statistics.mean(turnovers)
            turnover_trend = (turnovers[-1] - turnovers[0]) / turnovers[0] if turnovers[0] > 0 else 0
            
            return {
                'avg_turnover': avg_turnover,
                'turnover_trend': turnover_trend,
                'signal': self._space_signal(avg_turnover, turnover_trend)
            }
        
        except Exception as e:
            logger.debug(f"⚠️ 换手率分析失败 {code}: {e}")
            return {'signal': 'ERROR', 'error': str(e)}
    
    def _space_signal(self, avg_turnover: float, trend: float) -> str:
        """换手率信号判断"""
        if avg_turnover > 0.08 and trend > 0.2:
            return 'HIGH_TURNOVER_RISING'  # 高换手且上升（活跃）
        elif avg_turnover > 0.05 and abs(trend) < 0.1:
            return 'MODERATE_TURNOVER_STABLE'  # 中等换手且稳定（可能吸筹）
        elif avg_turnover < 0.02:
            return 'LOW_TURNOVER'  # 低换手（冷门）
        else:
            return 'NORMAL_TURNOVER'
    
    def _analyze_time(self, code: str) -> dict:
        """
        维度4：时间持续性分析
        
        检测：
        - 异动持续时间（3秒冲高 vs 持续10分钟）
        - 时段特征（早盘 vs 尾盘）
        """
        history = list(self.tick_history[code])
        
        # 计算异动持续时间
        volumes = [h['volume'] for h in history]
        avg_vol = statistics.mean(volumes) if volumes else 1
        
        surge_count = sum(1 for v in volumes[-10:] if v > avg_vol * 1.5)
        surge_duration = surge_count / 10 if len(volumes) >= 10 else 0  # 比例
        
        # 当前时段
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        if current_hour == 9 and current_minute < 45:
            time_period = 'MORNING_OPEN'  # 早盘开盘
        elif current_hour == 14 and current_minute >= 30:
            time_period = 'AFTERNOON_CLOSE'  # 尾盘
        else:
            time_period = 'NORMAL_TRADING'  # 正常交易时段
        
        return {
            'surge_duration': surge_duration,
            'time_period': time_period,
            'signal': self._time_signal(surge_duration, time_period)
        }
    
    def _time_signal(self, duration: float, period: str) -> str:
        """时间信号判断"""
        if duration > 0.7 and period == 'NORMAL_TRADING':
            return 'SUSTAINED_ACTIVITY'  # 持续异动（真实）
        elif duration < 0.3 and period == 'AFTERNOON_CLOSE':
            return 'TAIL_SURGE'  # 尾盘拉升（警惕诱多）
        elif duration > 0.5:
            return 'MODERATE_ACTIVITY'
        else:
            return 'SHORT_SPIKE'  # 短暂脉冲
    
    def _detect_traps(self, code: str, current_tick: dict) -> List[str]:
        """
        反诱多检测层
        
        检测：
        1. 对倒识别：成交量暴增但买卖盘挂单几乎不变
        2. 尾盘拉升：14:30后突然异动
        3. 涨停板打开：连续涨停后首次开板（可能出货）
        4. 单边成交：买盘或卖盘长时间为0（可能是对敲）
        """
        trap_signals = []
        history = list(self.tick_history[code])
        
        # 检测1：对倒识别
        if len(history) >= 5:
            # 成交量暴增
            current_vol = history[-1]['volume']
            avg_vol = statistics.mean([h['volume'] for h in history[:-1]]) if len(history) > 1 else 1
            
            if current_vol > avg_vol * 3 and avg_vol > 0:
                # 但买卖盘挂单变化不大
                bid_ask_change = self._calc_bid_ask_change(history)
                if bid_ask_change is not None and bid_ask_change < 0.1:  # 挂单变化 <10%
                    trap_signals.append('对倒嫌疑：成交量异常但买卖盘不变')
        
        # 检测2：尾盘拉升
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        if current_hour == 14 and current_minute >= 30:
            # 检查是否突然放量
            if len(history) >= 10:
                recent_vols = [h['volume'] for h in history[-5:]]
                earlier_vols = [h['volume'] for h in history[-10:-5]]
                
                recent_avg = statistics.mean(recent_vols) if recent_vols else 0
                earlier_avg = statistics.mean(earlier_vols) if earlier_vols else 1
                
                if recent_avg > earlier_avg * 2 and earlier_avg > 0:
                    trap_signals.append('尾盘拉升：警惕次日低开')
        
        # 检测3：涨停板打开（需要日线数据）
        try:
            kline = xtdata.get_market_data_ex(
                field_list=['close', 'high', 'low'],
                stock_list=[code],
                period='1d',
                count=3,
                dividend_type='none'
            )
            
            if code in kline and len(kline[code]) >= 3:
                df = kline[code]
                # 检查前2天是否连续涨停
                closes = df['close'].tolist()
                if len(closes) >= 3:
                    prev_day_change = (closes[-2] - closes[-3]) / closes[-3] if closes[-3] > 0 else 0
                    
                    if prev_day_change > 0.095:  # 前一天涨停
                        current_price = current_tick.get('lastPrice', 0)
                        yesterday_close = closes[-2]
                        today_change = (current_price - yesterday_close) / yesterday_close if yesterday_close > 0 else 0
                        
                        if 0.02 < today_change < 0.08:  # 今天开板了但没继续涨停
                            trap_signals.append('连板开板：可能是主力出货')
        
        except Exception as e:
            logger.debug(f"⚠️ 连板检测失败 {code}: {e}")
        
        # 检测4：单边挂单（买盘或卖盘长时间为0）
        if len(history) >= 5:
            bid_counts = [len(h.get('bid_volume', [])) for h in history[-5:]]
            ask_counts = [len(h.get('ask_volume', [])) for h in history[-5:]]
            
            if sum(bid_counts) == 0 or sum(ask_counts) == 0:
                trap_signals.append('单边挂单：可能是对敲')
        
        return trap_signals
    
    def _calc_bid_ask_change(self, history: List[dict]) -> Optional[float]:
        """计算买卖盘挂单变化率"""
        if len(history) < 2:
            return None
        
        try:
            # 计算最近的买卖盘总量变化
            prev_bid_total = sum(history[-2].get('bid_volume', []))
            curr_bid_total = sum(history[-1].get('bid_volume', []))
            
            prev_ask_total = sum(history[-2].get('ask_volume', []))
            curr_ask_total = sum(history[-1].get('ask_volume', []))
            
            if prev_bid_total == 0 or prev_ask_total == 0:
                return None
            
            bid_change = abs((curr_bid_total - prev_bid_total) / prev_bid_total)
            ask_change = abs((curr_ask_total - prev_ask_total) / prev_ask_total)
            
            return (bid_change + ask_change) / 2
        
        except Exception as e:
            logger.debug(f"⚠️ 计算买卖盘变化率失败: {e}")
            return None
    
    def _synthesize_signal(self, quantity_dim: dict, price_dim: dict, 
                          space_dim: dict, time_dim: dict, 
                          trap_signals: List[str]) -> tuple:
        """
        综合判断（多维度投票机制）
        
        规则：
        1. 如果有诱多信号 → 直接返回 TRAP_WARNING
        2. 四个维度同时符合 → STRONG_INFLOW（高置信度）
        3. 3个维度符合 → WEAK_INFLOW（中置信度）
        4. 2个及以下 → NEUTRAL（低置信度）
        """
        # 优先级1：诱多检测
        if trap_signals:
            return 'TRAP_WARNING', 0.9, f"诱多预警: {'; '.join(trap_signals)}"
        
        # 统计各维度的正面信号
        positive_signals = []
        
        # 成交量维度
        if quantity_dim['signal'] in ['STRONG_VOLUME', 'MODERATE_VOLUME']:
            positive_signals.append('量能')
        
        # 价格维度
        if price_dim['signal'] in ['STEADY_RISE', 'SIDEWAYS']:
            positive_signals.append('价格')
        
        # 换手率维度
        if space_dim['signal'] in ['MODERATE_TURNOVER_STABLE', 'HIGH_TURNOVER_RISING']:
            positive_signals.append('换手')
        
        # 时间维度
        if time_dim['signal'] in ['SUSTAINED_ACTIVITY', 'MODERATE_ACTIVITY']:
            positive_signals.append('持续性')
        
        # 投票机制
        vote_count = len(positive_signals)
        
        if vote_count >= 4:
            return 'STRONG_INFLOW', 0.85, f"机构吸筹特征明显（{'+'.join(positive_signals)}）"
        elif vote_count == 3:
            return 'WEAK_INFLOW', 0.65, f"温和流入（{'+'.join(positive_signals)}）"
        elif vote_count == 2:
            return 'NEUTRAL', 0.4, f"部分维度符合（{'+'.join(positive_signals)}）"
        else:
            # 检查是否是出货信号
            if quantity_dim['signal'] == 'SHRINKING_VOLUME' and price_dim['signal'] == 'DECLINE':
                return 'STRONG_OUTFLOW', 0.75, "缩量下跌，资金流出"
            else:
                return 'NEUTRAL', 0.3, "无明显特征"
    
    def _get_float_shares(self, code: str) -> float:
        """获取流通股本（从本地缓存或QMT）"""
        if code in self.equity_info:
            return self.equity_info[code].get('float_shares', 0)
        
        # 如果本地缓存没有，尝试从QMT获取
        try:
            # 这里可以扩展为从QMT获取实时股本信息
            pass
        except:
            pass
        
        return 0
    
    def _empty_result(self, reason: str) -> dict:
        """空结果"""
        return {
            'final_signal': 'NEUTRAL',
            'confidence': 0.0,
            'dimensions': {},
            'trap_signals': [],
            'reason': reason,
            'timestamp': time.strftime('%H:%M:%S')
        }
    
    def close(self):
        """关闭资源"""
        if self.enable_persistence and hasattr(self, 'db_conn'):
            self.db_conn.close()
            logger.info("✅ SmartFlowEstimator 资源已释放")
