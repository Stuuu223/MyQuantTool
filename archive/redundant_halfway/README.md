# 冗余halfway_*.py文件归档说明

## 归档原因
根据CTO技术指令(2026-02-22)：
> "这些文件是冗余的，应该被删除或归档。我们只需要一个统一策略引擎。"

## 归档文件清单

### 1. halfway_breakout_detector.py
- **原路径**: `logic/strategies/halfway_breakout_detector.py`
- **功能**: 半路板突破检测器
- **归档原因**: 
  - 与 `halfway_core.py` 存在功能重叠
  - 使用了全局平均基准的错误方案(已被CTO否决)
  - 代码中存在'sustain'字段访问错误
- **替代方案**: 使用新的分层动态Ratio系统 `tools/tiered_ratio_system.py`

### 2. halfway_core.py  
- **原路径**: `logic/strategies/halfway_core.py`
- **功能**: 半路板核心逻辑
- **归档原因**:
  - 存在FloatVolume单位错误(将2.306B误认为2.306M，导致22.5倍误差)
  - 存在UTC时间戳错误(未+8转换北京时区)
  - 使用魔法数字阈值，未考虑股票流动性差异
- **替代方案**: 使用 `compute_active_baseline_v3.py` (已修复上述问题)

### 3. halfway_tick_strategy.py
- **原路径**: `logic/strategies/halfway_tick_strategy.py`
- **功能**: 半路板tick策略
- **归档原因**:
  - 与上述两个文件高度耦合
  - 策略逻辑分散在多个文件中，维护困难
- **替代方案**: 待重新设计统一策略引擎

## 历史背景

### 关键错误教训
1. **FloatVolume单位错误**: 
   - xtdata.get_instrument_detail()返回的FloatVolume已经是"股"单位(2,306,141,629)
   - 旧代码乘以10000，导致22.5倍误差

2. **UTC时间戳错误**:
   - QMT返回的是UTC毫秒时间戳
   - 旧代码未+8小时，导致09:30数据显示为01:30
   - 已修复：`pd.to_datetime(tick_df['time'], unit='ms') + timedelta(hours=8)`

3. **分层Ratio必要性**:
   - 300017(高频票): 最高ratio仅0.92，远低于2.0阈值
   - 000547(低频票): ratio可达5.0+
   - 需要不同的分位基准(90th vs 75th)和阈值(2.0 vs 5.0)

## 新方案架构

### 分层动态Ratio系统
位置: `tools/tiered_ratio_system.py`

```python
TIERED_CONFIG = {
    'high_freq': {  # 高频活跃票
        'stocks': ['300017.SZ', '300058.SZ'],
        'baseline_percentile': 90,
        'ratio_threshold': 2.0
    },
    'low_freq': {  # 低频冷门票
        'stocks': ['000547.SZ', '603778.SH'],
        'baseline_percentile': 75,
        'ratio_threshold': 5.0
    }
}
```

### 横向相对强度排名
- 将目标股与150股池进行横向比较
- 目标: 进入Top 2% (约前3只股)
- 解决高频票单票ratio失效问题

## 归档日期
2026-02-22

## 责任人
CTO技术决策，工程师执行归档
