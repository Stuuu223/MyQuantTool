# MyQuantTool V20.5.1 终极量化架构 (纯血游资雷达 + Boss P0修复)

---

## ⚠️ 【系统最高宪法】摒弃散户思维，拥抱市场物理学

> **语言决定思维！** 本系统严禁使用任何"散户视角"的魔法数字（Magic Number）。

### 🚫 禁止事项（红线）

| 禁止行为 | 错误示例 | 正确做法 |
|----------|----------|----------|
| **禁止涨幅硬编码** | `change_pct > 0.08` (8%涨停判断) | `price_momentum > 0.90` (日内动能净值) |
| **禁止绝对阈值** | `if profit > 5%: sell` | `if profit_pullback > 30%: sell` (相对回撤) |
| **禁止固定百分比** | 主板10%/创业板20%涨停 | 动态识别涨停状态 (`is_limit_up`) |

### ✅ 无量纲化宪法（Ratio化）

**核心原则**：所有判断必须基于资金做功的物理本质，而非表象刻度。

1. **日内动能净值 (Price Momentum)** - 替代绝对涨幅
   ```
   price_momentum = (Current_Price - Low) / (High - Low)
   ```
   - `> 0.90` = 逼空起爆临界状态（死死咬住日内最高点）
   - 不论涨幅是3%还是18%，只要咬住最高点就是强势

2. **MFE做功效率** - 测算涨幅纯度
   ```
   MFE = 振幅百分比 / 净流入占比
   ```
   - `> 1.0` = 真空无阻力状态（资金推力效率极高）
   - 强行拉升的8% vs 真空加速的3%，后者势能碾压前者

3. **大力出奇迹特权** - 资金绝对霸权
   ```
   inflow_ratio_pct > 10.0  →  无视一切摩擦力与时间衰减
   ```
   - 净流入占流通市值超过10% = 主力花天价吃筹码
   - 强制解除尾盘打折、阻力位摩擦力等任何负面压制

### 📐 量纲铁律

| 数据源 | volume单位 | amount单位 | 入口清洗 |
|--------|------------|------------|----------|
| `subscribe_quote` 实盘流 | 手(100股) | 元 | `volume *= 100` |
| `get_full_tick` 快照 | 股 | 元 | 无需转换 |
| `get_local_data` 回测 | 股 | 元 | 无需转换 |

**流通市值锚点**：`float_market_cap = float_volume × price` 必须是绝对人民币元！

### 🧹 字段清洗铁律 (CTO V62钦定)

| 数据源 | 昨收价字段 | 当前价字段 | 数据结构 | 访问方式 |
|--------|------------|------------|----------|----------|
| `subscribe_quote` 实盘流 | `lastClose` | `lastPrice` | C++对象 | `tick.lastPrice` |
| `get_full_tick` 快照 | `lastClose` | `lastPrice` | 字典嵌套 | `tick['lastPrice']` |
| `get_local_data` 回测 | `lastClose` | `lastPrice` | Pandas DataFrame | `df['lastPrice']` |

**统一清洗规则**：
```python
# 引擎只接收纯物理常量，不接触原始格式！
current_price = tick.get('lastPrice', 0) or tick.get('price', 0)
pre_close = tick.get('lastClose', 0) or tick.get('prev_close', 0)
```

**同源方案**：隔离数据通道，同源物理逻辑。引擎只接收5个纯物理常量：`price/amount/high/low/pre_close` + 时间进度 `minutes_passed`

---

## 🧠 V20.5 资金物理学核心法则 (CTO 钦定)

本系统彻底废除传统技术指标与均线系统，全面拥抱资金动能物理学。以下为不可摧动的系统宪法：

### 1. 时间归一化量比 (Volume Ratio)
**公式:** `量比 = (当前累计成交量 / 开盘至今有效分钟) / (五日均量 / 240)`
**铁律:** 盘中瞬时补网漏斗，绝对量比阈值定死为 **> 3.0 倍**。严禁使用未经时间加权的静态除法！

### 2. 极速真实换手率 (Turnover Rate)
**公式:** `换手率 = (当前累计成交量[手] / 流通股本[股]) * 100 * 100`
**铁律:** 死亡拦截线定死为 **150%**（Boss裁决：300%是摆设，70%会误杀真龙）。绝不允许爆量诈尸股入池！

### 3. 真实资金做功效率 (MFE)
**公式:** `MFE = (波段最高价 - 波段最低价) / (主动净买入额 / 流通市值)`
**铁律:** 废除绝对振幅，分子必须是百分比振幅，防量纲灾难！

### 4. 跨日记忆衰减算子 (Decay Factor)
**公式:** `T+1 记忆残值 = 昨日抽血占比 * 0.5`
**铁律:** 两日未上榜直接 TTL 物理湮灭！

---

## ⚙️ QMT 物理交互边界

1. **VIP 直连真理源** 全量由 `58609/58610` 端口直连本地已启动的 QMT 客户端，由客户端负责鉴权，严禁使用 xtdatacenter 无头模式！
2. **盘前装弹真理源** TrueDictionary 提取 5 日均量时，target_date 必须且只能是 **"上一个有效交易日"**，已引入 JSON 硬盘缓存实现毫秒启动！
3. **探针真理源** 验证 QMT 是否连通的唯一探针是 `xtdata.get_trading_calendar('SSE')`

