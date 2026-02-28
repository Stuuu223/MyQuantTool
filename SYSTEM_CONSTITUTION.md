# 量化交易系统宪法 (System Constitution)

**版本**: v9.5.0  
**生效日期**: 2026-02-27  
**制定者**: CTO + 老板  
**执行者**: AI开发团队

---

## 宪法宣言

本宪法具有最高法律效力。任何代码、任何提交、任何报告，必须遵守以下条款。

违反者，代码拒绝合并；屡犯者，回滚重来。

---

## 第一条：计算基准铁律

### 1.1 真实涨幅计算
**绝对禁止**: 使用`(收盘价-开盘价)/开盘价`计算涨幅  
**唯一正确**: `(今收-昨收)/昨收`  
**强制使用**: `MetricDefinitions.TRUE_CHANGE(current, pre_close)`

**示例**:
```python
# ❌ 错误
day_change = (close_price - open_price) / open_price * 100

# ✅ 正确
day_change = MetricDefinitions.TRUE_CHANGE(close_price, pre_close)
```

### 1.2 真实振幅计算
**绝对禁止**: 使用当日最高最低价差除以当日开盘价  
**唯一正确**: `(最高-最低)/昨收`  
**强制使用**: `MetricDefinitions.TRUE_AMPLITUDE(high, low, pre_close)`

### 1.3 昨收价获取
**绝对禁止**: 使用任何外部API或估算值  
**唯一正确**: QMT本地日线数据  
**强制使用**: `PathResolver.get_qmt_data_dir()` + `xtdata.get_local_data()`

**禁止**:
- 禁止`pre_close = open_price * 0.97`（估算）
- 禁止`pre_close = close_price`（用当日收盘价冒充）
- 禁止`pre_close = df.iloc[0]['price']`（用首笔价格）

---

## 第二条：路径规范铁律

### 2.1 禁止硬编码
**绝对禁止**: 任何`E:\`、`C:\`、`./`、`../`开头的路径字符串  
**唯一正确**: 使用PathResolver动态解析  
**审查红线**: 代码中出现硬编码路径，提交直接打回

**示例**:
```python
# ❌ 错误
data_dir = 'E:/MyQuantTool/data'

# ✅ 正确
data_dir = PathResolver.get_data_dir()
```

### 2.2 目录结构（极简版）
```
MyQuantTool/           # 根目录
├── config/            # 配置层（JSON/YAML）
├── data/              # 数据缓存
├── logic/             # 【唯一】业务逻辑中心
│   ├── core/          # 算子字典（MetricDefinitions等）
│   ├── data_providers/# 仅QMT数据提供者
│   ├── strategies/    # 策略核心（V18等）
│   └── backtest/      # 回测引擎
├── tests/             # 单元测试（仅core/）
├── SYSTEM_CONSTITUTION.md  # 本宪法
└── main.py            # 【唯一】入口
```

**绝对禁止**:
- 在根目录创建任何新文件夹
- 在logic/下创建非核心目录
- tools/、tasks/、backtest/根目录已删除

---

## 第三条：代码规范铁律

### 3.1 零硬编码原则
- ❌ 禁止魔法数字（40.0, 300986, 20260105等）
- ❌ 禁止股票代码硬编码
- ❌ 禁止日期硬编码
- ✅ 所有参数必须从config读取或从CLI传入
- ✅ 支持命令行参数，提供灵活性

### 3.2 零异常吞没原则
- ❌ 禁止`try-except-pass`
- ❌ 禁止`return None`代替错误
- ❌ 禁止`fillna(0)`掩盖数据问题
- ✅ 必须`Fail Fast`，立即报错熔断

**示例**:
```python
# ❌ 错误
try:
    pre_close = get_pre_close(stock, date)
except:
    pre_close = open_price * 0.97  # 估算！

# ✅ 正确
pre_close = get_pre_close(stock, date)
if pre_close is None:
    raise DataMissingError(f"{stock} {date} 昨收价缺失")
