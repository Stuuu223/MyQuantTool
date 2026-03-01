# -*- coding: utf-8 -*-
"""
CTO扫雷指挥部 - 多进程调度器

【CTO扫雷令】：
Boss的直觉才是对的！逃避永远解决不了底层数据损坏的问题！
既然确诊了有个别股票会导致QMT C++底层BSON断言崩溃，
那就写一个独立的扫雷车，把它们一只只揪出来封杀！

核心战术：
- 主进程（司令部）派出独立的子进程（排雷兵）
- 每个排雷兵只拿着1只股票去试探QMT的get_local_data
- 如果排雷兵安全回来了（exit 0），说明这只票没毒
- 如果排雷兵"光荣牺牲"了（进程返回负数），司令部记入黑名单

Author: CTO扫雷部队
Date: 2026-03-01
"""
import os
import sys
import json
import logging
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("MineSweeper")


def get_all_stocks():
    """获取全市场股票列表"""
    try:
        from xtquant import xtdata
        # 尝试连接QMT
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        return all_stocks
    except Exception as e:
        logger.error(f"❌ 无法连接QMT获取股票列表: {e}")
        return []


def run_sweeper(date: str, period: str = 'tick', max_workers: int = 5, target_market: str = 'all'):
    """
    启动扫雷行动
    
    Args:
        date: 测试日期 YYYYMMDD
        period: 数据周期 (tick/1d)
        max_workers: 最大并发数
        target_market: 目标市场 ('all'/'sh'/'sz')
    """
    logger.info("=" * 60)
    logger.info("💣 CTO QMT扫雷车启动！")
    logger.info(f"📅 测试日期: {date}")
    logger.info(f"📊 数据周期: {period}")
    logger.info(f"🎯 目标市场: {target_market}")
    logger.info("=" * 60)
    
    # 获取股票列表
    all_stocks = get_all_stocks()
    if not all_stocks:
        logger.error("❌ 无法获取股票列表，退出！")
        return
    
    # 按市场过滤
    if target_market == 'sh':
        target_stocks = [s for s in all_stocks if s.endswith('.SH')]
        logger.info(f"🎯 锁定上海市场，共需扫雷 {len(target_stocks)} 只股票...")
    elif target_market == 'sz':
        target_stocks = [s for s in all_stocks if s.endswith('.SZ')]
        logger.info(f"🎯 锁定深圳市场，共需扫雷 {len(target_stocks)} 只股票...")
    else:
        target_stocks = all_stocks
        logger.info(f"🎯 锁定全市场，共需扫雷 {len(target_stocks)} 只股票...")
    
    # 获取Python解释器路径（使用venv_qmt）
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python_exe = os.path.join(base_dir, 'venv_qmt', 'Scripts', 'python.exe')
    if not os.path.exists(python_exe):
        python_exe = sys.executable
        logger.warning(f"⚠️ venv_qmt Python不存在，使用系统Python: {python_exe}")
    
    worker_script = os.path.join(os.path.dirname(__file__), 'qmt_probe_worker.py')
    if not os.path.exists(worker_script):
        logger.error(f"❌ 探雷兵脚本不存在: {worker_script}")
        return
    
    # 结果统计
    safe_list = []
    mine_list = []
    empty_list = []
    error_list = []
    
    def dispatch_worker(stock):
        """派发探雷兵"""
        try:
            # 启动子进程，设置超时10秒
            # 如果C++崩溃，进程返回码会是负数（如 -1073740791）
            result = subprocess.run(
                [python_exe, worker_script, "--stock", stock, "--date", date, "--period", period],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=base_dir
            )
            return stock, result.returncode, result.stderr
        except subprocess.TimeoutExpired:
            return stock, 999, "超时"
        except Exception as e:
            return stock, 998, str(e)
    
    # 使用线程池并发派发子进程
    completed = 0
    start_time = datetime.now()
    
    logger.info(f"🚀 开始派发探雷兵（并发数: {max_workers}）...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(dispatch_worker, stock): stock for stock in target_stocks}
        
        for future in as_completed(futures):
            stock, code, stderr = future.result()
            completed += 1
            
            if code == 0:
                safe_list.append(stock)
            elif code == 2:
                empty_list.append(stock)
            elif code == 3:
                error_list.append(stock)
                logger.warning(f"⚠️ Python异常: {stock}")
            else:
                # 返回码是非正常值（负数或异常），说明引爆了C++ BSON，确认为地雷！
                mine_list.append(stock)
                logger.error(f"💥 发现地雷: {stock} (Exit Code: {code})")
            
            # 进度报告
            if completed % 50 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                speed = completed / elapsed if elapsed > 0 else 0
                eta = (len(target_stocks) - completed) / speed if speed > 0 else 0
                logger.info(f"👉 扫雷进度: {completed}/{len(target_stocks)} ({completed*100//len(target_stocks)}%) "
                          f"| 安全:{len(safe_list)} 空数据:{len(empty_list)} 地雷:{len(mine_list)} "
                          f"| 速度:{speed:.1f}只/秒 ETA:{eta/60:.1f}分钟")
    
    # 最终统计
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 60)
    logger.info("✅ 扫雷结束！")
    logger.info(f"   🟢 安全股票: {len(safe_list)}")
    logger.info(f"   ⚪ 无数据股票: {len(empty_list)}")
    logger.info(f"   🟡 Python异常: {len(error_list)}")
    logger.info(f"   💥 剧毒地雷: {len(mine_list)}")
    logger.info(f"   ⏱️ 总耗时: {elapsed:.1f}秒")
    logger.info("=" * 60)
    
    # 写入黑名单
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    blacklist_path = os.path.join(data_dir, 'qmt_blacklist.json')
    blacklist_data = {
        "generated_at": datetime.now().isoformat(),
        "test_date": date,
        "test_period": period,
        "total_scanned": len(target_stocks),
        "safe_count": len(safe_list),
        "mine_count": len(mine_list),
        "empty_count": len(empty_list),
        "mines": mine_list,
        "empty_stocks": empty_list,
        "error_stocks": error_list
    }
    
    with open(blacklist_path, 'w', encoding='utf-8') as f:
        json.dump(blacklist_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"💾 黑名单已落盘: {blacklist_path}")
    
    # 写入安全白名单
    whitelist_path = os.path.join(data_dir, 'qmt_whitelist.json')
    whitelist_data = {
        "generated_at": datetime.now().isoformat(),
        "test_date": date,
        "safe_stocks": safe_list
    }
    
    with open(whitelist_path, 'w', encoding='utf-8') as f:
        json.dump(whitelist_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"💾 白名单已落盘: {whitelist_path}")
    
    # 打印地雷列表
    if mine_list:
        logger.info("")
        logger.info("💣 地雷清单（共{}颗）:".format(len(mine_list)))
        for i, mine in enumerate(mine_list[:20], 1):
            logger.info(f"   {i}. {mine}")
        if len(mine_list) > 20:
            logger.info(f"   ... 还有 {len(mine_list)-20} 颗地雷，详见 qmt_blacklist.json")
    
    return mine_list


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CTO扫雷车 - 排查QMT有毒数据")
    parser.add_argument("--date", default="20260226", help="测试日期 YYYYMMDD")
    parser.add_argument("--period", default="tick", choices=['tick', '1d'], help="数据周期")
    parser.add_argument("--workers", type=int, default=5, help="并发数")
    parser.add_argument("--market", default="all", choices=['all', 'sh', 'sz'], help="目标市场")
    args = parser.parse_args()
    
    run_sweeper(date=args.date, period=args.period, max_workers=args.workers, target_market=args.market)
