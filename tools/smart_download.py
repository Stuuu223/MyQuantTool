"""
智能下载器 - 日K本地读取 + Tick精准狙击
用法:
    python tools/smart_download.py                                        # 默认上个交易日（粗筛）
    python tools/smart_download.py 20260303                               # 单日（粗筛）
    python tools/smart_download.py 20260206 20260303                      # 日期范围（粗筛）
    python tools/smart_download.py 20260206 20260303 --full               # 日期范围（全市场全量）
    python tools/smart_download.py 20260119 20260121 --stocks 600759.SH   # 指定股票，绕开粗筛
    python tools/smart_download.py 20260119 20260121 --stocks 600759.SH,603353.SH  # 多只

设计原则:
  1. 日K直接读本地；不足时先自动补充，补失败才退出
  2. 常规模式：逐日 UniverseBuilder 粗筛 → 下载 Tick（量比达标票）
  3. --full 模式：全市场循环投递，每100只打印一次进度
  4. --stocks 模式：绕开粗筛，直接对指定股票下载 Tick（研究用）
  5. [P0修复] download_history_data 是异步调用，ok计数必须经落盘验证
     verify_landed() 投递后 sleep(VERIFY_WAIT_S) 再读本地，真实非空才算 verified
     全量模式批量投递完后统一抽样验证（不逐只等待，保证速度）
"""
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

PRINT_EVERY    = 100   # 每100只打印一次进度
DAY_SLEEP      = 2     # 两个交易日之间间隔(s)
VERIFY_WAIT_S  = 1.5   # 投递后等待落盘的秒数（--stocks 模式每只验证）
BATCH_VERIFY_N = 10    # --full/粗筛模式完成后抽样验证的只数


def log(msg: str) -> None:
    ts = datetime.now().strftime('%H:%M:%S')
    print(f'[{ts}] {msg}', flush=True)


# ──────────────────────────────────────────────
# 核心：落盘验证
# ──────────────────────────────────────────────

def verify_landed(stock: str, date: str, xtdata, wait_s: float = VERIFY_WAIT_S) -> bool:
    """
    等待 wait_s 秒后读本地 tick，返回是否真实落盘。
    注意：get_local_data 的 field_list=[] 表示读全部字段。
    """
    time.sleep(wait_s)
    try:
        raw = xtdata.get_local_data(
            field_list=[], stock_list=[stock],
            period='tick', start_time=date, end_time=date,
            count=-1
        )
        df = raw.get(stock)
        return df is not None and len(df) > 0
    except Exception:
        return False


