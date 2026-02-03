"""
诊断 xtquant/xtdata 导入问题

用于诊断 IPythonApiClient DLL load failed 问题
"""
import os
import sys
import platform

# 🚀 添加项目根目录到 Python 路径（这是关键！）
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print("="*80)
print("环境诊断 - xtquant/xtdata 导入测试")
print("="*80)
print(f"\n项目根目录: {project_root}")
print(f"是否在 sys.path 中: {project_root in sys.path}")

print("\n1. Python 环境:")
print(f"   Python 版本: {sys.version}")
print(f"   Python 可执行文件: {sys.executable}")
print(f"   平台: {platform.platform()}")
print(f"   架构: {platform.architecture()}")

print("\n2. PATH 环境变量（前300字符）:")
path = os.environ.get("PATH", "")
print(f"   {path[:300]}")

print("\n3. 检查 xtquant 模块:")
try:
    import xtquant
    print(f"   ✅ xtquant 导入成功")
    print(f"   xtquant 路径: {xtquant.__file__}")
except Exception as e:
    print(f"   ❌ xtquant 导入失败: {repr(e)}")

print("\n4. 检查 xtdata 模块:")
try:
    from xtquant import xtdata
    print(f"   ✅ xtdata 导入成功")
    print(f"   xtdata 路径: {xtdata.__file__}")
    
    # 尝试调用基本方法
    print("\n5. 测试 xtdata 基本方法:")
    try:
        # 测试 get_market_data 方法
        print(f"   ✅ xtdata.get_market_data 方法存在: {hasattr(xtdata, 'get_market_data')}")
    except Exception as e:
        print(f"   ⚠️ xtdata 方法测试失败: {repr(e)}")
        
except Exception as e:
    print(f"   ❌ xtdata 导入失败")
    print(f"   错误类型: {type(e).__name__}")
    print(f"   错误详情: {repr(e)}")
    
    # 导入 traceback 获取完整堆栈
    import traceback
    print("\n6. 完整堆栈跟踪:")
    traceback.print_exc()

print("\n7. 检查 IPythonApiClient 模块:")
try:
    import importlib.util
    spec = importlib.util.find_spec("xtquant.IPythonApiClient")
    if spec:
        print(f"   ✅ 找到 IPythonApiClient 模块")
        print(f"   路径: {spec.origin}")
        
        # 检查 .pyd 文件
        pyd_path = spec.origin
        if pyd_path and pyd_path.endswith('.pyd'):
            print(f"   ✅ 这是二进制扩展模块 (.pyd)")
            print(f"   文件存在: {os.path.exists(pyd_path)}")
    else:
        print(f"   ❌ 未找到 IPythonApiClient 模块")
except Exception as e:
    print(f"   ❌ IPythonApiClient 检查失败: {repr(e)}")

print("\n8. 检查系统依赖 DLL (Windows):")
if platform.system() == "Windows":
    try:
        import ctypes
        # 检查 VC++ 运行库
        vc_dlls = [
            "msvcp140.dll",
            "vcruntime140.dll",
            "api-ms-win-crt-runtime-l1-1-0.dll",
            "api-ms-win-crt-stdio-l1-1-0.dll",
            "api-ms-win-crt-math-l1-1-0.dll"
        ]
        
        system_path = os.environ.get("SystemRoot", r"C:\Windows")
        system32 = os.path.join(system_path, "System32")
        
        for dll in vc_dlls:
            dll_path = os.path.join(system32, dll)
            exists = os.path.exists(dll_path)
            status = "✅" if exists else "❌"
            print(f"   {status} {dll}: {dll_path}")
    except Exception as e:
        print(f"   ❌ DLL 检查失败: {repr(e)}")

print("\n" + "="*80)
print("诊断完成")
print("="*80)