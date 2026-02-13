#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QMT 保活守护线程测试脚本

功能：
1. 模拟 QMT 正常运行场景，观察心跳探测
2. 模拟 QMT 断连场景，观察重连逻辑
3. 验证保活线程不会阻塞主线程

Usage:
    python test_keepalive.py

测试步骤：
1. 启动测试脚本
2. 观察 xtdata 心跳探测日志
3. 手动关闭 QMT 客户端（可选）
4. 观察保活线程的反应（心跳丢失、唤醒、重连）
5. 按 Ctrl+C 停止测试

Author: iFlow CLI
Date: 2026-02-13
"""

import time
import threading
from logic.qmt_keepalive import start_qmt_keepalive, stop_qmt_keepalive
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """测试主函数"""
    print("=" * 70)
    print("🧪 QMT 保活守护线程测试")
    print("=" * 70)
    print()
    print("📋 测试说明：")
    print("  1. 启动保活守护线程（15秒心跳间隔）")
    print("  2. 观察日志输出（✅ 心跳正常 / ⚠️ 心跳丢失）")
    print("  3. 可选：手动关闭 QMT 客户端，观察保活线程反应")
    print("  4. 按 Ctrl+C 停止测试")
    print()
    print("💡 提示：")
    print("  - 保活线程是守护线程，不会阻塞主线程")
    print("  - 连续 3 次心跳丢失后会记录 CRITICAL 日志")
    print("  - xtdata 断连时会尝试 subscribe_quote() 唤醒")
    print("  - xt_trader 断连时会尝试 connect() 重连")
    print("=" * 70)
    print()
    
    # 启动保活守护线程
    logger.info("🚀 启动 QMT 保活守护线程...")
    keepalive = start_qmt_keepalive(heartbeat_interval=15, max_retries=3)
    
    print("✅ 保活守护线程已启动")
    print()
    print("📊 观察日志输出...")
    print("⏸️  按 Ctrl+C 停止测试")
    print()
    
    # 主线程计数器（验证保活线程不阻塞主线程）
    counter = 0
    
    try:
        while True:
            # 主线程每秒输出一次，验证不阻塞
            counter += 1
            if counter % 10 == 0:  # 每 10 秒输出一次
                logger.info(f"🕐 主线程运行中... ({counter}秒)")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("🛑 收到停止信号，正在关闭...")
        print("=" * 70)
        
        # 停止保活守护线程
        stop_qmt_keepalive()
        
        print("✅ 保活守护线程已停止")
        print("✅ 测试结束")
        print("=" * 70)


if __name__ == "__main__":
    main()