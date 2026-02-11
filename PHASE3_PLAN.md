# Phase3 规划文档：竞价快照+历史回测+机器学习增强

> **规划日期**: 2026-02-11
> **版本**: Phase3 - V1.0
> **预计周期**: 4-6周
> **目标**: 构建完整的诱多检测+回测+智能预测系统

---

## 🎯 Phase3 核心目标

### 主目标
1. **竞价快照分析** - 识别"早盘诱多"模式（竞价高开→开盘砸盘）
2. **历史回测框架** - 验证算法准确率，优化参数
3. **机器学习增强** - 提升置信度从85%到90%+

### 验证标准
- 榜单准确率: >70% → >80%
- 误报率: <20% → <15%
- 漏报率: <30% → <25%
- 置信度: 85% → 90%+

---

## 📋 Phase3 详细规划

### 模块1: 竞价快照分析系统

#### 1.1 竞价快照数据采集

**功能需求**:
- 每个交易日09:25采集全市场竞价快照
- 保存竞价数据到Redis/SQLite
- 支持快照数据回放分析

**数据结构**:
```json
{
  "code": "300997.SZ",
  "name": "欢乐家",
  "snapshot_time": "09:25:00",
  "auction_data": {
    "open": 15.50,
    "high": 15.80,
    "low": 15.30,
    "volume": 500000,
    "amount": 7750000,
    "bid_vol": [100000, 200000, 300000],
    "ask_vol": [50000, 100000, 150000],
    "buy_orders": 50,
    "sell_orders": 30
  }
}
```

**实现方案**:
```python
# tasks/collect_auction_snapshot.py
def collect_auction_snapshot():
    """采集全市场竞价快照"""
    # 1. 获取全市场股票列表
    stock_list = get_all_stocks()
    
    # 2. 采集竞价数据
    auction_data = xtdata.get_full_tick(stock_list)
    
    # 3. 保存到数据库
    save_to_redis(auction_data)
    save_to_sqlite(auction_data)
```

#### 1.2 竞价异动检测算法

**检测规则**:
| 模式 | 特征 | 风险级别 |
|------|------|----------|
| 竞价高开+开盘砸盘 | 竞价涨幅>3% + 开盘5分钟内跌幅>2% | 🔴 高 |
| 竞价爆量+尾盘回落 | 竞价量比>2 + 尾盘回落>1% | 🟠 中 |
| 竞价平开+开盘拉升 | 竞价涨幅<1% + 开盘5分钟涨幅>3% | 🟡 低 |

**核心算法**:
```python
def detect_auction_trap(auction_data, open_data):
    """竞价异动检测"""
    auction_change = (auction_data['open'] - prev_close) / prev_close
    open_change = (open_data['open'] - auction_data['open']) / auction_data['open']
    
    # 竞价高开+开盘砸盘
    if auction_change > 0.03 and open_change < -0.02:
        return 'AUC_HIGH_OPEN_DUMP'
    
    # 竞价爆量+尾盘回落
    if auction_data['volume_ratio'] > 2.0 and open_data['tail_drop'] > 0.01:
        return 'AUC_BOOM_TAIL_DROP'
    
    return 'NORMAL'
```

#### 1.3 竞价快照回放器

**功能**:
- 回放任意日期的竞价快照
- 结合开盘后分钟K数据
- 验证竞价异动有效性

**使用方法**:
```bash
# 回放2026-02-10的竞价快照
python tasks/replay_auction_snapshot.py --date 2026-02-10

# 分析竞价高开股票
python tasks/analyze_auction_high_open.py --days 30
```

---

### 模块2: 历史回测框架

#### 2.1 历史数据采集

**数据需求**:
- 每日TOP 50榜单（Phase2扫描结果）
- T+1/T+3/T+5价格走势
- 板块共振数据
- 指数走势（上证/深证/创业板）

**数据存储**:
```sql
-- 历史榜单表
CREATE TABLE history_top_list (
    date TEXT NOT NULL,
    rank INTEGER NOT NULL,
    code TEXT NOT NULL,
    name TEXT,
    confidence REAL,
    trap_type TEXT,
    price REAL,
    PRIMARY KEY (date, rank)
);

-- 回测结果表
CREATE TABLE backtest_results (
    date TEXT,
    code TEXT,
    T1_return REAL,
    T3_return REAL,
    T5_return REAL,
    is_correct INTEGER,  -- 1=准确, 0=误报
    PRIMARY KEY (date, code)
);
```

