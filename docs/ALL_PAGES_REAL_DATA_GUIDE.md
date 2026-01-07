# 全页面真实数据改造指南 (Deep + Network + Kline + V4 Hub)

**改造日期**: 2026-01-08  
**分支**: `feature/all-pages-real-data-integration`  
**改造范围**:
- `pages/deep_analysis.py`
- `pages/network_fusion_analysis.py`
- `pages/kline_analysis_dashboard.py`
- `pages/v4_integrated_analysis.py`

---

## 1. 总体设计

### 统一原则
- 所有页面都 **预留真实数据接入点**，统一走 `logic` 下的数据/网络/多因子模块
- UI 尽量保持不变，先保证可用，再逐步替换为真正的生产数据
- 所有对外数据都加 `@st.cache_data` + TTL，避免频繁请求
- 所有外部依赖都包 `try/except`，失败自动降级为 Demo 数据

---

## 2. deep_analysis.py 改造要点

**文件**: `pages/deep_analysis.py`

### ✅ 新增内容

1. **导入 + DataManager 检测**

```python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from logic.data_manager import DataManager
    REAL_DATA_AVAILABLE = True
except ImportError:
    DataManager = None
    REAL_DATA_AVAILABLE = False
    logging.warning("❌ DataManager 不可用，深度分析使用 Demo 数据")
```

2. **统一数据访问函数**

- `get_basic_fundamental(code)` → 财务指标
- `get_valuation_pe_pb(code)` → PE/PB 对比
- `get_technical_series(code)` → 技术指标时间序列
- `get_capital_flow(code)` → 主力/散户资金流 + 持仓结构

全部带 `@st.cache_data(ttl=300)`，内部留 `TODO` 用于后续对接 `DataManager` 实际接口。

3. **UI 接入真实数据**

- Tab1 使用 `get_basic_fundamental()` 和 `get_valuation_pe_pb()` 的返回值
- Tab2 技术线图使用 `get_technical_series()` 的数据
- Tab3 资金流 & 持仓图使用 `get_capital_flow()` 的返回值

4. **页面底部版本标记**

```python
st.caption("🔬 深度研究系统 v3.7.0 Real Data Ready")
```

---

## 3. network_fusion_analysis.py 改造要点

**文件**: `pages/network_fusion_analysis.py`

### ✅ 新增内容

1. **导入网络 & 多因子模块**

```python
try:
    from logic.capital_network import CapitalNetworkAnalyzer
    from logic.multifactor_fusion import MultifactorFusionEngine
    REAL_DATA_AVAILABLE = True
except ImportError:
    CapitalNetworkAnalyzer = None
    MultifactorFusionEngine = None
    REAL_DATA_AVAILABLE = False
    logging.warning("❌ 网络/多因子模块不可用，使用 Demo 数据")
```

2. **数据访问层封装**

- `get_network_snapshot(network_type, threshold)`
- `get_centrality_stats()`
- `get_opponent_view(capital_name)`
- `get_fusion_result(lstm_w, kline_w, network_w)`

全部带缓存 TTL=600，并预留 `TODO` 处接真实实现。

3. **Tabs 接入封装后的函数**

- Tab1 用 `get_network_snapshot()` 提供节点/边/Cluster 表
- Tab2 用 `get_centrality_stats()` 输出中心度表 & 图
- Tab3 用 `get_opponent_view()` 输出对手表和图
- Tab4 用 `get_fusion_result()` 输出三因子融合结果表

4. **页面底部版本标记**

```python
st.caption("🕸️ 网络融合分析系统 v3.7.0 Real Data Ready")
```

---

## 4. kline_analysis_dashboard.py 改造要点

**文件**: `pages/kline_analysis_dashboard.py`

### ✅ 新增内容

1. **DataManager 检测 + 数据源切换**

- 支持两个模式:
  - `Demo 模拟数据`
  - `DataManager 实时数据`
- 侧边栏顶部展示: `✅ 已连接 DataManager` 或 `⚠️ 当前使用 Demo 模拟数据`

2. **行情函数重构**

- `get_quote_data(codes, source)`
  - 如果 `DataManager` 可用，则预留 `dm.get_realtime_quote(code)` 的挂接点
  - 否则走 Demo 基础表
- `get_kline_data(main_code, frame)`
  - 预留 `dm.get_kline` 的调用
  - Demo 模式下用随机游走生成 K 线 + MA5/20/60

3. **UI 改造**

- Tab1 所有行情表和 K 线都改为通过上述函数获取
- 形态识别 & 信号监控仍用示例数据，等后续接逻辑

4. **页面底部版本标记**

```python
st.caption("📈 K线分析系统 v3.8.0 Real Data Ready | 支持真实数据 + Demo模拟")
```

---

## 5. v4_integrated_analysis.py 总控台

**文件**: `pages/v4_integrated_analysis.py`

### 作用
- 作为 **总控台/HUB 页面**，帮你从一个入口跳转到所有子分析页面
- 未来可以在这里集中显示多因子综合结果 & 策略总览

### 结构

1. 顶部市场概览 (目前仍为示例指标)
2. 中间 **快速导航区**:
   - deep_analysis
   - kline_analysis_dashboard
   - network_fusion_analysis
   - advanced_analysis
   每个给出一句简介 + 一行 `streamlit run ...` 命令
3. 底部示例的核心因子评分条形图

---

## 6. 本地测试步骤

```bash
# 1. 拉取分支
git fetch origin
git checkout feature/all-pages-real-data-integration

# 2. 分别测试页面
streamlit run pages/deep_analysis.py
streamlit run pages/network_fusion_analysis.py
streamlit run pages/kline_analysis_dashboard.py
streamlit run pages/v4_integrated_analysis.py
```

检查要点:
- 所有页面能正常运行
- 没有 ImportError
- 侧边栏能正确显示 `Real Data Ready` 状态
- 没有明显性能问题 (页面切换流畅)

---

## 7. Git 提交流程 (如需你本地再微调)

```bash
# 查看差异
git status
git diff pages/deep_analysis.py

# 根据需要修改后提交
git add pages/deep_analysis.py pages/network_fusion_analysis.py \
        pages/kline_analysis_dashboard.py pages/v4_integrated_analysis.py docs/ALL_PAGES_REAL_DATA_GUIDE.md

git commit -m "chore: polish real-data ready pages and docs"

git push origin feature/all-pages-real-data-integration
```

---

## 8. 合并前检查清单

- [ ] deep_analysis 用统一数据访问函数替代散落 Demo 数据
- [ ] network_fusion_analysis 用统一的 CapitalNetwork/Multifactor 封装
- [ ] kline_analysis_dashboard 真正准备好接 DataManager 实盘行情
- [ ] v4_integrated_analysis 总控台可正常展示 & 导航
- [ ] 所有页面加入 `Real Data Ready` 版本标记

---

**到这里，这四个页面都已经完成“真实数据接入准备 + 统一数据访问层”的改造。**

下一步就是按需逐个补齐逻辑层接口 (DataManager / CapitalNetworkAnalyzer / MultifactorFusionEngine) 即可真正“实盘/准实盘”运行。