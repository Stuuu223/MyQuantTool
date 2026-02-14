# 竞价强弱校验器使用指南

## 概述

竞价强弱校验器（Auction Strength Validator）是 V12.1.0 的核心模块之一，用于在集合竞价阶段识别"预期差"，避免竞价陷阱。

## 核心功能

### 1. 明牌焦点股判断
- **逻辑**：昨日涨停股今日竞价量比 < 1.0 或 低开 → 不及预期 → 放弃
- **特点**：昨日越强，今日预期越高
- **阈值**：
  - 最小量比：1.0
  - 最小高开：0%（不能低开）

### 2. 首板挖掘判断
- **逻辑**：竞价量比 > 3.0 且 高开 1-3% → 超预期 → 加分
- **特点**：竞价爆量跳空高开 → 强烈关注
- **阈值**：
  - 最小量比：3.0
  - 最小高开：1%
  - 最大高开：3%

### 3. 基础判定
- **逻辑**：量比排序 + 涨幅排序配合
- **阈值**：
  - 最小量比：1.5
  - 最小高开：2%

## 使用方法

### 基本用法

```python
from logic.strategies.auction_strength_validator import get_auction_strength_validator

# 获取校验器实例
validator = get_auction_strength_validator()

# 准备竞价数据
auction_data = {
    "open_price": 1850.0,      # 竞价开盘价
    "prev_close": 1800.0,      # 昨日收盘价
    "volume_ratio": 2.5,       # 竞价量比
    "amount": 500000000,       # 竞价成交额（元）
    "high_price": 1860.0,      # 竞价最高价
    "low_price": 1840.0,       # 竞价最低价
    "is_limit_up": False       # 是否竞价涨停
}

# 验证竞价强弱
result = validator.validate_auction(
    stock_code="600519",
    auction_data=auction_data
)

# 查看结果
print(f"是否有效: {result['is_valid']}")
print(f"操作建议: {result['action']}")  # STRONG_BUY/BUY/WATCH/REJECT
print(f"原因: {result['reason']}")
print(f"置信度: {result['confidence']}")
```

### 批量验证

```python
# 批量验证多只股票
batch_data = {
    "600519": auction_data_1,
    "000001": auction_data_2,
    "300750": auction_data_3
}

results = validator.batch_validate(batch_data)

for code, result in results.items():
    print(f"{code}: {result['action']}")
```

### 计算预期溢价

```python
# 计算竞价预期溢价率
expectation = validator.calculate_expectation("600519")
print(f"预期高开幅度: {expectation*100:.2f}%")
```

## 返回结果说明

### 结果结构

```python
{
    "is_valid": bool,          # 是否通过验证
    "reason": str,             # 原因说明
    "action": str,             # 操作建议
    "confidence": float,       # 置信度（0-1）
    "details": {               # 详细信息
        "open_gap_pct": float,     # 高开幅度
        "volume_ratio": float,     # 量比
        "expectation": float,      # 预期溢价
        "is_focus_stock": bool,    # 是否焦点股
        "is_limit_up": bool,       # 是否竞价涨停
        "bonus_points": float,     # 加分项
        "bonus_reasons": list,     # 加分原因
        "calculation_time_ms": float  # 计算耗时
    }
}
```

### 操作建议说明

- **STRONG_BUY**：强烈买入（置信度 ≥ 0.8）
- **BUY**：买入（置信度 0.6-0.8）
- **WATCH**：观察（置信度 0.4-0.6）
- **REJECT**：拒绝（置信度 < 0.4）

## 性能指标

- **单次验证耗时**：< 30ms ✅
- **批量验证效率**：~0ms/股（得益于缓存）
- **缓存时间**：
  - 历史数据：1小时
  - 预期数据：5分钟

## 测试用例

运行测试：

```bash
python test_auction_strength_validator.py
```

测试覆盖：
- ✅ 焦点股超预期
- ✅ 焦点股不及预期
- ✅ 首板超预期
- ✅ 首板爆量跳空
- ✅ 基础通过
- ✅ 未达阈值
- ✅ 竞价涨停

## 集成到三漏斗扫描器

```python
from logic.strategies.triple_funnel_scanner import TripleFunnelScanner
from logic.strategies.auction_strength_validator import get_auction_strength_validator

# 获取校验器
auction_validator = get_auction_strength_validator()

# 在扫描过程中使用
for stock in candidates:
    # 1. 板块共振过滤
    resonance_result = wind_filter.check_sector_resonance(stock['code'])
    
    # 2. 动态阈值过滤
    thresholds = dynamic_threshold.calculate_thresholds(
        stock['code'],
        current_time,
        sentiment_stage
    )
    
    # 3. 竞价强弱校验
    auction_result = auction_validator.validate_auction(
        stock['code'],
        stock['auction_data']
    )
    
    # 综合判断
    if (resonance_result['is_resonance'] and
        auction_result['is_valid']):
        # 通过所有过滤器
        pass
```

## 注意事项

1. **数据格式**：确保竞价数据包含所有必需字段
2. **焦点股判断**：系统会自动判断是否是焦点股，也可以手动指定
3. **降级策略**：数据缺失时返回中性判断（WATCH）
4. **缓存优化**：首次计算后，预期数据会被缓存5分钟

## 维护和优化

- 定期更新历史数据（data/hot_stocks.json）
- 根据实际回测结果调整阈值参数
- 监控性能指标，确保 <30ms 的响应时间

## 相关文件

- 主模块：`logic/strategies/auction_strength_validator.py`
- 测试脚本：`test_auction_strength_validator.py`
- 历史数据：`data/hot_stocks.json`
- 板块共振过滤器：`logic/strategies/wind_filter.py`
- 动态阈值管理器：`logic/strategies/dynamic_threshold.py`