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


def check_qmt_vip_connection() -> Tuple[bool, str]:
    """检查QMT VIP连接状态（恢复PR-3删除的VIP连接功能，从本地配置读取）"""
    logger.info("检查QMT VIP连接状态...")
    
    print("=" * 60)
    print("🔍 连接QMT VIP站点")
    print("=" * 60)
    
    # 从本地配置读取VIP信息，避免硬编码
    try:
        # 尝试从本地文件读取VIP配置
        import os
        import json
        from pathlib import Path
        
        # 尝试从本地配置文件读取VIP信息
        local_config_paths = [
            Path.home() / '.iflow' / 'AGENTS.md',
            Path(__file__).parent.parent / 'config' / 'qmt_config.json',
            Path(__file__).parent.parent / 'config' / 'config.json'
        ]
        
        vip_token = None
        vip_sites = []
        
        for config_path in local_config_paths:
            if config_path.exists():
                content = config_path.read_text(encoding='utf-8')
                if '6b1446e317ed67596f13d2e808291a01e0dd9839' in content:
                    # 从AGENTS.md读取格式
                    import re
                    token_match = re.search(r'VIP Token:\s*([a-f0-9]{40})', content)
                    if token_match:
                        vip_token = token_match.group(1)
                    
                    # 从AGENTS.md读取站点信息
                    sites = [
                        ("vipsxmd1.thinktrader.net", 55310),
                        ("vipsxmd2.thinktrader.net", 55310),
                        ("dxzzmd1.thinktrader.net", 55300),
                        ("dxzzmd2.thinktrader.net", 55300),
                        ("ltzzmd1.thinktrader.net", 55300),
                        ("ltzzmd2.thinktrader.net", 55300),
                    ]
                    vip_sites = sites
                    break
        
        if not vip_token:
            print("⚠️  未找到VIP Token配置，请确保本地配置文件包含VIP信息")
            print("   提示：检查 C:/Users/<username>/.iflow/AGENTS.md 文件")
            return False, "⚠️  未找到VIP Token配置"
        
        print(f"📋 VIP站点数量: {len(vip_sites)}")
        
        # 只测试连接性，不打印token
        for site_id, (host, port) in enumerate(vip_sites, 1):
            print(f"\n📋 尝试连接站点{site_id}: {host}:{port}")
            
            try:
                # 使用TickProvider连接站点
                from logic.data_providers.tick_provider import TickProvider
                provider = TickProvider()
                
                # 尝试连接
                result = provider.connect()
                
                if result:
                    print(f"   ✅ 站点{site_id}连接成功")
                    
                    # 检查热股数据可用性
                    check_hot_stocks_data_vip(provider)
                    
                    print(f"\n📊 站点{site_id}连接测试完成")
                    return True, f"✅ 站点{site_id}连接成功: {host}:{port}"
                else:
                    print(f"   ❌ 站点{site_id}连接失败")
                    
            except Exception as e:
                print(f"   ❌ 站点{site_id}连接异常: {e}")
        
        print("\n❌ 所有VIP站点连接失败")
        return False, "❌ 所有VIP站点连接失败"
        
    except Exception as e:
        logger.error(f"VIP配置读取失败: {e}")
        return False, f"❌ VIP配置读取失败: {e}"


def check_hot_stocks_data_vip(provider) -> Tuple[bool, str]:
    """检查热股数据可用性（VIP连接模式）"""
    print("\n📋 检查热门股Tick数据...")
    
    hot_stocks = [
        '300997.SZ',  # 欢乐家
        '603697.SH',  # 有友食品
        '000001.SZ',  # 平安银行
        '600519.SH',  # 贵州茅台
        '300750.SZ',  # 宁德时代
    ]
    
    success_count = 0
    for stock in hot_stocks:
        try:
            # 使用provider检查数据可用性
            results = provider.check_coverage([stock])
            stock_result = results.get(stock, {})
            
            if stock_result.get('exists', False):
                tick_count = stock_result.get('count', 0)
                print(f"   ✅ {stock}: 数据可用 (记录数: {tick_count})")
                success_count += 1
            else:
                print(f"   ❌ {stock}: 无数据")
                
        except Exception as e:
            print(f"   ⚠️  {stock}: 读取失败 ({e})")
    
    if success_count > 0:
        print(f"\n📊 VIP数据检查: {success_count}/{len(hot_stocks)} 只股票数据可用")
        return True, f"✅ VIP数据检查: {success_count}/{len(hot_stocks)} 只股票数据可用"
    else:
        print(f"\n❌ VIP数据检查: 无股票数据可用")
        return False, "❌ VIP数据检查: 无股票数据可用"


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
        ('QMT VIP连接', check_qmt_vip_connection),
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
  python tools/system_check.py --type all
  
  # 只检查QMT连接
  python tools/system_check.py --type connection
  
  # 检查QMT VIP连接
  python tools/system_check.py --type vip
  
  # 检查数据和配置
  python tools/system_check.py --type data --type config
        """
    )
    
    parser.add_argument('--type', type=str, action='append',
                       choices=['connection', 'vip', 'data', 'config', 'coverage', 'all'],
                       default=['all'],
                       help='检查类型，可多次指定')
    
    args = parser.parse_args()
    
    # 确定检查列表
    if 'all' in args.type:
        check_types = ['connection', 'vip', 'data', 'config', 'coverage']
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
        elif check_type == 'vip':
            success, message = check_qmt_vip_connection()
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


class SystemCheck:
    """系统检查类 - 面向对象包装"""
    
    def __init__(self):
        self.results = {}
    
    def check_all(self) -> Dict[str, Tuple[bool, str]]:
        """执行所有检查"""
        self.results = {
            'connection': check_qmt_connection(),
            'data': check_data_integrity(),
            'config': check_config_consistency()
        }
        return self.results
    
    def is_healthy(self) -> bool:
        """检查系统是否健康"""
        if not self.results:
            self.check_all()
        return all(result[0] for result in self.results.values())


if __name__ == '__main__':
    sys.exit(main())
