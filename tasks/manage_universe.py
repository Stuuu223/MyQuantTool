#!/usr/bin/env python3
"""
股票池管理工具 - 统一入口

取代脚本:
- scripts/generate_150_stocks_config.py

使用示例:
  # 生成顽主Top150股票池
  python tasks/manage_universe.py --action generate --profile wanzhu_top150
  
  # 生成顽主精选150（从CSV）
  python tasks/manage_universe.py --action generate --profile wanzhu_selected
  
  # 只查看统计信息，不保存
  python tasks/manage_universe.py --action stats --profile wanzhu_top150

Author: AI Project Director
Version: V1.0
Date: 2026-02-19
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.analyzers.universe_builder import (
    build_wanzhu_top150,
    build_wanzhu_selected,
    save_universe,
    get_universe_summary
)


def generate_universe(profile: str, output: Optional[Path] = None, format: str = 'json'):
    """生成股票池
    
    Args:
        profile: 股票池类型 (wanzhu_top150, wanzhu_selected)
        output: 输出路径，默认使用标准路径
        format: 输出格式 (json, csv)
    """
    print(f"\n{'='*60}")
    print(f"生成股票池: {profile}")
    print(f"{'='*60}\n")
    
    # 根据profile构建股票池
    if profile == 'wanzhu_top150':
        universe = build_wanzhu_top150()
        default_output = PROJECT_ROOT / 'config' / 'wanzhu_top150_tick_download.json'
    elif profile == 'wanzhu_selected':
        universe = build_wanzhu_selected()
        default_output = PROJECT_ROOT / 'config' / 'wanzhu_selected_tick_download.json'
    else:
        print(f"❌ 未知的股票池类型: {profile}")
        print(f"   支持的类型: wanzhu_top150, wanzhu_selected")
        return False
    
    # 显示统计
    summary = get_universe_summary(universe)
    print(f"股票池统计:")
    print(f"  总数: {summary['total']}")
    print(f"  上海: {summary['sh_count']} | 深圳: {summary['sz_count']}")
    print(f"  来源分布:")
    for src, count in summary['sources'].items():
        print(f"    - {src}: {count}")
    
    # 显示前10只
    print(f"\n前10只股票:")
    for s in universe[:10]:
        print(f"  {s['rank']:3d}. {s['name']:<12} ({s['code']}) [{s['source']}]")
    
    # 保存
    if output is None:
        output = default_output
    
    save_universe(universe, output, format)
    print(f"\n✅ 股票池生成完成: {output}")
    return True


def show_stats(profile: str):
    """显示股票池统计信息"""
    print(f"\n{'='*60}")
    print(f"股票池统计: {profile}")
    print(f"{'='*60}\n")
    
    if profile == 'wanzhu_top150':
        universe = build_wanzhu_top150()
    elif profile == 'wanzhu_selected':
        universe = build_wanzhu_selected()
    else:
        print(f"❌ 未知的股票池类型: {profile}")
        return False
    
    summary = get_universe_summary(universe)
    
    print(f"总数: {summary['total']}")
    print(f"市场分布:")
    print(f"  - 上海(SH): {summary['sh_count']}")
    print(f"  - 深圳(SZ): {summary['sz_count']}")
    print(f"\n来源分布:")
    for src, count in summary['sources'].items():
        pct = count / summary['total'] * 100
        print(f"  - {src}: {count} ({pct:.1f}%)")
    
    # 行业分布（如果有sector字段）
    sectors = {}
    for s in universe:
        sector = s.get('sector', 'unknown')
        sectors[sector] = sectors.get(sector, 0) + 1
    
    if len(sectors) > 1:
        print(f"\n行业分布:")
        for sector, count in sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {sector}: {count}")
    
    return True


def validate_universe(profile: str):
    """验证股票池有效性"""
    print(f"\n{'='*60}")
    print(f"验证股票池: {profile}")
    print(f"{'='*60}\n")
    
    if profile == 'wanzhu_top150':
        universe = build_wanzhu_top150()
    elif profile == 'wanzhu_selected':
        universe = build_wanzhu_selected()
    else:
        print(f"❌ 未知的股票池类型: {profile}")
        return False
    
    issues = []
    
    # 检查必要字段
    required_fields = ['code', 'qmt_code', 'market', 'name', 'rank']
    for i, stock in enumerate(universe):
        for field in required_fields:
            if field not in stock or not stock[field]:
                issues.append(f"第{i+1}条记录缺失字段: {field}")
        
        # 检查代码格式
        code = stock.get('code', '')
        if not (code.endswith('.SH') or code.endswith('.SZ')):
            issues.append(f"{code}: 代码格式不正确，应为 xxx.SH 或 xxx.SZ")
    
    # 检查重复
    codes = [s['code'] for s in universe]
    if len(codes) != len(set(codes)):
        duplicates = [c for c in codes if codes.count(c) > 1]
        issues.append(f"发现重复代码: {set(duplicates)}")
    
    if issues:
        print(f"❌ 验证失败，发现 {len(issues)} 个问题:")
        for issue in issues[:10]:
            print(f"  - {issue}")
        if len(issues) > 10:
            print(f"  ... 等共 {len(issues)} 个问题")
        return False
    else:
        print(f"✅ 验证通过")
        print(f"   共 {len(universe)} 只股票，所有字段完整")
        return True


def main():
    parser = argparse.ArgumentParser(
        description='股票池管理工具 - 统一构建和维护股票池',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 生成顽主Top150股票池
  python tasks/manage_universe.py --action generate --profile wanzhu_top150
  
  # 生成并保存为CSV格式
  python tasks/manage_universe.py --action generate --profile wanzhu_top150 --format csv
  
  # 查看统计信息
  python tasks/manage_universe.py --action stats --profile wanzhu_top150
  
  # 验证股票池
  python tasks/manage_universe.py --action validate --profile wanzhu_top150
        """
    )
    
    parser.add_argument('--action', type=str, required=True,
                       choices=['generate', 'stats', 'validate'],
                       help='操作类型')
    parser.add_argument('--profile', type=str, required=True,
                       choices=['wanzhu_top150', 'wanzhu_selected'],
                       help='股票池配置')
    parser.add_argument('--output', type=str,
                       help='输出文件路径（默认使用标准路径）')
    parser.add_argument('--format', type=str, default='json',
                       choices=['json', 'csv'],
                       help='输出格式')
    
    args = parser.parse_args()
    
    # 解析输出路径
    output_path = None
    if args.output:
        output_path = Path(args.output)
    
    # 执行操作
    if args.action == 'generate':
        success = generate_universe(args.profile, output_path, args.format)
    elif args.action == 'stats':
        success = show_stats(args.profile)
    elif args.action == 'validate':
        success = validate_universe(args.profile)
    else:
        print(f"❌ 未知的操作: {args.action}")
        success = False
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
