---
version: V12.1.0
updated: 2026-02-15
scope: logic/full_market_scanner.py, tasks/run_event_driven_monitor.py
author: MyQuantTool Team
---

# MyQuantTool 项目知识库 V12.1.0

> **版本**: V12.1.0  
> **创建日期**: 2026-02-15  
> **目标**: 为AI团队提供完整的项目理解，确保不再出现基础性错误  
> **CTO**: iFlow CLI

---

## 📚 目录

1. [数据源知识库](#数据源知识库)
2. [战法知识库](#战法知识库)
3. [架构知识库](#架构知识库)
4. [CTO裁决知识库](#cto裁决知识库)
5. [老板核心哲学知识库](#老板核心哲学知识库)
6. [常见错误纠正](#常见错误纠正)
7. [下一步建议](#下一步建议)

---

## 📊 数据源知识库

### QMT数据源

#### 1. QMT Tick数据能力

**API名称**: `get_full_tick()`

**返回字段**:
| 字段名 | 说明 | 数据类型 | 备注 |
|--------|------|----------|------|
| time_str | 时间字符串 | str | 如 "10:30:45" |
| last_price | 最新价 | float | |
| open | 开盘价 | float | |
| high | 最高价 | float | |
| low | 最低价 | float | |
| volume | 成交量 | float | 单位：手 |
| amount | 成交额 | float | 单位：元 |
| p_volume | 成交笔数 | int | |
| ask1 ~ ask5 | 卖盘1-5价格 | float | |
| ask_vol1 ~ ask_vol5 | 卖盘1-5量 | float | 单位：手 |
| bid1 ~ bid5 | 买盘1-5价格 | float | |
| bid_vol1 ~ bid_vol5 | 买盘1-5量 | float | 单位：手 |
| open_int | 持仓量 | float | 期货专用 |
| settle_price | 结算价 | float | 期货专用 |
| upper_limit | 涨停价 | float | |
| lower_limit | 跌停价 | float | |
| pre_close | 昨收价 | float | |

**刷新频率**: 约 **3秒一次**

**数据精度**:
- 价格精度：2位小数（如10.50）
- 成交量精度：整数（手）
- 成交额精度：2位小数

**代码示例**:
```python
from xtquant import xtdata

# 获取单只股票的Tick数据
tick_data = xtdata.get_full_tick(['000001.SZ'])

# 获取多只股票的Tick数据（批量获取）
stock_list = ['000001.SZ', '000002.SZ', '600000.SH']
tick_data = xtdata.get_full_tick(stock_list)

# 访问数据
for code, data in tick_data.items():
    print(f"{code}: 最新价={data['lastPrice']}, 买一价={data['bidPrice'][0]}")
```

#### 2. QMT Level-1数据能力

**特性**:
- ✅ 免费可用
- ✅ 刷新频率：约3秒
- ✅ 买卖盘5档委托
- ✅ 可推断资金流

**局限性**:
- ❌ 无逐笔成交数据
- ❌ 无逐笔委托数据
- ❌ 无法直接获取资金流

**推断资金流方法**:
```python
# 基于Tick数据推断资金流
estimated_main_flow = (
    base_flow * 0.4 +                      # 历史基础 40%
    amount * (bid_pressure - 1.0) * 0.3 +  # 买卖压力 30%
    amount * price_strength * 0.3          # 价格强度 30%
)
```

#### 3. QMT Level-2数据能力

**特性**:
- ❌ 需要VIP权限
- ✅ 刷新频率：毫秒级（500ms-1s）
- ✅ 买卖盘10档委托
- ✅ 逐笔成交数据
- ✅ 逐笔委托数据

**VIP权限**:
- 标准版：可展示Level2行情，但无法在策略中使用
- 增强版：支持在策略中使用Level2行情数据

**CTO裁决**: 
> "够用，但需算法补偿。Level-2虽然逐笔，但成本高且接口复杂。Level-1的3秒快照配合差分算法足够捕捉'脉冲式'资金。"

#### 4. QMT API性能指标

**调用方式**:
- **主动获取**: `get_full_tick(stock_list)` - 主动请求
- **被动订阅**: `subscribe_quote(stock_list, callback)` - 实时推送

**批量获取能力**:
- ✅ 支持批量获取多只股票数据
- ✅ 可一次获取5000+只股票数据
- ✅ 返回字典格式，key为股票代码

**并发能力**:
- QMT API内部已优化，支持高并发调用
- 建议批量调用，减少单次调用次数

**性能要求**:
- 单次调用：<100ms
- 批量调用（100只）：<500ms

#### 5. QMT实时数据延迟

**延迟时间**:
- **Level-1数据**: 约3秒延迟
- **Level-2数据**: 约500ms-1秒延迟

**数据新鲜度**:
- QMT Tick数据比分钟K快20倍
- 适合实时监控和短线交易

#### 6. QMT历史数据完整性

**API名称**: `download_history_data()`

**获取方式**:
```python
# 下载历史数据
xtdata.download_history_data(
    stock_code='000001.SZ',
    period='1d',  # 周期：1d/1m/5m/1w/1M
    start_time='20200101',  # 开始时间
    end_time='20231231'     # 结束时间
)

# 获取本地数据
data = xtdata.get_local_data(
    field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
    stock_list=['000001.SZ'],
    period='1d',
    start_time='20200101',
    end_time='20231231'
)
```

**数据完整性**:
- ✅ 支持分钟级、日线、周线、月线
- ✅ 支持前复权、后复权、不复权
- ✅ 历史数据可追溯到2000年以前

---

### Tushare Pro数据源

#### 1. Tushare积分机制

**重要认知**: 
> ⚠️ **Tushare积分是一个分级门槛，并不消耗积分**

**积分规则**:
- 积分按年计算，不是按次扣费
- 积分只作为API访问权限的门槛
- 调用API不会消耗积分，但受频率限制

**获取方式**:
- 注册新用户：获得100分
- 捐赠：每捐赠1元获得1积分
- 社区贡献：分享代码、文档等

#### 2. 8000积分的权限范围

**权限表格**:
| 积分 | 每分钟调用次数 | 权限范围 |
|------|---------------|----------|
| 120 | 50次 | 8000次总量 |
| 2000以上 | 200次 | 100000次/个API |
| 5000以上 | 500次 | 常规数据无上限 |
| **8000以上** | **500次** | 常规数据无上限 |
| 10000以上 | 500次 | 常规数据无上限，特色数据300次每分钟 |

**8000积分可访问的接口**:
- ✅ 股票基础信息
- ✅ 股票日线行情
- ✅ 股票复权行情
- ✅ 行业板块数据
- ✅ 财务指标数据
- ✅ 宏观经济数据
- ⚠️ 分钟数据需要单独开权限
- ❌ 实时数据需要更高积分

#### 3. Tushare API性能指标

**调用频率限制**:
- 8000积分：500次/分钟
- 2000积分：200次/分钟
- 120积分：50次/分钟

**并发能力**:
- 支持HTTP请求
- 建议使用SDK（Python SDK）
- 可使用连接池优化

**性能要求**:
- 单次调用：<200ms
- 批量调用（100只）：<2s

#### 4. Tushare数据新鲜度

**实时数据延迟**:
- 免费用户：延迟约15分钟以上
- 分钟级数据：需要单独开权限，每分钟更新
- 日线数据：收盘后更新

**历史数据更新频率**:
- 日线数据：收盘后2小时内更新
- 分钟数据：需要付费权限
- 财务数据：每季度更新

#### 5. Tushare历史数据能力

**可获取的数据**:
- ✅ 股票日线行情（复权/不复权）
- ✅ 股票分钟行情（需要权限）
- ✅ 财务指标（季报/年报）
- ✅ 行业板块数据
- ✅ 宏观经济数据
- ✅ 期货期权数据

**数据范围**:
- 股票数据：可追溯到1990年
- 分钟数据：最近3个月（付费）
- 财务数据：可追溯到2000年

**单次提取限制**:
- 分钟数据：单次最大8000行数据
- 日线数据：单次最大3000行数据
- 可通过股票代码和时间循环获取

#### 6. Tushare实盘数据能力

**局限性**:
- ❌ 不支持实盘交易
- ❌ 实时数据有延迟（15分钟+）
- ❌ 分钟数据需要单独开权限

**适用场景**:
- ✅ 历史数据回测
- ✅ 数据分析研究
- ✅ 基本面分析
- ❌ 实时交易决策

---

### AkShare数据源

#### AkShare能力范围

**数据来源**:
- 东方财富网
- 新浪财经
- 腾讯财经
- 同花顺

**可获取的数据**:
- ✅ 实时行情（新浪、腾讯）
- ✅ 资金流数据（东方财富DDE）
- ✅ 热门股票榜单
- ✅ 龙虎榜数据
- ✅ 板块行情

**代码示例**:
```python
import akshare as ak

# 获取实时行情
stock_zh_a_spot_em = ak.stock_zh_a_spot_em()

# 获取DDE资金流
stock_individual_fund_flow = ak.stock_individual_fund_flow(stock="000001", indicator="今日")

# 获取龙虎榜
stock_lhb_detail_em = ak.stock_lhb_detail_em(date="20260214")
```

#### AkShare局限性

**限速问题**:
- **60次/分钟**的API调用限制
- 频繁调用可能被封IP
- 需要使用缓存机制

**数据延迟**:
- DDE数据：T+1延迟
- 资金流数据：T+1延迟
- 实时行情：约3秒延迟

**适用场景**:
- ✅ 获取历史数据（无频率限制）
- ✅ 获取DDE资金流（T+1）
- ❌ 高频实时监控

#### AkShare适用场景

**推荐场景**:
1. **历史数据回测**: 无频率限制，可大量获取
2. **DDE资金流分析**: 东方财富DDE数据质量高
3. **辅助数据获取**: 龙虎榜、热门榜单等
4. **备用数据源**: QMT不可用时降级使用

**不推荐场景**:
1. ❌ 高频实时监控（60次/分钟限制）
2. ❌ 实时资金流分析（T+1延迟）
3. ❌ 大规模全市场扫描

---

## ⚔️ 战法知识库

### 1. 半路战法（Halfway）

#### 目标标的
- **创业板 (300)**: 20cm涨幅
- **科创板 (688)**: 20cm涨幅

#### 涨幅区间
| 股票类型 | 最小涨幅 | 最大涨幅 |
|----------|----------|----------|
| 20cm | 10% | 19.5% |
| 10cm | 5% | 9.5% |

#### 入场条件
1. **平台突破**:
   - 过去30分钟振幅 < 3%
   - 突破平台高点 ≥ 1%
   
2. **成交量放大**:
   - 突破成交量 ≥ 平台期平均量的1.5倍

3. **资金流确认**:
   - QMT Tick初筛：1分钟内主动买入 > 1000万
   - 二筛：ratio（主力净流入/流通市值）达标
   - 三筛：TrapDetector确认不是陷阱

#### 数据源要求
- **Level 1**: QMT Tick数据（3秒刷新）
- **Level 2**: QMT资金流推断（买卖盘压力、价格强度）
- **Level 3**: 东方财富DDE数据（T+1参考）

#### 核心代码
```python
# logic/strategies/halfway_event_detector.py
class HalfwayEventDetector:
    def detect_breakout(self, stock_code, tick_data):
        # 检查平台突破
        platform_volatility = self._calculate_volatility(tick_data, minutes=30)
        if platform_volatility > 0.03:
            return False
        
        # 检查突破幅度
        breakout_strength = (current_price - platform_high) / platform_high
        if breakout_strength < 0.01:
            return False
        
        # 检查成交量放大
        volume_surge = current_volume / platform_avg_volume
        if volume_surge < 1.5:
            return False
        
        return True
```

---

### 2. 龙头战法（Leader）

#### 板块龙头候选
- 同板块内涨幅第一名或Top3且差距<1%
- 涨幅≥5%

#### 竞价弱转强龙头预备
- 高开幅度≥5%
- 竞价量比≥1.5
- 昨日收盘涨幅<3%

#### 日内加速（分时龙头）
- 10分钟内加速
- 加速量比≥1.5

#### 数据源要求
- **Level 1**: QMT Tick数据（实时涨速监控）
- **Level 2**: 板块共振确认（WindFilter）
- **Level 3**: 竞价强弱校验（AuctionStrengthValidator）

#### 核心代码
```python
# logic/strategies/leader_event_detector.py
class LeaderEventDetector:
    def detect_leader_candidate(self, stock_code, sector_data):
        # 检查是否是板块龙头
        rank = self._get_sector_rank(stock_code, sector_data)
        if rank not in [1, 2, 3]:
            return False
        
        # 检查涨幅
        pct_change = self._get_pct_change(stock_code)
        if pct_change < 0.05:
            return False
        
        # 检查龙头差距
        if self._get_leader_gap(stock_code, sector_data) > 0.01:
            return False
        
        return True
```

---

### 3. 资金流分析

#### QMT Tick推断逻辑

**核心公式**:
```python
estimated_main_flow = (
    base_flow * 0.4 +                      # 历史基础 40%
    amount * (bid_pressure - 1.0) * 0.3 +  # 买卖压力 30%
    amount * price_strength * 0.3          # 价格强度 30%
)
```

**bid_pressure计算**:
```python
bid_pressure = (sum(bid_vol) - sum(ask_vol)) / sum(bid_vol + ask_vol)
```

**price_strength计算**:
```python
price_strength = (current_price - prev_close) / prev_close
```

#### 动态阈值管理

**市值分层**:
| 市值分层 | 市值范围 | 阈值比例 |
|----------|----------|----------|
| 小盘股 | < 50亿 | 0.2% |
| 中盘股 | 50-100亿 | 0.1% |
| 大盘股 | 100-1000亿 | 0.05% |
| 超大盘股 | > 1000亿 | 0.02% |

**计算公式**:
```python
main_inflow_threshold = circulating_cap * ratio
```

**示例**:
- 小盘股（30亿市值）：3000万 * 0.2% = 60万
- 中盘股（80亿市值）：8000万 * 0.1% = 80万
- 大盘股（500亿市值）：50000万 * 0.05% = 250万
- 超大盘股（2000亿市值）：200000万 * 0.02% = 400万

#### 真攻击vs假攻击判断

**真攻击特征**:
1. **持续流入**: 不是一闪而过，持续3分钟以上
2. **价格上涨伴随放量**: 不是对倒
3. **买盘力量 > 卖盘力量**: 主力真买
4. **不是尾盘偷袭**: 避免尾盘拉升出货

**假攻击特征**:
1. **一闪而过**: 1分钟内大单买入，之后无后续流入
2. **对倒**: 买卖盘同时挂大单，制造假象
3. **卖盘力量 > 买盘力量**: 主力在出货
4. **尾盘偷袭**: 收盘前拉升，为第二天出货做准备

**真攻击检测代码**:
```python
class TrueAttackDetector:
    def is_true_attack(self, code, flow_data):
        # 特征1：持续流入
        if not self._check_sustained_inflow(flow_data, minutes=3):
            return False
        
        # 特征2：价格上涨伴随放量
        if not self._check_volume_price_relationship(flow_data):
            return False
        
        # 特征3：买盘力量 > 卖盘力量
        if flow_data['main_sell'] > flow_data['main_buy']:
            return False
        
        # 特征4：不是尾盘偷袭
        if self._is_last_15_minutes():
            return False
        
        return True
```

#### 数据源要求
- **QMT Tick**: 实时买卖盘数据（推断资金流）
- **AkShare DDE**: T+1资金流参考
- **Tushare**: 历史资金流数据（回测）

---

### 4. 时机斧（Timing）

#### 板块共振（进攻斧）

**判定条件**:
- **条件A**: 板块内涨停股 ≥ 3只
- **条件B**: 板块内上涨股票占比 ≥ 35%
- **条件C**: 板块指数连续3日资金净流入

**共振判定**:
- 满足至少2个条件才返回True
- 共振分数 = (通过条件的权重和) / 总权重
- 权重: A=0.4, B=0.35, C=0.25

**核心代码**:
```python
# logic/strategies/wind_filter.py
class WindFilter:
    def check_sector_resonance(self, stock_code):
        # 条件A: 涨停股数
        limit_up_count = self.count_limit_up_stocks(industry)
        condition_a_passed = limit_up_count >= 3
        
        # 条件B: 上涨比例
        breadth = self.calculate_rise_breadth(industry)
        condition_b_passed = breadth >= 0.35
        
        # 条件C: 持续流入
        sustained_inflow = self.check_sustained_capital_inflow(industry)
        condition_c_passed = sustained_inflow
        
        # 共振判定（满足至少2个条件）
        passed_conditions = []
        if condition_a_passed: passed_conditions.append('A')
        if condition_b_passed: passed_conditions.append('B')
        if condition_c_passed: passed_conditions.append('C')
        
        is_resonance = len(passed_conditions) >= 2
        
        # 计算共振分数
        weights = {'A': 0.4, 'B': 0.35, 'C': 0.25}
        score = sum(weights.get(c, 0) for c in passed_conditions)
        resonance_score = min(1.0, score)
        
        return {
            'is_resonance': is_resonance,
            'resonance_score': resonance_score,
            'passed_conditions': passed_conditions
        }
```

#### 防守斧（防守斧）

**禁止场景**:
- **TAIL_RALLY**: 尾盘拉升（陷阱）
- **TRAP**: 诱多陷阱

**陷阱特征**:
1. 单日暴量+隔日反手
2. 游资突袭（一闪而过）
3. 对倒（买卖盘同时挂大单）

**核心代码**:
```python
class TrapDetector:
    def detect_trap(self, stock_code, flow_data, price_data):
        # 特征1：单日暴量
        if self._check_surge_volume(price_data):
            return True
        
        # 特征2：游资突袭
        if self._check_flash_attack(flow_data):
            return True
        
        # 特征3：对倒
        if self._check_wash_trading(flow_data):
            return True
        
        return False
```

#### 数据源要求
- **QMT Tick**: 实时涨停股统计
- **AkShare**: 板块资金流数据
- **Tushare**: 板块指数数据

---

## 🏗️ 架构知识库

### 1. 数据抽象层

#### ICapitalFlowProvider接口

**核心原则**: 策略层永远不直接连接数据源，必须通过抽象层

**三层架构**:
```
策略层（半路/龙头/时机斧）
    ↓
抽象层（ICapitalFlowProvider）
    ↓
数据源层（Level2 → Level1 → DongCai）
```

**接口定义**:
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class ICapitalFlowProvider(ABC):
    """资金流数据提供者接口"""
    
    @abstractmethod
    def get_capital_flow(self, stock_code: str) -> Dict[str, Any]:
        """
        获取资金流数据
        
        Returns:
            {
                'main_net_inflow': float,  # 主力净流入
                'main_buy': float,         # 主力买入
                'main_sell': float,        # 主力卖出
                'retail_net_inflow': float, # 散户净流入
                'timestamp': datetime
            }
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查数据源是否可用"""
        pass
```

#### 自动降级机制

**降级策略**:
```
Level-2（付费逐笔）
  ↓ 不可用
Level-1（免费推断）
  ↓ 不可用
DongCai（T-1历史）
```

**降级代码**:
```python
class CapitalFlowProviderFactory:
    def get_provider(self):
        # 优先使用Level-2
        if self._check_level2_available():
            return Level2Provider()
        
        # 降级到Level-1
        if self._check_level1_available():
            return Level1Provider()
        
        # 最后降级到DongCai
        return DongCaiProvider()
```

---

### 2. 事件驱动系统

#### 事件类型

**四大事件**:
1. **OPENING_WEAK_TO_STRONG**: 竞价弱转强
2. **HALFWAY_BREAKOUT**: 半路突破
3. **LEADER_CANDIDATE**: 龙头候选
4. **DIP_BUY_CANDIDATE**: 低吸候选

**事件数据结构**:
```python
{
    'event_type': 'HALFWAY_BREAKOUT',
    'stock_code': '300750',
    'timestamp': datetime(2026, 2, 14, 10, 30),
    'confidence': 0.85,
    'reason': '平台突破 + 成交量放大',
    'data': {
        'breakout_strength': 0.02,
        'volume_surge': 2.5,
        'capital_flow': 5000000
    }
}
```

#### 事件触发机制

**触发流程**:
1. **事件检测器**监听Tick数据
2. 检测到符合条件的信号
3. 生成事件对象
4. 发布到事件总线
5. 策略引擎处理事件

**代码示例**:
```python
class EventPublisher:
    def __init__(self):
        self.subscribers = []
    
    def subscribe(self, event_type, callback):
        """订阅事件"""
        self.subscribers.append((event_type, callback))
    
    def publish(self, event):
        """发布事件"""
        for event_type, callback in self.subscribers:
            if event['event_type'] == event_type:
                callback(event)

# 使用示例
publisher = EventPublisher()
publisher.subscribe('HALFWAY_BREAKOUT', lambda event: print(event))
```

#### 事件处理流程

```
Tick数据到达
  ↓
事件检测器检测
  ↓
生成事件对象
  ↓
发布到事件总线
  ↓
策略引擎订阅处理
  ↓
生成交易信号
  ↓
发送给交易接口
```

---

### 3. 三漏斗扫描系统

#### Level 1: 技术面粗筛（QMT）

**筛选范围**: 全市场5000只股票

**筛选条件**:
- 涨速 > 1%（1分钟内）
- 成交量 > 平台的1.5倍
- 价格在合理区间（半路战法）

**输出**: 300-500只异动股

**代码示例**:
```python
def level1_scan(stock_list):
    results = []
    for stock in stock_list:
        tick_data = get_tick_data(stock)
        
        # 涨速筛选
        if tick_data['pct_change'] < 0.01:
            continue
        
        # 成交量筛选
        if tick_data['volume_surge'] < 1.5:
            continue
        
        results.append(stock)
    
    return results[:500]
```

#### Level 2: 资金流向分析（QMT）

**筛选范围**: Level 1输出的300-500只股票

**筛选条件**:
- 主力净流入 > 动态阈值
- ratio（主力净流入/流通市值）达标
- 真攻击确认（非假攻击）

**输出**: 50-100只精选

**代码示例**:
```python
def level2_scan(stock_list):
    results = []
    for stock in stock_list:
        flow_data = get_capital_flow(stock)
        
        # 动态阈值
        threshold = calculate_dynamic_threshold(stock)
        
        # 主力流入筛选
        if flow_data['main_net_inflow'] < threshold:
            continue
        
        # ratio筛选
        ratio = flow_data['main_net_inflow'] / get_circulating_cap(stock)
        if ratio < 0.001:
            continue
        
        # 真攻击确认
        if not is_true_attack(stock, flow_data):
            continue
        
        results.append(stock)
    
    return results[:100]
```

#### Level 3: 坑vs机会分类（TrapDetector）

**筛选范围**: Level 2输出的50-100只股票

**筛选条件**:
- 非陷阱（Tail Rally、Trap）
- 板块共振确认
- 风险评分 ≤ 0.2

**输出**: 20-50只最终信号

**代码示例**:
```python
def level3_scan(stock_list):
    results = []
    for stock in stock_list:
        # 陷阱检测
        if detect_trap(stock):
            continue
        
        # 板块共振
        resonance = check_sector_resonance(stock)
        if not resonance['is_resonance']:
            continue
        
        # 风险评分
        risk_score = calculate_risk_score(stock)
        if risk_score > 0.2:
            continue
        
        results.append(stock)
    
    return results[:50]
```

#### 性能优化

**分层监控策略**:
- **Layer 1（快速扫描）**: 全市场5000只，只看涨速>1%，每5分钟扫描一次
- **Layer 2（深度确认）**: 对Layer 1筛出来的20-50只，进行毫秒级Tick分析，每30秒扫描一次
- **Layer 3（风险过滤）**: 对Layer 2输出的股票，进行陷阱检测和板块共振确认，每分钟扫描一次

**性能要求**:
- Layer 1: <5分钟扫描全市场
- Layer 2: <30秒分析50只股票
- Layer 3: <10秒过滤50只股票

---

## 📋 CTO裁决知识库

### 1. 数据与基础设施裁决

#### QMT Level-1必须使用推断

**CTO裁决**:
> "QMT提供的是Level-1数据（3秒刷新），能否准确计算'1分钟内主动买入>1000万'？是否需要升级到Level-2数据？"

**裁决结果**: 够用，但需算法补偿

**具体要求**:
- ✅ 必须使用QMT Level-1数据
- ✅ 基于Tick数据推断资金流
- ❌ 禁止降级到分钟K数据
- ✅ Level-2必须是可选的

**推断逻辑**:
```python
estimated_main_flow = (
    base_flow * 0.4 +                      # 历史基础 40%
    amount * (bid_pressure - 1.0) * 0.3 +  # 买卖压力 30%
    amount * price_strength * 0.3          # 价格强度 30%
)
```

#### 资金流数据抽象层封装

**CTO裁决**:
> "策略层必须通过ICapitalFlowProvider接口访问资金流数据，禁止直接调用QMT API"

**具体要求**:
- ✅ 策略层永远不直接连接数据源
- ✅ 必须通过ICapitalFlowProvider接口
- ✅ 实现自动降级机制（Level-2→Level-1→DongCai）

**代码示例**:
```python
# ✅ 正确做法
flow_data = capital_flow_provider.get_capital_flow(stock_code)

# ❌ 错误做法
flow_data = xtdata.get_market_data(...)  # 禁止直接调用QMT API
```

#### 数据源策略自动降级

**CTO裁决**:
> "数据源必须支持自动降级，Level-2→Level-1→DongCai"

**降级策略**:
```python
class CapitalFlowProviderFactory:
    def get_provider(self):
        # 优先使用Level-2
        if self._check_level2_available():
            return Level2Provider()
        
        # 降级到Level-1
        if self._check_level1_available():
            return Level1Provider()
        
        # 最后降级到DongCai
        return DongCaiProvider()
```

#### 数据新鲜度3秒刷新率

**CTO裁决**:
> "Tick数据延迟3秒，比分钟K快20倍，必须使用Tick数据"

**具体要求**:
- ✅ 使用QMT Tick数据（3秒刷新）
- ❌ 禁止使用分钟K数据（300秒刷新）
- ✅ 数据新鲜度是策略的核心竞争力

---

### 2. 策略逻辑裁决

#### 假攻击识别必须区分

**CTO裁决**:
> "1分钟内买入1000万，是真攻击还是诱多？如何避免追在最高点被套？"

**具体要求**:
- ✅ 必须区分真攻击和假攻击
- ✅ 检测持续流入、量价关系、买卖盘力量
- ✅ 避免尾盘偷袭

**真攻击检测**:
```python
class TrueAttackDetector:
    def is_true_attack(self, code, flow_data):
        # 特征1：持续流入（不是一闪而过）
        if not self._check_sustained_inflow(flow_data):
            return False
        
        # 特征2：价格上涨伴随放量（不是对倒）
        if not self._check_volume_price_relationship(flow_data):
            return False
        
        # 特征3：买盘力量 > 卖盘力量（主力真买）
        if flow_data['main_sell'] > flow_data['main_buy']:
            return False
        
        # 特征4：不是尾盘偷袭（避免尾盘拉升出货）
        if self._is_last_15_minutes():
            return False
        
        return True
```

#### 阈值设定必须动态调整

**CTO裁决**:
> "1000万的阈值是否适合所有股票？是否应该按市值比例设定阈值？"

**具体要求**:
- ✅ 根据市值比例设定阈值
- ✅ 禁止固定值
- ✅ 小盘股：0.2%，大盘股：0.02%

**动态阈值计算**:
```python
class DynamicThreshold:
    def calculate_threshold(self, stock_code, market_cap):
        if market_cap > 1000:  # 千亿市值
            return market_cap * 0.0002  # 0.02%
        elif market_cap > 100:  # 百亿市值
            return market_cap * 0.001  # 0.1%
        else:  # 小盘股
            return market_cap * 0.002  # 0.2%
```

#### ratio决策树不可替代

**CTO裁决**:
> "买入决策必须基于ratio（主力净流入/流通市值）"

**具体要求**:
- ✅ 买入决策必须基于ratio
- ✅ ratio = 主力净流入 / 流通市值
- ✅ ratio阈值根据市值分层

**ratio计算**:
```python
ratio = main_net_inflow / circulating_cap

# 阈值设定
if circulating_cap < 50:  # 小盘股
    threshold = 0.002  # 0.2%
elif circulating_cap < 100:  # 中盘股
    threshold = 0.001  # 0.1%
else:  # 大盘股
    threshold = 0.0005  # 0.05%

if ratio > threshold:
    return True
```

#### 诱多检测不可省略

**CTO裁决**:
> "诱多检测不可省略，包括单日暴量+隔日反手、游资突袭、对倒"

**具体要求**:
- ✅ 检测单日暴量+隔日反手
- ✅ 检测游资突袭
- ✅ 检测对倒
- ✅ 禁止Tail Rally场景

**陷阱检测**:
```python
class TrapDetector:
    def detect_trap(self, stock_code, flow_data, price_data):
        # 特征1：单日暴量
        if self._check_surge_volume(price_data):
            return True
        
        # 特征2：游资突袭
        if self._check_flash_attack(flow_data):
            return True
        
        # 特征3：对倒
        if self._check_wash_trading(flow_data):
            return True
        
        return False
```

---

### 3. 系统架构裁决

#### 事件驱动强制要求

**CTO裁决**:
> "检测到事件才扫描，不固定间隔扫描"

**具体要求**:
- ✅ 必须使用事件驱动架构
- ❌ 禁止固定间隔扫描
- ✅ 事件类型：OPENING_WEAK_TO_STRONG, HALFWAY_BREAKOUT, LEADER_CANDIDATE, DIP_BUY_CANDIDATE

**事件驱动架构**:
```python
class EventDrivenScanner:
    def __init__(self):
        self.event_publisher = EventPublisher()
        self.event_detector = EventDetector()
    
    def on_tick(self, tick_data):
        # 检测事件
        event = self.event_detector.detect(tick_data)
        
        if event:
            # 发布事件
            self.event_publisher.publish(event)
```

#### 三把斧体系不可删减

**CTO裁决**:
> "防守斧+时机斧+资金斧，缺一不可"

**具体要求**:
- ✅ 防守斧：禁止Tail Rally/Trap场景
- ✅ 时机斧：板块共振是入场前提
- ✅ 资金斧：真攻击确认
- ❌ 禁止删除任何一个斧头

**三把斧决策**:
```python
def three_axes_decision(stock_code):
    # 时机斧：板块共振
    resonance = check_sector_resonance(stock_code)
    if not resonance['is_resonance']:
        return False
    
    # 资金斧：真攻击确认
    if not is_true_attack(stock_code, flow_data):
        return False
    
    # 防守斧：陷阱检测
    if detect_trap(stock_code, flow_data, price_data):
        return False
    
    return True
```

#### 板块共振是入场前提

**CTO裁决**:
> "板块共振是入场前提，Leaders≥3 + Breadth≥35%，否则降级到观察池"

**具体要求**:
- ✅ 板块共振是入场前提
- ✅ Leaders≥3 + Breadth≥35%
- ✅ 未满足共振时降级到观察池
- ❌ 禁止绕过板块共振检查

**板块共振检查**:
```python
def check_sector_resonance(stock_code):
    # 条件A：板块内涨停股≥3只
    limit_up_count = count_limit_up_in_sector(sector)
    
    # 条件B：板块内上涨股票占比≥35%
    up_count = count_up_stocks_in_sector(sector)
    total_count = count_total_stocks_in_sector(sector)
    breadth = up_count / total_count if total_count > 0 else 0
    
    # 条件C：板块指数连续3日资金净流入
    sector_index_flow = get_sector_index_flow(sector, days=3)
    sustained_inflow = all(flow > 0 for flow in sector_index_flow)
    
    # 共振判定
    is_resonance = (
        limit_up_count >= 3 and
        breadth >= 0.35 and
        sustained_inflow
    )
    
    return is_resonance
```

#### 状态管理必须有指纹对比

**CTO裁决**:
> "只有状态变化才保存快照"

**具体要求**:
- ✅ 使用指纹对比检测状态变化
- ✅ 只有状态变化才保存快照
- ❌ 禁止每次都保存快照

**指纹对比**:
```python
def save_snapshot_if_changed(stock_code, new_state):
    # 计算指纹
    fingerprint = calculate_fingerprint(new_state)
    
    # 检查是否有变化
    last_fingerprint = get_last_fingerprint(stock_code)
    if fingerprint == last_fingerprint:
        return
    
    # 保存快照
    save_snapshot(stock_code, new_state)
    update_fingerprint(stock_code, fingerprint)
```

---

### 4. 核心战略裁决

#### 预测vs爬榜：预测优先

**CTO裁决**:
> "顽主杯榜单本身是T-1数据，已经滞后。为什么还要'实时版'？真正的价值不是跟随，而是**预测谁上榜**。"

**具体要求**:
- ✅ 预测今天谁上明天的榜单
- ❌ 禁止实时爬取顽主杯榜单
- ✅ 顽主杯是训练集，不是信号源

**预测逻辑**:
```python
class WanzhuPredictor:
    def predict_tomorrow_leaders(self):
        # 特征1：今日主力净流入>5000万
        # 特征2：今日涨幅>7%且未涨停
        # 特征3：板块内有其他涨停股（板块共振）
        # 特征4：近3天换手率>10%（活跃度）
        
        candidates = self._filter_by_features()
        predictions = self._rank_by_probability(candidates)
        
        return predictions[:10]  # 预测前10名
```

#### 实战导向：数据为王

**CTO裁决**:
> "没有数据验证，所有逻辑都是纸上谈兵"

**具体要求**:
- ✅ 所有逻辑必须有数据验证
- ✅ 回测结果必须与实盘对齐
- ❌ 禁止未经验证的逻辑

**数据验证流程**:
```python
def validate_strategy(strategy, historical_data):
    # 运行回测
    backtest_results = strategy.run_backtest(historical_data)
    
    # 验证指标
    if backtest_results['win_rate'] < 0.3:
        return False
    
    if backtest_results['max_drawdown'] > -0.05:
        return False
    
    return True
```

#### 风控第一：保命防线

**CTO裁决**:
> "宁可错过机会，不要踩雷"

**具体要求**:
- ✅ 止损策略：-5%（硬止损）
- ✅ 止盈策略：根据信号止盈
- ✅ 风险评分：≤0.2
- ❌ 禁止无止损交易

**风控规则**:
```python
def risk_control(position, current_price, stop_loss_price):
    # 硬止损：-5%
    if current_price < stop_loss_price:
        return 'SELL'
    
    # 风险评分
    risk_score = calculate_risk_score(position)
    if risk_score > 0.2:
        return 'SELL'
    
    # 主力资金大量流出
    if position['main_net_inflow'] < -50000000:
        return 'SELL'
    
    return 'HOLD'
```

---

## 💰 老板核心哲学知识库

### 1. 核心哲学

#### 宁可停止，不要错误

**核心观点**:
> "宁可停止交易，不要犯错误"

**具体表现**:
- ✅ 止损线：-5%（硬止损）
- ✅ 风控第一：保命防线
- ❌ 禁止无止损交易
- ❌ 禁止侥幸心理

#### 绝对精度 > 灾备能力

**核心观点**:
> "绝对精度比灾备能力更重要"

**具体表现**:
- ✅ 数据精度：2位小数
- ✅ 时间精度：秒级
- ✅ 计算精度：动态阈值
- ❌ 禁止模糊计算

#### 本地私有化程序，只对老板的资金负责

**核心观点**:
> "不是面向客户的产品，只对老板的资金负责"

**具体表现**:
- ✅ 本地部署，不使用云端
- ✅ 数据本地化，不依赖外部
- ✅ 策略私有化，不分享
- ❌ 禁止使用第三方平台

#### 不是面向客户的产品

**核心观点**:
> "这是私人量化交易系统，不是面向客户的产品"

**具体表现**:
- ✅ 功能定制化，针对老板需求
- ✅ 无UI美化，功能优先
- ✅ 无用户文档，内部使用
- ❌ 禁止过度开发

---

### 2. 盈利目标

#### 单只股票：30%-50%（理想目标）

**核心观点**:
> "单只股票的理想盈利目标是30%-50%"

**具体表现**:
- ✅ 止盈策略：根据信号止盈
- ✅ 主力资金大量流出 → 提前止盈
- ✅ 上涨动力丧失 → 提前止盈
- ❌ 禁止死板止盈

**止盈策略**:
```python
def calculate_take_profit(stock_code, buy_price, current_price, flow_data):
    profit_rate = (current_price - buy_price) / buy_price
    
    # 基础止盈：+30%
    base_take_profit = buy_price * 1.30
    
    # 条件1：主力资金大量流出 → 提前止盈
    if flow_data['main_net_inflow'] < -50000000:
        return current_price  # 立即止盈
    
    # 条件2：上涨动力丧失 → 提前止盈
    if check_price_volume_divergence(flow_data):
        return current_price  # 立即止盈
    
    # 条件3：情绪周期处于高潮 → 延长止盈
    sentiment_stage = get_sentiment_cycle_stage()
    if sentiment_stage in ['高潮', '主升'] and profit_rate > 0.20:
        return buy_price * 1.50  # +50%止盈
    
    return base_take_profit
```

#### 月度账户：30%-50%（理想目标）

**核心观点**:
> "月度账户的理想盈利目标是30%-50%"

**具体表现**:
- ✅ 单月胜率：35%+
- ✅ 单月交易次数：40-50次
- ✅ 单月最大回撤：-2.0%以下
- ❌ 禁止过度交易

#### 止盈策略：根据信号止盈

**核心观点**:
> "止盈根据信号去止盈，如主力资金大量流出等，上涨动力已经缺乏。不是死板的30-50%。"

**具体表现**:
- ✅ 主力资金大量流出 → 提前止盈
- ✅ 上涨动力丧失 → 提前止盈
- ✅ 情绪周期变化 → 动态止盈
- ❌ 禁止死板止盈

#### 止损策略：-5%（硬止损）

**核心观点**:
> "止损策略是-5%（硬止损），但实际根据资金流和趋势判断"

**具体表现**:
- ✅ 硬止损：-5%
- ✅ 软止损：根据资金流和趋势判断
- ✅ 主力资金大量流出 → 提前止损
- ❌ 禁止无止损交易

**止损策略**:
```python
def calculate_stop_loss(stock_code, buy_price, current_price, flow_data):
    # 基础止损：-5%
    base_stop_loss = buy_price * 0.95
    
    # 条件1：主力资金大量流出 → 提前止损
    if flow_data['main_net_inflow'] < -50000000:
        return buy_price * 0.97  # -3%止损
    
    # 条件2：情绪周期处于退潮/冰点 → 提前止损
    sentiment_stage = get_sentiment_cycle_stage()
    if sentiment_stage in ['退潮', '冰点']:
        return buy_price * 0.96  # -4%止损
    
    # 条件3：板块共振失效 → 提前止损
    sector_resonance = check_sector_resonance(stock_code)
    if not sector_resonance['is_resonance']:
        return buy_price * 0.97  # -3%止损
    
    return base_stop_loss
```

---

### 3. 交易哲学

#### 赚钱快，小资金效率高

**核心观点**:
> "赚钱快，小资金效率高"

**具体表现**:
- ✅ 目标标的：创业板300 + 科创板688
- ✅ 涨幅区间：20cm（10%-19.5%），10cm（5%-9.5%）
- ✅ 持仓时间：根据信号动态调整
- ❌ 禁止长期持有

#### 无任何特殊要求

**核心观点**:
> "无任何特殊要求"

**具体表现**:
- ✅ 交易频率：无特殊要求
- ✅ 持仓时间：无特殊要求
- ✅ 交易数量：无特殊要求
- ✅ 唯一标准：赚钱快

#### 唯一要求是赚钱快

**核心观点**:
> "唯一要求是赚钱快，小资金效率要高"

**具体表现**:
- ✅ 单只股票：30%-50%
- ✅ 月度账户：30%-50%
- ✅ 胜率：35%+
- ✅ 最大回撤：-2.0%以下

---

## ❌ 常见错误纠正

### 1. 我之前错误说法的纠正

#### 错误说法1：QMT没有资金流数据

**正确说法**: QMT没有直接的资金流API，但可以通过Tick推断

**纠正**:
```python
# ❌ 错误说法
"QMT没有资金流数据"

# ✅ 正确说法
"QMT没有直接的资金流API，但可以通过Tick推断资金流"
```

#### 错误说法2：Tushare积分是按次扣费

**正确说法**: Tushare积分是一个分级门槛，并不消耗积分

**纠正**:
```python
# ❌ 错误说法
"Tushare积分是按次扣费的"

# ✅ 正确说法
"Tushare积分是一个分级门槛，并不消耗积分，只受频率限制"
```

#### 错误说法3：需要升级到Level-2数据

**正确说法**: Level-1够用，但需算法补偿

**纠正**:
```python
# ❌ 错误说法
"需要升级到Level-2数据"

# ✅ 正确说法
"Level-1够用，但需算法补偿。Level-1的3秒快照配合差分算法足够捕捉'脉冲式'资金"
```

#### 错误说法4：1000万的阈值适用于所有股票

**正确说法**: 阈值必须根据市值动态调整

**纠正**:
```python
# ❌ 错误说法
"1000万的阈值适用于所有股票"

# ✅ 正确说法
"阈值必须根据市值动态调整，小盘股0.2%，大盘股0.02%"
```

#### 错误说法5：顽主杯榜单是信号源

**正确说法**: 顽主杯是训练集，不是信号源

**纠正**:
```python
# ❌ 错误说法
"顽主杯榜单是信号源"

# ✅ 正确说法
"顽主杯是训练集，不是信号源。真正的价值是预测谁上榜，而不是跟随"
```

---

### 2. 正确理解的技术细节

#### QMT Tick数据能力

**正确理解**:
- ✅ QMT Tick数据包含买卖盘5档委托
- ✅ QMT Tick数据刷新频率约3秒
- ✅ QMT Tick数据可以推断资金流
- ✅ QMT Tick数据支持批量获取5000+只股票
- ❌ QMT Tick数据没有逐笔成交数据（需要Level-2）

#### Tushare积分机制

**正确理解**:
- ✅ Tushare积分是一个分级门槛，并不消耗积分
- ✅ 8000积分每分钟可以调用500次
- ✅ 分钟数据需要单独开权限
- ❌ Tushare积分不是按次扣费

#### 战法多级筛选逻辑

**正确理解**:
- ✅ Level 1：技术面粗筛（QMT）
- ✅ Level 2：资金流向分析（QMT）
- ✅ Level 3：坑vs机会分类（TrapDetector）
- ❌ 不是单级筛选，而是三级过滤

#### Fail-Safe机制设计

**正确理解**:
- ✅ 数据源自动降级（Level-2→Level-1→DongCai）
- ✅ 动态阈值管理（根据市值、时间、情绪）
- ✅ 真攻击检测（区分真攻击和假攻击）
- ❌ 不是单点故障，而是多层防护

---

### 3. 避免再次犯错的注意事项

#### 注意事项1：永远不要绕过数据抽象层

**铁律5**: 策略层必须永远不直接连接数据源，必须通过抽象层

**正确做法**:
```python
# ✅ 正确做法
flow_data = capital_flow_provider.get_capital_flow(stock_code)

# ❌ 错误做法
flow_data = xtdata.get_market_data(...)  # 禁止直接调用QMT API
```

#### 注意事项2：永远不要使用固定阈值

**CTO建议**: 阈值必须动态调整，根据市值、时间、情绪

**正确做法**:
```python
# ✅ 正确做法
threshold = dynamic_threshold.calculate_threshold(stock_code, current_time, sentiment_stage)

# ❌ 错误做法
threshold = 10000000  # 固定值1000万
```

#### 注意事项3：永远不要忽略板块共振检查

**铁律4**: 板块共振是入场前提

**正确做法**:
```python
# ✅ 正确做法
resonance = wind_filter.check_sector_resonance(stock_code)
if not resonance['is_resonance']:
    return False

# ❌ 错误做法
# 直接跳过板块共振检查
```

#### 注意事项4：永远不要省略陷阱检测

**CTO建议**: 诱多检测不可省略

**正确做法**:
```python
# ✅ 正确做法
if trap_detector.detect_trap(stock_code, flow_data, price_data):
    return False

# ❌ 错误做法
# 直接跳过陷阱检测
```

#### 注意事项5：永远不要使用Tushare作为实时数据源

**正确理解**: Tushare免费用户延迟约15分钟以上

**正确做法**:
```python
# ✅ 正确做法
# 使用QMT作为实时数据源
tick_data = qmt_manager.get_full_tick(stock_list)

# ❌ 错误做法
# 使用Tushare作为实时数据源
tick_data = tushare.get_tick(stock_code)  # 延迟15分钟+
```

---

## 🚀 下一步建议

### 1. 如何使用知识库

#### 知识库使用流程

1. **阅读理解**: 先通读整个知识库，理解项目架构和技术细节
2. **重点标注**: 对重点内容进行标注，如CTO裁决、铁律等
3. **定期回顾**: 每次开发前回顾相关部分，避免犯错
4. **持续更新**: 随着项目迭代，持续更新知识库

#### 知识库使用建议

- ✅ 开发前先阅读相关部分
- ✅ 遇到问题时先查知识库
- ✅ 发现错误时及时更新知识库
- ❌ 不要完全依赖记忆，知识库是权威来源

---

### 2. 如何验证知识库的准确性

#### 验证方法1：回测验证

**验证流程**:
1. 使用知识库中的逻辑运行回测
2. 对比回测结果与实际结果
3. 如果不一致，检查知识库是否正确

**代码示例**:
```python
# 验证动态阈值逻辑
backtest_results = run_backtest(
    strategy='dynamic_threshold',
    date_range='2024-01-01 to 2024-12-31'
)

if backtest_results['win_rate'] < 0.35:
    print("动态阈值逻辑可能有问题，需要检查知识库")
```

#### 验证方法2：实盘验证

**验证流程**:
1. 使用知识库中的逻辑进行实盘交易
2. 对比实盘结果与预期结果
3. 如果不一致，检查知识库是否正确

**代码示例**:
```python
# 验证板块共振逻辑
realtime_results = run_realtime(
    strategy='wind_filter',
    duration='1 week'
)

if realtime_results['resonance_accuracy'] < 0.8:
    print("板块共振逻辑可能有问题，需要检查知识库")
```

#### 验证方法3：代码审查

**验证流程**:
1. 阅读项目代码，检查是否与知识库一致
2. 如果不一致，检查知识库是否正确
3. 如果知识库错误，更新知识库

**代码示例**:
```python
# 检查是否绕过数据抽象层
# 搜索 xtdata.get_market_data
if search_code('xtdata.get_market_data'):
    print("发现绕过数据抽象层的代码，需要检查知识库")
```

---

### 3. 如何更新知识库

#### 更新触发条件

1. **代码变更**: 当代码逻辑发生变化时
2. **CTO裁决**: 当有新的CTO裁决时
3. **错误发现**: 当发现知识库错误时
4. **需求变更**: 当有新的需求时

#### 更新流程

1. **识别变更**: 识别需要更新的部分
2. **编写内容**: 编写新的知识库内容
3. **验证准确性**: 验证新内容的准确性
4. **提交审核**: 提交CTO审核
5. **发布更新**: 审核通过后发布更新

#### 更新模板

```markdown
## [章节名称] [更新日期]

### 更新原因
[描述更新的原因]

### 更新内容
[描述更新的内容]

### 验证方法
[描述如何验证更新的准确性]

### 相关代码
[列出相关的代码文件]
```

---

### 4. 知识库维护建议

#### 维护频率

- **日常维护**: 每周检查一次，确保知识库与代码一致
- **重大更新**: 每次重大功能更新后，更新知识库
- **错误修复**: 发现错误后立即修复

#### 维护责任

- **CTO**: 负责审核知识库更新
- **开发团队**: 负责更新知识库内容
- **测试团队**: 负责验证知识库准确性

#### 维护工具

- **版本控制**: 使用Git进行版本控制
- **变更记录**: 记录每次更新的原因和内容
- **审核流程**: 建立审核流程，确保准确性

---

## 📝 总结

### 核心发现

1. **CTO核心裁决**:
   - 数据与基础设施：必须使用QMT Level-1推断，数据抽象层封装
   - 策略逻辑：必须区分真攻击和假攻击，动态调整阈值
   - 系统架构：事件驱动、三把斧完整、板块共振、状态指纹
   - 核心战略：预测优先，顽主杯是训练集不是信号源

2. **数据源能力**:
   - QMT Tick：3秒刷新，可推断资金流，支持批量获取
   - Tushare：积分不消耗，8000积分每分钟500次，免费用户延迟15分钟
   - AkShare：60次/分钟限制，T+1延迟，适合回测

3. **战法逻辑**:
   - 半路战法：创业板300 + 科创板688，涨幅10%-19.5%（20cm）或5%-9.5%（10cm）
   - 龙头战法：板块龙头候选，竞价弱转强龙头预备，日内加速
   - 资金流分析：QMT Tick推断，动态阈值管理，真攻击vs假攻击判断
   - 时机斧：板块共振，防守斧

4. **架构设计**:
   - 数据抽象层：ICapitalFlowProvider接口，三层架构，自动降级
   - 事件驱动：检测到事件才扫描，四大事件类型
   - 三漏斗扫描：技术面粗筛 → 资金流向分析 → 坑vs机会分类

5. **老板核心哲学**:
   - 宁可停止，不要错误
   - 绝对精度 > 灾备能力
   - 本地私有化程序，只对老板的资金负责
   - 不是面向客户的产品

### 下一步行动

**立即执行**:
1. [ ] 通读知识库，理解所有内容
2. [ ] 标注重点内容（CTO裁决、铁律等）
3. [ ] 验证知识库的准确性

**近期执行**:
4. [ ] 检查代码是否与知识库一致
5. [ ] 修复绕过数据抽象层的代码
6. [ ] 更新固定阈值的代码

**长期规划**:
7. [ ] 建立知识库维护流程
8. [ ] 建立知识库审核流程
9. [ ] 建立知识库更新流程

---

**文档生成时间**: 2026-02-15  
**CTO**: iFlow CLI  
**版本**: V12.1.0  
**状态**: 待团队讨论和CTO批准  
**预计完成时间**: 持续更新

---

## 📞 联系方式

如有任何问题或建议，请联系CTO（iFlow CLI）。