"""
MyQuantTool 启动脚本
"""

import os
import sys
import subprocess


def check_dependencies():
    """检查依赖是否安装"""
    print("检查依赖...")
    
    required_packages = [
        'pandas',
        'streamlit',
        'plotly',
        'akshare',
        'sqlalchemy'
    ]
    
    optional_packages = [
        'tensorflow',
        'xgboost',
        'requests'
    ]
    
    missing_required = []
    missing_optional = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_required.append(package)
    
    for package in optional_packages:
        try:
            __import__(package)
        except ImportError:
            missing_optional.append(package)
    
    if missing_required:
        print(f"❌ 缺少必需依赖: {', '.join(missing_required)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    if missing_optional:
        print(f"⚠️  缺少可选依赖: {', '.join(missing_optional)}")
        print("部分功能可能不可用")
    
    print("✅ 依赖检查通过")
    return True


def check_database():
    """检查数据库"""
    print("检查数据库...")
    
    db_path = 'data/stock_data.db'
    
    if not os.path.exists(db_path):
        print(f"⚠️  数据库不存在: {db_path}")
        print("首次运行时将自动创建数据库")
    else:
        print(f"✅ 数据库存在: {db_path}")
    
    return True


def check_config():
    """检查配置文件"""
    print("检查配置文件...")
    
    config_file = 'config.json'
    
    if not os.path.exists(config_file):
        print(f"⚠️  配置文件不存在: {config_file}")
        print("将使用默认配置")
    else:
        print(f"✅ 配置文件存在: {config_file}")
    
    return True


def start_app():
    """启动应用"""
    print("\n" + "=" * 50)
    print("MyQuantTool 启动中...")
    print("=" * 50 + "\n")
    
    # 检查依赖
    if not check_dependencies():
        return False
    
    # 检查数据库
    if not check_database():
        return False
    
    # 检查配置
    if not check_config():
        return False
    
    print("\n✅ 所有检查通过，启动应用...\n")
    
    # 启动Streamlit
    try:
        subprocess.run([sys.executable, '-m', 'streamlit', 'run', 'main.py'])
    except KeyboardInterrupt:
        print("\n\n应用已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        return False
    
    return True


if __name__ == '__main__':
    start_app()
