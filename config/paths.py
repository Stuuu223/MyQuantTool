"""
项目路径配置 - 统一管理所有路径，避免硬编码盘符

使用方式：
    from config.paths import REBUILD_SNAP_DIR
    snapshot_path = REBUILD_SNAP_DIR / "xxx.json"
"""
from pathlib import Path

# 项目根目录（当前文件向上两层）
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"

# 各子目录
REBUILD_SNAP_DIR = DATA_DIR / "rebuild_snapshots"
SCAN_RESULTS_DIR = DATA_DIR / "scan_results"
REVIEW_DIR = DATA_DIR / "review"
STOCK_ANALYSIS_DIR = DATA_DIR / "stock_analysis"
KLINE_CACHE_DIR = DATA_DIR / "kline_cache"

# 日志目录
LOGS_DIR = PROJECT_ROOT / "logs"

# 配置目录
CONFIG_DIR = PROJECT_ROOT / "config"

# 输出目录
OUTPUT_DIR = PROJECT_ROOT / "output"

# 回测结果目录
BACKTEST_RESULTS_DIR = OUTPUT_DIR / "backtest_results"

# 创建目录（如果不存在）
def ensure_directories():
    """确保所有目录存在"""
    REBUILD_SNAP_DIR.mkdir(parents=True, exist_ok=True)
    SCAN_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    STOCK_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    KLINE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    # 测试路径配置
    print("项目路径配置测试")
    print("=" * 60)
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"REBUILD_SNAP_DIR: {REBUILD_SNAP_DIR}")
    print(f"SCAN_RESULTS_DIR: {SCAN_RESULTS_DIR}")
    print(f"LOGS_DIR: {LOGS_DIR}")
    print(f"BACKTEST_RESULTS_DIR: {BACKTEST_RESULTS_DIR}")
    print("=" * 60)

    # 创建所有目录
    ensure_directories()
    print("✅ 所有目录已创建（如果不存在）")