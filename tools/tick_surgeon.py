"""
涨停前暗流分析器 - Tick外科解剖
目标：找到涨停前N分钟的量能/大单/价速特征
用法：python tools/tick_surgeon.py 20260303 [oil|batch]
"""
import sys
import ast
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
from xtquant import xtdata

# ── 常量 ────────────────────────────────────────────────────────
CST = timezone(timedelta(hours=8))
BIG_ORDER_THRESHOLD = 100_000   # 大单定义：单笔成交额 >= 10万元
WINDOWS = [5, 10, 15, 20, 30, 60]  # 涨停前回溯窗口（分钟）
# 独立切片定义：[(start_min, end_min), ...]
SLICES = [
    (120, 90),   # 远景背景
    (90,  60),   # 洗盘确认
    (60,  30),   # 洗盘执行
    (30,  15),   # 方向切换
    (15,   5),   # 起爆加速
    (5,    0),   # 封板冲刺
]
OIL_STOCKS = ['600028.SH', '601857.SH', '000096.SZ',
              '600339.SH', '601808.SH', '000554.SZ']

def ts_to_dt(ts_ms: int) -> datetime:
    """毫秒时间戳 → CST datetime"""
    return datetime.fromtimestamp(ts_ms / 1000, tz=CST)

def safe_get_first(x):
    """安全提取askPrice/bidPrice第一档（处理字符串形式的列表）"""
    if isinstance(x, (list, np.ndarray)):
        return x[0] if len(x) > 0 else 0
    if isinstance(x, str):
        try:
            lst = ast.literal_eval(x)
            return lst[0] if lst else 0
        except:
            return 0
    return 0

def load_tick(stock: str, date: str) -> pd.DataFrame:
    """读取本地Tick，返回整理好的DataFrame"""
    raw = xtdata.get_local_data(
        [], [stock], 'tick',
        start_time=date, end_time=date,
        count=-1
    )
    if stock not in raw or raw[stock] is None:
        return pd.DataFrame()

    arr = raw[stock]
    if len(arr) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(arr)
    df['dt'] = df['time'].apply(ts_to_dt)
    df['minute'] = df['dt'].dt.floor('1min')

    # 增量成交量/额（Tick存的是累计值，差分得单笔）
    df['vol_delta']    = df['volume'].diff().fillna(df['volume'].iloc[0])
    df['amount_delta'] = df['amount'].diff().fillna(df['amount'].iloc[0])

    # 单笔均价（粗估，用于区分大单）
    df['tick_price'] = df['amount_delta'] / (df['vol_delta'] * 100 + 1e-9)

    # 主动方向判断：lastPrice vs askPrice[0]
    # askPrice / bidPrice 可能是列表或字符串形式的列表
    df['ask1'] = df['askPrice'].apply(safe_get_first)
    df['bid1'] = df['bidPrice'].apply(safe_get_first)
    
    # 价格变化方向（用于降级判断）
    df['price_delta'] = df['lastPrice'].diff()
    
    # 主动买入判断：
    # 有盘口数据时：用盘口判断（精准）
    # 无盘口数据时：用价格上涨方向判断（降级）
    df['is_active_buy'] = (
        ((df['lastPrice'] >= df['ask1']) & (df['ask1'] > 0)) |
        ((df['ask1'] == 0) & (df['price_delta'] > 0))
    )
    df['is_active_sell'] = (
        ((df['lastPrice'] <= df['bid1']) & (df['bid1'] > 0)) |
        ((df['bid1'] == 0) & (df['price_delta'] < 0))
    )
    # price_delta == 0 的Tick：方向不明，不参与大单统计

    # 大单标记（单笔成交额 >= 10万）
    df['is_big'] = df['amount_delta'] >= BIG_ORDER_THRESHOLD

    return df