```

### 3.3 接口隔离原则
- ❌ 业务层禁止`import xtdata`
- ❌ 业务层禁止直接操作文件
- ❌ 业务层禁止自行编写计算逻辑
- ✅ 必须通过封装接口

**分层调用**:
```
main.py -> logic/strategies/ -> logic/core/ -> logic/data_providers/ -> xtdata
```

---

## 第四条：数据质量铁律

### 4.1 Sanity Check必过
所有计算结果必须通过`SanityGuards.full_sanity_check()`

**强制检查项**:
1. 涨幅是否合理（<100%）
2. 得分是否一致（final_score=0但base_score>0时熔断）
3. 成交量是否合理（不为0）
4. 昨收价是否有效（>0）

### 4.2 熔断机制
以下情况系统必须熔断（拒绝生成报告）：
- 涨幅超过100%
- 成交量为0
- 最终得分为0但基础分>0
- 昨收价<=0
- SanityGuards未通过

### 4.3 数据血缘
所有数据必须能追溯到QMT本地数据源
- 禁止任何外部数据源作为数据源
- 禁止估算值
- 禁止兜底默认值

---

## 第五条：禁止事项清单

### 绝对禁止的技术债务
| 禁止项 | 后果 | 替代方案 |
|--------|------|----------|
| ❌ 随意创建文件（除非绝对必要） | 项目混乱 | 优先编辑现有文件 |
| ❌ 在tools/目录创建新文件 | 屎山+1 | 使用main.py CLI |
| ❌ 在tasks/目录创建新文件 | 屎山+1 | 使用main.py CLI |
| ❌ 使用任何外部数据源 | 数据污染 | 使用QMT本地数据 |
| ❌ 使用估算值代替真实数据 | 错误结果 | 报错熔断，拒绝计算 |
| ❌ 自行编写计算逻辑 | 不一致 | 使用MetricDefinitions |
| ❌ 硬编码路径 | 系统脆弱 | 使用PathResolver |
| ❌ 返回None代替错误 | 隐藏问题 | 抛出异常 |
| ❌ 捕获异常不处理 | 隐藏问题 | Fail Fast |
| ❌ 魔法数字（40.0, 300986） | 维护困难 | 使用config或参数 |
| ❌ 单股硬编码脚本 | 不可复用 | 通用分析器 |

---

## 第六条：AI团队行为准则

### 6.1 开发前必读
每次接到新任务前，必须：
1. 阅读本宪法（SYSTEM_CONSTITUTION.md）
2. 检查是否已有封装好的算子（logic/core/）
3. 检查是否已有类似功能（禁止重复造轮子）
4. 优先编辑现有文件而非创建新文件
5. 为现有工具添加参数支持以提高灵活性

### 6.2 代码提交前自检
提交前必须确认：
- [ ] 没有硬编码路径
- [ ] 使用MetricDefinitions进行计算
- [ ] 通过SanityGuards检查
- [ ] 没有新建tools/或tasks/文件
- [ ] 单元测试通过

### 6.3 遇到问题时的处理
**禁止**:
- ❌ 另辟蹊径写临时脚本
- ❌ 绕过规范打补丁
- ❌ 用任何外部数据源糊弄

**正确**:
- ✅ 查看QMT官方文档（dict.thinktrader.net）
- ✅ 向CTO/老板报告问题
- ✅ 封装成通用解决方案

---

## 第七条：违规处罚

### 7.1 代码审查红线
以下情况代码提交将被**立即拒绝**：
1. 硬编码路径（`E:\`, `C:\`等）
2. 自行计算涨幅而不使用MetricDefinitions
3. 使用任何外部数据源
4. 新建tools/或tasks/文件
5. 未通过SanityGuards检查
6. 返回None代替错误

### 7.2 累计违规处理
- 首次违规：代码打回，重写
- 二次违规：整模块回滚
- 三次违规：暂停开发权限，重新培训

---

## 第八条：本宪法的修订

本宪法由CTO和老板共同制定，任何修订必须经两人共同批准。

AI开发团队无权修改本宪法。

---

## 第九条：Ratio化铁律（2026-02-24 血泪教训）

### 9.1 什么是正确的Ratio化
**Ratio化的核心是动态指标**，而不是把绝对阈值改成分位数。

**正确的Ratio化**：
- ✅ 每分钟换手率 `turnover_rate_per_min > 0.2%`
- ✅ 时间衰减权重 `decay_ratio: 1.2/1.0/0.8/0.5`
- ✅ 动态计算基于市场状态

**错误的"Ratio化"**：
- ❌ 把绝对阈值3.0改成88分位数
- ❌ 分位数只代表相对排名，不代表真正放量
- ❌ 88分位数的值可能只有1.6，远低于3.0

### 9.2 绝对阈值不可随意更改
**量比绝对阈值3.0代表交易哲学**：
- 资金为王：量比>3.0确保真正放量
- 排除杂毛：筛选资金活跃的股票
- 右侧起爆：只保留最强势标的

**禁止**：
```python
# ❌ 错误：把绝对阈值改成分位数
volume_ratio_threshold = df['volume_ratio'].quantile(0.88)

