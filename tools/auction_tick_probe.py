"""
竟价Tick格式验证探针

验证目标：
  Q1: 竟价期间 volume 是「增量」还是「累计」？
      → volume.diff() 的正负比例和分布
  Q2: ask1/bid1 在竟价阶段有效率是多少？
      → ask1==0 的占比
  Q3: QMT Tick 的推送频率？
      → 相邻两条Tick的时间间隔分布
  Q4: 9:25-9:30锁定期 vs 9:15-9:25自由期，两个窗口的数据质量差异
      → 两个窗口各自的 Tick 数量、价格变化次数、volume差分为负的次数
  Q5: lastPrice 更新频率？据此判断价格就至 9:30 几秒点的可靠性

用法：
  9:05 就要启动！
  python tools/auction_tick_probe.py          # 默认石油山长
  python tools/auction_tick_probe.py hot       # 配合当日热门股手动填入

输出：
  控制台实时打印每一条Tick的全量字段
  data/auction_tick_raw_{date}.csv  ← 所有原始 Tick 记录
  data/auction_tick_summary_{date}.csv ← 第一次大一统分析
运行时间：9:15 自动等待开始记录，9:32 自动停止
"""
import sys
import time
import csv
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from xtquant import xtdata

# ── CST 时区 ──────────────────────────────────────────────────
CST = timezone(timedelta(hours=8))

# ── 默认监控标的：石油山长 + 2只活跃参照股 ─────────────────
WATCH_STOCKS = [
    '600028.SH',   # 中国石化  ← 石油大市値代表
    '601857.SH',   # 中国石油
    '600583.SH',   # 海油工程  ← 小市値石油
    '000001.SZ',   # 平安银行  ← 参照：极高流动性
    '600519.SH',   # 茅台贵州  ← 参照：费金类大市値
]

# ── 时间边界 ──────────────────────────────────────────────────
T_RECORD_START = '09:15'
T_LOCK_START   = '09:25'
T_OPEN         = '09:30'
T_STOP         = '09:32'

# ── CSV 输出字段顺序（固定，方便对比）──────────────────────
CSV_FIELDS = [
    'wall_time',        # 本机收到该Tick的时刻 (HH:MM:SS.mmm)
    'stock',
    'auction_phase',    # 'early'(9:15-9:25) / 'lock'(9:25-9:30) / 'open'(9:30+)
    # --- 原始 QMT 字段 ---
    'qmt_time_ms',      # QMT 内部时间戳（毫秒）
    'lastPrice',
    'lastClose',
    'open',
    'high',
    'low',
    'volume',           # 累计成交量（手）
    'amount',           # 累计成交额（元）
    'ask1',             # 卖一
    'bid1',             # 买一
    'askVol1',
    'bidVol1',
    'transactionNum',   # 成交笔数
    # --- 派生字段（本脚本计算） ---
    'volume_delta',     # volume 差分（正=单笔成交, 负=异常!）
    'amount_delta',
    'price_delta',      # lastPrice 差分
    'ask1_valid',       # ask1 > 0
    'tick_interval_ms', # 相邻两条Tick的时间间隔
]


class _StockState:
    """单只股票的状态演进器（纯内部用）"""
    __slots__ = ('prev_volume', 'prev_amount', 'prev_price',
                 'prev_tick_ms', 'tick_count')

    def __init__(self):
        self.prev_volume:  Optional[float] = None
        self.prev_amount:  Optional[float] = None
        self.prev_price:   Optional[float] = None
        self.prev_tick_ms: Optional[int]   = None
        self.tick_count:   int             = 0


# ── 全局状态（callback 里直接访问，避免 closure 嵌套）─────────────
G_STATES:   dict[str, _StockState] = {s: _StockState() for s in WATCH_STOCKS}
G_ROWS:     list[dict]              = []   # 待写 CSV
G_STARTED:  bool                   = False
G_DATE:     str                    = datetime.now(CST).strftime('%Y%m%d')


def _current_hhmm() -> str:
    return datetime.now(CST).strftime('%H:%M')


def _auction_phase(hhmm: str) -> str:
    if   hhmm < T_LOCK_START: return 'early'
    elif hhmm < T_OPEN:       return 'lock'
    else:                     return 'open'


def _safe_first(val) -> float:
    """数组/列表取第一个元素，其他类型直接转 float"""
    if isinstance(val, (list, tuple)) and len(val) > 0:
        return float(val[0])
    try:
        return float(val)
    except Exception:
        return 0.0


