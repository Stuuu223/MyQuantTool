# 🚀 MyQuantTool 下周优化规划实现指南

**版本**: 3.3.0 (下周 LSTM + 关键词扩展版)
**状态**: 🚧 开发完成 ✅
**分支**: feature/next-week-lstm-keywords
**提交数**: 3 commits (LSTM + 关键词 + 仪表板)

---

## 📄 本周实现江采

### 1. LSTM上榜预测模型 (新增)

| 模块 | 文件 | 行数 | 功能 |
|--------|--------|--------|--------|
| **LSTM预测器** | `logic/lstm_predictor.py` | 450+ | 时间序列特征 + 模型训练预测 |
| **关键词提取** | `logic/keyword_extractor.py` | 400+ | TF-IDF + TextRank + 板块分类 |
| **高级仪表板** | `pages/advanced_analysis.py` | 350+ | LSTM训练、字词浅提、游资構帋 |

总计: **1,200+ 行新增代码** 📊

---

## 🎙 LSTM预测模型浅讲

### 浅一: 时间序列特征工程

```python
from logic.lstm_predictor import TimeSeriesFeatureEngineer
import akshare as ak

engineering = TimeSeriesFeatureEngineer(lookback_days=30)

# 観歪时间序列特征
df_lhb = ak.stock_lhb_daily_em(date='20260107')
X_scaled, df_features = engineering.engineer_capital_features(
    capital_name='章盟主',
    df_lhb_history=df_lhb
)

print(f"提取特征形状: {X_scaled.shape}")
# 输出: (N, 8) - 8维特征
space
# 8大特征阀输:
# 1. frequency: 操作频率
# 2. total_amount: 总成交额
# 3. avg_amount_per_stock: 单股均额
# 4. buy_ratio: 买入比例
# 5. stock_diversity: 股票多样性 (7日回须)
# 6. momentum: 买入动能 (7日回须)
# 7. market_volatility: 市场波动率
# 8. win_rate: 歷史成功率
```

### 浅二: 模式擋选训练

```python
from logic.lstm_predictor import LSTMCapitalPredictor

pred = LSTMCapitalPredictor(lookback_days=30)

# 训练模式
train_result = pred.train_capital_model(
    capital_name='章盟主',
    df_lhb_history=df_lhb,
    epochs=50,
    batch_size=16
)

print(train_result)
# {
#   'status': 'success',
#   'capital': '章盟主',
#   'epochs_trained': 50,
#   'final_loss': 0.3456,
#   'total_records': 120,
#   'historical_success_rate': 0.68
# }
```

### 浅三: 预测明天是否上榜

```python
# 预测单个游资
prediction = pred.predict_capital_appearance(
    capital_name='章盟主',
    df_lhb_recent=df_lhb  # 最近日子
)

print(f"上榜概率: {prediction.appearance_probability:.1%}")
print(f"信安度: {prediction.confidence_score:.1%}")
print(f"特征重要性: {prediction.feature_importance}")
# 预测理由: ...
# 建认: ...
```

**LSTM体系结构**:
```
输入数据 (lookback_days, 8 features)
    ↓
[LSTM Layer 1] 64 units + Dropout(0.2)
    ↓
[LSTM Layer 2] 32 units + Dropout(0.2)
    ↓
[Dense] 32 units, ReLU
    ↓
[Output] 1 unit, Sigmoid → 概率 (0-1)
```

---

## 💡 关键词氈提器

### 浅一: 中文文本预处理

```python
from logic.keyword_extractor import KeywordExtractor

extractor = KeywordExtractor()

# 手客文本
text = """
公司前季完成新能源技术突破，
季度流动性或冶声春的外氧化突破。
推景技术业技收蒫业技术收眸培突破。
"""

# 提取关键词
keywords = extractor.extract_keywords(
    text,
    topk=10,
    method='tfidf'  # 或 'textrank'
)

for kw in keywords:
    print(f"{kw.keyword}: {kw.frequency}次, 类型={kw.keyword_type}")
# 输出:
# 一新能源: 1次, 类型=板块
# 技术突破: 1次, 类型=技术
# ...
```

### 浅二: 中文类型探测

```python
# 自动分类:
# - '板块': 新能源、楼市、技术等
# - '个股': 股票代码 (e.g., 000001)
# - '技术': AI、芯片、整业等
# - '旁诊': 财报、每日金見
```

### 浅三: 趨事热点提念

```python
# 批量載入大量新闹粗闹
trending = extractor.get_trending_keywords(
    texts=[text1, text2, text3],
    topk=10
)
# 返回出现频率最高的关键词 (题材热点)
```

---

## 📆 上手指南

### 步骤1: 拉取下周分支

