# V17 技术债清单

## 已修复 ✅

### 1. 最大回撤计算 (2026-02-18)
- **问题**: max_drawdown始终返回0.0
- **修复**: 基于equity_curve滚动计算peak和drawdown
- **验证**: V3回测显示MDD=5.00%

### 2. 成本模型参数化 (2026-02-18)
- **问题**: 硬编码万三费率
- **修复**: CostModel类，默认万0.85（真实账户费率）+ 10bp滑点
- **验证**: JSON报告包含cost_assumptions字段

### 3. Signal Layer三层统计 (2026-02-18)
- **问题**: signal_layer全部为0
- **修复**: 分离Raw/Executable/Executed三层统计
- **验证**: V3回测显示Raw open=31, Executable=61, Executed=30

### 4. 涨跌停检查 (2026-02-18)
- **问题**: 无涨跌停约束
- **修复**: _check_limit_price方法，支持10cm/20cm/30cm
- **验证**: 压力测试通过（test_limit_price.py）

## 待优化 ⚠️

### 1. Raw Close Signal重复统计
**当前状态**: 87,439笔（过高）
**原因**: 每个tick都检查平仓条件，首次满足后仍持续计数
**建议方案**: 
- 在T1Position添加first_exit_signal_timestamp字段
- 只记录"首次满足平仓条件"的那个tick
- 预期结果: Raw close ≈ 30（与Executed同量级）

**优先级**: 中
**阻塞性**: 不阻塞主线（Executable/Executed统计正确）
**计划**: 在80×64基线后实施

### 2. HALFWAY策略A/B测试
**当前状态**: TRIVIAL V3已完成，HALFWAY待跑
**阻塞**: HalfwaySignalAdapter需要验证
**下一步**: 
- 运行HALFWAY 20×30
- 对比TRIVIAL vs HALFWAY的三层信号统计
- 分析策略质量差异

**优先级**: 高
**阻塞性**: 阻塞80×64扩量

## 下一步行动 (按CTO指示)

1. **立即**: 完成HALFWAY 20×30 A/B测试
2. **随后**: 80×64扩量建立V17正式基线
3. **技术债**: Raw close首触发计数改造（择机实施）
