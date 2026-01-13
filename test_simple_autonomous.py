"""
简单测试自主学习系统
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from logic.autonomous_learning_system import AutonomousLearningSystem
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_simple():
    """简单测试"""
    print("=" * 70)
    print("简单测试")
    print("=" * 70)
    
    # 创建数据
    np.random.seed(42)
    n = 100
    
    data = pd.DataFrame({
        'date': pd.date_range(start=datetime.now() - timedelta(days=n), periods=n),
        'close': 100 + np.cumsum(np.random.normal(0, 1, n)),
        'volume': np.random.uniform(1000000, 5000000, n),
        'factor1': np.random.randn(n),
        'factor2': np.random.randn(n)
    })
    
    print(f"数据创建完成: {len(data)} 行")
    print(f"列: {data.columns.tolist()}")
    
    # 创建系统
    system = AutonomousLearningSystem()
    
    # 初始化
    print("\n开始初始化...")
    try:
        result = system.initialize(data, target='close')
        print(f"初始化成功!")
        print(f"  特征数量: {result['n_features']}")
        print(f"  最佳模型: {result['best_model_type']}")
        print(f"  最佳分数: {result['best_score']}")
    except Exception as e:
        print(f"初始化失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 系统状态
    print("\n系统状态:")
    status = system.get_system_status()
    print(f"  已初始化: {status['system_state']['initialized']}")
    print(f"  已训练: {status['system_state']['trained']}")
    print(f"  特征数量: {status['n_features']}")
    print(f"  模型类型: {status['model_type']}")
    print(f"  模型对象: {system.model}")
    print(f"  模型类型(type): {type(system.model)}")
    
    if system.model:
        print(f"  模型类型名称: {type(system.model).__name__}")


if __name__ == "__main__":
    test_simple()