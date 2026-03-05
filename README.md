# MyQuantTool V20.5.1 终极量化架构 (纯血游资雷达 + Boss P0修复)

## 🧠 V20.5 资金物理学核心法则 (CTO 钦定)
本系统彻底废除传统技术指标与均线系统，全面拥抱资金动能物理学。以下为不可摧动的系统宪法：

### 1. 时间归一化量比 (Volume Ratio)
**公式:** `量比 = (当前累计成交量 / 开盘至今有效分钟) / (五日均量 / 240)`
**铁律:** 盘中瞬时补网漏斗，绝对量比阈值定死为 **> 3.0 倍**。严禁使用未经时间加权的静态除法！

### 2. 极速真实换手率 (Turnover Rate)
**公式:** `换手率 = (当前累计成交量[手] / 流通股本[股]) * 100 * 100`
**铁律:** 死亡拦截线定死为 **150%**（Boss裁决：300%是摆设，70%会误杀真龙）。绝不允许爆量诈尸股入池。

### 3. 真实资金做功效率 (MFE)
**公式:** `MFE = (波段最高价 - 波段最低价) / (主动净买入额 / 流通市值)`
**铁律:** 废除绝对振幅，分子必须是百分比振幅，防量纲灾难。

### 4. 跨日记忆衰减算子 (Decay Factor)
**公式:** `T+1 记忆残值 = 昨日抽血占比 * 0.5`
**铁律:** 两日未上榜直接 TTL 物理湮灭。

---
## ⚙️ QMT 物理交互边界
1. **VIP 直连真理：** 全量走 `58609/58610` 端口直连本地已启动的 QMT 客户端，由客户端负责鉴权，严禁使用 xtdatacenter 无头模式。
2. **盘前装弹真理：** TrueDictionary 提取 5 日均量时，target_date 必须且只能是 **"上一个有效交易日"**，已引入 JSON 硬盘缓存，0毫秒启动。
3. **探针真理：** 验证 QMT 是否连通的唯一探针是 `xtdata.get_trading_calendar('SSE')`。

*(注：SectorEmotionCalculator、FullMarketScanner 等旧版冗余模块已于 V20.5 被物理斩首，严禁复活！)*

---
## 📊 参数启用状态表 (V20.5.1 - 2026-03-04 Boss P0修复)

| 参数 | 状态 | 说明 |
|------|------|------|
| `early_scale_factor` | ✅ 已启用 | 早盘降阈系数0.6，09:30-09:45阈值降至60% |
| `atr_ratio_min` | ✅ 已启用(仅记录) | ATR势垒阈值1.8x，当前不拦截只记录到df，**P0修复：缺数据保留NaN** |
| `atr_filter_mode` | ✅ 已启用 | 当前`record_only`，等回测后切换为`hard_filter` |
| `min_volume_multiplier` | ✅ 已启用 | 量比阈值3.0x |
| `turnover_rate_max` | ✅ 已启用 | **死亡换手线150%**（Boss裁决：游资出货完毕红线） |
| `kinetic_barrier_min` | ⏳ 占位未启用 | 公式：a(t)=60s换手率加速度，待成交动能引擎完成后启用 |
| `micro_kinetic_window` | 🧪 实验参数 | 对应已废弃的盘口引擎，不建议使用 |
| `micro_kinetic_min_acceleration` | 🧪 实验参数 | 对应已废弃的盘口引擎，不建议使用 |

### 👶 关于新股策略
新股在 `stock_filter` 的第一道（`min_avg_amount=5000万` 需要历史数据）就被过滤，不会进入死亡换手判断环节。系统专注于有历史数据支撑的右侧起爆点，新股前几天的乱打行为不符合模型假设。

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

# 注意：QMT数据为.DAT二进制格式，需用xtdata API读取
```

### 废弃说明
- ❌ **`data/kline_cache/` 已于 V20.5 废弃**，不再维护
- ✅ 所有历史脚本如引用该目录，必须改为读取 QMT 客户端缓存

---
## 🐛 历史 Bug 记录 (血泪教训)

### 2026-03-05: 快照字段名 + 量比单位双杀 Bug

**Bug #1: 快照字段名错误**
- **现象**: 粗筛池固定4000+只，量比中位数75.89（异常放大）
- **根因**: QMT快照中昨收价字段是`lastClose`，代码用的是`preClose`
- **影响**: `prev_close`全是0，第一斩过滤完全失效
- **修复位置**: `qmt_event_adapter.py:192`, `run_live_trading_engine.py:404,1732`

**Bug #2: 量比单位错误**
- **现象**: 所有股票量比都>3.0，无筛选效果
- **根因**: `avg_volume_5d`单位是手，`volume_gu`单位是股，量比=股/手放大100倍
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
- 快照 volume: **手**
- 快照昨收: **lastClose**（不是preClose！）

---
### 待办事项
- [ ] 本周末：三个月回测框架，重新估ATR阈值
- [ ] 本周末：日K数据验证150%死亡换手合理性
- [ ] 下周：新建`amount_kinetic_engine.py`（基于成交金额dAmount/dt）
