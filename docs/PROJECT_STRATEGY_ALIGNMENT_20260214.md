# 项目战略对齐文档

> **日期**: 2026-02-14
> **目标**: 顽主杯数据价值挖掘 + "实时顽主雷达"愿景
> **角色**: CTO 视角

---

## 一、核心问题回顾

### 1.1 回测失败原因

#### 问题诊断

**根本原因1：QMT数据时间解析错误**
```python
# 错误代码
result_df['datetime'] = pd.to_datetime(result_df['time'], format='mixed')
# 问题：time列是毫秒时间戳1770946200000，被误解析为纳秒
# 结果：所有日期变成1970-01-01，无法匹配回测日期

# 修复方案
result_df.index = pd.to_datetime(result_df.index, format='%Y%m%d%H%M%S')
# 正确：直接使用索引（字符串格式的时间戳）
```

**根本原因2：涨幅计算逻辑错误**
```python
# 错误代码
last_row = daily_df.iloc[-1]
pct_change = (last_row['close'] - last_row['open']) / last_row['open'] * 100
# 问题：使用当日最后一根K线（15:00）的open和close
# 结果：涨幅永远是0%，策略无法触发

# 修复方案
first_row = daily_df.iloc[0]  # 9:30
last_row = daily_df.iloc[-1]   # 15:00
pct_change = (last_row['close'] - first_row['open']) / first_row['open'] * 100
# 正确：使用第一根K线开盘价和最后一根K线收盘价
```

### 1.2 最终回测结果

| 指标 | 数值 | 评价 |
|------|------|------|
| 总收益率 | +9.42% | ✅ 优秀 |
| 最大回撤 | -2.76% | ✅ 控制良好 |
| 交易次数 | 66次 | ⚠️ 偏高 |
| 胜率 | 22.73% | ⚠️ 偏低 |
| 平均盈利 | +45.81% | ✅ 丰厚 |
| 平均亏损 | -6.82% | ✅ 控制良好 |
| 盈亏比 | 6.71 | ✅ 优秀 |

**核心发现**：
- ✅ 盈亏比高（6.71）：盈利交易利润丰厚
- ⚠️ 胜率低（22.73%）：大部分交易止损
- ⚠️ 交易频繁（66次/月）：可能过度交易

---

## 二、用户愿景分析

### 2.1 顽主杯数据的三大价值

**用户观点**：
> "它的价值更多是回测（比如之前因为爬热门股麻烦 这下有顽主杯数据就简单了不少 还能用顽主杯数据去优化竞价策略）"

**价值1：回测优化（训练集）**
- 顽主杯榜单 = 现成的"高分答案"
- 用回测引擎分析过去3个月顽主前10名
- 提取共同特征：起爆前1-3天的资金流、量比、买卖压

**价值2：情绪锚点（市场判断）**
- 昨日顽主前50名的今日平均溢价率
- 情绪指数：>3%情绪亢奋，<-2%核按钮潮
- 据此调整策略激进程度

**价值3：先于市场的实时雷达**
- 不是复制顽主杯，而是逆向工程他们的选股逻辑
- 用QMT实时Tick数据截胡
- 目标：在顽主榜单发布前就持有

### 2.2 核心战略转变

**用户观点**：
> "先于顽主杯之前持有 抓最早的起爆点 等待手里的票众人吹票"

**核心矛盾**：
- 顽主杯 = "事后诸葛亮"（看到时已经晚了）
- 我们 = "事前/事中预判"（比他们更早发现起爆点）

**战略转变**：
```
从：跟随者（看榜下单）
到：抢跑者（比榜单更早发现）
```

---

## 三、CTO方案分析

### 3.1 "实时顽主雷达"核心逻辑

**CTO观点**：
> "核心逻辑：资金不撒谎 (Money Never Lies)"

**三大主力痕迹**：

1. **攻击波（Attack Wave）**
   - 定义：1分钟内主动买入>1000万，涨幅>1%
   - 含义：游资（顽主）进场信号

2. **潜伏盘（Stealth Accumulation）**
   - 定义：股价横盘（振幅<1%），小单流出，大单持续流入
   - 含义：起爆前夜的吸筹

