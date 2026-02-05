# 三漏斗扫描系统 - 完整实现

**版本**: V1.0
**日期**: 2026-02-05
**作者**: iFlow CLI

---

## 🎯 系统概述

三漏斗扫描系统是一个完整的股票筛选和监控系统，通过三级筛选漏斗和实时监控，帮助识别潜在的交易机会。

### 核心功能

- **漏斗1: 盘后筛选 (Level 1-3)**
  - Level 1: 基础过滤 (价格、成交量、换手率)
  - Level 2: 资金流向分析 (DDE、主力资金)
  - Level 3: 风险评估 (诱多检测、资金性质)

- **漏斗2: 盘中触发 (Level 4)**
  - VWAP 突破检测
  - 扫单爆量检测
  - 竞价爆量检测

- **信号管理**
  - 信号去重 (避免重复触发)
  - 信号通知 (UI、日志、邮件)
  - 信号统计

---

## 📁 文件结构

```
MyQuantTool/
├── logic/
│   ├── triple_funnel_scanner.py      # 核心扫描器
│   ├── signal_manager.py              # 信号管理器
│   ├── intraday_monitor.py            # 盘中监控 (已有)
│   └── ...
├── ui/
│   └── triple_funnel_tab.py           # UI界面
├── config/
│   ├── watchlist_pool.json            # 观察池配置
│   └── signal_config.json             # 信号配置
├── tasks/
│   └── run_triple_funnel_scan.py      # 运行脚本
├── tests/
│   └── test_triple_funnel.py          # 测试脚本
├── docs/
│   └── tech/
│       └── triple_funnel_scanner_guide.md  # 使用指南
├── main.py                             # 主程序 (已集成)
└── start_triple_funnel.bat             # 启动脚本
```

---

## 🚀 快速开始

### 方式1: UI界面 (推荐)

```bash
# Windows
start_triple_funnel.bat

# 或直接运行
python -m streamlit run ui/triple_funnel_tab.py
```

### 方式2: 命令行

```bash
# 盘后扫描
python tasks/run_triple_funnel_scan.py --mode post-market

# 盘中监控
python tasks/run_triple_funnel_scan.py --mode intraday

# 添加股票
python tasks/run_triple_funnel_scan.py --mode add --code 000001 --name 平安银行

# 查看信号
python tasks/run_triple_funnel_scan.py --mode signals
```

### 方式3: 集成到主程序

```bash
python main.py
```

然后在"🔥 交易策略"标签页中找到"🎯 三漏斗扫描"。

---

## 📊 使用流程

### 1. 准备观察池

添加你想要监控的股票到观察池（建议30-50只）。

**UI界面**:
- 打开三漏斗扫描UI
- 点击"➕ 添加股票"
- 输入股票代码、名称、原因

**命令行**:
```bash
python tasks/run_triple_funnel_scan.py --mode add --code 000001 --name 平安银行 --reason 测试用
```

### 2. 运行盘后扫描

在收盘后（建议15:30）运行盘后扫描，进行三级筛选。

**UI界面**:
- 切换到"盘后扫描"标签
- 点击"🚀 开始扫描"
- 查看筛选结果

**命令行**:
```bash
python tasks/run_triple_funnel_scan.py --mode post-market
```

### 3. 运行盘中监控

在交易时间运行盘中监控，实时检测信号。

**UI界面**:
- 切换到"盘中监控"标签
- 点击"🔄 开始监控"
- 保持页面打开，接收实时信号

**命令行**:
```bash
python tasks/run_triple_funnel_scan.py --mode intraday
```

### 4. 查看信号历史

查看最近的信号和统计数据。

**UI界面**:
- 切换到"信号历史"标签
- 筛选和查看信号详情

**命令行**:
```bash
python tasks/run_triple_funnel_scan.py --mode signals
```

---

## 🎛️ 配置说明

### 观察池配置 (`config/watchlist_pool.json`)

