#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown日报生成器

功能：
  - 汇总当日扫描结果
  - 统计准确率（需人工标注）
  - 生成Markdown格式日报
  - 可邮件发送

使用方式：
  python tasks/generate_daily_report.py --date 20260211
  python tasks/generate_daily_report.py  # 默认今日

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 2
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.logger import get_logger

logger = get_logger(__name__)


def load_scan_results(scan_dir: str, date: str) -> List[dict]:
    """
    加载指定日期的扫描结果
    
    Args:
        scan_dir: 扫描结果目录
        date: 日期字符串（YYYYMMDD）
    
    Returns:
        扫描结果列表
    """
    scan_path = Path(scan_dir)
    
    if not scan_path.exists():
        logger.error(f"❌ 扫描结果目录不存在: {scan_path}")
        return []
    
    # 查找指定日期的所有扫描文件
    pattern = f"scan_{date}_*.json"
    scan_files = sorted(scan_path.glob(pattern))
    
    if not scan_files:
        logger.warning(f"⚠️ 未找到 {date} 的扫描结果")
        return []
    
    logger.info(f"✅ 找到 {len(scan_files)} 个扫描文件")
    
    # 合并所有结果
    all_results = []
    for scan_file in scan_files:
        with open(scan_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
            all_results.extend(results)
    
    return all_results


def deduplicate_results(results: List[dict]) -> List[dict]:
    """
    去重（同一股票只保留置信度最高的记录）
    
    Args:
        results: 扫描结果列表
    
    Returns:
        去重后的结果列表
    """
    seen_codes = {}
    
    for result in results:
        code = result.get('code')
        confidence = result.get('confidence', 0)
        
        if code not in seen_codes or confidence > seen_codes[code]['confidence']:
            seen_codes[code] = result
    
    return list(seen_codes.values())


def generate_markdown_report(results: List[dict], date: str) -> str:
    """
    生成Markdown格式日报
    
    Args:
        results: 扫描结果列表
        date: 日期字符串（YYYYMMDD）
    
    Returns:
        Markdown文本
    """
    # 解析日期
    try:
        date_obj = datetime.strptime(date, '%Y%m%d')
        date_str = date_obj.strftime('%Y年%m月%d日')
        weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][date_obj.weekday()]
    except:
        date_str = date
        weekday = ''
    
    # 统计信息
    total_count = len(results)
    high_conf = sum(1 for r in results if r['confidence'] > 0.8)
    mid_conf = sum(1 for r in results if 0.6 < r['confidence'] <= 0.8)
    low_conf = total_count - high_conf - mid_conf
    
    # 生成Markdown
    md_lines = []
    md_lines.append(f"# 🚨 诱多预警日报 - {date_str} {weekday}")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## 📊 概览")
    md_lines.append("")
    md_lines.append(f"- **扫描日期**: {date_str} {weekday}")
    md_lines.append(f"- **预警总数**: {total_count} 只股票")
    md_lines.append(f"- **高置信度 (>80%)**: {high_conf} 只 🔴")
    md_lines.append(f"- **中置信度 (60-80%)**: {mid_conf} 只 🟡")
    md_lines.append(f"- **低置信度 (<60%)**: {low_conf} 只 ⚪")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## 🔥 重点关注（高置信度 TOP 10）")
    md_lines.append("")
    
    # 高置信度股票
    high_conf_stocks = [r for r in results if r['confidence'] > 0.8]
    high_conf_stocks.sort(key=lambda x: x['confidence'], reverse=True)
    
    if high_conf_stocks:
        md_lines.append("| 排名 | 股票代码 | 置信度 | 预警原因 | 时间 |")
        md_lines.append("|------|----------|--------|----------|------|")
        
        for idx, result in enumerate(high_conf_stocks[:10], 1):
            code = result.get('code', 'N/A')
            confidence = f"{result['confidence']:.1%}"
            reason = result['reason'][:30] + '...' if len(result['reason']) > 30 else result['reason']
            timestamp = result['timestamp']
            
            md_lines.append(f"| {idx} | {code} | {confidence} | {reason} | {timestamp} |")
    else:
        md_lines.append("*暂无高置信度预警*")
    
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## 📋 完整榜单（按置信度排序）")
    md_lines.append("")
    
    # 按置信度排序
    results.sort(key=lambda x: x['confidence'], reverse=True)
    
    md_lines.append("| 排名 | 股票代码 | 置信度 | 信号 | 预警原因 | 时间 |")
    md_lines.append("|------|----------|--------|------|----------|------|")
    
    for idx, result in enumerate(results, 1):
        code = result.get('code', 'N/A')
        confidence = f"{result['confidence']:.1%}"
        signal = result['final_signal']
        reason = result['reason'][:30] + '...' if len(result['reason']) > 30 else result['reason']
        timestamp = result['timestamp']
        
        md_lines.append(f"| {idx} | {code} | {confidence} | {signal} | {reason} | {timestamp} |")
    
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## 📝 备注")
    md_lines.append("")
    md_lines.append("- 本日报由 **MyQuantTool** 自动生成")
    md_lines.append("- 诱多预警仅供参考，不构成投资建议")
    md_lines.append("- 置信度越高，诱多概率越大")
    md_lines.append("- 建议配合实盘验证，持续优化模型")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    return '\n'.join(md_lines)


def save_report(report: str, output_dir: str, date: str):
    """
    保存日报
    
    Args:
        report: Markdown文本
        output_dir: 输出目录
        date: 日期字符串（YYYYMMDD）
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    report_file = output_path / f"daily_report_{date}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"💾 日报已保存: {report_file}")
    return str(report_file)


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='生成诱多预警日报')
    parser.add_argument('--date', type=str, default=None,
                       help='日期（YYYYMMDD），默认今日')
    parser.add_argument('--scan-dir', type=str, default='data/scan_results',
                       help='扫描结果目录，默认 data/scan_results')
    parser.add_argument('--output', type=str, default='data/reports',
                       help='输出目录，默认 data/reports')
    
    args = parser.parse_args()
    
    # 确定日期
    if args.date:
        date = args.date
    else:
        date = datetime.now().strftime('%Y%m%d')
    
    logger.info(f"📅 生成日报: {date}")
    
    # 加载扫描结果
    results = load_scan_results(args.scan_dir, date)
    
    if not results:
        logger.warning("⚠️ 无数据可生成日报")
        return
    
    # 去重
    results = deduplicate_results(results)
    logger.info(f"✅ 去重后剩余 {len(results)} 只股票")
    
    # 生成日报
    report = generate_markdown_report(results, date)
    
    # 保存日报
    report_file = save_report(report, args.output, date)
    
    # 显示预览
    print("\n" + "="*80)
    print("📄 日报预览")
    print("="*80)
    print(report[:500] + "\n...\n(完整内容请查看文件)")
    print("="*80)
    print(f"\n✅ 日报生成完成: {report_file}\n")


if __name__ == '__main__':
    main()
