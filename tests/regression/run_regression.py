# -*- coding: utf-8 -*-
"""
回归测试一键运行脚本

用法：
    python tests/regression/run_regression.py

三层测试：
1. 量纲铁律测试（无需 QMT 环境，纯数学验证）  → 必须 100% 通过
2. L1 探针存活测试（mock QMT，验证派发拦截）   → 必须 100% 通过
3. 分数基准稳定测试（需要 xtquant，无环境跳过）→ 有环境时必须通过

何时运行：
    - 修改 kinetic_core_engine.py 后
    - 修改 run_live_trading_engine.py 打分路径后
    - 修改 true_dictionary.py 的 get_float_volume 后
    - 每次 AI 生成修复代码后，提交 GitHub 前
"""
import subprocess
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def run_tests():
    print("=" * 70)
    print("[回归测试] MyQuantTool 量化引擎回归测试套件")
    print("=" * 70)

    test_modules = [
        ("量纲铁律测试",   "tests/regression/test_dimension_law.py"),
        ("L1探针存活测试", "tests/regression/test_l1_probe.py"),
        ("分数基准稳定",   "tests/regression/test_score_baseline.py"),
    ]

    all_passed = True
    results = []
    for label, module in test_modules:
        print(f"\n>>> 运行: {label} ({module})")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", module, "-v", "--tb=short"],
            cwd=ROOT,
            capture_output=False
        )
        passed = result.returncode == 0
        results.append((label, passed))
        if not passed:
            all_passed = False

    print("\n" + "=" * 70)
    print("[汇总]")
    for label, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {label}")
    print("=" * 70)

    if all_passed:
        print("[OK] 所有回归测试通过，可以安全提交！")
    else:
        print("[BLOCK] 存在失败的回归测试，请修复后再提交！")
        print("提示：检查 docs/architecture/PHYSICS_LAW.md 中的铁律")
    print("=" * 70)
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(run_tests())
