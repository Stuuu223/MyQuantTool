# MyQuantTool - 右侧极端换手起爆时间机器 (V20 全息版)

**核心定位**: A股右侧极端换手起爆点 + 资金物理学（向上推力与纯度）  
**数据源**: 100% 纯血 QMT 本地数据 (0 网络请求，毫秒级响应)  
**最新架构**: V20 纯血游资雷达 (已彻底剿灭所有散户指标与绝对金额)

---

## 🚀 极简执行手册 (SSOT 统一入口)

系统已完成大一统重构，彻底废除杂乱的策略参数，所有指令极简化。

### 1. 启动实盘火控雷达 (盘中)
```bash
python main.py live --mode real
```
* **智能感知**: 如果当前是非交易日或盘后，系统将拒绝启动雷达，并自动为您转入【热复盘模式】。

### 2. 启动昨日热复盘 (盘后)
```bash
python main.py live --mode real --dry-run
```
* 自动锚定最近一个已收盘的交易日，生成带有 `MFE`、`自身爆发` 等高阶指标的 V20 工业级大屏。

### 3. 启动全息时间机器 (历史回演)
```bash
python main.py backtest --date YYYYMMDD
```
* **强制纯净**: 已废弃 `--strategy` 等历史残党。系统将自动调用 `TimeMachineEngine`，严格过滤无数据空壳，绞杀尖刺骗炮杂毛，还原真实历史。

### 4. 启动极限数据吸血鬼 (强制下载)
```bash
python tools/unified_downloader.py --type tick --start-date YYYYMMDD --end-date YYYYMMDD
```
* 缺数据？直接开启吸血鬼模式，将 QMT 上的极速 Tick 一笔笔拽进本地硬盘。

---

## 🧠 V20 核心物理法则 (CTO 钦定)

1. **真实做功效率 (MFE)**: 废除绝对振幅，只认"向上推力"。`MFE = ((收盘-最低) + (最高-开盘))/2 / 流入比`。MFE 过低说明是资金黑洞，>5.0 扣分防一字板。
2. **绝对无量纲化**: 废除"净流入 5 亿满分"的规模歧视，全面采用 `Inflow Ratio` (流入比) 和 `Ratio Stock` (自身爆发倍数)。
3. **尖刺骗炮断头台**: 前 5 分钟放量，后 10 分钟泄洪 (`sustain_ratio < 1.0`)，得分直接乘以 0.1 物理抹杀！南兴股份等跟风杂毛见光死。
4. **全天候时空锁**: 基于 `xtdata.get_trading_dates('SH')` 的 0 延迟原生交易日历。彻底告别 `timedelta` 减一天的周末黑洞。
5. **safe_float护城河**: 从 QMT 读出的任何数据，运算前必须经过 `safe_float()` 强转，彻底消灭 `'>' not supported between str and int`！
6. **数据造假零容忍**: 当 `avg_volume_5d` 获取失败时，**绝对禁止**硬编码塞入 `1.0` 兜底！算不出就跳过 (`continue`)，宁可空榜，不可造假！

---

## ⚡ 系统宪法 (6条带电铁丝网)

> **警告：任何人、任何 Agent、任何 AI 助手，在修改代码前必须熟读并宣誓遵守。违背任意一条，直接判定为严重工程事故！**

1. **严禁时空穿透 (Look-ahead Bias)**: 回测引擎调取历史均量、历史 ATR，**必须强传 `target_date`**！用今天的数据算去年的得分，直接自毁！
2. **严禁自然日推算**: 计算日期禁止使用 `timedelta(days=1)`！必须调用 `calendar_utils.py` 中的 QMT 原生交易日历 `get_real_trading_dates()`。
3. **safe_float护城河**: 从 QMT 字典或 JSON 读出的任何数据，运算前**必须经过 `safe_float()` 强转**！
4. **数据造假零容忍**: 数据获取失败时，**绝对禁止**硬编码塞入假数据！算不出就跳过，宁可空榜，不可造假！
5. **垃圾文件焚烧法**: 根目录绝对禁止出现 `debug_xx.py`、`check_xx.py`。测试一律进 `tests/`，临时脚本用完立刻删除。
6. **严禁捏造 API**: 不确定的 QMT 接口必须查阅官方文档，严禁脑补不存在 API！流通股本必须用 `get_instrument_detail`！

---

## 🏗️ 核心目录结构

```
MyQuantTool/
├── main.py                     # 🎯 唯一CLI入口
├── SYSTEM_CONSTITUTION.md      # ⚖️ 系统宪法
├── logic/                      # 核心业务逻辑
│   ├── core/                   # 唯一事实来源 (SSOT)
│   │   ├── metric_definitions.py
│   │   ├── path_resolver.py
│   │   └── sanity_guards.py
│   ├── strategies/
│   │   └── v18_core_engine.py  # V20纯血游资雷达
│   ├── backtest/
│   │   └── time_machine_engine.py  # 全息时间机器
│   └── data_providers/
│       ├── qmt_manager.py
│       └── true_dictionary.py
├── config/                     # 配置文件
├── data/                       # 数据池 (qmt_data/)
├── tests/                      # 单元测试
└── tools/
    └── unified_downloader.py   # 极限数据吸血鬼
```

---

## ❌ 绝对禁止事项

1. 🗑️ **禁止** 在根目录创建 `.py` 文件 (野脚本)
2. 🗑️ **禁止** 使用模拟数据 (必须真实 QMT)
3. 🗑️ **禁止** 直接运行子模块 (`python logic/xxx.py`)
4. 🗑️ **禁止** 硬编码路径或魔法数字
5. 🗑️ **禁止** 异常静默吞没 (必须 Fail Fast)
6. 🗑️ **禁止** 非交易日启动实盘火控雷达
7. 🗑️ **禁止** 数据获取失败时塞入假数据

---

**最终强调**: 所有操作必须通过 `main.py` CLI入口。QMT是唯一数据源，熔断即停止。
