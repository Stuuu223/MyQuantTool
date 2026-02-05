# 完美三漏斗全市场扫描系统使用指南

## 系统简介

**完美三漏斗全市场扫描系统（Perfect Triple Funnel Market Scanner）**是一套自动化的A股市场机会发现系统，通过三层逐级筛选，从全市场5000+只股票中精准识别真正的交易机会。

### 核心优势

1. **全自动化** - 无需人工介入，一键扫描全市场
2. **三层漏斗** - 技术面 → 资金流 → 陷阱检测，层层把关
3. **精准分类** - 机会池/观察池/黑名单，清晰标注
4. **充分复用** - 集成TrapDetector、CapitalClassifier等成熟模块
5. **高效执行** - QMT分批+限速，2-3分钟完成全市场扫描

---

## 架构设计

### 数据流全景

```
┌─────────────────────────────────────────────────┐
│   QMT 全市场股票池（5187 只）                      │
└──────────────┬──────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────┐
│  分批获取（6 批 × 1000 只，耗时 0.5 秒）            │
│  - 获取字段：lastPrice, volume, amount, pct_chg  │
└──────────────┬───────────────────────────────────┘
               ↓
╔══════════════════════════════════════════════════╗
║  Level 1: 技术面粗筛（本地计算，无 API 调用）        ║
╠══════════════════════════════════════════════════╣
║  条件：                                           ║
║  1. |涨跌幅| > 3%（异动票）                        ║
║  2. 成交额 > 3000 万（流动性要求）                  ║
║  3. 换手率 > 2%（活跃度）                          ║
║  4. 剔除：ST、退市、科创板（风控）                   ║
╚══════════════┬═══════════════════════════════════╝
               ↓
        300-500 只候选（压缩到 6-10%）
               ↓
╔══════════════════════════════════════════════════╗
║  Level 2: 资金流向深度分析（AkShare，限速18/分钟）  ║
╠══════════════════════════════════════════════════╣
║  每只股票单独请求：                                 ║
║  1. 主力净流入 > 0（必须有机构买入）                ║
║  2. 超大单占比 > 30%（非散户行情）                  ║
║  3. 近 3 日资金流向趋势（连续性判断）                ║
╚══════════════┬═══════════════════════════════════╝
               ↓
         50-100 只精选（再压缩到 1-2%）
               ↓
╔══════════════════════════════════════════════════╗
║  Level 3: 坑 vs 机会分类（TrapDetector + CapitalClassifier）║
╠══════════════════════════════════════════════════╣
║  调用现有组件：                                     ║
║  1. TrapDetector（诱多检测）                       ║
║     - 单日暴量 + 隔日反手                          ║
║     - 长期流出 + 单日巨量（游资突袭）                ║
║  2. CapitalClassifier（资金性质）                  ║
║     - 机构长线 / 游资短炒 / 散户接盘                ║
║  3. 风险评分（综合判断）                            ║
║     - >0.8: AVOID（远离）                         ║
║     - 0.6-0.8: WATCH（观察）                      ║
║     - <0.6: CONSIDER（可考虑）                    ║
╚══════════════┬═══════════════════════════════════╝
               ↓
┌──────────────────────────────────────────────────┐
│  最终输出：                                        │
│  - 机会池（10-20 只）：低风险 + 主力建仓            │
│  - 观察池（20-30 只）：有潜力但需验证               │
│  - 黑名单（20-30 只）：明显诱多陷阱                 │
└──────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 环境准备

确保已安装以下依赖：

```bash
pip install xtquant akshare pandas
```

### 2. 配置文件

编辑 `config/market_scan_config.json`，调整筛选阈值：

```json
{
  "level1": {
    "pct_chg_min": 3.0,       // 涨跌幅最小值（%）
    "amount_min": 30000000,   // 成交额最小值（元）
    "turnover_min": 2.0       // 换手率最小值（%）
  },
  "level2": {
    "main_inflow_min": 5000000,  // 主力流入最小值（元）
    "super_ratio_min": 0.3       // 超大单占比
  },
  "level3": {
    "risk_score_max": 0.6     // 风险评分上限
  }
}
```

### 3. 运行扫描

```bash
# 盘前扫描（9:00 前）
python tasks/run_full_market_scan.py --mode premarket

# 盘中扫描（交易时间）
python tasks/run_full_market_scan.py --mode intraday

