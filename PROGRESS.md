# 项目进度追踪

## 2026-02-20 研究进展

### 今日完成
- [x] 完成16只顽主票（高频8+中频5+低频3）分层抽样
- [x] 验证24个正反例案例（真起爆13个+骗炮11个）
- [x] 建立Ratio化资金指标体系（替代魔法数字）
- [x] 确定自适应阈值: ratio_stock>15, ratio_day>12, sustain>1.2
- [x] 修正数据路径混乱问题（创建data_paths.json统一配置）
- [x] 修正涨幅计算错误（使用pre_close替代open_price）

### 关键发现
- 真起爆的max_ratio_stock(21.45)显著高于骗炮(13.72)，差异+56%
- 网宿科技正反例对比：ratio_stock 57.80 vs 14.91（4.2倍差异）
- 技术路径验证：QMTHistoricalProvider + RollingFlow + HalfwayV2 稳定可用

### 待解决问题
- [ ] 淳中科技等案例昨收价计算异常（涨幅>400%）
- [ ] 补充中频/低频层案例至40-50个
- [ ] 将Ratio阈值集成到策略服务

### 文档记录
- 详细研究日志: `docs/RESEARCH_LOG_20260220.md`
- 数据路径配置: `config/data_paths.json`
- Ratio计算工具: `logic/rolling_metrics.py`

---

## [顽主票右侧起爆点回测] 需求卡

- 背景：验证半路/龙头战法在顽主票池的历史胜率，商业验证优先级最高
- 目标：复用V17已验证的Tick回放架构，替换策略逻辑为顽主票池
- 影响范围：backtest/目录下新增脚本，复用现有引擎
- 红线约束：
  - 不得绕过UnifiedWarfareCore
  - 不得直连xtdata，必须通过QMTHistoricalProvider
  - 不得硬编码阈值，使用相对分位数
- 发起人：老板
- 创建日期：2026-02-20

## [顽主票右侧起爆点回测] 设计卡

### 1. 目录与模块变更
- 新增：backtest/run_wanzhu_replay_backtest.py (顽主专用回放)
- 修改：无
- 删除：tools/run_wanzhu_backtest_dirty.py (废弃脏包方案)

### 2. 抽象与接口使用
- 统一使用UnifiedWarfareCore.process_tick()处理事件
- 通过QMTHistoricalProvider获取Tick数据
- 保持与run_halfway_replay_backtest.py一致的回测框架

### 3. 数据源与模式
- 实时模式：QMT Tick → Level2/Level1/QmtTick Provider
- 回放模式：本地Tick数据 → QMTHistoricalProvider

### 4. 最小自测计划
- 命令：python backtest/run_wanzhu_replay_backtest.py --stocks 300997.SZ --start 2026-01-29 --end 2026-01-29
- 观察：是否检测到诱多信号，回测结果是否正常