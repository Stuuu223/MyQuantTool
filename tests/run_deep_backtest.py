#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量回测执行器 - 验证所有历史快照的实际收益

核心功能：
1. 扫描data/scan_results/目录下的所有历史快照
2. 对每个快照进行回测
3. 汇总统计胜率、盈亏比等指标
4. 生成完整的回测报告

使用方法：
    python tests/run_deep_backtest.py                          # 回测所有快照
    python tests/run_deep_backtest.py --file xxx.json          # 回测单个快照
    python tests/run_deep_backtest.py --days 7                 # 回测最近7天的快照

Author: MyQuantTool Team
Date: 2026-02-10
Version: V1.0
"""

import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
from datetime import datetime, timedelta
from typing import List

from logic.snapshot_backtest_engine import SnapshotBacktestEngine
from logic.logger import get_logger

logger = get_logger(__name__)


def find_snapshot_files(scan_results_dir: Path, days: int = None, file: str = None) -> List[Path]:
    """
    查找快照文件

    Args:
        scan_results_dir: 扫描结果目录
        days: 最近N天（可选）
        file: 指定文件（可选）

    Returns:
        快照文件列表
    """
    if file:
        # 单文件模式
        file_path = Path(file)
        if not file_path.exists():
            file_path = scan_results_dir / file

        if file_path.exists():
            return [file_path]
        else:
            logger.error(f"❌ 文件不存在: {file}")
            return []

    # 批量模式：查找所有JSON文件
    snapshot_files = list(scan_results_dir.glob('*.json'))

    if not snapshot_files:
        logger.warning(f"⚠️ 未找到快照文件: {scan_results_dir}")
        return []

    # 按时间过滤
    if days:
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_files = []

        for file in snapshot_files:
            # 从文件名提取日期（假设格式：YYYY-MM-DD_xxx.json）
            try:
                date_str = file.stem[:10]  # 提取 YYYY-MM-DD
                file_date = datetime.strptime(date_str, '%Y-%m-%d')

                if file_date >= cutoff_date:
                    filtered_files.append(file)
            except ValueError:
                # 文件名不符合日期格式，跳过
                logger.warning(f"⚠️ 文件名格式不符: {file.name}")

        return sorted(filtered_files)

    # 返回所有文件（按时间排序）
    return sorted(snapshot_files)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='批量回测执行器')
    parser.add_argument('--file', type=str, help='回测指定文件')
    parser.add_argument('--days', type=int, help='回测最近N天的快照')
    parser.add_argument('--dir', type=str, default='data/scan_results', help='快照目录')

    args = parser.parse_args()

    print()
    print("=" * 80)
    print("🚀 MyQuantTool - 批量回测执行器")
    print("=" * 80)
    print()

    # 查找快照文件
    scan_results_dir = Path(args.dir)
    snapshot_files = find_snapshot_files(scan_results_dir, args.days, args.file)

    if not snapshot_files:
        logger.error("❌ 没有找到需要回测的快照文件")
        logger.info(f"💡 提示：请先运行全市场扫描生成快照")
        logger.info(f"   快照目录: {scan_results_dir}")
        return

    logger.info(f"📂 找到 {len(snapshot_files)} 个快照文件:")
    for i, file in enumerate(snapshot_files, 1):
        logger.info(f"   [{i}] {file.name}")
    print()

    # 初始化回测引擎
    logger.info("🔧 初始化回测引擎...")
    try:
        engine = SnapshotBacktestEngine()
    except ImportError as e:
        logger.error(f"❌ 初始化失败: {e}")
        logger.info("💡 提示：请确保QMT客户端已启动并登录")
        return

    print()
    print("=" * 80)
    print("🔥 开始批量回测")
    print("=" * 80)

    # 逐个回测快照
    all_backtest_results = []

    for i, snapshot_file in enumerate(snapshot_files, 1):
        logger.info(f"\n[{i}/{len(snapshot_files)}] 回测快照: {snapshot_file.name}")
        logger.info("=" * 80)

        result = engine.backtest_snapshot(snapshot_file)

        if result and result.get('results'):
            all_backtest_results.append(result)
            logger.info(f"✅ 回测完成: {len(result['results'])} 个有效样本")
        else:
            logger.warning(f"⚠️ 回测结果为空，跳过")

    # 计算汇总指标
    if not all_backtest_results:
        logger.error("\n❌ 没有有效的回测结果")
        return

    print()
    print("=" * 80)
    print("📊 汇总回测结果")
    print("=" * 80)
    print()

    logger.info(f"有效快照数: {len(all_backtest_results)}/{len(snapshot_files)}")

    total_signals = sum(len(r['results']) for r in all_backtest_results)
    logger.info(f"总信号数: {total_signals}")

    # 计算整体指标
    metrics = engine.calculate_metrics(all_backtest_results)

    if not metrics:
        logger.error("❌ 指标计算失败")
        return

    # 生成报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"data/backtest/reports/backtest_report_{timestamp}.json"

    engine.generate_backtest_report(metrics, output_file)

    # 保存详细结果
    detailed_output = f"data/backtest/results/backtest_details_{timestamp}.json"
    detailed_output_path = Path(detailed_output)
    detailed_output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(detailed_output, 'w', encoding='utf-8') as f:
        json.dump(all_backtest_results, f, ensure_ascii=False, indent=2)

    logger.info(f"💾 详细结果已保存: {detailed_output}")

    print()
    print("=" * 80)
    print("✅ 批量回测完成")
    print("=" * 80)
    print()

    logger.info(f"📊 回测报告: {output_file}")
    logger.info(f"📊 详细结果: {detailed_output}")

    print()
    print("💡 下一步:")
    print("   1. 查看回测报告，评估策略有效性")
    print("   2. 如果胜率>60%，可以小仓位实盘验证")
    print("   3. 如果胜率<40%，需要优化筛选条件")
    print()


if __name__ == "__main__":
    main()