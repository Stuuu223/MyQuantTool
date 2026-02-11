#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
周报生成器 - 阶段2

功能：
1. 汇总本周扫描结果
2. 统计预警准确率
3. 生成Markdown周报

使用方法：
    # 生成本周报告
    python tasks/generate_weekly_report.py
    
    # 指定周的开始日期
    python tasks/generate_weekly_report.py --start-date 2026-02-10

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
from collections import defaultdict

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


def get_week_dates(start_date_str: str) -> List[str]:
    """获取一周的日期列表（周一到周五）"""
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    dates = []
    for i in range(5):  # 周一到周五
        date = start_date + timedelta(days=i)
        dates.append(date.strftime('%Y-%m-%d'))
    return dates


def load_week_results(dates: List[str]) -> Dict[str, List[Dict]]:
    """加载本周扫描结果"""
    scan_dir = ROOT_DIR / 'data' / 'scan_results'
    week_results = {}
    
    for date_str in dates:
        pattern = f"scan_qpst_{date_str.replace('-', '')}*.json"
        files = list(scan_dir.glob(pattern))
        
        daily_results = []
        for file in files:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                daily_results.extend(data.get('results', []))
        
        week_results[date_str] = daily_results
        print(f"✅ {date_str}: 加载 {len(daily_results)} 条记录")
    
    return week_results


def generate_markdown_report(week_results: Dict[str, List[Dict]], start_date: str) -> str:
    """生成Markdown周报"""
    
    end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=4)).strftime('%Y-%m-%d')
    
    report = f"""# 📅 QPST诱多监控周报

**周期**: {start_date} 至 {end_date}  
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**扫描范围**: 全A股 5000+ 股票

---

## 📊 本周概况

"""
    
    # 统计总数
    total_alerts = sum(len(results) for results in week_results.values())
    
    if total_alerts == 0:
        report += "🎉 **本周未发现诱多信号，市场表现健康**\n\n"
        return report
    
    report += f"- **总预警次数**: {total_alerts}\n"
    report += f"- **日均预警**: {total_alerts / 5:.1f} 次\n\n"
    
    # 每日统计
    report += "### 每日预警数量\n\n"
    report += "| 日期 | 预警次数 | 高置信度(≥90%) | 中置信度(70-89%) |\n"
    report += "|------|----------|-----------------|-------------------|\n"
    
    for date_str, results in week_results.items():
        high = len([r for r in results if r['confidence'] >= 90])
        medium = len([r for r in results if 70 <= r['confidence'] < 90])
        report += f"| {date_str} | {len(results)} | {high} | {medium} |\n"
    
    report += "\n---\n\n"
    
    # TOP 10频发股票
    stock_count = defaultdict(int)
    for results in week_results.values():
        for r in results:
            stock_count[r['code']] += 1
    
    top_stocks = sorted(stock_count.items(), key=lambda x: x[1], reverse=True)[:10]
    
    if top_stocks:
        report += "## ⚠️ TOP 10 频发预警股票\n\n"
        report += "| 排名 | 股票代码 | 预警次数 | 建议 |\n"
        report += "|------|----------|----------|------|\n"
        
        for idx, (code, count) in enumerate(top_stocks, 1):
            advice = "🛑 高度警惕" if count >= 3 else "⚠️ 密切关注"
            report += f"| {idx} | {code} | {count} | {advice} |\n"
        
        report += "\n---\n\n"
    
    # 预警类型分布
    trap_type_count = defaultdict(int)
    for results in week_results.values():
        for r in results:
            for trap in r.get('trap_signals', []):
                trap_type_count[trap] += 1
    
    if trap_type_count:
        report += "## 📈 预警类型分布\n\n"
        report += "| 预警类型 | 出现次数 | 占比 |\n"
        report += "|----------|----------|------|\n"
        
        for trap_type, count in sorted(trap_type_count.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_alerts * 100
            report += f"| {trap_type} | {count} | {percentage:.1f}% |\n"
        
        report += "\n---\n\n"
    
    # 总结与建议
    report += """## 📝 本周总结

### 市场特征

- **诱多频率**: """
    
    if total_alerts < 20:
        report += "低，市场相对健康"
    elif total_alerts < 50:
        report += "中等，需要谨慎"
    else:
        report += "高，市场波动较大"
    
    report += "\n\n### 下周建议\n\n"
    report += "1. 继续监控本周频发预警股票\n"
    report += "2. 关注高置信度预警后的走势验证\n"
    report += "3. 谨慎参与连续多日被警告的股票\n\n"
    
    report += "---\n\n"
    report += "> **免责声明**: 本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。\n"
    
    return report


def save_report(report: str, start_date: str):
    """保存报告"""
    report_dir = ROOT_DIR / 'data' / 'reports' / 'weekly'
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = report_dir / f"weekly_report_{start_date.replace('-', '')}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n💾 周报已保存: {report_file}\n")
    return report_file


def main():
    parser = argparse.ArgumentParser(description="QPST诱多监控周报生成器")
    
    parser.add_argument(
        '--start-date',
        type=str,
        default=(datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d'),
        help="本周开始日期（周一，默认: 本周周一）"
    )
    
    args = parser.parse_args()
    
    print(f"\n📅 生成 {args.start_date} 开始的周报...\n")
    
    # 获取本周日期
    dates = get_week_dates(args.start_date)
    print(f"周期: {dates[0]} 至 {dates[-1]}\n")
    
    # 加载扫描结果
    week_results = load_week_results(dates)
    
    # 生成报告
    report = generate_markdown_report(week_results, args.start_date)
    
    # 保存报告
    report_file = save_report(report, args.start_date)
    
    print("✨ 周报生成完成!\n")


if __name__ == '__main__':
    main()
