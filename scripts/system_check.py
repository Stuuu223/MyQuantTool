#!/usr/bin/env python3
"""
系统检查工具 - 统一入口 (System Check)

整合所有检查脚本，通过参数控制检查类型：
- connection: QMT连接状态
- data: 数据完整性
- config: 配置一致性
- all: 全部检查

取代脚本：
- check_download_status.py
- check_qmt_local_data.py
- check_qmt_vip_data.py
- check_download_status.bat
- check_data_size.bat

Author: AI Project Director
Version: V1.0
Date: 2026-02-19
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.data_providers.tick_provider import TickProvider
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def check_qmt_connection() -> Tuple[bool, str]:
    """检查QMT连接状态"""
    logger.info("检查QMT连接状态...")
    
    try:
        with TickProvider() as provider:
            if provider.connect():
                return True, "✅ QMT连接正常"
            else:
                return False, "❌ QMT连接失败"
    except Exception as e:
        return False, f"❌ QMT连接异常: {e}"


def check_data_integrity() -> Tuple[bool, str]:
    """检查数据完整性"""
    logger.info("检查数据完整性...")
    
    data_dir = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir'
    
    if not data_dir.exists():
        return False, f"❌ 数据目录不存在: {data_dir}"
    
    # 检查关键子目录
    required_subdirs = ['daily', 'tick', '1m']
    missing = []
    
    for subdir in required_subdirs:
        if not (data_dir / subdir).exists():
            missing.append(subdir)
    
    if missing:
        return False, f"⚠️  缺失子目录: {', '.join(missing)}"
    
    return True, f"✅ 数据目录结构正常 ({data_dir})"


def check_config_consistency() -> Tuple[bool, str]:
    """检查配置一致性"""
    logger.info("检查配置一致性...")
    
    issues = []
    
    # 检查必要配置文件
    required_configs = [
        'config/config.json',
        'config/paths.py',
        'config/true_attack_config.json'
    ]
    
    for config_file in required_configs:
        config_path = PROJECT_ROOT / config_file
        if not config_path.exists():
            issues.append(f"缺失配置文件: {config_file}")
    
    # 检查数据路径配置
    try:
        from config.paths import DATA_DIR
        if not Path(DATA_DIR).exists():
            issues.append(f"DATA_DIR不存在: {DATA_DIR}")
    except ImportError as e:
        issues.append(f"无法导入paths配置: {e}")
    
    if issues:
        return False, "⚠️  配置问题:\n" + "\n".join(f"  - {issue}" for issue in issues)
    
    return True, "✅ 配置一致性检查通过"


def check_tick_coverage() -> Tuple[bool, str]:
    """检查Tick数据覆盖"""
    logger.info("检查顽主股票池Tick数据覆盖...")
    
    try:
        # 加载股票池
        csv_path = PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv'
        import pandas as pd
        df = pd.read_csv(csv_path)
        
        stock_codes = []
        for _, row in df.head(20).iterrows():  # 只检查前20只
            code = str(row['code']).zfill(6)
            if code.startswith('6'):
                stock_codes.append(f"{code}.SH")
            else:
                stock_codes.append(f"{code}.SZ")
        
        with TickProvider() as provider:
            results = provider.check_coverage(stock_codes)
            
            # 统计覆盖率
            total = len(results)
            has_data = sum(1 for r in results.values() if r.get('exists', False))
            coverage_pct = has_data / total * 100 if total > 0 else 0
            
            if coverage_pct >= 90:
                return True, f"✅ Tick数据覆盖良好: {coverage_pct:.1f}% ({has_data}/{total})"
            elif coverage_pct >= 50:
                return False, f"⚠️  Tick数据覆盖不足: {coverage_pct:.1f}% ({has_data}/{total})"
            else:
                return False, f"❌ Tick数据覆盖严重不足: {coverage_pct:.1f}% ({has_data}/{total})"
    
    except Exception as e:
        return False, f"❌ 检查失败: {e}"


def run_all_checks() -> Dict[str, Tuple[bool, str]]:
    """运行所有检查"""
    results = {}
    
    print("\n" + "=" * 60)
    print("系统全面检查")
    print("=" * 60)
    
    checks = [
        ('QMT连接', check_qmt_connection),
        ('数据完整性', check_data_integrity),
        ('配置一致性', check_config_consistency),
        ('Tick数据覆盖', check_tick_coverage),
    ]
    
    for name, check_func in checks:
        print(f"\n🔍 {name}...")
        try:
            success, message = check_func()
            results[name] = (success, message)
            print(message)
        except Exception as e:
            results[name] = (False, f"❌ 检查异常: {e}")
            print(f"❌ 检查异常: {e}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='系统检查工具 - 统一检查入口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 全面检查
  python scripts/system_check.py --type all
  
  # 只检查QMT连接
  python scripts/system_check.py --type connection
  
  # 检查数据和配置
  python scripts/system_check.py --type data --type config
        """
    )
    
    parser.add_argument('--type', type=str, action='append',
                       choices=['connection', 'data', 'config', 'coverage', 'all'],
                       default=['all'],
                       help='检查类型，可多次指定')
    
    args = parser.parse_args()
    
    # 确定检查列表
    if 'all' in args.type:
        check_types = ['connection', 'data', 'config', 'coverage']
    else:
        check_types = args.type
    
    # 执行检查
    results = {}
    
    print("=" * 60)
    print("系统检查工具")
    print("=" * 60)
    
    for check_type in check_types:
        print(f"\n🔍 检查: {check_type}")
        
        if check_type == 'connection':
            success, message = check_qmt_connection()
        elif check_type == 'data':
            success, message = check_data_integrity()
        elif check_type == 'config':
            success, message = check_config_consistency()
        elif check_type == 'coverage':
            success, message = check_tick_coverage()
        else:
            continue
        
        results[check_type] = success
        print(message)
    
    # 汇总
    print("\n" + "=" * 60)
    print("检查汇总")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for check_type, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status}: {check_type}")
    
    print("=" * 60)
    
    if all_passed:
        print("🎉 所有检查通过")
        return 0
    else:
        print("⚠️  部分检查未通过，请查看详情")
        return 1


if __name__ == '__main__':
    sys.exit(main())
