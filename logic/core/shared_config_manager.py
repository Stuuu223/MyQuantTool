#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享配置管理器 (V16.1 - 多进程配置同步)

核心功能：
1. 使用multiprocessing.Manager实现跨进程配置共享
2. 支持动态参数调整，所有子进程毫秒级感知变更
3. Windows兼容：针对spawn启动模式设计了set_proxy接口
4. 编码卫士：防止Windows控制台打印中文乱码

Architecture:
- Main Process: 创建Manager，初始化共享配置字典
- Child Processes: 通过set_proxy挂载配置代理，实时读取配置
- UI Process: 通过update_param动态修改配置

Usage:
    # Main Process
    import multiprocessing
    from logic.core.shared_config_manager import SharedConfigManager
    
    if __name__ == "__main__":
        manager = multiprocessing.Manager()
        config_proxy = SharedConfigManager.initialize(manager)
        
        # Start child processes
        # p = Process(target=run_scanner, args=(config_proxy,))
        # p.start()
    
    # Child Process
    def run_scanner(config_proxy):
        SharedConfigManager.set_proxy(config_proxy)
        while True:
            config = SharedConfigManager.get_config()
            # Use config...

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.1
"""

import sys
import os
from typing import Any, Dict
from multiprocessing import Manager

# Windows编码卫士：强制UTF-8输出
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


class SharedConfigManager:
    """
    共享配置管理器（跨进程配置同步）
    
    解决问题：
    1. Python单例在multiprocessing下失效
    2. 主进程修改参数，子进程无法感知
    3. 需要支持动态参数调整（如止损阈值）
    
    实现方案：
    1. 使用multiprocessing.Manager创建共享字典
    2. 子进程通过set_proxy挂载配置代理
    3. 每次循环读取最新配置（Read-Copy模式）
    """
    
    _instance = None
    _shared_state = None  # 跨进程的代理对象 (Proxy)
    
    @staticmethod
    def initialize(manager: Manager = None) -> Dict[str, Any]:
        """
        初始化共享配置（必须在主进程调用）
        
        Args:
            manager: multiprocessing.Manager实例（如果为None则自动创建）
        
        Returns:
            Dict: 共享配置字典代理对象
        """
        if SharedConfigManager._shared_state is not None:
            return SharedConfigManager._shared_state
        
        # 创建Manager（如果未提供）
        if manager is None:
            manager = Manager()
        
        # 加载默认配置
        try:
            from logic.core.strategy_config import StrategyConfig
            default_conf = StrategyConfig().get_config_dict()
        except Exception as e:
            print(f"[SharedConfigManager] ⚠️ 加载默认配置失败: {e}")
            default_conf = {}
        
        # 创建共享字典
        SharedConfigManager._shared_state = manager.dict(default_conf)
        
        print(f"[SharedConfigManager] ✅ 配置初始化完成，共享内存ID: {id(SharedConfigManager._shared_state)}")
        print(f"[SharedConfigManager] ✅ 配置项数量: {len(SharedConfigManager._shared_state)}")
        
        return SharedConfigManager._shared_state
    
    @staticmethod
    def set_proxy(config_proxy: Dict[str, Any]) -> None:
        """
        子进程挂载配置代理（Windows spawn模式专用）
        
        Args:
            config_proxy: 主进程传入的共享配置字典代理对象
        """
        SharedConfigManager._shared_state = config_proxy
        print(f"[SharedConfigManager] ✅ 子进程挂载配置代理成功，PID: {os.getpid()}")
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        获取整个配置字典（实时）
        
        Returns:
            Dict: 当前配置字典
        
        Raises:
            RuntimeError: 如果共享配置未初始化
        """
        if SharedConfigManager._shared_state is None:
            raise RuntimeError(
                "[SharedConfigManager] ❌ 共享配置未初始化！"
                "请在主进程调用 SharedConfigManager.initialize()"
            )
        
        # Read-Copy模式：返回字典副本（避免并发修改问题）
        return dict(SharedConfigManager._shared_state)
    
    @staticmethod
    def get_param(section: str, key: str, default: Any = None) -> Any:
        """
        获取单个参数（实时）
        
        Args:
            section: 配置节（如 'capital_flow'）
            key: 参数键（如 'ratio_bullish'）
            default: 默认值（如果参数不存在）
        
        Returns:
            Any: 参数值
        
        Example:
            >>> bullish_ratio = SharedConfigManager.get_param('capital_flow', 'ratio_bullish')
            >>> print(f"看多比例: {bullish_ratio * 100:.0f}%")
        """
        config = SharedConfigManager.get_config()
        return config.get(section, {}).get(key, default)
    
    @staticmethod
    def update_param(section: str, key: str, value: Any) -> None:
        """
        动态更新参数，所有进程立即生效
        
        Args:
            section: 配置节（如 'capital_flow'）
            key: 参数键（如 'ratio_bullish'）
            value: 新值
        
        Example:
            >>> SharedConfigManager.update_param('capital_flow', 'ratio_bullish', 0.35)
            >>> print("参数更新成功，所有子进程将立即生效")
        """
        if SharedConfigManager._shared_state is None:
            raise RuntimeError(
                "[SharedConfigManager] ❌ 共享配置未初始化！"
                "请在主进程调用 SharedConfigManager.initialize()"
            )
        
        # 读取当前配置
        current_conf = dict(SharedConfigManager._shared_state)
        
        # 更新配置
        if section not in current_conf:
            current_conf[section] = {}
        
        old_value = current_conf[section].get(key)
        current_conf[section][key] = value
        
        # 触发同步（必须重新赋值整个字典）
        SharedConfigManager._shared_state.update(current_conf)
        
        print(f"[SharedConfigManager] 🔄 参数更新成功: [{section}][{key}] {old_value} -> {value}")
    
    @staticmethod
    def is_initialized() -> bool:
        """
        检查共享配置是否已初始化
        
        Returns:
            bool: 是否已初始化
        """
        return SharedConfigManager._shared_state is not None


if __name__ == "__main__":
    # 测试代码
    print("=" * 80)
    print("SharedConfigManager 测试")
    print("=" * 80)
    
    # 1. 初始化共享配置
    manager = Manager()
    config_proxy = SharedConfigManager.initialize(manager)
    
    print(f"\n📊 初始配置:")
    config = SharedConfigManager.get_config()
    for section, params in config.items():
        print(f"  [{section}]: {len(params)} 个参数")
    
    print(f"\n🔍 获取单个参数:")
    bullish_ratio = SharedConfigManager.get_param('capital_flow', 'ratio_bullish')
    print(f"  看多比例: {bullish_ratio * 100:.0f}%")
    
    print(f"\n✏️  修改参数:")
    SharedConfigManager.update_param('capital_flow', 'ratio_bullish', 0.35)
    bullish_ratio_new = SharedConfigManager.get_param('capital_flow', 'ratio_bullish')
    print(f"  新的看多比例: {bullish_ratio_new * 100:.0f}%")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
