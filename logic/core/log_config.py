# -*- coding: utf-8 -*-
"""
日志配置模块 - 精简版
统一管理所有日志输出级别
"""
import logging
import os
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def setup_scan_logging(
    scan_level: LogLevel = "WARNING",
    root_level: LogLevel = "INFO",
    qmt_level: LogLevel = "WARNING"
):
    """
    配置扫描系统日志输出

    Args:
        scan_level: 扫描模块日志级别（建议 WARNING 或 ERROR）
        root_level: 根日志级别（建议 INFO）
        qmt_level: QMT 模块日志级别（建议 WARNING）
    """

    # 1. 设置根 logger 级别
    logging.getLogger().setLevel(root_level)

    # 2. 扫描相关模块（精简输出）
    scan_modules = [
        "logic.fund_flow_analyzer",          # 资金流分析器
        "logic.full_market_scanner",         # 全市场扫描器
        "logic.rolling_metrics",             # 滚动指标计算器
        "logic.capital_classifier",          # 资金性质分类器
        "logic.trap_detector",               # 诱多陷阱检测器
        "logic.enhanced_stock_analyzer",     # 增强股票分析器
        "logic.sector_resonance",            # 板块共振分析器
        "logic.risk_manager",                # 风险管理器
    ]

    for module in scan_modules:
        logging.getLogger(module).setLevel(scan_level)

    # 3. QMT 相关模块（只显示警告和错误）
    qmt_modules = [
        "logic.qmt_health_check",            # QMT 健康检查
        "logic.qmt_tick_monitor",            # QMT Tick 监控器
        "data_sources.qmt_source",           # QMT 数据源
    ]

    for module in qmt_modules:
        logging.getLogger(module).setLevel(qmt_level)

    # 4. 关键业务模块（保持 INFO 级别）
    critical_modules = [
        "__main__",                          # 主程序入口
        "logic.event_detector",              # 事件检测器
        "logic.event_recorder",              # 事件记录器
        "logic.market_phase_checker",        # 市场阶段检查器
    ]

    for module in critical_modules:
        logging.getLogger(module).setLevel("INFO")

    # 5. 第三方库（完全静默）
    third_party_modules = [
        "urllib3",
        "requests",
        "akshare",
        "pandas",
        "numpy",
    ]

    for module in third_party_modules:
        logging.getLogger(module).setLevel("ERROR")

    # 6. 打印配置摘要
    print("=" * 80)
    print("📋 日志配置完成")
    print("=" * 80)
    print(f"[OK] 根日志级别: {root_level}")
    print(f"[OK] 扫描模块级别: {scan_level}")
    print(f"[OK] QMT 模块级别: {qmt_level}")
    print(f"[OK] 精简模块数: {len(scan_modules)}")
    print("=" * 80)
    print()


def setup_logging_from_env():
    """
    从环境变量读取日志配置

    环境变量:
        SCAN_LOG_LEVEL: 扫描模块日志级别（默认 WARNING）
        ROOT_LOG_LEVEL: 根日志级别（默认 INFO）
        QMT_LOG_LEVEL: QMT 模块日志级别（默认 WARNING）

    用法:
        # Linux/Mac
        export SCAN_LOG_LEVEL=ERROR
        export QMT_LOG_LEVEL=WARNING

        # Windows (PowerShell)
        $env:SCAN_LOG_LEVEL="ERROR"
        $env:QMT_LOG_LEVEL="WARNING"
    """
    scan_level = os.getenv("SCAN_LOG_LEVEL", "WARNING")
    root_level = os.getenv("ROOT_LOG_LEVEL", "INFO")
    qmt_level = os.getenv("QMT_LOG_LEVEL", "WARNING")

    setup_scan_logging(
        scan_level=scan_level,  # type: ignore
        root_level=root_level,  # type: ignore
        qmt_level=qmt_level     # type: ignore
    )


def setup_ultra_quiet_logging():
    """
    极简模式：只显示关键信息和错误

    适用场景:
        - 长时间运行的监控程序
        - 只关心结果，不关心过程
        - 需要清晰的终端输出
    """
    setup_scan_logging(
        scan_level="ERROR",      # 扫描模块只显示错误
        root_level="INFO",       # 根级别保持 INFO（显示关键汇总）
        qmt_level="ERROR"        # QMT 模块只显示错误
    )


# ===== 快速配置预设 =====

def use_debug_mode():
    """调试模式：显示所有日志"""
    setup_scan_logging(scan_level="DEBUG", root_level="DEBUG", qmt_level="DEBUG")


def use_normal_mode():
    """正常模式：显示警告和错误"""
    setup_scan_logging(scan_level="WARNING", root_level="INFO", qmt_level="WARNING")


def use_quiet_mode():
    """安静模式：只显示错误"""
    setup_ultra_quiet_logging()


# ===== 默认配置 =====
if __name__ == "__main__":
    # 测试配置
    print("📝 日志配置模块测试")
    print()

    print("1️⃣ 正常模式:")
    use_normal_mode()

    print("\n2️⃣ 安静模式:")
    use_quiet_mode()

    print("\n3️⃣ 调试模式:")
    use_debug_mode()


# ===== 条件编译：调试目标股票 =====
# 调试模式标志（通过环境变量控制）
DEBUG_TARGET_STOCK = os.environ.get('DEBUG_TARGET_STOCK', '')  # 默认为空（关闭）


def is_debug_target(stock_code: str) -> bool:
    """
    判断是否为调试目标股票

    Args:
        stock_code: 股票代码

    Returns:
        bool: 是否启用调试输出

    Example:
        # 启用调试：export DEBUG_TARGET_STOCK=601869.SH
        # 关闭调试：unset DEBUG_TARGET_STOCK

        # 调试多只股票（逗号分隔）
        # export DEBUG_TARGET_STOCK=601869.SH,300997.SZ
    """
    if not DEBUG_TARGET_STOCK:
        return False

    # 支持多个股票（逗号分隔）
    target_stocks = [s.strip() for s in DEBUG_TARGET_STOCK.split(',')]
    return stock_code in target_stocks