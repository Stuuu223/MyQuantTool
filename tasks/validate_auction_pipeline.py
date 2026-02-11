"""
日内真实竞价链路验收脚本

功能闭环：09:25 竞价采集 → 数据入库 → 数据质量标记 → 09:35 后诱多回放

使用场景：
1. 真实交易日早盘验收（09:20-10:00）
2. 验证整个链路在生产环境是否畅通
3. 生成完整的验收报告
"""

import argparse
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class AuctionPipelineValidator:
    """竞价链路验收器"""

    def __init__(self, db_path: str = "data/auction_snapshots.db"):
        self.db_path = db_path
        self.results = {}

    def run_collection(self, date: str) -> Dict[str, Any]:
        """步骤1：执行竞价采集"""
        print("=" * 70)
        print("步骤1：竞价采集（09:24-09:26）")
        print("=" * 70)

        try:
            result = subprocess.run(
                [sys.executable, "tasks/collect_auction_snapshot.py", "--date", date],
                capture_output=True,
                text=True,
                timeout=120
            )

            print(result.stdout)

            if result.returncode != 0:
                print(f"❌ 采集失败：{result.stderr}")
                return {"status": "failed", "error": result.stderr}

            return {"status": "success", "output": result.stdout}

        except subprocess.TimeoutExpired:
            print("❌ 采集超时")
            return {"status": "failed", "error": "timeout"}
        except Exception as e:
            print(f"❌ 采集异常：{e}")
            return {"status": "failed", "error": str(e)}

    def verify_data_quality(self, date: str) -> Dict[str, Any]:
        """步骤2：验证数据质量"""
        print("\n" + "=" * 70)
        print("步骤2：数据质量验证")
        print("=" * 70)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 检查数据是否存在
        cursor.execute('SELECT COUNT(*) FROM auction_snapshots WHERE date = ?', (date,))
        total_count = cursor.fetchone()[0]

        if total_count == 0:
            print("❌ 未找到采集数据")
            conn.close()
            return {"status": "failed", "error": "no_data"}

        # 检查数据质量字段
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN volume_ratio_valid = 1 THEN 1 ELSE 0 END) as valid,
                SUM(CASE WHEN data_source = 'production' THEN 1 ELSE 0 END) as production,
                AVG(volume_ratio) as avg_ratio
            FROM auction_snapshots
            WHERE date = ?
        ''', (date,))
        stats = cursor.fetchone()

        total, valid, production, avg_ratio = stats
        valid_rate = valid / total * 100 if total > 0 else 0
        production_rate = production / total * 100 if total > 0 else 0

        print(f"✅ 数据总量：{total}")
        print(f"✅ 有效数据：{valid} ({valid_rate:.2f}%)")
        print(f"✅ 生产数据：{production} ({production_rate:.2f}%)")
        print(f"✅ 平均量比：{avg_ratio:.2f}")

        # 验收标准
        checks = {
            "environment": production_rate > 80,
            "quality": valid_rate > 80,
            "ratio": 0.1 < avg_ratio < 100
        }

        print("\n验收结果：")
        print(f"  环境标记（生产>80%）：{'✅ 通过' if checks['environment'] else '❌ 失败'}")
        print(f"  数据质量（有效>80%）：{'✅ 通过' if checks['quality'] else '❌ 失败'}")
        print(f"  量比合理性（0.1-100）：{'✅ 通过' if checks['ratio'] else '❌ 失败'}")

        conn.close()

        return {
            "status": "success",
            "total": total,
            "valid": valid,
            "valid_rate": valid_rate,
            "production": production,
            "production_rate": production_rate,
            "avg_ratio": avg_ratio,
            "checks": checks
        }

    def run_trap_detection(self, date: str, top: int = 100) -> Dict[str, Any]:
        """步骤3：执行诱多检测"""
        print("\n" + "=" * 70)
        print("步骤3：诱多检测（09:35-09:45）")
        print("=" * 70)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 检测诱多候选（高开+低量比）
        cursor.execute('''
            SELECT
                code, name, auction_price,
                ROUND(auction_change * 100, 2) as change_pct,
                ROUND(volume_ratio, 2) as volume_ratio
            FROM auction_snapshots
            WHERE date = ?
              AND auction_change > 0.05
              AND volume_ratio_valid = 1
              AND volume_ratio < 2.0
            ORDER BY auction_change DESC, volume_ratio ASC
            LIMIT ?
        ''', (date, top))

        trap_candidates = cursor.fetchall()

        print(f"✅ 检测到 {len(trap_candidates)} 只诱多候选（高开+低量比）")

        if len(trap_candidates) > 0:
            print("\n诱多候选Top 10：")
            print(f"{'代码':<12}{'名称':<12}{'价格':>8}{'涨幅%':>8}{'量比':>8}")
            print("-" * 60)
            for stock in trap_candidates[:10]:
                code, name, price, change_pct, volume_ratio = stock
                print(f"{code:<12}{name:<12}{price:>8.2f}{change_pct:>8.2f}{volume_ratio:>8.2f}")

        # 检测强势股票（高开+高量比）
        cursor.execute('''
            SELECT COUNT(*) FROM auction_snapshots
            WHERE date = ?
              AND auction_change > 0.05
              AND volume_ratio_valid = 1
              AND volume_ratio >= 2.0
        ''', (date,))
        strong_count = cursor.fetchone()[0]

        print(f"\n✅ 检测到 {strong_count} 只强势股票（高开+高量比）")

        conn.close()

        # 验收标准：检出率在1%-10%之间
        total_samples = self.results.get('quality', {}).get('total', 0)
        trap_rate = len(trap_candidates) / total_samples * 100 if total_samples > 0 else 0
        check = 1 <= trap_rate <= 10

        print(f"\n验收结果：")
        print(f"  诱多检出率（1%-10%）：{'✅ 通过' if check else '❌ 失败'} ({trap_rate:.2f}%)")

        return {
            "status": "success",
            "trap_count": len(trap_candidates),
            "trap_rate": trap_rate,
            "strong_count": strong_count,
            "top_candidates": trap_candidates[:20],
            "check": check
        }

    def generate_report(self, date: str) -> str:
        """生成验收报告"""
        print("\n" + "=" * 70)
        print("验收报告")
        print("=" * 70)

        collection = self.results.get('collection', {})
        quality = self.results.get('quality', {})
        detection = self.results.get('detection', {})

        report = []
        report.append(f"# 竞价链路验收报告 - {date}")
        report.append("")
        report.append(f"**验收时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        report.append("## 验收结果")
        report.append("")

        all_passed = True

        # 采集验收
        collection_passed = collection.get('status') == 'success'
        all_passed = all_passed and collection_passed
        report.append(f"- 竞价采集：{'✅ 通过' if collection_passed else '❌ 失败'}")

        # 数据质量验收
        if quality.get('status') == 'success':
            quality_checks = quality.get('checks', {})
            quality_passed = all(quality_checks.values())
            all_passed = all_passed and quality_passed
            report.append(f"- 数据质量：{'✅ 通过' if quality_passed else '❌ 失败'}")
            report.append(f"  - 有效率：{quality['valid_rate']:.2f}%")
            report.append(f"  - 生产数据率：{quality['production_rate']:.2f}%")
        else:
            all_passed = False
            report.append("- 数据质量：❌ 失败")

        # 诱多检测验收
        if detection.get('status') == 'success':
            detection_passed = detection.get('check', False)
            all_passed = all_passed and detection_passed
            report.append(f"- 诱多检测：{'✅ 通过' if detection_passed else '❌ 失败'}")
            report.append(f"  - 检出率：{detection['trap_rate']:.2f}%")
        else:
            all_passed = False
            report.append("- 诱多检测：❌ 失败")

        report.append("")

        report.append("## 综合判定")
        report.append("")
        report.append(f"**链路验收**：{'✅ 通过' if all_passed else '❌ 不通过'}")
        report.append("")

        if all_passed:
            report.append("✅ 链路完整，数据质量合格，诱多检测正常，可以进入试运行阶段。")
        else:
            report.append("⚠️ 链路存在问题，请检查上述失败项。")

        report.append("")
        report.append("---")
        report.append("*此报告由 `validate_auction_pipeline.py` 自动生成*")

        return "\n".join(report)

    def validate(self, date: str, top: int = 100, save_report: bool = True) -> Dict[str, Any]:
        """执行完整验收流程"""
        print(f"\n{'='*70}")
        print(f"竞价链路验收 - {date}")
        print(f"{'='*70}\n")

        # 步骤1：采集
        self.results['collection'] = self.run_collection(date)
        if self.results['collection']['status'] != 'success':
            return {"status": "failed", "stage": "collection"}

        # 步骤2：数据质量验证
        self.results['quality'] = self.verify_data_quality(date)
        if self.results['quality']['status'] != 'success':
            return {"status": "failed", "stage": "quality"}

        # 步骤3：诱多检测
        self.results['detection'] = self.run_trap_detection(date, top)

        # 生成报告
        report = self.generate_report(date)
        print("\n" + report)

        # 保存报告
        if save_report:
            report_dir = Path("docs/auction_validation")
            report_dir.mkdir(parents=True, exist_ok=True)
            report_file = report_dir / f"pipeline_{date.replace('-', '')}.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n✅ 验收报告已保存：{report_file}")

        return {
            "status": "success",
            "results": self.results,
            "all_passed": all(self.results.get('quality', {}).get('checks', {}).values())
        }


def main():
    parser = argparse.ArgumentParser(description="竞价链路验收")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"),
                        help="日期（格式：YYYY-MM-DD）")
    parser.add_argument("--top", type=int, default=100,
                        help="诱多候选Top数量")
    parser.add_argument("--skip-collection", action="store_true",
                        help="跳过采集步骤（仅验证已有数据）")
    parser.add_argument("--no-save", action="store_true",
                        help="不保存报告")

    args = parser.parse_args()

    validator = AuctionPipelineValidator()

    if args.skip_collection:
        print("⚠️ 跳过采集步骤，仅验证已有数据")
        # 直接执行数据质量验证和诱多检测
        quality_result = validator.verify_data_quality(args.date)
        validator.results['quality'] = quality_result

        if quality_result['status'] == 'success':
            detection_result = validator.run_trap_detection(args.date, args.top)
            validator.results['detection'] = detection_result

            # 生成报告
            report = validator.generate_report(args.date)
            print("\n" + report)

            if args.no_save == False:
                report_dir = Path("docs/auction_validation")
                report_dir.mkdir(parents=True, exist_ok=True)
                report_file = report_dir / f"pipeline_{args.date.replace('-', '')}.md"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\n✅ 验收报告已保存：{report_file}")

            # 检查验收结果
            quality_checks = quality_result.get('checks', {})
            all_passed = all(quality_checks.values()) and detection_result.get('check', False)

            if all_passed:
                print("\n✅ 验收通过！")
                sys.exit(0)
            else:
                print("\n⚠️ 验收未完全通过，请检查失败项。")
                sys.exit(1)
        else:
            print(f"\n❌ 数据质量验证失败")
            sys.exit(1)
    else:
        result = validator.validate(args.date, args.top, not args.no_save)

        if result['status'] == 'success':
            if result['all_passed']:
                print("\n✅ 验收通过！")
                sys.exit(0)
            else:
                print("\n⚠️ 验收未完全通过，请检查失败项。")
                sys.exit(1)
        else:
            print(f"\n❌ 验收失败：{result['stage']}")
            sys.exit(1)


if __name__ == "__main__":
    main()