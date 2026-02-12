#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
代理配置管理模块 - V19.10

功能：
- 管理代理配置，支持动态切换
- 强制屏蔽代理，绕过Clash等VPN工具
- 网络健康监控和自动降级
- 支持多种代理模式：直连/系统代理/自定义代理

Author: iFlow CLI
Version: V19.10
"""

import os
from typing import Optional, Dict, Any
from enum import Enum
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class ProxyMode(Enum):
    """代理模式枚举"""
    DIRECT = "direct"  # 直连模式（绕过所有代理）
    SYSTEM = "system"  # 使用系统代理
    CUSTOM = "custom"  # 自定义代理


class ProxyManager:
    """
    代理配置管理器
    
    功能：
    1. 强制屏蔽代理（绕过Clash等VPN）
    2. 动态切换代理模式
    3. 网络健康监控
    4. 自动降级策略
    """
    
    def __init__(self):
        """初始化代理管理器"""
        self.current_mode = ProxyMode.DIRECT
        self.custom_proxy = None
        self.health_check_enabled = True
        self.failure_count = 0
        self.max_failures = 5  # 连续失败5次后自动降级
        
        # 🆕 V19.10: 默认使用直连模式，绕过Clash
        self.set_direct_mode()
        
        logger.info("✅ [代理管理器] 初始化完成（直连模式）")
    
    def set_direct_mode(self) -> bool:
        """
        设置直连模式（绕过所有代理）
        
        这是推荐的模式，可以避免因为使用共享VPN节点而被封IP
        
        Returns:
            bool: 是否设置成功
        """
        try:
            # 强制屏蔽代理，绕过Clash，直连东方财富和新浪
            os.environ['NO_PROXY'] = 'eastmoney.com,sina.com.cn,127.0.0.1,localhost,*'
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)
            os.environ.pop('http_proxy', None)
            os.environ.pop('https_proxy', None)
            os.environ.pop('ALL_PROXY', None)
            os.environ.pop('all_proxy', None)
            
            self.current_mode = ProxyMode.DIRECT
            self.custom_proxy = None
            logger.info("🛡️ [代理管理器] 已切换到直连模式（绕过所有代理）")
            return True
        except Exception as e:
            logger.error(f"❌ [代理管理器] 设置直连模式失败: {e}")
            return False
    
    def set_system_proxy_mode(self) -> bool:
        """
        设置系统代理模式
        
        Returns:
            bool: 是否设置成功
        """
        try:
            # 清除NO_PROXY，允许使用系统代理
            os.environ.pop('NO_PROXY', None)
            
            self.current_mode = ProxyMode.SYSTEM
            self.custom_proxy = None
            logger.info("🔄 [代理管理器] 已切换到系统代理模式")
            return True
        except Exception as e:
            logger.error(f"❌ [代理管理器] 设置系统代理模式失败: {e}")
            return False
    
    def set_custom_proxy(self, proxy_url: str) -> bool:
        """
        设置自定义代理
        
        Args:
            proxy_url: 代理URL，例如 "http://127.0.0.1:7890"
        
        Returns:
            bool: 是否设置成功
        """
        try:
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
            os.environ.pop('NO_PROXY', None)
            
            self.current_mode = ProxyMode.CUSTOM
            self.custom_proxy = proxy_url
            logger.info(f"🔗 [代理管理器] 已切换到自定义代理: {proxy_url}")
            return True
        except Exception as e:
            logger.error(f"❌ [代理管理器] 设置自定义代理失败: {e}")
            return False
    
    def get_current_mode(self) -> ProxyMode:
        """
        获取当前代理模式
        
        Returns:
            ProxyMode: 当前代理模式
        """
        return self.current_mode
    
    def get_proxy_config(self) -> Dict[str, Any]:
        """
        获取当前代理配置
        
        Returns:
            Dict: 代理配置信息
        """
        config = {
            'mode': self.current_mode.value,
            'custom_proxy': self.custom_proxy,
            'http_proxy': os.environ.get('HTTP_PROXY'),
            'https_proxy': os.environ.get('HTTPS_PROXY'),
            'no_proxy': os.environ.get('NO_PROXY'),
            'health_check_enabled': self.health_check_enabled,
            'failure_count': self.failure_count
        }
        return config
    
    def record_failure(self):
        """记录一次失败"""
        self.failure_count += 1
        logger.warning(f"⚠️ [代理管理器] 记录失败，当前失败次数: {self.failure_count}/{self.max_failures}")
        
        # 自动降级：连续失败超过阈值，切换到直连模式
        if self.health_check_enabled and self.failure_count >= self.max_failures:
            logger.warning(f"🚨 [代理管理器] 连续失败次数超过阈值，自动切换到直连模式")
            self.set_direct_mode()
            self.failure_count = 0
    
    def record_success(self):
        """记录一次成功"""
        if self.failure_count > 0:
            self.failure_count = 0
            logger.debug(f"✅ [代理管理器] 成功记录，重置失败计数")
    
    def enable_health_check(self):
        """启用健康检查"""
        self.health_check_enabled = True
        logger.info("✅ [代理管理器] 已启用健康检查")
    
    def disable_health_check(self):
        """禁用健康检查"""
        self.health_check_enabled = False
        logger.info("⚠️ [代理管理器] 已禁用健康检查")
    
    def test_connection(self, test_url: str = "https://www.baidu.com") -> bool:
        """
        测试网络连接
        
        Args:
            test_url: 测试URL
        
        Returns:
            bool: 是否连接成功
        """
        try:
            import requests
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ [代理管理器] 网络连接测试成功: {test_url}")
                return True
            else:
                logger.warning(f"⚠️ [代理管理器] 网络连接测试失败: {test_url}, 状态码: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ [代理管理器] 网络连接测试异常: {e}")
            return False
    
    def test_eastmoney_connection(self) -> bool:
        """
        测试东方财富连接
        
        Returns:
            bool: 是否连接成功
        """
        try:
            import requests
            # 测试东方财富的一个轻量级接口
            response = requests.get(
                "https://push2.eastmoney.com/api/qt/clist/get",
                params={'pn': 1, 'pz': 1, 'po': 1, 'np': 1, 'fltt': 2, 'invt': 2},
                timeout=5
            )
            if response.status_code == 200:
                logger.info("✅ [代理管理器] 东方财富连接测试成功")
                return True
            else:
                logger.warning(f"⚠️ [代理管理器] 东方财富连接测试失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ [代理管理器] 东方财富连接测试异常: {e}")
            return False
    
    def get_status_summary(self) -> str:
        """
        获取状态摘要
        
        Returns:
            str: 状态摘要
        """
        mode_name = {
            ProxyMode.DIRECT: "直连模式（推荐）",
            ProxyMode.SYSTEM: "系统代理模式",
            ProxyMode.CUSTOM: f"自定义代理: {self.custom_proxy}"
        }
        
        summary = f"""
代理管理器状态：
- 当前模式: {mode_name.get(self.current_mode, '未知')}
- NO_PROXY: {os.environ.get('NO_PROXY', '未设置')}
- HTTP_PROXY: {os.environ.get('HTTP_PROXY', '未设置')}
- HTTPS_PROXY: {os.environ.get('HTTPS_PROXY', '未设置')}
- 健康检查: {'启用' if self.health_check_enabled else '禁用'}
- 失败次数: {self.failure_count}/{self.max_failures}
        """.strip()
        
        return summary


# 全局单例
_proxy_manager = None


def get_proxy_manager() -> ProxyManager:
    """
    获取代理管理器单例
    
    Returns:
        ProxyManager: 代理管理器实例
    """
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager


# 便捷函数
def set_direct_mode() -> bool:
    """设置直连模式（便捷函数）"""
    return get_proxy_manager().set_direct_mode()


def get_proxy_config() -> Dict[str, Any]:
    """获取代理配置（便捷函数）"""
    return get_proxy_manager().get_proxy_config()


def record_failure():
    """记录失败（便捷函数）"""
    get_proxy_manager().record_failure()


def record_success():
    """记录成功（便捷函数）"""
    get_proxy_manager().record_success()