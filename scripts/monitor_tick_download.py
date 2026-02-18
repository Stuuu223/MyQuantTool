#!/usr/bin/env python3
"""
监控tick下载进度
"""
import time
from pathlib import Path
import re

def monitor_progress():
    """监控下载进度"""
    log_file = Path('C:/Users/pc/Desktop/Astock/MyQuantTool/logs/tick_download_150.log')

    if not log_file.exists():
        print(f"❌ 日志文件不存在: {log_file}")
        print("等待下载任务启动...")
        return

    print(f"📊 监控下载进度...")
    print(f"日志文件: {log_file}")
    print("=" * 80)
    print("按 Ctrl+C 退出监控\n")

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # 跳转到文件末尾
            f.seek(0, 2)
            last_pos = f.tell()

        while True:
            with open(log_file, 'r', encoding='utf-8') as f:
                f.seek(last_pos)
                new_lines = f.readlines()
                last_pos = f.tell()

                for line in new_lines:
                    # 只显示下载成功的日志
                    if '下载成功' in line or '下载失败' in line:
                        print(line.strip())

                    # 显示完成信息
                    if '下载完成' in line:
                        print("\n" + "=" * 80)
                        print("🎉 下载任务已完成！")
                        print("=" * 80)
                        # 读取最后的统计信息
                        print(f.read())
                        return

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n👋 监控已退出")
    except Exception as e:
        print(f"❌ 监控出错: {e}")


if __name__ == '__main__':
    monitor_progress()