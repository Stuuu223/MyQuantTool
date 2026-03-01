#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BSON炸弹扫雷车 - Windows串行子进程隔离版

【设计原则】
  - 每只股票启动独立子进程调用 get_local_data(period='1d')
  - 父进程只观察子进程退出码，永不崩溃
  - Windows下 C++ abort() 退出码 = 3
  - 严禁使用 ProcessPoolExecutor（Windows+QMT子进程互斥，会卡死）
  - 串行逐只扫描，慢但稳，全市场约15-30分钟

【用法】
  python tools/find_bson_bomb.py

【输出】
  data/bson_blacklist.json

【关于探测日期】
  必须选一个「已确认完整下载过日K」的日期，否则本地无数据的股票
  会触发 QMT 网络请求阻塞，导致每只超时6秒，8小时跑不完。
  当前设定 PROBE_DATE = '20260214'（上上周五，三年日K已下载完毕）。
  超时 ≠ 炸弹，超时只是「该日无本地数据」，单独记录不加黑名单。

Version: 2.1.0 - 修正探测日期，超时不入黑名单
"""

import sys
import os
import json
import logging
import subprocess
import time

# Windows编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def _ensure_log_dir():
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs'
    )
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

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

# ── 崩溃码定义 ────────────────────────────────────────────────────────────────
# 只有以下退出码才是真正的 BSON 炸弹（C++层崩溃）：
#   3           - Windows abort()  / C++ assert 失败
#   134         - Linux SIGABRT
#   -1073741819 - Windows access violation (0xC0000005)
#   -1073740940 - Windows heap corruption (0xC0000374)
#   -1073740777 - Windows stack overflow
#   -1073741571 - Windows stack overflow alt
#   3221226505  - 0xC0000009 STATUS_INVALID_PARAMETER（无符号表示，Python会转成负数）
#
# 超时 ≠ 炸弹：超时只代表该日本地无数据，QMT在等网络，不应入黑名单
# rc==0  - 正常
# rc==2  - Python层异常（数据为空/KeyError），不是炸弹
CRASH_CODES = frozenset({
    3,
    134,
    -1073741819,
    -1073740940,
    -1073740777,
    -1073741571,
    -1073741787,  # 0xC0000009 有符号值
})

# ── 探测日期 ──────────────────────────────────────────────────────────────────
# 必须是「已完整下载过日K」的交易日。
# 用最近交易日风险：收盘后QMT可能尚未写入本地缓存，导致大量超时。
# 20260214 = 2026年2月14日（周六前的周五），三年日K已下载完毕，安全。
PROBE_DATE = '20260214'


def _probe_worker():
    """
    子进程入口：只试探一只股票在 PROBE_DATE 的1d日K。
    C++ abort 无法被Python捕获，会直接杀死本进程（这正是我们需要的）。
    Python层异常用 sys.exit(2) 标记（数据为空等，非炸弹）。
    """
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


def main():
    # 子进程模式
    if len(sys.argv) == 3:
        _probe_worker()
        return

    # ── 父进程主逻辑 ───────────────────────────────────────────────────────────
    try:
        from xtquant import xtdata
    except ImportError:
        logger.error('xtquant未安装或QMT未连接，无法扫雷')
        sys.exit(1)

    logger.info(f'💣 BSON扫雷车启动 | 探测日期: {PROBE_DATE} | PID: {os.getpid()}')
    logger.info('⚠️  串行模式，全市场约15-30分钟，请勿关闭窗口')
    logger.info(f'📌 超时 ≠ 炸弹：超时只代表该日无本地数据，不加黑名单')

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

    mine_list:    list[str] = []  # 真正的BSON炸弹（C++崩溃）
    timeout_list: list[str] = []  # 超时（无本地数据，不入黑名单）
    completed = 0
    t_start   = time.time()

    for stock in all_stocks:
        completed += 1
        try:
            result = subprocess.run(
                [python_exe, script_path, stock, PROBE_DATE],
                capture_output=True,
                timeout=8
            )
            rc = result.returncode

            if rc in CRASH_CODES:
                mine_list.append(stock)
                logger.error(f'💥 BSON炸弹: {stock} | exit={rc}')
            elif rc not in (0, 2):
                # 未知退出码，保守入黑名单并记录
                mine_list.append(stock)
                logger.warning(f'⚠️  未知退出码(入黑名单): {stock} | exit={rc}')
            # rc==0 正常，rc==2 数据为空，均跳过

        except subprocess.TimeoutExpired:
            # 超时 = 该日本地无数据，QMT等网络，不是炸弹
            timeout_list.append(stock)
            logger.debug(f'⏱ 超时(无本地数据，跳过): {stock}')
        except Exception as e:
            logger.warning(f'子进程启动失败 {stock}: {e}')

        # 进度+ETA，每200只打印一次
        if completed % 200 == 0:
            elapsed = time.time() - t_start
            rate    = completed / elapsed
            eta_min = (len(all_stocks) - completed) / rate / 60
            logger.info(
                f'📈 进度 {completed}/{len(all_stocks)} '
                f'| 💥炸弹: {len(mine_list)} '
                f'| ⏱超时(无数据): {len(timeout_list)} '
                f'| ETA: {eta_min:.1f}min'
            )

    # ── 写黑名单 ───────────────────────────────────────────────────────────────
    base_dir       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir       = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    blacklist_path = os.path.join(data_dir, 'bson_blacklist.json')

    payload = {
        'probe_date':    PROBE_DATE,
        'scan_time':     time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_scanned': completed,
        'mine_count':    len(mine_list),
        'timeout_count': len(timeout_list),
        'mines':         sorted(mine_list),
        'timeout_stocks': sorted(timeout_list),  # 仅记录，不是黑名单
    }
    with open(blacklist_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)

    elapsed_total = time.time() - t_start
    logger.info(
        f'\n{"="*60}\n'
        f'✅ 扫雷完成\n'
        f'   扫描总数:     {completed}\n'
        f'   💥BSON炸弹:  {len(mine_list)} 只（已写入黑名单）\n'
        f'   ⏱无本地数据: {len(timeout_list)} 只（超时，不入黑名单）\n'
        f'   总耗时:       {elapsed_total/60:.1f} 分钟\n'
        f'   黑名单路径:   {blacklist_path}\n'
        f'{"="*60}'
    )
    if mine_list:
        logger.info(f'炸弹列表({len(mine_list)}只): {mine_list}')


if __name__ == '__main__':
    main()
