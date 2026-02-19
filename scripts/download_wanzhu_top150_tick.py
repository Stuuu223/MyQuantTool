#!/usr/bin/env python3
"""
顽主杯Top 150股票Tick数据下载（迁移到TickProvider）
下载2025-11-21至2026-02-13的Tick数据

使用TickProvider统一封装类，不再直接导入xtdata

环境要求:
1. 需要安装xtquant模块 (通常在venv_qmt虚拟环境中)
2. 需要有效的QMT VIP Token
3. QMT终端需要启动（或使用独立数据服务）

运行方式:
    python scripts/download_wanzhu_top150_tick.py
"""
import sys
import csv
import time
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 🔥 T4迁移：不再直接导入xtdata，改用TickProvider
# from xtquant import xtdatacenter as xtdc
# from xtquant import xtdata
from logic.data_providers.tick_provider import TickProvider, DownloadStatus
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def determine_market(code_str: str) -> str:
    """根据股票代码判断市场"""
    code_str = str(code_str).strip()

    # 科创板（8开头，6位，例如688110）
    if code_str.startswith('688'):
        return 'SH'

    # 主板（6开头，6位，例如600000）
    if code_str.startswith('6'):
        return 'SH'

    # 创业板（3开头，6位，例如300058）
    if code_str.startswith('3'):
        return 'SZ'

    # 深圳主板（0开头，6位，例如000001）
    if code_str.startswith('0'):
        return 'SZ'

    # 北交所（8开头，但688开头已排除，例如830799）
    if code_str.startswith('8'):
        return 'BJ'

    # 默认规则：根据代码长度判断
    if len(code_str) == 6:
        if code_str[0] in ['6', '9']:
            return 'SH'
        else:
            return 'SZ'

    # 其他情况，根据第一位判断
    if code_str[0] in ['6', '9']:
        return 'SH'
    else:
        return 'SZ'


def pad_stock_code(code: str) -> str:
    """补全股票代码到6位"""
    code_str = str(code).strip()
    return code_str.zfill(6)


def load_stock_list(csv_path: Path) -> list:
    """从CSV文件加载股票列表"""
    stocks = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = pad_stock_code(row['code'])
            name = row['name']
            market = determine_market(code)
            stocks.append({
                'code': code,
                'name': name,
                'market': market
            })
    return stocks


def progress_callback(current: int, total: int, stock_code: str, result):
    """进度回调函数"""
    progress = current / total * 100
    status_icon = "✅" if result.status == DownloadStatus.SUCCESS else "❌"
    print(f"\r[{current}/{total}] {progress:.1f}% | {stock_code} {status_icon}", end='', flush=True)


def download_tick_batch(stocks: list, start_date: str, end_date: str):
    """批量下载Tick数据（使用TickProvider）"""
    
    print(f"=" * 80)
    print(f"📥 下载顽主杯Top 150股票Tick数据")
    print(f"=" * 80)
    print(f"\n股票数: {len(stocks)}")
    print(f"日期范围: {start_date} 至 {end_date}")
    print(f"\n🔧 使用TickProvider统一封装类")

    logger.info(f"开始下载Top 150股票Tick数据，共{len(stocks)}只")

    # 🔥 T4迁移：使用TickProvider上下文管理器
    try:
        with TickProvider() as provider:
            if not provider.is_connected():
                print("❌ 连接失败，请检查QMT环境")
                logger.error("TickProvider连接失败")
                return
            
            print("✅ 成功连接到行情服务！")
            logger.info("成功连接到行情服务")
            
            # 转换股票代码为QMT格式
            qmt_codes = [f"{stock['code']}.{stock['market']}" for stock in stocks]
            
            # 标准化日期格式
            start = start_date.replace('-', '')
            end = end_date.replace('-', '')
            
            print(f"\n{'=' * 80}")
            print(f"🚀 开始下载Tick数据...")
            print(f"{'=' * 80}\n")
            
            start_time_total = time.time()
            
            # 使用TickProvider批量下载
            result = provider.download_ticks(
                stock_codes=qmt_codes,
                start_date=start,
                end_date=end,
                progress_callback=progress_callback
            )
            
            print()  # 换行
            
            # 统计失败的股票
            fail_stocks = []
            for r in result.results:
                if r.status != DownloadStatus.SUCCESS:
                    # 找到对应的股票信息
                    for stock in stocks:
                        if f"{stock['code']}.{stock['market']}" == r.stock_code:
                            fail_stocks.append(stock)
                            break
            
            # 打印统计
            print(f"\n{'=' * 80}")
            print(f"📊 下载完成统计")
            print(f"{'=' * 80}")
            print(f"总股票数: {len(stocks)}")
            print(f"成功: {result.success} 只 ({result.success/len(stocks)*100:.1f}%)")
            print(f"失败: {result.failed} 只 ({result.failed/len(stocks)*100:.1f}%)")
            print(f"总耗时: {(time.time() - start_time_total)/60:.1f} 分钟")

            if fail_stocks:
                print(f"\n❌ 失败股票列表:")
                for stock in fail_stocks:
                    qmt_code = f"{stock['code']}.{stock['market']}"
                    print(f"  - {stock['name']} ({qmt_code})")

                # 保存失败列表
                fail_list_path = PROJECT_ROOT / 'logs' / 'tick_download_failures_150.txt'
                fail_list_path.parent.mkdir(parents=True, exist_ok=True)
                with open(fail_list_path, 'w', encoding='utf-8') as f:
                    for stock in fail_stocks:
                        qmt_code = f"{stock['code']}.{stock['market']}"
                        f.write(f"{stock['name']},{qmt_code}\n")
                print(f"\n📝 失败列表已保存: {fail_list_path}")
            
            logger.info(f"下载完成: 成功{result.success}只, 失败{result.failed}只")
            
    except Exception as e:
        logger.error(f"下载过程出错: {e}")
        print(f"\n❌ 下载过程出错: {e}")
        return
    
    print(f"\n{'=' * 80}")
    print(f"🎉 任务完成！数据已保存到本地。")
    print(f"{'=' * 80}")


def main():
    """主函数"""
    # 设置日志
    log_file = PROJECT_ROOT / 'logs' / 'tick_download_150.log'
    log_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"📝 日志文件: {log_file}\n")

    # 读取股票列表
    csv_path = PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv'

    if not csv_path.exists():
        print(f"❌ 股票列表不存在: {csv_path}")
        logger.error(f"股票列表不存在: {csv_path}")
        return

    stocks = load_stock_list(csv_path)

    print(f"\n✅ 成功加载 {len(stocks)} 只股票")
    print(f"上海市场: {sum(1 for s in stocks if s['market'] == 'SH')} 只")
    print(f"深圳市场: {sum(1 for s in stocks if s['market'] == 'SZ')} 只")
    print(f"北京市场: {sum(1 for s in stocks if s['market'] == 'BJ')} 只")
    
    # 显示使用的下载方式
    print(f"\n🔧 下载方式: TickProvider统一封装类")
    print(f"   - 自动管理xtdata连接")
    print(f"   - 内置重试机制")
    print(f"   - 自动限流控制")

    # 开始下载 - 日期范围: 2025-11-15 至 2026-02-13
    download_tick_batch(
        stocks,
        start_date='2025-11-15',
        end_date='2026-02-13'
    )


if __name__ == '__main__':
    main()