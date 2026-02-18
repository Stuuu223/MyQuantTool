# CASE: Tick 链路封装与 Provider 计划
# ID: CASE_2026_02_TICK_PROVIDER

## 0. 背景 & 目标

- **为什么开始这条探索**：Tick数据获取链路散落在5+个脚本中，重复踩坑，效率低下
- **想回答的关键问题**：
  1. 如何设计统一的TickProvider接口？
  2. 如何迁移现有脚本到TickProvider？
  3. 迁移优先级是什么？

---

## 1. 当天进展 (2026-02-18)

### 1.1 做了什么
- 输出TickProvider规范文档（`.iflow/tick_provider_spec.md`）
- 识别当前直接使用xtdata/xtdatacenter的脚本
- 制定迁移优先级

### 1.2 关键发现
- **当前状态**：5+个脚本直接使用xtdata/xtdatacenter
- **重复问题**：每个脚本都要手动初始化xtdatacenter、设置Token、管理端口
- **架构违规**：违反铁律2.1（Tick数据必须通过唯一Provider）

**TickProvider最低要求**：
- 负责xtdatacenter初始化、Token、数据目录、listen端口
- 提供`ensure_history(code, start, end)`接口
- 提供`load_ticks(code, start, end)`接口
- 返回tick可用日期范围（区分录制vs回灌）

### 1.3 决策/动作
- **立即执行**：禁止新增脚本直接import xtdata/xtdatacenter
- **迁移优先级**：
  1. 顽主相关：`scripts/download_wanzhu_tick_data.py` + 回测使用的Tick入口
  2. 网宿/顽主实验中用到的tick回放脚本
- **长期计划**：逐步迁移所有tick相关脚本

---

## 2. 未解决问题

- **必填**：
  - TickProvider的具体实现细节
  - 如何处理tick缺失的情况
  - 迁移完成时间表

---

## 3. 回顾链接

- **相关代码文件**：
  - `.iflow/tick_provider_spec.md` - TickProvider规范文档
  - `scripts/download_wangsu_tick.py` - 网宿tick下载脚本（需要迁移）
  - `scripts/download_wanzhu_tick_data.py` - 顽主tick下载脚本（需要迁移）
  - `backtest/run_tick_backtest.py` - 基础tick回测（需要迁移）

- **相关文档**：
  - `docs/dev/CTO_DECISION_2026-02-18.md` - CTO决策（第2章Tick数据链路）
  - `docs/MyQuantTool-Architecture-Iron-Laws.md` - 架构铁律（第2章数据与Tick链路）

---

**Owner**: AI项目总监  
**Status**: OPEN