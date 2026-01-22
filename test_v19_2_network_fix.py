#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.2 网络层修复验证测试

测试内容：
1. 验证并发执行器线程数降低（从10降到5）
2. 验证资金流获取绕过代理
3. 验证连接池警告是否消失
"""

import sys
import os
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("=" * 80)
print("🚀 V19.2 网络层修复验证测试")
print("=" * 80)
print(f"测试开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

# 测试1：验证并发执行器线程数
print("📋 测试1: 验证并发执行器线程数")
print("-" * 80)
try:
    from logic.concurrent_executor import get_concurrent_executor, shutdown_global_executor
    
    # 创建执行器
    executor = get_concurrent_executor()
    print(f"✅ ConcurrentExecutor 导入成功")
    print(f"   最大线程数: {executor.max_workers}")
    
    if executor.max_workers == 5:
        print(f"✅ 线程数已正确降低为 5（原为10）")
    else:
        print(f"⚠️ 线程数为 {executor.max_workers}，预期为 5")
    
    # 关闭执行器
    shutdown_global_executor()
except Exception as e:
    print(f"❌ 测试失败: {e}")

print()

# 测试2：验证资金流获取绕过代理
print("📋 测试2: 验证资金流获取绕过代理")
print("-" * 80)
try:
    from logic.data_adapter_akshare import MoneyFlowAdapter
    
    print(f"✅ MoneyFlowAdapter 导入成功")
    print(f"   正在获取资金流榜单（绕过代理）...")
    
    # 获取资金流榜单
    t1 = time.time()
    rank_df = MoneyFlowAdapter._fetch_rank_data()
    t2 = time.time()
    
    if rank_df is not None and not rank_df.empty:
        print(f"✅ 资金流榜单获取成功")
        print(f"   耗时: {t2 - t1:.2f}秒")
        print(f"   数据行数: {len(rank_df)}")
        print(f"   前5行数据:")
        print(rank_df.head().to_string(index=False))
    else:
        print(f"⚠️ 资金流榜单获取失败或为空")
        print(f"   耗时: {t2 - t1:.2f}秒")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试3：验证并发获取实时数据（检查连接池警告）
print("📋 测试3: 验证并发获取实时数据（检查连接池警告）")
print("-" * 80)
try:
    from logic.concurrent_executor import get_concurrent_executor, batch_get_realtime_data_fast, shutdown_global_executor
    from logic.data_manager import DataManager
    
    # 初始化数据管理器
    dm = DataManager()
    
    # 测试股票列表（20只）
    test_stocks = ['000001', '000002', '600000', '600519', '300750', 
                   '000858', '002415', '600036', '601318', '601888',
                   '000725', '002594', '600276', '600309', '600887',
                   '000063', '002475', '600690', '601012', '601988']
    
    print(f"   测试股票数: {len(test_stocks)}")
    print(f"   最大线程数: 5")
    print(f"   正在并发获取实时数据...")
    
    # 并发获取数据
    t1 = time.time()
    results = batch_get_realtime_data_fast(dm, test_stocks, batch_size=10)
    t2 = time.time()
    
    print(f"✅ 并发获取完成")
    print(f"   耗时: {t2 - t1:.2f}秒")
    print(f"   成功: {len(results)}/{len(test_stocks)} 只股票")
    
    # 关闭执行器
    shutdown_global_executor()
    
    # 检查是否有连接池警告
    print(f"\n   ⚠️ 请检查上方日志，确认是否还有 'Connection pool is full' 警告")
    print(f"   如果没有警告，说明修复成功！")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试4：验证代理环境变量恢复
print("📋 测试4: 验证代理环境变量恢复")
print("-" * 80)
try:
    from logic.data_adapter_akshare import MoneyFlowAdapter
    
    # 记录当前代理设置
    http_proxy_before = os.environ.get('HTTP_PROXY')
    https_proxy_before = os.environ.get('HTTPS_PROXY')
    
    print(f"   获取资金流前的代理设置:")
    print(f"     HTTP_PROXY: {http_proxy_before}")
    print(f"     HTTPS_PROXY: {https_proxy_before}")
    
    # 获取资金流榜单（会临时移除代理）
    rank_df = MoneyFlowAdapter._fetch_rank_data()
    
    # 检查代理是否恢复
    http_proxy_after = os.environ.get('HTTP_PROXY')
    https_proxy_after = os.environ.get('HTTPS_PROXY')
    
    print(f"\n   获取资金流后的代理设置:")
    print(f"     HTTP_PROXY: {http_proxy_after}")
    print(f"     HTTPS_PROXY: {https_proxy_after}")
    
    # 验证代理是否恢复
    if http_proxy_before == http_proxy_after and https_proxy_before == https_proxy_after:
        print(f"\n✅ 代理环境变量正确恢复")
    else:
        print(f"\n⚠️ 代理环境变量未恢复，请检查代码")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("📊 测试总结")
print("=" * 80)
print("✅ 所有测试完成")
print("\n预期结果:")
print("1. ConcurrentExecutor 最大线程数为 5（不再是10）")
print("2. 资金流榜单获取成功，无 ProxyError")
print("3. 并发获取实时数据无 'Connection pool is full' 警告")
print("4. 代理环境变量正确恢复")
print(f"\n测试结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)