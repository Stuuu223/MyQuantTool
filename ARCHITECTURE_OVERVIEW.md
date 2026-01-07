# 🎯 MyQuantTool 技术架构概览

**版本**: 3.3.0
**更新日期**: 2026-01-07
**概述**: 完整的A股量化分析平台架构

---

## 🎯 整体架构览

```
┌─────────────────────────────────────┐
│           MyQuantTool 量化交易平台                    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│                 🌝 Streamlit 前端                    │
│  [主页] [深度分析] [K线MD] [高级分析]        │
└─────────────────────────────────────┘
                                    ↑
                                    ↑ Streamlit API
                                    ↓
┌─────────────────────────────────────┐
│            🎁 业务逻辑层 (logic/)                  │
├─────────────────────────────────────┤
│  ░ 游资画像         ░ 游资预测        ░ 风险评估│
│  (CapitalProfiler) (OpportunityPredictor) (RiskMonitor) │
├─────────────────────────────────────┤
│  ░ K线数据          ░ 邮件告警        ░ 缓存管理│
│  (KlineAnalyzer) (EmailAlertService) (CacheManager)  │
├─────────────────────────────────────┤
│  🤖 LSTM预测           💡 关键词提取│
│  (LSTMCapitalPredictor) (KeywordExtractor)  │
└─────────────────────────────────────┘
                                    ↑
                                    ↑ Python import
                                    ↓
┌─────────────────────────────────────┐
│            📄 数据整紐层 (akshare)                   │
│  ak.stock_lhb_daily_em()  ━━ 龙虎榜日数据     │
│  ak.stock_zh_a_hist()     ━━ K线整年数据     │
│  ak.stock_zh_a_spot_em()  ━━ 实新行情数据     │
│  ak.stock_finance_analysis() ━━ 资金面时资简     │
└─────────────────────────────────────┘
```

---

## 📆 模块横拁表

### Phase 3.1: 游资画像 + 预测 + 风险

| 模块 | 类名 | 主要方法 | 输入 | 输出 |
|--------|--------|--------|--------|----------|
| **游资画像** | CapitalProfiler | 10维度评估 | df_lhb | Profile(score, grade, type) |
| **游资预测** | OpportunityPredictor | 上榜概率预测 | df_lhb | Prediction(prob, capital, stock) |
| **风险评估** | RiskMonitor | 风险指标计算 | df_current, df_history | Report(score, level, alerts) |

### Phase 3.2: K线 + 邮件 + 仪表板

| 模块 | 类名 | 主要方法 | 输入 | 输出 |
|--------|--------|--------|--------|----------|
| **K线分析** | KlineAnalyzer | 6大技术指标 | symbol, date_range | Metrics(MA, MACD, RSI, KDJ) |
| **邮件告警** | EmailAlertService | 4类告警模板 | capital, risk_score | Email(HTML body) |
| **Streamlit** | pages/kline_analysis_dashboard.py | 前端仪表板 | 用户互动 | 来收疏化上標 |

### Phase 3.3: LSTM + 关键词 (NEW)

| 模块 | 类名 | 主要方法 | 输入 | 输出 |
|--------|--------|--------|--------|----------|
| **LSTM预测** | LSTMCapitalPredictor | 8维时間序列 + 2层LSTM | df_lhb | Prediction(prob, confidence, features) |
| **特征工程** | TimeSeriesFeatureEngineer | 时間序列整理 | df_capital | X_scaled, df_features |
| **关键词提取** | KeywordExtractor | TF-IDF / TextRank | text | [KeywordInfo, ...] |
| **Streamlit** | pages/advanced_analysis.py | 高级仪表板 | 用户互动 | 仪表板 + 图表 |

---

## 🎁 业务逻辑层 详细体系

### 游资画像 (CapitalProfiler)

```
输入: 游资名称 + 龙虎榜整体数据
  ↓
1. 提取游资操作记录
2. 计算 10 个维度
   - 持续突注度
   - 资金实么串
   - 成功率
   - 行业浓度
   - 选时能力
   - ...
3. 综合评分 = weighted_sum(10维)
4. 判断游资级别 (5-star)
  ↓
输出: Profile {
  overall_score: 75,
  capital_grade: '超级',
  capital_type: '陇贴上飯拜',
  risk_warnings: ['...'],
  ...
}
```

### LSTM预测器 (LSTMCapitalPredictor)

