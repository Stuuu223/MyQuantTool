#!/usr/bin/env python3
"""
一键启动tick下载并自动关机

使用方法：
1. 运行此脚本
2. 脚本会自动：
   - 显示时间估算
   - 启动tick下载任务
   - 设置定时关机（下载时间 + 12分钟缓冲）
3. 如需取消关机，运行：shutdown /a

注意：
- 请确保QMT服务已启动
- 请确保网络连接正常
- 关机前请保存所有重要文件
"""
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def calculate_shutdown_time():
    """计算关机时间"""
    # 参数
    num_stocks = 150  # 股票数量
    num_days = 58     # 时间范围（天）

    # 下载时间估算（保守估计）
    # 每只股票40-80秒，取80秒的保守值
    download_time_per_stock = 80  # 秒
    sleep_interval = 0.2  # 秒

    # 总下载时间（秒）
    total_download_seconds = num_stocks * (download_time_per_stock + sleep_interval)

    # 增加20%缓冲
    total_download_seconds *= 1.2

    # 转换为分钟
    total_download_minutes = total_download_seconds / 60

    # 关机缓冲时间
    buffer_minutes = 12

    # 总时间（秒）
    total_seconds = int(total_download_minutes * 60 + buffer_minutes * 60)

    current_time = datetime.now()
    shutdown_time = current_time + timedelta(seconds=total_seconds)

    return {
        'download_minutes': round(total_download_minutes, 1),
        'buffer_minutes': buffer_minutes,
        'total_minutes': round(total_seconds / 60, 1),
        'total_seconds': total_seconds,
        'shutdown_time': shutdown_time.strftime('%Y-%m-%d %H:%M:%S'),
        'shutdown_command': f'shutdown /s /t {total_seconds}'
    }


def print_banner():
    """打印横幅"""
    print("=" * 80)
    print("🚀 Tick下载 + 自动关机 启动脚本")
    print("=" * 80)
    print()


def print_summary(shutdown_info):
    """打印摘要"""
    print("=" * 80)
    print("📋 任务摘要")
    print("=" * 80)
    print(f"   股票数量：150 只")
    print(f"   时间范围：58 天 (2025-11-21 到 2026-02-13)")
    print(f"   预计数据：约35 GB")
    print()
    print(f"⏰ 关机计划：")
    print(f"   当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   下载时间：{shutdown_info['download_minutes']} 分钟")
    print(f"   缓冲时间：{shutdown_info['buffer_minutes']} 分钟")
    print(f"   总计时间：{shutdown_info['total_minutes']} 分钟")
    print(f"   预计关机：{shutdown_info['shutdown_time']}")
    print()
    print(f"💡 提示：")
    print(f"   - 下载过程中请勿关闭此窗口")
    print(f"   - 如需取消关机，运行：shutdown /a")
    print(f"   - 完成后数据保存在：data/qmt_data/")
    print("=" * 80)
    print()


def confirm_start():
    """确认开始"""
    print("⚠️  即将启动tick下载并设置自动关机！")
    print()
    print("请确认：")
    print("  1. 已保存所有重要文件")
    print("  2. QMT服务已启动")
    print("  3. 网络连接正常")
    print("  4. 硬盘有足够空间（至少40GB）")
    print()
    choice = input("确认开始？.strip().lower()

    return choice in ['yes', 'y']


def set_shutdown(seconds):
    """设置定时关机"""
    cmd = f'shutdown /s /t {seconds}'
    print(f"\n🔔 设置定时关机：{seconds} 秒后关机")

    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
        print(f"✅ 关机计划已设置")
        print(f"   取消命令：shutdown /a")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 设置关机失败：{e}")
        return False


def main():
    """主函数"""
    print_banner()

    # 计算关机时间
    shutdown_info = calculate_shutdown_time()

    # 打印摘要
    print_summary(shutdown_info)

    # 确认开始
    if not confirm_start():
        print("\n❌ 已取消")
        return

    print("\n" + "=" * 80)
    print("🚀 开始执行")
    print("=" * 80)
    print()

    # 设置定时关机
    if not set_shutdown(shutdown_info['total_seconds']):
        print("\n❌ 关机设置失败，请手动设置关机或手动监控下载进度")
        print(f"   手动关机命令：{shutdown_info['shutdown_command']}")
        return

    print()
    print("=" * 80)
    print("📥 开始下载tick数据")
    print("=" * 80)
    print()

    # 启动下载任务
    download_script = PROJECT_ROOT / 'scripts' / 'download_150_stocks_tick.py'

    if not download_script.exists():
        print(f"❌ 下载脚本不存在：{download_script}")
        print("请先创建或修改下载脚本")
        # 取消关机
        subprocess.run('shutdown /a', shell=True, capture_output=True)
        print("已取消关机")
        return

    print(f"执行下载脚本：{download_script}")
    print()

    # 运行下载脚本
    try:
        # 使用当前Python解释器运行
        import subprocess
        result = subprocess.run(
            [sys.executable, str(download_script)],
            cwd=str(PROJECT_ROOT),
            check=True
        )
        print("\n✅ 下载完成！")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 下载失败：{e}")
        print("请检查日志和错误信息")
        # 取消关机
        subprocess.run('shutdown /a', shell=True, capture_output=True)
        print("已取消关机")
        return
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        # 取消关机
        subprocess.run('shutdown /a', shell=True, capture_output=True)
        print("已取消关机")
        return

    print()
    print("=" * 80)
    print("🎉 所有任务完成！")
    print("=" * 80)
    print(f"   系统将在 {shutdown_info['shutdown_time']} 自动关机")
    print(f"   如需取消关机，运行：shutdown /a")
    print()


if __name__ == '__main__':
    main()