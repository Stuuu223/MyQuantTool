#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BSON炸弹扫雷车 - Windows串行子进程隔离版 v2.3

【关键修复历史】
  v2.0 - 串行版基础架构
  v2.1 - 探测日期改为20260226，超时不入黑名单
  v2.2 - 用DEVNULL防父进程被干死（错误：xtquant初始化时必须能写stdout）
  v2.3 - 回退到stdout管道，改用CREATE_NO_WINDOW隔离子进程控制台信号
         同时用 PIPE 会拖死父进程，所以不读内容，只用 wait()

【架构说明】
  父进程负责轮询，子进程负责单只探测。
  子进程输出直接打印到终端（不读取），避免pipe拖死父进程。
  C++ abort只杀子进程，父进程仅通过wait()观察退出码。

Version: 2.3.0
"""

import sys
import os
import json
import logging
import subprocess
import time

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0


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
# rc==0    正常
# rc==2    Python层异常（数据为空），不是炸弹
# rc==3    Windows abort() / C++ assert  ← 炸弹
# rc==134  Linux SIGABRT                 ← 炸弹
# 以下均为Windows结构化异常码（有符号）：
# rc==-1073741819  0xC0000005 access violation  ← 炸弹
# rc==3            abort()                      ← 炸弹
# rc==134          Linux SIGABRT                ← 炸弹
# rc==-1073741819  0xC0000005 access violation  ← 炸弹
# rc==-1073740940  0xC0000374 heap corruption   ← 炸弹
# rc==-1073740777  0xC0000409 stack buffer overrun ← 炸弹 (无符号3221226505)
# rc==-1073740791  0xC0000409 同上，另一种计算方式
# rc==-1073741571  0xC0000409 同上
# rc==-1073741787  0xC0000009 invalid param     ← 炸弹
# 超时  无本地数据，QMT等网络，不是炸弹
CRASH_CODES = frozenset({
      3, 134,
      -1073741819, -1073740940, -1073740777, -1073740791, -1073741571, -1073741787,
      3221226505,  # 0xC0000409 无符号格式
  })
PROBE_DATE = '20260226'  # 已确认有本地日K的交易日


def _probe_worker():
    """
    子进程入口：只试探一只股票在PROBE_DATE的1d日K。
    xtquant初始化时必须能写stdout，不能用DEVNULL。
    C++ abort直接杀死本进程，父进程通过wait()的退出码感知。
    """
    stock_code = sys.argv[1]
    date_str   = sys.argv[2]
    try:
        from xtquant import xtdata
        xtdata.enable_hello = False  # 隐藏连接提示信息
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

    logger.info(f'💣 BSON扫雷车启动 v2.3 | 探测日期: {PROBE_DATE} | PID: {os.getpid()}')
    logger.info('🔧 子进程不用DEVNULL，xtquant初始化必须可写stdout')
    logger.info('💾 每200只自动保存黑名单，中断不丢已扫结果')

    try:
        from xtquant import xtdata
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    except Exception as e:
        logger.error(f'获取股票列表失败: {e}')
        sys.exit(1)

    if not all_stocks:
        logger.error('股票列表为空')
        sys.exit(1)

    logger.info(f'🎯 全市场 {len(all_stocks)} 只股票待扫描')

    python_exe     = sys.executable
    script_path    = os.path.abspath(__file__)
    base_dir       = os.path.dirname(os.path.dirname(script_path))
    blacklist_path = os.path.join(base_dir, 'data', 'bson_blacklist.json')

    mine_list:    list[str] = []
    timeout_list: list[str] = []
    completed = 0
    t_start   = time.time()

    try:
        for stock in all_stocks:
            completed += 1
            try:
                # 【关键】不用capture_output也不用DEVNULL
                # 子进程 stdout/stderr 继承父进程（直打终端）
                # CREATE_NO_WINDOW防止Windows弹出崩溃对话框卡住父进程
                proc = subprocess.Popen(
                    [python_exe, script_path, stock, PROBE_DATE],
                    creationflags=CREATE_NO_WINDOW
                )
                try:
                    rc = proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                    timeout_list.append(stock)
                    logger.debug(f'⏱ 超时(无本地数据): {stock}')
                    continue

                if rc in CRASH_CODES:
                    mine_list.append(stock)
                    logger.error(f'💥 BSON炸弹: {stock} | exit={rc}')
                else:
                    # 无符号转有符号再比较（Windows退出码可能返回无符号）
                    rc_signed = rc if rc < 0x80000000 else rc - 0x100000000
                    if rc_signed in CRASH_CODES:
                        mine_list.append(stock)
                        logger.error(f'💥 BSON炸弹: {stock} | exit={rc}(signed={rc_signed})')
                    elif rc not in (0, 2):
                        # 未知退出码，先记录但不直接入黑名单，方便事后分析
                        logger.warning(f'❓ 未知退出码(仅记录，不入黑名单): {stock} | exit={rc}')

            except Exception as e:
                logger.warning(f'子进程启动失败 {stock}: {e}')

            if completed % 200 == 0:
                elapsed = time.time() - t_start
                rate    = completed / elapsed
                eta_min = (len(all_stocks) - completed) / rate / 60
                logger.info(
                    f'📈 进度 {completed}/{len(all_stocks)} '
                    f'| 💥炸弹: {len(mine_list)} '
                    f'| ❓未知码: 看日志 '
                    f'| ⏱超时: {len(timeout_list)} '
                    f'| ETA: {eta_min:.1f}min'
                )
                _write_blacklist(blacklist_path, completed, mine_list, timeout_list, len(all_stocks))

    finally:
        _write_blacklist(blacklist_path, completed, mine_list, timeout_list, len(all_stocks))
        elapsed_total = time.time() - t_start
        logger.info(
            f'\n{"="*60}\n'
            f'✅ 扫雷完成（或中断）\n'
            f'   扫描: {completed}/{len(all_stocks)}\n'
            f'   💥炸弹(入黑名单): {len(mine_list)}只\n'
            f'   ⏱超时(不入黑名单): {len(timeout_list)}只\n'
            f'   耗时: {elapsed_total/60:.1f}分钟\n'
            f'   黑名单: {blacklist_path}\n'
            f'{"="*60}'
        )


if __name__ == '__main__':
    main()
