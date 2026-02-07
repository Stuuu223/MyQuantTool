#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从全市场扫描结果更新观察池

Usage:
    python tasks/update_watchlist_from_scan.py --latest
    python tasks/update_watchlist_from_scan.py --file data/scan_results/2026-02-06_postmarket.json
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.logger import get_logger
from logic.triple_funnel_scanner import WatchlistManager

logger = get_logger(__name__)


def get_latest_scan_result():
    """获取最新的扫描结果文件"""
    scan_results_dir = Path('data/scan_results')
    if not scan_results_dir.exists():
        logger.error("❌ 扫描结果目录不存在")
        return None
    
    # 获取所有JSON文件
    files = list(scan_results_dir.glob('*.json'))
    if not files:
        logger.error("❌ 没有找到扫描结果文件")
        return None
    
    # 按修改时间排序，取最新的
    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    logger.info(f"✅ 找到最新扫描结果: {latest_file}")
    return latest_file


def load_scan_result(file_path):
    """加载扫描结果"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"❌ 加载扫描结果失败: {e}")
        return None


def update_watchlist_from_scan(scan_data, replace=True, max_count=50):
    """
    从扫描结果更新观察池
    
    Args:
        scan_data: 扫描结果数据
        replace: 是否替换现有观察池（True）还是追加（False）
        max_count: 最大添加数量
    """
    watchlist_manager = WatchlistManager()
    
    # 获取机会池股票
    opportunities = scan_data.get('results', {}).get('opportunities', [])
    watchlist_candidates = scan_data.get('results', {}).get('watchlist', [])
    
    # 合并候选池（优先机会池，然后是观察池）
    all_candidates = opportunities + watchlist_candidates
    
    if not all_candidates:
        logger.warning("⚠️ 扫描结果中没有候选股票")
        return
    
    # 限制数量
    candidates_to_add = all_candidates[:max_count]
    
    # 如果是替换模式，先清空观察池
    if replace:
        logger.info(f"🔄 清空现有观察池")
        watchlist_manager.watchlist.clear()
        watchlist_manager._save()
    
    # 添加股票
    added_count = 0
    for candidate in candidates_to_add:
        code = candidate.get('code', '')
        code_6digit = candidate.get('code_6digit', '')
        name = candidate.get('name', '')
        
        if not code:
            continue
        
        # 优先使用6位代码，否则使用完整代码
        stock_code = code_6digit if code_6digit else code
        
        # 如果没有名称，使用代码作为名称
        if not name:
            name = stock_code
        
        # 添加原因
        risk_score = candidate.get('risk_score', 0)
        capital_type = candidate.get('capital_type', 'UNKNOWN')
        reason = f"扫描结果 - 风险评分:{risk_score:.2f} - 类型:{capital_type}"
        
        # 检查是否已存在
        if stock_code in watchlist_manager.watchlist:
            logger.debug(f"股票已存在: {stock_code} {name}")
            continue
        
        # 添加到观察池
        watchlist_manager.add(stock_code, name, reason)
        added_count += 1
        
        logger.info(f"✅ 添加股票: {stock_code} {name} - 风险评分:{risk_score:.2f} - 类型:{capital_type}")
    
    logger.info(f"\n📊 更新完成:")
    logger.info(f"   - 候选股票: {len(all_candidates)} 只")
    logger.info(f"   - 实际添加: {added_count} 只")
    logger.info(f"   - 观察池总数: {len(watchlist_manager.watchlist)} 只")


def main():
    parser = argparse.ArgumentParser(
        description='从全市场扫描结果更新观察池',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  使用最新扫描结果:
    python tasks/update_watchlist_from_scan.py --latest
  
  使用指定文件:
    python tasks/update_watchlist_from_scan.py --file data/scan_results/2026-02-06_postmarket.json
  
  追加模式（不替换现有观察池）:
    python tasks/update_watchlist_from_scan.py --latest --append
  
  限制添加数量:
    python tasks/update_watchlist_from_scan.py --latest --max 30
        """
    )
    parser.add_argument(
        '--file',
        type=str,
        help='扫描结果文件路径'
    )
    parser.add_argument(
        '--latest',
        action='store_true',
        help='使用最新的扫描结果文件'
    )
    parser.add_argument(
        '--append',
        action='store_true',
        help='追加模式（不替换现有观察池）'
    )
    parser.add_argument(
        '--max',
        type=int,
        default=50,
        help='最大添加数量（默认: 50）'
    )
    
    args = parser.parse_args()
    
    # 打印启动信息
    print("\n" + "=" * 80)
    print("🚀 从扫描结果更新观察池")
    print("=" * 80)
    
    # 确定扫描结果文件
    if args.file:
        scan_file = Path(args.file)
        if not scan_file.exists():
            logger.error(f"❌ 扫描结果文件不存在: {args.file}")
            sys.exit(1)
    elif args.latest:
        scan_file = get_latest_scan_result()
        if not scan_file:
            sys.exit(1)
    else:
        logger.error("❌ 请指定 --file 或 --latest")
        sys.exit(1)
    
    print(f"📅 扫描结果文件: {scan_file}")
    print(f"📝 更新模式: {'追加' if args.append else '替换'}")
    print(f"📊 最大数量: {args.max}")
    print("=" * 80 + "\n")
    
    # 加载扫描结果
    scan_data = load_scan_result(scan_file)
    if not scan_data:
        sys.exit(1)
    
    # 打印扫描结果摘要
    summary = scan_data.get('summary', {})
    print(f"📊 扫描结果摘要:")
    print(f"   - 机会池: {summary.get('opportunities', 0)} 只")
    print(f"   - 观察池: {summary.get('watchlist', 0)} 只")
    print(f"   - 黑名单: {summary.get('blacklist', 0)} 只")
    print()
    
    # 更新观察池
    update_watchlist_from_scan(
        scan_data,
        replace=not args.append,
        max_count=args.max
    )
    
    print("\n" + "=" * 80)
    print("✅ 观察池更新完成！")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()