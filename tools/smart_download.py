"""
智能下载器 - 日K本地读取 + Tick精准狙击
用法:
    python tools/smart_download.py                           # 默认上个交易日
    python tools/smart_download.py 20260303                  # 单日
    python tools/smart_download.py 20260206 20260303         # 日期范围(逐日粗筛)
    python tools/smart_download.py 20260206 20260303 --full  # 日期范围(全量补Tick,跳过粗筛)
设计原则:
  1. 日K直接读本地，不调用download
  2. 常规模式：逐日粗筛后下载Tick
  3. --full模式：全市场分批投递，200只/批，每批打印时间戳+进度
"""
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

BATCH_SIZE  = 200   # 每批投递数量（过大会QMT队列堡穴）
BATCH_SLEEP = 3     # 批间间隔科数
DAY_SLEEP   = 5     # 两个交易日之间间隔


def log(msg: str):
    """TODO: 带时间戳的输出，flush=True确保实时显示"""
    ts = datetime.now().strftime('%H:%M:%S')
    print(f'[{ts}] {msg}', flush=True)


def get_trading_days(start_date: str, end_date: str, xtdata) -> list[str]:
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
    # 兑底：排除周末
    s = datetime.strptime(start_date, '%Y%m%d')
    e = datetime.strptime(end_date, '%Y%m%d')
    days, cur = [], s
    while cur <= e:
        if cur.weekday() < 5:
            days.append(cur.strftime('%Y%m%d'))
        cur += timedelta(days=1)
    return days


def get_last_completed_day(xtdata, fallback: str) -> str:
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
                valid = sum(1 for s in ['000001.SZ', '600000.SH', '300001.SZ']
                            if s in sample and sample[s] is not None
                            and len(sample[s]) > 0)
                if valid >= 2:
                    return d
            except Exception:
                pass
        cur -= timedelta(days=1)
    return fallback


def download_batch(stocks: list[str], date: str, xtdata) -> bool:
    """对单批股票投递单日Tick指令，返回是否成功"""
    try:
        xtdata.download_history_data2(
            stock_list=stocks,
            period='tick',
            start_time=date,
            end_time=date,
        )
        return True
    except Exception as e:
        log(f'  download_history_data2异常: {e}，尝试单只备用')
        ok = 0
        for s in stocks:
            try:
                xtdata.download_history_data(s, 'tick', start_time=date, end_time=date)
                ok += 1
            except Exception:
                pass
        log(f'  单只备用结果: {ok}/{len(stocks)} 成功')
        return ok > 0


