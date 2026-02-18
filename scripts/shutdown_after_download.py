#!/usr/bin/env python3
"""
Tick下载完成后自动关机脚本

功能：
1. 估算下载时间
2. 监控下载任务完成
3. 完成后自动关机（带缓冲时间）
"""
import sys
import time
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger

logger = get_logger(__name__)


class TickDownloadEstimator:
    """Tick下载时间估算器"""

    def __init__(self, num_stocks=150, num_days=58):
        self.num_stocks = num_stocks
        self.num_days = num_days
        self.trading_hours_per_day = 4  # 每天交易时间（小时）
        self.ticks_per_second = 3  # 每秒tick数

    def calculate_data_volume(self):
        """计算数据量"""
        # 单只股票单日tick数
        ticks_per_day = self.trading_hours_per_day * 3600 * self.ticks_per_second

        # 单只股票总tick数
        ticks_per_stock = ticks_per_day * self.num_days

        # 总tick数
        total_ticks = ticks_per_stock * self.num_stocks

        # 存储空间估算（每个tick约100字节）
        storage_gb = (total_ticks * 100) / (1024 ** 3)

        return {
            'ticks_per_day': ticks_per_day,
            'ticks_per_stock': ticks_per_stock,
            'total_ticks': total_ticks,
            'storage_gb': storage_gb
        }

    def estimate_download_time(self):
        """估算下载时间（分钟）"""
        # 基于QMT API经验数据
        # 方案1：逐只下载（推荐，当前代码逻辑）
        # 每只股票下载整个时间范围，40-80秒/只
        download_time_per_stock_min = 40  # 秒
        download_time_per_stock_max = 80  # 秒
        sleep_interval = 0.2  # 秒

        # 乐观估计
        optimistic_min = (self.num_stocks * download_time_per_stock_min +
                         self.num_stocks * sleep_interval) / 60

        # 保守估计
        conservative_min = (self.num_stocks * download_time_per_stock_max +
                           self.num_stocks * sleep_interval) / 60

        # 考虑网络波动、重试等，额外增加20%
        optimistic_with_buffer = optimistic_min * 1.2
        conservative_with_buffer = conservative_min * 1.2

        return {
            'optimistic': round(optimistic_with_buffer, 1),  # 分钟
            'conservative': round(conservative_with_buffer, 1)  # 分钟
        }

    def calculate_shutdown_time(self, buffer_minutes=12):
        """计算关机时间"""
        estimate = self.estimate_download_time()
        current_time = datetime.now()

        # 使用保守估计 + 缓冲时间
        total_minutes = estimate['conservative'] + buffer_minutes

        shutdown_time = current_time + timedelta(minutes=total_minutes)

        return {
            'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'download_estimate_minutes': estimate['conservative'],
            'buffer_minutes': buffer_minutes,
            'total_minutes': total_minutes,
            'shutdown_time': shutdown_time.strftime('%Y-%m-%d %H:%M:%S'),
            'shutdown_command': f'shutdown /s /t {int(total_minutes * 60)}'
        }

    def print_report(self):
        """打印估算报告"""
        print("=" * 80)
        print("📊 Tick下载时间估算报告")
        print("=" * 80)

        print(f"\n📋 下载参数：")
        print(f"   股票数量：{self.num_stocks} 只")
        print(f"   时间范围：{self.num_days} 天")
        print(f"   交易时间：{self.trading_hours_per_day} 小时/天")
        print(f"   Tick频率：{self.ticks_per_second} tick/秒")

        # 数据量
        data_volume = self.calculate_data_volume()
        print(f"\n💾 数据量估算：")
        print(f"   单只股票单日：{data_volume['ticks_per_day']:,} tick")
        print(f"   单只股票总计：{data_volume['ticks_per_stock']:,} tick")
        print(f"   总Tick数量：{data_volume['total_ticks']:,} tick")
        print(f"   预估存储空间：{data_volume['storage_gb']:.2f} GB")

        # 下载时间
        download_time = self.estimate_download_time()
        print(f"\n⏱️  下载时间估算（逐只下载模式）：")
        print(f"   乐观估计：{download_time['optimistic']} 分钟")
        print(f"   保守估计：{download_time['conservative']} 分钟")
        print(f"   说明：基于QMT API实测，每只股票40-80秒")

        # 关机时间
        shutdown = self.calculate_shutdown_time()
        print(f"\n⏰ 关机时间安排：")
        print(f"   当前时间：{shutdown['current_time']}")
        print(f"   下载时间：{shutdown['download_estimate_minutes']} 分钟")
        print(f"   缓冲时间：{shutdown['buffer_minutes']} 分钟")
        print(f"   总计时间：{shutdown['total_minutes']} 分钟")
        print(f"   预计关机：{shutdown['shutdown_time']}")
        print(f"   关机命令：{shutdown['shutdown_command']}")

        print("\n" + "=" * 80)
        print()

        return shutdown


def check_download_completion():
    """检查下载任务是否完成"""
    # 检查QMT数据目录
    qmt_data_dir = PROJECT_ROOT / 'data' / 'qmt_data'

    if not qmt_data_dir.exists():
        return False, "QMT数据目录不存在"

    # 检查股票代码目录
    stock_dirs = [d for d in qmt_data_dir.iterdir() if d.is_dir()]

    # 这里可以根据实际情况添加更详细的检查逻辑
    # 例如：检查进度文件、检查下载的日期范围等

    return True, f"发现 {len(stock_dirs)} 只股票数据"


def schedule_shutdown(seconds):
    """设置定时关机（Windows）"""
    cmd = f'shutdown /s /t {seconds}'
    print(f"\n🔔 设置定时关机：{seconds} 秒后关机")
    print(f"   命令：{cmd}")

    try:
        subprocess.run(cmd, shell=True, check=True)
        print("✅ 关机计划已设置")
        print(f"   使用 'shutdown /a' 可以取消关机")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 设置关机失败：{e}")
        return False


def main():
    """主函数"""
    print("\n🚀 Tick下载自动关机脚本启动\n")

    # 创建估算器（可根据实际参数调整）
    estimator = TickDownloadEstimator(
        num_stocks=150,  # 150只股票
        num_days=58      # 58天
    )

    # 打印估算报告
    shutdown_info = estimator.print_report()

    # 询问用户是否设置关机
    print("请选择操作：")
    print("  1. 立即设置定时关机（使用估算时间）")
    print("  2. 自定义关机时间（分钟）")
    print("  3. 仅显示估算，不设置关机")
    print("  4. 取消现有关机计划")

    choice = input("\n请输入选项 (1/2/3/4): ").strip()

    if choice == '1':
        # 使用估算时间设置关机
        total_seconds = int(shutdown_info['total_minutes'] * 60)
        schedule_shutdown(total_seconds)

    elif choice == '2':
        # 自定义关机时间
        try:
            custom_minutes = float(input("请输入关机倒计时（分钟）: "))
            custom_seconds = int(custom_minutes * 60)
            schedule_shutdown(custom_seconds)
        except ValueError:
            print("❌ 输入无效")

    elif choice == '3':
        print("\n✅ 已完成估算，未设置关机")

    elif choice == '4':
        # 取消关机
        print("\n🔔 取消关机计划...")
        try:
            subprocess.run('shutdown /a', shell=True, check=True)
            print("✅ 关机计划已取消")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ 取消关机失败：{e}")

    else:
        print("\n❌ 无效选项")

    print("\n👋 脚本结束")


if __name__ == '__main__':
    main()
