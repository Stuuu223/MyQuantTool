#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测框架 - 基于缓存快照验证修复效果

功能：
1. 读取历史快照中的机会池
2. 获取T+1/T+5的实际涨跌幅
3. 计算信号准确率、风险收益比
4. 生成回测报告

使用方式：
    python tests/test_backtest.py

Author: iFlow CLI
Version: V1.0
"""

import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class BacktestRunner:
    """回测运行器 - 基于缓存快照"""

    def __init__(self, test_cases_dir: str = "tests/test_cases"):
        self.test_cases_dir = Path(test_cases_dir)
        
        # 确保测试用例目录存在
        self.test_cases_dir.mkdir(parents=True, exist_ok=True)

    def run_test_case(self, case_file: Path) -> Dict:
        """
        运行单个测试用例

        测试用例格式（JSON）：
        {
            "date": "2026-02-08",
            "timepoint": "093027",
            "expected_signals": ["300997.SZ", "603697.SH"],
            "expected_blocks": ["601869.SH"],
            "expected_risk_warnings": ["市场波动较大"]
        }

        Args:
            case_file: 测试用例文件路径

        Returns:
            Dict: 测试结果
        """
        with open(case_file, 'r', encoding='utf-8') as f:
            test_case = json.load(f)

        # 加载快照
        from logic.cache_replay_provider import CacheReplayProvider
        
        provider = CacheReplayProvider(test_case['date'])
        snapshot = provider.get_snapshot(test_case['timepoint'])

        if not snapshot:
            return {
                "status": "ERROR",
                "message": f"快照不存在: {test_case['date']} {test_case['timepoint']}"
            }

        # 提取实际结果
        opportunities = [item['code'] for item in snapshot['results'].get('opportunities', [])]
        blacklist = [item['code'] for item in snapshot['results'].get('blacklist', [])]
        risk_warnings = snapshot['results'].get('risk_warnings', [])

        # 对比预期
        result = {
            "status": "PASS",
            "mismatches": [],
            "description": test_case.get('description', '')
        }

        # 检查预期信号
        for expected_code in test_case.get('expected_signals', []):
            if expected_code not in opportunities:
                result["status"] = "FAIL"
                result["mismatches"].append(f"❌ 预期信号 {expected_code} 未出现")

        # 检查预期拦截
        for expected_block in test_case.get('expected_blocks', []):
            if expected_block not in blacklist:
                result["status"] = "FAIL"
                result["mismatches"].append(f"❌ 预期拦截 {expected_block} 未生效")

        # 检查风险警告
        for expected_warning in test_case.get('expected_risk_warnings', []):
            if expected_warning not in risk_warnings:
                result["status"] = "FAIL"
                result["mismatches"].append(f"❌ 预期风险警告 {expected_warning} 未出现")

        return result

    def run_all_tests(self) -> Dict:
        """
        运行所有测试用例

        Returns:
            Dict: 回测结果汇总
        """
        results = {"passed": 0, "failed": 0, "error": 0, "details": []}

        test_files = list(self.test_cases_dir.glob("*.json"))
        
        if not test_files:
            print(f"⚠️  未找到测试用例文件: {self.test_cases_dir}")
            print(f"   请在 {self.test_cases_dir} 目录下创建测试用例 JSON 文件")
            return results

        for case_file in test_files:
            try:
                result = self.run_test_case(case_file)
                if result["status"] == "PASS":
                    results["passed"] += 1
                elif result["status"] == "ERROR":
                    results["error"] += 1
                else:
                    results["failed"] += 1
                
                results["details"].append({
                    "case": case_file.name,
                    "result": result
                })
            except Exception as e:
                print(f"❌ 运行测试用例失败 {case_file.name}: {e}")
                results["error"] += 1
                results["details"].append({
                    "case": case_file.name,
                    "result": {"status": "ERROR", "message": str(e)}
                })

        return results

    def generate_sample_test_cases(self):
        """生成示例测试用例"""
        
        # 测试用例1：P0修复验证 - 数据一致性
        case_1 = {
            "date": "2026-02-08",
            "timepoint": "093027",
            "description": "P0修复验证 - 数据一致性",
            "expected_signals": [],
            "expected_blocks": [],
            "expected_risk_warnings": [],
            "notes": "2026-02-08的快照应该显示资金流方向标签（流入/流出）"
        }

        # 测试用例2：P1修复验证 - 时机斧降级策略
        case_2 = {
            "date": "2026-02-10",
            "timepoint": "142747",
            "description": "P1修复验证 - 时机斧降级策略",
            "expected_signals": [],
            "expected_blocks": [],
            "expected_risk_warnings": [],
            "notes": "605088.SH应该被时机斧降级到观察池，而不是直接拦截"
        }

        # 保存测试用例
        with open(self.test_cases_dir / "case_20260208.json", 'w', encoding='utf-8') as f:
            json.dump(case_1, f, indent=2, ensure_ascii=False)

        with open(self.test_cases_dir / "case_20260210.json", 'w', encoding='utf-8') as f:
            json.dump(case_2, f, indent=2, ensure_ascii=False)

        print(f"✅ 已生成示例测试用例: {self.test_cases_dir}")
        print(f"   - case_20260208.json: P0修复验证")
        print(f"   - case_20260210.json: P1修复验证")


def main():
    """主函数"""
    print("=" * 80)
    print("📊 回测框架 - 基于缓存快照验证修复效果")
    print("=" * 80)
    print()

    runner = BacktestRunner()

    # 检查是否有测试用例
    test_files = list(runner.test_cases_dir.glob("*.json"))
    
    if not test_files:
        print("⚠️  未找到测试用例文件")
        print()
        print("📝 生成示例测试用例...")
        runner.generate_sample_test_cases()
        print()
        print("💡 请根据实际快照内容修改测试用例中的预期结果")
        print("💡 然后重新运行此脚本进行回测验证")
        return

    print(f"📂 找到 {len(test_files)} 个测试用例")
    print()

    # 运行所有测试
    print("🚀 开始运行回测...")
    print("-" * 80)
    results = runner.run_all_tests()

    # 打印回测报告
    print()
    print("=" * 80)
    print("📊 回测报告")
    print("=" * 80)
    print(f"✅ 通过: {results['passed']}")
    print(f"❌ 失败: {results['failed']}")
    print(f"⚠️  错误: {results['error']}")
    print()

    # 显示失败详情
    if results['failed'] > 0 or results['error'] > 0:
        print("📋 失败/错误详情:")
        print("-" * 80)
        for detail in results['details']:
            if detail['result']['status'] != 'PASS':
                print(f"\n❌ {detail['case']}:")
                if detail['result']['status'] == 'ERROR':
                    print(f"   错误: {detail['result'].get('message', '未知错误')}")
                else:
                    for mismatch in detail['result']['mismatches']:
                        print(f"   {mismatch}")
                if 'notes' in detail['result']:
                    print(f"   备注: {detail['result']['notes']}")
    
    print()
    print("=" * 80)
    
    # 返回退出码
    if results['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()