```
输入: 游资名称 + 最近 N 天的龙虎榜数据
  ↓
1. 时間序列特征工程
   - 8维特征: frequency, total_amount, ..., win_rate
2. MinMax 残役化
3. 滑窗鼠样庄加序 (lookback_days=30)
4. LSTM模式推戈
   Input: (N, 30, 8)
   ↓
   LSTM1: 64 units + Dropout
   ↓
   LSTM2: 32 units + Dropout
   ↓
   Dense: 32 units
   ↓
   Output: Sigmoid → [0, 1]
  ↓
输出: LSTMPrediction {
  appearance_probability: 0.68,
  confidence_score: 0.65,
  feature_importance: {'frequency': 0.4, ...},
  predicted_reason: '...',
  recommended_action: '...'
}
```

### 关键词提取器 (KeywordExtractor)

```
输入: 中文文本
  ↓
1. 文本清理
   - 移除特殊符号
   - 移除HTML标签
2. jieba中文分词 + 自定义词典
3. 停用词過濾
4. TF-IDF或TextRank特征
5. 板块分类
6. 相关性计算
  ↓
输出: [KeywordInfo, ...] {
  keyword: '上能源',
  frequency: 3,
  tfidf_score: 0.456,
  keyword_type: '板块',
  relevance_score: 0.8
}
```

---

## 📊 数据流位置流

```
Streamlit 前端
  ↑
  ↓ st.write(), st.metric(), st.dataframe()
  ↑
Python 业务逻辑层 (logic/)
  ↑
  ↓ akshare API
  ↑
A股数据中心
  ↓
龙虎榜日数据
  ↓ K线整年数据
  ↓ 实新行情数据
  ↓
业务逻辑应处理
  ↑
  ↓ 计算特征 、训练模式、预测
  ↑
Streamlit 认権阶阶
```

---

## 📇 邮件喊到罗根齿预算流

### 告警优先级

```
高预优先级 (High)
  ↑
  ┓━ 高风险 (risk_score > 65)
  ┓━ 高机会 (activity_score > 75)
  ┓━ 打板突破 (价格突破关键位)
中优先级 (Medium)
  ↑
  ┓━ 游资変化 (风格变化)
  ┓━ 资金开始 (>了股上 次数)
低优先级 (Low)
  ↑
  ┓━ 日线总结
  ┓━ 敷情分享
```

### 邮件时间採绊

```
早旧 (09:30)
  ↑
  ┓━ 开盘流动性检查
中午 (12:00)
  ↑
  ┓━ 流动性预警问候
下午 (15:30)
  ↑
  ┓━ 收盘后统计统计统计
  ┓━ 龙虎榜整经分析
晨 (20:00)
  ↑
  ┓━ 明天上榜预测
  ┓━ 商业角膣理由
```

---

## 💳 次下阶段 (2 道)

### 阶段 1: 游资关系图谱 (1 道)

```python
# NetworkX 二部图
G = nx.Graph()
# 游资节点 <--> 股票节点
# 改 游资节点 <--> 游资节点 (对手关系)
# Plotly 可載化上标
```

### 阶段 2: 多因子模式 (1 道)

```python
# 预测 = w1 * LSTM + w2 * KlineMetrics + w3 * SectorMomentum
# 取龍资筆游资至住地衰術遫
```

---

## 💳 需求依赖对比

| 依赖 | 类戸 | 依赖模型 | 版本 |
|--------|--------|--------|--------|
| pandas | 数据处理 | 日其 | >=1.3.0 |
| numpy | 数值计算 | 核一 | >=1.21.0 |
| akshare | 数据据深 | 湈已雮 | >=1.12.0 |
| streamlit | 前端 | 缓機 | >=1.28.0 |
| plotly | 可載图表 | 可載 | >=5.10.0 |
| tensorflow | LSTM | 深度学习 | >=2.13.0 |
| scikit-learn | 機器学習 | ML | >=1.3.0 |
| jieba | 中文分词 | NLP | >=0.42.1 |

---

## 🌟 超鸽伐惠断面

**下一阶段资金流推樼计划：**

```
下鑨阷时间序列特征工程
  ↓
下鑨等与下婌粗諶等对我主需求特子
  ↓
出上詫逸子突破遤歩地不満一个黑弫川上
  ↓
出上重万光趨下雨情文章级抉誮待
  ↓
出上石河子的封速稫地辛苦
  ↓
出上盒筁臣實款洲风诎詫筐其多射殫温浸素異化
  ↓
版本发布！
```

---

👋 **上手指南: 见 `NEXTWEEK_IMPLEMENTATION_GUIDE.md`** 📝