def find_limit_up_time(df: pd.DataFrame, prev_close: float) -> datetime:
    """找到首次触及涨停价的时间"""
    limit_price = round(prev_close * 1.10, 2)  # 普通股10%
    hits = df[df['lastPrice'] >= limit_price - 0.01]
    if hits.empty:
        return None
    return hits.iloc[0]['dt']

def analyze_prelude(df: pd.DataFrame, limit_time: datetime) -> dict:
    """分析涨停前各时间窗口的特征"""
    result = {}

    # 全天数据
    total_vol    = df['vol_delta'].sum()
    total_amount = df['amount_delta'].sum()

    # ── 累计窗口（原有逻辑）────────────────────────────────
    for w in WINDOWS:
        win_start = limit_time - timedelta(minutes=w)
        win_df = df[(df['dt'] >= win_start) & (df['dt'] < limit_time)]

        if win_df.empty:
            result[f'vol_ratio_{w}m']        = 0
            result[f'big_net_buy_{w}m']      = 0
            result[f'big_buy_ratio_{w}m']    = 0
            result[f'price_accel_{w}m']      = 0
            continue

        w_vol    = win_df['vol_delta'].sum()
        w_amount = win_df['amount_delta'].sum()

        # 量能占比：该窗口成交量 / 全天总量
        result[f'vol_ratio_{w}m'] = round(w_vol / (total_vol + 1e-9) * 100, 1)

        # 大单净买入（元）：主动买大单 - 主动卖大单
        big_buy  = win_df[win_df['is_big'] & win_df['is_active_buy']]['amount_delta'].sum()
        big_sell = win_df[win_df['is_big'] & win_df['is_active_sell']]['amount_delta'].sum()
        result[f'big_net_buy_{w}m']   = round((big_buy - big_sell) / 10000, 1)  # 万元
        result[f'big_buy_ratio_{w}m'] = round(
            big_buy / (w_amount + 1e-9) * 100, 1
        )

        # 价格加速度：窗口内每分钟均价的线性斜率
        min_df = win_df.groupby('minute')['lastPrice'].last().reset_index()
        if len(min_df) >= 2:
            x = np.arange(len(min_df))
            slope = np.polyfit(x, min_df['lastPrice'].values, 1)[0]
            result[f'price_accel_{w}m'] = round(float(slope), 4)
        else:
            result[f'price_accel_{w}m'] = 0

    # ── 独立切片分析（新增）────────────────────────────────
    for start, end in SLICES:
        slice_start = limit_time - timedelta(minutes=start)
        slice_end = limit_time - timedelta(minutes=end)
        slice_df = df[(df['dt'] >= slice_start) & (df['dt'] < slice_end)]

        if slice_df.empty:
            result[f'slice_{start}_{end}m_vol'] = 0
            result[f'slice_{start}_{end}m_big_net'] = 0
            continue

        s_vol = slice_df['vol_delta'].sum()
        s_amount = slice_df['amount_delta'].sum()

        # 量能占比
        result[f'slice_{start}_{end}m_vol'] = round(s_vol / (total_vol + 1e-9) * 100, 1)

        # 大单净买入
        big_buy  = slice_df[slice_df['is_big'] & slice_df['is_active_buy']]['amount_delta'].sum()
        big_sell = slice_df[slice_df['is_big'] & slice_df['is_active_sell']]['amount_delta'].sum()
        result[f'slice_{start}_{end}m_big_net'] = round((big_buy - big_sell) / 10000, 1)  # 万元

    return result

def single_stock_report(stock: str, date: str) -> dict:
    """单股完整解剖"""
    df = load_tick(stock, date)
    if df.empty:
        print(f"  {stock}: 无Tick数据")
        return None

    prev_close = df['lastClose'].iloc[0]
    if prev_close <= 0:
        print(f"  {stock}: 前收盘价异常")
        return None

    final_chg = (df['lastPrice'].iloc[-1] - prev_close) / prev_close * 100
    limit_time = find_limit_up_time(df, prev_close)

    if limit_time is None:
        return {
            'stock': stock,
            'change_pct': round(final_chg, 2),
            'limit_up': False,
            'limit_time': None,
        }

    prelude = analyze_prelude(df, limit_time)
    return {
        'stock':       stock,
        'change_pct':  round(final_chg, 2),
        'limit_up':    True,
        'limit_time':  limit_time.strftime('%H:%M:%S'),
        'prev_close':  prev_close,
        **prelude,
    }