3. **弱转强（Weak to Strong）**
   - 定义：竞价平开/低开，但5分钟内量比>3
   - 含义：最经典的短线买点

### 3.2 系统升级方案

**模块1：实时扫描器（Radar Scanner）**
```python
class RealtimeWanzhuRadar:
    def scan(self, code, tick_data):
        # 条件A: 资金猛（主力净买>1000万 OR 1分钟突袭>300万）
        is_big_money = (flow['main_net_inflow'] > 1000) or \
                       (flow['1min_inflow'] > 300)
        
        # 条件B: 位置好（涨幅在1%-5%之间）
        is_good_position = 1.0 < tick_data['pct_change'] < 5.0
        
        # 条件C: 人气旺（量比>1.5）
        is_active = tick_data['volume_ratio'] > 1.5
        
        if is_big_money and is_good_position and is_active:
            return {
                "signal": "RADAR_DETECTED",
                "reason": f"资金突袭: {flow['1min_inflow']}万",
                "confidence": 0.85
            }
```

**模块2：竞价优选（Auction Filter）**
- 09:25生成"雷达监控名单"
- 只监控400-800只票（而不是全市场5000只）
- 保证QMT的3秒刷新率不卡顿

**模块3：共振确认（Resonance Confirmation）**
- 当雷达扫出Code A起爆时
- 检查Code A所属板块
- 板块共振 = 真突破
- 板块不动 = 假动作（诱多）

---

## 四、拾荒网知识精华

### 4.1 选股三板斧

**第一斧：判断风口**
- 市场主流热点、题材方向
- 板块共振判断（Leaders≥3, Breadth≥35%）

**第二斧：判断股性**
- 股票活跃度、涨停历史
- 经常涨停，且涨停后第二天大都有溢价
- 很少坑人的，涨停后溢价率高

**第三斧：判断主力**
- 主力资金成本、介入程度
- 主力是推动龙头股的力量，没有主力就没有行情
- 跟随主力成本越近，风险越低，收益越大

### 4.2 竞价战法要点

**操作条件**：
- 股票波段涨幅小于25%
- 开盘一小时股价处于强势中
- 回调不破开盘价、均价线或前日收盘价

**竞价预期规则**：
- 规则一：明牌焦点股，竞价不能超预期 → 打折扣
- 规则二：明牌股，竞价超预期 → 不要轻易卖

**量比排序使用**：
- 9:25竞价出来后，9:30开盘后15分钟内完成
- 量比排序 + 涨幅排序配合使用
- 在有效价格范围内选取成交量最大的价位

### 4.3 情绪周期判断

**阶段论**：
```
启动 → 分歧 → 主升 → 高潮 → (高潮延续/分歧) → 退潮 → 冰点
```

**各阶段策略**：
- 情绪上升期：参与最强板块的最强个股就是龙头战法
- 情绪下降期：休息
- 震荡期：做试错

---

## 五、现有架构分析

### 5.1 现有策略模块

| 战法 | 实现文件 | 事件类型 | 状态 |
|------|----------|----------|------|
| 竞价战法 | `logic/auction_event_detector.py` | OPENING_WEAK_TO_STRONG<br>OPENING_THEME_SPREAD | ✅ 完整实现 |
| 半路战法 | `logic/halfway_event_detector.py` | HALFWAY_BREAKOUT | ✅ 完整实现 |
| 龙头战法 | `logic/leader_event_detector.py` | LEADER_CANDIDATE | ✅ 完整实现 |
| 低吸战法 | `logic/dip_buy_event_detector.py` | DIP_BUY_CANDIDATE | ✅ 完整实现 |

**三漏斗扫描系统**：
```
全市场5187只
  ↓ Level 1: 技术面粗筛 (QMT)
300-500只异动股
  ↓ Level 2: 资金流向分析 (AkShare)
50-100只精选
  ↓ Level 3: 坑vs机会分类 (TrapDetector)
20-50只最终输出
```

### 5.2 数据流瓶颈

| 环节 | 瓶颈 | 影响 |
|------|------|------|
| AkShare限速 | 60次/分钟 | Level 2资金流分析慢 |
| T+1延迟 | 资金流数据滞后 | 实时决策精度低 |
| DDE异步获取 | 30秒更新间隔 | 数据不够实时 |
| 三漏斗扫描 | 串行处理 | 全市场扫描耗时5-10分钟 |

