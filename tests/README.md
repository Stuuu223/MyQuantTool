# 测试目录结构

## 目录组织

```
tests/
├── __init__.py              # 测试包初始化
├── README.md                # 本文件
├── unit/                    # 单元测试（自动化）
│   ├── __init__.py
│   ├── test_capital_allocator.py
│   ├── test_contract_compliance.py
│   ├── test_qmt_historical_provider.py
│   └── test_true_attack_detector.py
└── manual/                  # 手动/集成测试
    ├── __init__.py
    ├── test_core_system_emergency.py
    ├── test_halfway_detector_integration.py
    ├── test_halfway_in_unified_core.py
    ├── test_unified_warfare_core.py
    └── test_unified_warfare_real_samples.py
```

## 分类标准

### unit/ - 真正单元测试
- 使用 pytest 或 unittest 框架
- 包含明确的断言语句 (assert)
- 可自动化运行
- 测试单一组件的独立功能

### manual/ - 手动/集成测试
- 主要用于调试和验证
- 依赖print输出而非断言
- 需要人工判断结果
- 用于复杂场景或集成验证

## 运行测试

```bash
# 运行所有单元测试
python -m pytest tests/unit/ -v

# 运行单个测试文件
python -m pytest tests/unit/test_capital_allocator.py -v

# 运行手动测试（需要人工检查输出）
python tests/manual/test_unified_warfare_core.py
```

## V16测试清理

已删除/迁移的过期测试：
- test_core_system_emergency.py (V16版本，已移至manual/)

## 文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| test_capital_allocator.py | 单元测试 | CapitalAllocator完整单元测试 |
| test_contract_compliance.py | 单元测试 | 架构契约一致性测试 |
| test_qmt_historical_provider.py | 单元测试 | QMT历史数据提供者测试 |
| test_true_attack_detector.py | 单元测试 | TrueAttackDetector完整测试套件 |
| test_core_system_emergency.py | 手动测试 | V16系统健康检查（过期） |
| test_halfway_detector_integration.py | 手动测试 | Halfway Breakout集成测试 |
| test_halfway_in_unified_core.py | 手动测试 | 统一战法核心Halfway测试 |
| test_unified_warfare_core.py | 手动测试 | 统一战法核心架构验证 |
| test_unified_warfare_real_samples.py | 手动测试 | 真实历史样本验证 |