def batch_verify_sample(stocks: list[str], date: str, xtdata,
                         n: int = BATCH_VERIFY_N) -> dict:
    """
    批量投递完成后，从 stocks 中等间距抽取 n 只验证落盘情况。
    返回 {'checked': n, 'landed': k, 'sample': [...]}
    """
    if not stocks:
        return {'checked': 0, 'landed': 0, 'sample': []}
    step    = max(1, len(stocks) // n)
    targets = stocks[::step][:n]
    landed  = 0
    sample  = []
    for s in targets:
        ok = verify_landed(s, date, xtdata, wait_s=0.5)   # 抽样给短暂等待
        if ok:
            landed += 1
        sample.append({'stock': s, 'landed': ok})
    return {'checked': len(targets), 'landed': landed, 'sample': sample}


# ──────────────────────────────────────────────
# 日期工具
# ──────────────────────────────────────────────

def get_trading_days(start_date: str, end_date: str, xtdata) -> list[str]:
    """优先读本地510300日K判断交易日，fallback用自然日去除周末"""
    try:
        raw = xtdata.get_local_data(
            field_list=['close'], stock_list=['510300.SH'],
            period='1d', start_time=start_date, end_time=end_date
        )
        df = raw.get('510300.SH')
        if df is not None and not df.empty:
            days = [str(idx)[:8] for idx in df.index.tolist()]
            days = [d for d in days if start_date <= d <= end_date]
            if days:
                return days
    except Exception:
        pass
    s = datetime.strptime(start_date, '%Y%m%d')
    e = datetime.strptime(end_date,   '%Y%m%d')
    days, cur = [], s
    while cur <= e:
        if cur.weekday() < 5:
            days.append(cur.strftime('%Y%m%d'))
        cur += timedelta(days=1)
    return days


def get_last_completed_day(xtdata, fallback: str) -> str:
    """向前最多找14天，找到本地日K有数据的最近交易日"""
    cur = datetime.now() - timedelta(days=1)
    for _ in range(14):
        if cur.weekday() < 5:
            d = cur.strftime('%Y%m%d')
            try:
                sample = xtdata.get_local_data(
                    field_list=['close'],
                    stock_list=['000001.SZ', '600000.SH', '300001.SZ'],
                    period='1d', start_time=d, end_time=d
                )
                valid = sum(
                    1 for s in ['000001.SZ', '600000.SH', '300001.SZ']
                    if s in sample and sample[s] is not None and len(sample[s]) > 0
                )
                if valid >= 2:
                    return d
            except Exception:
                pass
        cur -= timedelta(days=1)
    return fallback


# ──────────────────────────────────────────────
# 日K本地检查 + 自动补充（P2修复）
# ──────────────────────────────────────────────

def ensure_daily_kline(xtdata, check_date: str, start_date: str, end_date: str) -> bool:
    """
    检查本地日K是否充足；不足时自动投递补充请求后重新验证。
    返回 True=可继续，False=日K仍不足需退出。
    """
    ANCHORS = ['000001.SZ', '600000.SH', '510300.SH']

    def _count_valid() -> int:
        sample = xtdata.get_local_data(
            field_list=['close'], stock_list=ANCHORS,
            period='1d', start_time=check_date, end_time=check_date
        )
        return sum(
            1 for s in ANCHORS
            if s in sample and sample[s] is not None and len(sample[s]) > 0
        )

    valid_n = _count_valid()
    if valid_n >= 2:
        log(f'  ✅ 本地日K充足 ({valid_n}/{len(ANCHORS)})')
        return True

    log(f'  ⚠️ 本地日K不足 ({valid_n}/{len(ANCHORS)})，尝试自动补充...')
    for s in ANCHORS:
        try:
            xtdata.download_history_data(s, '1d',
                                         start_time=start_date, end_time=end_date)
        except Exception:
            pass
    log('  等待3s让日K落盘...')
    time.sleep(3)

    valid_n = _count_valid()
    if valid_n >= 2:
        log(f'  ✅ 日K补充成功 ({valid_n}/{len(ANCHORS)})')
        return True

    log(f'  ❌ 日K补充后仍不足 ({valid_n}/{len(ANCHORS)})。')
    log('  原因可能: QMT客户端未登录 / 未订阅日K权限 / 无网络连接。')
    log('  请在QMT客户端手动下载日K数据后重试。')
    return False


# ──────────────────────────────────────────────
# 单日下载核心（批量投递 + 完成后抽样验证）
# ──────────────────────────────────────────────

def download_one_day(date: str, stocks: list[str], xtdata,
                     full: bool, do_verify: bool = False) -> dict:
    """
    [P0修复说明]
    download_history_data 是异步调用，立即返回None。
    原始代码中 ok+1 只说明"调用未抛异常"，不代表数据落盘。
    本函数：
      - 批量投递全部股票（保持速度）
      - 完成后抽样 BATCH_VERIFY_N 只验证真实落盘率
      - 落盘率写入 tick_index.json
    若需逐只精确验证，请用 download_with_verify()（--stocks模式专用）
    """
    total = len(stocks)
    t0    = time.time()
    ok    = 0
    fail  = 0

    log(f'  开始投递 {total}只 Tick ({date})')
    for i, stock in enumerate(stocks):
        try:
            xtdata.download_history_data(stock, 'tick',
                                         start_time=date, end_time=date)
            ok += 1
        except Exception:
            fail += 1

        if (i + 1) % PRINT_EVERY == 0 or (i + 1) == total:
            elapsed   = time.time() - t0
            speed     = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (total - i - 1) / speed if speed > 0 else 0
            log(f'  [{i+1}/{total}] 投递✅{ok} 失败❌{fail} | '
                f'{elapsed:.0f}s已用 预计剩{remaining:.0f}s | {speed:.0f}只/s')

    elapsed = time.time() - t0
    log(f'  投递完毕: {total}只 投递成功{ok} 投递失败{fail} 耗时{elapsed:.0f}s')

    # 抽样落盘验证
    verify_result = {'checked': 0, 'landed': 0, 'sample': []}
    if do_verify and ok > 0:
        log(f'  [落盘验证] 抽取{BATCH_VERIFY_N}只验证真实落盘...')
        time.sleep(2)   # 给异步队列处理窗口
        verify_result = batch_verify_sample(stocks, date, xtdata)
        land_rate = verify_result['landed'] / verify_result['checked'] * 100 \
                    if verify_result['checked'] > 0 else 0
        log(f'  [落盘验证] {verify_result["landed"]}/{verify_result["checked"]}只 '
            f'落盘率{land_rate:.0f}%')
        if land_rate < 30:
            log(f'  ⚠️  落盘率过低！可能原因: QMT数据服务未启动 / 服务端无此日期Tick / 磁盘写满')

    # 写 tick_index
    try:
        idx_dir = Path(__file__).parent.parent / 'data' / 'tick_index'
        idx_dir.mkdir(parents=True, exist_ok=True)
        with open(idx_dir / f'{date}.json', 'w', encoding='utf-8') as f:
            json.dump({
                'date':          date,
                'mode':          'full' if full else 'filtered',
                'count':         total,
                'dispatched_ok': ok,
                'dispatched_fail': fail,
                'elapsed_s':     round(elapsed, 1),
                'verify':        verify_result,   # 落盘验证结果（新增）
                'timestamp':     datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'note':          '[P0] dispatched_ok=投递成功数(非落盘数)，'
                                 '落盘以verify.landed/checked为准'
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return {'dispatched': ok, 'fail': fail, 'verify': verify_result}


# ──────────────────────────────────────────────
# --stocks 模式：逐只投递+验证（研究用，慢但精确）
# ──────────────────────────────────────────────

def download_with_verify(date: str, stocks: list[str], xtdata) -> dict:
    """
    [P1] --stocks 模式专用：每只股票投递后等待落盘验证。
    速度慢（每只约1.5s），但结果精确，适合研究少量标的。
    验证失败时重试一次。
    """
    total    = len(stocks)
    verified = 0
    failed   = 0
    detail   = []

    log(f'  [--stocks精确模式] 逐只投递+验证 {total}只 ({date})')
    for i, stock in enumerate(stocks):
        try:
            xtdata.download_history_data(stock, 'tick',
                                         start_time=date, end_time=date)
        except Exception as e:
            log(f'  [{i+1}/{total}] {stock} 投递异常: {e}')
            failed += 1
            detail.append({'stock': stock, 'status': 'dispatch_error'})
            continue

        landed = verify_landed(stock, date, xtdata, wait_s=VERIFY_WAIT_S)
        if not landed:
            # 重试一次：再投递+再等待
            try:
                xtdata.download_history_data(stock, 'tick',
                                             start_time=date, end_time=date)
            except Exception:
                pass
            landed = verify_landed(stock, date, xtdata, wait_s=VERIFY_WAIT_S)

        if landed:
            verified += 1
            status = 'landed'
        else:
            failed += 1
            status = 'not_landed'   # 服务端可能无此日期数据

        log(f'  [{i+1}/{total}] {stock} → {"✅ 落盘" if landed else "❌ 未落盘"} ({status})')
        detail.append({'stock': stock, 'status': status})

    log(f'  [{date}] 落盘✅{verified} 未落盘❌{failed} / 共{total}只')
    if failed > 0 and verified == 0:
        log('  ⚠️  全部未落盘！服务端可能无此日期Tick，或QMT数据服务未连接')
    return {'date': date, 'verified': verified, 'failed': failed, 'detail': detail}


# ──────────────────────────────────────────────
# 主程序
# ──────────────────────────────────────────────

def main():
    from xtquant import xtdata
    from logic.core.config_manager import get_config_manager
    from logic.utils.calendar_utils import get_latest_completed_trading_day

    cfg  = get_config_manager()
    args = sys.argv[1:]

    full_mode    = '--full' in args
    stocks_arg   = next((a for a in args if a.startswith('--stocks=')), None)
    # 支持 --stocks=600759.SH,603353.SH 或 --stocks 600759.SH,603353.SH
    if stocks_arg:
        pinpoint_stocks = [s.strip() for s in stocks_arg.split('=', 1)[1].split(',') if s.strip()]
    else:
        # 检查 --stocks 后有无跟着值（不含 = 的写法）
        try:
            idx = args.index('--stocks')
            pinpoint_stocks = [s.strip() for s in args[idx + 1].split(',') if s.strip()]
        except (ValueError, IndexError):
            pinpoint_stocks = []

    dates_args = [a for a in args if not a.startswith('--') and ',' not in a]

    if len(dates_args) >= 2:
        start_date, end_date = dates_args[0], dates_args[1]
    elif len(dates_args) == 1:
        start_date = end_date = dates_args[0]
    else:
        start_date = end_date = get_latest_completed_trading_day()

    # 模式标签
    if pinpoint_stocks:
        mode_label = f'PINPOINT精确({len(pinpoint_stocks)}只)'
    elif full_mode:
        mode_label = 'FULL全量'
    else:
        mode_label = '粗筛'

    print('=' * 60)
    print(f'智能下载器 | {start_date}~{end_date} | {mode_label}')
    if pinpoint_stocks:
        print(f'  指定标的: {", ".join(pinpoint_stocks)}')
    print('=' * 60)

    port = cfg.get('system_and_risk.qmt_port', 58610)
    log(f'连接端口 {port}...')
    try:
        xtdata.connect(port=port)
        log('✅ 连接成功')
    except Exception as e:
        log(f'❌ 连接失败: {e}')
        return

    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    log(f'全市场 {len(all_stocks)} 只股票')

    # ── 阶段一：日K检查（P2修复：不足时自动补充） ──
    log('[阶段一] 检查本地日K...')
    check_date = get_last_completed_day(xtdata, fallback=start_date)
    log(f'  检查基准日期: {check_date}')
    if not ensure_daily_kline(xtdata, check_date, start_date, end_date):
        return

    trading_days = get_trading_days(start_date, end_date, xtdata)
    today        = datetime.now().strftime('%Y%m%d')
    trading_days = [d for d in trading_days if d <= today]
    log(f'  交易日 ({len(trading_days)}天): '
        f'{trading_days[0] if trading_days else "N/A"} ~ '
        f'{trading_days[-1] if trading_days else "N/A"}')

    if not trading_days:
        log('❌ 没有可处理的交易日，退出')
        return

    # ── 阶段二：下载 ──

    # [P1] --stocks 精确模式
    if pinpoint_stocks:
        log(f'[阶段二] PINPOINT模式 - 逐只精确验证落盘')
        grand_t0    = time.time()
        all_results = []
        for i, date in enumerate(trading_days):
            log(f'\n>>> [{i+1}/{len(trading_days)}] {date}')
            result = download_with_verify(date, pinpoint_stocks, xtdata)
            all_results.append(result)
            if i < len(trading_days) - 1:
                time.sleep(DAY_SLEEP)

        # 汇总报告写入 tick_index
        try:
            idx_dir = Path(__file__).parent.parent / 'data' / 'tick_index'
            idx_dir.mkdir(parents=True, exist_ok=True)
            rpt_path = idx_dir / f'pinpoint_{start_date}_{end_date}.json'
            with open(rpt_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'mode':      'pinpoint',
                    'stocks':    pinpoint_stocks,
                    'start':     start_date,
                    'end':       end_date,
                    'results':   all_results,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }, f, ensure_ascii=False, indent=2)
            log(f'\n📄 报告已写入: {rpt_path}')
        except Exception:
            pass

        total_elapsed = time.time() - grand_t0
        log(f'\n✅ PINPOINT完成! 总耗时 {total_elapsed:.0f}s')
        log('  如所有日期均❌未落盘 → 服务端无此标的历史Tick（确认结论前请用更早日期轮询）')
        return

    # FULL 模式
    if full_mode:
        log(f'[阶段二] FULL模式 - {len(trading_days)}天 x {len(all_stocks)}只')
        grand_t0 = time.time()
        for i, date in enumerate(trading_days):
            log(f'\n>>> [{i+1}/{len(trading_days)}] {date}')
            download_one_day(date, all_stocks, xtdata, full=True, do_verify=True)
            total_elapsed = time.time() - grand_t0
            remaining     = (total_elapsed / (i + 1)) * (len(trading_days) - i - 1)
            log(f'  总进度: {i+1}/{len(trading_days)}天 | '
                f'总耗时{total_elapsed:.0f}s | 预计剩{remaining:.0f}s ({remaining/60:.1f}min)')
            if i < len(trading_days) - 1:
                time.sleep(DAY_SLEEP)
        total_elapsed = time.time() - grand_t0
        log(f'\n✅ FULL全量完成! 总耗时 {total_elapsed:.0f}s ({total_elapsed/60:.1f}min)')
        return

    # 粗筛模式
    from logic.data_providers.universe_builder import UniverseBuilder
    grand_total = 0
    grand_t0    = time.time()
    for i, date in enumerate(trading_days):
        log(f'\n>>> [{i+1}/{len(trading_days)}] {date}')
        try:
            t0           = time.time()
            valid_stocks = UniverseBuilder(date).build()
            log(f'  粗筛: {len(valid_stocks)}只 ({time.time()-t0:.1f}s)')
        except Exception as e:
            log(f'  ❌ 粗筛失败: {e}，跳过')
            continue
        if not valid_stocks:
            log('  ⚠️ 粗筛后无标的，跳过')
            continue
        download_one_day(date, valid_stocks, xtdata, full=False, do_verify=True)
        grand_total   += len(valid_stocks)
        total_elapsed  = time.time() - grand_t0
        remaining      = (total_elapsed / (i + 1)) * (len(trading_days) - i - 1)
        log(f'  总进度: {i+1}/{len(trading_days)}天 | '
            f'总耗时{total_elapsed:.0f}s | 预计剩{remaining:.0f}s ({remaining/60:.1f}min)')
        if i < len(trading_days) - 1:
            time.sleep(DAY_SLEEP)
    log(f'\n✅ 完成! 处理 {len(trading_days)}天，投递 {grand_total}只次Tick指令')


if __name__ == '__main__':
    main()