*(注：SectorEmotionCalculator、FullMarketScanner 等旧版冗余模块已于 V20.5 被物理斩首，严禁复活)*

---

## 📊 参数启用状态表 (V20.5.1 - 2026-03-04 Boss P0修复)

| 参数 | 状态 | 说明 |
|------|------|------|
| `early_scale_factor` | ✅ 已启用 | 早盘降阈系数0.6，9:30-09:45阈值降低40% |
| `atr_ratio_min` | ✅ 已启用(仅记录) | ATR势垒阈值1.8x，当前不拦截只记录到df。**P0修复：缺数据保留NaN** |
| `atr_filter_mode` | ✅ 已启用 | 当前`record_only`，等回测后切换为`hard_filter` |
| `min_volume_multiplier` | ✅ 已启用 | 量比阈值1.0x |
| `turnover_rate_max` | ✅ 已启用 | **死亡换手150%**（研究验证：70%以上10日亏损4.67%）|
| `kinetic_barrier_min` | ⚠️ 占位未启用 | 公式：a(t)=60s换手率加速度，待成交动能引擎完成后启用 |
| `micro_kinetic_window` | 🧪 实验参数 | 对应已废弃的盘口引擎，不建议使用 |
| `micro_kinetic_min_acceleration` | 🧪 实验参数 | 对应已废弃的盘口引擎，不建议使用 |

### 👶 关于新股策略

新股在 `stock_filter` 的第一道（`min_avg_amount=5000万` 需要历史数据）就被过滤，不会进入死亡换手判断环节。系统专注于有历史数据支撑的右侧起爆点，新股前几天的乱打行为不符合模型假设！

---

## 📂 数据目录约定 (V20.5.1)

### QMT 客户端缓存（唯一真理源）

本系统所有数据统一从 **QMT 客户端本地缓存** 读取，确保实盘/回测/验证脚本数据一致性。

#### 路径配置（优先级从高到低）

1. **环境变量**：`QMT_USERDATA_PATH`（推荐部署时设置）
2. **config.json**：`qmt_data_source.userdata_path`（本地开发配置）
3. **自动探测**：`E:/QMT/userdata_mini`（Windows 默认位置，最后兜底）

#### 目录结构
```
{QMT_USERDATA_PATH}/datadir/
├── SZ/                           # 深市
│   ├── 86400/                    # 日线（直接是.DAT文件）
│   │   ├── 000001.DAT
│   │   └── 000002.DAT
│   ├── 60/                       # 分钟线（直接是.DAT文件）
│   │   ├── 000001.DAT
│   │   └── 000002.DAT
│   └── 0/                        # Tick（按股票代码/日期分文件）
│       ├── 000001/               # 股票代码目录
│       │   ├── 20260202.dat      # .dat格式
│       │   └── 20260203          # 或无后缀格式（两种都存在）
│       └── 000002/
└── SH/                           # 沪市（结构同上）
```

#### 用途说明

- **实盘**：`xtdata.get_market_data_ex()` 自动读取 QMT 缓存
- **回测/验证脚本**：通过 `ConfigManager.get_qmt_userdata_path()` 获取路径后直接读取
- **历史数据**：首次运行时 QMT 会自动下载并缓存

#### 代码示例（正确 vs 错误）

```python
# ❌ 错误：硬编码路径
df = pd.read_csv('E:/QMT/userdata_mini/datadir/SZ/86400/000001.DAT')

# ✅ 正确：通过 ConfigManager 统一获取
from logic.core.config_manager import get_config_manager
config = get_config_manager()
qmt_path = config.get_qmt_userdata_path()

# 日线路径: datadir/SZ/86400/000001.DAT
sz_daily = os.path.join(qmt_path, 'datadir', 'SZ', '86400')
# Tick路径: datadir/SZ/0/{股票代码}/{日期文件}
# 注意: Tick文件有两种格式: {日期}.dat 或 {日期}(无后缀)
sz_tick = os.path.join(qmt_path, 'datadir', 'SZ', '0', '000001')

# 注意：QMT数据是.DAT二进制格式，需用xtdata API读取
```

### 废弃说明

- ❌ **`data/kline_cache/` 已于 V20.5 废弃**，不再维护
- ❌ 所有历史脚本如引用该目录，必须改为读取 QMT 客户端缓存

---

## 🔧 实战操纵与排错手册

### 1. 冷启动流程

1. 启动 QMT 客户端并登录。
2. 运行 `python main.py live`。
3. 检查控制台：`⚡ [CTO缓存命中] 0毫秒装弹完成!` 表示均量数据加载成功。

### 2. 漏斗透视 (故障排查)

- **看板为空?** 检查 `logs/radar.log`。
- **关键词搜索**: `🚫 [CTO透视]`。
- **判断依据**: 若显示 `未达量比门槛`，则说明当前无强势资金流；若无任何 Tick 日志，检查 QMT 是否断线。

### 3. 一键熔断

