#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BSON炸弹扫雷车 - 子进程物理隔离版

原理: 对每只股票启动独立子进程调用 get_local_data(period='1d')
     若子进程被C++ abort()杀死(退出码3/134), 则记入永久黑名单
     父进程永不崩溃, 只观察子进程退出码

使用方法:
    python tools/find_bson_bomb.py

输出:
    data/bson_blacklist.json

Version: 1.0.0
"""

import sys
import os
import json
import logging
import subprocess
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bson_sweep.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("BSON_Sweeper")

# Windows: abort()退出码=3, access_violation=-1073740791
# Linux:   SIGABRT=134 (128+6)
# Python正常异常退出: sys.exit(2) = 2
CRASH_CODES = {3, 134, -1073740777, -1073740791, -1073741819}


def _probe_worker():
    """
    子进程入口: 只试探一只股票, 不捕获C++ abort
    argv: [script, stock_code, date_str]
    """
    stock_code = sys.argv[1]
    date_str = sys.argv[2]
    try:
        from xtquant import xtdata
        start = (date_str[:4] + date_str[4:6] + date_str[6:8])
        data = xtdata.get_local_data(
            field_list=['close'],
            stock_list=[stock_code],
            period='1d',
            start_time=start,
            end_time=start
        )
        sys.exit(0)  # 正常
    except Exception:
        sys.exit(2)  # Python异常, 非炸弹


def main():
    # 子进程模式
    if len(sys.argv) == 3:
        _probe_worker()
        return

    # ── 父进程主逻辑 ──────────────────────────────────────────────
    try:
        from xtquant import xtdata
    except ImportError:
        logger.error("❌ xtquant未安装或QMT未连接, 无法扫雷")
        sys.exit(1)

    # 使用最近一个交易日(周五收盘)
    DATE = '20260228'
    logger.info(f"💣 启动BSON炸弹扫雷车 | 测试日期: {DATE} | Python: {sys.executable}")

    # 获取全市场(不只扫沪市!)
    try:
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    except Exception as e:
        logger.error(f"❌ 获取股票列表失败: {e}")
        sys.exit(1)

    logger.info(f"🎯 全市场共 {len(all_stocks)} 只股票待扫雷")

    python_exe = sys.executable
    script_path = os.path.abspath(__file__)

    mine_list: list[str] = []
    timeout_list: list[str] = []
    completed = 0
    start_time = time.time()

    for stock in all_stocks:
        completed += 1
        try:
            result = subprocess.run(
                [python_exe, script_path, stock, DATE],
                capture_output=True,
                timeout=5  # 5秒超时, 防止卡死
            )
            rc = result.returncode
            if rc in CRASH_CODES:
                mine_list.append(stock)
                logger.error(f"💥 BSON炸弹: {stock} | 退出码: {rc}")
            elif rc not in (0, 2):
                # 未知退出码, 保守加入黑名单
                mine_list.append(stock)
                logger.warning(f"⚠️  未知退出码: {stock} | 退出码: {rc}")
        except subprocess.TimeoutExpired:
            timeout_list.append(stock)
            mine_list.append(stock)
            logger.error(f"💥 超时卡死炸弹: {stock}")
        except Exception as e:
            logger.warning(f"子进程启动失败 {stock}: {e}")

        if completed % 200 == 0:
            elapsed = time.time() - start_time
            eta = (elapsed / completed) * (len(all_stocks) - completed)
            logger.info(
                f"进度: {completed}/{len(all_stocks)} "
                f"| 已发现炸弹: {len(mine_list)} "
                f"| 预计剩余: {eta/60:.1f}分钟"
            )

    # ── 落盘黑名单 ────────────────────────────────────────────────
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    blacklist_path = os.path.join(data_dir, 'bson_blacklist.json')

    blacklist = {
        "scan_date": DATE,
        "scan_time": time.strftime('%Y-%m-%d %H:%M:%S'),
        "total_scanned": completed,
        "mine_count": len(mine_list),
        "timeout_count": len(timeout_list),
        "mines": sorted(mine_list)
    }

    with open(blacklist_path, 'w', encoding='utf-8') as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=4)

    elapsed_total = time.time() - start_time
    logger.info(f"""\n{'='*60}
✅ 扫雷完成!
   扫描总数: {completed} 只
   BSON炸弹: {len(mine_list)} 只
   其中超时: {len(timeout_list)} 只
   总耗时:   {elapsed_total/60:.1f} 分钟
   黑名单:   {blacklist_path}
{'='*60}""")

    if mine_list:
        logger.info(f"炸弹股票列表: {mine_list}")


if __name__ == '__main__':
    main()
