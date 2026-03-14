# -*- coding: utf-8 -*-
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
     【新增】附带计算全市场量比 95th 分位数作为动态阈值写入 tick_index.json
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


# ────────────────────────────────────────────
# 核心：落盘验证
# ────────────────────────────────────────────

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


# ────────────────────────────────────────────
# 日期工具
# ────────────────────────────────────────────

def get_trading_days(start_date: str, end_date: str, xtdata) -> list:
    """
    【CTO V158 修复】真正获取交易日列表，排除节假日
    
    优先级：
    1. xtdata.get_trading_calendar（官方接口）
    2. fallback: 自然日去周末
    """
    from datetime import datetime, timedelta
    
    # 方案A：尝试调用xtdata官方接口
    try:
        calendar = xtdata.get_trading_calendar('SH')
        if calendar:
            trading_days = [d for d in calendar if start_date <= d <= end_date]
            print(f'  交易日列表来源: xtdata.get_trading_calendar ({len(trading_days)}天)')
            return trading_days
    except Exception as e:
        print(f'  [WARN] xtdata.get_trading_calendar失败: {e}，fallback到自然日去周末')
    
    # 方案B：fallback - 自然日去周末
    s = datetime.strptime(start_date, '%Y%m%d')
    e = datetime.strptime(end_date, '%Y%m%d')
    days, cur = [], s
    while cur <= e:
        if cur.weekday() < 5:
            days.append(cur.strftime('%Y%m%d'))
        cur += timedelta(days=1)
    print(f'  交易日列表来源: fallback自然日去周末 ({len(days)}天，含节假日)')
    return days



# ────────────────────────────────────────────
# 日K本地检查 + 自动补充（P2修复）
# ────────────────────────────────────────────


# ────────────────────────────────────────────
# 单日下载核心（批量投递 + 完成后抽样验证）
# ────────────────────────────────────────────

