#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HALFWAY策略 20×30 回测脚本
使用BacktestEngine框架，输出格式与run_hot_cases_suite一致（可比性）

功能：
1. 从wanzhu_selected_150.csv加载股票池
2. 只选Tick完整的前20-30只
3. 运行20只股票×30天的回测
4. 输出与hot_cases_suite一致的JSON格式

作者: AI Assistant
日期: 2026-02-19
"""

import sys
import json
import time
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.strategies.halfway_core import evaluate_halfway_state, create_halfway_platform_detector
from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.strategies.tick_strategy_interface import TickData
from logic.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HalfwayBacktestConfig:
    """HALFWAY回测配置"""
    initial_capital: float = 100000.0
    position_size: float = 0.5  # 单吊仓位50%
    stop_loss_pct: float = 0.02  # 止损2%
    take_profit_pct: float = 0.05  # 止盈5%
    max_holding_minutes: int = 120  # 最大持有2小时
    
    # HALFWAY策略参数
    volatility_threshold: float = 0.02  # 波动率阈值（放宽）
    volume_surge: float = 1.2  # 量能放大倍数（放宽）
    breakout_strength: float = 0.005  # 突破强度（放宽）
    window_minutes: int = 30  # 平台期窗口
    min_history_points: int = 60  # 最小历史点数


class HalfwayTickAdapter:
    """
    HALFWAY策略Tick适配器
    将HALFWAY核心逻辑包装为Tick处理类
    """
    
    def __init__(self, config: HalfwayBacktestConfig):
        self.config = config
        self.params = {
            'volatility_threshold': config.volatility_threshold,
            'volume_surge': config.volume_surge,
            'breakout_strength': config.breakout_strength,
            'window_minutes': config.window_minutes,
            'min_history_points': config.min_history_points,
            'history_limit': 500
        }
        
        # 为每只股票创建独立的检测器
        self.detectors: Dict[str, Any] = {}
        self.price_histories: Dict[str, List] = {}
        self.volume_histories: Dict[str, List] = {}
        
        # 调试计数器
        self.debug_counters = {
            'total_ticks_processed': 0,
            'signals_generated': 0,
            'stocks_with_data': 0
        }
    
    def get_detector(self, stock_code: str):
        """获取或创建股票对应的检测器"""
        if stock_code not in self.detectors:
            self.detectors[stock_code] = create_halfway_platform_detector(self.params)
            self.price_histories[stock_code] = []
            self.volume_histories[stock_code] = []
        return self.detectors[stock_code]
    
    def process_tick(self, stock_code: str, tick: TickData) -> Optional[Dict]:
        """
        处理单个Tick，返回信号（如果有）
        
        Returns:
            Dict or None: 信号字典，包含price, time, strength, factors等
        """
        self.debug_counters['total_ticks_processed'] += 1
        
        # 获取检测器和历史数据
        detector = self.get_detector(stock_code)
        price_history = self.price_histories[stock_code]
        volume_history = self.volume_histories[stock_code]
        
        # 更新历史数据
        price_history.append((tick.time, tick.last_price))
        volume_history.append((tick.time, tick.volume))
        
        # 限制历史长度
        history_limit = self.params['history_limit']
        if len(price_history) > history_limit:
            price_history[:] = price_history[-history_limit:]
        if len(volume_history) > history_limit:
            volume_history[:] = volume_history[-history_limit:]
        
        # 检查历史数据是否足够
        if len(price_history) < self.params['min_history_points']:
            return None
        
        # 使用检测器评估
        result = detector(
            price_history,
            volume_history,
            tick.time,
            tick.last_price
        )
        
        if result.get('is_signal', False):
            self.debug_counters['signals_generated'] += 1
            return {
                'stock_code': stock_code,
                'time': tick.time,
                'price': tick.last_price,
                'strength': 1.0,
                'factors': result.get('factors', {}),
                'conditions': result.get('conditions', {}),
                'platform_state': result.get('platform_state', {})
            }
        
        return None
    
    def reset_daily(self):
        """每日重置（保持检测器状态连续）"""
        # 不清除历史数据，保持平台识别状态
        pass


class HalfwayBacktestRunner:
    """
    HALFWAY策略回测运行器
    输出格式与run_hot_cases_suite一致
    """
    
    def __init__(self, config: HalfwayBacktestConfig = None):
        self.config = config or HalfwayBacktestConfig()
        self.adapter = HalfwayTickAdapter(self.config)
        
    def load_stock_pool(self, csv_path: Path, top_n: int = 30) -> List[str]:
        """
        从CSV加载股票池，返回前N只股票的代码列表
        
        Args:
            csv_path: CSV文件路径
            top_n: 取前N只
            
        Returns:
            List[str]: 股票代码列表（格式：带后缀如000001.SZ）
        """
        df = pd.read_csv(csv_path)
        
        # 获取前N只
        top_stocks = df.head(top_n)
        
        # 转换代码格式（根据code列，添加.SZ或.SH后缀）
        codes = []
        for _, row in top_stocks.iterrows():
            code = str(row['code']).strip()
            # 根据代码规则添加后缀
            if code.startswith('6'):
                codes.append(f"{code}.SH")
            elif code.startswith(('0', '3')):
                codes.append(f"{code}.SZ")
            else:
                # 其他情况默认.SZ
                codes.append(f"{code}.SZ")
        
        logger.info(f"✅ 加载股票池: {len(codes)} 只 (从{csv_path.name}前{top_n}只)")
        return codes
    
    def filter_stocks_with_tick_data(self, stock_codes: List[str], 
                                     start_date: str, 
                                     end_date: str,
                                     min_days: int = 20) -> List[str]:
        """
        过滤出有足够Tick数据的股票
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            min_days: 最少需要多少天的数据
            
        Returns:
            List[str]: 有完整数据的股票代码
        """
        valid_stocks = []
        
        print(f"\n🔍 检查Tick数据完整性 ({start_date} 至 {end_date})...")
        
        for code in stock_codes:
            try:
                # 尝试获取第一天的数据作为检查
                provider = QMTHistoricalProvider(
                    stock_code=code,
                    start_time=start_date.replace('-', ''),
                    end_time=end_date.replace('-', ''),
                    period='tick'
                )
                
                # 获取tick数据
                tick_df = provider.get_raw_ticks()
                
                if not tick_df.empty and len(tick_df) > 100:
                    # 计算有多少个不同的交易日
                    tick_df['date'] = pd.to_datetime(tick_df['time'], unit='ms').dt.date
                    unique_days = tick_df['date'].nunique()
                    
                    if unique_days >= min_days:
                        valid_stocks.append(code)
                        print(f"  ✅ {code}: {len(tick_df)} ticks, {unique_days} 天")
                    else:
                        print(f"  ⚠️  {code}: 仅{unique_days}天数据（需要{min_days}天）")
                else:
                    print(f"  ❌ {code}: 无tick数据")
                    
            except Exception as e:
                print(f"  ❌ {code}: 获取失败 - {str(e)[:50]}")
                continue
        
        print(f"\n📊 数据检查完成: {len(valid_stocks)}/{len(stock_codes)} 只有完整数据")
        return valid_stocks
    
    def run_single_stock_backtest(self, stock_code: str, 
                                   start_date: str, 
                                   end_date: str) -> Dict[str, Any]:
        """
        运行单只股票回测
        
        Returns:
            Dict: 符合hot_cases_suite格式的回测结果
        """
        print(f"\n{'='*60}")
        print(f"📊 回测: {stock_code}")
        print(f"📅 日期: {start_date} ~ {end_date}")
        print(f"{'='*60}")
        
        initial_capital = self.config.initial_capital
        cash = initial_capital
        position = None  # 当前持仓
        trades = []
        equity_curve = []
        
        # 生成日期范围
        date_range = pd.date_range(start=start_date, end=end_date, freq='B')
        
        for date_obj in date_range:
            date_str = date_obj.strftime('%Y-%m-%d')
            
            try:
                # 获取当日tick数据
                next_day = (date_obj + timedelta(days=1)).strftime('%Y%m%d')
                provider = QMTHistoricalProvider(
                    stock_code=stock_code,
                    start_time=date_str.replace('-', ''),
                    end_time=next_day,
                    period='tick'
                )
                
                tick_df = provider.get_raw_ticks()
                if tick_df.empty:
                    continue
                
                # 按时间排序
                tick_df = tick_df.sort_values('time')
                
                # 处理每个tick
                for _, row in tick_df.iterrows():
                    tick = TickData(
                        time=int(row['time']),
                        last_price=float(row['lastPrice']),
                        volume=int(row['volume']),
                        amount=float(row['amount']),
                        bid_price=float(row['bidPrice'][0]) if isinstance(row['bidPrice'], list) else float(row['bidPrice']),
                        ask_price=float(row['askPrice'][0]) if isinstance(row['askPrice'], list) else float(row['askPrice']),
                        bid_vol=int(row['bidVol'][0]) if isinstance(row['bidVol'], list) else int(row['bidVol']),
                        ask_vol=int(row['askVol'][0]) if isinstance(row['askVol'], list) else int(row['askVol'])
                    )
                    
                    # 检查是否有持仓需要平仓
                    if position is not None:
                        entry_time = datetime.strptime(f"{position['entry_date']} {position['entry_time']}", 
                                                        '%Y-%m-%d %H:%M:%S')
                        current_time = datetime.fromtimestamp(tick.time / 1000)
                        holding_minutes = (current_time - entry_time).total_seconds() / 60
                        
                        pnl_pct = (tick.last_price - position['entry_price']) / position['entry_price']
                        
                        # 检查平仓条件
                        should_close = False
                        close_reason = None
                        
                        if pnl_pct >= self.config.take_profit_pct:
                            should_close = True
                            close_reason = 'take_profit'
                        elif pnl_pct <= -self.config.stop_loss_pct:
                            should_close = True
                            close_reason = 'stop_loss'
                        elif holding_minutes >= self.config.max_holding_minutes:
                            should_close = True
                            close_reason = 'time_exit'
                        
                        if should_close:
                            # 平仓
                            shares = position['shares']
                            sell_amount = shares * tick.last_price * 0.999  # 扣除手续费
                            profit = sell_amount - position['cost']
                            profit_pct = profit / position['cost']
                            
                            cash += sell_amount
                            
                            trade_sell = {
                                'date': date_str,
                                'code': stock_code,
                                'action': 'SELL',
                                'price': tick.last_price,
                                'shares': shares,
                                'amount': sell_amount,
                                'profit': profit,
                                'profit_ratio': profit_pct * 100,
                                'exit_reason': close_reason
                            }
                            trades.append(trade_sell)
                            
                            print(f"  📉 卖出 {date_str} {current_time.strftime('%H:%M:%S')} "
                                  f"@{tick.last_price:.2f} 盈亏:{profit_pct*100:.2f}% ({close_reason})")
                            
                            position = None
                            continue
                    
                    # 检查开仓信号
                    if position is None:
                        signal = self.adapter.process_tick(stock_code, tick)
                        
                        if signal:
                            # 计算可买数量
                            position_value = cash * self.config.position_size
                            shares = int(position_value / tick.last_price / 100) * 100
                            
                            if shares >= 100:
                                cost = shares * tick.last_price * 1.001  # 包含手续费
                                
                                if cost <= cash:
                                    cash -= cost
                                    
                                    current_time = datetime.fromtimestamp(tick.time / 1000)
                                    position = {
                                        'entry_date': date_str,
                                        'entry_time': current_time.strftime('%H:%M:%S'),
                                        'entry_price': tick.last_price,
                                        'shares': shares,
                                        'cost': cost
                                    }
                                    
                                    trade_buy = {
                                        'date': date_str,
                                        'code': stock_code,
                                        'action': 'BUY',
                                        'price': tick.last_price,
                                        'shares': shares,
                                        'amount': cost,
                                        'signal_score': signal['strength'],
                                        'factors': signal['factors']
                                    }
                                    trades.append(trade_buy)
                                    
                                    print(f"  📈 买入 {date_str} {current_time.strftime('%H:%M:%S')} "
                                          f"@{tick.last_price:.2f} {shares}股")
                
                # 记录日终权益
                equity = cash
                if position is not None:
                    last_price = tick_df['lastPrice'].iloc[-1]
                    equity += position['shares'] * last_price * 0.999
                
                equity_curve.append({
                    'date': date_str,
                    'equity': equity
                })
                
            except Exception as e:
                print(f"  ⚠️  {date_str}: 处理失败 - {str(e)[:50]}")
                continue
        
        # 计算最终权益（清仓）
        final_equity = cash
        if position is not None:
            # 使用最后已知价格估算
            final_equity += position['shares'] * position['entry_price'] * 0.999
        
        # 计算收益指标
        total_return = (final_equity - initial_capital) / initial_capital * 100
        
        # 计算最大回撤
        max_drawdown = 0.0
        peak = initial_capital
        for point in equity_curve:
            equity = point['equity']
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 统计交易
        buy_trades = [t for t in trades if t['action'] == 'BUY']
        sell_trades = [t for t in trades if t['action'] == 'SELL']
        
        winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(winning_trades) / len(sell_trades) * 100 if sell_trades else 0.0
        
        # 简化的夏普比率计算
        if len(equity_curve) > 1:
            returns = []
            for i in range(1, len(equity_curve)):
                ret = (equity_curve[i]['equity'] - equity_curve[i-1]['equity']) / equity_curve[i-1]['equity']
                returns.append(ret)
            sharpe_ratio = (sum(returns) / len(returns)) / (pd.Series(returns).std() + 1e-10) * (252 ** 0.5) if returns else 0.0
        else:
            sharpe_ratio = 0.0
        
        result = {
            'code': stock_code,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'max_drawdown': max_drawdown * 100,
            'total_trades': len(buy_trades),
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'trades': trades,
            'equity_curve': equity_curve,
            'debug_info': self.adapter.debug_counters.copy()
        }
        
        print(f"✅ 回测完成: {len(buy_trades)}笔交易, 收益率:{total_return:.2f}%, 胜率:{win_rate:.1f}%")
        
        return result
    
    def run_suite(self, stock_codes: List[str], start_date: str, end_date: str) -> Dict[str, Any]:
        """
        运行完整回测套件
        
        Returns:
            Dict: 符合hot_cases_suite格式的结果
        """
        print(f"\n{'='*80}")
        print(f"🚀 HALFWAY 20×30 回测套件")
        print(f"{'='*80}")
        print(f"📊 股票数: {len(stock_codes)}")
        print(f"📅 回测区间: {start_date} ~ {end_date}")
        print(f"⚙️  HALFWAY参数:")
        print(f"   - 波动率阈值: {self.config.volatility_threshold}")
        print(f"   - 量能阈值: {self.config.volume_surge}")
        print(f"   - 突破强度: {self.config.breakout_strength}")
        print(f"💰 交易参数:")
        print(f"   - 初始资金: {self.config.initial_capital:,.0f}")
        print(f"   - 仓位比例: {self.config.position_size*100:.0f}%")
        print(f"   - 止盈/止损: {self.config.take_profit_pct*100:.1f}%/{self.config.stop_loss_pct*100:.1f}%")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        # 运行每只股票回测
        results = []
        for i, code in enumerate(stock_codes, 1):
            print(f"\n【{i}/{len(stock_codes)}】")
            try:
                result = self.run_single_stock_backtest(code, start_date, end_date)
                results.append(result)
            except Exception as e:
                print(f"❌ {code} 回测失败: {e}")
                import traceback
                traceback.print_exc()
        
        elapsed_time = time.time() - start_time
        
        # 构建套件结果（与hot_cases_suite格式一致）
        suite_results = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'strategy': 'HALFWAY',
                'stock_count': len(stock_codes),
                'start_date': start_date,
                'end_date': end_date,
                'halfway_params': {
                    'volatility_threshold': self.config.volatility_threshold,
                    'volume_surge': self.config.volume_surge,
                    'breakout_strength': self.config.breakout_strength
                },
                'trading_params': {
                    'initial_capital': self.config.initial_capital,
                    'position_size': self.config.position_size,
                    'stop_loss_pct': self.config.stop_loss_pct,
                    'take_profit_pct': self.config.take_profit_pct,
                    'max_holding_minutes': self.config.max_holding_minutes
                }
            },
            'wanzhu': {
                'total_count': len(results),
                'results': results,
                'summary': self._calculate_summary(results)
            },
            'performance': {
                'elapsed_time_seconds': elapsed_time,
                'time_per_stock': elapsed_time / len(stock_codes) if stock_codes else 0
            }
        }
        
        return suite_results
    
    def _calculate_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """计算汇总统计"""
        if not results:
            return {}
        
        total_trades = sum(r['total_trades'] for r in results)
        
        # 计算加权胜率
        total_sell_trades = 0
        total_wins = 0
        for r in results:
            sells = len([t for t in r['trades'] if t['action'] == 'SELL'])
            wins = len([t for t in r['trades'] if t['action'] == 'SELL' and t.get('profit', 0) > 0])
            total_sell_trades += sells
            total_wins += wins
        
        avg_win_rate = total_wins / total_sell_trades * 100 if total_sell_trades > 0 else 0.0
        
        return {
            'total_stocks': len(results),
            'total_trades': total_trades,
            'avg_return': sum(r['total_return'] for r in results) / len(results),
            'avg_win_rate': avg_win_rate,
            'avg_max_drawdown': sum(r['max_drawdown'] for r in results) / len(results),
            'total_profit_stocks': len([r for r in results if r['total_return'] > 0]),
            'total_loss_stocks': len([r for r in results if r['total_return'] <= 0])
        }


def main():
    """主函数"""
    # 配置
    config = HalfwayBacktestConfig()
    
    # 创建运行器
    runner = HalfwayBacktestRunner(config)
    
    # 加载股票池 - 按出现次数排序，选最多的10只大哥股
    csv_path = PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv'
    df = pd.read_csv(csv_path)
    
    # 按appear_count降序排序，取前10只（大哥股）
    df_sorted = df.sort_values('appear_count', ascending=False)
    top10 = df_sorted.head(10)
    
    print("="*80)
    print("🎯 选中10只大哥股（按出现次数排序）:")
    print("="*80)
    for _, row in top10.iterrows():
        print(f"  {row['code']:>6} {row['name']:<8} 出现{row['appear_count']:>2}次  {row['layer']}")
    print()
    
    # 转换代码格式
    stock_codes = []
    for _, row in top10.iterrows():
        code = str(row['code']).strip()
        if code.startswith('6'):
            stock_codes.append(f"{code}.SH")
        elif code.startswith(('0', '3')):
            stock_codes.append(f"{code}.SZ")
        else:
            stock_codes.append(f"{code}.SZ")
    
    # 回测日期（匹配实际下载的数据范围）
    start_date = '2025-11-15'
    end_date = '2026-02-13'  # 与下载数据完全对齐
    
    # 过滤有完整数据的股票
    valid_stocks = runner.filter_stocks_with_tick_data(stock_codes, start_date, end_date, min_days=20)
    
    # 只取有数据的全部股票
    selected_stocks = valid_stocks
    
    print(f"\n📊 最终选中: {len(selected_stocks)}/10 只有完整Tick数据")
    
    # 运行回测套件
    results = runner.run_suite(selected_stocks, start_date, end_date)
    
    # 保存结果
    output_dir = PROJECT_ROOT / 'backtest' / 'results'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'halfway_20x30_{timestamp}.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n{'='*80}")
    print(f"💾 结果已保存: {output_file}")
    print(f"{'='*80}")
    
    # 打印汇总
    _print_summary(results)
    
    return results


def _print_summary(results: Dict):
    """打印汇总报告"""
    summary = results.get('wanzhu', {}).get('summary', {})
    performance = results.get('performance', {})
    
    print(f"\n📊 HALFWAY 20×30 回测汇总")
    print(f"{'='*80}")
    print(f"总股票数: {summary.get('total_stocks', 0)}")
    print(f"总交易次数: {summary.get('total_trades', 0)}")
    print(f"平均收益率: {summary.get('avg_return', 0):.2f}%")
    print(f"平均胜率: {summary.get('avg_win_rate', 0):.2f}%")
    print(f"平均最大回撤: {summary.get('avg_max_drawdown', 0):.2f}%")
    print(f"盈利股票数: {summary.get('total_profit_stocks', 0)}")
    print(f"亏损股票数: {summary.get('total_loss_stocks', 0)}")
    print(f"总耗时: {performance.get('elapsed_time_seconds', 0):.1f}秒")
    print(f"{'='*80}")


if __name__ == '__main__':
    try:
        results = main()
        print("\n✅ HALFWAY 20×30 回测完成")
    except Exception as e:
        print(f"\n❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
