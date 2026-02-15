"""
Tick数据快速回测脚本（只测试3只股票）
"""
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
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
    'start_date': '2026-02-13',  # 只测试一天
    'end_date': '2026-02-13',
    'initial_capital': 100000,
}

# ================= 全局变量 =================
_qmt_initialized = False

def init_qmt():
    """初始化QMT连接"""
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
    """加载Tick数据"""
    try:
        from xtquant import xtdata

        start_time = start_date.replace('-', '') + '093000'
        end_time = end_date.replace('-', '') + '150000'

        tick_df = xtdata.get_market_data_ex(
            field_list=['time', 'lastPrice', 'open', 'high', 'low', 'volume', 'amount'],
            stock_list=[stock_code],
            period='tick',
            start_time=start_time,
            end_time=end_time
        )

        if stock_code in tick_df and not tick_df[stock_code].empty:
            df = tick_df[stock_code].copy()
            df = df.rename(columns={'time': 'timestamp', 'lastPrice': 'price'})
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df[df['price'].notna() & (df['price'] > 0)].copy()
            df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d')
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"  {stock_code}: 加载成功 {len(df)} 条tick记录")
            return df

        return pd.DataFrame()

    except Exception as e:
        logger.warning(f"加载 {stock_code} Tick数据失败: {e}")
        return pd.DataFrame()

def simple_tick_strategy(tick_df: pd.DataFrame) -> Dict:
    """简单Tick策略：09:35买入，14:55卖出"""
    if tick_df.empty:
        return {}

    buy_time = pd.to_datetime(f"{tick_df.iloc[0]['timestamp'].date()} 09:35:00")
    buy_tick = tick_df[tick_df['timestamp'] <= buy_time].iloc[-1] if not tick_df[tick_df['timestamp'] <= buy_time].empty else None

    if buy_tick is None or buy_tick['price'] <= 0:
        return {}

    buy_price = buy_tick['price']

    sell_time = pd.to_datetime(f"{tick_df.iloc[0]['timestamp'].date()} 14:55:00")
    sell_tick = tick_df[tick_df['timestamp'] >= sell_time].iloc[0] if not tick_df[tick_df['timestamp'] >= sell_time].empty else None

    if sell_tick is None or sell_tick['price'] <= 0:
        sell_tick = tick_df.iloc[-1]

    sell_price = sell_tick['price']

    if sell_price <= 0:
        return {}

    profit_pct = (sell_price - buy_price) / buy_price * 100

    return {
        'buy_time': str(buy_tick['timestamp']),
        'buy_price': float(buy_price),
        'sell_time': str(sell_tick['timestamp']),
        'sell_price': float(sell_price),
        'profit_pct': float(profit_pct)
    }

# ================= 主函数 =================
def main():
    logger.info("=" * 60)
    logger.info("🚀 Tick数据快速回测")
    logger.info("=" * 60)

    if not init_qmt():
        logger.error("❌ QMT连接初始化失败")
        return

    # 只测试3只股票
    test_stocks = ['600007.SH', '000001.SZ', '300182.SZ']
    start_date = BACKTEST_CONFIG['start_date']
    end_date = BACKTEST_CONFIG['end_date']

    logger.info(f"测试股票: {test_stocks}")
    logger.info(f"测试日期: {start_date}")
    logger.info("")

    trades = []
    
    for stock_code in test_stocks:
        logger.info(f"正在处理 {stock_code}...")
        
        # 加载所有数据
        all_df = load_tick_data(stock_code, start_date, end_date)
        
        if all_df.empty:
            logger.warning(f"  ❌ 无数据")
            continue

        # 筛选当日数据
        daily_df = all_df[all_df['date'] == start_date]
        
        if daily_df.empty:
            logger.warning(f"  ❌ 当日无数据")
            continue

        # 运行策略
        result = simple_tick_strategy(daily_df)

        if result:
            trade = {
                'code': stock_code,
                'date': start_date,
                **result
            }
            trades.append(trade)
            
            logger.info(f"  ✅ 买入价={result['buy_price']:.2f}, "
                       f"卖出价={result['sell_price']:.2f}, "
                       f"收益率={result['profit_pct']:.2f}%")
        else:
            logger.warning(f"  ⚠️ 策略未触发")

    # 汇总结果
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 回测结果汇总")
    logger.info("=" * 60)

    if trades:
        logger.info(f"总交易次数: {len(trades)}")
        
        win_trades = [t for t in trades if t['profit_pct'] > 0]
        lose_trades = [t for t in trades if t['profit_pct'] < 0]
        
        win_rate = len(win_trades) / len(trades) * 100
        avg_profit = np.mean([t['profit_pct'] for t in win_trades]) if win_trades else 0
        avg_loss = np.mean([t['profit_pct'] for t in lose_trades]) if lose_trades else 0
        
        logger.info(f"盈利次数: {len(win_trades)}")
        logger.info(f"亏损次数: {len(lose_trades)}")
        logger.info(f"胜率: {win_rate:.2f}%")
        logger.info(f"平均盈利: {avg_profit:.2f}%")
        logger.info(f"平均亏损: {avg_loss:.2f}%")

        # 保存结果
        result_file = PROJECT_ROOT / 'backtest' / 'results' / f'tick_backtest_quick_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        result_file.parent.mkdir(parents=True, exist_ok=True)

        report = {
            'config': BACKTEST_CONFIG,
            'trades': trades,
            'summary': {
                'total_trades': len(trades),
                'win_count': len(win_trades),
                'lose_count': len(lose_trades),
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss
            }
        }

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 结果已保存: {result_file}")
    else:
        logger.warning("⚠️ 没有触发任何交易")

if __name__ == '__main__':
    main()