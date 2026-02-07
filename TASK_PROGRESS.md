# 任务进度记录

**更新时间**: 2026-02-07
**当前状态**: 进行中

---

## ✅ 已完成的工作

### 1. 环境准备
- ✅ 配置 tushare token: `1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b`
- ✅ 创建 V2.0 数据结构: `data/equity_info_tushare.json` (按 trade_date 索引)
- ✅ 创建测试数据: 603607.SH 在 2026-02-06 的 circ_mv = 4546822896.0 元 (45.47 亿)
- ✅ 创建开发校准记录: `data/dev_checks.md`

### 2. 数据迁移
- ✅ 创建迁移脚本: `tasks/migrate_add_trade_date.py`
- ✅ 运行迁移脚本，给 7/9 个历史快照补充 `trade_date` 字段
- ✅ 验证 `trade_date` 字段已成功添加到所有 opportunities
- ✅ 推送代码到 GitHub (commit f286dec)

### 3. 文档创建
- ✅ 创建 `TODO.md`: 记录 circ_mv 缺失问题和实现计划
- ✅ 创建 `data/dev_checks.md`: 开发校准记录
- ✅ 创建 `data/review/2026-02-07_诱惑记录.md`: 诱惑记录模板

---

## 📋 待完成的工作

### 优先级1: 修改 `logic/full_market_scanner.py`

#### 1.1 添加 `extract_trade_date()` 函数
**位置**: 文件顶部，导入语句之后
**插入内容**:
```python
def extract_trade_date(scan_time: str) -> str | None:
    """
    从 scan_time 提取交易日期（YYYYMMDD）
    
    Args:
        scan_time: 时间戳字符串，格式如 '2026-02-06T09:45:21.390438'
    
    Returns:
        交易日期字符串，格式如 '20260206'，如果失败返回 None
    """
    if not scan_time:
        return None
    
    # 优先走严格解析
    try:
        dt = datetime.fromisoformat(scan_time)
        return dt.strftime("%Y%m%d")
    except ValueError:
        # 兜底：处理其他格式
        try:
            date_part = scan_time.split("T")[0].split(" ")[0]
            return date_part.replace("-", "")
        except Exception:
            return None
```

#### 1.2 在生成机会 item 时添加 `trade_date` 字段
**位置**: 搜索 `scan_time = datetime.now().isoformat()` 这行代码
**插入内容**:
```python
scan_time = datetime.now().isoformat()
trade_date = datetime.now().strftime("%Y%m%d")  # 新增这行

# 在 result 字典中添加
result = {
    "code": code,
    "scan_time": scan_time,
    "trade_date": trade_date,  # 新增这行
    # ... 其他字段
}
```

---

### 优先级2: 修改 `tasks/run_event_driven_monitor.py`

#### 2.1 修改 circ_mv 查询逻辑
**位置**: 搜索 `trade_date = datetime.now().strftime("%Y%m%d")` 这行代码
**修改内容**:
```python
# 原代码（错误）
# trade_date = datetime.now().strftime("%Y%m%d")

# 修改为（正确）
trade_date = item.get("trade_date")  # 从 item 读取
if trade_date:
    circ_mv_tushare = get_circ_mv(code, trade_date)
else:
    circ_mv_tushare = 0

# 计算 ratio
if circ_mv_tushare > 0:
    ratio = main_net_yuan / circ_mv_tushare * 100
    float_mv_yi = circ_mv_tushare / 1e8
elif circulating_market_cap > 0:
    ratio = main_net_yuan / circulating_market_cap * 100
else:
    ratio = None
```

#### 2.2 添加 ratio < 0.5% 的 PASS 规则
**位置**: 搜索 `_calculate_decision_tag` 函数
**修改内容**: 在函数开头添加第一关
```python
def _calculate_decision_tag(self, ratio: float | None, 
                           risk_score: float,
                           trap_signals: list[str]) -> str:
    """
    资金推动力决策树:
    第1关: ratio < 0.5% → PASS (止损优先)
    第2关: ratio > 5% → TRAP (暴拉出货)
    第3关: 诱多 + 高风险 → BLOCK
    第4关: 1-3% + 低风险 + 无诱多 → FOCUS
    """
    
    # 第1关: 资金推动力太弱，直接 PASS
    if ratio is not None and ratio < 0.5:
        return "PASS❌"
    
    # 第2关: 暴拉出货风险
    if ratio is not None and ratio > 5:
        return "TRAP❌"
    
    # 第3关: 诱多 + 高风险
    if trap_signals and risk_score >= 0.4:
        return "BLOCK❌"
    
    # 第4关: 标准 FOCUS
    if (ratio is not None and 
        1 <= ratio <= 3 and
        risk_score <= 0.2 and
        not trap_signals):
        return "FOCUS✅"
    
    # 兜底
    return "BLOCK❌"
```

---

### 优先级3: 回放验证

#### 3.1 回放 2026-02-06 的数据
```bash
python tasks/run_event_driven_monitor.py --replay --date 2026-02-06 --timepoint 094521
```

#### 3.2 验证关键数据
- ✅ 603607.SH 的 circ_mv 是否等于 45.47 亿
- ✅ 601869.SH 的 ratio 是否等于 0.0047%
- ✅ 决策标签是否符合预期
  - 603607.SH (ratio ≈ 1.71%): FOCUS✅
  - 601869.SH (ratio ≈ 0.0047%): PASS❌

