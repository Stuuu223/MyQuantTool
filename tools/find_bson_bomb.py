#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BSON炸弹扫雷车 - Windows串行子进程隔离版 v2.2

【关键修复 v2.2】
  - capture_output=True 在 Windows 下遇到 C++ abort 时会拖死父进程的 pipe。
    改用 stdout=DEVNULL + stderr=DEVNULL，子进程输出直接丢弃，父进程不受累。
  - 黑名单写入改用 finally 块，任何情况下都能保存已扫结果。
  - 探测日期改为 20260226（确认有本地日K的交易日）。
  - 超时 ≠ 炸弹，超时只记录不入黑名单。

【用法】
  python tools/find_bson_bomb.py

【输出】
  data/bson_blacklist.json

Version: 2.2.0
"""

import sys
import os
import json
import logging
import subprocess
import time
from subprocess import DEVNULL

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def _ensure_log_dir():
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(d, exist_ok=True)
    return d


_ensure_log_dir()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'logs', 'bson_sweep.log'),
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger('BSON_Sweeper')

# ── 崩溃码 ───────────────────────────────────────────────────────────────
# rc==0              正常
# rc==2              Python层异常（数据为空），不是炸弹
# rc==3              Windows abort() / C++ assert  ← 炸弹
# rc==134            Linux SIGABRT                 ← 炸弹
# rc==-1073741819    0xC0000005 access violation   ← 炸弹
# rc==-1073740940    0xC0000374 heap corruption     ← 炸弹
# rc==-1073740777    stack overflow                 ← 炸弹
# rc==-1073741571    stack overflow alt             ← 炸弹
# rc==-1073741787    0xC0000009 invalid parameter   ← 炸弹
# 超时               无本地数据，QMT等网络，不是炸弹
CRASH_CODES = frozenset({
    3, 134,
    -1073741819, -1073740940, -1073740777, -1073741571, -1073741787,
})

PROBE_DATE = '20260226'  # 已确认有本地日K的交易日


def _probe_worker():
    """  子进程入口：只试探一只股票在 PROBE_DATE 的1d日K """
    stock_code = sys.argv[1]
    date_str   = sys.argv[2]
    try:
        from xtquant import xtdata
        xtdata.get_local_data(
            field_list=['close'],
            stock_list=[stock_code],
            period='1d',
            start_time=date_str,
            end_time=date_str
        )
        sys.exit(0)
    except Exception:
        sys.exit(2)


def _write_blacklist(blacklist_path, completed, mine_list, timeout_list, all_count):
    """ 写黑名单 JSON（中途也能写，不丢已扫结果） """
    payload = {
        'probe_date':     PROBE_DATE,
        'scan_time':      time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_scanned':  completed,
        'total_stocks':   all_count,
        'mine_count':     len(mine_list),
        'timeout_count':  len(timeout_list),
        'mines':          sorted(mine_list),
        'timeout_stocks': sorted(timeout_list),
    }
    os.makedirs(os.path.dirname(blacklist_path), exist_ok=True)
    with open(blacklist_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)


def main():
    if len(sys.argv) == 3:
        _probe_worker()
        return

    try:
        from xtquant import xtdata
    except ImportError:
        logger.error('xtquant未安装或QMT未连接')
        sys.exit(1)

    logger.info(f'💣 BSON扫雷车启动 v2.2 | 探测日期: {PROBE_DATE} | PID: {os.getpid()}')
    logger.info('🔧 修复: 用DEVNULL替代capture_output，父进程不再被C++abort拖死')
    logger.info('💾 中途定期写黑名单，中断也不丢已扫结果')

    try:
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    except Exception as e:
        logger.error(f'获取股票列表失败: {e}')
        sys.exit(1)

    if not all_stocks:
        logger.error('股票列表为空')
        sys.exit(1)

    logger.info(f'🎯 全市场 {len(all_stocks)} 只股票待扫描')

    python_exe  = sys.executable
    script_path = os.path.abspath(__file__)
    base_dir    = os.path.dirname(os.path.dirname(script_path))
    blacklist_path = os.path.join(base_dir, 'data', 'bson_blacklist.json')

    mine_list:    list[str] = []
    timeout_list: list[str] = []
    completed = 0
    t_start   = time.time()

    try:
        for stock in all_stocks:
            completed += 1
            try:
                result = subprocess.run(
                    [python_exe, script_path, stock, PROBE_DATE],
                    stdout=DEVNULL,   # ← 关键修复：不用pipe，父进程不被子进程死拖
                    stderr=DEVNULL,   # ← 同上
                    timeout=8
                )
                rc = result.returncode

                if rc in CRASH_CODES:
                    mine_list.append(stock)
                    logger.error(f'💥 BSON炸弹: {stock} | exit={rc}')
                elif rc not in (0, 2):
                    mine_list.append(stock)
                    logger.warning(f'⚠️  未知退出码(入黑名单): {stock} | exit={rc}')

            except subprocess.TimeoutExpired:
                timeout_list.append(stock)
                logger.debug(f'⏱ 超时(无本地数据): {stock}')
            except Exception as e:
                logger.warning(f'子进程启动失败 {stock}: {e}')

            # 进度报告 + 中途写黑名单（每200只）
            if completed % 200 == 0:
                elapsed = time.time() - t_start
                rate    = completed / elapsed
                eta_min = (len(all_stocks) - completed) / rate / 60
                logger.info(
                    f'📈 进度 {completed}/{len(all_stocks)} '
                    f'| 💥炸弹: {len(mine_list)} '
                    f'| ⏱超时: {len(timeout_list)} '
                    f'| ETA: {eta_min:.1f}min'
                )
                # 中途写黑名单，防止后面崩丢已扫结果
                _write_blacklist(blacklist_path, completed, mine_list, timeout_list, len(all_stocks))

    finally:
        # 不管是正常结束、中断还是崩溃，都写入已扫结果
        _write_blacklist(blacklist_path, completed, mine_list, timeout_list, len(all_stocks))
        elapsed_total = time.time() - t_start
        logger.info(
            f'\n{"="*60}\n'
            f'✅ 扫雷完成（或中断）\n'
            f'   扫描: {completed}/{len(all_stocks)}\n'
            f'   💥炸弹: {len(mine_list)}只（已写入黑名单）\n'
            f'   ⏱超时: {len(timeout_list)}只（无本地数据，不入黑名单）\n'
            f'   耗时: {elapsed_total/60:.1f}分钟\n'
            f'   黑名单: {blacklist_path}\n'
            f'{"="*60}'
        )


if __name__ == '__main__':
    main()