# 盘后复盘（15:00 后）
python tasks/run_full_market_scan.py --mode postmarket
```

### 4. 查看结果

扫描结果保存在 `data/scan_results/` 目录下：

```
data/scan_results/
├── 2026-02-05_premarket.json   # 盘前结果
├── 2026-02-05_intraday.json    # 盘中结果
└── 2026-02-05_postmarket.json  # 盘后结果
```

---

## 输出结果详解

### JSON 结构

```json
{
  "scan_time": "2026-02-05T09:00:00",
  "mode": "premarket",
  "summary": {
    "opportunities": 18,
    "watchlist": 29,
    "blacklist": 20
  },
  "results": {
    "opportunities": [
      {
        "code": "600519.SH",
        "code_6digit": "600519",
        "risk_score": 0.23,
        "trap_signals": [],
        "capital_type": "机构长线",
        "flow_data": {
          "main_net_inflow": 12500000,
          "super_ratio": 0.45
        },
        "scan_time": "2026-02-05T09:15:23"
      }
    ],
    "watchlist": [...],
    "blacklist": [...]
  }
}
```

### 字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `code` | QMT格式股票代码 | `600519.SH` |
| `code_6digit` | 6位代码（AkShare格式） | `600519` |
| `risk_score` | 风险评分（0-1，越高越危险） | `0.23` |
| `trap_signals` | 诱多信号列表 | `["单日暴量+隔日反手"]` |
| `capital_type` | 资金性质 | `机构长线` / `游资短炒` / `散户接盘` |
| `flow_data.main_net_inflow` | 主力净流入（元） | `12500000` |
| `flow_data.super_ratio` | 超大单占比 | `0.45` |

---

## 使用场景

### 场景 1: 盘前快速选股（推荐）

**时间点：** 每天 8:30-9:00

**目的：** 在开盘前筛选出今日值得关注的股票

```bash
python tasks/run_full_market_scan.py --mode premarket
```

**预期输出：**
- 机会池：10-20 只（今日可重点关注）
- 观察池：20-30 只（盘中跟踪验证）
- 黑名单：20-30 只（今日避开）

**后续操作：**
1. 将机会池加入自选股
2. 开盘后用 `triple_funnel_scanner` 做实时监控
3. 符合买点即可入场

### 场景 2: 盘中动态更新

**时间点：** 10:30、13:30（盘中两次）

**目的：** 捕捉盘中新出现的异动股

```bash
python tasks/run_full_market_scan.py --mode intraday
```

**预期输出：**
- 机会池可能增加（盘中启动的股票）
- 黑名单可能增加（盘中诱多的股票）

### 场景 3: 盘后复盘总结

**时间点：** 15:30-16:00

**目的：** 复盘今日市场全貌，为明日做准备

```bash
python tasks/run_full_market_scan.py --mode postmarket
```

**预期输出：**
- 今日强势股汇总
- 今日诱多陷阱汇总
- 明日潜在机会预判

---

## 进阶用法

### 1. 自定义筛选条件

修改 `config/market_scan_config.json`：

```json
{
  "level1": {
    "pct_chg_min": 5.0,       // 提高到5%，只看强势股
    "amount_min": 50000000,   // 提高到5000万，只看大盘股
    "turnover_min": 3.0       // 提高到3%，只看活跃股
  }
}
```

### 2. 集成到自动化流程

```python
from logic.full_market_scanner import FullMarketScanner

# 在定时任务中调用
scanner = FullMarketScanner()
results = scanner.scan_market(mode='premarket')

# 自动发送机会池到邮件/微信
opportunities = results['opportunities']
for stock in opportunities:
    send_alert(stock['code'], stock['risk_score'])
```

### 3. 结合 Level 4 实时监控

```bash
# Step 1: 盘前生成机会池
python tasks/run_full_market_scan.py --mode premarket

# Step 2: 将机会池导入 triple_funnel_scanner 的观察池
python tasks/run_triple_funnel_scan.py --mode intraday
```

---

## 性能优化

### 当前性能指标

- **Level 1**: 5187 只 → 300-500 只，耗时 ~0.5 秒
- **Level 2**: 300-500 只 → 50-100 只，耗时 ~60 秒（受限于AkShare限速）
- **Level 3**: 50-100 只 → 最终分类，耗时 ~30 秒
- **总耗时**: 90-120 秒（1.5-2分钟）

### 优化建议

1. **Level 2 并行化** - 使用多线程+限速队列，缩短到 30 秒
2. **缓存资金数据** - 5 分钟内重复请求直接读缓存
3. **增量扫描** - 盘中模式只扫新增异动股

---

## 常见问题

### Q1: Level 1 为什么一只股票都没筛出来？

**可能原因：**
- 市场整体无异动（大盘平稳时正常）
- 筛选条件过严（降低 `pct_chg_min` 试试）
- QMT 数据源问题（检查 QMT 是否正常运行）

**解决方案：**
```json
{
  "level1": {
    "pct_chg_min": 2.0,  // 从3%降到2%
    "amount_min": 20000000  // 从3000万降到2000万
  }
}
```

### Q2: Level 2 耗时过长

**原因：** AkShare 限速 18 次/分钟

**解决方案：**
- 提高 Level 1 筛选标准，减少进入 Level 2 的股票数量
- 使用缓存机制（开发中）

### Q3: 风险评分都很低，没有黑名单

**原因：** 市场没有明显诱多行为

**这是好事！** 说明当前市场相对健康。

---

## 技术细节

### 风险评分算法

```python
def _calculate_risk_score(trap_result, capital_result):
    score = 0.0
    
    # 诱多信号权重
    if '单日暴量+隔日反手' in trap_signals:
        score += 0.4
    if '游资突袭' in trap_signals:
        score += 0.3
    if '长期流出+单日巨量' in trap_signals:
        score += 0.2
    
    # 资金性质权重
    if capital_type == '散户接盘':
        score += 0.3
    elif capital_type == '游资短炒':
        score += 0.2
    elif capital_type == '机构长线':
        score -= 0.1
    
    return min(max(score, 0.0), 1.0)
```

### 数据源优先级

| 数据类型 | 优先级 | 数据源 | 用途 |
|---------|--------|--------|------|
| 实时行情 | 1 | QMT | Level 1 粗筛 |
| 资金流向 | 2 | AkShare | Level 2 精筛 |
| 历史K线 | 3 | AkShare | Level 3 分析 |

---

## 更新日志

### v1.0.0 (2026-02-05)

- ✅ 初始版本发布
- ✅ 三层漏斗架构实现
- ✅ QMT + AkShare 数据源集成
- ✅ TrapDetector + CapitalClassifier 集成
- ✅ 三种运行模式（盘前/盘中/盘后）
- ✅ JSON 结果持久化

---

## 后续规划

- [ ] Level 2 并行化优化（多线程）
- [ ] 资金数据缓存机制
- [ ] 增量扫描模式（盘中模式）
- [ ] Web UI 可视化界面
- [ ] 微信/邮件告警集成
- [ ] 历史扫描结果回测分析

---

## 联系方式

如有问题或建议，请提交 Issue 到 GitHub 仓库。
