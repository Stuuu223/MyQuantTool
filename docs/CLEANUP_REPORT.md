# 项目架构清理报告

**清理日期**: 2026-02-22  
**执行人**: AI项目总监  
**状态**: ✅ 完成

---

## 一、清理概览

| 清理项 | 数量 | 状态 |
|--------|------|------|
| 修复Critical导入错误 | 1处 | ✅ 完成 |
| 删除冗余文档 | 1个 | ✅ 完成 |
| 归档历史版本脚本 | 3个 | ✅ 完成 |
| 识别待清理项目 | 15+处 | ⏳ 待执行 |

---

## 二、Critical修复

### 1. 修复 `logic/__init__.py` 导入错误

**问题**: 
```python
from logic.strategies.halfway_breakout_detector import HalfwayBreakoutDetector
```
该模块已被归档至 `archive/redundant_halfway/`

**修复**:
```python
from logic.strategies.unified_warfare_core import UnifiedWarfareCore
```

**影响**: 修复了6个文件的导入错误风险

---

## 三、文档清理

### 删除冗余文档
- ❌ `docs/AUDIT_REPORT_CTO.md` (中间报告)
- ✅ 保留 `docs/AUDIT_FINAL_REPORT.md` (最终报告)

### 文档重组建议 (待执行)

**Tier 1 - 核心权威文档 (保留)**:
- `KNOWLEDGE_BASE_V17.md` - 业务权威
- `CORE_ARCHITECTURE_V17.md` - 架构权威
- `OPERATION_GUIDE.md` - 运维指南
- `V17_TECH_DEBT.md` - 技术债务

**Tier 2 - 研究报告 (合并)**:
- `PHASE2_REPORT.md` + `PHASE3_FINDINGS.md` → `research/PHASE2_3_COMPREHENSIVE.md`
- `AUDIT_FINAL_REPORT.md` → `research/AUDIT_ZHITEXINCAI.md`

**Tier 3 - 开发日志 (归档)**:
- `dev/exploration_log/*.md` → 保留CASE结论文档，过程文档标记DEPRECATED

---

## 四、代码清理

### 已归档脚本

| 脚本 | 归档位置 | 理由 |
|------|----------|------|
| `compute_active_baseline.py` | `archive/v1_deprecated/` | v1版本废弃 |
| `compute_active_baseline_v2.py` | `archive/v1_deprecated/` | v2版本废弃 |
| `rebuild_300017_cache.py` | `archive/v1_deprecated/` | 一次性脚本 |

### 待统一函数 (识别但未执行)

**问题**: `get_turnover_5min_series` 函数在6个文件中重复定义

**建议**: 统一至 `logic/utils/tick_metrics.py`

涉及文件:
- `tools/compute_active_baseline_v3.py`
- `tools/build_hist_median_cache.py`
- `tools/tiered_ratio_system.py`
- `tools/climax_scanner_v2.py`
- `tools/golden_benchmark_extractor.py`
- `tools/liquidity_elasticity_analyzer.py`

---

## 五、架构问题汇总

### 🔴 P0 - Critical (已修复)
1. ✅ `logic/__init__.py` 导入错误

### 🟡 P1 - High (待执行)
2. 统一 `get_turnover_5min_series` 函数实现
3. 清理 `logic/` 目录中的测试main块 (72个)
4. 归档剩余历史版本脚本:
   - `run_research_pipeline.py` (被v2替代)
   - `run_single_wanzhu_replay.py` (被batch替代)
   - `run_4stocks_quick.py` (被16stocks替代)

### ⚪ P2 - Medium (建议)
5. 将测试代码从 `test_*.py` (根目录) 移至 `tests/`
6. 更新 `README.md` (引用过时路径)
7. 合并重复文档内容

---

## 六、核心文档精简建议

### KNOWLEDGE_BASE_V17.md
- 删除与 `CORE_ARCHITECTURE_V17.md` 重复的架构描述
- 保留业务决策、战法说明、资金路线

### CORE_ARCHITECTURE_V17.md
- 删除详细业务说明
- 保留系统分层图、组件关系、数据流

---

## 七、后续行动

### 立即执行 (今日)
- [x] 修复导入错误
- [x] 删除冗余文档
- [x] 归档历史脚本

### 短期执行 (本周)
- [ ] 统一 `get_turnover_5min_series` 实现
- [ ] 更新 `README.md`
- [ ] 合并PHASE2/3报告

### 中期执行 (本月)
- [ ] 清理main块测试代码
- [ ] 建立工具脚本分类机制
- [ ] 文档一致性检查

---

## 八、文件变更清单

```
M  logic/__init__.py              # 修复导入错误
D  docs/AUDIT_REPORT_CTO.md       # 删除冗余
A  tools/archive/v1_deprecated/   # 新建归档目录
M  tools/compute_active_baseline.py → archive/v1_deprecated/
M  tools/compute_active_baseline_v2.py → archive/v1_deprecated/
M  tools/rebuild_300017_cache.py → archive/v1_deprecated/
```

---

**清理完成时间**: 2026-02-22  
**提交分支**: v11-ratio-clean