# ✅ 正确：保持绝对阈值
VOLUME_RATIO_THRESHOLD = 3.0
df[df['volume_ratio'] >= VOLUME_RATIO_THRESHOLD]
```

### 9.3 修改后必须验证结果
**每次修改阈值后必须验证**：
- 粗筛结果：预期60-120只
- 第二斩结果：预期30只以内
- 数量异常必须排查原因

### 9.4 参数分类管理
| 类型 | 示例 | 管理方式 |
|------|------|----------|
| 绝对阈值 | 量比>3.0 | 配置文件固定值 |
| 动态指标 | 每分钟换手率 | ratio化计算 |
| 时间权重 | 衰减系数 | 配置文件 |

### 9.5 今日核心成果（必须保留）
```python
# 双Ratio化（核心创新）- CTO新标准
from logic.core.config_manager import get_config_manager
config_manager = get_config_manager()

# 从配置获取参数（SSOT原则）
turnover_thresholds = config_manager.get_turnover_rate_thresholds()
volume_ratio_percentile = config_manager.get_volume_ratio_percentile('live_sniper')

# 计算动态量比阈值（基于市场实际情况）
if len(df) > 0 and 'volume_ratio' in df.columns:
    volume_ratio_threshold = df['volume_ratio'].quantile(volume_ratio_percentile)
    volume_ratio_threshold = max(volume_ratio_threshold, 1.5)  # 最小保护阈值
else:
    volume_ratio_threshold = 1.5

# 应用过滤（使用动态阈值而非硬编码）
turnover_rate_per_min = turnover_rate / minutes_passed
mask = (df['volume_ratio'] > volume_ratio_threshold) & \
       (df['turnover_rate_per_min'] > turnover_thresholds['per_minute_min']) & \
       (df['turnover_rate'] < turnover_thresholds['total_max'])

# V18时间衰减
09:30-09:40 → decay_ratio = 1.2  # 早盘冲刺，加权20%
09:40-10:30 → decay_ratio = 1.0  # 上午确认，正常
10:30-14:00 → decay_ratio = 0.8  # 午间垃圾时间，降权
14:00-14:55 → decay_ratio = 0.5  # 尾盘陷阱，大幅降权
```

### 9.6 血泪教训
| 错误 | 后果 | 教训 |
|------|------|------|
| 盲目ratio化 | 589只(应为60只) | ratio化≠分位数化 |
| 不验证结果 | 筛选过松 | 每次修改后验证数量 |
| 概念理解错误 | 成果丢失 | 深刻理解动态换手率才是核心 |

---

## 第十条：V20极致全息架构铁律（2026-02-26 CTO战略决策）

### 10.1 数据分级管理战略
**战略原则**：日K全市场 + Tick精准靶向

| 数据类型 | 策略 | 技术实现 |
|---------|------|---------|
| **日K** | 全市场下载，几年无压力 | 每天自动检测补全，非交易时间静默补齐 |
| **Tick** | 绝不浪费在杂毛上 | 精准靶向，每天100-150只，60天上下文 |

**绝对禁止**：
- ❌ 为"阿猫阿狗"股票下载Tick数据
- ❌ 只下载当日Tick而无上下文
- ❌ 用Magic Number筛选下载标的

### 10.2 全息下载靶向算法（镜像降维法）
**核心原则**：比实盘稍宽，捕获真龙+陷阱

**下载阈值计算**（严禁Magic Number硬编码）：
```python
# 从ConfigManager读取实盘配置
config = get_config_manager()
live_sniper = config.get('live_sniper', {})

# 量比：实盘0.95分位 → 下载0.90分位（降维0.05）
volume_ratio_download = live_sniper.get('volume_ratio_percentile', 0.95) - 0.05

# 换手率：直接使用实盘min_active_turnover_rate（3.0%）
turnover_threshold = live_sniper.get('min_active_turnover_rate', 3.0)

