# -*- coding: utf-8 -*-
"""
性能测试脚本 - 测试盘前缓存系统和半路战法扫描性能

功能：
1. 测试盘前缓存系统的加载速度
2. 测试半路战法的扫描速度
3. 验证换手率和量比是否正确显示
4. 验证乖离率是否正确计算（使用盘前缓存）
"""

import time
from logic.pre_market_cache import get_pre_market_cache
from logic.algo import QuantAlgo

print("=" * 80)
print("🚀 开始性能测试")
print("=" * 80)

# 测试1：盘前缓存系统
print("\n" + "=" * 80)
print("📊 测试1：盘前缓存系统")
print("=" * 80)

start_time = time.time()
pre_market_cache = get_pre_market_cache()
cache_info = pre_market_cache.get_cache_info()
elapsed = time.time() - start_time

print(f"✅ 盘前缓存加载完成，耗时: {elapsed:.4f} 秒")
print(f"  缓存版本: {cache_info['cache_version']}")
print(f"  缓存日期: {cache_info['cache_date']}")
print(f"  缓存时间: {cache_info['cache_time']}")
print(f"  股票数量: {cache_info['total_stocks']}")
print(f"  是否已加载: {cache_info['is_loaded']}")

# 测试2：乖离率计算性能
print("\n" + "=" * 80)
print("📊 测试2：乖离率计算性能（使用盘前缓存）")
print("=" * 80)

test_codes = ['300606', '688630', '301590']
test_prices = [38.0, 196.0, 233.0]

start_time = time.time()
for code, price in zip(test_codes, test_prices):
    bias = pre_market_cache.calculate_ma_bias(code, price)
    print(f"  {code} (价格: {price:.2f}): 乖离率 = {bias}%")
elapsed = time.time() - start_time

print(f"✅ 乖离率计算完成，耗时: {elapsed:.6f} 秒")

# 测试3：半路战法扫描性能
print("\n" + "=" * 80)
print("📊 测试3：半路战法扫描性能")
print("=" * 80)

start_time = time.time()
result = QuantAlgo.scan_halfway_stocks(limit=3, min_score=30)
elapsed = time.time() - start_time

print(f"✅ 半路战法扫描完成，耗时: {elapsed:.2f} 秒")
print(f"  数据状态: {result.get('数据状态')}")
print(f"  扫描数量: {result.get('扫描数量')}")
print(f"  符合条件数量: {result.get('符合条件数量')}")

# 测试4：验证换手率和量比
print("\n" + "=" * 80)
print("📊 测试4：验证换手率和量比")
print("=" * 80)

stocks = result.get('半路板列表', [])
print(f"前 {min(3, len(stocks))} 只符合条件的股票:")

invalid_count = 0
for i, stock in enumerate(stocks[:3], 1):
    print(f"\n{i}. {stock['代码']} {stock['名称']}")
    print(f"   最新价: {stock['最新价']:.2f}")
    print(f"   涨跌幅: {stock['涨跌幅']:.2f}%")
    print(f"   换手率: {stock['换手率']:.2f}%")
    print(f"   量比: {stock['量比']:.2f}")
    print(f"   乖离率: {stock.get('乖离率', 0):.2f}%")
    print(f"   评分: {stock['评分']}")
    print(f"   评级: {stock['评级']}")

    # 检查换手率和量比是否为默认值
    if stock['换手率'] == 0 or stock['量比'] == 1:
        invalid_count += 1
        print(f"   ⚠️ 警告：换手率或量比为默认值")

if invalid_count > 0:
    print(f"\n⚠️ 警告：有 {invalid_count} 只股票的换手率或量比为默认值")
else:
    print(f"\n✅ 所有 {len(stocks)} 只股票的换手率和量比都正确获取！")

# 测试5：性能总结
print("\n" + "=" * 80)
print("📊 测试5：性能总结")
print("=" * 80)

print(f"✅ 所有测试完成！")
print(f"  盘前缓存加载: {cache_info['total_stocks']} 只股票，耗时 {elapsed:.4f} 秒")
print(f"  半路战法扫描: {result.get('扫描数量', 0)} 只股票，耗时 {elapsed:.2f} 秒")
print(f"  符合条件: {result.get('符合条件数量', 0)} 只股票")

if invalid_count == 0:
    print(f"  换手率和量比: ✅ 全部正确")
else:
    print(f"  换手率和量比: ⚠️ {invalid_count} 只股票有误")

print("\n" + "=" * 80)
print("✅ 性能测试完成！")
print("=" * 80)