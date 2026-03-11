# 回归测试脚手架 - MyQuantTool

## 作用

每次修改打分逻辑（`kinetic_core_engine.py`、`run_live_trading_engine.py`、
`true_dictionary.py` 等核心模块）后，跑一遍回归测试，确认：

1. **分数基准稳定** — 已知妖股（300997、603697）在固定日期的得分不超过 ±5 分漂移
2. **量纲自校验** — float_volume、volume、amount 单位是否正确（对照 PHYSICS_LAW.md）
3. **L1 探针存活** — `_micro_defense_check` 中 L1 放量滞涨探针能否正确拦截派发信号
4. **Scan/Live 同源** — Scan 模式与 Live 模式对同一快照的打分误差 < 2 分

## 文件结构

```
tests/regression/
├── README.md                  # 本文件
├── run_regression.py          # 一键运行所有测试
├── test_dimension_law.py      # 量纲铁律单元测试（对照 PHYSICS_LAW.md）
├── test_score_baseline.py     # 分数基准稳定测试（300997/603697 已知案例）
└── test_l1_probe.py           # L1 探针存活测试
```

## 快速使用

```bash
# 一键运行全部回归测试（推荐每次提交前执行）
python tests/regression/run_regression.py

# 只跑量纲测试（最快，无需 xtquant 环境）
python -m pytest tests/regression/test_dimension_law.py -v

# 只跑 L1 探针测试
python -m pytest tests/regression/test_l1_probe.py -v

# 只跑分数基准（需要 xtquant 环境，无环境自动跳过）
python -m pytest tests/regression/test_score_baseline.py -v
```

## 通过标准

| 测试项 | 通过条件 | 失败处理 |
|--------|----------|----------|
| 量纲自校验 | float_market_cap >= 2亿 | 阻断合并，检查 float_volume |
| 分数基准 | \|当前分 - 基准分\| <= 5.0 | 更新基准或回滚代码 |
| L1 探针 | 派发信号返回 False | 检查 `_micro_defense_check` |
| delta_turnover 公式 | (手*100)/股*100 结果约 0.01% | 检查 V70 量纲修复 |

## 何时更新基准分数

在 `test_score_baseline.py` 的 `SCORE_BASELINES` 字典中更新：
- **有意调参**（如修改引力阻尼系数）：允许更新基准，需注明原因
- **回归 BUG**（如修复量纲错误导致分数变化）：必须先确认方向正确再更新
- **绝不允许**：因为测试失败就直接扩大区间掩盖问题
