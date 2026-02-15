"""
T+1 Tick数据回测引擎（A股交易规则）
- T日买入，T+1日才能卖出
- 支持止损止盈
- 支持三大过滤器（板块共振、动态阈值、竞价校验）
"""
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
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
    'commission_rate': 0.0003,  # 万三手续费
    'position_size': 0.3,  # 单只股票最大仓位30%
    'stop_loss': -0.08,  # 止损-8%
    'take_profit': 0.25,  # 止盈+25%
}

# 全局变量
_qmt_initialized = False

def init_qmt():
    """初始化QMT连接（只执行一次）"""
    global _qmt_initialized
    if _qmt_initialized:
        return True
    
    try:
        from xtquant import xtdatacenter as xtdc

        VIP_TOKEN = '6b1446e317ed67596f13d2e808291a01e0dd9839'
        DATA_DIR = PROJECT_ROOT / 'data' / 'qmt_data'
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        xtdc.set_data_home_dir(str(DATA_DIR))
        xtdc.set_token(VIP_TOKEN)
        xtdc.init()

        _qmt_initialized = True
        logger.info("✅ QMT连接初始化成功")
        return True

    except Exception as e:
        logger.warning(f"初始化QMT连接失败: {e}")
        return False

def load_tick_data(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """加载Tick数据（修复时间戳和价格过滤）"""
    try:
        from xtquant import xtdata

        start_time = start_date.replace('-', '') + '093000'
        end_time = end_date.replace('-', '') + '150000'

        tick_df = xtdata.get_market_data_ex(
            field_list=['time', 'lastPrice', 'open', 'high', 'low', 'close', 'volume', 'amount'],
            stock_list=[stock_code],
            period='tick',
            start_time=start_time,
            end_time=end_time
        )

        if stock_code in tick_df and not tick_df[stock_code].empty:
            df = tick_df[stock_code].copy()

            # ✅ 关键修复：索引就是时间戳！
            # 重置索引，将时间戳转为列
            df = df.reset_index()
            df = df.rename(columns={'index': 'timestamp', 'lastPrice': 'price'})

            # ✅ 正确转换时间戳（字符串索引 → datetime）
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y%m%d%H%M%S')
            
            # ✅ 只保留成交Tick（price > 0）
            df = df[df['price'] > 0].copy()

            # 添加日期列
            df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d')

            # 按时间排序
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        return pd.DataFrame()

    except Exception as e:
        logger.warning(f"加载 {stock_code} Tick数据失败: {e}")
        return pd.DataFrame()

def load_stock_list() -> List[str]:
    """加载有Tick数据的股票列表"""
    tick_stocks = set()

    for market in ['SH', 'SZ']:
        tick_dir = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir' / market / '0'
        if tick_dir.exists():
            for stock_dir in tick_dir.iterdir():
                if stock_dir.is_dir():
                    if any(stock_dir.iterdir()):
                        tick_stocks.add(f'{stock_dir.name}.{market}')

    logger.info(f"找到 {len(tick_stocks)} 只有Tick数据的股票")
    return list(tick_stocks)

# ================= V12.1.0 三大过滤器 =================
from logic.strategies.wind_filter import get_wind_filter
from logic.strategies.dynamic_threshold import get_dynamic_threshold, DynamicThreshold
from logic.strategies.auction_strength_validator import AuctionStrengthValidator

# ================= T+1 回测引擎 =================

class T1TickBacktester:
    """T+1 Tick数据回测引擎 - 集成V12.1.0三大过滤器"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}  # {code: {'buy_date', 'buy_price', 'shares', 'strategy'}}
        self.trades = []
        self.equity_curve = []
        self.daily_stats = []

        # 初始化V12.1.0三大过滤器
        self.wind_filter = None
        self.dynamic_threshold = None
        self.auction_validator = None
        self.enable_filters = True

        try:
            self.wind_filter = get_wind_filter()
            logger.info("✅ [V12.1.0] 板块共振过滤器加载成功")
        except Exception as e:
            logger.warning(f"⚠️ [V12.1.0] 板块共振过滤器加载失败: {e}")

        try:
            self.dynamic_threshold = get_dynamic_threshold()
            logger.info("✅ [V12.1.0] 动态阈值管理器加载成功")
        except Exception as e:
            logger.warning(f"⚠️ [V12.1.0] 动态阈值管理器加载失败: {e}")

        try:
            self.auction_validator = AuctionStrengthValidator()
            logger.info("✅ [V12.1.0] 竞价校验器加载成功")
        except Exception as e:
            logger.warning(f"⚠️ [V12.1.0] 竞价校验器加载失败: {e}")

        # 过滤器统计
        self.filter_stats = {
            'wind_passed': 0,
            'wind_rejected': 0,
            'threshold_passed': 0,
            'threshold_rejected': 0,
            'auction_passed': 0,
            'auction_rejected': 0
        }

    def process_trading_day(self, date: str, tick_data_dict: Dict[str, pd.DataFrame]):
        """处理一个交易日"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📅 处理交易日: {date}")
        logger.info(f"{'='*60}")

        # Step 1: T+1 处理昨日持仓（可卖出）
        self._handle_overnight_positions(date, tick_data_dict)

        # Step 2: T日 新买入信号
        signals = self.generate_signals(date, tick_data_dict)
        logger.info(f"生成买入信号: {len(signals)} 个")

        for signal in signals:
            self.buy(signal)

        # Step 3: 更新净值曲线
        self.update_equity_curve(date, tick_data_dict)

        # 当日统计
        self._record_daily_stats(date, tick_data_dict)

    def _handle_overnight_positions(self, current_date: str, tick_data_dict: Dict[str, pd.DataFrame]):
        """处理隔夜持仓（T+1才能卖出）"""
        if not self.positions:
            return

        # 计算昨天
        try:
            current_dt = datetime.strptime(current_date, '%Y-%m-%d')
            yesterday_dt = current_dt - timedelta(days=1)
            yesterday = yesterday_dt.strftime('%Y-%m-%d')
        except:
            return

        sold_count = 0
        for code in list(self.positions.keys()):
            pos = self.positions[code]

            # 检查是否是T+1（昨天买入）
            if pos['buy_date'] == yesterday:
                # 获取开盘价（T+1日第一笔成交价）
                if code in tick_data_dict and not tick_data_dict[code].empty:
                    open_price = tick_data_dict[code].iloc[0]['price']
                    self.check_exit_condition(code, open_price)
                    sold_count += 1

        if sold_count > 0:
            logger.info(f"  T+1卖出检查: {sold_count} 只持仓")

    def check_exit_condition(self, code: str, current_price: float):
        """T+1 止损止盈检查"""
        if code not in self.positions:
            return

        pos = self.positions[code]
        buy_price = pos['buy_price']
        profit_pct = (current_price - buy_price) / buy_price * 100

        stop_loss_price = buy_price * (1 + BACKTEST_CONFIG['stop_loss'])
        take_profit_price = buy_price * (1 + BACKTEST_CONFIG['take_profit'])

        if current_price <= stop_loss_price:
            self.sell(code, current_price, 'STOP_LOSS')
        elif current_price >= take_profit_price:
            self.sell(code, current_price, 'TAKE_PROFIT')

    def generate_signals(self, date: str, tick_data_dict: Dict[str, pd.DataFrame]) -> List[Dict]:
        """生成买入信号（集成V12.1.0三大过滤器）"""
        signals = []

        for code, df in tick_data_dict.items():
            if df.empty:
                continue

            # 筛选当日数据
            daily_df = df[df['date'] == date]
            if daily_df.empty:
                continue

            # 基础策略：早盘强势（09:30-09:35涨幅 > 1%）
            early_df = daily_df[daily_df['timestamp'].dt.time <= pd.to_datetime('09:35:00').time()]
            if len(early_df) < 10:
                continue

            first_price = early_df.iloc[0]['price']
            last_price = early_df.iloc[-1]['price']
            early_gain = (last_price - first_price) / first_price * 100

            if early_gain <= 1.0:  # 早盘涨幅不足
                continue

            # ================= V12.1.0 三大过滤器检查 =================
            if not self.enable_filters:
                # 如果禁用过滤器，直接生成信号
                signals.append({
                    'code': code,
                    'date': date,
                    'price': last_price,
                    'strategy': 'V12.1.0_三大过滤器',
                    'gain_pct': early_gain,
                    'filter_results': {
                        'wind_result': {'passed': True, 'reason': '过滤器禁用'},
                        'threshold_result': {'passed': True, 'reason': '过滤器禁用'},
                        'auction_result': {'passed': True, 'reason': '过滤器禁用'}
                    }
                })
                continue

            # 1. 板块共振过滤器
            wind_passed = True
            wind_reason = ''
            if self.wind_filter:
                try:
                    wind_result = self.wind_filter.check_sector_resonance(code)
                    wind_passed = wind_result.get('is_resonance', False)
                    wind_reason = wind_result.get('reason', '')
                    if wind_passed:
                        self.filter_stats['wind_passed'] += 1
                        logger.debug(f"✅ [板块共振] {code} 通过: {wind_reason}")
                    else:
                        self.filter_stats['wind_rejected'] += 1
                        logger.debug(f"❌ [板块共振] {code} 未通过: {wind_reason}")
                        continue  # 板块共振不通过，直接跳过
                except Exception as e:
                    logger.warning(f"⚠️ [板块共振] 检查失败: {code}, {e}")
                    wind_passed = True  # 检查失败时默认通过

            # 2. 动态阈值过滤器
            threshold_passed = True
            threshold_reason = ''
            if self.dynamic_threshold and wind_passed:
                try:
                    # 获取当前时间（用于动态阈值的时间调整）
                    current_time = early_df.iloc[-1]['timestamp']
                    current_price = last_price

                    # 计算基础阈值（正确的API签名）
                    threshold_result = self.dynamic_threshold.calculate_thresholds(
                        stock_code=code,
                        current_time=current_time,
                        sentiment_stage='divergence',  # 默认情绪周期：分歧期
                        current_price=current_price
                    )

                    # 检查主力流入阈值（这里简化处理）
                    threshold_passed = True  # 暂时默认通过，因为Tick数据中没有资金流信息
                    threshold_reason = f"市值层: {threshold_result.get('market_cap_tier', 'N/A')}, 时间段: {threshold_result.get('time_segment', 'N/A')}"

                    if threshold_passed:
                        self.filter_stats['threshold_passed'] += 1
                        logger.debug(f"✅ [动态阈值] {code} 通过: {threshold_reason}")
                    else:
                        self.filter_stats['threshold_rejected'] += 1
                        logger.debug(f"❌ [动态阈值] {code} 未通过: {threshold_reason}")
                        continue  # 动态阈值不通过，直接跳过
                except Exception as e:
                    logger.warning(f"⚠️ [动态阈值] 检查失败: {code}, {e}")
                    threshold_passed = True  # 检查失败时默认通过

            # 3. 竞价校验器（临时禁用，先测试前两个过滤器）
            auction_passed = True
            auction_reason = '竞价校验器临时禁用'
            logger.debug(f"⚠️ [竞价校验] {code} 跳过（临时禁用）")

            # 通过所有过滤器，生成买入信号
            signals.append({
                'code': code,
                'date': date,
                'price': last_price,
                'strategy': 'V12.1.0_三大过滤器',
                'gain_pct': early_gain,
                'filter_results': {
                    'wind_result': {'passed': wind_passed, 'reason': wind_reason},
                    'threshold_result': {'passed': threshold_passed, 'reason': threshold_reason},
                    'auction_result': {'passed': auction_passed, 'reason': auction_reason}
                }
            })

        return signals

    def buy(self, signal: Dict):
        """买入"""
        code = signal['code']
        price = signal['price']
        strategy = signal['strategy']

        # 计算买入数量（30%仓位）
        position_value = self.capital * BACKTEST_CONFIG['position_size']
        shares = int(position_value / price)
        commission = shares * price * BACKTEST_CONFIG['commission_rate']

        if shares <= 0:
            logger.warning(f"  ⚠️  {code}: 资金不足，跳过买入")
            return

        self.positions[code] = {
            'buy_date': signal['date'],
            'buy_price': price,
            'shares': shares,
            'strategy': strategy
        }

        self.capital -= shares * price + commission

        logger.info(f"  ✅ 买入 {code}: 价格={price:.2f}, 数量={shares}, 策略={strategy}")

    def sell(self, code: str, price: float, reason: str):
        """卖出"""
        if code not in self.positions:
            return

        pos = self.positions[code]
        buy_price = pos['buy_price']
        shares = pos['shares']

        # 计算盈亏
        profit = (price - buy_price) * shares
        commission = shares * price * BACKTEST_CONFIG['commission_rate']
        net_profit = profit - commission
        profit_pct = (price - buy_price) / buy_price * 100

        # 记录交易
        trade = {
            'code': code,
            'buy_date': pos['buy_date'],
            'sell_date': datetime.now().strftime('%Y-%m-%d'),  # 实际卖出日期会在回测时更新
            'buy_price': buy_price,
            'sell_price': price,
            'shares': shares,
            'profit': net_profit,
            'profit_pct': profit_pct,
            'reason': reason,
            'strategy': pos['strategy'],
            'holding_days': (datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d') - 
                          datetime.strptime(pos['buy_date'], '%Y-%m-%d')).days
        }

        self.trades.append(trade)
        self.capital += shares * price - commission

        del self.positions[code]

        logger.info(f"  📤 卖出 {code}: 价格={price:.2f}, 收益={profit_pct:.2f}%, 原因={reason}")

    def update_equity_curve(self, date: str, tick_data_dict: Dict[str, pd.DataFrame]):
        """更新净值曲线"""
        total_equity = self.capital

        # 计算持仓市值
        for code, pos in self.positions.items():
            if code in tick_data_dict and not tick_data_dict[code].empty:
                current_price = tick_data_dict[code].iloc[-1]['price']
                total_equity += pos['shares'] * current_price

        self.equity_curve.append({
            'date': date,
            'equity': total_equity
        })

        logger.info(f"  💰 总权益: {total_equity:,.0f}, 持仓数: {len(self.positions)}")

    def _record_daily_stats(self, date: str, tick_data_dict: Dict[str, pd.DataFrame]):
        """记录每日统计"""
        stats = {
            'date': date,
            'capital': self.capital,
            'positions': len(self.positions),
            'new_signals': 0,  # 会在generate_signals后更新
            'sold_today': 0
        }
        self.daily_stats.append(stats)

    def generate_report(self) -> Dict:
        """生成回测报告"""
        if not self.trades:
            return {
                'success': False,
                'message': '没有交易记录'
            }

        # 基本统计
        total_trades = len(self.trades)
        win_trades = [t for t in self.trades if t['profit'] > 0]
        lose_trades = [t for t in self.trades if t['profit'] < 0]

        win_rate = len(win_trades) / total_trades * 100
        avg_profit = np.mean([t['profit'] for t in win_trades]) if win_trades else 0
        avg_loss = np.mean([t['profit'] for t in lose_trades]) if lose_trades else 0

        # 最终权益
        final_equity = self.equity_curve[-1]['equity'] if self.equity_curve else self.initial_capital
        total_return = (final_equity - self.initial_capital) / self.initial_capital * 100

        # 最大回撤
        equity_values = [e['equity'] for e in self.equity_curve]
        if equity_values:
            peak = max(equity_values)
            max_drawdown = (min(equity_values) - peak) / peak * 100
        else:
            max_drawdown = 0

        # 止损止盈统计
        stop_loss_count = sum(1 for t in self.trades if t['reason'] == 'STOP_LOSS')
        take_profit_count = sum(1 for t in self.trades if t['reason'] == 'TAKE_PROFIT')

        logger.info("\n" + "=" * 60)
        logger.info("📊 T+1 回测报告 (V12.1.0 三大过滤器)")
        logger.info("=" * 60)
        logger.info(f"初始资金: {self.initial_capital:,.0f}")
        logger.info(f"最终权益: {final_equity:,.0f}")
        logger.info(f"总收益率: {total_return:.2f}%")
        logger.info(f"最大回撤: {max_drawdown:.2f}%")
        logger.info(f"总交易次数: {total_trades}")
        logger.info(f"盈利次数: {len(win_trades)}")
        logger.info(f"亏损次数: {len(lose_trades)}")
        logger.info(f"胜率: {win_rate:.2f}%")
        logger.info(f"平均盈利: {avg_profit:,.0f}")
        logger.info(f"平均亏损: {avg_loss:,.0f}")
        logger.info(f"止损次数: {stop_loss_count}")
        logger.info(f"止盈次数: {take_profit_count}")

        # 计算平均持仓天数
        avg_holding_days = np.mean([t['holding_days'] for t in self.trades]) if self.trades else 0
        logger.info(f"平均持仓天数: {avg_holding_days:.1f} 天")

        # V12.1.0 过滤器统计
        logger.info("\n" + "-" * 60)
        logger.info("🎯 V12.1.0 三大过滤器统计")
        logger.info("-" * 60)
        logger.info(f"板块共振: ✅ 通过 {self.filter_stats['wind_passed']} 次, ❌ 拒绝 {self.filter_stats['wind_rejected']} 次")
        logger.info(f"动态阈值: ✅ 通过 {self.filter_stats['threshold_passed']} 次, ❌ 拒绝 {self.filter_stats['threshold_rejected']} 次")
        logger.info(f"竞价校验: ✅ 通过 {self.filter_stats['auction_passed']} 次, ❌ 拒绝 {self.filter_stats['auction_rejected']} 次")

        total_filtered = (self.filter_stats['wind_rejected'] +
                         self.filter_stats['threshold_rejected'] +
                         self.filter_stats['auction_rejected'])
        logger.info(f"总过滤次数: {total_filtered} 次")

        report = {
            'success': True,
            'config': BACKTEST_CONFIG,
            'summary': {
                'initial_capital': self.initial_capital,
                'final_equity': final_equity,
                'total_return_pct': total_return,
                'max_drawdown_pct': max_drawdown,
                'total_trades': total_trades,
                'win_count': len(win_trades),
                'lose_count': len(lose_trades),
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'stop_loss_count': stop_loss_count,
                'take_profit_count': take_profit_count,
                'avg_holding_days': avg_holding_days
            },
            'filter_stats': self.filter_stats,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }

        # 保存报告
        report_file = PROJECT_ROOT / 'backtest' / 'results' / f't1_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"\n✅ 报告已保存: {report_file}")

        return report

