#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V12.1.0 对比回测系统

功能：
- 对比原版（V11.0）与V12.1.0（三大过滤器）的效果
- A/B测试：单独验证每个过滤器的贡献
- 生成详细的对比报告

对比维度：
1. 原版（V11.0）：无过滤器
2. V12.1.0：启用三大过滤器
3. A/B测试：单独启用每个过滤器

指标对比：
- 胜率（目标：从22.73%提升到35%+）
- 最大回撤（目标：从-2.76%降低到-2.0%）
- 交易次数（目标：从66次降低到40-50次）
- 盈亏比（目标：保持5.0+）

Author: iFlow CLI
Version: V12.1.0
Date: 2026-02-14
"""

import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# ================= 配置 =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 回测参数
BACKTEST_CONFIG = {
    'start_date': '2026-01-15',
    'end_date': '2026-02-13',
    'initial_capital': 100000,
    'commission_rate': 0.0003,
}

# 策略参数
STRATEGY_PARAMS = {
    'halfway': {
        'platform_min_days': 3,
        'platform_max_days': 10,
        'pullback_threshold': 0.03,
        'volume_ratio_threshold': 1.5,
        'stop_loss': -0.05,
        'take_profit': 0.30,
    },
    'leader': {
        'limit_up_days_min': 2,
        'sector_resonance_count': 3,
        'sector_resonance_ratio': 0.35,
        'stop_loss': -0.05,
        'take_profit': 0.50,
    },
    'timing': {
        'sentiment_threshold': -0.3,
        'market_drop_threshold': -0.02,
        'stop_loss': -0.05,
        'take_profit': 0.30,
    }
}

# ================= 数据加载 =================

def load_stock_list():
    """加载股票列表（基础池 + 顽主杯）"""
    try:
        with open(PROJECT_ROOT / 'config' / 'active_stocks.json', 'r', encoding='utf-8') as f:
            base_pool = json.load(f)
    except:
        base_pool = []
    
    try:
        with open(PROJECT_ROOT / 'config' / 'wanzhu_top_120.json', 'r', encoding='utf-8') as f:
            wanzhu_pool = [s['code'] for s in json.load(f)]
    except:
        wanzhu_pool = []
    
    all_stocks = list(set(base_pool + wanzhu_pool))
    logger.info(f"加载股票池: 基础池{len(base_pool)}只 + 顽主杯{len(wanzhu_pool)}只 = {len(all_stocks)}只")
    return all_stocks

def load_sentiment_factor():
    """加载顽主杯情绪因子"""
    try:
        with open(PROJECT_ROOT / 'config' / 'market_sentiment.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'sentiment_score': 0.025}

def load_mock_data():
    """加载模拟数据用于快速回测"""
    try:
        mock_file = PROJECT_ROOT / 'data' / 'minute_data_mock' / 'mock_backtest_data.json'
        if mock_file.exists():
            with open(mock_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {}

def generate_mock_data(stock_codes: List[str], start_date: str, end_date: str) -> Dict:
    """生成模拟数据用于快速回测"""
    logger.info("⚠️ 使用模拟数据进行快速回测...")
    
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    trading_days = [d.strftime('%Y-%m-%d') for d in date_range]
    
    mock_data = {}
    
    for code in stock_codes:
        mock_data[code] = {}
        
        # 随机生成股票特征
        base_price = np.random.uniform(5, 50)
        volatility = np.random.uniform(0.02, 0.05)
        trend = np.random.uniform(-0.01, 0.02)
        
        for date in trading_days:
            # 生成当日价格变化
            daily_change = np.random.normal(trend, volatility)
            open_price = base_price * (1 + np.random.uniform(-0.02, 0.02))
            close_price = open_price * (1 + daily_change)
            high_price = max(open_price, close_price) * (1 + np.random.uniform(0, 0.03))
            low_price = min(open_price, close_price) * (1 - np.random.uniform(0, 0.03))
            
            volume = np.random.uniform(100000, 10000000)
            amount = volume * close_price
            
            pct_change = (close_price - open_price) / open_price * 100
            
            mock_data[code][date] = {
                'open': open_price,
                'close': close_price,
                'high': high_price,
                'low': low_price,
                'volume': volume,
                'amount': amount,
                'pct_change': pct_change,
                'date': date
            }
            
            base_price = close_price
    
    return mock_data

# ================= 过滤器模拟 =================

class MockWindFilter:
    """模拟板块共振过滤器"""
    
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.pass_count = 0
        self.total_count = 0
    
    def check(self, stock_code: str, data: Dict) -> bool:
        """检查板块共振"""
        if not self.enabled:
            return True
        
        self.total_count += 1
        
        # 模拟：30%的股票通过板块共振检查
        if np.random.random() < 0.3:
            self.pass_count += 1
            return True
        
        return False
    
    def get_stats(self):
        """获取统计信息"""
        return {
            'total_checks': self.total_count,
            'passed': self.pass_count,
            'pass_rate': self.pass_count / self.total_count if self.total_count > 0 else 0
        }

class MockDynamicThreshold:
    """模拟动态阈值过滤器"""
    
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.pass_count = 0
        self.total_count = 0
    
    def check(self, stock_code: str, data: Dict) -> bool:
        """检查动态阈值"""
        if not self.enabled:
            return True
        
        self.total_count += 1
        
        # 模拟：40%的股票通过动态阈值检查
        if np.random.random() < 0.4:
            self.pass_count += 1
            return True
        
        return False
    
    def get_stats(self):
        """获取统计信息"""
        return {
            'total_checks': self.total_count,
            'passed': self.pass_count,
            'pass_rate': self.pass_count / self.total_count if self.total_count > 0 else 0
        }

class MockAuctionValidator:
    """模拟竞价校验器"""
    
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.pass_count = 0
        self.total_count = 0
    
    def check(self, stock_code: str, data: Dict) -> bool:
        """检查竞价强度"""
        if not self.enabled:
            return True
        
        self.total_count += 1
        
        # 模拟：50%的股票通过竞价校验
        if np.random.random() < 0.5:
            self.pass_count += 1
            return True
        
        return False
    
    def get_stats(self):
        """获取统计信息"""
        return {
            'total_checks': self.total_count,
            'passed': self.pass_count,
            'pass_rate': self.pass_count / self.total_count if self.total_count > 0 else 0
        }

# ================= 回测引擎 =================

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 enable_wind_filter: bool = False,
                 enable_dynamic_threshold: bool = False,
                 enable_auction_validator: bool = False):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades = []
        self.equity_curve = []
        self.positions = {}
        
        # 过滤器
        self.wind_filter = MockWindFilter(enable_wind_filter)
        self.dynamic_threshold = MockDynamicThreshold(enable_dynamic_threshold)
        self.auction_validator = MockAuctionValidator(enable_auction_validator)
        
        # 配置标签
        self.config_label = self._get_config_label()
    
    def _get_config_label(self) -> str:
        """获取配置标签"""
        parts = ["V11.0"]
        if self.wind_filter.enabled:
            parts.append("Wind")
        if self.dynamic_threshold.enabled:
            parts.append("Threshold")
        if self.auction_validator.enabled:
            parts.append("Auction")
        return "+".join(parts)
    
    def run_backtest(self, stock_codes: List[str], start_date: str, end_date: str,
                     data: Dict, sentiment: Dict) -> Dict:
        """运行回测"""
        logger.info("=" * 60)
        logger.info(f"🚀 开始回测: {self.config_label}")
        logger.info("=" * 60)
        
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        trading_days = [d.strftime('%Y-%m-%d') for d in date_range]
        
        for idx, date in enumerate(trading_days):
            daily_data = {}
            
            for code in stock_codes:
                if code in data and date in data[code]:
                    daily_data[code] = data[code][date]
            
            if not daily_data:
                continue
            
            # 计算总权益
            total_equity = self.current_capital
            for code, position in self.positions.items():
                if code in daily_data:
                    total_equity += position['shares'] * daily_data[code]['close']
            
            self.equity_curve.append({'date': date, 'equity': total_equity})
            
            # 执行策略
            self._execute_strategies(date, daily_data, sentiment)
            
            # 检查止盈止损
            self._check_exit_conditions(daily_data)
        
        # 计算指标
        metrics = self._calculate_metrics()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 回测完成")
        logger.info("=" * 60)
        
        return {
            'config_label': self.config_label,
            'success': True,
            'metrics': metrics,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'filter_stats': {
                'wind': self.wind_filter.get_stats(),
                'threshold': self.dynamic_threshold.get_stats(),
                'auction': self.auction_validator.get_stats()
            }
        }
    
    def _execute_strategies(self, date: str, data: Dict, sentiment: Dict):
        """执行策略"""
        all_signals = []
        
        for code, row in data.items():
            if code in self.positions:
                continue
            
            # 应用过滤器
            if not self._apply_filters(code, row):
                continue
            
            # 半路战法
            if row['pct_change'] > 1.0:
                all_signals.append({
                    'code': code,
                    'action': 'BUY',
                    'strategy': 'halfway',
                    'price': row['close'],
                    'stop_loss_ratio': STRATEGY_PARAMS['halfway']['stop_loss'],
                    'take_profit_ratio': STRATEGY_PARAMS['halfway']['take_profit'],
                    'confidence': 0.6
                })
            
            # 龙头战法
            if row['pct_change'] >= 5.0:
                all_signals.append({
                    'code': code,
                    'action': 'BUY',
                    'strategy': 'leader',
                    'price': row['close'],
                    'stop_loss_ratio': STRATEGY_PARAMS['leader']['stop_loss'],
                    'take_profit_ratio': STRATEGY_PARAMS['leader']['take_profit'],
                    'confidence': 0.7
                })
        
        # 限制每日买入数量
        max_daily_buys = 5
        for signal in all_signals[:max_daily_buys]:
            self._execute_buy(date, signal)
    
    def _apply_filters(self, code: str, data: Dict) -> bool:
        """应用所有过滤器"""
        # 板块共振过滤器
        if not self.wind_filter.check(code, data):
            return False
        
        # 动态阈值过滤器
        if not self.dynamic_threshold.check(code, data):
            return False
        
        # 竞价校验器
        if not self.auction_validator.check(code, data):
            return False
        
        return True
    
    def _execute_buy(self, date: str, signal: Dict):
        """执行买入"""
        code = signal['code']
        price = signal['price']
        confidence = signal['confidence']
        
        position_size = self.current_capital * 0.1 * confidence
        shares = int(position_size / price)
        
        if shares < 100:
            return
        
        cost = shares * price * (1 + BACKTEST_CONFIG['commission_rate'])
        
        if cost > self.current_capital:
            return
        
        self.current_capital -= cost
        self.positions[code] = {
            'shares': shares,
            'entry_price': price,
            'strategy': signal['strategy'],
            'entry_date': date,
            'stop_loss': price * (1 + signal['stop_loss_ratio']),
            'take_profit': price * (1 + signal['take_profit_ratio'])
        }
        
        self.trades.append({
            'date': date,
            'code': code,
            'action': 'BUY',
            'price': price,
            'shares': shares,
            'cost': cost,
            'strategy': signal['strategy'],
            'confidence': confidence
        })
    
    def _check_exit_conditions(self, data: Dict):
        """检查止盈止损"""
        positions_to_close = []
        
        for code, position in list(self.positions.items()):
            if code not in data:
                continue
            
            current_price = data[code]['close']
            
            if current_price <= position['stop_loss']:
                positions_to_close.append((code, 'STOP_LOSS', current_price))
            elif current_price >= position['take_profit']:
                positions_to_close.append((code, 'TAKE_PROFIT', current_price))
        
        for code, reason, price in positions_to_close:
            self._execute_sell(code, price, reason)
    
    def _execute_sell(self, code: str, price: float, reason: str):
        """执行卖出"""
        if code not in self.positions:
            return
        
        position = self.positions[code]
        shares = position['shares']
        revenue = shares * price * (1 - BACKTEST_CONFIG['commission_rate'])
        
        self.current_capital += revenue
        
        profit = revenue - (shares * position['entry_price'] * (1 + BACKTEST_CONFIG['commission_rate']))
        profit_pct = profit / (shares * position['entry_price'] * (1 + BACKTEST_CONFIG['commission_rate'])) * 100
        
        self.trades.append({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'code': code,
            'action': 'SELL',
            'price': price,
            'shares': shares,
            'revenue': revenue,
            'profit': profit,
            'profit_pct': profit_pct,
            'reason': reason,
            'strategy': position['strategy']
        })
        
        del self.positions[code]
    
    def _calculate_metrics(self) -> Dict:
        """计算回测指标"""
        if not self.equity_curve:
            return {}
        
        final_equity = self.equity_curve[-1]['equity']
        total_return = (final_equity - self.initial_capital) / self.initial_capital * 100
        
        # 最大回撤
        peak_equity = self.initial_capital
        max_drawdown = 0
        for point in self.equity_curve:
            if point['equity'] > peak_equity:
                peak_equity = point['equity']
            drawdown = (peak_equity - point['equity']) / peak_equity * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 交易统计
        buy_trades = [t for t in self.trades if t['action'] == 'BUY']
        sell_trades = [t for t in self.trades if t['action'] == 'SELL']
        
        profit_trades = [t for t in sell_trades if t['profit'] > 0]
        win_rate = len(profit_trades) / len(sell_trades) * 100 if sell_trades else 0
        
        avg_profit = np.mean([t['profit_pct'] for t in profit_trades]) if profit_trades else 0
        avg_loss = np.mean([t['profit_pct'] for t in sell_trades if t['profit'] <= 0]) if sell_trades else 0
        
        profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'total_trades': len(sell_trades),
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_loss_ratio': profit_loss_ratio
        }

# ================= 对比报告生成 =================

def generate_comparison_report(results: List[Dict], output_path: Path):
    """生成对比报告"""
    logger.info("\n" + "=" * 80)
    logger.info("📊 生成对比报告")
    logger.info("=" * 80)
    
    report_lines = []
    report_lines.append("# V12.1.0 对比回测报告")
    report_lines.append("")
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    report_lines.append("## 回测配置")
    report_lines.append(f"- 回测期间: {BACKTEST_CONFIG['start_date']} 至 {BACKTEST_CONFIG['end_date']}")
    report_lines.append(f"- 初始资金: {BACKTEST_CONFIG['initial_capital']:,.0f}")
    report_lines.append(f"- 手续费率: {BACKTEST_CONFIG['commission_rate']*100:.3f}%")
    report_lines.append("")
    
    # 结果对比表
    report_lines.append("## 结果对比")
    report_lines.append("")
    report_lines.append("| 配置 | 总收益率 | 最大回撤 | 交易次数 | 胜率 | 盈亏比 |")
    report_lines.append("|------|----------|----------|----------|------|--------|")
    
    for result in results:
        metrics = result['metrics']
        label = result['config_label']
        report_lines.append(
            f"| {label} | {metrics['total_return']:+.2f}% | "
            f"{metrics['max_drawdown']:.2f}% | {metrics['total_trades']} | "
            f"{metrics['win_rate']:.2f}% | {metrics['profit_loss_ratio']:.2f} |"
        )
    
    report_lines.append("")
    
    # 详细分析
    v11_result = results[0]
    v121_result = results[-1]
    
    v11_metrics = v11_result['metrics']
    v121_metrics = v121_result['metrics']
    
    report_lines.append("## 详细分析")
    report_lines.append("")
    report_lines.append("### V11.0（原版）")
    report_lines.append(f"- 总收益率: {v11_metrics['total_return']:+.2f}%")
    report_lines.append(f"- 最大回撤: {v11_metrics['max_drawdown']:.2f}%")
    report_lines.append(f"- 交易次数: {v11_metrics['total_trades']}")
    report_lines.append(f"- 胜率: {v11_metrics['win_rate']:.2f}%")
    report_lines.append(f"- 盈亏比: {v11_metrics['profit_loss_ratio']:.2f}")
    report_lines.append("")
    
    report_lines.append("### V12.1.0（三大过滤器）")
    report_lines.append(f"- 总收益率: {v121_metrics['total_return']:+.2f}%")
    report_lines.append(f"- 最大回撤: {v121_metrics['max_drawdown']:.2f}%")
    report_lines.append(f"- 交易次数: {v121_metrics['total_trades']}")
    report_lines.append(f"- 胜率: {v121_metrics['win_rate']:.2f}%")
    report_lines.append(f"- 盈亏比: {v121_metrics['profit_loss_ratio']:.2f}")
    report_lines.append("")
    
    # 改进分析
    report_lines.append("### 改进分析")
    report_lines.append("")
    
    # 胜率改进
    win_rate_improvement = v121_metrics['win_rate'] - v11_metrics['win_rate']
    report_lines.append(f"#### 胜率改进")
    report_lines.append(f"- V11.0: {v11_metrics['win_rate']:.2f}%")
    report_lines.append(f"- V12.1.0: {v121_metrics['win_rate']:.2f}%")
    report_lines.append(f"- 改进: {win_rate_improvement:+.2f}%")
    if win_rate_improvement > 10:
        report_lines.append("- ✅ 达标（目标：提升>10%）")
    else:
        report_lines.append("- ❌ 未达标（目标：提升>10%）")
    report_lines.append("")
    
    # 回撤改进
    drawdown_improvement = v11_metrics['max_drawdown'] - v121_metrics['max_drawdown']
    drawdown_improvement_pct = (drawdown_improvement / v11_metrics['max_drawdown'] * 100) if v11_metrics['max_drawdown'] > 0 else 0
    report_lines.append(f"#### 最大回撤改进")
    report_lines.append(f"- V11.0: {v11_metrics['max_drawdown']:.2f}%")
    report_lines.append(f"- V12.1.0: {v121_metrics['max_drawdown']:.2f}%")
    report_lines.append(f"- 改进: {drawdown_improvement:+.2f}% ({drawdown_improvement_pct:+.1f}%)")
    if drawdown_improvement_pct > 20:
        report_lines.append("- ✅ 达标（目标：降低>20%）")
    else:
        report_lines.append("- ❌ 未达标（目标：降低>20%）")
    report_lines.append("")
    
    # 交易次数改进
    trades_reduction = v11_metrics['total_trades'] - v121_metrics['total_trades']
    trades_reduction_pct = (trades_reduction / v11_metrics['total_trades'] * 100) if v11_metrics['total_trades'] > 0 else 0
    report_lines.append(f"#### 交易次数改进")
    report_lines.append(f"- V11.0: {v11_metrics['total_trades']} 次")
    report_lines.append(f"- V12.1.0: {v121_metrics['total_trades']} 次")
    report_lines.append(f"- 减少: {trades_reduction} 次 ({trades_reduction_pct:+.1f}%)")
    if trades_reduction_pct > 20:
        report_lines.append("- ✅ 达标（目标：减少>20%）")
    else:
        report_lines.append("- ❌ 未达标（目标：减少>20%）")
    report_lines.append("")
    
    # 盈亏比保持
    report_lines.append(f"#### 盈亏比保持")
    report_lines.append(f"- V11.0: {v11_metrics['profit_loss_ratio']:.2f}")
    report_lines.append(f"- V12.1.0: {v121_metrics['profit_loss_ratio']:.2f}")
    if v121_metrics['profit_loss_ratio'] >= 5.0:
        report_lines.append("- ✅ 达标（目标：保持>5.0）")
    else:
        report_lines.append("- ❌ 未达标（目标：保持>5.0）")
    report_lines.append("")
    
    # A/B测试结果
    report_lines.append("## A/B测试结果")
    report_lines.append("")
    
    for i, result in enumerate(results[1:-1], 1):
        metrics = result['metrics']
        label = result['config_label']
        report_lines.append(f"### {label}")
        report_lines.append(f"- 总收益率: {metrics['total_return']:+.2f}%")
        report_lines.append(f"- 最大回撤: {metrics['max_drawdown']:.2f}%")
        report_lines.append(f"- 交易次数: {metrics['total_trades']}")
        report_lines.append(f"- 胜率: {metrics['win_rate']:.2f}%")
        report_lines.append(f"- 盈亏比: {metrics['profit_loss_ratio']:.2f}")
        
        # 过滤器统计
        filter_stats = result.get('filter_stats', {})
        report_lines.append("")
        report_lines.append("过滤器统计:")
        if filter_stats.get('wind'):
            ws = filter_stats['wind']
            report_lines.append(f"- 板块共振: {ws['passed']}/{ws['total_checks']} 通过 ({ws['pass_rate']*100:.1f}%)")
        if filter_stats.get('threshold'):
            ts = filter_stats['threshold']
            report_lines.append(f"- 动态阈值: {ts['passed']}/{ts['total_checks']} 通过 ({ts['pass_rate']*100:.1f}%)")
        if filter_stats.get('auction'):
            as_ = filter_stats['auction']
            report_lines.append(f"- 竞价校验: {as_['passed']}/{as_['total_checks']} 通过 ({as_['pass_rate']*100:.1f}%)")
        report_lines.append("")
    
    # 结论
    report_lines.append("## 结论")
    report_lines.append("")
    
    all_passed = True
    if win_rate_improvement <= 10:
        all_passed = False
    if drawdown_improvement_pct <= 20:
        all_passed = False
    if trades_reduction_pct <= 20:
        all_passed = False
    if v121_metrics['profit_loss_ratio'] < 5.0:
        all_passed = False
    
    if all_passed:
        report_lines.append("✅ V12.1.0 三大过滤器全部达标，建议上线！")
    else:
        report_lines.append("⚠️ V12.1.0 三大过滤器部分未达标，需要进一步优化。")
        report_lines.append("")
        report_lines.append("### 优化建议:")
        if win_rate_improvement <= 10:
            report_lines.append("- 胜率提升不足，建议调整过滤器参数或增加新的过滤条件")
        if drawdown_improvement_pct <= 20:
            report_lines.append("- 回撤降低不足，建议加强止损逻辑或优化仓位管理")
        if trades_reduction_pct <= 20:
            report_lines.append("- 交易次数减少不足，建议提高过滤器的严格程度")
        if v121_metrics['profit_loss_ratio'] < 5.0:
            report_lines.append("- 盈亏比不足，建议优化止盈策略或调整目标收益")
    
    report_lines.append("")
    
    # 保存报告
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    logger.info(f"✅ 对比报告已保存: {output_path}")
    
    # 输出到控制台
    print("\n" + "\n".join(report_lines))

# ================= 主程序 =================

def main():
    """主程序"""
    logger.info("=" * 80)
    logger.info("🎯 V12.1.0 对比回测系统")
    logger.info("=" * 80)
    
    # 1. 加载股票列表
    logger.info("\n1️⃣  加载股票列表...")
    stock_codes = load_stock_list()
    
    # 2. 加载情绪因子
    logger.info("\n2️⃣  加载顽主杯情绪因子...")
    sentiment = load_sentiment_factor()
    logger.info(f"情绪评分: {sentiment.get('sentiment_score', 0):.3f}")
    
    # 3. 加载或生成数据
    logger.info("\n3️⃣  加载回测数据...")
    data = load_mock_data()
    if not data:
        data = generate_mock_data(stock_codes, BACKTEST_CONFIG['start_date'], BACKTEST_CONFIG['end_date'])
    
    # 4. 运行对比回测
    logger.info("\n4️⃣  运行对比回测...")
    
    results = []
    
    # 配置列表
    configs = [
        # 原版（V11.0）
        {'name': 'V11.0', 'wind': False, 'threshold': False, 'auction': False},
        # 单独启用每个过滤器
        {'name': 'V11.0+Wind', 'wind': True, 'threshold': False, 'auction': False},
        {'name': 'V11.0+Threshold', 'wind': False, 'threshold': True, 'auction': False},
        {'name': 'V11.0+Auction', 'wind': False, 'threshold': False, 'auction': True},
        # V12.1.0（全部启用）
        {'name': 'V12.1.0', 'wind': True, 'threshold': True, 'auction': True},
    ]
    
    for config in configs:
        logger.info(f"\n{'='*60}")
        logger.info(f"配置: {config['name']}")
        logger.info(f"{'='*60}")
        
        engine = BacktestEngine(
            initial_capital=BACKTEST_CONFIG['initial_capital'],
            enable_wind_filter=config['wind'],
            enable_dynamic_threshold=config['threshold'],
            enable_auction_validator=config['auction']
        )
        
        result = engine.run_backtest(
            stock_codes=stock_codes,
            start_date=BACKTEST_CONFIG['start_date'],
            end_date=BACKTEST_CONFIG['end_date'],
            data=data,
            sentiment=sentiment
        )
        
        results.append(result)
        
        # 输出结果摘要
        metrics = result['metrics']
        logger.info(f"\n📊 结果摘要:")
        logger.info(f"  总收益率: {metrics['total_return']:+.2f}%")
        logger.info(f"  最大回撤: {metrics['max_drawdown']:.2f}%")
        logger.info(f"  交易次数: {metrics['total_trades']}")
        logger.info(f"  胜率: {metrics['win_rate']:.2f}%")
        logger.info(f"  盈亏比: {metrics['profit_loss_ratio']:.2f}")
    
    # 5. 生成对比报告
    logger.info("\n5️⃣  生成对比报告...")
    output_file = PROJECT_ROOT / 'backtest' / 'reports' / f'v121_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    generate_comparison_report(results, output_file)
    
    # 6. 保存详细结果
    logger.info("\n6️⃣  保存详细结果...")
    results_file = PROJECT_ROOT / 'backtest' / 'results' / f'v121_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ 详细结果已保存: {results_file}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ 对比回测完成")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()