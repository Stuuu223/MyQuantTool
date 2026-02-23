"""
Tick数据回测脚本 - 使用QMT真实tick数据

⚠️  V17生产约束声明 / 研究用途标记
==============================================================================
【重要】本脚本使用独立TickBacktestEngine，不是V17官方回测流水线

根据 SIGNAL_AND_PORTFOLIO_CONTRACT.md V17生产约束：
- V17上线前唯一认可的回测命令：run_tick_replay_backtest.py（使用统一BacktestEngine）
- 本脚本（run_tick_backtest.py）禁止作为V17上线决策依据
- 本脚本仅用于：Tick策略快速验证、参数调试、技术研究

V18任务：将TickBacktestEngine统一迁移到BacktestEngine框架（Issue待创建）
==============================================================================
"""

import sys
import json
import struct
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
    'start_date': '2026-01-15',  # Tick数据起始日期
    'end_date': '2026-02-13',    # Tick数据结束日期
    'initial_capital': 100000,
    'commission_rate': 0.0003,  # 万三手续费
}

# ================= 全局变量 =================

# QMT连接状态（全局，避免重复初始化）
_qmt_initialized = False

def init_qmt():
    """初始化QMT连接（只执行一次）"""
    global _qmt_initialized
    if _qmt_initialized:
        return True

    try:
        from xtquant import xtdatacenter as xtdc
        from xtquant import xtdata

        # 设置VIP Token
        VIP_TOKEN = '6b1446e317ed67596f13d2e808291a01e0dd9839'
        # 🔥 关键修复：数据目录必须为QMT客户端目录（不得下载到项目内）
        DATA_DIR = Path('E:/qmt/userdata_mini/datadir')
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        xtdc.set_data_home_dir(str(DATA_DIR))
        xtdc.set_token(VIP_TOKEN)

        # 初始化
        xtdc.init()

        # 监听端口
        listen_port = xtdc.listen(port=(58700, 58720))
        logger.info(f"QMT服务监听端口: {listen_port}")

        # 连接到服务
        _, port = listen_port
        xtdata.connect(ip='127.0.0.1', port=port, remember_if_success=False)

        # 验证数据目录
        logger.info(f"QMT数据目录: {DATA_DIR}")
        test_data = xtdata.get_market_data(['close'], ['300017.SZ'], period='1d', count=1)
        if test_data is not None:
            if isinstance(test_data, dict):
                logger.info("✅ QMT数据目录验证成功（dict格式）")
            elif hasattr(test_data, 'empty') and not test_data.empty:
                logger.info("✅ QMT数据目录验证成功（DataFrame格式）")
            else:
                logger.warning("⚠️ QMT数据目录验证失败：返回数据为空")
        else:
            logger.warning("⚠️ QMT数据目录验证失败：返回None")

        _qmt_initialized = True
        logger.info("✅ QMT连接初始化成功")
        return True

    except Exception as e:
        logger.warning(f"初始化QMT连接失败: {e}")
        import traceback
        logger.warning(traceback.format_exc())
        return False

# ================= Tick数据读取 =================

