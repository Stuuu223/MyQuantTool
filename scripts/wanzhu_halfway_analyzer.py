#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顽主杯HALFWAY策略分析器

分析HALFWAY策略在顽主杯强势股上的表现：
1. 从顽主杯历史排名数据中提取每只股票的"首次上榜日期"
2. 在首次上榜前的N个交易日进行HALFWAY回测
3. 统计HALFWAY提前捕捉到信号的比例、提前天数、盈亏分布

Author: AI Project Director
Version: V1.0
Date: 2026-02-18
"""

import sys
import json
import csv
import random
import argparse
import requests
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import pandas as pd
import numpy as np

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backtest.run_single_holding_t1_backtest import (
    SingleHoldingT1Backtester, HalfwaySignalAdapter, CostModel, T1BacktestResult
)
from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy
from logic.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WanzhuStockInfo:
    """顽主杯股票信息"""
    code: str
    name: str
    first_rank_date: str
    first_rank_pos: int
    first_rank_weight: float
    sector: str = ""


@dataclass
class HalfwayPreRankResult:
    """单只股票回测结果"""
    stock_code: str
    stock_name: str
    first_rank_date: str
    backtest_start_date: str
    backtest_end_date: str
    days_before_rank: int
    
    # 信号统计
    has_signal: bool = False
    signal_date: Optional[str] = None
    signal_time: Optional[str] = None
    signal_price: Optional[float] = None
    signal_strength: Optional[float] = None
    days_ahead: Optional[int] = None  # 提前天数
    
    # 盈亏统计（如果有信号）
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    exit_date: Optional[str] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    exit_reason: Optional[str] = None
    
    # Raw信号统计
    raw_signal_count: int = 0
    executable_signal_count: int = 0
    
    # 错误信息
    error: Optional[str] = None


class WanzhuDataGenerator:
    """顽主杯Mock数据生成器
    
    由于真实历史排名数据可能不可用，生成合理的mock数据用于测试
    """
    
    def __init__(self, start_date: str = "2025-01-01", end_date: str = "2025-12-31"):
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
    def generate_mock_history(
        self, 
        stock_list: List[Dict],
        output_path: Path,
        min_appearances: int = 1,
        max_appearances: int = 5
    ) -> pd.DataFrame:
        """生成Mock历史排名数据
        
        Args:
            stock_list: 股票列表 [{code, name, sector}]
            output_path: 输出CSV路径
            min_appearances: 每只股票最少上榜次数
            max_appearances: 每只股票最多上榜次数
            
        Returns:
            pd.DataFrame: 生成的历史数据
        """
        records = []
        
        # 生成交易日列表（排除周末）
        trading_days = []
        current = self.start_date
        while current <= self.end_date:
            if current.weekday() < 5:  # 周一到周五
                trading_days.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        logger.info(f"生成Mock数据: {len(trading_days)}个交易日, {len(stock_list)}只股票")
        
        for stock in stock_list:
            code = stock['code']
            name = stock.get('name', '')
            sector = stock.get('sector', '')
            
            # 随机决定这只股票上榜几次
            num_appearances = random.randint(min_appearances, max_appearances)
            
            # 随机选择上榜日期（确保日期递增）
            if len(trading_days) >= num_appearances:
                rank_dates = sorted(random.sample(trading_days, num_appearances))
            else:
                rank_dates = trading_days[:num_appearances]
            
            for i, date in enumerate(rank_dates):
                # 首次上榜排名更靠前，后续可能波动
                if i == 0:
                    rank = random.randint(1, 30)
                    weight = round(random.uniform(0.8, 1.0), 2)
                else:
                    rank = random.randint(10, 80)
                    weight = round(random.uniform(0.5, 0.9), 2)
                
                records.append({
                    'date': date,
                    'code': code,
                    'name': name,
                    'rank': rank,
                    'weight': weight,
                    'sector': sector
                })
        
        # 按日期排序
        df = pd.DataFrame(records)
        df = df.sort_values(['date', 'rank']).reset_index(drop=True)
        
        # 保存CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"Mock数据已保存: {output_path} ({len(df)}条记录)")
        
        return df


class WanzhuAPILoader:
    """顽主杯官方API数据加载器
    
    从官方API获取历史排名数据:
    https://www.hunanwanzhu.com/api/rankings?date=YYYY-MM-DD
    """
    
    def __init__(self, base_url: str = "https://www.hunanwanzhu.com/api/rankings"):
        self.base_url = base_url
        self.session = requests.Session()
        # 设置请求头模拟浏览器
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def fetch_rankings_by_date(self, date_str: str) -> List[Dict]:
        """获取指定日期的排行榜数据
        
        Args:
            date_str: 日期字符串 (YYYY-MM-DD)
            
        Returns:
            List[Dict]: 排名记录列表
        """
        url = f"{self.base_url}?date={date_str}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析API返回的数据
            # 根据实际API结构调整字段映射
            records = []
            if isinstance(data, list):
                # 如果返回的是列表格式
                for item in data:
                    record = {
                        'date': date_str,
                        'code': item.get('code') or item.get('stock_code'),
                        'name': item.get('name') or item.get('stock_name'),
                        'rank': item.get('rank'),
                        'weight': item.get('weight') or item.get('position_weight', 0),
                        'player_id': item.get('player_id') or item.get('user_id'),
                        'sector': item.get('sector', '')
                    }
                    records.append(record)
            elif isinstance(data, dict):
                # 如果返回的是字典格式，提取data字段
                items = data.get('data', []) or data.get('rankings', []) or data.get('list', [])
                for item in items:
                    record = {
                        'date': date_str,
                        'code': item.get('code') or item.get('stock_code'),
                        'name': item.get('name') or item.get('stock_name'),
                        'rank': item.get('rank'),
                        'weight': item.get('weight') or item.get('position_weight', 0),
                        'player_id': item.get('player_id') or item.get('user_id'),
                        'sector': item.get('sector', '')
                    }
                    records.append(record)
            
            logger.info(f"获取 {date_str} 数据: {len(records)}条记录")
            return records
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取 {date_str} 数据失败: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"解析 {date_str} 数据失败: {e}")
            return []
    
    def fetch_date_range(
        self, 
        start_date: str, 
        end_date: str,
        delay_seconds: float = 0.5
    ) -> pd.DataFrame:
        """获取日期范围内的所有排名数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            delay_seconds: 请求间隔秒数(避免请求过快)
            
        Returns:
            pd.DataFrame: 所有日期的排名数据
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        all_records = []
        current = start
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            records = self.fetch_rankings_by_date(date_str)
            all_records.extend(records)
            
            # 延迟避免请求过快
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            
            current += timedelta(days=1)
        
        if not all_records:
            logger.warning("未获取到任何数据")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_records)
        df = df.sort_values(['date', 'rank']).reset_index(drop=True)
        
        logger.info(f"获取完成: {len(df)}条记录，日期范围 {start_date} 至 {end_date}")
        return df
    
    def save_to_csv(self, df: pd.DataFrame, output_path: Path):
        """保存数据到CSV"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"数据已保存: {output_path}")


class WanzhuDataLoader:
    """顽主杯数据加载器"""
    
    def __init__(self, history_csv_path: Optional[Path] = None):
        self.history_csv_path = history_csv_path
        self.history_df: Optional[pd.DataFrame] = None
        self.first_rank_dict: Dict[str, WanzhuStockInfo] = {}
        
    def load_from_csv(self, csv_path: Path) -> pd.DataFrame:
        """从CSV加载历史排名数据"""
        if not csv_path.exists():
            raise FileNotFoundError(f"历史数据文件不存在: {csv_path}")
        
        df = pd.read_csv(csv_path)
        required_cols = ['date', 'code', 'rank', 'weight']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"CSV缺少必要列: {col}")
        
        self.history_df = df
        logger.info(f"加载历史数据: {len(df)}条记录")
        return df
    
    def extract_first_rank_info(self) -> Dict[str, WanzhuStockInfo]:
        """提取每只股票的首次上榜信息"""
        if self.history_df is None:
            raise ValueError("请先调用load_from_csv加载数据")
        
        # 按code分组，找出每只股票的最早上榜日期
        grouped = self.history_df.groupby('code').agg({
            'date': 'min',
            'rank': 'first',
            'weight': 'first',
            'name': 'first',
            'sector': 'first'
        }).reset_index()
        
        for _, row in grouped.iterrows():
            info = WanzhuStockInfo(
                code=row['code'],
                name=row.get('name', ''),
                first_rank_date=row['date'],
                first_rank_pos=int(row['rank']),
                first_rank_weight=float(row['weight']),
                sector=row.get('sector', '')
            )
            self.first_rank_dict[row['code']] = info
        
        logger.info(f"提取首次上榜信息: {len(self.first_rank_dict)}只股票")
        return self.first_rank_dict
    
    def get_stock_list(self) -> List[str]:
        """获取股票代码列表"""
        return list(self.first_rank_dict.keys())


class WanzhuHalfwayAnalyzer:
    """顽主杯HALFWAY分析器"""
    
    def __init__(
        self,
        lookback_days: int = 5,
        strategy_params: Optional[Dict] = None,
        initial_capital: float = 100000.0,
        position_size: float = 0.5,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.05,
        max_holding_minutes: int = 120,
    ):
        self.lookback_days = lookback_days
        self.strategy_params = strategy_params or {
            'volatility_threshold': 0.02,
            'volume_surge': 1.2,
            'breakout_strength': 0.005,
            'window_minutes': 30,
            'min_history_points': 5
        }
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_holding_minutes = max_holding_minutes
        
        self.results: List[HalfwayPreRankResult] = []
        
    def _get_trading_days_before(
        self, 
        target_date: str, 
        n_days: int
    ) -> Tuple[str, str]:
        """获取目标日期前N个交易日
        
        Returns:
            (start_date, end_date) - 回测窗口起止日期
        """
        target = datetime.strptime(target_date, "%Y-%m-%d")
        
        # 简单处理：往前推N+2个自然日（确保包含N个交易日）
        start = target - timedelta(days=n_days + 5)
        
        return start.strftime("%Y-%m-%d"), target_date
    
    def _run_single_stock_backtest(
        self, 
        stock_info: WanzhuStockInfo
    ) -> HalfwayPreRankResult:
        """对单只股票进行回测"""
        
        # 计算回测窗口
        start_date, end_date = self._get_trading_days_before(
            stock_info.first_rank_date, 
            self.lookback_days
        )
        
        # 创建结果对象
        result = HalfwayPreRankResult(
            stock_code=stock_info.code,
            stock_name=stock_info.name,
            first_rank_date=stock_info.first_rank_date,
            backtest_start_date=start_date,
            backtest_end_date=end_date,
            days_before_rank=self.lookback_days
        )
        
        logger.info(f"\n🔍 回测 {stock_info.code} ({stock_info.name})")
        logger.info(f"   首次上榜: {stock_info.first_rank_date}")
        logger.info(f"   回测窗口: {start_date} ~ {end_date}")
        
        try:
            # 创建HALFWAY策略
            halfway_strategy = HalfwayTickStrategy(self.strategy_params)
            signal_generator = HalfwaySignalAdapter(halfway_strategy)
            
            # 创建回测器
            backtester = SingleHoldingT1Backtester(
                initial_capital=self.initial_capital,
                position_size=self.position_size,
                stop_loss_pct=self.stop_loss_pct,
                take_profit_pct=self.take_profit_pct,
                max_holding_minutes=self.max_holding_minutes,
                signal_generator=signal_generator,
                cost_model=CostModel()
            )
            
            # 运行回测
            backtest_result = backtester.run_backtest(
                stock_codes=[stock_info.code],
                start_date=start_date,
                end_date=end_date
            )
            
            # 统计Raw信号
            result.raw_signal_count = backtest_result.raw_signal_total
            result.executable_signal_count = backtest_result.executable_signal_total
            
            logger.info(f"   Raw信号: {result.raw_signal_count}")
            logger.info(f"   Executable信号: {result.executable_signal_count}")
            logger.info(f"   实际成交: {backtest_result.trade_total}")
            
            # 检查是否在首次上榜前有信号
            if backtest_result.raw_signal_trades:
                # 找到第一个Raw信号
                first_signal = backtest_result.raw_signal_trades[0]
                result.has_signal = True
                result.signal_date = first_signal.entry_date
                result.signal_time = first_signal.entry_time
                result.signal_price = first_signal.entry_price
                
                # 计算提前天数
                signal_dt = datetime.strptime(first_signal.entry_date, "%Y-%m-%d")
                rank_dt = datetime.strptime(stock_info.first_rank_date, "%Y-%m-%d")
                result.days_ahead = (rank_dt - signal_dt).days
                
                logger.info(f"   ✅ 提前{result.days_ahead}天发现信号!")
                logger.info(f"      信号日期: {result.signal_date} {result.signal_time}")
                logger.info(f"      信号价格: {result.signal_price}")
            else:
                logger.info(f"   ❌ 未提前发现信号")
            
            # 如果有实际成交，记录盈亏
            if backtest_result.t1_trades:
                trade = backtest_result.t1_trades[0]
                result.entry_price = trade.entry_price
                result.exit_price = trade.exit_price
                result.exit_date = trade.exit_date
                result.pnl = trade.pnl
                result.pnl_pct = trade.pnl_pct
                result.exit_reason = trade.exit_reason
                
                if trade.pnl is not None:
                    logger.info(f"   盈亏: {trade.pnl_pct*100:.2f}% ({trade.exit_reason})")
            
        except Exception as e:
            logger.error(f"回测 {stock_info.code} 失败: {e}")
            result.error = str(e)
        
        return result
    
    def analyze_stocks(
        self, 
        stock_infos: List[WanzhuStockInfo],
        max_stocks: Optional[int] = None
    ) -> List[HalfwayPreRankResult]:
        """批量分析股票"""
        
        stocks_to_analyze = stock_infos[:max_stocks] if max_stocks else stock_infos
        logger.info(f"开始分析 {len(stocks_to_analyze)} 只股票...")
        
        for i, info in enumerate(stocks_to_analyze):
            logger.info(f"\n[{i+1}/{len(stocks_to_analyze)}] {info.code}")
            result = self._run_single_stock_backtest(info)
            self.results.append(result)
        
        return self.results
    
    def generate_report(self) -> Dict:
        """生成分析报告"""
        
        total = len(self.results)
        if total == 0:
            return {"error": "没有分析结果"}
        
        # 有信号的股票
        with_signals = [r for r in self.results if r.has_signal]
        # 无信号的股票
        without_signals = [r for r in self.results if not r.has_signal and not r.error]
        # 出错的股票
        with_errors = [r for r in self.results if r.error]
        
        # 计算提前天数统计
        days_ahead_list = [r.days_ahead for r in with_signals if r.days_ahead is not None]
        avg_days_ahead = np.mean(days_ahead_list) if days_ahead_list else 0
        
        # 计算盈亏统计（仅限有成交的股票）
        completed_trades = [r for r in self.results if r.pnl is not None]
        winning_trades = [r for r in completed_trades if r.pnl and r.pnl > 0]
        losing_trades = [r for r in completed_trades if r.pnl and r.pnl < 0]
        
        win_rate = len(winning_trades) / len(completed_trades) * 100 if completed_trades else 0
        avg_pnl_pct = np.mean([r.pnl_pct for r in completed_trades if r.pnl_pct]) * 100 if completed_trades else 0
        
        report = {
            "summary": {
                "total_stocks_analyzed": total,
                "stocks_with_signals": len(with_signals),
                "stocks_without_signals": len(without_signals),
                "stocks_with_errors": len(with_errors),
                "signal_detection_rate": round(len(with_signals) / total * 100, 2),
                "avg_days_ahead": round(avg_days_ahead, 2),
                "lookback_window_days": self.lookback_days,
            },
            "performance": {
                "completed_trades": len(completed_trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate_pct": round(win_rate, 2),
                "avg_pnl_pct": round(avg_pnl_pct, 2),
            },
            "data_quality": {
                "source": "api" if hasattr(self, '_use_api') and self._use_api else "csv/mock",
                "filter_applied": f"Top{args.min_rank}" if hasattr(args, 'min_rank') and args.min_rank > 0 else "none",
                "total_records_in_csv": len(loader.history_df) if 'loader' in locals() and loader.history_df is not None else 0,
            },
            "strategy_params": self.strategy_params,
            "details": [
                {
                    "stock_code": r.stock_code,
                    "stock_name": r.stock_name,
                    "first_rank_date": r.first_rank_date,
                    "has_signal": r.has_signal,
                    "signal_date": r.signal_date,
                    "days_ahead": r.days_ahead,
                    "pnl_pct": round(r.pnl_pct * 100, 2) if r.pnl_pct else None,
                    "exit_reason": r.exit_reason,
                    "error": r.error
                }
                for r in self.results
            ],
            "signals_detail": [
                {
                    "stock_code": r.stock_code,
                    "stock_name": r.stock_name,
                    "first_rank_date": r.first_rank_date,
                    "first_rank_pos": r.first_rank_pos if hasattr(r, 'first_rank_pos') else None,
                    "signal_date": r.signal_date,
                    "signal_time": r.signal_time,
                    "signal_price": r.signal_price,
                    "days_ahead": r.days_ahead,
                    "entry_price": r.entry_price,
                    "exit_price": r.exit_price,
                    "pnl_pct": round(r.pnl_pct * 100, 2) if r.pnl_pct else None,
                    "exit_reason": r.exit_reason,
                    "raw_signals": r.raw_signal_count,
                    "executable_signals": r.executable_signal_count
                }
                for r in with_signals
            ]
        }
        
        return report
    
    def save_report(self, output_path: Path):
        """保存报告到文件"""
        report = self.generate_report()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n💾 报告已保存: {output_path}")
        
        # 同时保存CSV格式
        csv_path = output_path.with_suffix('.csv')
        self._save_csv_report(csv_path)
        
        return report
    
    def _save_csv_report(self, csv_path: Path):
        """保存CSV格式报告"""
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                '股票代码', '股票名称', '首次上榜日期', '首次上榜排名',
                '是否有信号', '信号日期', '信号时间', '提前天数',
                '入场价格', '出场价格', '盈亏%', '出场原因',
                'Raw信号数', 'Executable信号数', '错误信息'
            ])
            
            for r in self.results:
                writer.writerow([
                    r.stock_code,
                    r.stock_name,
                    r.first_rank_date,
                    getattr(r, 'first_rank_pos', ''),
                    '是' if r.has_signal else '否',
                    r.signal_date or '',
                    r.signal_time or '',
                    r.days_ahead if r.days_ahead is not None else '',
                    round(r.entry_price, 2) if r.entry_price else '',
                    round(r.exit_price, 2) if r.exit_price else '',
                    round(r.pnl_pct * 100, 2) if r.pnl_pct else '',
                    r.exit_reason or '',
                    r.raw_signal_count,
                    r.executable_signal_count,
                    r.error or ''
                ])
        
        logger.info(f"💾 CSV报告已保存: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description='顽主杯HALFWAY策略分析器')
    parser.add_argument('--stocks-json', type=str, 
                        default='config/wanzhu_top_120.json',
                        help='顽主杯股票列表JSON文件')
    parser.add_argument('--history-csv', type=str,
                        default='data/wanzhu_history_mock.csv',
                        help='顽主杯历史排名CSV文件（如不存在则生成mock数据）')
    parser.add_argument('--output', type=str,
                        default='backtest/results/wanzhu_halfway_analysis.json',
                        help='输出报告路径')
    parser.add_argument('--lookback-days', type=int, default=5,
                        help='回测窗口：首次上榜前N个交易日')
    parser.add_argument('--max-stocks', type=int, default=None,
                        help='最多分析多少只股票（用于测试）')
    parser.add_argument('--generate-mock-only', action='store_true',
                        help='仅生成mock数据，不运行回测')
    
    # V17: 添加官方API数据获取选项
    parser.add_argument('--use-api', action='store_true',
                        help='使用官方API获取数据（默认使用本地CSV）')
    parser.add_argument('--api-start-date', type=str,
                        default='2025-11-01',
                        help='API数据获取开始日期 (YYYY-MM-DD)')
    parser.add_argument('--api-end-date', type=str,
                        default='2025-12-31',
                        help='API数据获取结束日期 (YYYY-MM-DD)')
    parser.add_argument('--api-delay', type=float, default=0.5,
                        help='API请求间隔秒数（避免请求过快）')
    parser.add_argument('--min-rank', type=int, default=10,
                        help='只处理排名在TopN以内的股票')
    
    args = parser.parse_args()
    
    # 路径处理
    stocks_json_path = PROJECT_ROOT / args.stocks_json
    history_csv_path = PROJECT_ROOT / args.history_csv
    output_path = PROJECT_ROOT / args.output
    
    logger.info("=" * 60)
    logger.info("顽主杯HALFWAY策略分析器")
    logger.info("=" * 60)
    
    # 1. 加载股票列表
    logger.info(f"\n📋 加载股票列表: {stocks_json_path}")
    with open(stocks_json_path, 'r', encoding='utf-8') as f:
        stock_list = json.load(f)
    
    # 确保格式正确
    if isinstance(stock_list, list) and len(stock_list) > 0:
        if isinstance(stock_list[0], str):
            # 如果是简单字符串列表，转换为dict格式
            stock_list = [{'code': code, 'name': '', 'sector': ''} for code in stock_list]
    
    logger.info(f"加载了 {len(stock_list)} 只股票")
    
    # 2. 准备历史数据（本地CSV或API获取）
    if args.use_api:
        # V17: 使用官方API获取数据
        logger.info(f"\n🌐 从官方API获取数据...")
        logger.info(f"   日期范围: {args.api_start_date} 至 {args.api_end_date}")
        logger.info(f"   请求间隔: {args.api_delay}秒")
        
        api_loader = WanzhuAPILoader()
        history_df = api_loader.fetch_date_range(
            start_date=args.api_start_date,
            end_date=args.api_end_date,
            delay_seconds=args.api_delay
        )
        
        if history_df.empty:
            logger.error("❌ API未返回数据，请检查网络连接或API地址")
            logger.info("💡 提示: 可以使用 --use-api 参数切换到本地CSV模式")
            return
        
        # 保存API数据到CSV（缓存）
        api_loader.save_to_csv(history_df, history_csv_path)
        logger.info(f"✅ API数据已缓存: {history_csv_path}")
        
    elif not history_csv_path.exists():
        logger.info(f"\n📝 生成Mock历史数据...")
        # 使用与QMT数据匹配的日期范围（2025年11月）
        generator = WanzhuDataGenerator(start_date="2025-11-01", end_date="2025-12-31")
        generator.generate_mock_history(
            stock_list=stock_list,
            output_path=history_csv_path,
            min_appearances=1,
            max_appearances=3
        )
    else:
        logger.info(f"\n📂 使用已有历史数据: {history_csv_path}")
    
    if args.generate_mock_only:
        logger.info("仅生成mock数据，退出")
        return
    
    # 3. 加载历史数据并提取首次上榜信息
    logger.info(f"\n📊 加载历史排名数据...")
    loader = WanzhuDataLoader()
    loader.load_from_csv(history_csv_path)
    first_rank_dict = loader.extract_first_rank_info()
    
    # V17: 应用排名过滤
    if args.min_rank > 0:
        logger.info(f"\n🔍 应用排名过滤: 只保留Top{args.min_rank}")
        filtered_dict = {
            code: info for code, info in first_rank_dict.items()
            if info.first_rank_pos <= args.min_rank
        }
        logger.info(f"过滤前: {len(first_rank_dict)}只，过滤后: {len(filtered_dict)}只")
        first_rank_dict = filtered_dict
    
    # 4. 运行分析
    logger.info(f"\n🎯 开始HALFWAY回测分析...")
    logger.info(f"   回测窗口: 首次上榜前 {args.lookback_days} 个交易日")
    
    analyzer = WanzhuHalfwayAnalyzer(lookback_days=args.lookback_days)
    
    stock_infos = list(first_rank_dict.values())
    analyzer.analyze_stocks(stock_infos, max_stocks=args.max_stocks)
    
    # 5. 生成报告
    report = analyzer.save_report(output_path)
    
    # 6. 打印摘要
    logger.info("\n" + "=" * 60)
    logger.info("📈 分析结果摘要")
    logger.info("=" * 60)
    
    summary = report['summary']
    performance = report['performance']
    
    logger.info(f"\n总体统计:")
    logger.info(f"  - 分析股票数: {summary['total_stocks_analyzed']}")
    logger.info(f"  - 提前发现信号: {summary['stocks_with_signals']} 只 ({summary['signal_detection_rate']}%)")
    logger.info(f"  - 平均提前天数: {summary['avg_days_ahead']} 天")
    logger.info(f"  - 数据出错: {summary['stocks_with_errors']} 只")
    
    logger.info(f"\n成交统计:")
    logger.info(f"  - 完成交易: {performance['completed_trades']} 笔")
    logger.info(f"  - 胜率: {performance['win_rate_pct']}%")
    logger.info(f"  - 平均盈亏: {performance['avg_pnl_pct']}%")
    
    logger.info("\n" + "=" * 60)
    logger.info("分析完成!")
    logger.info(f"详细报告: {output_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
