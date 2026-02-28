# AI开发团队最高约束宪法：开发范式与知识库挂载 (V20)

> **Boss痛批：**你们用正则表达式去匹配和修改Python代码，导致缩进错乱、逻辑崩塌，陷入无限死循环！代码臃肿不堪，毫无工业级设计可言！
> **要求：**立刻停止一切"正则表达式打补丁"的野蛮行为！全面升级开发范式！

## 🧠 一、强制知识库挂载 (Knowledge Base)

从今天起，所有Agent开始工作前，必须先读取以下三份文档：

1. `SYSTEM_CONSTITUTION.md` (系统铁律)
2. `DEVELOPMENT_PARADIGM.md` (开发规范，即本文档)
3. `QMT_DOMAIN_KNOWLEDGE.md` (QMT接口特性与坑点清单)

## 🔨 二、绝对禁止的开发行为 (红线)

### 💀 严禁1：正则打补丁 (No Regex Patching)

**严禁**使用`sed`、`re.sub()`来修改`.py`文件！

**正确做法**：必须通过读取整个类/函数，理解其AST（语法树）逻辑后，**完整地重写该函数或类**，并安全地覆盖！如果文件太大，必须先拆分重构！

**错误示例：**
```python
# ❌ 严禁！用正则盲狙修改代码
tm_content = re.sub(r'print\(f"\\s*⏳ 检查进度:.*?"\)', '', tm_content)
```

**正确示例：**
```python
# ✅ 正确！完整重写函数，确保安全
with open('file.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 精确定位函数位置，完整替换
new_function = '''
def new_func():
    # 完整的新逻辑
    pass
'''

# 安全替换（保持缩进和上下文）
# ...
```

### 💀 严禁2：静默吞没异常 (No Silent Failures)

**严禁**写类似于`try: ... except: return 0.0`的掩盖性代码。

**正确做法**：脏数据必须在数据接入层（DAL）拦截，使用DTO或强类型断言。宁可抛出`DataValidationError`让那一只股票熔断跳过，也不准把脏数据喂给V20引擎算分！

### 💀 严禁3：冗余的数据请求 (No Duplicate I/O)

全系统必须统一使用DTO作为唯一数据管线。严禁在业务引擎里直接`import xtdata`！

## 🏗️ 三、强制重构任务：拆解"屎山"，精简代码

### 第一步：建立DTO数据整流罩

在`logic/core/models.py`中强制定义数据契约：

```python
from dataclasses import dataclass

@dataclass
class StockTickData:
    stock_code: str
    price: float
    pre_close: float
    volume_ratio: float
    turnover_rate: float
    # 所有的强类型转换全部在这里完成！引擎层拿到的必须是100%干净的Float！
```

### 第二步：统一数据访问

废除分散的循环，建立严格的Pipeline模式：

```python
# 规范流程
candidates = UniverseBuilder().get_daily_universe(date)  # 返回50只
clean_data_objects = DataAdapter().get_clean_tick_models(candidates, date)  # 返回50个验证过的模型
scored_results = V20Engine().score_all(clean_data_objects)  # 纯算力，0 IO
DashboardRenderer().render(scored_results)
```

## 📏 四、单位换算铁律 (Unit Conversion Law)

**绝对禁止**在业务逻辑中散落`* 100`、`/ 10000`等魔术数字！

**所有单位换算必须且只能在`logic/core/models.py`的DTO中发生！**

QMT数据单位规范：
- **成交量（Volume）**：日K线为"手"，Tick可能为"股"
- **成交额（Amount）**：统一为"元"
- **流通股本（FloatVolume）**：通常为"万股"

DTO必须提供自适应纠偏：
```python
@property
def turnover_rate(self) -> float:
    """返回0~100之间的干净换手率百分比"""
    # 自动检测单位并纠偏
    pass
```

## 🎯 五、开发流程规范

1. **任何修改前**：必须先读取本规范和SYSTEM_CONSTITUTION.md
2. **任何修改中**：严禁使用正则，必须完整重写函数/类
3. **任何修改后**：必须从真实入口测试验证，不得创建假数据测试文件
4. **Git提交**：message必须包含修改原因和影响范围

## ⚠️ 六、违宪后果

违反以上任意一条：
- 代码拒绝合并
- 屡犯者回滚重来
- 严重违规者断开Agent权限

---

**生效日期：** 2026-02-28
**制定者：** CTO
**执行者：** AI开发团队