# 价格条件：只要最高价红过（high > pre_close）
price_condition = "high > pre_close"
```

**上下文切片**：
- 前30天 + 后30天 = **共60个交易日**
- 最新日期触发：往前下载60天
- 必须维护下载注册表，避免重复I/O

**预期结果**：每天**100-150只**股票进入Tick下载池

### 10.3 两段式混合回测架构
**阶段1：向量化极速雷达（上帝视角）**
- 使用Pandas向量化计算（cumsum/apply）
- 毫秒级定位起爆点：`df[df['volume_ratio'] > 0.95].first_valid_index()`
- **严禁**使用For循环遍历Tick数据

**阶段2：事件驱动微观模拟（散户视角）**
- 仅对起爆点后的关键30秒进行逐笔模拟
- 检测微观盘口陷阱（诱多撤单/散户跟风/封单衰减）
- 模拟撮合判定（排队位置/废单概率）

**性能指标**：
- 向量化阶段：<100ms/只
- 事件模拟阶段：逐笔3ms
- 全市场回测：<30分钟

### 10.4 微观盘口三道防线（基于Tick五档）
**防线1：诱多撤单检测**
- 滑动窗口：起爆前15秒（5个Tick周期）
- 检测指标：bid1_vol平均值在起爆后1-2个Tick内断崖下跌>70%
- 判定：假托单真出货

**防线2：散户跟风检测**
- 分析成交量分布：小单（<100手）vs 大单（>1000手）
- 判定：小单占比>80%为散户自嗨，无主力护盘

**防线3：封单衰减预警**
- 监测涨停后封单量变化
- 判定：1分钟内封单衰减>50%触发危险信号

### 10.5 严禁向下甩锅（Boss+CTO已拍板参数）
以下参数**立即执行**，禁止再问"是否合适"：

| 参数 | 值 | 来源 |
|------|-----|------|
| 量比降维 | **0.90分位** | 实盘0.95 - 0.05 |
| 换手率 | **3.0%** | live_sniper.min_active_turnover_rate |
| 价格条件 | **high > pre_close** | 只要最高价红过 |
| 上下文天数 | **60天** | 前30后30 |
| 日K策略 | **全市场自动补全** | 非交易时间静默补齐 |
| Tick策略 | **100-150只/天** | 精准靶向 |

**禁止行为**：
- ❌ "0.90还是0.92？"（抛出备选让老板选择）
- ❌ "是否合适？"（用疑问句替代执行）
- ❌ "建议确认..."（重复请示已确定参数）

### 10.6 AI-Native开发形态（CTO黑科技）
**记忆钩子**：自动加载ShortTermMemory.json，治愈AI失忆症
**自愈断言**：audit_rules.py红线强制拦截（Magic Number/外部数据源/For循环）
**专家路由**：5个专业Agent各司其职（量化策略/数据工程/微观结构/回测架构/代码审计）
**阅后即焚**：过程文档（Phase_*.md）在完成后自动清理
**文档即代码**：每次提交必须同步更新SYSTEM_CONSTITUTION.md

---

## 第十一条：V20.5 极致全息架构铁律（2026-02-27 CTO终极净化）

### 11.1 CTO终极净化成果
**最新状态**：[CTO战前终极净化] 三大边缘隐患已清除

**1. MFE向上做功优化**
- 使用 `(price-low + high-open)/2` 过滤天地板
- 避免极端价格波动对MFE指标的干扰
- 确保MFE指标在合理范围（0.52~1.09）

**2. 流入比保护**
- 添加 `float_market_cap > 1000` 检查
- 流入比限制在 -50%~50% 范围内
- 防止异常值对评分系统的影响

**3. MFE一字板惩罚**
- 排序时对 MFE > 5.0 的情况进行倒扣分
- 避免缩量秒板等无意义涨停的误判
- 保持评分系统的有效性

**验证结果**：
- MFE指标范围回归合理区间 (0.52~1.09)
- 两套看板结果100%一致

### 11.2 CTO天网对齐
**核心改进**：
- 修复MFE量纲问题
- 统一数据源 (SSOT - Single Source of Truth)
- 修复ATR计算中的pre_close列缺失问题
- 确保所有计算基于同一数据源

### 11.3 数据源统一(SSOT)原则
**SSOT原则**（Single Source of Truth）：
- 所有数据必须源自QMT本地数据
- 不允许多数据源并存
- 统一数据访问接口
- 避免数据不一致性

**数据流向**：
```
QMT本地数据 → TrueDictionary → V18CoreEngine → TradeGatekeeper
```

---

## 附录：常用接口速查

### PathResolver（路径解析）
```python
from logic.core.path_resolver import PathResolver

root = PathResolver.get_root()          # 项目根目录
data_dir = PathResolver.get_data_dir()  # 数据目录
config_dir = PathResolver.get_config_dir()  # 配置目录
qmt_dir = PathResolver.get_qmt_data_dir()   # QMT数据目录
```

### MetricDefinitions（指标计算）
```python
from logic.core.metric_definitions import MetricDefinitions

change = MetricDefinitions.TRUE_CHANGE(current, pre_close)
gap = MetricDefinitions.GAP_UP_PREMIUM(open_price, pre_close)
amplitude = MetricDefinitions.TRUE_AMPLITUDE(high, low, pre_close)
vwap = MetricDefinitions.VWAP(df)
```

### SanityGuards（数据检查）
```python
from logic.core.sanity_guards import SanityGuards

passed, errors = SanityGuards.full_sanity_check({
    'stock_code': '300986.SZ',
    'change_pct': 20.0,
    'base_score': 80.0,
    'final_score': 89.0,
    'volume': 1000000,
    'pre_close': 11.18
})
```

---

**本宪法是系统的最高法律，任何代码必须遵守。**

**制定日期**: 2026-02-23  
**修订日期**: 2026-02-27（V20.5 极致全息架构）  
**生效状态**: 立即生效