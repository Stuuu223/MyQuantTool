#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日报生成器

自动汇总当日扫描结果，生成Markdown格式日报

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 2
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logic.logger import get_logger

logger = get_logger(__name__)


class DailyReportGenerator:
    """
    日报生成器
    
    汇总当日多次扫描结果，生成Markdown报告
    """
    
    def __init__(self, date_str: str = None, scan_dir: str = 'data/scan_results'):
        """
        初始化报告生成器
        
        Args:
            date_str: 日期字符串（YYYYMMDD），默认为今天
            scan_dir: 扫描结果目录
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        
        self.date_str = date_str
        self.date_obj = datetime.strptime(date_str, '%Y%m%d')
        self.scan_dir = Path(scan_dir)
        self.report_dir = Path('data/daily_reports')
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def load_scan_results(self) -> List[Dict]:
        """
        加载当日所有扫描结果
        
        Returns:
            诱多榜单（去重、排序后）
        """
        logger.info(f"加载 {self.date_str} 的扫描结果...")
        
        all_results = []
        pattern = f"trap_scan_{self.date_str}_*.json"
        
        for json_file in self.scan_dir.glob(pattern):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results = data.get('results', [])
                    all_results.extend(results)
                    logger.info(f"  ✓ 加载 {json_file.name}: {len(results)} 条记录")
            except Exception as e:
                logger.error(f"  ✗ 加载 {json_file.name} 失败: {e}")
        
        # 去重（按股票代码）
        unique_results = {}
        for item in all_results:
            code = item['code']
            if code not in unique_results or item['confidence'] > unique_results[code]['confidence']:
                unique_results[code] = item
        
        # 按置信度排序
        sorted_results = sorted(unique_results.values(), key=lambda x: x['confidence'], reverse=True)
        
        logger.info(f"总计 {len(all_results)} 条记录，去重后 {len(sorted_results)} 条")
        return sorted_results
    
    def generate_report(self, trap_list: List[Dict]) -> str:
        """
        生成Markdown格式报告
        
        Args:
            trap_list: 诱多榜单
        
        Returns:
            Markdown文本
        """
        # 分级别统计
        high_risk = [item for item in trap_list if item['confidence'] >= 0.8]
        mid_risk = [item for item in trap_list if 0.6 <= item['confidence'] < 0.8]
        low_risk = [item for item in trap_list if item['confidence'] < 0.6]
        
        # 构建报告
        report = []
        report.append(f"# 📈 诱多扫描日报")
        report.append(f"")
        report.append(f"**报告日期**: {self.date_obj.strftime('%Y年%m月%d日 %A')}")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"")
        report.append(f"---")
        report.append(f"")
        
        # 统计概览
        report.append(f"## 📊 统计概览")
        report.append(f"")
        report.append(f"| 项目 | 数量 |")
        report.append(f"|------|------|")
        report.append(f"| 🔴 高风险（≥ 80%） | {len(high_risk)} |")
        report.append(f"| 🟡 中风险（60%-80%） | {len(mid_risk)} |")
        report.append(f"| 🟢 低风险（< 60%） | {len(low_risk)} |")
        report.append(f"| **总计** | **{len(trap_list)}** |")
        report.append(f"")
        report.append(f"---")
        report.append(f"")
        
        # 高风险榜单
        if high_risk:
            report.append(f"## 🔴 高风险警报 (置信度 ≥ 80%)")
            report.append(f"")
            report.append(self._generate_table(high_risk))
            report.append(f"")
        
        # 中风险榜单
        if mid_risk:
            report.append(f"## 🟡 中风险提示 (60% ≤ 置信度 < 80%)")
            report.append(f"")
            report.append(self._generate_table(mid_risk))
            report.append(f"")
        
        # 低风险榜单（只显示Top 10）
        if low_risk:
            report.append(f"## 🟢 低风险参考 (置信度 < 60%, Top 10)")
            report.append(f"")
            report.append(self._generate_table(low_risk[:10]))
            report.append(f"")
        
        # 附注
        report.append(f"---")
        report.append(f"")
        report.append(f"## 📌 附注")
        report.append(f"")
        report.append(f"1. **诱多预警原理**: QPST四维分析（Quantity/Price/Space/Time） + 反诱多检测")
        report.append(f"2. **高风险操作建议**: 远离或等待认证，避免盲目追涨")
        report.append(f"3. **中风险操作建议**: 谨慎观察，等待1-3个交易日验证")
        report.append(f"4. **低风险操作建议**: 可关注，但仍需结合其他指标决策")
        report.append(f"5. **免责声明**: 本报告仅供参考，不构成投资建议，错误决策风险自担")
        report.append(f"")
        report.append(f"---")
        report.append(f"")
        report.append(f"*报告由 MyQuantTool Phase 2 自动生成*")
        
        return "\n".join(report)
    
    def _generate_table(self, items: List[Dict]) -> str:
        """
        生成Markdown表格
        
        Args:
            items: 榜单条目
        
        Returns:
            Markdown表格文本
        """
        lines = []
        lines.append("| # | 股票代码 | 预警类型 | 置信度 | 时间 |")
        lines.append("|---|----------|----------|--------|------|")
        
        for idx, item in enumerate(items, start=1):
            code = item['code']
            reason = item['reason'][:50]  # 截断过长文本
            confidence = f"{item['confidence']:.0%}"
            timestamp = item.get('timestamp', '')
            
            lines.append(f"| {idx} | {code} | {reason} | {confidence} | {timestamp} |")
        
        return "\n".join(lines)
    
    def save_report(self, markdown_text: str) -> Path:
        """
        保存报告到文件
        
        Args:
            markdown_text: Markdown文本
        
        Returns:
            报告文件路径
        """
        filename = f"daily_report_{self.date_str}.md"
        filepath = self.report_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        logger.info(f"✅ 报告已保存: {filepath}")
        return filepath
    
    def run(self) -> Path:
        """
        执行报告生成流程
        
        Returns:
            报告文件路径
        """
        # 加载数据
        trap_list = self.load_scan_results()
        
        if not trap_list:
            logger.warning(f"⚠️ {self.date_str} 无扫描结果，跳过报告生成")
            return None
        
        # 生成报告
        logger.info("正在生成Markdown报告...")
        markdown_text = self.generate_report(trap_list)
        
        # 保存报告
        filepath = self.save_report(markdown_text)
        
        return filepath


def main():
    """主程序"""
    parser = argparse.ArgumentParser(
        description="诱多扫描日报生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 生成今日报告
  python tasks/generate_daily_report.py
  
  # 指定日期
  python tasks/generate_daily_report.py --date 20260211
        """
    )
    
    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help='日期（YYYYMMDD格式，默认为今天）'
    )
    
    args = parser.parse_args()
    
    # 创建生成器
    generator = DailyReportGenerator(date_str=args.date)
    
    # 执行
    print("\n" + "="*80)
    print("📄 正在生成日报...")
    print("="*80 + "\n")
    
    filepath = generator.run()
    
    if filepath:
        print("\n" + "="*80)
        print(f"✅ 日报生成完成: {filepath}")
        print("="*80 + "\n")
    else:
        print("\n⚠️ 未生成报告\n")


if __name__ == '__main__':
    main()
