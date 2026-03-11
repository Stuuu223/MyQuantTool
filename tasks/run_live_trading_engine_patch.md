# CTO V9.5 架构层修复补丁说明

## 修复清单

### F1【已修复】`kinetic_core_engine.py` - mfe 初始化防 UnboundLocalError
- **文件**: `logic/strategies/kinetic_core_engine.py`
- **问题**: `calculate_true_dragon_score` 中 `mfe` 变量仅在 `inflow_ratio_pct > 0` 分支赋值。当 `flow_15min <= 0` 触发 Spike极刑前置 `return` 时，若走了 `inflow_ratio_pct <= 0` 分支，`mfe` 引用未定义变量，抛 `UnboundLocalError`，线上静默崩溃。
- **修复**: 在函数入口处统一初始化 `mfe: float = -100.0`，后续分支再按需覆盖。
- **版本**: V1.1.1 → V1.2.0

### F2【待修复】`run_live_trading_engine.py` - `calculate_time_slice_flows` 空数据保护
- **文件**: `tasks/run_live_trading_engine.py`
- **问题**: `get_local_data` 返回 `df` 不为空但行数极少（如1行）时，`df.loc[first_idx - 1]` 越界（first_idx=0时-1不存在），抛 KeyError。
- **修复方案**: 在 `flow_5min` / `flow_15min` 差值计算处，判断 `first_idx > df.index[0]` 而非 `first_idx > 0`（RangeIndex与Int64Index行为不同），或统一使用 `df.iloc`。
- **状态**: 已标注，待下次推送修复。

### F3【待修复】`run_live_trading_engine.py` - 死亡 `except` 吞噬异常
- **文件**: `tasks/run_live_trading_engine.py` `run_historical_stream` 主循环
- **问题**: `except Exception as e: continue` 静默跳过所有股票级异常，导致调试时完全无法定位问题。
- **修复方案**: 改为 `except Exception as e: logger.debug(f"[SKIP] {stock_code}: {e}"); continue`。

### F4【待修复】`run_live_trading_engine.py` - `_run_radar_main_loop` 重复 `pre_close` 赋值
- **文件**: `tasks/run_live_trading_engine.py` `_run_radar_main_loop` 第四级打分块
- **问题**: `pre_close` 在外层已用 `tick.get('lastClose', 0)` 赋值，在打分块内部又被 `tick.get('lastClose', 0.0) or 0.0` 覆盖，造成逻辑混淆。
- **修复方案**: 删除内层重复赋值，统一使用外层变量。

### F5【待修复】`_calculate_signal_score` 僵尸代码
- **文件**: `tasks/run_live_trading_engine.py`
- **问题**: `_calculate_signal_score` 函数末尾 `return base_score` 之后还有死代码块（`memory_multiplier` 计算），永远不会被执行，但会迷惑代码审查者。
- **修复方案**: 删除 `return base_score` 后的僵尸代码块。

## 架构层建议（已分析，待实施）

1. **`calculate_time_slice_flows` 保护**: 对 `df` 使用 `.iloc` 替代 `.loc[idx-1]`，并在差值为负时返回 `None`
2. **统一 except 日志级别**: 主循环 `except` 至少 `logger.debug` 记录 stock_code 和异常信息
3. **消除重复 `pre_close`**: 提升到循环顶部统一赋值，后续不再覆盖
4. **删除僵尸代码**: `_calculate_signal_score` return 后的死代码段

---
*生成时间: 2026-03-11 | CTO审计版本: V9.5*
