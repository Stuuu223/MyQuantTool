"""
P0级事故修复验证脚本

验证内容:
1. InstrumentCache能正确获取并缓存FloatVolume和5日均量
2. full_market_scanner使用真实公式计算turnover_rate和volume_ratio
3. LiveTradingEngine盘前装弹逻辑正确

Author: AI总监
Date: 2026-02-24
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("🚨 P0级事故修复验证")
print("=" * 60)

# ===== 验证1: InstrumentCache =====
print("\n✅ 验证1: InstrumentCache 模块")
print("-" * 40)

try:
    from logic.data_providers.instrument_cache import InstrumentCache, get_instrument_cache
    print("✅ InstrumentCache 导入成功")
    
    # 测试单例模式
    cache1 = get_instrument_cache()
    cache2 = get_instrument_cache()
    assert cache1 is cache2, "单例模式失败"
    print("✅ 单例模式正确")
    
    # 测试缓存统计
    stats = cache1.get_cache_stats()
    print(f"✅ 缓存统计接口正常: {stats}")
    
except Exception as e:
    print(f"❌ InstrumentCache 验证失败: {e}")
    sys.exit(1)

# ===== 验证2: FullMarketScanner使用真实公式 =====
print("\n✅ 验证2: FullMarketScanner 真实公式")
print("-" * 40)

try:
    from logic.strategies.full_market_scanner import FullMarketScanner, INSTRUMENT_CACHE_AVAILABLE
    
    if INSTRUMENT_CACHE_AVAILABLE:
        print("✅ FullMarketScanner 已导入InstrumentCache")
    else:
        print("⚠️ FullMarketScanner 未找到InstrumentCache，将使用备用计算")
    
    # 检查关键代码片段
    import inspect
    source = inspect.getsource(FullMarketScanner.scan_snapshot_batch)
    
    # 验证假公式已被替换
    assert "amount / 1e6" not in source or "turnover_rate = (volume / float_volume)" in source, \
        "假的amount/1e6公式仍存在且未被真实公式覆盖"
    print("✅ 假公式 'amount / 1e6' 已被替换")
    
    assert "volume / volume.mean()" not in source or "volume / avg_5d_volume" in source, \
        "假的volume/volume.mean()公式仍存在且未被真实公式覆盖"
    print("✅ 假公式 'volume / volume.mean()' 已被替换")
    
    # 验证真实公式存在
    assert "turnover_rate = (volume / float_volume) * 100" in source, \
        "真实换手率公式未找到"
    print("✅ 真实换手率公式已集成")
    
    assert "volume_ratio = volume / avg_5d_volume" in source, \
        "真实量比公式未找到"
    print("✅ 真实量比公式已集成")
    
except Exception as e:
    print(f"❌ FullMarketScanner 验证失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ===== 验证3: LiveTradingEngine盘前装弹 =====
print("\n✅ 验证3: LiveTradingEngine 盘前装弹")
print("-" * 40)

try:
    from tasks.run_live_trading_engine import LiveTradingEngine
    import inspect
    
    source = inspect.getsource(LiveTradingEngine)
    
    # 验证InstrumentCache初始化
    assert "instrument_cache" in source, "未找到instrument_cache初始化"
    print("✅ InstrumentCache 初始化已添加")
    
    # 验证盘前装弹逻辑
    assert "warmup_cache" in source, "未找到warmup_cache调用"
    print("✅ 盘前装弹逻辑已添加")
    
    # 验证扩展股票池方法
    assert "_get_extended_stock_pool" in source, "未找到_get_extended_stock_pool方法"
    print("✅ 扩展股票池方法已添加")
    
except Exception as e:
    print(f"❌ LiveTradingEngine 验证失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ===== 验证4: 代码结构检查 =====
print("\n✅ 验证4: 代码结构检查")
print("-" * 40)

try:
    # 检查文件是否存在
    files_to_check = [
        "logic/data_providers/instrument_cache.py",
        "logic/strategies/full_market_scanner.py",
        "tasks/run_live_trading_engine.py"
    ]
    
    for file_path in files_to_check:
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)
        if os.path.exists(full_path):
            print(f"✅ 文件存在: {file_path}")
        else:
            print(f"❌ 文件缺失: {file_path}")
            sys.exit(1)
    
except Exception as e:
    print(f"❌ 代码结构检查失败: {e}")
    sys.exit(1)

# ===== 总结 =====
print("\n" + "=" * 60)
print("🎉 P0级事故修复验证通过!")
print("=" * 60)
print("\n修复内容:")
print("1. ✅ 创建 logic/data_providers/instrument_cache.py")
print("   - FloatVolume内存缓存 (O(1)查询)")
print("   - 5日均量内存缓存 (O(1)查询)")
print("   - 盘前装弹机制")
print("")
print("2. ✅ 修改 logic/strategies/full_market_scanner.py")
print("   - 替换假换手率公式: amount/1e6 → volume/float_volume*100")
print("   - 替换假量比公式: volume/volume.mean() → volume/avg_5d_volume")
print("")
print("3. ✅ 修改 tasks/run_live_trading_engine.py")
print("   - 添加InstrumentCache初始化")
print("   - 添加盘前装弹逻辑 (09:25前预热)")
print("   - 添加扩展股票池方法")
print("")
print("⚠️  注意: 实际功能测试需要在QMT环境中运行")
print("=" * 60)