### 5.3 与愿景的差距

| 维度 | 现状 | 愿景 | 差距 |
|------|------|------|------|
| 实时性 | 30秒监控间隔 | 1秒级实时监控 | ⚠️ 差距大 |
| 智能度 | 规则驱动 | AI驱动 | ⚠️ 差距大 |
| 预警能力 | 事后触发 | 预测性预警 | ⚠️ 差距大 |
| 决策支持 | 手动确认 | 智能决策 | ⚠️ 差距大 |
| 持续学习 | 无 | 自适应优化 | ❌ 无 |

---

## 六、CTO的不同想法

### 6.1 关于顽主杯数据

**CTO的不同观点1：不要过度依赖外部榜单**

**用户观点**：
> "还有锚点 我们要做一个实时版的'顽主杯'"

**我的疑问**：
- 顽主杯榜单本身是T-1数据，已经滞后
- 为什么还要"实时版"？
- 真正的价值不是跟随，而是**预测谁会上榜**

**我的建议**：
```python
# 不是：实时爬取顽主杯榜单（永远慢一步）
# 而是：预测今天谁会上明天的榜单

class WanzhuPredictor:
    def predict_tomorrow_leaders(self):
        """
        基于今日数据，预测明天可能上顽主杯的股票
        """
        # 特征1：今日主力净流入>5000万
        # 特征2：今日涨幅>7%且未涨停
        # 特征3：板块内有其他涨停股（板块共振）
        # 特征4：近3天换手率>10%（活跃度）
        
        candidates = self._filter_by_features()
        predictions = self._rank_by_probability(candidates)
        
        return predictions[:10]  # 预测前10名
```

**CTO的不同观点2：顽主杯是训练集，不是信号源**

**用户观点**：
> "可以用顽主杯数据去优化竞价策略"

**我的建议**：
```python
# Step 1: 用顽主杯数据训练模型
class WanzhuFeatureExtractor:
    def extract_features(self, stock_code, date):
        """
        提取顽主牛股起爆前的特征
        """
        return {
            'main_inflow_before_limit_up': 3000,  # 涨停前主力流入（万）
            'volume_ratio_before_limit_up': 2.5,  # 涨停前量比
            'sector_limit_up_count': 4,          # 板块涨停股数
            'pre_day_open_premium': 0.02,        # 前一日竞价溢价
        }

# Step 2: 用特征优化策略
class OptimizedAuctionStrategy:
    def __init__(self, wanzhu_features):
        # 基于顽主牛股特征，动态调整阈值
        self.inflow_threshold = wanzhu_features['main_inflow_before_limit_up'] * 0.8
        self.volume_ratio_threshold = wanzhu_features['volume_ratio_before_limit_up'] * 0.9
```

### 6.2 关于"实时顽主雷达"

**CTO的不同观点1：攻击波的阈值需要动态调整**

**CTO方案**：
```python
# 条件A: 资金猛（主力净买>1000万 OR 1分钟突袭>300万）
is_big_money = (flow['main_net_inflow'] > 1000) or \
               (flow['1min_inflow'] > 300)
```

**我的疑问**：
- 1000万的阈值是否适合所有股票？
- 贵州茅台和中小盘股票的资金流入规模完全不同
- 是否应该按市值比例设定阈值？

**我的建议**：
```python
class DynamicThresholdManager:
    def calculate_inflow_threshold(self, stock_code, market_cap):
        """
        根据市值动态计算资金流入阈值
        """
        if market_cap > 1000:  # 千亿市值
            # 阈值=市值的0.1%
            return market_cap * 0.001
        elif market_cap > 100:  # 百亿市值
            # 阈值=市值的0.2%
            return market_cap * 0.002
        else:  # 小盘股
            # 阈值=市值的0.5%
            return market_cap * 0.005

    def scan(self, code, tick_data):
        market_cap = get_market_cap(code)
        threshold = self.calculate_inflow_threshold(code, market_cap)
        
        # 动态阈值
        is_big_money = (flow['main_net_inflow'] > threshold)
```

