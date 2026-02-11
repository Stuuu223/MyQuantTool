#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日报生成器 - 阶段2

功能：
1. 汇总当日扫描结果
2. 生成Markdown日报
3. 可选邮件发送

使用方法：
    # 生成今日报告
    python tasks/generate_daily_report.py
    
    # 指定日期
    python tasks/generate_daily_report.py --date 2026-02-11
    
    # 发送邮件
    python tasks/generate_daily_report.py --send-email

作者：量化CTO
日期：2026-02-11
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


def load_scan_results(date_str: str) -> List[Dict]:
    """加载当日扫描结果"""
    scan_dir = ROOT_DIR / 'data' / 'scan_results'
    
    if not scan_dir.exists():
        print(f"⚠️  扫描结果目录不存在: {scan_dir}")
        return []
    
    # 查找当日的JSON文件
    pattern = f"scan_qpst_{date_str.replace('-', '')}*.json"
    files = list(scan_dir.glob(pattern))
    
    if not files:
        print(f"⚠️  未找到 {date_str} 的扫描结果")
        return []
    
    all_results = []
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_results.extend(data.get('results', []))
    
    print(f"✅ 加载了 {len(files)} 个扫描结果文件，共 {len(all_results)} 条记录")
    return all_results


def generate_markdown_report(results: List[Dict], date_str: str) -> str:
    """生成Markdown日报"""
    
    report = f"""# 📅 QPST诱多监控日报

**日期**: {date_str}  
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**扫描范围**: 全A股 5000+ 股票

---

## 📊 概况

"""
    
    if not results:
        report += "🎉 **今日未发现诱多信号，市场较为健康**\n\n"
        return report
    
    # 统计数据
    total_alerts = len(results)
    high_confidence = len([r for r in results if r['confidence'] >= 90])
    medium_confidence = len([r for r in results if 70 <= r['confidence'] < 90])
    
    report += f"""
- **总预警数**: {total_alerts}
- **高置信度** (≥90%): {high_confidence}
- **中置信度** (70-89%): {medium_confidence}

---

## ⚠️ TOP 20 诱多预警榜单

| 排名 | 股票代码 | 预警类型 | 置信度 | 原因 | 时间 |
|------|----------|----------|----------|------|------|
"""
    
    for idx, item in enumerate(results[:20], 1):
        trap_types = ", ".join(item.get('trap_signals', []))
        confidence = f"{item['confidence']:.0f}%"
        reason = item['reason'][:30] + ".." if len(item['reason']) > 30 else item['reason']
        time_str = item['timestamp']
        
        report += f"| {idx} | {item['code']} | {trap_types} | {confidence} | {reason} | {time_str} |\n"
    
    report += "\n---\n\n"
    
    # 预警类型分布
    trap_type_count = {}
    for r in results:
        for trap in r.get('trap_signals', []):
            trap_type_count[trap] = trap_type_count.get(trap, 0) + 1
    
    if trap_type_count:
        report += "## 📈 预警类型分布\n\n"
        for trap_type, count in sorted(trap_type_count.items(), key=lambda x: x[1], reverse=True):
            report += f"- **{trap_type}**: {count} 次\n"
        report += "\n---\n\n"
    
    # 附加说明
    report += """## 📝 预警说明

### 高风险预警（置信度 ≥90%）

- **对倒嫌疑**: 成交量异常但买卖盘不变，可能是庄家对敷
- **尾盘拉升**: 14:30后突然放量，警惕次日低开
- **连板开板**: 连续涨停后首次开板，可能出货

### 建议操作

1. **高置信度预警**: 立即停止买入，观察1-3个交易日
2. **中置信度预警**: 谨慎对待，配合其他指标分析
3. **已持有**: 考虑减仓或止盈

---

> **免责声明**: 本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。
"""
    
    return report


def save_report(report: str, date_str: str):
    """保存报告"""
    report_dir = ROOT_DIR / 'data' / 'reports' / 'daily'
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = report_dir / f"daily_report_{date_str.replace('-', '')}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n💾 日报已保存: {report_file}\n")
    return report_file


def send_email(report_file: Path):
    """发送邮件（可选）"""
    print("📧 邮件发送功能待实现...")
    # TODO: 集成邮件发送功能


def main():
    parser = argparse.ArgumentParser(description="QPST诱多监控日报生成器")
    
    parser.add_argument(
        '--date',
        type=str,
        default=datetime.now().strftime('%Y-%m-%d'),
        help="报告日期 (默认: 今天)"
    )
    
    parser.add_argument(
        '--send-email',
        action='store_true',
        help="发送邮件"
    )
    
    args = parser.parse_args()
    
    print(f"\n📅 生成 {args.date} 的日报...\n")
    
    # 加载扫描结果
    results = load_scan_results(args.date)
    
    # 生成报告
    report = generate_markdown_report(results, args.date)
    
    # 保存报告
    report_file = save_report(report, args.date)
    
    # 发送邮件
    if args.send_email:
        send_email(report_file)
    
    print("✨ 日报生成完成!\n")


if __name__ == '__main__':
    main()