def load_tick_data(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    使用QMT API加载指定股票的Tick数据

    Args:
        stock_code: 股票代码，如'600519.SH'
        start_date: 开始日期，如'2026-01-15'
        end_date: 结束日期，如'2026-02-13'

    Returns:
        DataFrame with columns: timestamp, price, volume, amount
    """
    try:
        from xtquant import xtdata

        # 转换日期格式
        start_time = start_date.replace('-', '') + '093000'
        end_time = end_date.replace('-', '') + '150000'

        # 获取tick数据
        tick_df = xtdata.get_market_data_ex(
            field_list=['time', 'lastPrice', 'open', 'high', 'low', 'volume', 'amount'],
            stock_list=[stock_code],
            period='tick',
            start_time=start_time,
            end_time=end_time
        )

        if stock_code in tick_df and not tick_df[stock_code].empty:
            df = tick_df[stock_code].copy()

            # 🔥 关键修复：索引就是时间戳！
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
        import traceback
        logger.warning(traceback.format_exc())
        return pd.DataFrame()

def load_stock_list_with_tick_data() -> List[str]:
    """加载有Tick数据的股票列表"""
    tick_stocks = set()

    for market in ['SH', 'SZ']:
        tick_dir = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir' / market / '0'
        if tick_dir.exists():
            for stock_dir in tick_dir.iterdir():
                if stock_dir.is_dir():
                    # 检查是否有数据文件
                    if any(stock_dir.iterdir()):
                        tick_stocks.add(f'{stock_dir.name}.{market}')

    logger.info(f"找到 {len(tick_stocks)} 只有Tick数据的股票")
    return list(tick_stocks)

# ================= 简单策略 =================

def simple_tick_strategy(tick_df: pd.DataFrame) -> Dict:
    """
    简单的Tick策略：
    - 在09:35:00时买入
    - 在14:55:00时卖出
    - 止损：-5%
    - 止盈：+10%
    """
    if tick_df.empty:
        return {}

    # 筛选有效价格数据（价格必须大于0）
    tick_df = tick_df[tick_df['price'] > 0].copy()

    if tick_df.empty:
        return {}

    # 计算当日第一笔成交价作为开盘价
    first_tick = tick_df.iloc[0]
    open_price = first_tick['price']

    # 买入信号：09:35:00时买入
    buy_time = pd.to_datetime(f"{tick_df.iloc[0]['timestamp'].date()} 09:35:00")
    buy_tick = tick_df[tick_df['timestamp'] <= buy_time].iloc[-1] if not tick_df[tick_df['timestamp'] <= buy_time].empty else None

    if buy_tick is None or buy_tick['price'] <= 0:
        return {}

    buy_price = buy_tick['price']

    # 卖出信号：14:55:00时卖出
    sell_time = pd.to_datetime(f"{tick_df.iloc[0]['timestamp'].date()} 14:55:00")
    sell_tick = tick_df[tick_df['timestamp'] >= sell_time].iloc[0] if not tick_df[tick_df['timestamp'] >= sell_time].empty else None

    if sell_tick is None or sell_tick['price'] <= 0:
        # 如果没有14:55:00的数据，使用最后一笔成交
        sell_tick = tick_df.iloc[-1]

    sell_price = sell_tick['price']

    if sell_price <= 0:
        return {}

    # 计算收益率
    profit_pct = (sell_price - buy_price) / buy_price * 100

    # 止损检查
    # 在买入后检查是否跌破止损线
    after_buy_ticks = tick_df[tick_df['timestamp'] > buy_tick['timestamp']]
    min_price = after_buy_ticks['price'].min() if not after_buy_ticks.empty else buy_price

    stop_loss_price = buy_price * 0.95  # -5%止损
    take_profit_price = buy_price * 1.10  # +10%止盈

    # 检查是否触发止损
    if min_price <= stop_loss_price:
        # 找到触发止损的时间点
        stop_loss_ticks = after_buy_ticks[after_buy_ticks['price'] <= stop_loss_price]
        if not stop_loss_ticks.empty:
            stop_loss_tick = stop_loss_ticks.iloc[0]
            sell_price = stop_loss_tick['price']
            sell_time = stop_loss_tick['timestamp']
            profit_pct = (sell_price - buy_price) / buy_price * 100
            reason = 'STOP_LOSS'
        else:
            reason = 'NORMAL'
    # 检查是否触发止盈
    elif sell_price >= take_profit_price:
        reason = 'TAKE_PROFIT'
    else:
        reason = 'NORMAL'

    return {
        'buy_time': buy_tick['timestamp'],
        'buy_price': buy_price,
        'sell_time': sell_tick['timestamp'],
        'sell_price': sell_price,
        'profit_pct': profit_pct,
        'reason': reason,
        'open_price': open_price,
        'close_price': sell_price
    }

# ================= 回测引擎 =================

class TickBacktestEngine:
    """Tick数据回测引擎"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades = []
        self.daily_results = []

    def run_backtest(self, stock_codes: List[str], start_date: str, end_date: str):
        """运行Tick回测"""
        logger.info("=" * 80)
        logger.info("🚀 开始Tick数据回测")
        logger.info("=" * 80)
        logger.info(f"回测时间: {start_date} 至 {end_date}")
        logger.info(f"股票数量: {len(stock_codes)} 只")
        logger.info(f"初始资金: {self.initial_capital:,.0f}")
        logger.info("")

        # 生成日期列表
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        trading_days = [d.strftime('%Y-%m-%d') for d in date_range]

        logger.info(f"交易日数量: {len(trading_days)} 天")

        # 逐日回测
        for date in trading_days:
            logger.info(f"\n{'='*80}")
            logger.info(f"📅 回测日期: {date}")
            logger.info(f"{'='*80}")

            daily_trades = []

            for stock_code in stock_codes:
                # 加载Tick数据
                tick_df = load_tick_data(stock_code, start_date, end_date)

                if tick_df.empty:
                    continue

                # 筛选当日的数据
                daily_tick_df = tick_df[tick_df['date'] == date]

                if daily_tick_df.empty:
                    continue

                # 运行策略
                result = simple_tick_strategy(daily_tick_df)

                if result:
                    trade = {
                        'date': date,
                        'code': stock_code,
                        **result
                    }
                    self.trades.append(trade)
                    daily_trades.append(trade)

                    logger.info(f"  {stock_code}: 买入价={result['buy_price']:.2f}, "
                               f"卖出价={result['sell_price']:.2f}, "
                               f"收益率={result['profit_pct']:.2f}%, "
                               f"原因={result['reason']}")

            # 统计当日结果
            if daily_trades:
                daily_profit = sum(t['profit_pct'] for t in daily_trades)
                daily_win = sum(1 for t in daily_trades if t['profit_pct'] > 0)
                daily_lose = sum(1 for t in daily_trades if t['profit_pct'] < 0)

                self.daily_results.append({
                    'date': date,
                    'trades': len(daily_trades),
                    'total_profit': daily_profit,
                    'win_count': daily_win,
                    'lose_count': daily_lose,
                    'win_rate': daily_win / len(daily_trades) * 100 if daily_trades else 0
                })

                logger.info(f"  当日统计: 交易{len(daily_trades)}次, "
                           f"盈利{daily_win}次, 亏损{daily_lose}次, "
                           f"胜率{daily_win/len(daily_trades)*100:.1f}%")

    def generate_report(self):
        """生成回测报告"""
        if not self.trades:
            logger.warning("没有交易记录")
            return

        logger.info("\n" + "=" * 80)
        logger.info("📊 回测结果汇总")
        logger.info("=" * 80)

        # 基本统计
        total_trades = len(self.trades)
        win_trades = [t for t in self.trades if t['profit_pct'] > 0]
        lose_trades = [t for t in self.trades if t['profit_pct'] < 0]

        win_rate = len(win_trades) / total_trades * 100 if total_trades > 0 else 0

        avg_profit = np.mean([t['profit_pct'] for t in win_trades]) if win_trades else 0
        avg_loss = np.mean([t['profit_pct'] for t in lose_trades]) if lose_trades else 0

        total_profit_pct = sum(t['profit_pct'] for t in self.trades)

        # 止损统计
        stop_loss_trades = [t for t in self.trades if t['reason'] == 'STOP_LOSS']
        stop_loss_rate = len(stop_loss_trades) / total_trades * 100 if total_trades > 0 else 0

        # 止盈统计
        take_profit_trades = [t for t in self.trades if t['reason'] == 'TAKE_PROFIT']
        take_profit_rate = len(take_profit_trades) / total_trades * 100 if total_trades > 0 else 0

        logger.info(f"总交易次数: {total_trades}")
        logger.info(f"盈利次数: {len(win_trades)}")
        logger.info(f"亏损次数: {len(lose_trades)}")
        logger.info(f"胜率: {win_rate:.2f}%")
        logger.info(f"平均盈利: {avg_profit:.2f}%")
        logger.info(f"平均亏损: {avg_loss:.2f}%")
        logger.info(f"总收益率: {total_profit_pct:.2f}%")
        logger.info(f"止损率: {stop_loss_rate:.2f}%")
        logger.info(f"止盈率: {take_profit_rate:.2f}%")

        # 保存结果
        report = {
            'config': BACKTEST_CONFIG,
            'summary': {
                'total_trades': total_trades,
                'win_count': len(win_trades),
                'lose_count': len(lose_trades),
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'total_profit_pct': total_profit_pct,
                'stop_loss_rate': stop_loss_rate,
                'take_profit_rate': take_profit_rate
            },
            'trades': self.trades,
            'daily_results': self.daily_results
        }

        report_file = PROJECT_ROOT / 'backtest' / 'results' / f'tick_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"\n详细报告已保存: {report_file}")

# ================= 主函数 =================

def main():
    """主函数"""
    # 初始化QMT连接
    if not init_qmt():
        logger.error("❌ QMT连接初始化失败，无法继续")
        return
    
    # 加载有Tick数据的股票列表
    stock_codes = load_stock_list_with_tick_data()

    if not stock_codes:
        logger.error("没有找到有Tick数据的股票")
        return

    # 限制股票数量（避免回测时间过长）
    max_stocks = 50
    if len(stock_codes) > max_stocks:
        stock_codes = stock_codes[:max_stocks]
        logger.info(f"限制回测股票数量为 {max_stocks} 只")

    # 运行回测
    engine = TickBacktestEngine(BACKTEST_CONFIG['initial_capital'])
    engine.run_backtest(
        stock_codes=stock_codes,
        start_date=BACKTEST_CONFIG['start_date'],
        end_date=BACKTEST_CONFIG['end_date']
    )

    # 生成报告
    engine.generate_report()

if __name__ == '__main__':
    main()