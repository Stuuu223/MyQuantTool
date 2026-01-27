#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网络环境诊断工具

用途：测试是走直连还是走代理能访问东方财富
"""

import requests
import time
import sys

# 目标：东方财富的一个 API
TARGET_URL = "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80&fields=f1,f2,f3,f4,f12,f14"

# 伪装头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}

def test_request(name, proxies):
    """测试请求"""
    print(f"\n🧪 测试 {name} ...")
    try:
        start = time.time()
        resp = requests.get(TARGET_URL, headers=HEADERS, proxies=proxies, timeout=10)
        elapsed = time.time() - start
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                if data.get('data') and data['data'].get('diff'):
                    stock = data['data']['diff'][0]
                    print(f"✅ 成功! 耗时: {elapsed:.2f}s")
                    print(f"   数据样本: {stock.get('f14', 'N/A')} (现价: {stock.get('f2', 'N/A')})")
                    return True
                else:
                    print(f"⚠️ 连接通了，但返回空数据 (可能被风控)")
                    print(f"   响应: {data}")
            except Exception as e:
                print(f"⚠️ 连接通了，但解析JSON失败: {e}")
        else:
            print(f"❌ 状态码错误: {resp.status_code}")
            print(f"   响应: {resp.text[:200]}")
    except requests.exceptions.ProxyError as e:
        print(f"❌ 代理错误: {e}")
    except requests.exceptions.Timeout as e:
        print(f"❌ 超时错误: {e}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("🕵️ 网络环境诊断工具")
    print("=" * 60)
    
    # 1. 测试直连 (不走代理)
    print("\n1. 尝试直连 (无代理)...")
    success_direct = test_request("直连模式", None)
    
    # 2. 测试走 Clash (假设端口 7890)
    print("\n2. 尝试走 Clash (127.0.0.1:7890)...")
    clash_proxy = {
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890"
    }
    success_clash = test_request("Clash 代理模式", clash_proxy)
    
    # 3. 测试走 Clash (假设端口 7891 - 有些Clash版本用7891)
    print("\n3. 尝试走 Clash (127.0.0.1:7891)...")
    clash_proxy_7891 = {
        "http": "http://127.0.0.1:7891",
        "https": "http://127.0.0.1:7891"
    }
    success_clash_7891 = test_request("Clash 代理模式 (7891)", clash_proxy_7891)
    
    # 总结
    print("\n" + "=" * 60)
    print("💡 诊断结论")
    print("=" * 60)
    
    if success_direct:
        print("✅ 你的网络【直连】是通的！")
        print("   建议：代码里应该禁用代理 (NO_PROXY='*')")
        print("   操作：保持当前的main.py配置，不要修改")
    elif success_clash:
        print("✅ 你的网络需要【走 Clash (7890)】才能通！")
        print("   建议：代码里必须配置 proxies 参数")
        print("   操作：在main.py开头添加代理配置")
    elif success_clash_7891:
        print("✅ 你的网络需要【走 Clash (7891)】才能通！")
        print("   建议：代码里必须配置 proxies 参数")
        print("   操作：在main.py开头添加代理配置")
    else:
        print("💀 全挂了！")
        print("   可能原因：")
        print("   1. TLS指纹问题 - Python的握手方式太老土")
        print("   2. IP被封锁 - 需要换IP（手机热点）")
        print("   3. 防火墙拦截 - 需要更高级的指纹伪装")
        print("   建议：")
        print("   - 先尝试用手机热点连接")
        print("   - 如果还不行，考虑安装 curl_cffi 库")
    
    print("\n" + "=" * 60)