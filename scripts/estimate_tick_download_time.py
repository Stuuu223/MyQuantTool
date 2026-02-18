#!/usr/bin/env python3
"""
Tick下载时间估算脚本（非交互式版本）
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timedelta


def estimate_tick_download():
    """估算tick下载时间"""
    # 参数
    num_stocks = 150  # 股票数量
    num_days = 58     # 时间范围（天）
    trading_hours_per_day = 4  # 每天交易时间（小时）
    ticks_per_second = 3  # 每秒tick数

    print("=" * 80)
    print("📊 Tick下载时间估算报告")
    print("=" * 80)

    print(f"\n📋 下载参数：")
    print(f"   股票数量：{num_stocks} 只")
    print(f"   时间范围：{num_days} 天 (2025-11-21 到 2026-02-13)")
    print(f"   交易时间：{trading_hours_per_day} 小时/天")
    print(f"   Tick频率：{ticks_per_second} tick/秒")

    # 数据量估算
    ticks_per_day = trading_hours_per_day * 3600 * ticks_per_second
    ticks_per_stock = ticks_per_day * num_days
    total_ticks = ticks_per_stock * num_stocks
    storage_gb = (total_ticks * 100) / (1024 ** 3)

    print(f"\n💾 数据量估算：")
    print(f"   单只股票单日：{ticks_per_day:,} tick")
    print(f"   单只股票总计：{ticks_per_stock:,} tick")
    print(f"   总Tick数量：{total_ticks:,} tick")
    print(f"   预估存储空间：{storage_gb:.2f} GB")

    # 下载时间估算（基于QMT API实测）
    # 每只股票下载整个时间范围：40-80秒
    download_time_per_stock_min = 40
    download_time_per_stock_max = 80
    sleep_interval = 0.2

    optimistic_min = (num_stocks * download_time_per_stock_min +
                     num_stocks * sleep_interval) / 60
    conservative_min = (num_stocks * download_time_per_stock_max +
                       num_stocks * sleep_interval) / 60

    # 增加20%缓冲
    optimistic_with_buffer = optimistic_min * 1.2
    conservative_with_buffer = conservative_min * 1.2

    print(f"\n⏱️  下载时间估算（逐只下载模式）：")
    print(f"   乐观估计：{optimistic_with_buffer:.1f} 分钟")
    print(f"   保守估计：{conservative_with_buffer:.1f} 分钟")
    print(f"   说明：基于QMT API实测，每只股票40-80秒")

    # 关机时间计算
    current_time = datetime.now()
    buffer_minutes = 12  # 缓冲时间
    total_minutes = conservative_with_buffer + buffer_minutes
    shutdown_time = current_time + timedelta(minutes=total_minutes)

    print(f"\n⏰ 关机时间安排：")
    print(f"   当前时间：{current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   下载时间：{conservative_with_buffer:.1f} 分钟")
    print(f"   缓冲时间：{buffer_minutes} 分钟")
    print(f"   总计时间：{total_minutes:.1f} 分钟")
    print(f"   预计关机：{shutdown_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   关机命令：shutdown /s /t {int(total_minutes * 60)}")

    print("\n" + "=" * 80)
    print()

    # 返回结果
    return {
        'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
        'download_time_minutes': round(conservative_with_buffer, 1),
        'buffer_minutes': buffer_minutes,
        'total_minutes': round(total_minutes, 1),
        'shutdown_time': shutdown_time.strftime('%Y-%m-%d %H:%M:%S'),
        'shutdown_command': f'shutdown /s /t {int(total_minutes * 60)}'
    }


if __name__ == '__main__':
    result = estimate_tick_download()
    print("\n✅ 估算完成")
    print(f"   关机命令可直接执行：{result['shutdown_command']}")
