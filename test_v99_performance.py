"""
V9.9 性能测试脚本

测试内容：
1. 懒加载+缓存机制的性能提升
2. 股票池过滤机制的性能提升
3. 整体扫描性能的提升
"""

import time
import os
from logic.data_manager import DataManager
from logic.algo import QuantAlgo


def test_lazy_loading_cache():
    """测试懒加载+缓存机制"""
    print("=" * 60)
    print("测试1：懒加载+缓存机制")
    print("=" * 60)
    
    # 测试股票列表
    test_stocks = ['300568', '000001', '600519', '000002', '600036']
    
    db = DataManager()
    
    # 第一次获取（无缓存）
    print("\n📊 第一次获取（无缓存）：")
    start_time = time.time()
    for stock in test_stocks:
        data = db.get_realtime_data(stock)
        if data:
            print(f"  {stock}: {data['price']:.2f}元")
    first_time = time.time() - start_time
    print(f"  耗时: {first_time:.3f}秒")
    
    # 第二次获取（有内存缓存）
    print("\n📊 第二次获取（有内存缓存）：")
    start_time = time.time()
    for stock in test_stocks:
        data = db.get_realtime_data(stock)
        if data:
            print(f"  {stock}: {data['price']:.2f}元")
    second_time = time.time() - start_time
    print(f"  耗时: {second_time:.3f}秒")
    
    # 计算性能提升
    speedup = first_time / second_time if second_time > 0 else 0
    print(f"\n✅ 性能提升: {speedup:.1f}倍")
    
    return first_time, second_time


def test_stock_pool_filter():
    """测试股票池过滤机制"""
    print("\n" + "=" * 60)
    print("测试2：股票池过滤机制")
    print("=" * 60)
    
    # 获取全市场数据
    db = DataManager()
    
    print("\n📊 获取市场数据（小样本测试）...")
    start_time = time.time()
    
    # 使用小样本测试（50只股票）
    test_stocks = ['000001', '000002', '600000', '600036', '600519', '300568', '300063', '002594', '000858', '002415']
    
    realtime_data = db.get_fast_price(test_stocks)
    fetch_time = time.time() - start_time
    print(f"  耗时: {fetch_time:.3f}秒")
    print(f"  获取到: {len(realtime_data)} 只股票")
    
    # 转换为列表格式
    all_stocks = []
    for full_code, data in realtime_data.items():
        try:
            current_price = float(data.get('now', 0))
            last_close = float(data.get('close', 0))
            
            if current_price == 0 or last_close == 0:
                continue
            
            pct_change = (current_price - last_close) / last_close * 100
            
            # 提取股票代码
            if len(full_code) == 6:
                code = full_code
            elif len(full_code) > 6:
                code = full_code[2:]
            else:
                continue
            
            name = data.get('name', '')
            
            all_stocks.append({
                '代码': code,
                '名称': name,
                '最新价': current_price,
                '涨跌幅': pct_change,
                '成交量': data.get('volume', 0) / 100,
                '成交额': data.get('turnover', 0)
            })
        except Exception as e:
            continue
    
    print(f"  转换后: {len(all_stocks)} 只股票")
    
    # 测试过滤
    print("\n📊 应用股票池过滤...")
    start_time = time.time()
    
    filtered_stocks = QuantAlgo.filter_active_stocks(
        all_stocks,
        min_change_pct=3.0,
        min_volume=5000,
        min_amount=3000
    )
    
    filter_time = time.time() - start_time
    print(f"  耗时: {filter_time:.3f}秒")
    print(f"  过滤前: {len(all_stocks)} 只")
    print(f"  过滤后: {len(filtered_stocks)} 只")
    print(f"  过滤比例: {len(filtered_stocks) / len(all_stocks) * 100:.1f}%")
    
    return fetch_time, filter_time, len(all_stocks), len(filtered_stocks)


def test_disk_cache():
    """测试磁盘缓存"""
    print("\n" + "=" * 60)
    print("测试3：磁盘缓存机制")
    print("=" * 60)
    
    db = DataManager()
    test_stock = '300568'
    
    # 清除缓存
    cache_path = db._get_kline_cache_path(test_stock)
    if os.path.exists(cache_path):
        os.remove(cache_path)
        print(f"  已清除缓存: {cache_path}")
    
    # 第一次获取（无磁盘缓存）
    print(f"\n📊 第一次获取 {test_stock}（无磁盘缓存）：")
    start_time = time.time()
    data = db.get_realtime_data(test_stock)
    first_time = time.time() - start_time
    print(f"  耗时: {first_time:.3f}秒")
    
    # 检查缓存是否创建
    if os.path.exists(cache_path):
        print(f"  ✅ 磁盘缓存已创建: {cache_path}")
        cache_size = os.path.getsize(cache_path)
        print(f"  缓存大小: {cache_size / 1024:.2f} KB")
    else:
        print(f"  ⚠️ 磁盘缓存未创建")
    
    # 第二次获取（有磁盘缓存）
    print(f"\n📊 第二次获取 {test_stock}（有磁盘缓存）：")
    start_time = time.time()
    data = db.get_realtime_data(test_stock)
    second_time = time.time() - start_time
    print(f"  耗时: {second_time:.3f}秒")
    
    # 计算性能提升
    speedup = first_time / second_time if second_time > 0 else 0
    print(f"\n✅ 性能提升: {speedup:.1f}倍")
    
    return first_time, second_time


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("V9.9 性能测试")
    print("=" * 60)
    
    # 测试1：懒加载+缓存机制
    first_time, second_time = test_lazy_loading_cache()
    
    # 测试2：股票池过滤机制
    fetch_time, filter_time, before_count, after_count = test_stock_pool_filter()
    
    # 测试3：磁盘缓存
    cache_first_time, cache_second_time = test_disk_cache()
    
    # 总结
    print("\n" + "=" * 60)
    print("性能测试总结")
    print("=" * 60)
    print(f"\n1. 内存缓存性能提升: {first_time / second_time:.1f}倍")
    print(f"2. 股票池过滤: {before_count} 只 → {after_count} 只 ({after_count / before_count * 100:.1f}%)")
    print(f"   预计K线下载时间减少: {(1 - after_count / before_count) * 100:.1f}%")
    print(f"3. 磁盘缓存性能提升: {cache_first_time / cache_second_time:.1f}倍")
    
    print("\n✅ V9.9 优化效果：")
    print("  - 懒加载机制：按需加载数据，避免不必要的网络请求")
    print("  - 内存缓存：60秒内重复查询直接返回缓存")
    print("  - 磁盘缓存：K线数据缓存2小时，重启后依然有效")
    print("  - 股票池过滤：减少需要下载K线的股票数量，大幅提升扫描速度")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()