若行情极端异常，直接将 `config/strategy_params.json` 中的 `min_volume_multiplier` 修改为 `10.0` 并保存，系统将自动进入全局停火状态。

---

## 🐛 历史 Bug 记录 (血泪教训)

### 2026-03-09: L1探针误杀 + 量纲归零双杀 Bug (V52 CTO纠偏令)

**Bug #1: L1探针死板拦截早盘建仓**
- **现象**: 20260105 scan只返回2只臭狗屎，真龙全部被误杀
- **根因**: L1探针用死板阈值`delta_turnover > 0.5%`就判派发，但早盘是主力爆量建仓黄金期！
- **修复**: 早盘15分钟内放行，价格必须下跌才算派发
- **修复位置**: `run_live_trading_engine.py:1939`

**Bug #2: 量纲错误时净流入归零**
- **现象**: 真龙INFLOW显示异常高，代码直接归零处理
- **根因**: QMT返回的`FloatVolume`单位可能不一致（股/手/万股），代码遇到异常直接归零而不是校准！
- **修复**: 实装量纲自适应校准仪（市值<2000万乘10000，<2亿乘100）
- **修复位置**: `kinetic_core_engine.py:432-449`, `main.py:505-527`, `run_live_trading_engine.py:1221-1242`

**Bug #3: INFLOW截断抹杀真龙**
- **现象**: 所有股票INFLOW都被截断到[-50%, 50%]
- **根因**: `inflow = min(max(inflow_ratio, -50.0), 50.0)` 一刀切截断
- **修复**: 移除截断，让真龙数据原汁原味展示
- **修复位置**: `main.py:761-763`

**血泪教训**:
> **永远不要用归零掩盖数据异常！** 量纲错了应该校准量纲，不是一刀切归零。早盘是主力建仓黄金期，不能用死板阈值误杀。

---

### 2026-03-05: 快照字段名 + 量比单位双杀 Bug

**Bug #1: 快照字段名错误**
- **现象**: 粗筛池固定300+只，量比中位数5.89（异常放大）
- **根因**: QMT快照中昨收价字段是`lastClose`，代码用的是`preClose`
- **影响**: `prev_close`全是0，第一斩过滤完全失效
- **修复位置**: `qmt_event_adapter.py:192`, `run_live_trading_engine.py:404,1732`

**Bug #2: 量比单位错误**
- **现象**: 所有股票量比都>3.0，无筛选效果
- **根因**: `avg_volume_5d`单位是手，`volume_gu`单位是股，量比 = 股/手 放大100倍！
- **修复**: `avg_volume_5d_gu = avg_volume_5d * 100`

```python
# ❌ 错误代码
df['volume_ratio'] = df['estimated_full_day_volume'] / df['avg_volume_5d']
# 股 / 手 = 放大100倍！

# ✅ 正确代码
df['avg_volume_5d_gu'] = df['avg_volume_5d'] * 100  # 手→股
df['volume_ratio'] = df['estimated_full_day_volume'] / df['avg_volume_5d_gu']
```

**教训**: QMT量纲铁律必须严格遵守：
- 日K volume: **手**
- FloatVolume: **股**
- 快照 volume: **股**
- 快照昨收: **lastClose**（不是preClose！）

---

## 📖 资金物理学白皮书 (V20.5)

### 序言：股市的尽头是物理学

本系统彻底摒弃散户思维中基于"涨幅"与"红绿"的后视镜偏见。在系统架构中，价格上涨只是结果，资金推力转化为价格的速度（动能）和暗中蓄积的能量（势能）才是原因！

### 第一定律：能量守恒与微观动能 (Kinetic Energy)

1. **时间归一化量比 (Time-Normalized Volume Ratio)**
   - **公式**: `(当前累计成交量 / 开盘至今有效分钟) / (五日均量 / 240)`
   - **铁律**: 盘中瞬时补网漏斗，绝对量比阈值定死为 **> 3.0 倍**。

2. **极速真实换手率 (Real Turnover Rate)**
   - **公式**: `(当前成交量[手] * 100 / 流通股本[股]) * 100`
   - **铁律**: 死亡拦截线上限定死为 **300%**。

### 第二定律：做功效率与 MFE 算子

- **MFE (Money-Force Efficiency)**: `(波段最高价 - 波段最低价) / (主动净买入额 / 流通市值)`
- **物理意义**: 衡量主力花了多少真金白银净流入，才把价格砸出了多高的山峰。效率极高说明上方抛压真空；效率极低说明面临套牢盘剧烈摩擦！

### 第三定律：记忆半衰期与物理湮灭 (Decay & TTL)

- **跨日衰减**: 强势股基因权重每日乘以 **0.5**
- **物理湮灭**: 连续 2 个交易日未触发强流入或上榜，记忆得分强制归零！

### 第四定律：绝对隔离门 (Filtering Gateways)

- **防守斧**: 严禁跌破全天均价线(VWAP)
- **尖刺骗炮 (Spike Trap)**: 识别重力异常坠落（二阶加速度负值），直接绞杀！

---

## 📋 待办事项
- [ ] 下周：新建`amount_kinetic_engine.py`（基于成交金额dAmount/dt）
