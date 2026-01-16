"""
V10.0 基础测试脚本

测试最基本的导入和初始化。

Author: iFlow CLI
Version: V10.0 Enhanced
Date: 2026-01-16
"""

import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, 'E:\\MyQuantTool')

print("\n" + "="*60)
print("V10.0 基础测试")
print("="*60)
print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 测试 1: 导入模块
print("\n测试 1: 导入模块...")
try:
    from logic.data_manager import DataManager
    print("✅ DataManager 导入成功")
except Exception as e:
    print(f"❌ DataManager 导入失败: {e}")
    sys.exit(1)

try:
    from logic.sentiment_analyzer import SentimentAnalyzer
    print("✅ SentimentAnalyzer 导入成功")
except Exception as e:
    print(f"❌ SentimentAnalyzer 导入失败: {e}")
    sys.exit(1)

# 测试 2: 检查代码修改
print("\n测试 2: 检查代码修改...")
try:
    import inspect
    
    # 检查 DataManager 是否有概念映射相关属性
    dm_source = inspect.getsource(DataManager)
    if 'concept_map' in dm_source:
        print("✅ DataManager 包含概念映射代码")
    else:
        print("❌ DataManager 缺少概念映射代码")
        sys.exit(1)
    
    # 检查 SentimentAnalyzer 是否有炸板类型相关代码
    sa_source = inspect.getsource(SentimentAnalyzer)
    if 'benign_zhaban' in sa_source and 'malignant_zhaban' in sa_source:
        print("✅ SentimentAnalyzer 包含炸板类型区分代码")
    else:
        print("❌ SentimentAnalyzer 缺少炸板类型区分代码")
        sys.exit(1)
    
    if 'max_pool_size = min(stock_pool_size, 10)' in sa_source:
        print("✅ SentimentAnalyzer 包含 Token 瘦身代码")
    else:
        print("❌ SentimentAnalyzer 缺少 Token 瘦身代码")
        sys.exit(1)
    
except Exception as e:
    print(f"❌ 代码检查失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("✅ 基础测试通过！")
print("="*60)

print("\n提示：由于概念数据更新需要较长时间，")
print("请运行 'python tools/update_concepts.py' 生成概念数据，")
print("然后运行完整测试。")