def print_single_report(r: dict):
    """格式化打印单股报告"""
    print(f"\n{'='*60}")
    print(f"  {r['stock']}  涨跌: {r['change_pct']:+.2f}%  "
          f"涨停时间: {r.get('limit_time', 'N/A')}")
    print(f"{'='*60}")
    if not r.get('limit_up'):
        print("  未涨停，跳过")
        return

    print(f"  {'窗口':>6} | {'量能占比%':>8} | {'大单净买(万)':>10} "
          f"| {'大单买占比%':>9} | {'价格斜率':>8}")
    print(f"  {'-'*58}")
    for w in WINDOWS:
        print(
            f"  {w:>4}m前 | "
            f"{r.get(f'vol_ratio_{w}m', 0):>8.1f} | "
            f"{r.get(f'big_net_buy_{w}m', 0):>10.1f} | "
            f"{r.get(f'big_buy_ratio_{w}m', 0):>9.1f} | "
            f"{r.get(f'price_accel_{w}m', 0):>8.4f}"
        )

def batch_analysis(date: str, limit_up_stocks: list) -> pd.DataFrame:
    """批量分析涨停股，统计各窗口分布"""
    rows = []
    for i, stock in enumerate(limit_up_stocks):
        print(f"  [{i+1}/{len(limit_up_stocks)}] {stock}...", end=' ', flush=True)
        r = single_stock_report(stock, date)
        if r and r.get('limit_up'):
            rows.append(r)
            print(f"涨停@{r['limit_time']}")
        else:
            print("跳过")

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    print(f"\n{'='*60}")
    print(f"批量统计：{len(df)} 只涨停股，各窗口中位数")
    print(f"{'='*60}")
    print(f"  {'窗口':>6} | {'量能占比%':>8} | {'大单净买(万)':>10} | {'大单买占比%':>9}")
    print(f"  {'-'*46}")
    for w in WINDOWS:
        vr = df[f'vol_ratio_{w}m'].median()
        nb = df[f'big_net_buy_{w}m'].median()
        br = df[f'big_buy_ratio_{w}m'].median()
        print(f"  {w:>4}m前 | {vr:>8.1f} | {nb:>10.1f} | {br:>9.1f}")

    return df

def main():
    date = sys.argv[1] if len(sys.argv) > 1 else '20260303'
    mode = sys.argv[2] if len(sys.argv) > 2 else 'oil'  # oil | batch

    xtdata.connect(port=58610)
    print(f"\nTick外科解剖 | 日期: {date} | 模式: {mode}")

    if mode == 'oil':
        # 先解剖石油板块6只
        print(f"\n【石油板块解剖】")
        for stock in OIL_STOCKS:
            r = single_stock_report(stock, date)
            if r:
                print_single_report(r)

    elif mode == 'batch':
        # 从atr_probe结果读涨停股列表
        probe_file = Path(f'data/atr_probe_{date}.csv')
        if not probe_file.exists():
            print(f"找不到 {probe_file}，请先运行 atr_probe_{date}")
            return

        probe_df = pd.read_csv(probe_file)
        limit_up = probe_df[probe_df['change_pct'] >= 9.8]['stock'].tolist()
        print(f"\n【批量分析】涨停股: {len(limit_up)} 只")

        result_df = batch_analysis(date, limit_up)

        if not result_df.empty:
            out = Path(f'data/tick_prelude_{date}.csv')
            result_df.to_csv(out, index=False, encoding='utf-8-sig')
            print(f"\n结果已保存: {out}")

if __name__ == '__main__':
    main()
