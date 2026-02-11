"""
pytest 配置文件
提供全局 fixture 和配置

Author: iFlow CLI
Version: V1.0
Date: 2026-02-11
"""
import pytest
import sys
from pathlib import Path

# 🔥 [关键] 添加项目根目录到 sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    测试环境初始化（会话级别，自动执行）

    功能：
    - 设置测试用环境变量
    - 初始化日志配置
    - 创建测试数据目录
    """
    import os
    import logging

    # 设置测试环境标志
    os.environ['TESTING'] = '1'

    # 关闭调试模式（避免干扰测试输出）
    os.environ.pop('DEBUG_TARGET_STOCK', None)

    # 配置测试日志（只显示 WARNING 及以上）
    logging.basicConfig(
        level=logging.WARNING,
        format='%(levelname)s - %(message)s'
    )

    print("\n" + "="*80)
    print("🧪 测试环境初始化完成")
    print("="*80)

    yield  # 运行测试

    # 清理
    os.environ.pop('TESTING', None)
    print("\n" + "="*80)
    print("✅ 测试环境清理完成")
    print("="*80)


@pytest.fixture
def mock_fund_flow_data():
    """
    Mock 资金流数据（fixture 复用）

    Returns:
        dict: 标准资金流数据结构
    """
    return {
        'trade_date': '20260210',
        'main_net_inflow': 10000000,      # 1000万
        'super_net_inflow': 6000000,      # 600万
        'big_net_inflow': 4000000,        # 400万
        'medium_net_inflow': 2000000,     # 200万
        'small_net_inflow': -2000000,     # -200万
        'close': 25.50,
        'pct_chg': 3.5
    }


# 配置 pytest 输出
def pytest_configure(config):
    """pytest 配置钩子"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )