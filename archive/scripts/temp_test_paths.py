"""
测试路径配置和目录创建
"""
from config.paths import (
    PROJECT_ROOT,
    DATA_DIR,
    REBUILD_SNAP_DIR,
    SCAN_RESULTS_DIR,
    REVIEW_DIR,
    STOCK_ANALYSIS_DIR,
    KLINE_CACHE_DIR,
    LOGS_DIR,
    OUTPUT_DIR,
    BACKTEST_RESULTS_DIR,
    ensure_directories
)

print("=" * 60)
print("路径配置测试")
print("=" * 60)

print(f"\n项目根目录:")
print(f"  PROJECT_ROOT: {PROJECT_ROOT}")

print(f"\n数据目录:")
print(f"  DATA_DIR: {DATA_DIR}")
print(f"  REBUILD_SNAP_DIR: {REBUILD_SNAP_DIR}")
print(f"  SCAN_RESULTS_DIR: {SCAN_RESULTS_DIR}")
print(f"  REVIEW_DIR: {REVIEW_DIR}")
print(f"  STOCK_ANALYSIS_DIR: {STOCK_ANALYSIS_DIR}")
print(f"  KLINE_CACHE_DIR: {KLINE_CACHE_DIR}")

print(f"\n其他目录:")
print(f"  LOGS_DIR: {LOGS_DIR}")
print(f"  OUTPUT_DIR: {OUTPUT_DIR}")
print(f"  BACKTEST_RESULTS_DIR: {BACKTEST_RESULTS_DIR}")

# 检查目录是否存在
print(f"\n目录存在性检查:")
directories = {
    "REBUILD_SNAP_DIR": REBUILD_SNAP_DIR,
    "SCAN_RESULTS_DIR": SCAN_RESULTS_DIR,
    "REVIEW_DIR": REVIEW_DIR,
    "STOCK_ANALYSIS_DIR": STOCK_ANALYSIS_DIR,
    "KLINE_CACHE_DIR": KLINE_CACHE_DIR,
    "LOGS_DIR": LOGS_DIR,
    "OUTPUT_DIR": OUTPUT_DIR,
    "BACKTEST_RESULTS_DIR": BACKTEST_RESULTS_DIR,
}

for name, path in directories.items():
    exists = path.exists()
    print(f"  {name}: {'✅ 存在' if exists else '❌ 不存在'}")

# 创建所有目录
print(f"\n创建目录...")
ensure_directories()
print("✅ 所有目录已创建（如果不存在）")

# 再次检查目录是否存在
print(f"\n再次检查目录存在性:")
for name, path in directories.items():
    exists = path.exists()
    print(f"  {name}: {'✅ 存在' if exists else '❌ 不存在'}")

# 测试路径拼接
print(f"\n路径拼接测试:")
test_snapshot = REBUILD_SNAP_DIR / "full_market_snapshot_20260208_rebuild.json"
print(f"  测试快照路径: {test_snapshot}")
print(f"  是否存在: {'✅ 存在' if test_snapshot.exists() else '❌ 不存在'}")

print("\n" + "=" * 60)
print("✅ 路径配置测试完成！")
print("=" * 60)
print("\n关键优势:")
print("  ✓ 所有路径相对项目根目录")
print("  ✓ 不绑定盘符，支持多设备开发")
print("  ✓ 集中管理，修改方便")
print("  ✓ 自动创建目录，避免路径错误")
print("=" * 60 + "\n")