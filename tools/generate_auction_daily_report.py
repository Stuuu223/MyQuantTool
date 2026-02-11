"""
竞价数据质量与诱多检出率日报自动生成脚本

功能：
1. 读取指定日期的竞价快照数据
2. 计算数据质量指标（有效率、分布等）
3. 统计诱多检出情况
4. 生成Markdown格式日报
5. 可选生成JSON格式数据
"""

import sqlite3
import argparse
import json
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path


class AuctionDailyReportGenerator:
    """竞价日报生成器"""

    def __init__(self, db_path: str = "data/auction_snapshots.db"):
        self.db_path = db_path

    def get_data(self, date: str) -> Dict[str, Any]:
        """获取指定日期的数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 基础统计
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN volume_ratio_valid = 1 THEN 1 ELSE 0 END) as valid,
                SUM(CASE WHEN data_source = 'production' THEN 1 ELSE 0 END) as production,
                SUM(CASE WHEN data_source = 'simulated' THEN 1 ELSE 0 END) as simulated
            FROM auction_snapshots
            WHERE date = ?
        ''', (date,))
        basic_stats = cursor.fetchone()

        # 量比分布
        cursor.execute('''
            SELECT
                CASE
                    WHEN volume_ratio < 0.5 THEN '0-0.5'
                    WHEN volume_ratio < 1.0 THEN '0.5-1.0'
                    WHEN volume_ratio < 2.0 THEN '1.0-2.0'
                    WHEN volume_ratio < 5.0 THEN '2.0-5.0'
                    WHEN volume_ratio < 10.0 THEN '5.0-10.0'
                    ELSE '>10.0'
                END as bucket,
                COUNT(*) as count
            FROM auction_snapshots
            WHERE date = ? AND volume_ratio_valid = 1
            GROUP BY bucket
            ORDER BY bucket
        ''', (date,))
        volume_distribution = cursor.fetchall()

        # 涨跌幅分布
        cursor.execute('''
            SELECT
                CASE
                    WHEN auction_change < -0.10 THEN '<-10%'
                    WHEN auction_change < -0.05 THEN '-10%~-5%'
                    WHEN auction_change < -0.02 THEN '-5%~-2%'
                    WHEN auction_change < 0.02 THEN '-2%~+2%'
                    WHEN auction_change < 0.05 THEN '+2%~+5%'
                    WHEN auction_change < 0.10 THEN '+5%~+10%'
                    ELSE '>+10%'
                END as bucket,
                COUNT(*) as count
            FROM auction_snapshots
            WHERE date = ?
            GROUP BY bucket
            ORDER BY bucket
        ''', (date,))
        change_distribution = cursor.fetchall()

        # 诱多检出（高开+低量比）
        cursor.execute('''
            SELECT
                COUNT(*) as trap_count
            FROM auction_snapshots
            WHERE date = ?
              AND auction_change > 0.05
              AND volume_ratio_valid = 1
              AND volume_ratio < 2.0
        ''', (date,))
        trap_stats = cursor.fetchone()

        # 高开诱多候选Top 20
        cursor.execute('''
            SELECT
                code, name, auction_price,
                ROUND(auction_change * 100, 2) as change_pct,
                ROUND(volume_ratio, 2) as volume_ratio,
                CASE
                    WHEN auction_change > 0.05 AND volume_ratio < 2.0 THEN '诱多候选'
                    WHEN auction_change > 0.05 AND volume_ratio >= 2.0 THEN '强势'
                    WHEN auction_change < -0.05 THEN '低开'
                    ELSE '普通'
                END as type
            FROM auction_snapshots
            WHERE date = ?
              AND ABS(auction_change) > 0.03
            ORDER BY auction_change DESC, volume_ratio ASC
            LIMIT 20
        ''', (date,))
        top_stocks = cursor.fetchall()

        # 涨跌幅中位数
        cursor.execute('''
            SELECT auction_change
            FROM auction_snapshots
            WHERE date = ?
            ORDER BY auction_change
            LIMIT 1
            OFFSET (SELECT COUNT(*) FROM auction_snapshots WHERE date = ?) / 2
        ''', (date, date))
        median_result = cursor.fetchone()
        median_change = median_result[0] * 100 if median_result else 0

        conn.close()

        return {
            'date': date,
            'basic_stats': {
                'total': basic_stats[0],
                'valid': basic_stats[1],
                'production': basic_stats[2],
                'simulated': basic_stats[3],
                'valid_rate': basic_stats[1] / basic_stats[0] * 100 if basic_stats[0] > 0 else 0,
                'data_source': 'production' if basic_stats[2] > basic_stats[3] else 'simulated'
            },
            'volume_distribution': volume_distribution,
            'change_distribution': change_distribution,
            'trap_stats': {
                'trap_count': trap_stats[0],
                'trap_rate': trap_stats[0] / basic_stats[0] * 100 if basic_stats[0] > 0 else 0
            },
            'top_stocks': top_stocks,
            'median_change': median_change
        }

    def generate_markdown(self, data: Dict[str, Any]) -> str:
        """生成Markdown格式报告"""
        md = []
        md.append(f"# 竞价诱多系统验证报告 - {data['date']}")
        md.append("")
        md.append("## 📊 数据质量")
        md.append("")
        md.append("### 基础统计")
        md.append("")
        md.append("| 指标 | 数值 |")
        md.append("|------|------|")
        md.append(f"| 样本总数 | {data['basic_stats']['total']} |")
        md.append(f"| 有效数据数 | {data['basic_stats']['valid']} |")
        md.append(f"| 数据有效率 | {data['basic_stats']['valid_rate']:.2f}% |")
        md.append(f"| 数据来源 | {data['basic_stats']['data_source']} |")
        md.append("")
        md.append("### 量比分布")
        md.append("")
        md.append("| 区间 | 数量 | 占比 |")
        md.append("|------|------|------|")
        for bucket, count in data['volume_distribution']:
            pct = count / data['basic_stats']['total'] * 100 if data['basic_stats']['total'] > 0 else 0
            md.append(f"| {bucket} | {count} | {pct:.2f}% |")
        md.append("")
        md.append("### 竞价涨跌幅分布")
        md.append("")
        md.append("| 区间 | 数量 | 占比 |")
        md.append("|------|------|------|")
        for bucket, count in data['change_distribution']:
            pct = count / data['basic_stats']['total'] * 100 if data['basic_stats']['total'] > 0 else 0
            md.append(f"| {bucket} | {count} | {pct:.2f}% |")
        md.append("")
        md.append(f"**中位数**：{data['median_change']:.2f}%")
        md.append("")
        md.append("## 🎯 诱多检出")
        md.append("")
        md.append("### 检出统计")
        md.append("")
        md.append("| 指标 | 数值 |")
        md.append("|------|------|")
        md.append(f"| 诱多候选数 | {data['trap_stats']['trap_count']} |")
        md.append(f"| 检出率 | {data['trap_stats']['trap_rate']:.2f}% |")
        md.append("")
        md.append("### 诱多候选列表（Top 20）")
        md.append("")
        md.append("| 代码 | 名称 | 竞价价 | 涨跌幅% | 量比 | 类型 |")
        md.append("|------|------|--------|---------|------|------|")
        for stock in data['top_stocks']:
            code, name, price, change_pct, volume_ratio, stock_type = stock
            md.append(f"| {code} | {name} | {price:.2f} | {change_pct} | {volume_ratio} | {stock_type} |")
        md.append("")
        md.append("## ✅ 验收结论")
        md.append("")
        md.append(f"**工程闭环**：{'✅ 通过' if data['basic_stats']['data_source'] == 'production' else '⚠️ 模拟环境'}")
        md.append(f"**数据质量**：{'✅ 合格' if data['basic_stats']['valid_rate'] > 80 else '⚠️ 需关注'}")
        md.append(f"**诱多检出**：{'✅ 正常' if 1 <= data['trap_stats']['trap_rate'] <= 10 else '⚠️ 异常'}")
        md.append("")
        md.append("---")
        md.append(f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(md)

    def save_report(self, date: str, content: str, format: str = "markdown"):
        """保存报告到文件"""
        report_dir = Path("docs/auction_validation")
        report_dir.mkdir(parents=True, exist_ok=True)

        if format == "markdown":
            file_path = report_dir / f"{date.replace('-', '')}.md"
        elif format == "json":
            file_path = report_dir / f"{date.replace('-', '')}.json"
        else:
            raise ValueError(f"Unsupported format: {format}")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 报告已保存：{file_path}")
        return file_path


def main():
    parser = argparse.ArgumentParser(description="生成竞价日报")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"),
                        help="日期（格式：YYYY-MM-DD）")
    parser.add_argument("--format", type=str, default="markdown", choices=["markdown", "json"],
                        help="输出格式")
    parser.add_argument("--output", action="store_true", help="保存到文件")

    args = parser.parse_args()

    generator = AuctionDailyReportGenerator()

    print(f"📊 正在生成 {args.date} 的竞价日报...")
    data = generator.get_data(args.date)

    if args.format == "markdown":
        content = generator.generate_markdown(data)
    else:
        content = json.dumps(data, ensure_ascii=False, indent=2)

    print(content)

    if args.output:
        generator.save_report(args.date, content, args.format)


if __name__ == "__main__":
    main()
