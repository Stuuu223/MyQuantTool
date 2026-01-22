#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统健康检查脚本

功能：
- 检查目录结构
- 检查数据库连接
- 检查配置文件
- 检查Redis连接
- 生成健康报告

Author: iFlow CLI
Version: V19.6
"""

import os
import sys
from datetime import datetime
from logic.logger import get_logger

logger = get_logger(__name__)


def check_directories() -> dict:
    """
    检查目录结构
    
    Returns:
        dict: 目录检查结果
    """
    logger.info("📁 检查目录结构...")
    
    dirs = [
        "data/review_cases/golden_cases",
        "logs",
        "config",
        "data/kline_cache",
        "data/history"
    ]
    
    result = {
        'status': 'OK',
        'missing_dirs': [],
        'existing_dirs': []
    }
    
    for d in dirs:
        if os.path.exists(d):
            result['existing_dirs'].append(d)
            logger.info(f"✅ 目录存在: {d}")
        else:
            result['missing_dirs'].append(d)
            logger.warning(f"⚠️ 目录缺失: {d}")
    
    if result['missing_dirs']:
        result['status'] = 'WARNING'
    
    return result


def check_database() -> dict:
    """
    检查数据库连接
    
    Returns:
        dict: 数据库检查结果
    """
    logger.info("🗄️ 检查数据库连接...")
    
    result = {
        'status': 'OK',
        'connected': False,
        'tables': 0,
        'error': None
    }
    
    try:
        from logic.database_manager import get_db_manager
        
        db = get_db_manager()
        
        # 测试数据库查询
        sql = "SELECT name FROM sqlite_master WHERE type='table'"
        tables = db.sqlite_query(sql)
        
        if tables:
            result['connected'] = True
            result['tables'] = len(tables)
            logger.info(f"✅ 数据库连接正常，发现 {len(tables)} 个表")
        else:
            result['status'] = 'WARNING'
            logger.warning("⚠️ 数据库连接正常，但没有发现表")
            
    except Exception as e:
        result['status'] = 'ERROR'
        result['error'] = str(e)
        logger.error(f"❌ 数据库连接失败: {e}")
    
    return result


def check_config() -> dict:
    """
    检查配置文件
    
    Returns:
        dict: 配置检查结果
    """
    logger.info("⚙️ 检查配置文件...")
    
    result = {
        'status': 'OK',
        'missing_files': [],
        'existing_files': []
    }
    
    config_files = [
        'config.json',
        'config_system.py',
        'config_database.json'
    ]
    
    for f in config_files:
        if os.path.exists(f):
            result['existing_files'].append(f)
            logger.info(f"✅ 配置文件存在: {f}")
        else:
            result['missing_files'].append(f)
            logger.warning(f"⚠️ 配置文件缺失: {f}")
    
    if result['missing_files']:
        result['status'] = 'WARNING'
    
    return result


def check_redis() -> dict:
    """
    检查Redis连接
    
    Returns:
        dict: Redis检查结果
    """
    logger.info("🔴 检查Redis连接...")
    
    result = {
        'status': 'OK',
        'connected': False,
        'error': None
    }
    
    try:
        from logic.database_manager import get_db_manager
        
        db = get_db_manager()
        
        # 检查Redis连接
        if hasattr(db, '_redis_client') and db._redis_client:
            db._redis_client.ping()
            result['connected'] = True
            logger.info("✅ Redis连接正常")
        else:
            result['status'] = 'WARNING'
            logger.warning("⚠️ Redis未连接")
            
    except Exception as e:
        result['status'] = 'ERROR'
        result['error'] = str(e)
        logger.error(f"❌ Redis连接失败: {e}")
    
    return result


def check_dependencies() -> dict:
    """
    检查依赖包
    
    Returns:
        dict: 依赖检查结果
    """
    logger.info("📦 检查依赖包...")
    
    result = {
        'status': 'OK',
        'missing_packages': [],
        'existing_packages': []
    }
    
    required_packages = [
        'pandas',
        'streamlit',
        'plotly',
        'akshare',
        'sqlalchemy',
        'requests'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            result['existing_packages'].append(package)
            logger.info(f"✅ 依赖包已安装: {package}")
        except ImportError:
            result['missing_packages'].append(package)
            logger.warning(f"⚠️ 依赖包缺失: {package}")
    
    if result['missing_packages']:
        result['status'] = 'WARNING'
    
    return result


def generate_report(directories: dict, database: dict, config: dict, redis: dict, dependencies: dict) -> dict:
    """
    生成健康报告
    
    Args:
        directories: 目录检查结果
        database: 数据库检查结果
        config: 配置检查结果
        redis: Redis检查结果
        dependencies: 依赖检查结果
    
    Returns:
        dict: 健康报告
    """
    report = {
        'timestamp': datetime.now().isoformat(),
        'overall_status': 'OK',
        'checks': {
            'directories': directories,
            'database': database,
            'config': config,
            'redis': redis,
            'dependencies': dependencies
        },
        'summary': {
            'total_checks': 5,
            'ok_checks': 0,
            'warning_checks': 0,
            'error_checks': 0
        }
    }
    
    # 统计检查结果
    for check_name, check_result in report['checks'].items():
        status = check_result['status']
        if status == 'OK':
            report['summary']['ok_checks'] += 1
        elif status == 'WARNING':
            report['summary']['warning_checks'] += 1
        elif status == 'ERROR':
            report['summary']['error_checks'] += 1
    
    # 确定整体状态
    if report['summary']['error_checks'] > 0:
        report['overall_status'] = 'ERROR'
    elif report['summary']['warning_checks'] > 0:
        report['overall_status'] = 'WARNING'
    
    return report


def main():
    """
    主函数
    """
    print("=" * 80)
    print("🏥 MyQuantTool 系统健康检查")
    print(f"📅 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 执行各项检查
    directories = check_directories()
    database = check_database()
    config = check_config()
    redis = check_redis()
    dependencies = check_dependencies()
    
    # 生成报告
    report = generate_report(directories, database, config, redis, dependencies)
    
    # 显示报告
    print("\n" + "=" * 80)
    print("📊 健康检查报告")
    print("=" * 80)
    
    print(f"\n📁 目录结构: {directories['status']}")
    if directories['missing_dirs']:
        print(f"   缺失目录: {', '.join(directories['missing_dirs'])}")
    
    print(f"\n🗄️ 数据库: {database['status']}")
    if database['connected']:
        print(f"   表数量: {database['tables']}")
    if database['error']:
        print(f"   错误: {database['error']}")
    
    print(f"\n⚙️ 配置文件: {config['status']}")
    if config['missing_files']:
        print(f"   缺失文件: {', '.join(config['missing_files'])}")
    
    print(f"\n🔴 Redis: {redis['status']}")
    if redis['connected']:
        print(f"   连接状态: 正常")
    else:
        print(f"   连接状态: 未连接")
    if redis['error']:
        print(f"   错误: {redis['error']}")
    
    print(f"\n📦 依赖包: {dependencies['status']}")
    if dependencies['missing_packages']:
        print(f"   缺失包: {', '.join(dependencies['missing_packages'])}")
    
    print("\n" + "=" * 80)
    print("📊 总结")
    print("=" * 80)
    print(f"总检查项: {report['summary']['total_checks']}")
    print(f"✅ 正常: {report['summary']['ok_checks']}")
    print(f"⚠️ 警告: {report['summary']['warning_checks']}")
    print(f"❌ 错误: {report['summary']['error_checks']}")
    print(f"\n整体状态: {report['overall_status']}")
    
    # 返回退出码
    if report['overall_status'] == 'OK':
        print("\n✅ 系统健康，一切正常！")
        return 0
    elif report['overall_status'] == 'WARNING':
        print("\n⚠️ 系统存在一些警告，建议修复。")
        return 1
    else:
        print("\n❌ 系统存在严重问题，请立即修复！")
        return 2


if __name__ == '__main__':
    sys.exit(main())