#### 2.2 自动回测引擎

**回测逻辑**:
```python
def backtest_single_day(date: str, top_list: List[Dict]):
    """单日回测"""
    results = []
    
    for item in top_list:
        code = item['code']
        buy_price = item['price']
        
        # 获取T+1/T+3/T+5价格
        future_prices = get_future_prices(code, date, [1, 3, 5])
        
        # 计算收益率
        T1_return = (future_prices[1] - buy_price) / buy_price
        T3_return = (future_prices[3] - buy_price) / buy_price
        T5_return = (future_prices[5] - buy_price) / buy_price
        
        # 判断是否准确（T+3天内下跌或横盘）
        is_correct = (T3_return < 0.02 or abs(T3_return) < 0.01)
        
        results.append({
            'code': code,
            'T1_return': T1_return,
            'T3_return': T3_return,
            'T5_return': T5_return,
            'is_correct': is_correct
        })
    
    return results
```

#### 2.3 回测报告生成

**报告内容**:
- 总体准确率/误报率/漏报率
- 各时间点准确率（T+1/T+3/T+5）
- 各诱多类型准确率分布
- 最优参数建议

**报告格式**:
```markdown
# 回测报告 - 2026年2月

## 总体统计
- 总预警次数: 150
- 准确次数: 105
- 误报次数: 30
- 漏报次数: 15
- 准确率: 70%
- 误报率: 20%
- 漏报率: 10%

## 时间维度分析
| 时间点 | 准确率 | 平均收益 |
|--------|--------|----------|
| T+1   | 65%    | -2.5%   |
| T+3   | 70%    | -3.2%   |
| T+5   | 72%    | -3.8%   |

## 诱多类型分析
| 类型 | 准确率 | 误报率 |
|------|--------|--------|
| 对倒识别 | 75%    | 15%    |
| 尾盘拉升 | 68%    | 25%    |
| 连板开板 | 72%    | 20%    |
| 竞价高开 | 82%    | 10%    |

## 参数优化建议
- volume_ratio_strong: 2.0 → 1.8
- price_change_min: 0.02 → 0.025
- turnover_high: 0.02 → 0.025
```

---

### 模块3: 机器学习增强

#### 3.1 特征工程

**基础特征**（QPST四维）:
- 量: volume_ratio, volume_volatility, volume_surge
- 价: price_change, amplitude, price_stability
- 空: turnover, turnover_trend
- 时: surge_ratio, time_period

**增强特征**:
- 板块共振: sector_leaders, sector_breadth
- 历史诱多次数: history_trap_count
- 竞价特征: auction_change, auction_volume_ratio
- 指数相关性: index_correlation
- 技术指标: RSI, MACD, KDJ

**特征示例**:
```python
def extract_features(code, kline_df, auction_data=None):
    """提取特征"""
    features = {}
    
    # QPST四维特征
    features.update(extract_qpst_features(kline_df))
    
    # 板块共振特征
    features.update(extract_sector_features(code))
    
    # 竞价特征
    if auction_data:
        features.update(extract_auction_features(auction_data))
    
    # 技术指标特征
    features.update(extract_technical_features(kline_df))
    
    return features
```

#### 3.2 XGBoost模型训练

**模型配置**:
```python
import xgboost as xgb

# 训练参数
params = {
    'objective': 'binary:logistic',
    'eval_metric': 'logloss',
    'max_depth': 6,
    'eta': 0.1,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'n_estimators': 100,
    'seed': 42
}

# 训练模型
model = xgb.XGBClassifier(**params)
model.fit(X_train, y_train)
```

**训练数据**:
- 正样本: 准确的诱多案例（T+3天内下跌）
- 负样本: 正常上涨股票
- 训练集: 70%
- 验证集: 15%
- 测试集: 15%

#### 3.3 模型评估与优化

**评估指标**:
- 准确率 (Accuracy)
- 精确率 (Precision)
- 召回率 (Recall)
- F1分数 (F1-Score)
- AUC-ROC

