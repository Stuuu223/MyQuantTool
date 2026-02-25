# Phase 2: Tick级热复盘系统架构设计文档

## 一、总体架构

```
TickReplayEngine (主引擎)
├── ConfigManager (参数SSOT - 对齐live_sniper)
├── QmtDataManager (数据访问)
├── ParallelProcessor (并行处理)
└── StockTickProcessor (单股处理器)
    ├── VolumeRatioCalculator (量比计算)
    ├── V18ScoreEngine (V18评分 - 时间衰减Ratio化)
    ├── ExplosionPointDetector (起爆点检测)
    └── BattleResultCalculator (战果计算)
```

## 二、核心数据模型

### TickSnapshot
- timestamp: datetime (3秒级精度)
- price, volume, amount, bid/ask

### VolumeRatioMetrics  
- volume_ratio: 量比 = 估算全日成交量 / 5日均量
- turnover_rate_per_min: 每分钟换手率(核心指标)
- base_score, time_decay_ratio, final_v18_score

### ExplosionPoint
- stock_code, timestamp, explosion_type
- trigger_price, volume_ratio_at_explosion
- v18_score, confidence

### TickReplayReport
- date, total_scanned, total_explosion_points
- stock_results, daily_statistics, limit_up_analysis

## 三、核心算法

### 1. 盘中量比计算
```python
# 估算全日成交量 = current_volume * (240 / elapsed_minutes)
# 量比 = 估算全日成交量 / avg_volume_5d
```

### 2. 起爆点检测条件(与实盘对齐)
- 量比 > 分位数阈值(0.95)
- 每分钟换手 > 0.2%
- 价格突破(3分钟新高)
- 成交量突增(较前3分钟增长>50%)

### 3. V18评分(时间衰减Ratio化)
```python
# 基础分 = min(涨幅*5, 100) + 量比/换手加分
# 时间衰减: 09:30-09:40(1.2x), 09:40-10:30(1.0x), 10:30-14:00(0.8x), 14:00+(0.5x)
# 最终分 = 基础分 * 时间衰减系数
```

## 四、配置对齐

所有参数从ConfigManager读取，对齐`live_sniper`配置：
- volume_ratio_percentile: 0.95
- turnover_rate_per_min_min: 0.2
- time_decay_ratios: {early_morning_rush: 1.2, morning_confirm: 1.0, noon_trash: 0.8, tail_trap: 0.5}
- scoring_bonuses: {extreme_volume_ratio: 3.0, extreme_vol_bonus: 10}

## 五、并行处理方案

- 多进程并行: ProcessPoolExecutor (Windows兼容)
- 批次处理: 100只/批次
- 最大工作进程: 8核
- 单股超时: 60秒

## 六、关键文件规划

```
logic/backtest/
├── tick_replay_engine.py        # 主引擎
├── tick_replay_models.py        # 数据模型
└── algorithms/
    ├── volume_ratio_calculator.py   # 量比计算
    ├── explosion_detector.py        # 起爆点检测
    └── v18_score_engine.py          # V18评分
```

---
设计完成时间: 2026-02-26
设计团队: AI架构师团队
