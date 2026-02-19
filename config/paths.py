"""
项目路径配置 - 统一管理所有路径，避免硬编码盘符

使用方式：
    from config.paths import SNAPSHOTS_DIR
    snapshot_path = SNAPSHOTS_DIR / "xxx.json"
"""
from pathlib import Path

# 项目根目录（当前文件向上两层）
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"

# 各子目录（按生命周期分类）
SNAPSHOTS_DIR = DATA_DIR / "snapshots"          # 历史快照（90天轮转）
SCAN_RESULTS_DIR = DATA_DIR / "scan_results"  # 扫描结果（4h轮转）
DECISION_LOGS_DIR = DATA_DIR / "decision_logs" # 决策日志（30天轮转）
MINUTE_DATA_DIR = DATA_DIR / "minute_data"    # K线数据（7天轮转）
BACKTEST_RESULTS_DIR = DATA_DIR / "backtest_results"  # 回测结果（永久保留）
EQUITY_INFO_DIR = DATA_DIR / "equity_info"    # 股本信息（定期更新）
SECTOR_MAP_DIR = DATA_DIR / "sector_map"      # 板块映射（定期更新）
REFERENCE_DIR = DATA_DIR / "reference"        # 参考数据（静态）
AUCTION_DIR = DATA_DIR / "auction"            # 竞价数据

# 日志目录
LOGS_DIR = PROJECT_ROOT / "logs" / "application"  # 默认应用程序日志目录
APP_LOGS_DIR = PROJECT_ROOT / "logs" / "application"  # 应用日志目录
PERFORMANCE_LOGS_DIR = PROJECT_ROOT / "logs" / "performance"  # 性能日志目录
BACKTEST_LOGS_DIR = PROJECT_ROOT / "logs" / "backtest"  # 回测日志目录
MONITOR_LOGS_DIR = PROJECT_ROOT / "logs" / "monitor"  # 监控日志目录
SCAN_LOGS_DIR = PROJECT_ROOT / "logs" / "scan"  # 扫描日志目录
AUCTION_LOGS_DIR = PROJECT_ROOT / "logs" / "auction"  # 竞价日志目录
DOWNLOAD_LOGS_DIR = PROJECT_ROOT / "logs" / "download"  # 下载日志目录
CLEANUP_LOGS_DIR = PROJECT_ROOT / "logs" / "cleanup"  # 清理日志目录
DEBUG_LOGS_DIR = PROJECT_ROOT / "logs" / "debug"  # 调试日志目录

# 配置目录
CONFIG_DIR = PROJECT_ROOT / "config"

# 输出目录
OUTPUT_DIR = PROJECT_ROOT / "output"

# 创建目录（如果不存在）
def ensure_directories():
    """确保所有目录存在"""
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    SCAN_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DECISION_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    MINUTE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    EQUITY_INFO_DIR.mkdir(parents=True, exist_ok=True)
    SECTOR_MAP_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    AUCTION_DIR.mkdir(parents=True, exist_ok=True)
    APP_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    PERFORMANCE_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    BACKTEST_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    MONITOR_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SCAN_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    AUCTION_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    CLEANUP_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    # 测试路径配置
    print("项目路径配置测试")
    print("=" * 60)
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"SNAPSHOTS_DIR: {SNAPSHOTS_DIR}")
    print(f"SCAN_RESULTS_DIR: {SCAN_RESULTS_DIR}")
    print(f"DECISION_LOGS_DIR: {DECISION_LOGS_DIR}")
    print(f"MINUTE_DATA_DIR: {MINUTE_DATA_DIR}")
    print(f"BACKTEST_RESULTS_DIR: {BACKTEST_RESULTS_DIR}")
    print(f"LOGS_DIR: {LOGS_DIR}")
    print("=" * 60)

    # 创建所有目录
    ensure_directories()
    print("✅ 所有目录已创建（如果不存在）")