#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行为回放引擎 (BehaviorReplayEngine)
CTO指令：回测系统MVP - 验证"维持能力"等特征的历史表现

核心功能：
1. Tick数据回放：复用DownloadManager历史数据
2. 事件检测：复用StrategyService（HALFWAY/TRUE_ATTACK/LEADER/TRAP）
3. 仓位模拟：复用Portfolio层逻辑（小资金1-3只）
4. 特征提取：维持能力、可交易窗口、环境权重
5. 统计输出：胜率、盈亏比、最大回撤
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.services.data_service import data_service
from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.rolling_metrics import RollingFlowCalculator
from logic.event_lifecycle_analyzer import EventLifecycleAnalyzer
from logic.services.event_lifecycle_service import EventLifecycleService


@dataclass
class ReplayTrade:
    """回测交易记录"""
    stock_code: str
    stock_name: str
    date: str
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    position_pct: float  # 仓位比例
    
    # 事件特征
    event_type: str  # TrueBreakout / Trap / Other
    t_warmup: Optional[float] = None  # 推升时长（分钟）
    warmup_change_pct: Optional[float] = None  # 推升段涨幅
    sustain_ability: Optional[float] = None  # 维持能力（高位维持时长）
    
    # 收益统计
    pnl_pct: float = 0.0  # 盈亏百分比
    max_drawdown_pct: float = 0.0  # 最大回撤
    holding_minutes: float = 0.0  # 持仓时长


@dataclass
class ReplayResult:
    """单日回放结果"""
    stock_code: str
    date: str
    trades: List[ReplayTrade] = field(default_factory=list)
    events_detected: int = 0
    trades_executed: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'stock_code': self.stock_code,
            'date': self.date,
            'events_detected': self.events_detected,
            'trades_executed': self.trades_executed,
            'trades': [self._trade_to_dict(t) for t in self.trades]
        }
    
    @staticmethod
    def _trade_to_dict(trade: ReplayTrade) -> Dict:
        return {
            'stock_code': trade.stock_code,
            'stock_name': trade.stock_name,
            'date': trade.date,
            'entry_time': trade.entry_time,
            'entry_price': trade.entry_price,
            'exit_time': trade.exit_time,
            'exit_price': trade.exit_price,
            'pnl_pct': trade.pnl_pct,
            'max_drawdown_pct': trade.max_drawdown_pct,
            'event_type': trade.event_type,
            't_warmup': trade.t_warmup,
            'sustain_ability': trade.sustain_ability,
            'holding_minutes': trade.holding_minutes
        }


@dataclass
class FeatureStats:
    """特征表现统计"""
    feature_name: str
    feature_threshold: float
    total_samples: int = 0
    win_count: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    
    @property
    def win_rate(self) -> float:
        return self.win_count / self.total_samples if self.total_samples > 0 else 0.0
    
    @property
    def avg_pnl(self) -> float:
        return self.total_pnl / self.total_samples if self.total_samples > 0 else 0.0
    
    def to_dict(self) -> Dict:
        return {
            'feature': f"{self.feature_name}>{self.feature_threshold}",
            'samples': self.total_samples,
            'win_rate': f"{self.win_rate:.1%}",
            'avg_pnl': f"{self.avg_pnl:+.2f}%",
            'max_dd': f"{self.max_drawdown:.2f}%"
        }