**CTO的不同观点2：需要区分"真攻击"和"假攻击"**

**我的疑问**：
- 1分钟内买入1000万，是真攻击还是诱多？
- 如何避免追在最高点被套？

**我的建议**：
```python
class TrueAttackDetector:
    def is_true_attack(self, code, flow_data):
        """
        判断是真攻击还是假攻击（诱多）
        """
        # 特征1：持续流入（不是一闪而过）
        if not self._check_sustained_inflow(flow_data):
            return False
        
        # 特征2：价格上涨伴随放量（不是对倒）
        if not self._check_volume_price_relationship(flow_data):
            return False
        
        # 特征3：买盘力量>卖盘力量（主力真买）
        if flow_data['main_sell'] > flow_data['main_buy']:
            return False
        
        # 特征4：不是尾盘偷袭（避免尾盘拉升出货）
        if self._is_last_15_minutes():
            return False
        
        return True
```

### 6.3 关于拾荒网知识的应用

**CTO的不同观点1：不要试图一次性实现所有逻辑**

**CTO方案**：
> "选股三板斧实现"
> - 风口判断（板块共振）
> - 股性判断（涨停历史）
> - 主力判断（成本分析）

**我的疑问**：
- 这三个判断都很复杂，是否每个都需要完整的实现？
- 现有的三漏斗扫描已经涵盖了部分逻辑

**我的建议**：
```python
# 不要一次性写完，先用最简版本验证可行性
class SimpleSectorResonance:
    def check_resonance(self, stock_code):
        """
        简化版板块共振判断
        """
        # 只判断：板块内涨停股数>=3
        sector = get_sector(stock_code)
        limit_up_count = count_limit_up_in_sector(sector)
        
        return limit_up_count >= 3

# 验证有效后再增加复杂逻辑
class AdvancedSectorResonance(SimpleSectorResonance):
    def check_resonance(self, stock_code):
        """
        增强版板块共振判断
        """
        # 基础判断
        if not super().check_resonance(stock_code):
            return False
        
        # 增加判断：板块指数连续3日资金净流入
        sector = get_sector(stock_code)
        if not self._check_sustained_inflow(sector, days=3):
            return False
        
        # 增加判断：板块上涨比例>35%
        if not self._check_up_ratio(sector, threshold=0.35):
            return False
        
        return True
```

**CTO的不同观点2：情绪周期判断需要量化指标**

**CTO方案**：
```python
cycle_stages = ['启动', '分歧', '主升', '高潮', '退潮', '冰点']
current_stage = determine_cycle_stage()
```

**我的疑问**：
- 如何量化"启动"、"分歧"等主观概念？
- 不同市场环境下，这些阶段的特征是否一致？

**我的建议**：
```python
class QuantifiedSentimentCycle:
    def calculate_cycle_stage(self):
        """
        量化情绪周期判断
        """
        # 指标1：昨日涨停晋级率
        promotion_rate = self._calculate_promotion_rate()
        
        # 指标2：昨日炸板率
        explosion_rate = self._calculate_explosion_rate()
        
        # 指标3：跌停家数
        limit_down_count = self._count_limit_down()
        
        # 指标4：空间高度（最高板）
        max_limit_up_days = self._get_max_limit_up_days()
        
        # 量化判定规则
        if promotion_rate > 0.8 and max_limit_up_days >= 5:
            return '高潮'
        elif promotion_rate > 0.6 and max_limit_up_days >= 3:
            return '主升'
        elif promotion_rate < 0.3 and limit_down_count > 20:
            return '冰点'
        elif explosion_rate > 0.5:
            return '退潮'
        elif 0.3 <= promotion_rate <= 0.6:
            return '分歧'
        else:
            return '启动'
```

### 6.4 关于回测系统

**CTO的不同观点1：回测结果需要实盘对齐**

**现有问题**：
- 回测成功率不代表实盘成功
- 回测逻辑与实时逻辑不一致

