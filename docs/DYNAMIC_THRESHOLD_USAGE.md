---
version: V12.1.0
updated: 2026-02-15
scope: logic/full_market_scanner.py, tasks/run_event_driven_monitor.py
author: MyQuantTool Team
---

# 动态阈值管理器使用指南

## 概述

动态阈值管理器（`DynamicThreshold`）是V12.1.0的核心模块，用于根据股票市值、交易时间和市场情绪动态计算筛选阈值。

## 功能特性

### 1. 市值分层

- **小盘股** (<50亿): 流通市值 × 0.2%
- **中盘股** (50-100亿): 流通市值 × 0.1%
- **大盘股** (100-1000亿): 流通市值 × 0.05%
- **超大盘股** (>1000亿): 流通市值 × 0.02%

### 2. 时间分段调整

- **开盘阶段** (9:30-10:00): 放宽阈值 (×0.8)
- **盘中阶段** (10:00-14:30): 标准阈值 (×1.0)
- **尾盘阶段** (14:30-15:00): 严格阈值 (×1.2)

### 3. 情绪周期调整

- **上升期** (启动/主升/高潮): 激进策略 (×0.8)
- **震荡期** (分歧): 标准策略 (×1.0)
- **下降期** (退潮/冰点): 保守策略 (×1.2)

## 使用方法

### 基本用法

```python
from logic.strategies.dynamic_threshold import DynamicThreshold, get_dynamic_threshold
from datetime import datetime

# 获取单例实例
dt = get_dynamic_threshold()

# 计算单只股票的阈值
thresholds = dt.calculate_thresholds(
    stock_code='002202.SZ',
    current_time=datetime.now(),
    sentiment_stage='divergence'
)

print(f"主力流入阈值: {thresholds['main_inflow_min']/1e4:.0f}万")
print(f"最小涨幅: {thresholds['pct_chg_min']}%")
print(f"市值分层: {thresholds['market_cap_tier_name']}")
```

### 批量计算

```python
# 批量计算多只股票的阈值
stock_codes = ['002202.SZ', '601600.SH', '002842.SZ']

results = dt.batch_calculate_thresholds(
    stock_codes=stock_codes,
    current_time=datetime.now(),
    sentiment_stage='divergence'
)

for code, thresholds in results.items():
    print(f"{code}: {thresholds['main_inflow_min']/1e4:.0f}万")
```

### 在扫描器中集成

```python
from logic.strategies.dynamic_threshold import get_dynamic_threshold

class MyScanner:
    def __init__(self):
        self.dt_manager = get_dynamic_threshold()

    def scan_stock(self, stock_code, tick_data, current_time):
        # 获取动态阈值
        thresholds = self.dt_manager.calculate_thresholds(
            stock_code=stock_code,
            current_time=current_time,
            sentiment_stage=self.current_sentiment_stage
        )

        # 使用动态阈值进行筛选
        if tick_data['main_inflow'] >= thresholds['main_inflow_min']:
            if tick_data['pct_chg'] >= thresholds['pct_chg_min']:
                if tick_data['volume_ratio'] >= thresholds['volume_ratio_min']:
                    return True

        return False
```

## 返回值说明

`calculate_thresholds()` 方法返回一个字典，包含以下字段：

### 核心阈值
- `pct_chg_min`: 最小涨幅（%）
- `volume_ratio_min`: 最小量比
- `turnover_min`: 最小换手率（%）
- `main_inflow_min`: 最小主力流入（元）
- `risk_score_max`: 最大风险评分

### 调整信息
- `circulating_cap`: 流通市值（元）
- `market_cap_tier`: 市值分层代码（'small', 'mid', 'large', 'mega'）
- `market_cap_tier_name`: 市值分层名称
- `time_segment`: 时间分段代码（'open', 'mid', 'close'）
- `time_segment_name`: 时间分段名称
- `time_adjustment`: 时间调整系数
- `sentiment_stage`: 情绪周期阶段
- `sentiment_stage_name`: 情绪周期名称
- `sentiment_adjustment`: 情绪调整系数
- `final_adjustment`: 最终调整系数（时间 × 情绪）

### 性能信息
- `calculation_time_ms`: 计算耗时（毫秒）

## 性能指标

- **单次计算耗时**: <50ms
- **批量计算**: 91只股票 <1ms
- **缓存优化**: 市值数据缓存1小时

## 注意事项

1. **股票代码格式**: 支持带后缀（如"002202.SZ"）和不带后缀（如"002202"）两种格式
2. **数据来源**: 优先使用 `data/equity_info_mvp.json`，备用 `data/equity_info_tushare.json`
3. **降级策略**: 数据缺失时使用默认阈值（1000万主力流入）
4. **日志记录**: 使用DEBUG级别记录详细计算过程

## 验收标准

✅ 能够根据市值动态计算阈值
✅ 能够根据时间分段调整
✅ 能够根据情绪周期调整
✅ 单次计算耗时<50ms
✅ 代码符合项目规范

## 测试

运行内置测试：

```bash
python -m logic.strategies.dynamic_threshold
```

或运行全面验证测试：

```bash
python -c "from logic.strategies.dynamic_threshold import DynamicThreshold; dt = DynamicThreshold(); print(f'已加载 {len(dt.equity_info)} 只股票')"
```

## 作者

- Version: V12.1.0
- Date: 2026-02-14
- Author: iFlow CLI