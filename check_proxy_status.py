#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
代理状态检查工具

用途：检查当前网络请求是否走代理
"""

import os
import sys

def check_env_proxy():
    """检查环境变量中的代理设置"""
    print("=" * 60)
    print("🔍 检查环境变量中的代理设置")
    print("=" * 60)
    
    proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'no_proxy', 'NO_PROXY']
    
    has_proxy = False
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var} = {value}")
            has_proxy = True
        else:
            print(f"❌ {var} = (未设置)")
    
    if not has_proxy:
        print("\n✅ 环境变量中没有代理设置")
    else:
        print("\n⚠️ 环境变量中存在代理设置")
    
    return has_proxy


def check_requests_proxy():
    """检查requests库的代理设置"""
    print("\n" + "=" * 60)
    print("🔍 检查requests库的代理设置")
    print("=" * 60)
    
    try:
        import requests
        session = requests.Session()
        proxies = session.proxies
        
        if proxies:
            print(f"⚠️ requests库有代理设置: {proxies}")
            return True
        else:
            print("✅ requests库没有代理设置")
            return False
    except ImportError:
        print("❌ requests库未安装")
        return False


def check_urllib3_proxy():
    """检查urllib3的代理设置"""
    print("\n" + "=" * 60)
    print("🔍 检查urllib3的代理设置")
    print("=" * 60)
    
    try:
        import urllib3
        # urllib3没有直接的代理检查方法
        # 但可以通过检查环境变量来判断
        print("ℹ️ urllib3使用环境变量中的代理设置")
        return False
    except ImportError:
        print("❌ urllib3未安装")
        return False


def test_connection(url):
    """测试实际连接，看是否走代理"""
    print("\n" + "=" * 60)
    print(f"🔍 测试连接: {url}")
    print("=" * 60)
    
    try:
        import requests
        import urllib3
        
        # 禁用SSL警告
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 创建session并禁用代理
        session = requests.Session()
        session.proxies = {}
        
        # 发送请求
        response = session.get(url, timeout=5, verify=False)
        
        print(f"✅ 连接成功！")
        print(f"   状态码: {response.status_code}")
        
        # 检查响应头中是否有代理信息
        if 'Via' in response.headers:
            print(f"⚠️ 响应头中有Via字段: {response.headers['Via']}")
            print("   这可能表示请求走了代理")
        else:
            print("✅ 响应头中没有Via字段")
            print("   这表示请求可能是直连")
        
        return True
        
    except requests.exceptions.ProxyError as e:
        print(f"❌ 代理错误: {e}")
        print("   这表示请求尝试使用代理但失败了")
        return False
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL错误: {e}")
        print("   这可能是直连但SSL证书问题")
        return False
    except requests.exceptions.Timeout as e:
        print(f"❌ 超时错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False


def main():
    """主函数"""
    print("🚀 代理状态检查工具")
    print("📅 时间:", sys.modules['time'].strftime("%Y-%m-%d %H:%M:%S") if 'time' in sys.modules else "")
    
    # 检查环境变量
    env_has_proxy = check_env_proxy()
    
    # 检查requests库
    requests_has_proxy = check_requests_proxy()
    
    # 检查urllib3
    urllib3_has_proxy = check_urllib3_proxy()
    
    # 测试实际连接
    print("\n" + "=" * 60)
    print("🔍 测试实际连接")
    print("=" * 60)
    
    test_urls = [
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        "https://www.baidu.com",
        "https://www.google.com"
    ]
    
    for url in test_urls:
        test_connection(url)
        print()
    
    # 总结
    print("=" * 60)
    print("📊 总结")
    print("=" * 60)
    
    if env_has_proxy or requests_has_proxy or urllib3_has_proxy:
        print("⚠️ 检测到代理配置")
        if env_has_proxy:
            print("   - 环境变量中有代理")
        if requests_has_proxy:
            print("   - requests库有代理")
        if urllib3_has_proxy:
            print("   - urllib3有代理")
        
        print("\n💡 建议:")
        print("   1. 如果你想走直连，请清除代理设置")
        print("   2. 或者在Clash Verge中配置绕过规则")
        print("   3. 或者使用手机热点连接")
    else:
        print("✅ 没有检测到代理配置")
        print("   当前应该走直连模式")


if __name__ == "__main__":
    main()