**我的建议**：
```python
class BacktestRealtimeAligner:
    def align_backtest_with_realtime(self, backtest_results):
        """
        对齐回测与实盘的差异
        """
        # 差异1：滑点
        slippage_cost = self._estimate_slippage()
        
        # 差异2：成交失败
        failure_rate = self._estimate_failure_rate()
        
        # 差异3：心理因素
        psychological_factor = self._estimate_psychological_impact()
        
        # 调整回测结果
        adjusted_return = backtest_results['total_return'] * (1 - slippage_cost) * (1 - failure_rate) * (1 - psychological_factor)
        
        return adjusted_return
```

**CTO的不同观点2：回测需要参数敏感性分析**

**现有问题**：
- 不知道参数变化对结果的影响
- 无法找到最优参数组合

**我的建议**：
```python
class ParameterSensitivityAnalyzer:
    def analyze_sensitivity(self, strategy, parameter_ranges):
        """
        参数敏感性分析
        """
        results = []
        
        for param_name, param_range in parameter_ranges.items():
            for param_value in param_range:
                # 运行回测
                backtest_result = strategy.run_with_param(param_name, param_value)
                
                results.append({
                    'param_name': param_name,
                    'param_value': param_value,
                    'return': backtest_result['total_return'],
                    'max_drawdown': backtest_result['max_drawdown'],
                    'win_rate': backtest_result['win_rate']
                })
        
        # 生成敏感性报告
        return self._generate_sensitivity_report(results)
```

---

## 七、核心疑问

### 7.1 关于数据来源

**疑问1：QMT数据是否足够支撑"实时顽主雷达"？**

- QMT提供的是Level-1数据（3秒刷新）
- 能否准确计算"1分钟内主动买入>1000万"？
- 是否需要升级到Level-2数据？

**疑问2：资金流数据如何实时获取？**

- AkShare是T+1延迟
- QMT的资金流数据是否准确？
- 是否需要付费数据源？

### 7.2 关于策略逻辑

**疑问3：如何避免"假攻击"？**

- 1分钟内买入1000万，可能是诱多
- 如何区分真攻击和假攻击？
- 是否需要等待确认信号（如突破前高）？

**疑问4：策略阈值如何设定？**

- 1000万的主力流入阈值是否合理？
- 不同市值的股票，阈值是否应该不同？
- 阈值是否需要动态调整？

### 7.3 关于系统架构

**疑问5：如何平衡实时性和准确性？**

- 1秒级监控会消耗大量资源
- 如何在保证实时性的同时不降低准确性？
- 是否需要分层监控（高频扫描+低频确认）？

**疑问6：多策略组合如何实现？**

- 竞价、半路、龙头、低吸同时触发时，如何选择？
- 是否需要策略评分体系？
- 动态权重如何分配？

---

## 八、下一步行动建议

### 8.1 短期（1-2周）

**优先级P0：建立顽主杯特征库**

```python
# tasks/build_wanzhu_feature_library.py

class WanzhuFeatureLibrary:
    def build_library(self):
        """
        构建顽主杯牛股特征库
        """
        # 1. 收集最近3个月顽主杯前10名
        wanzhu_data = self._collect_wanzhu_data(months=3)
        
        # 2. 提取每只股票起爆前的特征
        features = []
        for stock in wanzhu_data:
            stock_features = self._extract_features(stock)
            features.append(stock_features)
        
        # 3. 分析共同特征
        common_features = self._analyze_common_features(features)
        
        # 4. 生成特征库
        self._save_feature_library(common_features)
        
        return common_features
```

**优先级P0：验证现有回测逻辑**

```python
# tasks/validate_backtest_logic.py

class BacktestValidator:
    def validate(self):
        """
        验证回测逻辑与实时逻辑的一致性
        """
        # 1. 选择最近一周的交易日
        test_dates = self._get_recent_trading_days(days=5)
        
        # 2. 对比回测信号和实时信号
        for date in test_dates:
            backtest_signals = self._get_backtest_signals(date)
            realtime_signals = self._get_realtime_signals(date)
            
            # 3. 计算一致性
            consistency = self._calculate_consistency(backtest_signals, realtime_signals)
            
            print(f"{date}: 一致性 {consistency:.2%}")
        
        return consistency
```

### 8.2 中期（1-2个月）

**优先级P1：实现动态阈值管理**

