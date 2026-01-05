"""
Pytest配置文件

提供测试所需的fixture和配置
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    return project_root / "tests" / "data"


@pytest.fixture(scope="function")
def temp_db(tmp_path):
    """临时数据库fixture"""
    from logic.data_manager import DataManager
    
    # 创建临时数据库
    temp_db_path = tmp_path / "test.db"
    db = DataManager(str(temp_db_path))
    
    yield db
    
    # 清理 - 关闭连接后再删除
    try:
        if hasattr(db, 'conn'):
            db.conn.close()
        import os
        if os.path.exists(temp_db_path):
            # 尝试删除，如果失败则跳过（Windows文件锁定问题）
            try:
                os.remove(temp_db_path)
            except PermissionError:
                pass  # Windows文件锁定，跳过删除
    except Exception:
        pass


@pytest.fixture
def mock_stock_data():
    """模拟股票数据"""
    import pandas as pd
    from datetime import datetime, timedelta
    
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    data = {
        'date': dates,
        'open': [100.0 + i * 0.1 for i in range(100)],
        'high': [102.0 + i * 0.1 for i in range(100)],
        'low': [98.0 + i * 0.1 for i in range(100)],
        'close': [100.0 + i * 0.1 for i in range(100)],
        'volume': [1000000 + i * 1000 for i in range(100)],
        'amount': [100000000 + i * 100000 for i in range(100)]
    }
    return pd.DataFrame(data).set_index('date')


@pytest.fixture
def mock_realtime_data():
    """模拟实时数据"""
    return {
        'price': 110.0,
        'change_percent': 10.0,
        'timestamp': '2026-01-05 15:00:00',
        'is_trading': True,
        'volume': 1500000,
        'amount': 165000000
    }


# pytest配置
def pytest_configure(config):
    """Pytest配置"""
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)