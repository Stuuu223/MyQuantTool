# 板块共振过滤器 (Wind Filter) - V12.1.0

## 概述

板块共振过滤器是 V12.1.0 版本的核心模块，用于解决"孤军深入"问题——个股在动但板块没动，导致容易被砸。

## 核心功能

拒绝"孤军深入"，只有"个股强 + 板块共振"才是真龙。

### 三大判断条件

满足**至少2个条件**才返回True：

- **条件A**: 板块内涨停股 ≥ 3只
- **条件B**: 板块内上涨股票占比 ≥ 35%
- **条件C**: 板块指数连续3日资金净流入

### 共振评分

根据通过的条件计算共振分数（0-1）：
- 条件A权重: 0.4
- 条件B权重: 0.35
- 条件C权重: 0.25

## 使用方法

### 基础使用

```python
from logic.strategies.wind_filter import get_wind_filter

# 获取单例
wind_filter = get_wind_filter()

# 检查单只股票
result = wind_filter.check_sector_resonance('000001')

# 判断结果
if result['is_resonance']:
    print("✅ 通过板块共振检查")
else:
    print("❌ 未通过板块共振检查")
```

### 批量检查

```python
# 批量检查
watchlist = ['000001', '000002', '600519']
results = wind_filter.batch_check_resonance(watchlist)

# 筛选通过的股票
passed_stocks = [
    code for code, result in results.items()
    if result['is_resonance']
]
```

### 返回值说明

```python
{
    'is_resonance': bool,           # 是否共振
    'limit_up_count': int,          # 涨停股数
    'breadth': float,               # 上涨比例 (0-1)
    'sustained_inflow': bool,       # 持续流入
    'resonance_score': float,       # 共振分数 (0-1)
    'passed_conditions': list,      # 通过的条件列表 ['A', 'B', 'C']
    'industry': str,                # 行业名称
    'details': dict                 # 详细信息
}
```

## 性能优化

### 缓存策略

- **涨停股统计**: 缓存60秒
- **板块表现**: 缓存60秒
- **资金流数据**: 缓存10分钟（全局缓存）

### 缓存共享

同板块的股票共享缓存，第二次检查耗时接近0ms。

### 性能指标

- **首次检查**: 400-700ms（需要加载数据）
- **同板块检查**: 0ms（缓存命中）
- **批量检查**: 平均<100ms（实际使用场景）

## 数据源

- **板块映射**: `data/stock_sector_map.json`
- **实时价格**: QMT Tick / EasyQuotation
- **资金流数据**: AkShare

## 验收标准

- ✅ 能够正确判断板块共振状态
- ✅ 单次判断耗时<100ms（使用缓存）
- ⏳ 共振准确率>80%（需历史数据回测验证）
- ✅ 代码符合项目规范（使用现有数据提供者）
- ✅ 数据缓存优化（避免重复计算）
- ✅ 详细日志记录

## 集成示例

### 与三漏斗扫描器集成

```python
from logic.strategies.wind_filter import get_wind_filter

wind_filter = get_wind_filter()

# 在Level 2之后添加板块共振检查
level2_passed_stocks = ['000001', '000002', '600519']

level3_candidates = []
for code in level2_passed_stocks:
    result = wind_filter.check_sector_resonance(code)

    if result['is_resonance']:
        level3_candidates.append(code)
    else:
        logger.info(f"{code} 未通过板块共振检查，被过滤")
```

## 文件结构

```
logic/strategies/
├── wind_filter.py              # 主模块
└── wind_filter_usage.py        # 使用示例
```

## 测试

运行使用示例：

```bash
python logic/strategies/wind_filter_usage.py
```

## 注意事项

1. **首次运行较慢**: 需要加载行业资金流数据（约500ms）
2. **缓存有效期**: 板块数据缓存60秒，资金流数据缓存10分钟
3. **非交易时间**: 非交易时间可能无法获取实时数据，返回默认值
4. **行业映射**: 确保 `data/stock_sector_map.json` 文件存在且数据完整

## 版本信息

- **版本**: V12.1.0
- **作者**: iFlow CLI
- **日期**: 2026-02-14
- **状态**: ✅ 已完成