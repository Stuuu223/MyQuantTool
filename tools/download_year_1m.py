# -*- coding: utf-8 -*-
"""
【CTO V158 后台智能下载器】下载近一年全量1m分K数据

策略：
1. 从20260313往前推一年开始下载
2. 连续20个交易日无法下载才停止（证明榨干服务器数据）
3. 后台运行，定期上报进度

用法：
    python tools/download_year_1m.py
"""
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from xtquant import xtdata

# 参数配置
END_DATE = '20260313'
START_DATE = '20250314'  # 一年前
CONSECUTIVE_FAIL_LIMIT = 20  # 连续失败天数阈值
BATCH_SIZE = 200  # 每批下载股票数
BATCH_SLEEP = 3.0  # 批次间隔秒数


def log(msg: str) -> None:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] {msg}', flush=True)


def get_all_stocks() -> list:
    """获取全市场股票列表"""
    try:
        stocks = xtdata.get_stock_list_in_sector('沪深A股')
        log(f"获取全市场股票: {len(stocks)}只")
        return stocks
    except Exception as e:
        log(f"获取股票列表失败: {e}")
        return []


def get_trading_days(start_date: str, end_date: str) -> list:
    """获取交易日列表（简化版，用自然日去周末）"""
    s = datetime.strptime(start_date, '%Y%m%d')
    e = datetime.strptime(end_date, '%Y%m%d')
    days, cur = [], s
    while cur <= e:
        if cur.weekday() < 5:
            days.append(cur.strftime('%Y%m%d'))
        cur += timedelta(days=1)
    return days


def download_1m_for_date(stocks: list, date: str) -> tuple:
    """
    下载指定日期的1m分K数据
    返回: (成功数, 失败数)
    """
    success_count = 0
    fail_count = 0
    
    # 分批下载
    for i in range(0, len(stocks), BATCH_SIZE):
        batch = stocks[i:i + BATCH_SIZE]
        try:
            # 投递下载任务
            for stock in batch:
                try:
                    xtdata.download_history_data(
                        stock,
                        period='1m',
                        start_time=date,
                        end_time=date
                    )
                    success_count += 1
                except Exception:
                    fail_count += 1
            
            # 批次间隔
            time.sleep(BATCH_SLEEP)
            
        except Exception as e:
            log(f"批次下载失败 {date}: {e}")
            fail_count += len(batch)
    
    return success_count, fail_count


def verify_date_has_data(stocks: list, date: str, sample_size: int = 50) -> bool:
    """
    验证指定日期是否有数据
    抽样检查sample_size只股票
    """
    import random
    sample = random.sample(stocks, min(sample_size, len(stocks)))
    
    has_data_count = 0
    for stock in sample:
        try:
            data = xtdata.get_local_data(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=[stock],
                period='1m',
                start_time=date,
                end_time=date
            )
            if data and stock in data and data[stock] is not None and len(data[stock]) > 0:
                has_data_count += 1
        except Exception:
            pass
    
    # 如果抽样中超过10%有数据，认为该日期有数据
    return has_data_count > sample_size * 0.1


def main():
    log("=" * 60)
    log("【CTO V158 后台智能下载器】下载近一年全量1m分K数据")
    log("=" * 60)
    
    # 获取股票列表
    stocks = get_all_stocks()
    if not stocks:
        log("错误: 无法获取股票列表")
        return
    
    # 获取交易日列表
    trading_days = get_trading_days(START_DATE, END_DATE)
    log(f"待下载交易日: {len(trading_days)}天 ({START_DATE} ~ {END_DATE})")
    
    # 统计变量
    total_success = 0
    total_fail = 0
    consecutive_fails = 0
    dates_with_data = []
    dates_without_data = []
    
    # 从最新日期往前下载
    for date in reversed(trading_days):
        log(f"\n>>> 处理日期: {date}")
        
        # 检查是否已有数据
        if verify_date_has_data(stocks, date):
            log(f"  [已有数据] {date} 跳过下载")
            dates_with_data.append(date)
            consecutive_fails = 0
            continue
        
        # 下载数据
        success, fail = download_1m_for_date(stocks, date)
        total_success += success
        total_fail += fail
        
        # 等待数据落盘
        time.sleep(5)
        
        # 验证下载结果
        if verify_date_has_data(stocks, date):
            log(f"  [下载成功] {date} 成功:{success} 失败:{fail}")
            dates_with_data.append(date)
            consecutive_fails = 0
        else:
            log(f"  [下载失败] {date} 无数据返回")
            dates_without_data.append(date)
            consecutive_fails += 1
            
            # 检查是否达到连续失败阈值
            if consecutive_fails >= CONSECUTIVE_FAIL_LIMIT:
                log(f"\n*** 连续{consecutive_fails}天无数据，服务器数据已榨干！***")
                break
    
    # 最终报告
    log("\n" + "=" * 60)
    log("【下载完成报告】")
    log("=" * 60)
    log(f"总交易日: {len(trading_days)}天")
    log(f"有数据日期: {len(dates_with_data)}天")
    log(f"无数据日期: {len(dates_without_data)}天")
    log(f"连续失败天数: {consecutive_fails}天")
    log(f"总成功数: {total_success}")
    log(f"总失败数: {total_fail}")
    
    if dates_with_data:
        log(f"\n最早有数据日期: {min(dates_with_data)}")
        log(f"最新有数据日期: {max(dates_with_data)}")
    
    # 保存报告
    report_path = Path(__file__).parent.parent / "data" / "research_lab" / "1m_download_report.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("【CTO V158 1m分K下载报告】\n")
        f.write(f"下载时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总交易日: {len(trading_days)}天\n")
        f.write(f"有数据日期: {len(dates_with_data)}天\n")
        f.write(f"无数据日期: {len(dates_without_data)}天\n")
        f.write(f"连续失败天数: {consecutive_fails}天\n")
        f.write(f"最早有数据日期: {min(dates_with_data) if dates_with_data else 'N/A'}\n")
        f.write(f"最新有数据日期: {max(dates_with_data) if dates_with_data else 'N/A'}\n")
    
    log(f"\n报告已保存: {report_path}")


if __name__ == '__main__':
    main()
