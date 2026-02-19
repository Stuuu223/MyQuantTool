"""
综合回测脚本 - 三大战法全部回测

⚠️  V17生产约束声明 / 研究用途标记
==============================================================================
【重要】本脚本使用独立SimpleBacktestEngine，不是V17官方回测流水线

根据 SIGNAL_AND_PORTFOLIO_CONTRACT.md V17生产约束：
- V17上线前唯一认可的回测命令：run_tick_replay_backtest.py（使用统一BacktestEngine）
- 本脚本（run_comprehensive_backtest.py）禁止作为V17上线决策依据
- 本脚本仅用于：多战法综合测试、历史对比研究、技术验证

V18任务：将SimpleBacktestEngine统一迁移到BacktestEngine框架（Issue待创建）
==============================================================================

包含战法：
- 半路战法
- 龙头战法
- 时机斧
- 顽主杯情绪因子集成
"""

import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
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
    'start_date': '2026-01-15',  # 近1个月（优化：减少数据加载时间）
    'end_date': '2026-02-13',
    'initial_capital': 100000,
    'commission_rate': 0.0003,  # 万三手续费
}

# 策略参数
STRATEGY_PARAMS = {
    'halfway': {
        'platform_min_days': 3,
        'platform_max_days': 10,
        'pullback_threshold': 0.03,  # 回调幅度 < 3%
        'volume_ratio_threshold': 1.5,  # 突破量比 > 1.5
        'stop_loss': -0.05,  # 止损 -5%
        'take_profit': 0.30,  # 止盈 +30%
    },
    'leader': {
        'limit_up_days_min': 2,  # 至少2板
        'sector_resonance_count': 3,  # 板块涨停股 >= 3
        'sector_resonance_ratio': 0.35,  # 板块上涨比例 >= 35%
        'stop_loss': -0.05,
        'take_profit': 0.50,  # 龙头目标 +50%
    },
    'timing': {
        'sentiment_threshold': -0.3,  # 情绪评分 < -0.3 时防守
        'market_drop_threshold': -0.02,  # 大盘跌幅 > 2% 时防守
        'stop_loss': -0.05,
        'take_profit': 0.30,
    }
}

# ================= 数据加载 =================

def load_stock_list():
    """加载股票列表（基础池 + 顽主杯）"""
    # 加载基础池
    with open(PROJECT_ROOT / 'config' / 'active_stocks.json', 'r', encoding='utf-8') as f:
        base_pool = json.load(f)
    
    # 加载顽主杯（统一使用wanzhu_selected_150.csv）
    wanzhu_csv = PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv'
    if wanzhu_csv.exists():
        import pandas as pd
        wanzhu_df = pd.read_csv(wanzhu_csv)
        wanzhu_pool = wanzhu_df['code'].tolist()
    else:
        wanzhu_pool = []
        logger.warning(f"顽主榜单文件不存在: {wanzhu_csv}")
    
    # 合并去重
    all_stocks = list(set(base_pool + wanzhu_pool))
    logger.info(f"加载股票池: 基础池{len(base_pool)}只 + 顽主杯{len(wanzhu_pool)}只 = {len(all_stocks)}只")
    
    # 只返回有Tick数据的股票（优化性能）
    from pathlib import Path
    tick_stocks = set()
    for market in ['SH', 'SZ']:
        tick_dir = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir' / market / '0'
        if tick_dir.exists():
            for stock_dir in tick_dir.iterdir():
                if stock_dir.is_dir():
                    tick_stocks.add(f'{stock_dir.name}.{market}')
    
    available_stocks = [s for s in all_stocks if s in tick_stocks]
    logger.info(f"有Tick数据的股票: {len(available_stocks)}只")
    
    return available_stocks