def on_tick(data: dict):
    """QMT 订阅回调 —— 每条Tick都进来"""
    global G_STARTED

    now_hhmm = _current_hhmm()

    # 9:15 前不记录
    if now_hhmm < T_RECORD_START:
        return

    G_STARTED = True
    wall_time = datetime.now(CST).strftime('%H:%M:%S.%f')[:-3]
    phase     = _auction_phase(now_hhmm)

    for stock, fields in data.items():
        if stock not in G_STATES:
            continue

        state = G_STATES[stock]
        state.tick_count += 1

        # ── 安全取字段
        qmt_time_ms  = int(fields.get('time', 0))
        last_price   = float(fields.get('lastPrice',   0))
        last_close   = float(fields.get('lastClose',   0))
        open_p       = float(fields.get('open',        0))
        high_p       = float(fields.get('high',        0))
        low_p        = float(fields.get('low',         0))
        volume       = float(fields.get('volume',      0))  # 累计（手）
        amount       = float(fields.get('amount',      0))  # 累计（元）
        trans_num    = int(fields.get('transactionNum', 0))

        ask_raw      = fields.get('askPrice', [0])
        bid_raw      = fields.get('bidPrice', [0])
        ask_vol_raw  = fields.get('askVol',   [0])
        bid_vol_raw  = fields.get('bidVol',   [0])
        ask1    = _safe_first(ask_raw)
        bid1    = _safe_first(bid_raw)
        ask_v1  = _safe_first(ask_vol_raw)
        bid_v1  = _safe_first(bid_vol_raw)

        # ── 派生字段
        vol_delta    = (volume - state.prev_volume) if state.prev_volume is not None else 0.0
        amt_delta    = (amount - state.prev_amount) if state.prev_amount is not None else 0.0
        price_delta  = (last_price - state.prev_price) if state.prev_price is not None else 0.0
        tick_gap_ms  = (qmt_time_ms - state.prev_tick_ms) if state.prev_tick_ms is not None else 0

        # ── 更新状态
        state.prev_volume  = volume
        state.prev_amount  = amount
        state.prev_price   = last_price
        state.prev_tick_ms = qmt_time_ms

        row = {
            'wall_time':      wall_time,
            'stock':          stock,
            'auction_phase':  phase,
            'qmt_time_ms':    qmt_time_ms,
            'lastPrice':      last_price,
            'lastClose':      last_close,
            'open':           open_p,
            'high':           high_p,
            'low':            low_p,
            'volume':         volume,
            'amount':         amount,
            'ask1':           ask1,
            'bid1':           bid1,
            'askVol1':        ask_v1,
            'bidVol1':        bid_v1,
            'transactionNum': trans_num,
            'volume_delta':   round(vol_delta, 0),
            'amount_delta':   round(amt_delta, 2),
            'price_delta':    round(price_delta, 4),
            'ask1_valid':     1 if ask1 > 0 else 0,
            'tick_interval_ms': tick_gap_ms,
        }
        G_ROWS.append(row)

        # ── 控制台实时打印（每条都印）
        vol_delta_mark = ' ⚠️ NEG' if vol_delta < 0 else ''
        ask1_mark      = ' ⚠️ ask1=0' if ask1 == 0 else ''
        print(
            f"[{wall_time}][{phase.upper():5s}] {stock}"
            f"  price={last_price:.3f}(Δ{price_delta:+.3f})"
            f"  vol={volume:.0f}(Δ{vol_delta:+.0f}{vol_delta_mark})"
            f"  ask1={ask1:.3f}{ask1_mark}"
            f"  bid1={bid1:.3f}"
            f"  gap={tick_gap_ms}ms"
        )


