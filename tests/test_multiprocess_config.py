#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多进程配置同步测试 (V16.1 - Windows兼容性验证)

测试目标：
1. 验证主进程修改参数，子进程是否能实时感知
2. 验证Windows spawn模式下的配置代理传递
3. 验证UTF-8编码在Windows控制台下的正确性

Usage:
    python tests/test_multiprocess_config.py

Expected Output:
    [Main] 开始多进程配置同步测试...
    [Child] 启动... PID: 1234
    [Child] 参数保持: 100
    [Main] 🚨 主进程修改参数: 100 -> 999
    [SharedConfig] 🔄 参数更新成功: [test_section][dynamic_val] 100 -> 999
    [Child] ⚠️ 检测到参数变更! 100 -> 999  <-- 成功！

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.1
"""

import sys
import os
import time
import multiprocessing

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.core.shared_config_manager import SharedConfigManager
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def child_process(config_proxy: dict, test_duration: int = 10):
    """
    子进程：持续监听配置变化
    
    Args:
        config_proxy: 主进程传入的共享配置字典代理对象
        test_duration: 测试持续时间（秒）
    """
    try:
        # Windows编码卫士：强制UTF-8输出
        if sys.platform == 'win32':
            try:
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
            except Exception:
                pass
        
        print(f"[Child] ✅ 子进程启动成功，PID: {os.getpid()}")
        
        # 挂载配置代理
        SharedConfigManager.set_proxy(config_proxy)
        
        # 添加测试参数
        SharedConfigManager.update_param('test_section', 'dynamic_val', 100)
        
        last_val = 100
        start_time = time.time()
        
        print(f"[Child] 开始监听配置变化（持续{test_duration}秒）...")
        
        while time.time() - start_time < test_duration:
            # 每次循环读取最新配置
            current_val = SharedConfigManager.get_param('test_section', 'dynamic_val')
            
            # 检测参数变更
            if current_val != last_val:
                print(f"[Child] ⚠️ 检测到参数变更! {last_val} -> {current_val}")
                last_val = current_val
            else:
                print(f"[Child] 参数保持: {current_val}")
            
            time.sleep(1)  # 每秒检查一次
        
        print(f"[Child] ✅ 子进程结束监听，PID: {os.getpid()}")
        
    except Exception as e:
        print(f"[Child] ❌ 子进程异常: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("=" * 80)
    print("多进程配置同步测试 (V16.1 - Windows兼容性验证)")
    print("=" * 80)
    
    print("\n[Main] 🔍 检查Python版本...")
    print(f"  Python版本: {sys.version}")
    print(f"  Python路径: {sys.executable}")
    print(f"  当前平台: {sys.platform}")
    
    print("\n[Main] 🚀 启动多进程配置同步测试...")
    
    # 创建Manager
    print("\n[Main] 1️⃣ 创建Manager...")
    manager = multiprocessing.Manager()
    
    # 初始化共享配置
    print("[Main] 2️⃣ 初始化共享配置...")
    config_proxy = SharedConfigManager.initialize(manager)
    
    # 添加测试参数
    print("[Main] 3️⃣ 添加测试参数...")
    SharedConfigManager.update_param('test_section', 'dynamic_val', 100)
    
    # 启动子进程
    print("[Main] 4️⃣ 启动子进程...")
    child = multiprocessing.Process(
        target=child_process,
        args=(config_proxy, 10),  # 持续10秒
        name='ConfigTestChild'
    )
    child.start()
    
    print(f"[Main] ✅ 子进程已启动，PID: {child.pid}")
    
    # 等待3秒，让子进程稳定运行
    print("\n[Main] 5️⃣ 等待子进程稳定运行（3秒）...")
    time.sleep(3)
    
    # 修改参数
    print("\n[Main] 6️⃣ 主进程修改参数...")
    print("[Main] 🚨 主进程修改参数: 100 -> 999")
    SharedConfigManager.update_param('test_section', 'dynamic_val', 999)
    
    # 再等待2秒，观察子进程是否检测到变更
    print("\n[Main] 7️⃣ 等待子进程响应（2秒）...")
    time.sleep(2)
    
    # 恢复参数
    print("\n[Main] 8️⃣ 恢复参数...")
    print("[Main] 🚨 主进程恢复参数: 999 -> 100")
    SharedConfigManager.update_param('test_section', 'dynamic_val', 100)
    
    # 等待子进程结束
    print("\n[Main] 9️⃣ 等待子进程结束...")
    child.join(timeout=15)
    
    if child.is_alive():
        print("[Main] ⚠️ 子进程超时，强制结束...")
        child.terminate()
        child.join(timeout=5)
    
    print(f"[Main] 子进程退出码: {child.exitcode}")
    
    # 清理
    print("\n[Main] 🔟 清理Manager...")
    manager.shutdown()
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
    
    # 测试结果评估
    print("\n📊 测试结果评估:")
    print("  如果看到 [Child] ⚠️ 检测到参数变更! 100 -> 999")
    print("  说明配置同步成功 ✅")
    print("  否则说明配置同步失败 ❌")


if __name__ == "__main__":
    # Windows多进程必须使用spawn模式
    # 必须放在if __name__ == "__main__":保护下
    multiprocessing.set_start_method('spawn', force=True)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Main] ⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n[Main] ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()