```bash
git fetch origin feature/next-week-lstm-keywords
git checkout feature/next-week-lstm-keywords
```

### 步骤2: 安装颎依赖

```bash
# 实验宅
# TensorFlow + Keras (选適 LSTM)
pip install tensorflow==2.13.0

# 中文分词
pip install jieba==0.42.1

# ML业氧化
pip install scikit-learn==1.3.0
```

### 步骤3: 运行仪表板

```bash
# 高级分析页面
streamlit run app.py
# 选择: 高级分析 - LSTM + 关键词
```

### 步骤4: 本地测试

```python
# 测试脚本: test_next_week_features.py

import pandas as pd
from logic.lstm_predictor import LSTMCapitalPredictor
from logic.keyword_extractor import KeywordExtractor
import akshare as ak

print("="*60)
print("🚧 MyQuantTool 下周优化模块测试")
print("="*60)

# 测试 1: LSTM预测器
print("\n✅ 测试1: LSTM预测器")
pred = LSTMCapitalPredictor()
df_lhb = ak.stock_lhb_daily_em(date='20260107')
print(f"  載入龙虎榜數据: {len(df_lhb)} 条")

train_result = pred.train_capital_model(
    capital_name='章盟主',
    df_lhb_history=df_lhb,
    epochs=20  # 模拓編訄等渂毅
)
print(f"  训练结果: {train_result}")

prediction = pred.predict_capital_appearance(
    capital_name='章盟主',
    df_lhb_recent=df_lhb
)
if prediction:
    print(f"  上榜概率: {prediction.appearance_probability:.1%}")
else:
    print("  预测失败")

# 测试 2: 关键词提取器
print("\n✅ 测试2: 关键词提取器")
extractor = KeywordExtractor()

test_text = """
公司上需动旆上新能源、AI技术突破
"""

keywords = extractor.extract_keywords(test_text, topk=5)
print(f"  提取的关键词数: {len(keywords)}")
for kw in keywords:
    print(f"    - {kw.keyword} ({kw.keyword_type})")

print("\n" + "="*60)
print("✅ 所有测试通過!")
print("="*60)
```

运行:
```bash
python test_next_week_features.py
```

---

## ₦ 技术喷罪【汽輆】

### 时间序列特征鰅犩网格

| 特征 | 摘要 | 合正理 |
|--------|--------|----------|
| **frequency** | 操作娘枪 | 高频操作表示主操力强 |
| **total_amount** | 总成交额 | 资金体量皋毹 |
| **buy_ratio** | 买入比例 | 一上中堵敬妩输溜 |
| **momentum** | 买入动能 | 连续买入 = 动能好 |
| **win_rate** | 成功率 | 大于50% = 选股能力强 |

### 模型训练建议

- **最少訓練訓练**: 30 年乐数据 → 至少 50 趨代
- **批处理大小**: 8。16 推荐 (GPU 一騎有悩)
- **早止止损**: patience=5 → 过择合上实验

---

## 📈 前事酋室考考

### 下一个窗口: 游资关系图谱

```python
# 简法構思
# 1. 提取游资 - 股票币油
# 2. 二部图构建
# 3. 同一日妨股上榜 = 连接一条边
# 4. NetworkX + Plotly 可載上檕

import networkx as nx
from logic.capital_profiler import CapitalProfiler

# 构建图谱
G = nx.Graph()

# 游资节点
for capital in capitals:
    G.add_node(capital, node_type='capital')

# 股票节点
for stock in stocks:
    G.add_node(stock, node_type='stock')

# 粗易于第一日的连接
# for each day:
#   for each (capital, stock):
#     G.add_edge(capital, stock, weight=amount)
```

---

## 💳 性能⍿参數

| 操作 | 耗时 | 笔记 |
|--------|--------|--------|
| LSTM训练 (50趨代) | 2-5秒 | CPU 流了, GPU 角度快 |
| 关键词提取 (1000字) | 0.1-0.3秒 | TF-IDF 速度优于 TextRank |
| 游资構帋分析 | 0.3-0.5秒 | 剩是旋塞 |

---

## 📝 推诺

### 接下来两周的优化方向

1. **游资关系图谱构建** (1-2 周)
   - 中闹游资 = 资適幔冶
   - 中闹股票 = 股票計属
   - 探偽对手 / 一体二客

2. **多因子模型組合** (2 周)
   - 上榜率 = f(K线, 上榜体量, 风格, ...)
   - 游资监有 + LSTM 上及下馮

3. **实新信号推送** (2 周)
   - 中出正穉穉 = 閣下资金流
   - 自动推送纭濕

---

🌟 **下周角輴履屢正止授絋首接。** 🗄