---

### 优先级4: 写真实诱惑记录

#### 4.1 基于 601869.SH 的真实数据
**文件**: `data/review/2026-02-06_诱惑记录.md`
**内容**: 使用增强版模板，包含止损价位

**模板**:
```markdown
## 2026-02-06 诱惑记录

### 601869.SH（长飞光纤 - 高位老龙）

**时间**: 17:54（收盘）
**系统ratio**: 0.0047% (PASS❌)

**核心判断（系统 - 最高优先级）**:
- ratio = 331万 / 710亿 × 100 = **0.0047%**
- **ratio < 0.5% → 第一关直接 PASS❌**
- **"ratio 极低"说明没真资金推，这是最高优先级的判断标准**

**我的想法（直觉 - 辅助判断）**:
- 历史上涨 7-8 倍，高估值阶段
- 现在才开始被机构密集吹，多半是出货而不是建仓
- 即使周一再拉，更多是最后一轮表演，不是低位启动

**核心矛盾**:
- 盘面看起来很热闹（换手率 5.22%，成交额 37 亿）
- 但 ratio 只有 0.0047%，资金推动力极弱
- **这是典型的高位讲故事接盘阶段**

**如果当时真上了**:
- 买入价位: 174.77 元
- 止损价位: 164.30 元 (-6%)
- 预期最大亏损: 6%

**系统判断**:
- ratio < 0.5% → PASS❌
- 无论短线如何表演，一律不参与

**学到的教训**:
- **"ratio 极低"是最高优先级的判断标准**
- 历史涨幅和机构吹票是辅助判断
- **只要 ratio < 0.5%，无论其他因素如何，一律不参与**
```

---

## 🎯 核心设计理念

### 资金推动力决策树
1. **第1关**: ratio < 0.5% → PASS❌（止损优先）
2. **第2关**: ratio > 5% → TRAP❌（暴拉出货）
3. **第3关**: 诱多 + 高风险 → BLOCK❌
4. **第4关**: 1-3% + 低风险 + 无诱多 → FOCUS✅

### 数据结构
- **equity_info_tushare.json**: `{trade_date: {ts_code: {float_mv, total_mv, ...}}}`
- **快照**: 每个机会包含 `trade_date` 字段（YYYYMMDD 格式）

### ratio 计算
- **公式**: ratio = main_net_inflow（元） / circ_mv（元） × 100
- **单位**: circ_mv 以元为单位（从 tushare 的万元 × 10000 转换）
- **查询**: 从 `get_circ_mv(ts_code, trade_date)` 获取

---

## 📊 关键测试数据

### 603607.SH（京华激光）
- **日期**: 2026-02-06
- **circ_mv**: 45.47 亿（4546822896.0 元）
- **主力净流入**: 7768.56 万（77685610.0 元）
- **预期 ratio**: 77685610.0 / 4546822896.0 × 100 = 1.71%
- **预期标签**: FOCUS✅

### 601869.SH（长飞光纤）
- **日期**: 2026-02-06
- **流通市值**: 约 710.16 亿
- **主力净流入**: 约 331 万
- **预期 ratio**: 331万 / 710.16亿 × 100 ≈ 0.0047%
- **预期标签**: PASS❌

---

## 🔧 技术要点

### trade_date 提取
- **回放模式**: 从快照的 `scan_time` 字段提取
- **实盘模式**: 使用当前日期
- **工具函数**: `extract_trade_date(scan_time)`

### 回放验证
- **命令**: `python tasks/run_event_driven_monitor.py --replay --date 2026-02-06 --timepoint 094521`
- **关键检查**: circ_mv 是否正确（不为 0）、ratio 是否计算正确、决策标签是否合理

---

## 📝 行为训练

### 每日诱惑记录
- **频率**: 每天写 1 条
- **重点**: 记录"最想买但被系统 PASS 掉"的票
- **内容**: 
  - 系统ratio和决策标签
  - 我的想法（直觉）
  - 买入价位、止损价位、预期最大亏损
  - 事后验证

### 训练目标
- 强化"止损优先"心态
- 建立对系统规则的信心
- 验证"ratio < 0.5%"规则的价值

---

## 🚀 下一步行动

1. 修改 `logic/full_market_scanner.py`
   - 添加 `extract_trade_date()` 函数
   - 在生成机会 item 时添加 `trade_date` 字段

2. 修改 `tasks/run_event_driven_monitor.py`
   - 修改 circ_mv 查询逻辑
   - 添加 ratio < 0.5% 的 PASS 规则

3. 回放验证
   - 回放 2026-02-06 的数据
   - 验证 circ_mv、ratio、决策标签

4. 写真实诱惑记录
   - 基于 601869.SH 的真实数据
   - 使用增强版模板

---

## 💡 重要提醒

### tushare token
- **token**: `1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b`
- **设置方式**: 环境变量 `TUSHARE_TOKEN`

### 文件位置
- **迁移脚本**: `tasks/migrate_add_trade_date.py`
- **数据文件**: `data/equity_info_tushare.json`
- **校准记录**: `data/dev_checks.md`
- **诱惑记录**: `data/review/2026-02-06_诱惑记录.md`

### Git 提交
- **最新 commit**: f286dec
- **状态**: 已推送到 GitHub

---

**更新完成时间**: 2026-02-07
**预计完成时间**: 本周末