```python
# logic/dynamic_threshold_manager.py

class DynamicThresholdManager:
    def __init__(self):
        self.historical_data = {}
    
    def update_thresholds(self):
        """
        基于历史数据动态更新阈值
        """
        # 1. 加载最近1个月的数据
        recent_data = self._load_recent_data(months=1)
        
        # 2. 计算各指标的统计分布
        distributions = self._calculate_distributions(recent_data)
        
        # 3. 设定阈值（如：95分位数）
        self.thresholds = {
            'main_inflow': distributions['main_inflow']['p95'],
            'volume_ratio': distributions['volume_ratio']['p95'],
            'price_change': distributions['price_change']['p95']
        }
        
        return self.thresholds
```

**优先级P1：实现策略组合框架**

```python
# logic/strategy_combination.py

class StrategyCombination:
    def __init__(self):
        self.strategies = {
            'auction': AuctionStrategy(),
            'halfway': HalfwayStrategy(),
            'leader': LeaderStrategy(),
            'dip_buy': DipBuyStrategy()
        }
        self.weights = {
            'auction': 0.3,
            'halfway': 0.3,
            'leader': 0.3,
            'dip_buy': 0.1
        }
    
    def generate_combined_signal(self, tick_data, context):
        """
        生成组合策略信号
        """
        signals = {}
        
        # 1. 获取各策略信号
        for name, strategy in self.strategies.items():
            signal = strategy.generate_signal(tick_data, context)
            if signal:
                signals[name] = signal
        
        # 2. 计算组合信号
        if not signals:
            return None
        
        combined_score = sum(
            signals[name]['confidence'] * self.weights[name]
            for name in signals
        )
        
        # 3. 如果组合分数超过阈值，触发信号
        if combined_score > 0.7:
            return {
                'code': tick_data['code'],
                'action': 'BUY',
                'confidence': combined_score,
                'strategies': list(signals.keys())
            }
        
        return None
```

### 8.3 长期（3-6个月）

**优先级P2：实现智能决策引擎**

```python
# logic/intelligent_decision_engine.py

class IntelligentDecisionEngine:
    def __init__(self):
        self.model = self._load_model()
    
    def train_model(self, training_data):
        """
        训练机器学习模型
        """
        # 1. 特征工程
        features = self._feature_engineering(training_data)
        
        # 2. 模型训练
        self.model.fit(features['X'], features['y'])
        
        # 3. 模型评估
        metrics = self._evaluate_model(features['X_test'], features['y_test'])
        
        return metrics
    
    def make_decision(self, tick_data, context):
        """
        智能决策
        """
        # 1. 特征提取
        features = self._extract_features(tick_data, context)
        
        # 2. 模型预测
        prediction = self.model.predict([features])
        
        # 3. 决策
        if prediction[0] == 1:  # 买入
            return {
                'code': tick_data['code'],
                'action': 'BUY',
                'confidence': prediction[1],
                'reason': '智能决策'
            }
        
        return None
```

---

## 九、总结

### 9.1 核心共识

✅ **已达成共识**：
1. 顽主杯数据的价值在于回测优化和情绪锚点
2. 目标是"先于市场发现起爆点"
3. 需要实时资金流监控
4. 需要基于拾荒网知识优化策略

### 9.2 核心分歧

⚠️ **需要进一步讨论**：
1. 是否需要"实时顽主杯"榜单？
2. 攻击波阈值如何动态调整？
3. 如何区分真攻击和假攻击？
4. 情绪周期如何量化判断？
5. 策略组合如何实现？

### 9.3 关键问题

🔴 **需要明确**：
1. QMT数据是否足够支撑实时雷达？
2. 资金流数据如何实时获取？
3. 策略阈值如何设定和优化？
4. 如何平衡实时性和准确性？
5. 回测结果如何与实盘对齐？

### 9.4 下一步行动

**立即执行**：
1. 建立顽主杯特征库
2. 验证回测逻辑
3. 回复核心疑问

**近期执行**：
1. 实现动态阈值管理
2. 实现策略组合框架
3. 优化三漏斗扫描

**长期规划**：
1. 实现智能决策引擎
2. 实现风险预测系统
3. 实现自适应优化

---

**文档生成时间**: 2026-02-14  
**CTO**: AI Assistant  
**状态**: 待团队讨论