def download_one_day(date: str, stocks: list[str], xtdata, full: bool):
    """分批投递单个交易日Tick指令，每批打印进度"""
    total   = len(stocks)
    batches = [stocks[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    t0      = time.time()

    log(f'  {total}只股票 -> {len(batches)}批 ({BATCH_SIZE}只/批)')
    for bi, batch in enumerate(batches):
        bt0 = time.time()
        ok  = download_batch(batch, date, xtdata)
        elapsed = time.time() - bt0
        total_so_far = time.time() - t0
        status = '✅' if ok else '❌'
        log(f'  批[{bi+1}/{len(batches)}] {len(batch)}只 {status} '
            f'本批{elapsed:.1f}s | 天内共{total_so_far:.0f}s')
        if bi < len(batches) - 1:
            time.sleep(BATCH_SLEEP)

    # 更新 tick_index
    try:
        idx_dir = Path(__file__).parent.parent / 'data' / 'tick_index'
        idx_dir.mkdir(parents=True, exist_ok=True)
        with open(idx_dir / f'{date}.json', 'w', encoding='utf-8') as f:
            json.dump({
                'date':      date,
                'mode':      'full' if full else 'filtered',
                'count':     total,
                'batches':   len(batches),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def main():
    from xtquant import xtdata
    from logic.core.config_manager import get_config_manager
    from logic.utils.calendar_utils import get_latest_completed_trading_day

    cfg = get_config_manager()
    args = sys.argv[1:]
    full_mode  = '--full' in args
    dates_args = [a for a in args if not a.startswith('--')]

    if len(dates_args) >= 2:
        start_date, end_date = dates_args[0], dates_args[1]
    elif len(dates_args) == 1:
        start_date = end_date = dates_args[0]
    else:
        start_date = end_date = get_latest_completed_trading_day()

    print('=' * 52)
    mode_label = 'FULL全量' if full_mode else '粗筛'
    print(f'智能下载器 | {start_date}~{end_date} | {mode_label}')
    print('=' * 52)

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

    # ── 阶段一：检查本地日K ──
    log('[阶段一] 检查本地日K...')
    check_date = get_last_completed_day(xtdata, fallback=start_date)
    log(f'  检查日期: {check_date}')
    check_stocks = ['000001.SZ', '600000.SH', '300001.SZ']
    sample_data  = xtdata.get_local_data(
        field_list=['close'], stock_list=check_stocks,
        period='1d', start_time=check_date, end_time=check_date
    )
    valid_n = sum(1 for s in check_stocks
                  if s in sample_data and sample_data[s] is not None
                  and len(sample_data[s]) > 0)
    if valid_n >= 2:
        log(f'  ✅ 本地日K充足 ({valid_n}/3)，跳过下载')
    else:
        log(f'  ⚠️ 本地日K不足 ({valid_n}/3)，请在QMT客户端手动下载日K再运行')
        return

    trading_days = get_trading_days(start_date, end_date, xtdata)
    today = datetime.now().strftime('%Y%m%d')
    trading_days = [d for d in trading_days if d <= today]
    log(f'  交易日 ({len(trading_days)}天): {trading_days[0] if trading_days else "N/A"} ~ {trading_days[-1] if trading_days else "N/A"}')

    if not trading_days:
        log('❌ 没有可处理的交易日，退出')
        return

    if full_mode:
        # ── FULL模式：逐日分批投递 ──
        log(f'[阶段二] FULL模式 - {len(trading_days)}天 x {len(all_stocks)}只，分批{BATCH_SIZE}只/批')
        grand_t0 = time.time()
        for i, date in enumerate(trading_days):
            day_t0 = time.time()
            log(f'\n>>> [{i+1}/{len(trading_days)}] {date}')
            download_one_day(date, all_stocks, xtdata, full=True)
            day_elapsed   = time.time() - day_t0
            total_elapsed = time.time() - grand_t0
            remaining     = (total_elapsed / (i + 1)) * (len(trading_days) - i - 1)
            log(f'  天完成 {day_elapsed:.0f}s | 总耗时 {total_elapsed:.0f}s | '
                f'预计剩余 {remaining:.0f}s ({remaining/60:.1f}min)')
            if i < len(trading_days) - 1:
                time.sleep(DAY_SLEEP)
        total_elapsed = time.time() - grand_t0
        log(f'\n✅ FULL全量完成! 总耗时 {total_elapsed:.0f}s ({total_elapsed/60:.1f}min)')
        log(f'  Tick后台落盘中，请稍后验证覆盖率')

    else:
        # ── 常规模式：逐日粗筛 + Tick ──
        from logic.data_providers.universe_builder import UniverseBuilder
        total = 0
        for i, date in enumerate(trading_days):
            log(f'\n>>> [{i+1}/{len(trading_days)}] {date}')
            try:
                t0 = time.time()
                valid_stocks = UniverseBuilder(date).build()
                log(f'  粗筛: {len(valid_stocks)}只 ({time.time()-t0:.1f}s)')
            except Exception as e:
                log(f'  ❌ 粗筛失败: {e}，跳过')
                continue
            if not valid_stocks:
                log('  ⚠️ 粗筛后无标的，跳过')
                continue
            download_one_day(date, valid_stocks, xtdata, full=False)
            total += len(valid_stocks)
            if i < len(trading_days) - 1:
                time.sleep(1)
        log(f'\n✅ 完成! 处理 {len(trading_days)}天，投递 {total}只次Tick指令')


if __name__ == '__main__':
    main()
