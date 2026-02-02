# -*- coding: utf-8 -*-
"""
盘前数据预热脚本

功能：
- 在盘前（9:15之前）一次性计算全市场的均线数据
- 生成盘前缓存文件
"""

from logic.pre_market_cache import get_pre_market_cache

print("=" * 80)
print("☀️ 开始执行盘前数据预热...")
print("=" * 80)

pre_market_cache = get_pre_market_cache()

# 运行盘前预热任务
success = pre_market_cache.run_daily_job()

if success:
    print("\n✅ 盘前数据预热成功！")

    # 显示缓存信息
    cache_info = pre_market_cache.get_cache_info()
    print(f"\n📊 缓存信息:")
    print(f"  缓存版本: {cache_info['cache_version']}")
    print(f"  缓存日期: {cache_info['cache_date']}")
    print(f"  缓存时间: {cache_info['cache_time']}")
    print(f"  股票数量: {cache_info['total_stocks']}")
    print(f"  是否已加载: {cache_info['is_loaded']}")

    # 测试乖离率计算
    print(f"\n📊 测试乖离率计算:")
    test_codes = ['300606', '688630', '301590']
    test_prices = [38.0, 196.0, 233.0]

    for code, price in zip(test_codes, test_prices):
        bias = pre_market_cache.calculate_ma_bias(code, price)
        print(f"  {code} (价格: {price:.2f}): 乖离率 = {bias}%")
else:
    print("\n❌ 盘前数据预热失败！")

print("\n" + "=" * 80)
print("✅ 盘前数据预热完成！")
print("=" * 80)