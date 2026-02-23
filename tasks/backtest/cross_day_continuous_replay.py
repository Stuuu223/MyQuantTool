#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO Phase 6.3】跨日连贯回测引擎 (Cross-Day Continuous Replay Engine)

任务背景:
打通: 12.31选出73只 -> V18验出志特新材Top 3 -> 存入ShortTermMemory -> 
系统时间自动滚动到1月5日09:30 -> QMT获取1.05的Tick数据 -> 触发实盘开火信号

核心功能:
1. Day 1 (2025-12-31) 首扬日筛选 - 使用V18核心计算抽血占比得分
2. 跨日记忆存储 - 使用ShortTermMemory保存强势票
3. Day 2 (2026-01-05) 接力日检测 - 09:40前资金流入+横向排名
4. 开火信号生成 - [BUY]信号输出

Author: AI Backend Engineer
Date: 2026-02-23
Version: 1.0.0
"""

import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

import pandas as pd
import numpy as np

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# 导入V18核心组件
from logic.strategies.production.unified_warfare_core import (
    UnifiedWarfareCoreV18, ShortTermMemory
)
from logic.monitors.global_heat_state_machine import GlobalHeatStateMachine
from logic.utils.code_converter import CodeConverter

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False
    logging.warning("⚠️ xtquant未安装，将使用模拟数据模式")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BuySignal:
    """开火信号数据类"""
    stock_code: str
    signal_time: str
    confidence: float
    expected_return: float
    trigger_reason: str
    day1_memory: Dict[str, Any]
    day2_data: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RelayResult:
    """接力检测结果"""
    stock_code: str
    day1_date: str
    day2_date: str
    day1_rank: int
    day2_relay_triggered: bool
    day2_signal_time: Optional[str]
    capital_inflow_morning: float
    heat_rank: int
    buy_signal: Optional[BuySignal]
    
    def to_dict(self) -> Dict:
        return asdict(self)


class CrossDayContinuousReplay:
    """
    跨日连贯回测引擎
    
    实现CTO要求的完整跨日回演流程:
    Day 1筛选 -> 存储记忆 -> Day 2接力检测 -> 生成信号
    """
    
    # 默认日期配置
    DEFAULT_DAY1_DATE = '20251231'  # 首扬日
    DEFAULT_DAY2_DATE = '20260105'  # 接力日
    
    # 信号触发参数
    MORNING_CUTOFF_TIME = '09:40'  # 早盘截止时间
    MIN_CAPITAL_INFLOW = 5000000   # 最小资金流入500万
    TOP_N_SELECTION = 10           # 选出Top 10
    
    def __init__(
        self,
        stock_list: List[str],
        start_date: str = None,
        end_date: str = None,
        use_heat_state_machine: bool = True
    ):
        """
        初始化跨日回测引擎
        
        Args:
            stock_list: 股票代码列表 (如 ['300986.SZ', '300017.SZ'])
            start_date: Day 1日期 (YYYYMMDD)，默认20251231
            end_date: Day 2日期 (YYYYMMDD)，默认20260105
            use_heat_state_machine: 是否使用全局热力状态机
        """
        self.stock_list = self._normalize_stock_codes(stock_list)
        self.day1_date = start_date or self.DEFAULT_DAY1_DATE
        self.day2_date = end_date or self.DEFAULT_DAY2_DATE
        
        # 初始化V18核心
        self.v18_core = UnifiedWarfareCoreV18()
        
        # 初始化热力状态机
        self.heat_state_machine: Optional[GlobalHeatStateMachine] = None
        if use_heat_state_machine and QMT_AVAILABLE:
            try:
                # 提取6位代码用于热力状态机
                codes_6digit = [CodeConverter.to_6digit(c) for c in self.stock_list]
                self.heat_state_machine = GlobalHeatStateMachine(
                    watch_list=codes_6digit,
                    update_interval=3
                )
                logger.info(f"✅ 全局热力状态机初始化完成 | 关注数量: {len(codes_6digit)}")
            except Exception as e:
                logger.warning(f"⚠️ 热力状态机初始化失败: {e}")
        
        # 缓存数据
        self._day1_results: List[Dict] = []
        self._day2_results: List[Dict] = []
        self._buy_signals: List[BuySignal] = []
        
        # 流通股本缓存 (从文件或配置读取)
        self._float_volumes: Dict[str, float] = self._load_float_volumes()
        
        logger.info(f"✅ 跨日连贯回测引擎初始化完成")
        logger.info(f"   Day 1 (首扬日): {self.day1_date}")
        logger.info(f"   Day 2 (接力日): {self.day2_date}")
        logger.info(f"   股票数量: {len(self.stock_list)}")
    
    def _normalize_stock_codes(self, codes: List[str]) -> List[str]:
        """标准化股票代码为QMT格式"""
        normalized = []
        for code in codes:
            try:
                qmt_code = CodeConverter.to_qmt(code)
                normalized.append(qmt_code)
            except Exception as e:
                logger.warning(f"⚠️ 代码转换失败: {code}, 跳过. 错误: {e}")
                continue
        return normalized
    
    def _load_float_volumes(self) -> Dict[str, float]:
        """加载流通股本数据"""
        # 默认数据 (可以从CSV或配置文件加载)
        default_volumes = {
            '300986.SZ': 246000000,  # 志特新材
            '300017.SZ': 2306141629,  # 网宿科技
            '301005.SZ': 836269091,   # 超捷股份
        }
        
        # 尝试从CSV加载更多数据
        csv_path = PROJECT_ROOT / 'data' / 'cleaned_candidates_66.csv'
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                for _, row in df.iterrows():
                    ts_code = row.get('ts_code', '')
                    if ts_code:
                        # 根据平均成交额和换手率估算流通股本
                        avg_amount = row.get('avg_amount_5d', 0) * 10000  # 万元转元
                        turnover_rate = row.get('turnover_rate', 1) / 100  # 百分比转小数
                        if turnover_rate > 0:
                            estimated_float = avg_amount / turnover_rate
                            default_volumes[ts_code] = estimated_float
            except Exception as e:
                logger.warning(f"⚠️ 加载CSV流通股本失败: {e}")
        
        return default_volumes
    
    def _get_float_volume(self, stock_code: str) -> float:
        """获取流通股本"""
        return self._float_volumes.get(stock_code, 1e9)  # 默认10亿股
    
    def _get_tick_data(self, stock_code: str, date: str) -> pd.DataFrame:
        """
        从QMT获取Tick数据
        
        Args:
            stock_code: 股票代码 (QMT格式)
            date: 日期 (YYYYMMDD)
            
        Returns:
            DataFrame: Tick数据
        """
        if not QMT_AVAILABLE:
            logger.warning(f"⚠️ QMT不可用，返回空数据: {stock_code}")
            return pd.DataFrame()
        
        try:
            result = xtdata.get_local_data(
                field_list=['time', 'volume', 'lastPrice', 'amount'],
                stock_list=[stock_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if not result or stock_code not in result:
                logger.warning(f"⚠️ 无Tick数据: {stock_code} {date}")
                return pd.DataFrame()
            
            df = result[stock_code].copy()
            if df.empty:
                return pd.DataFrame()
            
            # UTC+8转换
            df['dt'] = pd.to_datetime(df['time'], unit='ms') + timedelta(hours=8)
            df = df[df['lastPrice'] > 0]
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 获取Tick数据失败 {stock_code} {date}: {e}")
            return pd.DataFrame()
    
    def _calculate_5min_windows(
        self,
        df: pd.DataFrame,
        float_volume: float
    ) -> List[Dict]:
        """
        计算5分钟窗口数据
        
        Args:
            df: Tick数据DataFrame
            float_volume: 流通股本
            
        Returns:
            List[Dict]: 5分钟窗口列表
        """
        if df.empty:
            return []
        
        df = df.sort_values('dt').copy()
        
        # 计算成交量增量 (手→股)
        df['vol_delta_shou'] = df['volume'].diff().fillna(df['volume'].iloc[0])
        df['vol_delta_shou'] = df['vol_delta_shou'].clip(lower=0)
        df['vol_delta'] = df['vol_delta_shou'] * 100  # 手→股
        
        # 5分钟聚合
        df = df.set_index('dt')
        resampled = df.resample('5min', label='left', closed='left').agg({
            'vol_delta': 'sum',
            'lastPrice': 'last',
            'amount': 'last'
        })
        resampled = resampled.dropna()
        
        if resampled.empty:
            return []
        
        windows = []
        prev_price = resampled['lastPrice'].iloc[0]
        
        for dt, row in resampled.iterrows():
            if row['vol_delta'] <= 0 or row['lastPrice'] <= 0:
                continue
            
            # 成交额计算
            amount = row['vol_delta'] * row['lastPrice']  # 股×元
            turnover = row['vol_delta'] / float_volume if float_volume > 0 else 0
            
            # 价格变化
            price_change = (row['lastPrice'] - prev_price) / prev_price * 100 if prev_price > 0 else 0
            
            # 强度得分
            intensity = amount / 10000 * abs(price_change)  # 万元×涨幅
            
            windows.append({
                'time': dt.strftime('%H:%M'),
                'datetime': dt,
                'hour': dt.hour,
                'minute': dt.minute,
                'price': float(row['lastPrice']),
                'volume': float(row['vol_delta']),  # 股
                'volume_shou': float(row['vol_delta'] / 100),  # 手
                'amount': float(amount),
                'amount_wan': float(amount / 10000),
                'turnover': float(turnover),
                'turnover_pct': float(turnover * 100),
                'change_pct': float(price_change),
                'intensity_score': float(intensity)
            })
            
            prev_price = row['lastPrice']
        
        return windows
    
    def run_day1_screening(self) -> List[Dict]:
        """
        Day 1筛选 - 首扬日筛选
        
        流程:
        1. 读取所有股票的12.31 Tick数据
        2. 计算5分钟窗口
        3. 使用V18核心calculate_blood_sucking_score计算得分
        4. 按final_score排序选出Top 10
        
        Returns:
            List[Dict]: Day 1 Top 10结果列表
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"【Day 1】{self.day1_date} 首扬日筛选")
        logger.info(f"{'='*70}")
        
        all_stocks_data: Dict[str, List[Dict]] = {}
        analysis_results: List[Dict] = []
        
        # 1. 获取所有股票的窗口数据
        logger.info(f"1. 获取 {len(self.stock_list)} 只票的Tick数据...")
        
        for stock_code in self.stock_list:
            df = self._get_tick_data(stock_code, self.day1_date)
            if df.empty:
                continue
            
            float_volume = self._get_float_volume(stock_code)
            windows = self._calculate_5min_windows(df, float_volume)
            
            if windows:
                all_stocks_data[stock_code] = windows
                logger.info(f"   ✅ {stock_code}: {len(windows)}个窗口")
        
        if not all_stocks_data:
            logger.error("❌ Day 1 无有效数据")
            return []
        
        logger.info(f"\n2. 使用V18核心计算抽血占比动态乘数得分...")
        
        # 2. 计算每只股票的基础得分和抽血占比
        for stock_code, windows in all_stocks_data.items():
            try:
                # 使用V18核心计算得分
                score_result = self.v18_core.calculate_blood_sucking_score(
                    stock_code=stock_code,
                    windows=windows,
                    all_stocks_data=all_stocks_data
                )
                
                # 执行全天分析 (标记STRONG_MOMENTUM)
                day_analysis = self.v18_core.analyze_day(stock_code, self.day1_date, windows)
                
                result = {
                    'stock_code': stock_code,
                    'date': self.day1_date,
                    'windows': windows,
                    'window_count': len(windows),
                    'base_score': score_result['base_score'],
                    'capital_share_pct': score_result['capital_share_pct'],
                    'multiplier': score_result['multiplier'],
                    'final_score': score_result['final_score'],
                    'is_strong_momentum': day_analysis.get('is_strong_momentum', False),
                    'turnover_rate': day_analysis.get('turnover_rate', 0),
                    'total_amount': day_analysis.get('total_amount', 0)
                }
                
                analysis_results.append(result)
                
            except Exception as e:
                logger.error(f"❌ 分析失败 {stock_code}: {e}")
                continue
        
        # 3. 按final_score排序并选出Top 10
        ranked_results = self.v18_core.rank_by_capital_share(analysis_results)
        top10 = ranked_results[:self.TOP_N_SELECTION] if len(ranked_results) >= self.TOP_N_SELECTION else ranked_results
        
        self._day1_results = top10
        
        logger.info(f"\n3. Day 1 筛选完成，选出Top {len(top10)}:")
        for i, r in enumerate(top10, 1):
            logger.info(
                f"   TOP{i}: {r['stock_code']} "
                f"得分={r['final_score']:.2f} "
                f"(基础{r['base_score']:.1f}×乘数{r['multiplier']:.2f}) "
                f"强势={'✅' if r['is_strong_momentum'] else '❌'}"
            )
        
        return top10
    
    def save_to_memory(self, day1_results: List[Dict]) -> None:
        """
        存储强势票到ShortTermMemory
        
        Args:
            day1_results: Day 1筛选结果列表
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"【存储记忆】保存强势票到ShortTermMemory")
        logger.info(f"{'='*70}")
        
        saved_count = 0
        
        for result in day1_results:
            stock_code = result['stock_code']
            is_strong = result.get('is_strong_momentum', False)
            
            if is_strong:
                # 找到最强窗口
                windows = result.get('windows', [])
                if windows:
                    max_window = max(windows, key=lambda x: x.get('amount', 0))
                    max_amount = max_window.get('amount', 0)
                    max_time = max_window.get('time', '')
                else:
                    max_amount = 0
                    max_time = ''
                
                # 存入V18接力引擎
                self.v18_core.relay_engine.analyze_day_end(
                    stock_code=stock_code,
                    date=self.day1_date,
                    close_price=windows[-1].get('price', 0) if windows else 0,
                    turnover_rate=result.get('turnover_rate', 0),
                    windows=windows
                )
                
                saved_count += 1
                logger.info(f"   ✅ {stock_code} 已标记为STRONG_MOMENTUM")
                logger.info(f"      收盘: {windows[-1].get('price', 0):.2f}, 换手: {result.get('turnover_rate', 0):.2f}%")
        
        logger.info(f"\n   共保存 {saved_count} 只强势票到记忆库")
    
    def run_day2_relay(self) -> List[Dict]:
        """
        Day 2接力检测
        
        流程:
        1. 检查ShortTermMemory中的强势票
        2. 读取1月5日Tick数据
        3. 计算早盘09:40前的资金流入
        4. 使用全局热力状态机获取实时排名
        
        Returns:
            List[Dict]: Day 2接力检测结果列表
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"【Day 2】{self.day2_date} 接力日检测")
        logger.info(f"{'='*70}")
        
        relay_results: List[Dict] = []
        
        # 1. 检查记忆库
        memory = self.v18_core.relay_engine.memory
        logger.info(f"1. 检查记忆库，共 {len(memory)} 只强势票")
        
        if not memory:
            logger.warning("⚠️ 记忆库为空，无法执行接力检测")
            return []
        
        # 启动热力状态机
        if self.heat_state_machine and not self.heat_state_machine.is_running():
            self.heat_state_machine.start()
            logger.info("✅ 全局热力状态机已启动")
        
        # 2. 对每只记忆票进行Day 2分析
        for stock_code in memory.keys():
            logger.info(f"\n2. 分析 {stock_code} Day 2数据...")
            
            # 获取Day 2数据
            df = self._get_tick_data(stock_code, self.day2_date)
            if df.empty:
                logger.warning(f"   ⚠️ {stock_code} 无Day 2数据")
                continue
            
            float_volume = self._get_float_volume(stock_code)
            windows = self._calculate_5min_windows(df, float_volume)
            
            if not windows:
                logger.warning(f"   ⚠️ {stock_code} 无有效窗口")
                continue
            
            # 3. 计算早盘资金流入 (09:40前)
            cutoff_hour, cutoff_minute = map(int, self.MORNING_CUTOFF_TIME.split(':'))
            morning_windows = [
                w for w in windows
                if w['hour'] < cutoff_hour or (w['hour'] == cutoff_hour and w['minute'] <= cutoff_minute)
            ]
            
            capital_inflow = sum(w.get('amount', 0) for w in morning_windows)
            
            logger.info(f"   早盘窗口数: {len(morning_windows)}")
            logger.info(f"   资金流入: {capital_inflow/10000:.1f}万元")
            
            # 4. 获取热力排名
            heat_rank = -1
            if self.heat_state_machine:
                heat_data = self.heat_state_machine.get_heat_rank(stock_code)
                heat_rank = heat_data.get('rank', -1)
                logger.info(f"   热力排名: {heat_rank}")
            
            # 5. 判断是否触发接力
            relay_triggered = (
                capital_inflow >= self.MIN_CAPITAL_INFLOW and
                heat_rank > 0 and heat_rank <= 20  # 排名前20
            )
            
            signal_time = None
            if relay_triggered and morning_windows:
                # 找到触发信号的窗口时间
                max_window = max(morning_windows, key=lambda x: x.get('amount', 0))
                signal_time = max_window.get('time', self.MORNING_CUTOFF_TIME)
            
            result = {
                'stock_code': stock_code,
                'day1_date': self.day1_date,
                'day2_date': self.day2_date,
                'day1_rank': self._get_day1_rank(stock_code),
                'day2_relay_triggered': relay_triggered,
                'day2_signal_time': signal_time,
                'capital_inflow_morning': capital_inflow,
                'heat_rank': heat_rank,
                'morning_windows': len(morning_windows),
                'windows': windows
            }
            
            relay_results.append(result)
            
            if relay_triggered:
                logger.info(f"   🚀 【接力信号触发】时间: {signal_time}, 资金: {capital_inflow/10000:.1f}万")
            else:
                logger.info(f"   ⚠️ 接力信号未触发")
        
        self._day2_results = relay_results
        return relay_results
    
    def _get_day1_rank(self, stock_code: str) -> int:
        """获取Day 1排名"""
        for i, result in enumerate(self._day1_results, 1):
            if result.get('stock_code') == stock_code:
                return i
        return -1
    
    def generate_signals(self) -> List[BuySignal]:
        """
        生成开火信号
        
        Returns:
            List[BuySignal]: [BUY]信号列表
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"【信号生成】生成[BUY]开火信号")
        logger.info(f"{'='*70}")
        
        signals: List[BuySignal] = []
        
        for result in self._day2_results:
            if not result.get('day2_relay_triggered', False):
                continue
            
            stock_code = result['stock_code']
            
            # 获取Day 1记忆
            memory = self.v18_core.relay_engine.memory.get(stock_code)
            day1_memory = memory.to_dict() if memory else {}
            
            # 计算置信度
            confidence = self._calculate_confidence(result, day1_memory)
            
            # 计算预期收益 (简化模型)
            expected_return = confidence * 0.1  # 假设10%最大收益
            
            # 构建触发原因
            trigger_reason = (
                f"Day1 STRONG_MOMENTUM + Day2早盘资金流入"
                f"({result.get('capital_inflow_morning', 0)/10000:.1f}万) + 热力排名{result.get('heat_rank', -1)}"
            )
            
            signal = BuySignal(
                stock_code=stock_code,
                signal_time=result.get('day2_signal_time', self.MORNING_CUTOFF_TIME),
                confidence=confidence,
                expected_return=expected_return,
                trigger_reason=trigger_reason,
                day1_memory=day1_memory,
                day2_data={
                    'capital_inflow': result.get('capital_inflow_morning', 0),
                    'heat_rank': result.get('heat_rank', -1),
                    'morning_windows': result.get('morning_windows', 0)
                }
            )
            
            signals.append(signal)
            
            logger.info(f"\n🚀 [BUY] 信号生成: {stock_code}")
            logger.info(f"   时间: {signal.signal_time}")
            logger.info(f"   置信度: {confidence:.2%}")
            logger.info(f"   预期收益: {expected_return:.2%}")
            logger.info(f"   原因: {trigger_reason}")
        
        self._buy_signals = signals
        return signals
    
    def _calculate_confidence(
        self,
        day2_result: Dict,
        day1_memory: Dict
    ) -> float:
        """
        计算信号置信度
        
        基于:
        - Day 1评分 (40%)
        - Day 2早盘资金流入 (30%)
        - 热力排名 (30%)
        """
        confidence = 0.0
        
        # 1. Day 1评分权重 (40%)
        day1_score = day1_memory.get('score', 0)
        confidence += min(day1_score / 100, 1.0) * 0.4
        
        # 2. Day 2资金流入权重 (30%)
        capital_inflow = day2_result.get('capital_inflow_morning', 0)
        confidence += min(capital_inflow / 10000000, 1.0) * 0.3  # 1000万封顶
        
        # 3. 热力排名权重 (30%)
        heat_rank = day2_result.get('heat_rank', -1)
        if heat_rank > 0:
            confidence += max(0, (21 - heat_rank) / 20) * 0.3  # 前20名有分
        
        return min(confidence, 1.0)
    
    def run_full_replay(self) -> Dict:
        """
        执行完整回演
        
        完整流程:
        1. Day 1筛选 -> 选出Top 10
        2. 存储强势票到ShortTermMemory
        3. Day 2接力检测
        4. 生成开火信号
        
        Returns:
            Dict: 完整回演报告
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"【完整回演启动】Cross-Day Continuous Replay")
        logger.info(f"{'='*70}")
        logger.info(f"时间跨度: {self.day1_date} -> {self.day2_date}")
        logger.info(f"股票池: {len(self.stock_list)} 只")
        
        start_time = datetime.now()
        
        # 1. Day 1筛选
        day1_top10 = self.run_day1_screening()
        
        if not day1_top10:
            return {
                'success': False,
                'error': 'Day 1筛选无结果',
                'day1_date': self.day1_date,
                'day2_date': self.day2_date
            }
        
        # 2. 存储到记忆
        self.save_to_memory(day1_top10)
        
        # 3. Day 2接力检测
        day2_results = self.run_day2_relay()
        
        # 4. 生成信号
        signals = self.generate_signals()
        
        # 5. 查找志特新材状态
        zhitexincai_status = self._get_zhitexincai_status(day1_top10, day2_results, signals)
        
        # 计算耗时
        duration = (datetime.now() - start_time).total_seconds()
        
        # 构建完整报告
        report = {
            'success': True,
            'day1_date': self.day1_date,
            'day2_date': self.day2_date,
            'duration_seconds': duration,
            'day1_top10': [
                {
                    'rank': i + 1,
                    'stock_code': r['stock_code'],
                    'final_score': r['final_score'],
                    'base_score': r['base_score'],
                    'multiplier': r['multiplier'],
                    'capital_share_pct': r['capital_share_pct'],
                    'is_strong_momentum': r['is_strong_momentum'],
                    'turnover_rate': r['turnover_rate']
                }
                for i, r in enumerate(day1_top10)
            ],
            'day2_signals': [s.to_dict() for s in signals],
            'zhitexincai_status': zhitexincai_status,
            'summary': {
                'total_stocks': len(self.stock_list),
                'day1_selected': len(day1_top10),
                'day1_strong_momentum': len([r for r in day1_top10 if r.get('is_strong_momentum')]),
                'day2_relay_candidates': len(day2_results),
                'day2_signals_generated': len(signals),
                'relay_success_rate': len(signals) / len(day2_results) * 100 if day2_results else 0
            }
        }
        
        # 打印总结
        self._print_final_report(report)
        
        return report
    
    def _get_zhitexincai_status(
        self,
        day1_top10: List[Dict],
        day2_results: List[Dict],
        signals: List[BuySignal]
    ) -> Dict:
        """获取志特新材状态 (特别关注)"""
        target_code = '300986.SZ'
        
        # Day 1排名
        day1_rank = -1
        for i, r in enumerate(day1_top10, 1):
            if r['stock_code'] == target_code:
                day1_rank = i
                break
        
        # Day 2状态
        day2_relay_triggered = False
        day2_signal_time = None
        
        for r in day2_results:
            if r['stock_code'] == target_code:
                day2_relay_triggered = r.get('day2_relay_triggered', False)
                day2_signal_time = r.get('day2_signal_time')
                break
        
        # 信号状态
        has_signal = any(s.stock_code == target_code for s in signals)
        
        return {
            'stock_code': target_code,
            'name': '志特新材',
            'day1_rank': day1_rank,
            'day1_in_top10': day1_rank > 0 and day1_rank <= 10,
            'day2_relay_triggered': day2_relay_triggered,
            'day2_signal_time': day2_signal_time,
            'buy_signal_generated': has_signal
        }
    
    def _print_final_report(self, report: Dict):
        """打印最终报告"""
        logger.info(f"\n{'='*70}")
        logger.info(f"【完整回演报告】")
        logger.info(f"{'='*70}")
        
        logger.info(f"\n📅 时间跨度: {report['day1_date']} -> {report['day2_date']}")
        logger.info(f"⏱️  总耗时: {report['duration_seconds']:.2f}秒")
        
        summary = report['summary']
        logger.info(f"\n📊 Day 1筛选:")
        logger.info(f"   入选: {summary['day1_selected']} 只")
        logger.info(f"   强势动能: {summary['day1_strong_momentum']} 只")
        
        logger.info(f"\n📊 Day 2接力:")
        logger.info(f"   候选: {summary['day2_relay_candidates']} 只")
        logger.info(f"   信号: {summary['day2_signals_generated']} 个")
        logger.info(f"   成功率: {summary['relay_success_rate']:.1f}%")
        
        # 志特新材特别关注
        ztxc = report['zhitexincai_status']
        logger.info(f"\n🎯 志特新材(300986)特别关注:")
        logger.info(f"   Day 1排名: {ztxc['day1_rank']}")
        logger.info(f"   进入Top 10: {'✅' if ztxc['day1_in_top10'] else '❌'}")
        logger.info(f"   Day 2接力: {'✅' if ztxc['day2_relay_triggered'] else '❌'}")
        logger.info(f"   信号时间: {ztxc['day2_signal_time'] or 'N/A'}")
        logger.info(f"   BUY信号: {'✅' if ztxc['buy_signal_generated'] else '❌'}")
        
        logger.info(f"\n{'='*70}")
        
        # 验收检查
        checks = [
            ("Day 1选出Top 10", len(report['day1_top10']) > 0),
            ("志特新材在Top 10", ztxc['day1_in_top10']),
            ("Day 2接力触发", ztxc['day2_relay_triggered']),
            ("生成BUY信号", ztxc['buy_signal_generated'])
        ]
        
        logger.info("【验收检查】")
        all_passed = True
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            logger.info(f"   {status} {check_name}")
            if not passed:
                all_passed = False
        
        if all_passed:
            logger.info("\n🎉 所有验收项目通过!")
        else:
            logger.info("\n⚠️ 部分验收项目未通过")
        
        logger.info(f"{'='*70}")
    
    def save_report(self, report: Dict, output_dir: Path = None) -> Tuple[Path, Path]:
        """
        保存报告到文件
        
        Args:
            report: 回演报告
            output_dir: 输出目录
            
        Returns:
            Tuple[Path, Path]: JSON文件路径和文本报告路径
        """
        if output_dir is None:
            output_dir = PROJECT_ROOT / 'data' / 'backtest_results'
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = output_dir / f"cross_day_replay_{self.day1_date}_{self.day2_date}_{timestamp}.json"
        txt_file = output_dir / f"cross_day_replay_{self.day1_date}_{self.day2_date}_{timestamp}.txt"
        
        # 保存JSON
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        # 保存文本报告
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("跨日连贯回测报告\n")
            f.write("="*80 + "\n\n")
            f.write(f"回演日期: {report['day1_date']} -> {report['day2_date']}\n")
            f.write(f"执行时间: {timestamp}\n")
            f.write(f"总耗时: {report['duration_seconds']:.2f}秒\n\n")
            
            f.write("Day 1 Top 10:\n")
            for item in report['day1_top10']:
                f.write(f"  {item['rank']}. {item['stock_code']} "
                       f"得分={item['final_score']:.2f} "
                       f"强势={'✅' if item['is_strong_momentum'] else '❌'}\n")
            
            f.write(f"\nDay 2 BUY信号 ({len(report['day2_signals'])}个):\n")
            for sig in report['day2_signals']:
                f.write(f"  [BUY] {sig['stock_code']} @ {sig['signal_time']} "
                       f"置信度={sig['confidence']:.2%}\n")
            
            f.write(f"\n志特新材状态:\n")
            ztxc = report['zhitexincai_status']
            f.write(f"  Day 1排名: {ztxc['day1_rank']}\n")
            f.write(f"  进入Top 10: {'是' if ztxc['day1_in_top10'] else '否'}\n")
            f.write(f"  Day 2接力: {'是' if ztxc['day2_relay_triggered'] else '否'}\n")
            f.write(f"  信号时间: {ztxc['day2_signal_time'] or 'N/A'}\n")
        
        logger.info(f"\n💾 报告已保存:")
        logger.info(f"   JSON: {json_file}")
        logger.info(f"   TXT:  {txt_file}")
        
        return json_file, txt_file