def load_sentiment_factor():
    """加载顽主杯情绪因子"""
    try:
        with open(PROJECT_ROOT / 'config' / 'market_sentiment.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'sentiment_score': 0}

def load_tick_data(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """加载Tick数据"""
    try:
        from xtquant import xtdata
        
        # 使用QMT数据
        start_time = start_date.replace('-', '') + '093000'
        end_time = end_date.replace('-', '') + '150000'
        
        # 尝试获取分钟线数据（如果Tick数据不可用）
        df = xtdata.get_market_data_ex(
            field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
            stock_list=[stock_code],
            period='1m',
            start_time=start_time,
            end_time=end_time
        )
        
        if stock_code in df and not df[stock_code].empty:
            # 索引是字符串格式的时间戳（如'20260213093000'），直接使用索引
            result_df = df[stock_code].copy()
            
            # 将索引转换为datetime
            result_df.index = pd.to_datetime(result_df.index, format='%Y%m%d%H%M%S')
            
            # 添加日期列
            result_df['date'] = result_df.index.strftime('%Y-%m-%d')
            
            return result_df
        
        return pd.DataFrame()
    except Exception as e:
        logger.warning(f"加载 {stock_code} 数据失败: {e}")
        return pd.DataFrame()

# ================= 策略函数 =================

def halfway_strategy(date: str, data: Dict, params: Dict) -> List[Dict]:
    """
    半路战法策略

    条件：
    1. 平台调整3-10天
    2. 突破平台高点 >= 1%
    3. 突破成交量 >= 平台期平均量的1.5倍
    """
    signals = []

    for code, row in data.items():
        # 使用预计算的涨幅
        pct_change = row['pct_change']

        # 半路战法条件
        if pct_change > 1.0:  # 涨幅 > 1%
            volume_ratio = row['volume'] / (row['amount'] / row['close'] + 1)

            if volume_ratio > params['volume_ratio_threshold']:
                signals.append({
                    'code': code,
                    'action': 'BUY',
                    'strategy': 'halfway',
                    'price': row['close'],
                    'stop_loss_ratio': params['stop_loss'],
                    'take_profit_ratio': params['take_profit'],
                    'confidence': 0.6
                })

    return signals

def leader_strategy(date: str, data: Dict, params: Dict) -> List[Dict]:
    """
    龙头战法策略

    条件：
    1. 连续涨停 >= 2板
    2. 涨幅 >= 5%
    3. 板块共振（涨停股 >= 3，上涨比例 >= 35%）
    """
    signals = []

    for code, row in data.items():
        # 使用预计算的涨幅
        pct_change = row['pct_change']

        if pct_change >= 5.0:  # 涨幅 >= 5%
            signals.append({
                'code': code,
                'action': 'BUY',
                'strategy': 'leader',
                'price': row['close'],
                'stop_loss_ratio': params['stop_loss'],
                'take_profit_ratio': params['take_profit'],
                'confidence': 0.7
            })

    return signals

def timing_strategy(date: str, data: Dict, sentiment: Dict, params: Dict) -> List[Dict]:
    """
    时机斧策略

    条件：
    1. 情绪评分 >= -0.3（非冰点）
    2. 情绪评分 > 0 时，积极进攻
    3. 情绪评分 < -0.3 时，防守模式
    """
    signals = []

    sentiment_score = sentiment.get('sentiment_score', 0)

    # 情绪评分过滤
    if sentiment_score < params['sentiment_threshold']:
        logger.info(f"情绪评分 {sentiment_score} < {params['sentiment_threshold']}，进入防守模式")
        return signals

    for code, row in data.items():
        # 使用预计算的涨幅
        pct_change = row['pct_change']

        # 根据情绪调整策略
        if sentiment_score > 0:
            # 积极模式：涨幅 >= 2%
            threshold = 2.0
            confidence = 0.7
        else:
            # 谨慎模式：涨幅 >= 3%
            threshold = 3.0
            confidence = 0.5

        if pct_change >= threshold:
            signals.append({
                'code': code,
                'action': 'BUY',
                'strategy': 'timing',
                'price': row['close'],
                'stop_loss_ratio': params['stop_loss'],
                'take_profit_ratio': params['take_profit'],
                'confidence': confidence
            })

    return signals

# ================= 回测引擎 =================

class SimpleBacktestEngine:
    """简单回测引擎"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades = []
        self.equity_curve = []
        self.positions = {}  # {code: {'shares': float, 'entry_price': float, 'strategy': str}}
    
    def run_backtest(self, stock_codes: List[str], start_date: str, end_date: str,
                     sentiment: Dict) -> Dict:
        """运行回测"""
        logger.info("=" * 60)
        logger.info("🚀 开始综合回测")
        logger.info("=" * 60)
        logger.info(f"回测时间: {start_date} 至 {end_date}")
        logger.info(f"股票数量: {len(stock_codes)} 只")
        logger.info(f"初始资金: {self.initial_capital:,.0f}")
        logger.info(f"情绪评分: {sentiment.get('sentiment_score', 0):.3f}")
        logger.info("")

        # 生成日期列表
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        trading_days = [d.strftime('%Y-%m-%d') for d in date_range]

        logger.info(f"交易日数量: {len(trading_days)} 天")

        # 逐日回测
        for idx, date in enumerate(trading_days):
            logger.info(f"\n{'='*60}")
            logger.info(f"📅 回测日期: {date} ({idx+1}/{len(trading_days)})")
            logger.info(f"{'='*60}")

            # 加载当日数据
            daily_data = {}
            for code in stock_codes:
                df = load_tick_data(code, start_date, end_date)
                if not df.empty:
                    # 筛选当日的数据（9:30-15:00）
                    daily_df = df[df['date'] == date]
                    if not daily_df.empty:
                        # 使用当日第一根K线的开盘价和最后一根K线的收盘价
                        first_row = daily_df.iloc[0]
                        last_row = daily_df.iloc[-1]

                        # 计算当日涨幅
                        pct_change = (last_row['close'] - first_row['open']) / first_row['open'] * 100

                        daily_data[code] = {
                            'open': first_row['open'],
                            'close': last_row['close'],
                            'high': daily_df['high'].max(),
                            'low': daily_df['low'].min(),
                            'volume': daily_df['volume'].sum(),
                            'amount': daily_df['amount'].sum(),
                            'pct_change': pct_change,
                            'date': date
                        }

            if not daily_data:
                logger.info(f"当日无数据，跳过")
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

            logger.info(f"当日总权益: {total_equity:,.0f}")
        
        # 计算回测指标
        metrics = self._calculate_metrics()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 回测完成")
        logger.info("=" * 60)
        
        return {
            'success': True,
            'metrics': metrics,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
    
    def _execute_strategies(self, date: str, data: Dict, sentiment: Dict):
        """执行所有策略"""
        all_signals = []
        
        # 半路战法
        halfway_signals = halfway_strategy(date, data, STRATEGY_PARAMS['halfway'])
        all_signals.extend(halfway_signals)
        
        # 龙头战法
        leader_signals = leader_strategy(date, data, STRATEGY_PARAMS['leader'])
        all_signals.extend(leader_signals)
        
        # 时机斧
        timing_signals = timing_strategy(date, data, sentiment, STRATEGY_PARAMS['timing'])
        all_signals.extend(timing_signals)
        
        # 去重：同一股票当天只买入一次
        unique_signals = {}
        for signal in all_signals:
            code = signal['code']
            if code not in self.positions and code not in unique_signals:
                unique_signals[code] = signal
        
        # 执行买入
        for signal in unique_signals.values():
            self._execute_buy(date, signal)
    
    def _execute_buy(self, date: str, signal: Dict):
        """执行买入"""
        code = signal['code']
        price = signal['price']
        strategy = signal['strategy']
        confidence = signal['confidence']
        
        # 计算仓位（根据置信度调整）
        position_size = self.current_capital * 0.1 * confidence  # 单只股票最大10%仓位
        shares = int(position_size / price)
        
        if shares < 100:
            logger.info(f"  ⚠️  {code} 资金不足，跳过买入")
            return
        
        cost = shares * price * (1 + BACKTEST_CONFIG['commission_rate'])
        
        if cost > self.current_capital:
            logger.info(f"  ⚠️  {code} 资金不足，跳过买入")
            return
        
        self.current_capital -= cost
        self.positions[code] = {
            'shares': shares,
            'entry_price': price,
            'strategy': strategy,
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
            'strategy': strategy,
            'confidence': confidence
        })
        
        logger.info(f"  ✅ 买入 {code} {strategy} 价格:{price:.2f} 数量:{shares} 成本:{cost:,.0f}")
    
    def _check_exit_conditions(self, data: Dict):
        """检查止盈止损"""
        positions_to_close = []
        
        for code, position in list(self.positions.items()):
            if code not in data:
                continue
            
            current_price = data[code]['close']
            
            # 检查止损
            if current_price <= position['stop_loss']:
                positions_to_close.append((code, 'STOP_LOSS', current_price))
            
            # 检查止盈
            elif current_price >= position['take_profit']:
                positions_to_close.append((code, 'TAKE_PROFIT', current_price))
        
        # 执行卖出
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
        
        logger.info(f"  ✅ 卖出 {code} {position['strategy']} 价格:{price:.2f} 盈亏:{profit:+.0f} ({profit_pct:+.2f}%) 原因:{reason}")
        
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

# ================= 主程序 =================

def main():
    """主程序"""
    logger.info("=" * 60)
    logger.info("🎯 MyQuantTool 综合回测系统")
    logger.info("=" * 60)
    
    # 1. 加载股票列表
    logger.info("\n1️⃣  加载股票列表...")
    stock_codes = load_stock_list()
    
    # 2. 加载情绪因子
    logger.info("\n2️⃣  加载顽主杯情绪因子...")
    sentiment = load_sentiment_factor()
    
    # 3. 运行回测
    logger.info("\n3️⃣  运行回测...")
    engine = SimpleBacktestEngine(initial_capital=BACKTEST_CONFIG['initial_capital'])
    result = engine.run_backtest(
        stock_codes=stock_codes,
        start_date=BACKTEST_CONFIG['start_date'],
        end_date=BACKTEST_CONFIG['end_date'],
        sentiment=sentiment
    )
    
    # 4. 输出结果
    if result['success']:
        metrics = result['metrics']
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 回测结果")
        logger.info("=" * 60)
        logger.info(f"初始资金: {metrics['initial_capital']:,.0f}")
        logger.info(f"最终权益: {metrics['final_equity']:,.0f}")
        logger.info(f"总收益率: {metrics['total_return']:+.2f}%")
        logger.info(f"最大回撤: {metrics['max_drawdown']:.2f}%")
        logger.info(f"交易次数: {metrics['total_trades']} 次")
        logger.info(f"胜率: {metrics['win_rate']:.2f}%")
        logger.info(f"平均盈利: {metrics['avg_profit']:.2f}%")
        logger.info(f"平均亏损: {metrics['avg_loss']:.2f}%")
        logger.info(f"盈亏比: {metrics['profit_loss_ratio']:.2f}")
        logger.info("=" * 60)
        
        # 保存结果
        output_file = PROJECT_ROOT / 'backtest' / 'results' / f'comprehensive_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n✅ 回测结果已保存: {output_file}")
    else:
        logger.error("❌ 回测失败")

if __name__ == "__main__":
    main()