**优化策略**:
1. 超参数调优（Grid Search + Cross Validation）
2. 特征重要性分析
3. 集成学习（XGBoost + LightGBM）
4. 增量训练（每周更新模型）

**预期效果**:
- 置信度: 85% → 90%+
- 准确率: 70% → 80%
- 误报率: 20% → 15%

---

## 📊 Phase3 实施计划

### 第1-2周: 竞价快照系统

**任务**:
1. 开发竞价快照采集脚本
2. 实现竞价异动检测算法
3. 创建竞价快照回放器
4. 测试竞价数据采集

**交付物**:
- `tasks/collect_auction_snapshot.py`
- `logic/auction_detector.py`
- `tasks/replay_auction_snapshot.py`

### 第3-4周: 历史回测框架

**任务**:
1. 采集历史榜单数据（过去3个月）
2. 实现自动回测引擎
3. 生成回测报告
4. 优化参数配置

**交付物**:
- `logic/backtest_engine.py`
- `data/history/top_list/` (历史榜单)
- `data/backtest/results/` (回测结果)
- `tools/generate_backtest_report.py`

### 第5-6周: 机器学习增强

**任务**:
1. 特征工程实现
2. XGBoost模型训练
3. 模型评估与优化
4. 集成到QPST分析器

**交付物**:
- `logic/ml_feature_extractor.py`
- `logic/ml_trainer.py`
- `models/trap_detection_model.json`
- 更新的`logic/batch_qpst_analyzer.py`

---

## 🎯 预期成果

### 性能指标

| 指标 | Phase2 | Phase3目标 | 提升 |
|------|--------|-----------|------|
| 准确率 | 70% | 80% | +10% |
| 误报率 | 20% | 15% | -5% |
| 漏报率 | 30% | 25% | -5% |
| 置信度 | 85% | 90% | +5% |
| 内存占用 | 1.5GB | 2GB | +0.5GB |

### 功能增强

| 功能 | Phase2 | Phase3 |
|------|--------|--------|
| 竞价分析 | ❌ | ✅ |
| 历史回测 | ❌ | ✅ |
| 机器学习 | ❌ | ✅ |
| 参数优化 | 手动 | 自动 |
| 准确率监控 | 人工 | 自动 |

---

## 📋 技术栈

### 新增依赖
```python
# requirements.txt 新增
xgboost>=2.0.0
scikit-learn>=1.5.0
joblib>=1.3.0
plotly>=5.0.0
```

### 数据存储
- SQLite（历史榜单+回测结果）
- Redis（竞价快照缓存）
- Parquet文件（高效数据存储）

---

## 🚀 快速开始

### 竞价快照采集
```bash
# 采集今日竞价快照
python tasks/collect_auction_snapshot.py

# 回放竞价快照
python tasks/replay_auction_snapshot.py --date 2026-02-10
```

### 历史回测
```bash
# 回测过去30天
python tools/run_backtest.py --days 30

# 生成回测报告
python tools/generate_backtest_report.py --days 30
```

### 机器学习训练
```bash
# 提取特征
python logic/ml_feature_extractor.py --days 90

# 训练模型
python logic/ml_trainer.py --train-days 90

# 评估模型
python logic/ml_trainer.py --eval
```

---

## ✅ 验收标准

### 功能验收
- [ ] 竞价快照采集成功率 >95%
- [ ] 竞价异动检测准确率 >70%
- [ ] 历史回测自动化运行
- [ ] 机器学习模型准确率 >75%

### 性能验收
- [ ] 准确率 >80%
- [ ] 误报率 <15%
- [ ] 漏报率 <25%
- [ ] 置信度 >90%

### 文档验收
- [ ] 完整API文档
- [ ] 使用指南
- [ ] 部署手册
- [ ] 性能测试报告

---

## 📞 下一步

**需要我立即开始实施Phase3吗？**

我可以帮你：
1. **立即开始竞价快照系统开发**
2. **先完善Phase2的文档和测试**
3. **讨论具体的实施细节**
4. **其他需求**

请告诉我你的选择，我会立即开始工作！

---

**规划人**: iFlow CLI (项目总监)  
**规划日期**: 2026-02-11  
**预计完成**: 2026年3月中旬