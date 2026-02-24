# 量化交易系统宪法 (System Constitution)

**版本**: v9.0.0  
**生效日期**: 2026-02-23  
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
**绝对禁止**: 使用Tushare或估算值  
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
- 禁止Tushare作为数据源
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
| ❌ 使用Tushare作为数据源 | 数据污染 | 使用QMT本地数据 |
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
- ❌ 用Tushare糊弄

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
3. 使用Tushare作为数据源
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
**生效状态**: 立即生效