```json
{
  "stocks": [
    {
      "code": "000001",
      "name": "平安银行",
      "reason": "测试用",
      "level1_result": {...},
      "level2_result": {...},
      "level3_result": {...}
    }
  ]
}
```

### 信号配置 (`config/signal_config.json`)

```json
{
  "deduplication": {
    "time_window_minutes": 5,      // 时间窗口
    "price_threshold_pct": 0.5,    // 价格阈值
    "cooldown_period_minutes": {   // 冷却期
      "VWAP_BREAKOUT": 10,
      "VOLUME_SURGE": 5
    }
  },
  "notification": {
    "channels": ["UI_POPUP", "LOG"]
  }
}
```

---

## 🧪 测试

运行测试套件:

```bash
python tests/test_triple_funnel.py
```

测试内容包括:
- Level 1 过滤器
- Level 2 分析器
- Level 3 风险评估器
- 观察池管理器
- 信号去重器
- 信号管理器
- 三漏斗扫描器

---

## 📖 详细文档

完整的使用指南请查看: `docs/tech/triple_funnel_scanner_guide.md`

---

## 🔧 技术特点

### 1. 渐进式筛选

从全市场5000只→1000只→100只→30只，逐层过滤，确保质量。

### 2. 实时监控

基于QMT Tick数据或EasyQuotation实时数据，毫秒级响应。

### 3. 风险控制

多层风险评估，包括:
- 诱多陷阱检测
- 资金性质分类
- 综合风险评分

### 4. 信号去重

智能去重机制:
- 时间窗口去重
- 价格阈值去重
- 冷却期机制

### 5. 可配置化

所有参数都可通过配置文件调整，无需修改代码。

---

## 🎨 架构设计

```
┌─────────────────────────────────────────┐
│         三漏斗扫描系统                   │
├─────────────────────────────────────────┤
│                                         │
│  📊 漏斗1: 盘后筛选 (Level 1-3)         │
│  ├─ Level 1: 基础过滤                   │
│  ├─ Level 2: 资金流向分析               │
│  └─ Level 3: 风险评估                   │
│                                         │
│  ─────────────────────────────────────── │
│                                         │
│  🎯 观察池 (30-50只)                     │
│                                         │
│  ─────────────────────────────────────── │
│                                         │
│  ⚡ 漏斗2: 盘中触发 (Level 4)            │
│  ├─ VWAP突破检测                        │
│  ├─ 扫单爆量检测                        │
│  └─ 竞价爆量检测                        │
│                                         │
└─────────────────────────────────────────┘
```

---

## 📝 注意事项

1. **观察池数量**: 建议保持30-50只，过多会影响性能
2. **监控间隔**: 建议使用3-5秒，过短可能触发限制
3. **交易时间**: 只在交易时间运行盘中监控
4. **数据源**: 确保数据源稳定，建议使用QMT或EasyQuotation
5. **风险控制**: 信号仅供参考，建议人工确认后再执行

---

## 🐛 故障排查

### 问题1: 盘后扫描返回空结果

**解决方案**:
1. 检查观察池是否有股票
2. 检查网络连接
3. 查看日志获取详细信息

### 问题2: 盘中监控无信号

**解决方案**:
1. 确认当前是交易时间
2. 检查监控列表
3. 调整监控间隔

### 问题3: 信号重复触发

**解决方案**:
1. 调整 `config/signal_config.json` 中的去重参数
2. 增加 `time_window_minutes`

更多问题请查看: `docs/tech/triple_funnel_scanner_guide.md`

---

## 🎉 总结

三漏斗扫描系统是一个完整的量化工具，包括:

✅ 三级筛选漏斗 (Level 1-3)
✅ 盘中实时监控 (Level 4)
✅ 信号去重系统
✅ 信号通知系统
✅ 观察池管理
✅ UI界面
✅ 命令行工具
✅ 测试套件
✅ 完整文档

---

**祝您使用愉快！** 🚀

如有问题，请查看:
- 项目文档: `docs/`
- 日志文件: `logs/`
- 配置文件: `config/`