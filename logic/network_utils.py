#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网络工具模块
处理代理设置和网络相关功能
"""
import os
import urllib.request


def disable_proxy():
    """
    禁用所有代理设置

    解决问题：
    - 系统代理可能导致 AkShare API 调用失败
    - 某些代理服务器可能不兼容或配置错误

    使用方法：
        在程序启动时调用（在任何 import 之前）

    示例：
        from logic.network_utils import disable_proxy
        disable_proxy()
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol='300997', period='daily')
    """
    # 1. 清除环境变量代理
    proxy_keys = [
        'HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
        'ALL_PROXY', 'all_proxy', 'FTP_PROXY', 'ftp_proxy'
    ]
    for key in proxy_keys:
        os.environ.pop(key, None)

    # 2. 设置 NO_PROXY
    os.environ['NO_PROXY'] = '*'

    # 3. 清除 urllib 的代理缓存
    try:
        urllib.request.getproxies.cache_clear()
    except Exception:
        pass

    print("✅ [Network] 代理已禁用，使用直连模式")


def check_proxy_status():
    """
    检查当前代理设置

    Returns:
        dict: 包含代理状态的信息
    """
    import urllib.request
    import requests

    proxies = urllib.request.getproxies()

    # 检查 requests 的代理设置
    session = requests.Session()
    requests_proxies = session.proxies

    return {
        'system_proxies': proxies if proxies else None,
        'requests_proxies': requests_proxies if requests_proxies else None,
        'no_proxy': os.environ.get('NO_PROXY', None),
        'has_proxy': bool(proxies)
    }


def get_safe_session():
    """
    获取禁用代理的 requests Session

    Returns:
        requests.Session: 禁用代理的 Session 对象
    """
    import requests
    session = requests.Session()
    session.trust_env = False  # 禁用环境变量和系统代理
    return session


if __name__ == "__main__":
    # 测试
    print("测试网络工具...")
    print("\n1. 禁用代理前:")
    status = check_proxy_status()
    print(f"   系统代理: {status['system_proxies']}")
    print(f"   requests 代理: {status['requests_proxies']}")

    print("\n2. 禁用代理...")
    disable_proxy()

    print("\n3. 禁用代理后:")
    status = check_proxy_status()
    print(f"   系统代理: {status['system_proxies']}")
    print(f"   requests 代理: {status['requests_proxies']}")
    print(f"   NO_PROXY: {status['no_proxy']}")