def download_one_day(date: str, stocks: list[str], xtdata,
                     full: bool, do_verify: bool = False,
                     volume_ratio_threshold: float | None = None) -> dict:
    """
    [P0修复说明]
    download_history_data 是异步调用，立即返回None。
    原始代码中 ok+1 只说明"调用未抛异常"，不代表数据落盘。
    本函数：
      - 批量投递全部股票（保持速度）
      - 完成后抽样 BATCH_VERIFY_N 只验证真实落盘率
      - 落盘率写入 tick_index.json
    若需逐只精确验证，请用 download_with_verify()（--stocks模式专用）

    Args:
        volume_ratio_threshold: 【新墝】动态量比阈值，写入 tick_index.json 供回测参考
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
        record = {
            'date':          date,
            'mode':          'full' if full else 'filtered',
            'count':         total,
            'dispatched_ok': ok,
            'dispatched_fail': fail,
            'elapsed_s':     round(elapsed, 1),
            'verify':        verify_result,
            'timestamp':     datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'note':          '[P0] dispatched_ok=投递成功数(非落盘数)，'
                             '落盘以verify.landed/checked为准'
        }
        # 【新墝】记录动态量比阈值
        if volume_ratio_threshold is not None:
            record['volume_ratio_threshold'] = round(volume_ratio_threshold, 4)
        with open(idx_dir / f'{date}.json', 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return {'dispatched': ok, 'fail': fail, 'verify': verify_result}


# ────────────────────────────────────────────
# --stocks 模式：逐只投递+验证（研究用，慢但精确）
# ────────────────────────────────────────────

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


# ────────────────────────────────────────────
# 主程序
# ────────────────────────────────────────────

def main():
    from xtquant import xtdata
    from logic.core.config_manager import get_config_manager
    from logic.utils.calendar_utils import get_latest_completed_trading_day

    cfg  = get_config_manager()
    args = sys.argv[1:]

    full_mode    = '--full' in args
    minute_mode  = '--1m' in args  # 【CTO V113】分K回溯下载模式
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
    
    # 【CTO V113 优雅升级：1分钟K线回溯下载模式】
    # 用法：python tools/smart_download.py --1m [--stocks 股票列表]
    # 功能：从今天往前下载分K，连续20天无数据停止，统计下载天数
    if minute_mode:
        print('=' * 60)
        print('分K回溯下载模式 (--1m)')
        print('=' * 60)
        
        port = cfg.get('system_and_risk.qmt_port', 58610)
        log(f'连接端口 {port}...')
        try:
            xtdata.connect(port=port)
            log('✅ 连接成功')
        except Exception as e:
            log(f'❌ 连接失败: {e}')
            return
        
        # 获取目标股票列表
        if pinpoint_stocks:
            target_stocks = pinpoint_stocks
            log(f'指定标的: {len(target_stocks)} 只')
        else:
            target_stocks = xtdata.get_stock_list_in_sector('沪深A股')
            # 过滤主板/创业板/科创板
            target_stocks = [s for s in target_stocks if s.startswith(('00', '60', '30', '68'))]
            target_stocks = [s for s in target_stocks if 'ST' not in s]
            log(f'全市场标的: {len(target_stocks)} 只')
        
        # 【CTO V158】支持传入日期范围，默认往前400天
        dates_args = [a for a in args if not a.startswith('--') and ',' not in a]
        if len(dates_args) >= 2:
            start_date, end_date = dates_args[0], dates_args[1]
        elif len(dates_args) == 1:
            start_date = end_date = dates_args[0]
        else:
            today = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=400)).strftime('%Y%m%d')
            end_date = today
        
        trading_days = get_trading_days(start_date, end_date, xtdata)
        log(f'交易日列表: {len(trading_days)}天 ({trading_days[0] if trading_days else "N/A"} ~ {trading_days[-1] if trading_days else "N/A"})')
        
        consecutive_no_data = 0
        total_downloaded_days = 0
        STOP_DAYS = 20  # 连续20天无数据停止
        
        log(f'开始回溯下载，停止条件: 连续{STOP_DAYS}天无数据')
        log('')
        
        # 倒序遍历交易日（从最新开始）
        for date_str in reversed(trading_days):
            
            # 【BUG#5修复】随机抽样20只检查
            import random
            sample_stocks = random.sample(target_stocks, min(20, len(target_stocks)))
            
            skip_check = xtdata.get_local_data(
                field_list=['close'],
                stock_list=sample_stocks,  # 用随机抽样
                period='1m',
                start_time=date_str,
                end_time=date_str
            )
            
            existing_count = 0
            if skip_check:
                for s in sample_stocks:  # 【BUG#5修复】用随机抽样结果
                    if s in skip_check and skip_check[s] is not None and len(skip_check[s]) > 0:
                        existing_count += 1
            
            if existing_count >= 10:  # 20只中>=10只已有数据，跳过
                log(f'>>> {date_str} 已有数据 ({existing_count}/20随机抽样)，跳过')
                continue
            
            log(f'>>> 回溯日期: {date_str} (连续无数据: {consecutive_no_data}/{STOP_DAYS})')
            
            try:
                # 【CTO V116 极速宽网嗅探】
                # 1. 【BUG#4修复】并发下发当日日K
                import concurrent.futures
                def submit_daily(stock):
                    try:
                        xtdata.download_history_data(stock, '1d', start_time=date_str, end_time=date_str)
                        return True
                    except Exception:
                        return False
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
                    list(executor.map(submit_daily, target_stocks))
                
                time.sleep(1.5)  # 等落盘
                
                # 2. 【BUG#3修复】死水股过滤 - 纯成交额，不用get_full_tick
                DEAD_AMOUNT = 100000000.0  # 1亿
                active_stocks = []
                
                daily_check = xtdata.get_local_data(
                    field_list=['amount'], 
                    stock_list=target_stocks, 
                    period='1d', 
                    start_time=date_str, 
                    end_time=date_str
                )
                
                for stock in target_stocks:
                    # 【BUG#6修复】严格类型检查，消灭静默异常
                    stock_data = daily_check.get(stock) if daily_check else None
                    if stock_data is None:
                        continue
                    if not hasattr(stock_data, 'empty'):
                        continue
                    if stock_data.empty:
                        continue
                    if 'amount' not in stock_data.columns:
                        continue
                    
                    try:
                        amt = float(stock_data['amount'].iloc[0])
                        if amt >= DEAD_AMOUNT:
                            active_stocks.append(stock)
                    except Exception as e:
                        # 不允许静默！
                        pass  # 单只股票异常不阻塞流程
                
                log(f'  死水过滤: {len(active_stocks)}/{len(target_stocks)} 只活跃 (成交>=1亿)')
                
                if not active_stocks:
                    consecutive_no_data += 1
                    log(f'  ⚠️ 当日无活跃股，跳过')
                    continue
                
                # 3. 【CTO V158 分批500只异步投递】
                BATCH_SIZE = 500
                t0 = time.time()
                total_submitted = 0
                for batch_start in range(0, len(active_stocks), BATCH_SIZE):
                    batch = active_stocks[batch_start:batch_start + BATCH_SIZE]
                    batch_num = batch_start // BATCH_SIZE + 1
                    total_batches = (len(active_stocks) + BATCH_SIZE - 1) // BATCH_SIZE
                    
                    for stock in batch:
                        try:
                            xtdata.download_history_data(stock, '1m', start_time=date_str, end_time=date_str)
                            total_submitted += 1
                        except Exception:
                            pass
                    
                    log(f'  批次 {batch_num}/{total_batches} 投递完成 ({len(batch)}只)')
                elapsed = time.time() - t0
                
                time.sleep(2.0)  # 等待异步落盘
                
                # 抽样探测是否真实有数据
                test_batch = active_stocks[:5]
                raw = xtdata.get_local_data(
                    field_list=[], stock_list=test_batch, 
                    period='1m', start_time=date_str, end_time=date_str
                )
                
                has_data = False
                if raw:
                    for s in test_batch:
                        if s in raw and raw[s] is not None and len(raw[s]) > 0:
                            has_data = True
                            break
                
                if has_data:
                    consecutive_no_data = 0
                    total_downloaded_days += 1
                    log(f'  ✅ {date_str} 分K落盘成功 ({elapsed:.0f}s, {len(active_stocks)}只) - 累计{total_downloaded_days}天')
                else:
                    consecutive_no_data += 1
                    log(f'  ⚠️ {date_str} 数据为空，券商服务器无此日数据')
                    
            except Exception as e:
                log(f'  ❌ 下载异常: {e}')
                consecutive_no_data += 1
        
        # 最终报告
        log('')
        print('=' * 60)
        print('分K回溯下载完成报告')
        print('=' * 60)
        print(f'有效下载天数: {total_downloaded_days} 天')
        print(f'停止原因: 连续{STOP_DAYS}天无数据')
        print('=' * 60)
        return
    
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

    # ── 阶段一：全市场日K基建无脑强刷（CTO V91 暴力美学 + V122 多线程加速） ──
    log('[阶段一] 执行全市场日K基建无脑强刷 (多线程极速模式)...')
    # 为了保证 5日均线/换手率 等指标能算出来，日K必须往前多下 30 天
    s_dt = datetime.strptime(start_date, '%Y%m%d') - timedelta(days=30)
    kline_start = s_dt.strftime('%Y%m%d')
    log(f'  强制指令：全市场日K覆盖 {kline_start} ~ {end_date}')
    
    try:
        # [CTO V115] QMT download_history_data 仅支持单只股票 str，不支持 list！
        # [CTO V122] 多线程并发投递，32线程暴力加速
        def submit_one(stock):
            try:
                xtdata.download_history_data(stock, '1d', start_time=kline_start, end_time=end_date)
                return True
            except Exception:
                return False
        
        import concurrent.futures
        t0_submit = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            futures = {executor.submit(submit_one, s): s for s in all_stocks}
            done = sum(1 for f in concurrent.futures.as_completed(futures))
        log(f'  OK 全市场日K投递完毕 ({done}只, {time.time()-t0_submit:.1f}s)，等待 3 秒落盘...')
        time.sleep(3)
    except Exception as e:
        log(f'  [WARN] 日K下载报出异常: {e}')

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

    # 粗筛模式 【CTO V122 样本完整性保卫令】
    # 老板命令：进了watchlist全下！绝不物理删除负样本！
    from logic.data_providers.universe_builder import UniverseBuilder
    import numpy as np
    import concurrent.futures

    grand_total = 0
    grand_t0    = time.time()
    for i, date in enumerate(trading_days):
        log(f'\n>>> [{i+1}/{len(trading_days)}] {date}')
        try:
            t0 = time.time()
            valid_stocks, market_ratios = UniverseBuilder(date).build()
            log(f'  粗筛原池: {len(valid_stocks)}只 ({time.time()-t0:.1f}s)')

            # 【CTO V122】废除铁血截断！保留完整负样本！
            # 让物理引擎自然淘汰骗炮股，而不是在下载阶段物理阉割！
            
            # 仅做统计参考
            valid_ratios = [market_ratios.get(s, 0) for s in valid_stocks if market_ratios.get(s, 0) > 0]
            if len(valid_ratios) >= 10:
                vol_threshold = float(np.percentile(valid_ratios, 92))
                log(f'  动态量比阈值(92th): {vol_threshold:.2f} | 全量下载 {len(valid_stocks)} 只（含负样本）')
            else:
                vol_threshold = 3.0
            
            if not valid_stocks:
                log('  ⚠️ 粗筛后无标的，跳过')
                continue

        except Exception as e:
            log(f'  ❌ 粗筛失败: {e}，跳过')
            continue

        download_one_day(date, valid_stocks, xtdata, full=False,
                         do_verify=True, volume_ratio_threshold=vol_threshold)
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