class BehaviorReplayEngine:
    """
    行为回放引擎
    
    设计原则：
    1. 复用生产系统同一套检测规则（StrategyService）
    2. 复用生产系统数据层（DownloadManager / DataService）
    3. 模拟小资金Portfolio逻辑（1-3只持仓）
    4. 提取关键特征用于统计验证
    """
    
    def __init__(self, 
                 initial_capital: float = 1000000.0,  # 初始资金100万
                 max_positions: int = 3,  # 小资金最多3只
                 position_pct_per_trade: float = 0.3,  # 单票30%仓位
                 sustain_threshold: float = 2.0,  # 维持能力阈值（%）
                 use_sustain_filter: bool = True):  # 新增：是否使用维持能力过滤器
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.position_pct_per_trade = position_pct_per_trade
        self.sustain_threshold = sustain_threshold
        
        # 事件分析器
        self.lifecycle_analyzer = EventLifecycleAnalyzer(
            breakout_threshold=5.0,
            trap_reversal_threshold=3.0,
            max_drawdown_threshold=5.0
        )
        
        # 新增：维持能力服务
        self.use_sustain_filter = use_sustain_filter
        if use_sustain_filter:
            self.lifecycle_service = EventLifecycleService()
            print("✅ 维持能力过滤器已启用")
        else:
            self.lifecycle_service = None
            print("⚠️ 维持能力过滤器已禁用（回退到原始逻辑）")
        
        # 统计结果
        self.all_trades: List[ReplayTrade] = []
        self.daily_results: List[ReplayResult] = []
        
    def replay_single_day(self, stock_code: str, stock_name: str, date: str) -> ReplayResult:
        """
        回放单日数据
        
        流程：
        1. 加载Tick数据
        2. 计算资金流
        3. 事件检测（HALFWAY/TRUE_ATTACK/LEADER/TRAP）
        4. 模拟交易（Portfolio逻辑）
        5. 提取特征
        """
        result = ReplayResult(stock_code=stock_code, date=date)
        
        try:
            # 1. 加载数据
            formatted_code = data_service._format_code(stock_code)
            pre_close = data_service.get_pre_close(stock_code, date)
            
            if pre_close <= 0:
                return result
            
            start_time = date.replace('-', '') + '093000'
            end_time = date.replace('-', '') + '150000'
            
            provider = QMTHistoricalProvider(
                stock_code=formatted_code,
                start_time=start_time,
                end_time=end_time,
                period='tick'
            )
            
            if provider.get_tick_count() == 0:
                return result
            
            # 2. 计算资金流
            calc = RollingFlowCalculator(windows=[1, 5, 15])
            tick_data = []
            last_tick = None
            
            for tick in provider.iter_ticks():
                metrics = calc.add_tick(tick, last_tick)
                true_change = (tick['lastPrice'] - pre_close) / pre_close * 100
                
                tick_data.append({
                    'time': datetime.fromtimestamp(int(tick['time']) / 1000),
                    'price': tick['lastPrice'],
                    'true_change_pct': true_change,
                    'flow_5min': metrics.flow_5min.total_flow,
                    'flow_15min': metrics.flow_15min.total_flow,
                })
                last_tick = tick
            
            df = pd.DataFrame(tick_data)
            
            # 3. 事件检测
            events = self.lifecycle_analyzer.analyze_day(df, pre_close)
            result.events_detected = len(events['breakouts']) + len(events['traps'])
            
            # 4. 处理真起爆事件
            for breakout in events['breakouts']:
                trade = self._simulate_breakout_trade(
                    stock_code, stock_name, date, df, breakout, pre_close
                )
                if trade:
                    result.trades.append(trade)
                    self.all_trades.append(trade)
            
            # 5. 处理骗炮事件
            for trap in events['traps']:
                trade = self._simulate_trap_trade(
                    stock_code, stock_name, date, df, trap, pre_close
                )
                if trade:
                    result.trades.append(trade)
                    self.all_trades.append(trade)
            
            result.trades_executed = len(result.trades)
            
        except Exception as e:
            print(f"回测失败 {stock_code} {date}: {e}")
        
        return result
    
    def _simulate_breakout_trade(self, stock_code: str, stock_name: str, 
                                 date: str, df: pd.DataFrame, 
                                 breakout_event, pre_close: float) -> Optional[ReplayTrade]:
        """模拟真起爆交易 - 集成维持能力过滤器"""
        
        if not breakout_event.push_phase:
            return None
        
        # 新增：维持能力过滤器
        if self.use_sustain_filter and self.lifecycle_service:
            try:
                lifecycle_result = self.lifecycle_service.analyze(stock_code, date)
                
                # 过滤器规则：
                # 1. sustain_score < 0.5 → 跳过（维持能力不足）
                # 2. env_score < 0.4 → 跳过（环境太差）
                # 3. is_true_breakout is False → 跳过（预测为骗炮）
                
                sustain_score = lifecycle_result.get('sustain_score', 0)
                env_score = lifecycle_result.get('env_score', 0)
                is_true_breakout = lifecycle_result.get('is_true_breakout')
                
                if sustain_score < 0.5:
                    print(f"   ⚠️ 过滤器：{stock_code} {date} sustain_score={sustain_score:.2f} < 0.5，跳过")
                    return None
                    
                if env_score < 0.4:
                    print(f"   ⚠️ 过滤器：{stock_code} {date} env_score={env_score:.2f} < 0.4，跳过")
                    return None
                    
                if is_true_breakout is False:
                    print(f"   ⚠️ 过滤器：{stock_code} {date} 预测为骗炮，跳过")
                    return None
                
                print(f"   ✅ 过滤器通过：{stock_code} {date} sustain={sustain_score:.2f}, env={env_score:.2f}")
                
                # 将维持能力信息存入trade对象
                sustain_ability = lifecycle_result.get('sustain_duration_min', 0)
                
            except Exception as e:
                print(f"   ⚠️ 维持能力分析失败：{e}，使用原始逻辑")
                sustain_ability = 0
        else:
            sustain_ability = 0
        
        push = breakout_event.push_phase
        
        # 入场时机：推升结束后+1分钟
        entry_idx = push.t_end_idx + 20  # 约1分钟后
        if entry_idx >= len(df):
            return None
        
        entry_price = df.loc[entry_idx, 'price']
        entry_time = df.loc[entry_idx, 'time'].strftime('%H:%M:%S')
        
        # 出场时机：收盘
        exit_price = df['price'].iloc[-1]
        exit_time = df['time'].iloc[-1].strftime('%H:%M:%S')
        
        # 计算收益和回撤
        pnl_pct = (exit_price - entry_price) / entry_price * 100
        hold_df = df.iloc[entry_idx:]
        cummax = hold_df['price'].cummax()
        max_dd = ((cummax - hold_df['price']) / cummax * 100).max()
        
        # 计算维持能力：推升结束后，价格保持在(entry_price * 0.98)以上的时长
        sustain_price = entry_price * (1 - self.sustain_threshold / 100)
        sustain_df = hold_df[hold_df['price'] >= sustain_price]
        sustain_ability_calc = len(sustain_df) * 3 / 60 if len(sustain_df) > 0 else 0  # 转换为分钟
        
        # 优先使用service返回的维持能力，如果没有则使用计算的
        if sustain_ability == 0:
            sustain_ability = sustain_ability_calc
        
        holding_minutes = (len(df) - entry_idx) * 3 / 60  # 约3秒一个tick
        
        return ReplayTrade(
            stock_code=stock_code,
            stock_name=stock_name,
            date=date,
            entry_time=entry_time,
            entry_price=entry_price,
            exit_time=exit_time,
            exit_price=exit_price,
            position_pct=self.position_pct_per_trade,
            event_type='TrueBreakout',
            t_warmup=push.duration_minutes,
            warmup_change_pct=push.change_end_pct - push.change_start_pct,
            sustain_ability=sustain_ability,
            pnl_pct=pnl_pct,
            max_drawdown_pct=max_dd,
            holding_minutes=holding_minutes
        )
    
    def _simulate_trap_trade(self, stock_code: str, stock_name: str,
                            date: str, df: pd.DataFrame,
                            trap_event, pre_close: float) -> Optional[ReplayTrade]:
        """模拟骗炮交易（用于对比分析，实际策略应过滤）"""
        if not trap_event.fake_phase:
            return None
        
        fake = trap_event.fake_phase
        
        # 入场时机：欺骗阶段高点后（模拟追高被套）
        # 找到fake_phase结束的位置
        peak_idx = df[df['true_change_pct'] == df['true_change_pct'].max()].index[0]
        entry_idx = peak_idx + 10  # 高点后稍晚入场
        
        if entry_idx >= len(df):
            return None
        
        entry_price = df.loc[entry_idx, 'price']
        entry_time = df.loc[entry_idx, 'time'].strftime('%H:%M:%S')
        
        # 出场时机：收盘（或止损）
        exit_price = df['price'].iloc[-1]
        exit_time = df['time'].iloc[-1].strftime('%H:%M:%S')
        
        # 计算收益和回撤
        pnl_pct = (exit_price - entry_price) / entry_price * 100
        hold_df = df.iloc[entry_idx:]
        cummax = hold_df['price'].cummax()
        max_dd = ((cummax - hold_df['price']) / cummax * 100).max()
        
        # 计算维持能力（对骗炮是负向指标）
        sustain_price = entry_price * (1 - self.sustain_threshold / 100)
        sustain_df = hold_df[hold_df['price'] >= sustain_price]
        sustain_ability = len(sustain_df) * 3 / 60 if len(sustain_df) > 0 else 0
        
        holding_minutes = (len(df) - entry_idx) * 3 / 60
        
        return ReplayTrade(
            stock_code=stock_code,
            stock_name=stock_name,
            date=date,
            entry_time=entry_time,
            entry_price=entry_price,
            exit_time=exit_time,
            exit_price=exit_price,
            position_pct=self.position_pct_per_trade,
            event_type='Trap',
            t_warmup=None,
            warmup_change_pct=None,
            sustain_ability=sustain_ability,
            pnl_pct=pnl_pct,
            max_drawdown_pct=max_dd,
            holding_minutes=holding_minutes
        )
    
    def replay_universe(self, stock_list: List[Tuple[str, str]], 
                       start_date: str, end_date: str) -> List[ReplayResult]:
        """
        回放整个股票池
        
        Args:
            stock_list: [(code, name), ...]
            start_date: '2026-01-01'
            end_date: '2026-01-31'
        """
        print(f"\n{'='*80}")
        print(f"行为回放引擎启动")
        print(f"股票池: {len(stock_list)}只")
        print(f"时间范围: {start_date} 至 {end_date}")
        print(f"{'='*80}\n")
        
        # 生成交易日列表
        dates = self._get_trading_days(start_date, end_date)
        
        total_days = len(stock_list) * len(dates)
        completed = 0
        
        for code, name in stock_list:
            for date in dates:
                result = self.replay_single_day(code, name, date)
                self.daily_results.append(result)
                
                completed += 1
                if completed % 10 == 0:
                    print(f"进度: {completed}/{total_days} ({completed/total_days*100:.1f}%)")
        
        print(f"\n{'='*80}")
        print(f"回放完成")
        print(f"总交易次数: {len(self.all_trades)}")
        print(f"{'='*80}\n")
        
        return self.daily_results
    
    def _get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """获取交易日列表（简化版，实际应接入Tushare trade_cal）"""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        days = []
        current = start
        while current <= end:
            # 跳过周末
            if current.weekday() < 5:
                days.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        return days
    
    def analyze_features(self) -> pd.DataFrame:
        """
        特征表现分析
        
        统计不同特征组合的：
        - 胜率
        - 平均盈亏
        - 最大回撤
        """
        if not self.all_trades:
            return pd.DataFrame()
        
        # 转换为DataFrame便于分析
        trades_df = pd.DataFrame([{
            'event_type': t.event_type,
            't_warmup': t.t_warmup or 0,
            'sustain_ability': t.sustain_ability or 0,
            'pnl_pct': t.pnl_pct,
            'max_drawdown_pct': t.max_drawdown_pct,
            'win': 1 if t.pnl_pct > 0 else 0
        } for t in self.all_trades])
        
        # 特征阈值列表
        sustain_thresholds = [10, 20, 30, 40]  # 维持能力分钟数
        
        stats = []
        
        # 真起爆：维持能力分析
        for threshold in sustain_thresholds:
            subset = trades_df[
                (trades_df['event_type'] == 'TrueBreakout') &
                (trades_df['sustain_ability'] >= threshold)
            ]
            
            if len(subset) > 0:
                stat = FeatureStats(
                    feature_name='sustain_ability',
                    feature_threshold=threshold,
                    total_samples=len(subset),
                    win_count=subset['win'].sum(),
                    total_pnl=subset['pnl_pct'].sum(),
                    max_drawdown=subset['max_drawdown_pct'].max()
                )
                stats.append(stat)
        
        # 骗炮：对比组
        trap_subset = trades_df[trades_df['event_type'] == 'Trap']
        if len(trap_subset) > 0:
            stat = FeatureStats(
                feature_name='trap_baseline',
                feature_threshold=0,
                total_samples=len(trap_subset),
                win_count=trap_subset['win'].sum(),
                total_pnl=trap_subset['pnl_pct'].sum(),
                max_drawdown=trap_subset['max_drawdown_pct'].max()
            )
            stats.append(stat)
        
        # 转换为DataFrame
        stats_data = [s.to_dict() for s in stats]
        return pd.DataFrame(stats_data)
    
    def generate_report(self, output_dir: Path):
        """生成回测报告 - 包含维持能力过滤器统计"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. 保存所有交易记录
        trades_file = output_dir / f"replay_trades_{timestamp}.json"
        trades_data = [ReplayResult._trade_to_dict(t) for t in self.all_trades]
        with open(trades_file, 'w', encoding='utf-8') as f:
            json.dump(trades_data, f, ensure_ascii=False, indent=2)
        
        # 2. 保存特征统计
        stats_df = self.analyze_features()
        stats_file = output_dir / f"feature_stats_{timestamp}.csv"
        stats_df.to_csv(stats_file, index=False)
        
        # 3. 控制台报告
        print("\n" + "="*80)
        print("回测统计报告")
        print("="*80)
        
        if self.all_trades:
            total_trades = len(self.all_trades)
            win_trades = sum(1 for t in self.all_trades if t.pnl_pct > 0)
            total_pnl = sum(t.pnl_pct for t in self.all_trades)
            avg_max_dd = sum(t.max_drawdown_pct for t in self.all_trades) / total_trades
            
            print(f"\n总交易次数: {total_trades}")
            print(f"胜率: {win_trades/total_trades:.1%}")
            print(f"平均盈亏: {total_pnl/total_trades:+.2f}%")
            print(f"平均最大回撤: {avg_max_dd:.2f}%")
            
            print("\n特征表现统计:")
            print(stats_df.to_string(index=False))
        
        # 新增：维持能力过滤器统计
        if self.use_sustain_filter:
            print("\n" + "-"*80)
            print("维持能力过滤器统计")
            print("-"*80)
            
            filtered_trades = [t for t in self.all_trades if t.sustain_ability > 0]
            if filtered_trades:
                avg_sustain = sum(t.sustain_ability for t in filtered_trades) / len(filtered_trades)
                print(f"通过过滤器的交易数: {len(filtered_trades)}/{len(self.all_trades)}")
                print(f"平均维持时长: {avg_sustain:.1f}分钟")
                
                # 对比有过滤器 vs 无过滤器
                win_rate_filtered = sum(1 for t in filtered_trades if t.pnl_pct > 0) / len(filtered_trades)
                print(f"过滤器后胜率: {win_rate_filtered:.1%}")
        
        print("\n" + "="*80)
        print(f"报告已保存:")
        print(f"  交易记录: {trades_file}")
        print(f"  特征统计: {stats_file}")
        print("="*80 + "\n")


# ==================== 测试代码 ====================
if __name__ == "__main__":
    print("行为回放引擎测试 - 维持能力过滤器对比")
    print("="*80)
    
    test_stocks = [
        ("300017", "网宿科技"),
        ("000547", "航天发展"),
        ("300058", "蓝色光标"),
    ]
    
    # 测试1：有过滤器
    print("\n【测试1】启用维持能力过滤器")
    engine_with_filter = BehaviorReplayEngine(
        use_sustain_filter=True
    )
    results_with = engine_with_filter.replay_universe(
        stock_list=test_stocks,
        start_date="2026-01-20",
        end_date="2026-01-31"
    )
    engine_with_filter.generate_report(PROJECT_ROOT / "data" / "backtest_results" / "with_filter")
    
    # 测试2：无过滤器（原始逻辑）
    print("\n【测试2】禁用维持能力过滤器（原始逻辑）")
    engine_without_filter = BehaviorReplayEngine(
        use_sustain_filter=False
    )
    results_without = engine_without_filter.replay_universe(
        stock_list=test_stocks,
        start_date="2026-01-20",
        end_date="2026-01-31"
    )
    engine_without_filter.generate_report(PROJECT_ROOT / "data" / "backtest_results" / "without_filter")
    
    # 对比结果
    print("\n" + "="*80)
    print("对比结果")
    print("="*80)
    print(f"有过滤器交易数: {len(engine_with_filter.all_trades)}")
    print(f"无过滤器交易数: {len(engine_without_filter.all_trades)}")
    if engine_with_filter.all_trades and engine_without_filter.all_trades:
        win_rate_with = sum(1 for t in engine_with_filter.all_trades if t.pnl_pct > 0) / len(engine_with_filter.all_trades)
        win_rate_without = sum(1 for t in engine_without_filter.all_trades if t.pnl_pct > 0) / len(engine_without_filter.all_trades)
        print(f"有过滤器胜率: {win_rate_with:.1%}")
        print(f"无过滤器胜率: {win_rate_without:.1%}")
