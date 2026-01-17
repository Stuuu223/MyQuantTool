"""
测试 main.py 是否能够正常导入
"""

import sys
import os

print("=" * 60)
print("测试 main.py 导入")
print("=" * 60)

try:
    print("\n📊 正在导入 main.py...")
    import main
    print("✅ main.py 导入成功")
except ModuleNotFoundError as e:
    print(f"❌ 模块导入失败: {e}")
    print(f"\n提示：可能是某些 UI 模块不存在")
except Exception as e:
    print(f"❌ 导入失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)