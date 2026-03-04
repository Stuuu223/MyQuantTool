"""
游资预期布局双日模型探针

核心研究目标:
  ① 石油标的周五有没有预兆 (fri_atr_ratio / fri_vol_ratio 是否高于基准)
  ② 周五预埋信号命中率 (prepos_signal=True 里周一真正引爆的比例 vs 随机基线)
  ③ 阈值从数据里来 (90分位数是多少就把阈值定在哪里)

用法:
  python tools/atr_preposition_probe.py                   # 默认 0228 vs 0303
  python tools/atr_preposition_probe.py 20260228 20260303  # 自定义日期对

研究背景:
  洲际油气6天4板——周五(0228)市场已有预期，游资提前布局
  周末:催化剂落地（伊朗地缘事件）
  周一(0303):全面引爆
  → 游资预期布局的痕迹是否可被系统捕捉？
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from xtquant import xtdata

from logic.utils.calendar_utils import get_nth_previous_trading_day

# ── 石油板块核心标的 ──────────────────────────────────────────────
OIL_STOCKS = [
    '600028.SH',  # 中国石化
    '601857.SH',  # 中国石油
    '600583.SH',  # 海油工程
    '600339.SH',  # 中油工程
    '601808.SH',  # 中海油服
    '000096.SZ',  # 广聚能源
    '002221.SZ',  # 东华能源
    '300159.SZ',  # 新研股份
    '000554.SZ',  # 泰山石油
]

# ── 阈值（暂定，跑完看90分位数再调） ─────────────────────────────
FRI_ATR_THRESHOLD    = 1.2   # 周五预兆：振幅/ATR20 > 1.2x（暂定）
MON_ATR_THRESHOLD    = 2.0   # 周一引爆：振幅/ATR20 > 2.0x
MON_CHANGE_THRESHOLD = 5.0   # 周一引爆：涨幅 > 5%（双条件确认）
ATR_HIST_DAYS        = 20    # 历史基准：周五之前N个交易日


def _to_date_str(val) -> str:
    """统一转成 YYYYMMDD 字符串，兼容 int/float/str 三种 QMT 返回格式"""
    s = str(val)
    # int 或 str 类型的纯数字（如 20260228 → '20260228'）
    if s.isdigit():
        return s[:8]
    # float 类型（如 '20260228.0'）
    try:
        return str(int(float(s)))[:8]
    except Exception:
        return s[:8]


def _build_row(stock: str, df_raw: pd.DataFrame, FRI: str, MON: str) -> dict | None:
    """
    对单只股票计算双日指标，失败返回 None。
    内联函数避免过深嵌套，保持主循环干净。
    """
    df = df_raw.copy()
    df.index = [_to_date_str(x) for x in df.index]

    # ── 历史基准：取周五之前末尾 ATR_HIST_DAYS 行 ──────────────
    hist = df[df.index < FRI].tail(ATR_HIST_DAYS)
    if len(hist) < 5:
        return None

    pre_close_shifted = hist['close'].shift(1)
    atr_base = (
        (hist['high'] - hist['low']) /
        pre_close_shifted.replace(0, np.nan)
    ).mean()

    if not atr_base or atr_base <= 0 or np.isnan(atr_base):
        return None

    avg_vol_base  = hist['volume'].mean()
    avg_amt_base  = hist['amount'].mean()
    prev_fri_close = hist['close'].iloc[-1]   # 周四收盘 = 周五的昨收

    # ── 取周五行、周一行 ─────────────────────────────────────
    fri_rows = df[df.index == FRI]
    mon_rows = df[df.index == MON]
    if fri_rows.empty or mon_rows.empty:
        return None

    fri = fri_rows.iloc[-1]
    mon = mon_rows.iloc[-1]

    if fri['close'] <= 0 or mon['close'] <= 0:
        return None

    # ── 周五指标 ─────────────────────────────────────────────
    fri_amp       = (fri['high'] - fri['low']) / fri['close']
    fri_atr_ratio = fri_amp / atr_base
    fri_vol_ratio = fri['volume'] / avg_vol_base  if avg_vol_base  > 0 else 0.0
    fri_amt_ratio = fri['amount'] / avg_amt_base  if avg_amt_base  > 0 else 0.0
    fri_change    = (fri['close'] - prev_fri_close) / prev_fri_close * 100 if prev_fri_close > 0 else 0.0

    # ── 周一指标 ─────────────────────────────────────────────
    mon_amp       = (mon['high'] - mon['low']) / mon['close']
    mon_atr_ratio = mon_amp / atr_base
    mon_vol_ratio = mon['volume'] / avg_vol_base  if avg_vol_base  > 0 else 0.0
    mon_amt_ratio = mon['amount'] / avg_amt_base  if avg_amt_base  > 0 else 0.0
    mon_change    = (mon['close'] - fri['close']) / fri['close'] * 100

    # ── 联动信号拆分（分开存，方便后续交叉分析）─────────────────
    has_fri_signal = fri_atr_ratio > FRI_ATR_THRESHOLD
    is_mon_breakout = (mon_atr_ratio > MON_ATR_THRESHOLD) and (mon_change > MON_CHANGE_THRESHOLD)
    prepos_signal  = has_fri_signal and is_mon_breakout

    return {
        'stock':           stock,
        # 周五
        'fri_atr_ratio':   round(fri_atr_ratio, 3),
        'fri_vol_ratio':   round(fri_vol_ratio, 3),
        'fri_amt_ratio':   round(fri_amt_ratio, 3),
        'fri_change':      round(fri_change, 2),
        # 周一
        'mon_atr_ratio':   round(mon_atr_ratio, 3),
        'mon_vol_ratio':   round(mon_vol_ratio, 3),
        'mon_amt_ratio':   round(mon_amt_ratio, 3),
        'mon_change':      round(mon_change, 2),
        # 联动
        'has_fri_signal':  has_fri_signal,
        'is_mon_breakout': is_mon_breakout,
        'prepos_signal':   prepos_signal,
    }


def scan_universe(stocks: list, FRI: str, MON: str, hist_start: str) -> tuple[pd.DataFrame, int]:
    """全市场扫描，返回 (df_all, error_count)"""
    rows = []
    errors = 0

    for i, stock in enumerate(stocks):
        try:
            d = xtdata.get_local_data(
                ['high', 'low', 'close', 'volume', 'amount'],
                [stock], '1d', hist_start, MON
            )
            if not d or stock not in d or d[stock].empty or len(d[stock]) < 6:
                continue

            row = _build_row(stock, d[stock], FRI, MON)
            if row is not None:
                rows.append(row)

        except Exception:
            errors += 1
            continue

        if (i + 1) % 500 == 0:
            print(f"  进度: {i+1}/{len(stocks)} | 入库: {len(rows)}")

    return pd.DataFrame(rows), errors


def print_quantiles(df: pd.DataFrame, col: str, label: str) -> None:
    print(f"\n{label}:")
    for p in [50, 75, 90, 95, 99]:
        v = df[col].quantile(p / 100)
        print(f"  {p:2d}分位: {v:.3f}x")


def print_hit_rate(df_all: pd.DataFrame) -> float:
    """
    命中率分析核心：
      精确率 = 有周五预兆 中 周一真引爆的比例
      随机基线 = 全市场周一引爆比例
      Lift = 精确率 / 随机基线  →  Lift > 1.5 才有实用价值
    返回 Lift 值供外部使用。
    """
    has_signal   = df_all[df_all['has_fri_signal']]
    mon_breakout = df_all[df_all['is_mon_breakout']]
    hit          = df_all[df_all['prepos_signal']]

    n_total      = len(df_all)
    n_signal     = len(has_signal)
    n_breakout   = len(mon_breakout)
    n_hit        = len(hit)

    baseline  = n_breakout / n_total if n_total > 0 else 0.0
    precision = n_hit      / n_signal if n_signal > 0 else 0.0
    lift      = precision  / baseline if baseline > 0 else 0.0

    print(f"\n{'='*65}")
    print(f"【命中率分析】")
    print(f"{'='*65}")
    print(f"  全市场样本:                 {n_total:5d} 只")
    print(f"  周五有预兆(>{FRI_ATR_THRESHOLD}x):         {n_signal:5d} 只  ({n_signal/n_total*100:.1f}%)")
    print(f"  周一引爆(>{MON_ATR_THRESHOLD}x & >{MON_CHANGE_THRESHOLD}%):   {n_breakout:5d} 只  ({n_breakout/n_total*100:.1f}%)")
    print(f"  ──────────────────────────────────────────────")
    print(f"  精确率 (预兆→引爆):         {precision*100:5.1f}%")
    print(f"  随机基线:                   {baseline*100:5.1f}%")
    print(f"  Lift (提升倍数):            {lift:5.2f}x")
    print(f"  ──────────────────────────────────────────────")
    if lift >= 2.0:
        verdict = '✅ 强显著：游资预埋信号可被系统化捕捉'
    elif lift >= 1.5:
        verdict = '✅ 有效：信号有统计意义，继续扩大样本验证'
    elif lift >= 1.0:
        verdict = '⚠️  微弱：信号需要配合其他维度过滤'
    else:
        verdict = '❌ 无效：随机噪声，调整阈值或研究方向'
    print(f"  结论: {verdict}")

    return lift


def print_threshold_advice(df_all: pd.DataFrame) -> None:
    """用分位数重算不同阈值下的命中率，给出数据驱动的阈值建议"""
    p75 = df_all['fri_atr_ratio'].quantile(0.75)
    p90 = df_all['fri_atr_ratio'].quantile(0.90)
    n_breakout = len(df_all[df_all['is_mon_breakout']])
    baseline   = n_breakout / len(df_all) if len(df_all) > 0 else 0.0

    print(f"\n{'='*65}")
    print(f"【数据驱动阈值建议】")
    print(f"{'='*65}")
    print_quantiles(df_all, 'fri_atr_ratio', '  周五 fri_atr_ratio 分位数')
    print_quantiles(df_all, 'mon_atr_ratio', '  周一 mon_atr_ratio 分位数')
    print_quantiles(df_all, 'fri_vol_ratio', '  周五 fri_vol_ratio 量比')

    for label, threshold in [('保守(75分位)', p75), ('激进(90分位)', p90)]:
        mask_signal   = df_all['fri_atr_ratio'] > threshold
        mask_hit      = mask_signal & df_all['is_mon_breakout']
        n_s = mask_signal.sum()
        n_h = mask_hit.sum()
        prec  = n_h / n_s if n_s > 0 else 0.0
        lift  = prec / baseline if baseline > 0 else 0.0
        print(f"\n  {label}: fri_atr_ratio > {threshold:.2f}x")
        print(f"    有预兆: {n_s} 只  命中引爆: {n_h} 只  "
              f"精确率: {prec*100:.1f}%  Lift: {lift:.2f}x")


def main() -> None:
    # ── 参数解析 ────────────────────────────────────────────────
    FRI = sys.argv[1] if len(sys.argv) >= 2 else '20260228'
    MON = sys.argv[2] if len(sys.argv) >= 3 else '20260303'
    HIST_START = get_nth_previous_trading_day(FRI, 25)

    print("=" * 65)
    print("游资预期布局双日模型探针")
    print(f"  周五(预埋日): {FRI}   周一(引爆日): {MON}")
    print(f"  历史基准: {HIST_START} ~ {FRI}（前{ATR_HIST_DAYS}日均值）")
    print(f"  预兆阈值: fri_atr_ratio > {FRI_ATR_THRESHOLD}x")
    print(f"  引爆条件: mon_atr_ratio > {MON_ATR_THRESHOLD}x  AND  mon_change > {MON_CHANGE_THRESHOLD}%")
    print("=" * 65)

    # ── 连接 QMT ─────────────────────────────────────────────────
    xtdata.connect(port=58610)

    stocks = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"\n全市场: {len(stocks)} 只 | 开始扫描...")

    # ── 主扫描 ──────────────────────────────────────────────────
    df_all, errors = scan_universe(stocks, FRI, MON, HIST_START)

    if df_all.empty:
        print("❌ 无有效数据，请确认本地 QMT 数据已下载（smart_download.py）")
        return

    print(f"\n有效样本: {len(df_all)} 只 | 异常跳过: {errors}")

    # ════════════════════════════════════════════════════════════
    # 输出一：石油板块双日对比表
    # ════════════════════════════════════════════════════════════
    SHOW_COLS = [
        'stock',
        'fri_atr_ratio', 'fri_vol_ratio', 'fri_change',
        'mon_atr_ratio', 'mon_vol_ratio', 'mon_change',
        'has_fri_signal', 'is_mon_breakout',
    ]

    print(f"\n{'='*65}")
    print(f"【石油板块双日对比】")
    print(f"{'='*65}")
    oil_df = (
        df_all[df_all['stock'].isin(OIL_STOCKS)]
        .sort_values('mon_atr_ratio', ascending=False)
    )
    if not oil_df.empty:
        print(oil_df[SHOW_COLS].to_string(index=False))

        # 关键判断：周五有没有预兆？
        fri_p75 = df_all['fri_atr_ratio'].quantile(0.75)
        oil_with_signal = oil_df[oil_df['fri_atr_ratio'] > fri_p75]
        print(f"\n  [全市场75分位基准] fri_atr_ratio > {fri_p75:.3f}x")
        print(f"  石油标的中高于基准: {len(oil_with_signal)}/{len(oil_df)} 只")
        if not oil_with_signal.empty:
            print(f"  命中: {oil_with_signal['stock'].tolist()}")
            print(f"  ✅ 周五已有游资预布局痕迹")
        else:
            print(f"  ❌ 周五无显著预兆 → 石油为催化剂驱动，非提前布局")
    else:
        print("  ⚠️  石油标的无数据，请检查本地数据")

    # ════════════════════════════════════════════════════════════
    # 输出二：周五预埋 + 周一引爆 联动命中榜
    # ════════════════════════════════════════════════════════════
    signal_df = (
        df_all[df_all['prepos_signal']]
        .sort_values('mon_atr_ratio', ascending=False)
    )
    print(f"\n{'='*65}")
    print(f"【周五预埋 + 周一引爆 联动命中】  共 {len(signal_df)} 只")
    print(f"{'='*65}")
    if not signal_df.empty:
        print(signal_df.head(30)[SHOW_COLS].to_string(index=False))
    else:
        print("  暂无命中（阈值暂定1.2x，见下方分位数建议调整）")

    # ════════════════════════════════════════════════════════════
    # 输出三：命中率分析（核心验证）
    # ════════════════════════════════════════════════════════════
    lift = print_hit_rate(df_all)

    # ════════════════════════════════════════════════════════════
    # 输出四：周一引爆股 Top30（不管周五有没有预兆）
    #         → 用来看「引爆股里有多少是有预兆的」
    # ════════════════════════════════════════════════════════════
    mon_breakout_df = (
        df_all[df_all['is_mon_breakout']]
        .sort_values('mon_atr_ratio', ascending=False)
    )
    n_has_prepos = mon_breakout_df['has_fri_signal'].sum()
    print(f"\n{'='*65}")
    print(f"【周一引爆股 Top30】  共 {len(mon_breakout_df)} 只")
    print(f"  其中有周五预兆(>{FRI_ATR_THRESHOLD}x): {n_has_prepos} 只 "
          f"({n_has_prepos/len(mon_breakout_df)*100:.1f}%  ← 这是关键比例)")
    print(f"{'='*65}")
    print(mon_breakout_df.head(30)[SHOW_COLS].to_string(index=False))

    # ════════════════════════════════════════════════════════════
    # 输出五：数据驱动阈值建议
    # ════════════════════════════════════════════════════════════
    print_threshold_advice(df_all)

    # ── 保存完整结果 ─────────────────────────────────────────────
    out = Path(f'data/atr_preposition_probe_{FRI[4:]}_{MON[4:]}.csv')
    out.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_csv(out, index=False, encoding='utf-8-sig')
    print(f"\n完整结果已保存: {out}")
    print(f"{'='*65}\n")


if __name__ == '__main__':
    main()
