# MyQuantTool V20.5 动能物理学与极致全息架构白皮书

## 1. 核心哲学：放弃幻想，极致物理学
本系统彻底摒弃"涨幅"、"红盘"等散户后视镜思维。将 A 股视为经典物理学实验室：
- **势能 (Potential Energy)**：当日 5min 资金流对比历史中位数的比值（要求 > 15 倍）。
- **动能 (Momentum)**：价格推力背离 (ΔPrice / ΔVolume)。单位成交量推高价格的效率。
- **重力衰减 (Decay)**：情绪跨日半衰期。连续 2 日未触及流入阈值，记忆得分强制物理湮灭 (TTL = 0)。

## 2. 纯血组织架构 (SSOT - Single Source of Truth)
系统已执行"死刑大清洗"，剥离了所有 Tushare 的妥协方案。当前架构为 **100% 纯血 QMT 本地化**，唯一合法模块分布如下：

- **数据供给层 (Data Providers)**：
  - `UniverseBuilder`: **唯一粗筛入口**。基于 **QMT 纯日 K (period='1d')** 实现三漏斗粗筛，结合 `bson_blacklist.json` 剔除毒瘤，**坚决不碰 Tick，彻底摒弃 Tushare！**
  - `TrueDictionary`: **唯一基础数据缓存**。负责盘前 O(1) 极速提取流通盘与 5 日均量，杜绝在算分时重复拉取数据。
  - `QmtManager / Tick Manager`: 唯一的 QMT Tick 数据隔离网关（防爆笼子）。

- **算分引擎层 (Strategies)**：
  - `TimeMachineEngine` / `V18_Core_Engine`: 执行横向吸血乘数 (Cross-Sectional PK) 与物理学 Tick 级算分。

- **执行防守层 (Execution)**：
  - `TradeGatekeeper`: 双斧防守。绝对 VWAP 均价线惩罚机制与 Golden 回落检验。

## 3. 严禁事项 (Red Lines)
- ❌ **严禁回退 Tushare**：既然我们在本地排雷战役中胜利（`find_bson_bomb.py`），就不允许再用 Tushare 的 API 去做粗筛。
- ❌ **严禁在 UniverseBuilder 碰 Tick**：Tick 数据只允许在 `TimeMachineEngine` 精算时，针对通过日 K 粗筛的 50-80 只健康股票进行单点调取。
- ❌ **严禁保留散户基因**：坚决铲除基于形态学的"半路战法"、`change_pct > 0` 的虚假情绪引擎。

## 4. 已执行的死刑清单 (2026-03-01)
以下死代码已被物理删除，永久告别：
- `logic/strategies/unified_warfare_*.py` - V11-V16半路战法残留
- `logic/strategies/sentiment_engine.py` - 散户情绪垃圾
- `logic/strategies/full_market_scanner.py` - 形态学扫雷史前代码
- `logic/data_providers/instrument_cache.py` - 已被TrueDictionary取代
- `logic/core/error_handler.py` - 零引用死代码
- `logic/backtest/hot_replay_engine*.py` - 旧版回测引擎
