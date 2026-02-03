import socket
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib.request
from urllib.request import ProxyHandler, build_opener
import ssl

def disable_proxy():
    """禁用系统代理以确保AkShare直连"""
    import os
    # 临时禁用系统代理
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''
    os.environ['http_proxy'] = ''
    os.environ['https_proxy'] = ''
    
    # 禁用urllib代理
    proxy_handler = ProxyHandler({})
    opener = build_opener(proxy_handler)
    urllib.request.install_opener(opener)
    
    # 设置SSL上下文
    ssl._create_default_https_context = ssl._create_unverified_context
    
    print("✅ [Network] 代理已禁用，使用直连模式")

def test_connection(url="https://www.baidu.com", timeout=10):
    """测试网络连接"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except:
        return False

def setup_urllib_proxy():
    """为urllib设置无代理"""
    import os
    # 确保urllib也不使用代理
    proxy_handler = ProxyHandler({})
    opener = build_opener(proxy_handler)
    urllib.request.install_opener(opener)


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