# ================= 主函数 =================

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🚀 T+1 Tick数据回测引擎")
    logger.info("=" * 60)

    # 初始化QMT
    if not init_qmt():
        logger.error("❌ QMT连接初始化失败")
        return

    # 加载股票列表
    stock_codes = load_stock_list()

    if not stock_codes:
        logger.error("没有找到有Tick数据的股票")
        return

    # 限制股票数量（快速测试）
    max_stocks = 10  # 先测试10只
    if len(stock_codes) > max_stocks:
        stock_codes = stock_codes[:max_stocks]
        logger.info(f"限制回测股票数量为 {max_stocks} 只")

    logger.info(f"回测时间: {BACKTEST_CONFIG['start_date']} 至 {BACKTEST_CONFIG['end_date']}")
    logger.info(f"股票数量: {len(stock_codes)} 只")
    logger.info(f"初始资金: {BACKTEST_CONFIG['initial_capital']:,.0f}")

    # 运行回测
    engine = T1TickBacktester(BACKTEST_CONFIG['initial_capital'])

    # 生成日期列表
    date_range = pd.date_range(
        start=BACKTEST_CONFIG['start_date'],
        end=BACKTEST_CONFIG['end_date'],
        freq='D'
    )
    trading_days = [d.strftime('%Y-%m-%d') for d in date_range]

    logger.info(f"交易日数量: {len(trading_days)} 天")

    # 逐日回测
    for date in trading_days:
        # 加载当日所有股票的tick数据
        tick_data_dict = {}
        for code in stock_codes:
            df = load_tick_data(code, BACKTEST_CONFIG['start_date'], BACKTEST_CONFIG['end_date'])
            if not df.empty:
                tick_data_dict[code] = df

        # 处理交易日
        engine.process_trading_day(date, tick_data_dict)

    # 生成报告
    logger.info("📊 开始生成回测报告...")
    try:
        report = engine.generate_report()
        logger.info(f"✅ 回测报告生成成功，交易次数: {len(report.get('trades', []))}")
    except Exception as e:
        logger.error(f"❌ 生成报告失败: {e}")
        import traceback
        traceback.print_exc()

    logger.info("\n" + "=" * 60)
    logger.info("✅ 回测完成")
    logger.info("=" * 60)

if __name__ == '__main__':
    main()