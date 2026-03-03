"""
涨停前暗流分析器 - Tick外科解剖 v2
改进：
  1. 大单门槛动态化：基于当日个股成交分布75分位，而非固定10万
  2. 微观动能三分量：价格速度 / 加速度 / 持续性，合成 momentum_score
  3. 独立切片 6层，每层输出：量能占比 / 大单净买 / 微观动能得分
用法：python tools/tick_surgeon.py 20260303 [oil|batch|control]
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

# 大单门槛：动态（见 load_tick），此处为无法计算时的兜底值
FALLBACK_BIG_THRESHOLD = 100_000

WINDOWS = [5, 10, 15, 20, 30, 60]  # 累计窗口（保留，用于对比历史）

# 独立切片：时间语义明确
SLICES = [
    (120, 90),   # 远景背景
    (90,  60),   # 洗盘确认
    (60,  30),   # 洗盘执行  ← 关键：净卖出 = 洗盘信号
    (30,  15),   # 方向切换  ← 关键：净买入翻正 = 预警信号
    (15,   5),   # 起爆加速
    (5,    0),   # 封板冲刺  ← 关键：净卖出 = 假突破信号
]

# 微观动能权重
W_SPEED  = 0.3
W_ACCEL  = 0.3
W_CONT   = 0.4   # 持续性权重最高，最难伪造

OIL_STOCKS = ['600028.SH', '601857.SH', '000096.SZ',
              '600339.SH', '601808.SH', '000554.SZ']


def ts_to_dt(ts_ms: int) -> datetime:
    return datetime.fromtimestamp(ts_ms / 1000, tz=CST)


def safe_get_first(x):
    """安全提取 askPrice/bidPrice 第一档（兼容 list / ndarray / str）"""
    if isinstance(x, (list, np.ndarray)):
        return x[0] if len(x) > 0 else 0
    if isinstance(x, str):
        try:
            lst = ast.literal_eval(x)
            return lst[0] if lst else 0
        except Exception:
            return 0
    return 0


def load_tick(stock: str, date: str) -> pd.DataFrame:
    """
    读取本地Tick，返回完整特征DataFrame。
    新增：
      - big_threshold   : 当日动态大单门槛（元）
      - is_big          : 基于动态门槛的大单标记
      - price_speed     : 分钟级价格变化率（%/min，merge回Tick级）
      - price_accel     : 分钟级价格加速度
      - continuity      : 分钟级主动买入Tick占比（持续性）
    """
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
    df['dt']     = df['time'].apply(ts_to_dt)
    df['minute'] = df['dt'].dt.floor('1min')

    # ── 增量成交（Tick存累计值，差分得单笔）
    df['vol_delta']    = df['volume'].diff().fillna(df['volume'].iloc[0])
    df['amount_delta'] = df['amount'].diff().fillna(df['amount'].iloc[0])

    # 过滤负值（集合竞价可能产生负差分）
    df['vol_delta']    = df['vol_delta'].clip(lower=0)
    df['amount_delta'] = df['amount_delta'].clip(lower=0)

    # ── 大单门槛：动态75分位归一化 ────────────────────────────
    nonzero = df.loc[df['amount_delta'] > 0, 'amount_delta']
    big_threshold = (
        nonzero.quantile(0.75)
        if len(nonzero) > 10
        else FALLBACK_BIG_THRESHOLD
    )
    df['big_threshold'] = big_threshold
    df['is_big']        = df['amount_delta'] >= big_threshold

    # ── 主动方向判断 ──────────────────────────────────────────
    df['ask1']        = df['askPrice'].apply(safe_get_first)
    df['bid1']        = df['bidPrice'].apply(safe_get_first)
    df['price_delta'] = df['lastPrice'].diff()

    # 精准判断（有盘口）优先；降级判断（无盘口，用价格方向）兜底
    df['is_active_buy'] = (
        ((df['lastPrice'] >= df['ask1']) & (df['ask1'] > 0)) |
        ((df['ask1'] == 0) & (df['price_delta'] > 0))
    )
    df['is_active_sell'] = (
        ((df['lastPrice'] <= df['bid1']) & (df['bid1'] > 0)) |
        ((df['bid1'] == 0) & (df['price_delta'] < 0))
    )
    # price_delta == 0：方向不明，两列均为 False，不参与大单统计

    # ── 分钟级微观动能三分量 ──────────────────────────────────
    # 聚合到分钟
    min_agg = df.groupby('minute').agg(
        close=('lastPrice',    'last'),
        buy_ticks=('is_active_buy',  'sum'),
        total_ticks=('is_active_buy', 'count')
    ).reset_index()

    # 速度：每分钟价格变化率（%）
    min_agg['price_speed'] = min_agg['close'].pct_change() * 100

    # 加速度：速度的一阶差分
    min_agg['price_accel'] = min_agg['price_speed'].diff()

    # 持续性：该分钟主动买入Tick占总Tick的比例
    min_agg['continuity'] = (
        min_agg['buy_ticks'] / (min_agg['total_ticks'] + 1e-9)
    )

    # merge 回 Tick 级（每个Tick继承所在分钟的动能值）
    df = df.merge(
        min_agg[['minute', 'price_speed', 'price_accel', 'continuity']],
        on='minute', how='left'
    )

    return df


def find_limit_up_time(df: pd.DataFrame, prev_close: float) -> datetime | None:
    """找到首次触及涨停价的时间（10%涨停，ST/科创另算）"""
    limit_price = round(prev_close * 1.10, 2)
    hits = df[df['lastPrice'] >= limit_price - 0.01]
    return hits.iloc[0]['dt'] if not hits.empty else None


def _slice_metrics(slice_df: pd.DataFrame, total_vol: float) -> dict:
    """
    计算单个切片的三项指标：
      - vol_ratio    : 量能占比（%）
      - big_net      : 大单净买入（万元）
      - momentum     : 微观动能得分（速度×0.3 + 加速度×0.3 + 持续性×0.4）
    """
    if slice_df.empty:
        return {'vol_ratio': 0.0, 'big_net': 0.0, 'momentum': 0.0}

    s_vol = slice_df['vol_delta'].sum()
    vol_ratio = round(s_vol / (total_vol + 1e-9) * 100, 1)

    big_buy  = slice_df[slice_df['is_big'] & slice_df['is_active_buy']]['amount_delta'].sum()
    big_sell = slice_df[slice_df['is_big'] & slice_df['is_active_sell']]['amount_delta'].sum()
    big_net  = round((big_buy - big_sell) / 10000, 1)

    # 微观动能：取切片内各分钟值的均值（NaN过滤后）
    speed_mean = slice_df['price_speed'].dropna().mean()
    accel_mean = slice_df['price_accel'].dropna().mean()
    cont_mean  = slice_df['continuity'].dropna().mean()

    speed_mean = float(speed_mean) if not np.isnan(speed_mean) else 0.0
    accel_mean = float(accel_mean) if not np.isnan(accel_mean) else 0.0
    cont_mean  = float(cont_mean)  if not np.isnan(cont_mean)  else 0.0

    momentum = round(
        speed_mean * W_SPEED + accel_mean * W_ACCEL + cont_mean * W_CONT, 4
    )

    return {'vol_ratio': vol_ratio, 'big_net': big_net, 'momentum': momentum}


def analyze_prelude(df: pd.DataFrame, limit_time: datetime) -> dict:
    """分析涨停前各时间窗口的特征（累计窗口 + 独立切片）"""
    result = {}
    total_vol = df['vol_delta'].sum()

    # ── 累计窗口（兼容旧版输出）
    for w in WINDOWS:
        win_start = limit_time - timedelta(minutes=w)
        win_df = df[(df['dt'] >= win_start) & (df['dt'] < limit_time)]

        if win_df.empty:
            result[f'vol_ratio_{w}m']     = 0
            result[f'big_net_buy_{w}m']   = 0
            result[f'big_buy_ratio_{w}m'] = 0
            result[f'price_accel_{w}m']   = 0
            continue

        w_vol    = win_df['vol_delta'].sum()
        w_amount = win_df['amount_delta'].sum()
        result[f'vol_ratio_{w}m'] = round(w_vol / (total_vol + 1e-9) * 100, 1)

        big_buy  = win_df[win_df['is_big'] & win_df['is_active_buy']]['amount_delta'].sum()
        big_sell = win_df[win_df['is_big'] & win_df['is_active_sell']]['amount_delta'].sum()
        result[f'big_net_buy_{w}m']   = round((big_buy - big_sell) / 10000, 1)
        result[f'big_buy_ratio_{w}m'] = round(big_buy / (w_amount + 1e-9) * 100, 1)

        min_df = win_df.groupby('minute')['lastPrice'].last().reset_index()
        if len(min_df) >= 2:
            x = np.arange(len(min_df))
            slope = np.polyfit(x, min_df['lastPrice'].values, 1)[0]
            result[f'price_accel_{w}m'] = round(float(slope), 4)
        else:
            result[f'price_accel_{w}m'] = 0

    # ── 独立切片（核心：每层语义独立，不累计）
    for start, end in SLICES:
        slice_start = limit_time - timedelta(minutes=start)
        slice_end   = limit_time - timedelta(minutes=end)
        slice_df    = df[(df['dt'] >= slice_start) & (df['dt'] < slice_end)]

        m = _slice_metrics(slice_df, total_vol)
        key = f'slice_{start}_{end}m'
        result[f'{key}_vol']      = m['vol_ratio']
        result[f'{key}_big_net']  = m['big_net']
        result[f'{key}_momentum'] = m['momentum']

    # ── 模式分类（基于独立切片，互斥定义）──────────────────────
    # 注意：三种模式必须互斥，否则分类比例之和会超过100%
    net_60_30 = result.get('slice_60_30m_big_net', 0)
    net_30_15 = result.get('slice_30_15m_big_net', 0)
    net_15_5  = result.get('slice_15_5m_big_net', 0)
    net_5_0   = result.get('slice_5_0m_big_net', 0)

    # 假突破优先级最高（封板时出货是最强信号）
    if net_5_0 < -50:   # 封板前5min净卖出超50万
        result['pattern'] = 'fake_breakout'
    elif net_60_30 < -50 and net_30_15 > 50:
        result['pattern'] = 'wash_and_launch'   # 洗盘后起爆
    elif net_15_5 > 50:
        result['pattern'] = 'slow_rise'         # 慢起型
    else:
        result['pattern'] = 'fast_surge'        # 急拉型（无明显前兆）

    return result


def single_stock_report(stock: str, date: str) -> dict | None:
    df = load_tick(stock, date)
    if df.empty:
        print(f"  {stock}: 无Tick数据")
        return None

    prev_close = df['lastClose'].iloc[0]
    if prev_close <= 0:
        print(f"  {stock}: 前收盘价异常")
        return None

    final_chg  = (df['lastPrice'].iloc[-1] - prev_close) / prev_close * 100
    limit_time = find_limit_up_time(df, prev_close)

    if limit_time is None:
        return {
            'stock': stock,
            'change_pct': round(final_chg, 2),
            'limit_up': False,
            'limit_time': None,
            'big_threshold': round(df['big_threshold'].iloc[0] / 10000, 1),
        }

    prelude = analyze_prelude(df, limit_time)
    return {
        'stock':         stock,
        'change_pct':    round(final_chg, 2),
        'limit_up':      True,
        'limit_time':    limit_time.strftime('%H:%M:%S'),
        'prev_close':    prev_close,
        'big_threshold': round(df['big_threshold'].iloc[0] / 10000, 1),  # 万元
        **prelude,
    }


def print_single_report(r: dict):
    print(f"\n{'='*65}")
    print(f"  {r['stock']}  涨跌: {r['change_pct']:+.2f}%  "
          f"涨停: {r.get('limit_time','N/A')}  "
          f"大单门槛: {r.get('big_threshold',0):.1f}万")
    print(f"{'='*65}")
    if not r.get('limit_up'):
        print("  未涨停，跳过")
        return

    print(f"  模式: {r.get('pattern','?')}")
    print(f"\n  {'切片':>12} | {'量能%':>6} | {'大单净买(万)':>10} | {'微观动能':>8}")
    print(f"  {'-'*48}")
    labels = {
        'slice_120_90m': '远景背景',
        'slice_90_60m':  '洗盘确认',
        'slice_60_30m':  '洗盘执行',
        'slice_30_15m':  '方向切换',
        'slice_15_5m':   '起爆加速',
        'slice_5_0m':    '封板冲刺',
    }
    for key, label in labels.items():
        vol = r.get(f'{key}_vol', 0)
        net = r.get(f'{key}_big_net', 0)
        mom = r.get(f'{key}_momentum', 0)
        print(f"  {label:>6} | {vol:>6.1f} | {net:>10.1f} | {mom:>8.4f}")


def batch_analysis(date: str, limit_up_stocks: list[str]) -> pd.DataFrame:
    rows = []
    for i, stock in enumerate(limit_up_stocks):
        print(f"  [{i+1}/{len(limit_up_stocks)}] {stock}...", end=' ', flush=True)
        r = single_stock_report(stock, date)
        if r and r.get('limit_up'):
            rows.append(r)
            print(f"涨停@{r['limit_time']} 模式={r.get('pattern','?')}")
        else:
            print("跳过")

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # 模式分布（互斥，合计应≈100%）
    print(f"\n{'='*65}")
    print(f"样本: {len(df)} 只涨停股 | 模式分布（互斥）")
    print(f"{'='*65}")
    pattern_counts = df['pattern'].value_counts()
    for p, cnt in pattern_counts.items():
        print(f"  {p:20s}: {cnt:3d} = {cnt/len(df)*100:.1f}%")

    # 各切片中位数
    print(f"\n  {'切片':>12} | {'量能%':>6} | {'大单净买(万)':>10} | {'微观动能':>8}")
    print(f"  {'-'*48}")
    for start, end in SLICES:
        key = f'slice_{start}_{end}m'
        vol = df[f'{key}_vol'].median()
        net = df[f'{key}_big_net'].median()
        mom = df[f'{key}_momentum'].median()
        print(f"  {start}~{end}m前    | {vol:>6.1f} | {net:>10.1f} | {mom:>8.4f}")

    return df


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else '20260303'
    mode = sys.argv[2] if len(sys.argv) > 2 else 'oil'

    xtdata.connect(port=58610)
    print(f"\nTick外科解剖 v2 | 日期: {date} | 模式: {mode}")

    if mode == 'oil':
        print("\n【石油板块解剖】")
        for stock in OIL_STOCKS:
            r = single_stock_report(stock, date)
            if r:
                print_single_report(r)

    elif mode in ('batch', 'control'):
        probe_file = Path(f'data/atr_probe_{date}.csv')
        if not probe_file.exists():
            print(f"找不到 {probe_file}，请先运行 atr_probe")
            return

        probe_df = pd.read_csv(probe_file)

        if mode == 'batch':
            # 实验组：涨停股
            stocks = probe_df[probe_df['change_pct'] >= 9.8]['stock'].tolist()
            print(f"\n【实验组：涨停股】{len(stocks)} 只")
        else:
            # 对照组：普通涨幅1-3%的股票（随机抽50只）
            normal = probe_df[
                (probe_df['change_pct'] >= 1.0) &
                (probe_df['change_pct'] <= 3.0)
            ]['stock'].tolist()
            stocks = normal[:50]
            print(f"\n【对照组：普通股】{len(stocks)} 只（涨幅1~3%）")

        result_df = batch_analysis(date, stocks)

        if not result_df.empty:
            suffix = 'limit' if mode == 'batch' else 'control'
            out = Path(f'data/tick_prelude_{date}_{suffix}.csv')
            result_df.to_csv(out, index=False, encoding='utf-8-sig')
            print(f"\n结果已保存: {out}")


if __name__ == '__main__':
    main()
