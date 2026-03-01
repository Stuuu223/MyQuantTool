#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BSON炸弹扫雷车 - Windows串行子进程隔离版

【设计原则】
  - 每只股票启动独立子进程调用 get_local_data(period='1d')
  - 父进程只观察子进程退出码，永不崩溃
  - Windows下 C++ abort() 退出码 = 3
  - 严禁使用 ProcessPoolExecutor（Windows+QMT子进程互斥，会卡死）
  - 串行逐只扫描，慢但稳，全市场约60-90分钟

【用法】
  python tools/find_bson_bomb.py

【输出】
  data/bson_blacklist.json

Version: 2.0.0 - 修正串行版，修复崩溃码判断
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
# Windows abort()       = 3
# Windows access viol.  = -1073741819 (0xC0000005)
# Windows HEAP corrupt  = -1073740940 (0xC0000374)
# Linux  SIGABRT        = 134
# returncode == 2       = Python层正常异常(数据为空/KeyError)，不是炸弹
# returncode == 0       = 正常
CRASH_CODES = frozenset({
    3,           # Windows abort()
    134,         # Linux SIGABRT
    -1073741819, # Windows access violation
    -1073740940, # Windows heap corruption
    -1073740777, # Windows stack overflow
    -1073741571, # Windows stack overflow alt
})


def _probe_worker():
    """
    子进程入口：只试探一只股票的1d日K，不做任何其他事
    argv: [script_path, stock_code, date_str, '--probe']
    """
    stock_code = sys.argv[1]
    date_str   = sys.argv[2]
    # 不捕获 C++ abort，它会直接杀死本进程
    # Python层异常用 sys.exit(2) 标记（非炸弹）
    try:
        from xtquant import xtdata
        xtdata.get_local_data(
            field_list=['close'],
            stock_list=[stock_code],
            period='1d',
            start_time=date_str,
            end_time=date_str
        )
        sys.exit(0)   # 正常
    except Exception:
        sys.exit(2)   # Python层异常，数据可能为空，不是炸弹


def _ensure_log_dir():
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs'
    )
    os.makedirs(log_dir, exist_ok=True)


def main():
    # 子进程模式：被父进程调用时执行
    if len(sys.argv) == 3:
        _probe_worker()
        return

    _ensure_log_dir()

    # ── 父进程主逻辑 ───────────────────────────────────────────────────────────
    try:
        from xtquant import xtdata
    except ImportError:
        logger.error('xtquant未安装或QMT未连接，无法扫雷')
        sys.exit(1)

    # 使用最近一个交易日（周五收盘）
    DATE = '20260228'
    logger.info(f'💣 BSON扫雷车启动 | 测试日期: {DATE} | PID: {os.getpid()}')
    logger.info('⚠️  串行模式，全市场约60-90分钟，请勿关闭窗口')

    try:
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    except Exception as e:
        logger.error(f'获取股票列表失败: {e}')
        sys.exit(1)

    if not all_stocks:
        logger.error('股票列表为空')
        sys.exit(1)

    logger.info(f'🎯 全市场 {len(all_stocks)} 只股票待扫描（沪深全覆盖，不跳过任何市场）')

    python_exe  = sys.executable
    script_path = os.path.abspath(__file__)

    mine_list:    list[str] = []
    timeout_list: list[str] = []
    completed = 0
    t_start   = time.time()

    for stock in all_stocks:
        completed += 1
        try:
            result = subprocess.run(
                [python_exe, script_path, stock, DATE],
                capture_output=True,
                timeout=6          # 单只超过6秒视为卡死，也是炸弹
            )
            rc = result.returncode

            if rc in CRASH_CODES:
                mine_list.append(stock)
                logger.error(f'💥 BSON炸弹: {stock} | exit={rc}')
            elif rc not in (0, 2):
                # 未知退出码，保守加入黑名单
                mine_list.append(stock)
                logger.warning(f'⚠️  未知退出码: {stock} | exit={rc}')
            # rc==0 正常，rc==2 数据为空，均不加黑名单

        except subprocess.TimeoutExpired:
            mine_list.append(stock)
            timeout_list.append(stock)
            logger.error(f'💥 超时卡死: {stock}')
        except Exception as e:
            logger.warning(f'子进程启动失败 {stock}: {e}')

        # 进度+ETA
        if completed % 200 == 0:
            elapsed = time.time() - t_start
            rate    = completed / elapsed
            eta_min = (len(all_stocks) - completed) / rate / 60
            logger.info(
                f'进度 {completed}/{len(all_stocks)} '
                f'| 炸弹: {len(mine_list)} '
                f'| 超时: {len(timeout_list)} '
                f'| ETA: {eta_min:.1f}min'
            )

    # ── 写黑名单 ───────────────────────────────────────────────────────────────
    base_dir       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir       = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    blacklist_path = os.path.join(data_dir, 'bson_blacklist.json')

    payload = {
        'scan_date':     DATE,
        'scan_time':     time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_scanned': completed,
        'mine_count':    len(mine_list),
        'timeout_count': len(timeout_list),
        'mines':         sorted(mine_list)
    }
    with open(blacklist_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)

    elapsed_total = time.time() - t_start
    logger.info(
        f'\n{"="*60}\n'
        f'✅ 扫雷完成\n'
        f'   扫描总数: {completed}\n'
        f'   BSON炸弹: {len(mine_list)}\n'
        f'   超时卡死: {len(timeout_list)}\n'
        f'   总耗时:   {elapsed_total/60:.1f} 分钟\n'
        f'   黑名单:   {blacklist_path}\n'
        f'{"="*60}'
    )
    if mine_list:
        logger.info(f'炸弹列表: {mine_list}')


if __name__ == '__main__':
    main()