def load_stock_list_from_csv(csv_path: Path = None) -> List[str]:
    """从CSV加载股票列表"""
    if csv_path is None:
        csv_path = PROJECT_ROOT / 'data' / 'cleaned_candidates_66.csv'
    
    if not csv_path.exists():
        logger.warning(f"⚠️ CSV文件不存在: {csv_path}")
        return []
    
    try:
        df = pd.read_csv(csv_path)
        stock_list = df['ts_code'].tolist()
        logger.info(f"✅ 从CSV加载 {len(stock_list)} 只股票")
        return stock_list
    except Exception as e:
        logger.error(f"❌ 加载CSV失败: {e}")
        return []


def main():
    """主函数 - 执行跨日连贯回测"""
    print("="*80)
    print("【CTO Phase 6.3】跨日连贯回测引擎")
    print("="*80)
    
    # 加载股票列表 (66只)
    stock_list = load_stock_list_from_csv()
    
    if not stock_list:
        # 使用默认列表
        stock_list = [
            '300986.SZ',  # 志特新材 (主角)
            '300017.SZ',  # 网宿科技
            '301005.SZ',  # 超捷股份
            '000001.SZ',  # 平安银行
            '600519.SH',  # 贵州茅台
        ]
        print(f"使用默认股票列表: {len(stock_list)} 只")
    
    # 创建回测引擎
    engine = CrossDayContinuousReplay(
        stock_list=stock_list,
        start_date='20251231',
        end_date='20260105',
        use_heat_state_machine=True
    )
    
    # 执行完整回演
    report = engine.run_full_replay()
    
    # 保存报告
    if report.get('success'):
        engine.save_report(report)
    
    print("\n" + "="*80)
    print("跨日连贯回测完成!")
    print("="*80)


if __name__ == '__main__':
    main()