def _print_summary():
    """项目最重要的输出：5个检验问题的定量回答"""
    if not G_ROWS:
        print("\n⚠️  没有收到任何Tick。请检查：")
        print("  1. QMT 客户端是否登录")
        print("  2. subscribe 是否在 9:15 前完成")
        return

    import statistics

    print(f"\n{'='*65}")
    print(f"【竟价Tick格式验证报告】  日期: {G_DATE}")
    print(f"{'='*65}")

    # 按股票分组
    from collections import defaultdict
    by_stock: dict[str, list] = defaultdict(list)
    for r in G_ROWS:
        by_stock[r['stock']].append(r)

    for stock, rows in by_stock.items():
        early = [r for r in rows if r['auction_phase'] == 'early']
        lock  = [r for r in rows if r['auction_phase'] == 'lock']
        opn   = [r for r in rows if r['auction_phase'] == 'open']
        total = len(rows)

        print(f"\n── {stock} ── 共{total}条Tick")
        for label, seg in [('9:15-9:25 自由期', early),
                           ('9:25-9:30 锁定期', lock),
                           ('9:30开盘后', opn)]:
            if not seg:
                print(f"  {label}: 0 条")
                continue

            # Q1: volume_delta 正负分布
            deltas      = [r['volume_delta'] for r in seg]
            neg_cnt     = sum(1 for d in deltas if d < 0)
            zero_cnt    = sum(1 for d in deltas if d == 0)
            pos_cnt     = sum(1 for d in deltas if d > 0)

            # Q2: ask1 有效率
            ask1_valid  = sum(r['ask1_valid'] for r in seg)

            # Q3: Tick 间隔
            gaps = [r['tick_interval_ms'] for r in seg if r['tick_interval_ms'] > 0]
            gap_median  = statistics.median(gaps) if gaps else 0
            gap_max     = max(gaps) if gaps else 0

            # Q4: 价格变化次数
            price_changes = sum(1 for r in seg if abs(r['price_delta']) > 0.001)

            # 题外话：竟价涨跌幅 vs 昨收
            last_price = seg[-1]['lastPrice']
            prev_close = seg[-1]['lastClose']
            gap_pct    = (last_price - prev_close) / prev_close * 100 if prev_close > 0 else 0

            print(f"  {label}")
            print(f"    Tick数: {len(seg)}  "
                  f"| volume_delta: +{pos_cnt} / 0:{zero_cnt} / −{neg_cnt}  "
                  f"[Q1: 负差分={neg_cnt/len(seg)*100:.0f}%]"
            )
            print(f"    ask1有效: {ask1_valid}/{len(seg)} = {ask1_valid/len(seg)*100:.0f}%  [Q2]")
            print(f"    Tick间隔: 中位={gap_median:.0f}ms 最大={gap_max:.0f}ms  [Q3]")
            print(f"    价格变化次数: {price_changes}/{len(seg)} = {price_changes/len(seg)*100:.0f}%  [Q4实时性]")
            print(f"    题外：竟价涨跌幅={gap_pct:+.2f}%  (lastPrice={last_price} / prevClose={prev_close})")

    # 锐利度结论：锁定期 vs 自由期
    print(f"\n{'='*65}")
    print("【Q4结论：9:25-9:30锁定期 vs 9:15-9:25自由期对比】")
    print(f"{'='*65}")

    all_early = [r for r in G_ROWS if r['auction_phase'] == 'early']
    all_lock  = [r for r in G_ROWS if r['auction_phase'] == 'lock']

    def _phase_stats(rows: list) -> dict:
        if not rows:
            return {}
        neg_pct    = sum(1 for r in rows if r['volume_delta'] < 0) / len(rows) * 100
        ask1_pct   = sum(r['ask1_valid'] for r in rows) / len(rows) * 100
        gaps       = [r['tick_interval_ms'] for r in rows if r['tick_interval_ms'] > 0]
        gap_med    = statistics.median(gaps) if gaps else 0
        changes    = sum(1 for r in rows if abs(r['price_delta']) > 0.001) / len(rows) * 100
        return {
            'n':         len(rows),
            'neg_vol%':  round(neg_pct, 1),
            'ask1%':     round(ask1_pct, 1),
            'gap_med':   round(gap_med, 0),
            'price_chg%': round(changes, 1),
        }

    se = _phase_stats(all_early)
    sl = _phase_stats(all_lock)

    if se and sl:
        print(f"  {'':20s} | {'9:15-9:25 自由期':>15} | {'9:25-9:30 锁定期':>15}")
        print(f"  {'-'*58}")
        print(f"  {'Tick总数':20s} | {se['n']:>15} | {sl['n']:>15}")
        print(f"  {'volume_delta<0占比':20s} | {se['neg_vol%']:>14.1f}% | {sl['neg_vol%']:>14.1f}%")
        print(f"  {'ask1有效率':20s} | {se['ask1%']:>14.1f}% | {sl['ask1%']:>14.1f}%")
        print(f"  {'Tick间隔中位(ms)':20s} | {se['gap_med']:>15} | {sl['gap_med']:>15}")
        print(f"  {'价格变化占比':20s} | {se['price_chg%']:>14.1f}% | {sl['price_chg%']:>14.1f}%")
        print()
        print("  解读向导：")
        if sl['ask1%'] > se['ask1%']:
            print(f"  ✅ 锁定期 ask1有效率更高 ({sl['ask1%']:.0f}% vs {se['ask1%']:.0f}%)，竟价数据质量符合预期")
        else:
            print(f"  ⚠️  ask1有效率无改善，考虑用 price_delta 方向判断替代 ask1")

        lock_neg = sl['neg_vol%']
        if lock_neg < 5:
            print(f"  ✅ 锁定期 volume_delta 负差分低 ({lock_neg:.0f}%)，成交量字段可用")
        else:
            print(f"  ⚠️  锁定期仍有 {lock_neg:.0f}% 负差分，采用 clip(lower=0) + 导串预警")


