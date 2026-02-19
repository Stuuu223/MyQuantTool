#!/usr/bin/env python3
"""
下载顽主杯Top150中缺失的股票Tick数据（迁移到TickProvider）

使用TickProvider统一封装类，不再直接导入xtdata
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 🔥 T4迁移：不再直接导入xtdata，改用TickProvider
# from xtquant import xtdatacenter as xtdc
# from xtquant import xtdata
from logic.data_providers.tick_provider import TickProvider, DownloadStatus
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def progress_callback(current: int, total: int, stock_code: str, result):
    """进度回调函数"""
    progress = current / total * 100
    status_icon = "✅" if result.status == DownloadStatus.SUCCESS else "❌"
    print(f"\r[{current}/{total}] {progress:.1f}% | {stock_code} {status_icon}", end='', flush=True)


def load_missing_stocks():
    """从缺失列表加载"""
    missing_file = PROJECT_ROOT / 'logs' / 'tick_download_failures_150.txt'
    if not missing_file.exists():
        print("❌ 未找到缺失列表，请先运行主下载脚本")
        print(f"   预期文件: {missing_file}")
        sys.exit(1)
    
    stocks = []
    with open(missing_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                # 格式: "股票名,代码.市场"
                if ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        stocks.append(parts[1])  # 取代码部分
                else:
                    stocks.append(line)
    
    return stocks


def main():
    print("=" * 70)
    print("🚀 顽主杯Top150缺失股票Tick数据下载")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔧 使用TickProvider统一封装类")
    print()
    
    # 加载缺失列表
    stocks = load_missing_stocks()
    print(f"📋 需要下载: {len(stocks)} 只股票")
    print()
    
    if not stocks:
        print("✅ 没有缺失的股票，无需下载")
        return
    
    # 🔥 T4迁移：使用TickProvider上下文管理器
    try:
        with TickProvider() as provider:
            if not provider.is_connected():
                print("❌ 连接失败，请检查QMT环境")
                sys.exit(1)
            
            print("✅ 成功连接到行情服务！")
            print()
            
            print("=" * 70)
            print("🚀 开始下载Tick数据...")
            print("=" * 70)
            print()
            
            start_time = time.time()
            
            # 使用TickProvider批量下载
            result = provider.download_ticks(
                stock_codes=stocks,
                start_date='20251115',
                end_date='20260213',
                progress_callback=progress_callback
            )
            
            print()  # 换行
            print()
            
            # 获取失败的股票
            fail_stocks = [r.stock_code for r in result.results if r.status != DownloadStatus.SUCCESS]
            
            # 打印统计
            print("=" * 70)
            print("📊 下载完成统计")
            print("=" * 70)
            print(f"总股票数: {len(stocks)}")
            print(f"成功: {result.success} 只 ({result.success/len(stocks)*100:.1f}%)")
            print(f"失败: {result.failed} 只 ({result.failed/len(stocks)*100:.1f}%)")
            print(f"总耗时: {(time.time() - start_time)/60:.1f} 分钟")
            
            if fail_stocks:
                print()
                print(f"❌ 失败股票 ({len(fail_stocks)} 只):")
                for code in fail_stocks:
                    print(f"  - {code}")
                
                # 更新失败列表
                fail_list_path = PROJECT_ROOT / 'logs' / 'tick_download_failures_150.txt'
                with open(fail_list_path, 'w', encoding='utf-8') as f:
                    for code in fail_stocks:
                        f.write(f"{code}\n")
                print(f"\n📝 已更新失败列表: {fail_list_path}")
            else:
                # 全部成功，删除失败列表
                fail_list_path = PROJECT_ROOT / 'logs' / 'tick_download_failures_150.txt'
                if fail_list_path.exists():
                    fail_list_path.unlink()
                    print("\n✅ 全部下载成功，已删除失败列表")
            
            print()
            print("=" * 70)
            print("🎉 任务完成！")
            print("=" * 70)
            
    except Exception as e:
        logger.error(f"下载过程出错: {e}")
        print(f"\n❌ 下载过程出错: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()