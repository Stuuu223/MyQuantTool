#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网络环境诊断工具

用途：测试是走直连还是走代理能访问东方财富
"""

import requests
import time
import sys

# 目标：多个数据源的API
TARGET_URLS = {
    "东方财富": "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80&fields=f1,f2,f3,f4,f12,f14",
    "新浪财经": "https://hq.sinajs.cn/list=sz300750,sh600000",
    "百度": "https://www.baidu.com",
    "谷歌": "https://www.google.com"
}

# 伪装头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}

def test_request(name, url, proxies):
    """测试请求"""
    print(f"\n🧪 测试 {name} ...")
    try:
        start = time.time()
        resp = requests.get(url, headers=HEADERS, proxies=proxies, timeout=10)
        elapsed = time.time() - start
        
        if resp.status_code == 200:
            print(f"✅ 成功! 耗时: {elapsed:.2f}s")
            
            # 尝试解析响应内容
            try:
                data = resp.json()
                if data.get('data') and data['data'].get('diff'):
                    stock = data['data']['diff'][0]
                    print(f"   数据样本: {stock.get('f14', 'N/A')} (现价: {stock.get('f2', 'N/A')})")
                else:
                    print(f"   响应: {str(data)[:100]}")
            except:
                # 如果不是JSON，显示文本内容
                print(f"   响应: {resp.text[:100]}")
            
            return True
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
    print("🕵️ 网络环境诊断工具 - 多数据源测试")
    print("=" * 60)
    
    # 测试所有数据源
    print("\n📡 测试直连模式 (无代理)...")
    print("-" * 60)
    
    success_results = {}
    for name, url in TARGET_URLS.items():
        success = test_request(f"{name} (直连)", url, None)
        success_results[f"{name}_direct"] = success
    
    # 测试Clash代理模式
    print("\n📡 测试Clash代理模式 (127.0.0.1:7890)...")
    print("-" * 60)
    
    clash_proxy = {
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890"
    }
    
    for name, url in TARGET_URLS.items():
        success = test_request(f"{name} (Clash)", url, clash_proxy)
        success_results[f"{name}_clash"] = success
    
    # 测试Clash代理模式 (7891端口)
    print("\n📡 测试Clash代理模式 (127.0.0.1:7891)...")
    print("-" * 60)
    
    clash_proxy_7891 = {
        "http": "http://127.0.0.1:7891",
        "https": "http://127.0.0.1:7891"
    }
    
    for name, url in TARGET_URLS.items():
        success = test_request(f"{name} (Clash 7891)", url, clash_proxy_7891)
        success_results[f"{name}_clash_7891"] = success
    
    # 总结
    print("\n" + "=" * 60)
    print("💡 诊断结论")
    print("=" * 60)
    
    # 统计直连成功率
    direct_success_count = sum(1 for k, v in success_results.items() if k.endswith('_direct') and v)
    total_direct_count = sum(1 for k in success_results.keys() if k.endswith('_direct'))
    
    # 统计Clash成功率
    clash_success_count = sum(1 for k, v in success_results.items() if k.endswith('_clash') and v)
    total_clash_count = sum(1 for k in success_results.keys() if k.endswith('_clash'))
    
    # 统计Clash 7891成功率
    clash_7891_success_count = sum(1 for k, v in success_results.items() if k.endswith('_clash_7891') and v)
    total_clash_7891_count = sum(1 for k in success_results.keys() if k.endswith('_clash_7891'))
    
    print(f"\n📊 统计结果：")
    print(f"   直连模式: {direct_success_count}/{total_direct_count} 成功")
    print(f"   Clash模式: {clash_success_count}/{total_clash_count} 成功")
    print(f"   Clash 7891: {clash_7891_success_count}/{total_clash_7891_count} 成功")
    
    if direct_success_count > 0:
        print(f"\n✅ 你的网络【直连】是通的！")
        print(f"   建议：代码里应该禁用代理 (NO_PROXY='*')")
        print(f"   操作：保持当前的main.py配置，不要修改")
    elif clash_success_count > 0:
        print(f"\n✅ 你的网络需要【走 Clash】才能通！")
        print(f"   建议：代码里必须配置 proxies 参数")
        print(f"   操作：在main.py开头添加代理配置")
    elif clash_7891_success_count > 0:
        print(f"\n✅ 你的网络需要【走 Clash (7891)】才能通！")
        print(f"   建议：代码里必须配置 proxies 参数")
        print(f"   操作：在main.py开头添加代理配置")
    else:
        print(f"\n💀 全挂了！")
        print(f"   可能原因：")
        print(f"   1. TLS指纹问题 - Python的握手方式太老土")
        print(f"   2. IP被封锁 - 需要换IP（手机热点）")
        print(f"   3. 防火墙拦截 - 需要更高级的指纹伪装")
        print(f"   建议：")
        print(f"   - 先尝试用手机热点连接")
        print(f"   - 如果还不行，考虑安装 curl_cffi 库")
    
    print("\n" + "=" * 60)