def _save_csv():
    if not G_ROWS:
        return

    # 原始 Tick
    raw_path = Path(f'data/auction_tick_raw_{G_DATE}.csv')
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(G_ROWS)
    print(f"\n原始Tick已保存: {raw_path}  ({len(G_ROWS)}条)")

    # 按股票按阶段汇总的简洁表（次日快速回顾）
    from collections import defaultdict
    import statistics

    summary_rows = []
    by_stock: dict[str, list] = defaultdict(list)
    for r in G_ROWS:
        by_stock[r['stock']].append(r)

    for stock, rows in by_stock.items():
        for phase in ('early', 'lock', 'open'):
            seg = [r for r in rows if r['auction_phase'] == phase]
            if not seg:
                continue
            gaps = [r['tick_interval_ms'] for r in seg if r['tick_interval_ms'] > 0]
            summary_rows.append({
                'stock':         stock,
                'phase':         phase,
                'tick_count':    len(seg),
                'vol_neg_pct':   round(sum(1 for r in seg if r['volume_delta'] < 0) / len(seg) * 100, 1),
                'ask1_valid_pct': round(sum(r['ask1_valid'] for r in seg) / len(seg) * 100, 1),
                'tick_gap_med_ms': round(statistics.median(gaps), 0) if gaps else 0,
                'price_change_pct': round(sum(1 for r in seg if abs(r['price_delta']) > 0.001) / len(seg) * 100, 1),
                'final_lastPrice': seg[-1]['lastPrice'],
                'final_lastClose': seg[-1]['lastClose'],
                'auction_gap_pct': round(
                    (seg[-1]['lastPrice'] - seg[-1]['lastClose']) / seg[-1]['lastClose'] * 100
                    if seg[-1]['lastClose'] > 0 else 0, 2
                ),
            })

    sum_path = Path(f'data/auction_tick_summary_{G_DATE}.csv')
    if summary_rows:
        import csv as _csv
        with open(sum_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = _csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"汇总已保存: {sum_path}")


def main():
    # 自定义监控标的
    mode = sys.argv[1] if len(sys.argv) > 1 else 'default'
    if mode == 'hot':
        print("模式: hot — 请将当日热门股票代码填入 WATCH_STOCKS 再运行")
        print("示例: WATCH_STOCKS = ['000001.SZ', '600028.SH', ...]")
        return

    print("=" * 65)
    print(f"竟价Tick格式验证探针  |  日期: {G_DATE}")
    print(f"监控标的: {WATCH_STOCKS}")
    print(f"记录窗口: {T_RECORD_START} ~ {T_STOP}")
    print("=" * 65)

    # ── 连接 QMT ─────────────────────────────────────────────
    xtdata.connect(port=58610)

    # ── 订阅实时 Tick（订阅要在 9:15 前完成，否则早期 Tick 会丢失）─────
    print("\n[订阅实时Tick开始]")
    for stock in WATCH_STOCKS:
        seq = xtdata.subscribe_quote(
            stock,
            period='tick',
            start_time='',
            count=-1,
            callback=on_tick
        )
        print(f"  {stock} 订阅 seq={seq}")

    # ── 等待到 9:15 才开始打印 ────────────────────────────────
    while _current_hhmm() < T_RECORD_START:
        remaining = (
            datetime.strptime(T_RECORD_START, '%H:%M') -
            datetime.now().replace(second=0, microsecond=0)
        ).seconds
        print(f"  等待竟价开始 (9:15)，还有 {remaining//60}分{remaining%60}秒…", end='\r')
        time.sleep(5)

    print(f"\n\n[竟价开始] {datetime.now(CST).strftime('%H:%M:%S')} 开始记录")
    print("格式: [wall_time][PHASE] stock  price=xxx(Δxxx)  vol=xxx(Δxxx)  ask1=xxx  bid1=xxx  gap=xxxms")
    print("-" * 65)

    # ── 主循环：保活到 9:32 ─────────────────────────────────────────
    # 不用 xtdata.run()（会阻塞无法定时停止），改用轮询等待
    try:
        while _current_hhmm() < T_STOP:
            time.sleep(0.2)   # 200ms 轮询足够细腐
    except KeyboardInterrupt:
        print("\n[手动中断]")

    # ── 9:32 停止，打印汇总────────────────────────────────────────
    print(f"\n\n[停止记录] {datetime.now(CST).strftime('%H:%M:%S')}  共收到 {len(G_ROWS)} 条Tick")

    # 取消订阅
    for stock in WATCH_STOCKS:
        try:
            xtdata.unsubscribe_quote(stock, period='tick')
        except Exception:
            pass

    _print_summary()
    _save_csv()


if __name__ == '__main__':
    main()
