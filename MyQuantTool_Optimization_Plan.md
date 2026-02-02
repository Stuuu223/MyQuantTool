# MyQuantTool 系统化优化方案

**生成时间**: 2026-02-02 19:34  
**目标**: 从"手动分析工具"升级为"诱多陷阱识别系统"  
**基础**: commit e234a21 架构分析  
**结合案例**: 300997（诱多识别失败）、603697（游资判断困难）

---

## 🎯 核心问题诊断

### 问题 1: 数据层缺陷（60分 → 85分目标）

**现状**:
```python
# 当前的 JSON 输出（来自 300997/603697 案例）
{
  "fund_flow": {
    "daily_data": [
      {
        "date": "2026-02-02",
        "institution": 5025.1,
        "signal": "吸筹"  # ← 太简单，无法判断"游资 vs 庄家"
      }
    ]
  }
}
```

**问题**:
- ✗ 无法区分"单日诱多 vs 持续吸筹"
- ✗ 无法判断"游资 vs 长线资金"
- ✗ 无法预警"异常流入"

**目标**:
```python
{
  "fund_flow": {
    "daily_data": [
      {
        "date": "2026-02-02",
        "institution": 5025.1,
        "signal": "吸筹",
        
        # 新增：诱多识别关键指标
        "inflow_level": "MEGA",           # TINY/SMALL/MEDIUM/LARGE/MEGA
        "rolling_5d_net": -317.54,        # 5日累计
        "rolling_10d_net": -1043.98,      # 10日累计
        "inflow_rank_90d": 0.92,          # 排名（百分位）
        
        # 新增：资金性质判断
        "capital_type": "HOT_MONEY",      # INSTITUTIONAL/LONG_TERM/HOT_MONEY
        "capital_confidence": 0.65,       # 判断置信度
        
        # 新增：异常检测
        "anomalies": [
          {
            "type": "MEGA_INFLOW_AFTER_LONG_OUTFLOW",
            "severity": "CRITICAL",
            "desc": "90天累计流出后单日巨量流入"
          }
        ],
        "trap_risk_score": 0.85           # 诱多风险评分 0-1
      }
    ]
  }
}
```

---

### 问题 2: 分析逻辑缺陷（50分 → 90分目标）

**现状**:
```python
# enhanced_stock_analyzer.py 当前逻辑
def comprehensive_analysis(self):
    # 只做单日分析
    if institution > 0:
        signal = "吸筹"
    else:
        signal = "接盘"
    
    # 没有时序对比
    # 没有异常检测
    # 没有诱多识别
```

**问题**:
- ✗ 看不到"隔日反手卖"的诱多套路
- ✗ 看不到"滚动流入趋势"
- ✗ 所有"吸筹"信号一视同仁

**目标**:
```python
def enhanced_comprehensive_analysis(self):
    # 1. 基础分析（保留）
    basic_signal = self._get_basic_signal()
    
    # 2. 诱多陷阱检测（新增）
    trap_signals = self._detect_pump_traps()
    
    # 3. 资金性质分类（新增）
    capital_type = self._classify_capital_type()
    
    # 4. 异常预警（新增）
    anomalies = self._detect_anomalies()
    
    # 5. 综合评分（新增）
    risk_score = self._calculate_trap_risk()
    
    return {
        'basic': basic_signal,
        'trap_detection': trap_signals,
        'capital_type': capital_type,
        'anomalies': anomalies,
        'risk_score': risk_score
    }
```

---

### 问题 3: 架构职责混乱（40分 → 80分目标）

**现状架构问题**:
```
enhanced_stock_analyzer.py:
  - 数据获取 ← 应该在独立的 data_fetcher 里
  - 指标计算 ← OK
  - 信号分析 ← OK
  - 诱多识别 ← 缺失
  - 风险评分 ← 缺失
  
职责过重，且缺少核心模块
```

**目标架构**:
```
新增模块:
  1. trap_detector.py        ← 诱多陷阱检测器
  2. capital_classifier.py   ← 资金性质分类器
  3. anomaly_detector.py     ← 异常检测器
  4. risk_scorer.py          ← 风险评分器
  
改进模块:
  1. enhanced_stock_analyzer.py ← 减负，只管指标计算
  2. stock_ai_tool.py           ← 加入新分析模式
```

---

## 🔧 详细优化方案

### 优化 1: 新增"诱多陷阱检测器"模块

**文件**: `logic/trap_detector.py`

**功能**: 识别 300997/603697 中的诱多套路

**核心逻辑**:
```python
class TrapDetector:
    """
    诱多陷阱检测器
    
    识别模式:
    1. 单日大额吸筹 + 隔日反手卖 = 诱多
    2. 长期流出 + 单日巨量流入 = 可能是游资
    3. 超大单主导（>70%） + 散户恐慌 = 对倒风险
    """
    
    def detect_pump_and_dump(self, daily_data: list[dict]) -> dict:
        """检测"吸筹-反手卖"诱多模式"""
        
        if len(daily_data) < 2:
            return {'detected': False}
        
        prev_day = daily_data[-2]
        curr_day = daily_data[-1]
        
        # 特征 1: 前一天大额吸筒
        big_inflow = prev_day['institution'] > 5000
        
        # 特征 2: 当天反手卖出
        big_outflow = curr_day['institution'] < -2000
        
        # 特征 3: 前一天涨幅明显
        price_surge = prev_day.get('pct_chg', 0) > 2.0
        
        if big_inflow and big_outflow and price_surge:
            return {
                'detected': True,
                'type': 'PUMP_AND_DUMP',
                'confidence': 0.85,
                'inflow_day': prev_day['date'],
                'inflow_amount': prev_day['institution'],
                'dump_day': curr_day['date'],
                'dump_amount': curr_day['institution'],
                'evidence': f"前日吸筒{prev_day['institution']:.2f}万，今日反手卖{curr_day['institution']:.2f}万"
            }
        
        return {'detected': False}
    
    def detect_hot_money_raid(self, daily_data: list[dict], window=30) -> dict:
        """检测"游资突袭"模式（603697案例）"""
        
        if len(daily_data) < window:
            return {'detected': False}
        
        recent = daily_data[-window:]
        latest = daily_data[-1]
        
        # 计算前 29 天的累计流向
        cumulative_before = sum(d['institution'] for d in recent[:-1])
        
        # 最后一天的流入
        latest_inflow = latest['institution']
        
        # 特征：长期流出后，单日巨量流入
        if cumulative_before < -5000 and latest_inflow > 3000:
            # 计算"填坑率"
            fill_ratio = latest_inflow / abs(cumulative_before)
            
            return {
                'detected': True,
                'type': 'HOT_MONEY_RAID',
                'confidence': 0.70,
                'cumulative_outflow': cumulative_before,
                'single_day_inflow': latest_inflow,
                'fill_ratio': fill_ratio,
                'evidence': f"{window-1}天累计流出{cumulative_before:.2f}万，今日单日流入{latest_inflow:.2f}万（填坑率{fill_ratio*100:.1f}%）"
            }
        
        return {'detected': False}
    
    def detect_self_trading(self, daily_data: list[dict]) -> dict:
        """检测"对倒"风险"""
        
        latest = daily_data[-1]
        
        # 特征：超大单占比过高（>70%）
        super_large = abs(latest.get('super_large', 0))
        total_flow = abs(latest['institution'])
        
        if total_flow > 0:
            super_large_ratio = super_large / total_flow
            
            if super_large_ratio > 0.7 and total_flow > 3000:
                return {
                    'detected': True,
                    'type': 'SELF_TRADING_RISK',
                    'confidence': 0.60,
                    'super_large_ratio': super_large_ratio,
                    'evidence': f"超大单占比{super_large_ratio*100:.1f}%，可能存在对倒"
                }
        
        return {'detected': False}
    
    def comprehensive_trap_scan(self, daily_data: list[dict]) -> list[dict]:
        """综合扫描所有陷阱模式"""
        
        traps = []
        
        # 检测 1: 诱多
        pump_dump = self.detect_pump_and_dump(daily_data)
        if pump_dump['detected']:
            traps.append(pump_dump)
        
        # 检测 2: 游资突袭
        hot_money = self.detect_hot_money_raid(daily_data)
        if hot_money['detected']:
            traps.append(hot_money)
        
        # 检测 3: 对倒风险
        self_trade = self.detect_self_trading(daily_data)
        if self_trade['detected']:
            traps.append(self_trade)
        
        return traps
```

---

### 优化 2: 新增"滚动指标计算"功能

**文件**: `logic/rolling_metrics.py`

**功能**: 计算 flow_5d_net, flow_10d_net 等关键指标

```python
class RollingMetricsCalculator:
    """滚动指标计算器"""
    
    @staticmethod
    def add_rolling_metrics(daily_data: list[dict]) -> list[dict]:
        """为每日数据添加滚动指标"""
        
        enriched = []
        
        for i, record in enumerate(daily_data):
            # 复制原始数据
            enhanced = record.copy()
            
            # 计算滚动净流入
            if i >= 4:  # 至少5天
                flow_5d = sum(daily_data[j]['institution'] for j in range(i-4, i+1))
                enhanced['flow_5d_net'] = flow_5d
            else:
                enhanced['flow_5d_net'] = None
            
            if i >= 9:  # 至少10天
                flow_10d = sum(daily_data[j]['institution'] for j in range(i-9, i+1))
                enhanced['flow_10d_net'] = flow_10d
            else:
                enhanced['flow_10d_net'] = None
            
            if i >= 19:  # 至少20天
                flow_20d = sum(daily_data[j]['institution'] for j in range(i-19, i+1))
                enhanced['flow_20d_net'] = flow_20d
            else:
                enhanced['flow_20d_net'] = None
            
            # 计算当前流入的排名（百分位）
            all_flows = [d['institution'] for d in daily_data[:i+1]]
            if all_flows:
                rank = sum(1 for f in all_flows if f < record['institution']) / len(all_flows)
                enhanced['inflow_rank_percentile'] = rank
            else:
                enhanced['inflow_rank_percentile'] = 0.5
            
            enriched.append(enhanced)
        
        return enriched
```

---

### 优化 3: 新增"资金性质分类器"模块

**文件**: `logic/capital_classifier.py`

**功能**: 判断是"庄家"还是"游资"还是"长线资金"

```python
class CapitalClassifier:
    """
    资金性质分类器
    
    分类标准:
    - INSTITUTIONAL（机构）: 持续小额吸筒，5日+10日均为正
    - LONG_TERM（长线）: 累计大额流入，持续时间>20天
    - HOT_MONEY（游资）: 单日巨量，前后无连续性
    - UNCLEAR（不明确）: 无法判断
    """
    
    def classify(self, daily_data: list[dict], window=30) -> dict:
        """分类当前资金性质"""
        
        if len(daily_data) < window:
            return {'type': 'UNCLEAR', 'confidence': 0}
        
        recent = daily_data[-window:]
        latest = daily_data[-1]
        
        # 计算滚动指标
        flow_5d = sum(d['institution'] for d in daily_data[-5:])
        flow_10d = sum(d['institution'] for d in daily_data[-10:])
        flow_20d = sum(d['institution'] for d in daily_data[-20:])
        flow_30d = sum(d['institution'] for d in daily_data[-30:])
        
        latest_inflow = latest['institution']
        
        # 规则 1: 长线资金（稳定持续流入）
        if flow_5d > 0 and flow_10d > 0 and flow_20d > 0:
            if latest_inflow > 0 and latest_inflow < flow_10d / 5:
                return {
                    'type': 'LONG_TERM',
                    'confidence': 0.80,
                    'evidence': f"5/10/20日滚动均为正流入，单日{latest_inflow:.2f}万符合持续模式"
                }
        
        # 规则 2: 游资（单日巨量，前后无连续）
        if latest_inflow > 3000:
            if flow_10d < 0 or flow_20d < -5000:
                return {
                    'type': 'HOT_MONEY',
                    'confidence': 0.75,
                    'evidence': f"单日巨量{latest_inflow:.2f}万，但10日累计{flow_10d:.2f}万（前期流出）"
                }
        
        # 规则 3: 机构（中等规模持续吸筒）
        if 0 < flow_5d < 2000 and flow_10d > 0:
            inflow_days = sum(1 for d in recent[-10:] if d['institution'] > 100)
            if inflow_days >= 6:
                return {
                    'type': 'INSTITUTIONAL',
                    'confidence': 0.70,
                    'evidence': f"10日内{inflow_days}天流入，5日累计{flow_5d:.2f}万（稳健模式）"
                }
        
        # 默认：不明确
        return {
            'type': 'UNCLEAR',
            'confidence': 0.40,
            'evidence': "资金流向无明显模式"
        }
```

---

### 优化 4: 修改现有的 `enhanced_stock_analyzer.py`

**核心改动**: 集成新模块

```python
# 在 enhanced_stock_analyzer.py 中添加

from logic.trap_detector import TrapDetector
from logic.capital_classifier import CapitalClassifier
from logic.rolling_metrics import RollingMetricsCalculator

class EnhancedStockAnalyzer:
    
    def __init__(self):
        # 原有初始化
        ...
        
        # 新增：诱多检测器
        self.trap_detector = TrapDetector()
        self.capital_classifier = CapitalClassifier()
        self.rolling_calculator = RollingMetricsCalculator()
    
    def comprehensive_analysis(self, stock_code, days=90):
        """增强版综合分析"""
        
        # 1. 获取原始数据（保留原有逻辑）
        fund_flow_data = self._get_fund_flow(stock_code, days)
        qmt_data = self._get_qmt_data(stock_code, days)
        
        # 2. 新增：计算滚动指标
        fund_flow_data['daily_data'] = self.rolling_calculator.add_rolling_metrics(
            fund_flow_data['daily_data']
        )
        
        # 3. 新增：诱多陷阱检测
        traps = self.trap_detector.comprehensive_trap_scan(
            fund_flow_data['daily_data']
        )
        
        # 4. 新增：资金性质分类
        capital_type = self.capital_classifier.classify(
            fund_flow_data['daily_data']
        )
        
        # 5. 新增：风险评分
        trap_risk_score = self._calculate_trap_risk(traps, capital_type)
        
        # 6. 整合结果
        result = {
            'stock_code': stock_code,
            'analyze_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'analyze_days': days,
            
            # 原有数据
            'fund_flow': fund_flow_data,
            'qmt': qmt_data,
            
            # 新增：诱多检测
            'trap_detection': {
                'detected_traps': traps,
                'trap_count': len(traps),
                'highest_severity': max([t.get('confidence', 0) for t in traps], default=0)
            },
            
            # 新增：资金性质
            'capital_analysis': capital_type,
            
            # 新增：风险评分
            'risk_assessment': {
                'trap_risk_score': trap_risk_score,
                'risk_level': self._get_risk_level(trap_risk_score),
                'recommendation': self._get_recommendation(trap_risk_score, capital_type)
            }
        }
        
        return result
    
    def _calculate_trap_risk(self, traps: list, capital_type: dict) -> float:
        """计算综合诱多风险评分（0-1）"""
        
        base_risk = 0.0
        
        # 检测到的陷阱越多，风险越高
        for trap in traps:
            base_risk += trap.get('confidence', 0) * 0.3
        
        # 游资类型风险更高
        if capital_type['type'] == 'HOT_MONEY':
            base_risk += 0.4
        elif capital_type['type'] == 'LONG_TERM':
            base_risk -= 0.2
        
        # 限制在 0-1
        return max(0.0, min(1.0, base_risk))
    
    def _get_risk_level(self, score: float) -> str:
        """风险等级"""
        if score >= 0.8:
            return 'CRITICAL'
        elif score >= 0.6:
            return 'HIGH'
        elif score >= 0.4:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _get_recommendation(self, score: float, capital_type: dict) -> str:
        """操作建议"""
        
        if score >= 0.8:
            return 'AVOID - 高风险诱多陷阱，建议远离'
        elif score >= 0.6:
            if capital_type['type'] == 'HOT_MONEY':
                return 'WAIT_AND_WATCH - 疑似游资操盘，观察1-3天后再决策'
            else:
                return 'CAUTIOUS - 谨慎观察，设置严格止损'
        elif score >= 0.4:
            return 'MODERATE - 中等风险，可小仓位参与'
        else:
            if capital_type['type'] == 'LONG_TERM':
                return 'OPPORTUNITY - 长线资金进场，可考虑布局'
            else:
                return 'NEUTRAL - 无明显信号，继续观察'
```

---

## 📝 AI 团队执行 Prompt（4 个）

### Prompt 1: 实现"滚动指标计算器"（最优先）

```markdown
# 任务：实现滚动指标计算器

## 背景
当前 JSON 输出只有单日流向数据，无法看到"5日/10日滚动净流入"，
导致无法判断"持续吸筒 vs 单日诱多"。

## 需求
创建文件 `logic/rolling_metrics.py`，实现 `RollingMetricsCalculator` 类。

## 核心功能
`add_rolling_metrics(daily_data)`: 为每日数据添加滚动指标

## 需要添加的字段
```python
{
    'date': '2026-02-02',
    'institution': 5025.1,
    
    # 新增字段
    'flow_5d_net': -317.54,           # 过去5天累计净流入
    'flow_10d_net': -1043.98,         # 过去10天累计
    'flow_20d_net': -6850.27,         # 过去20天累计
    'inflow_rank_percentile': 0.92    # 当前流入在历史中的排名（百分位）
}
```

## 边界处理
- 前5天 `flow_5d_net` 为 `None`
- 前10天 `flow_10d_net` 为 `None`
- 前20天 `flow_20d_net` 为 `None`

## 测试用例
输入 603697 的 90 天数据，验证：
- 2月2日的 `flow_10d_net` 应该是 "1月24日-2月2日" 的累计
- `inflow_rank_percentile` 应接近 0.92（因为 5025万 是 90 天最大）

## 交付物
1. `logic/rolling_metrics.py`
2. 单元测试 `tests/test_rolling_metrics.py`
```

---

### Prompt 2: 实现"诱多陷阱检测器"（核心）

```markdown
# 任务：实现诱多陷阱检测器模块

## 背景
MyQuantTool 项目（commit e234a21）当前无法识别机构的"诱多"操作，
导致在 300997/603697 等股票分析中误判。

## 需求
创建文件 `logic/trap_detector.py`，实现 `TrapDetector` 类。

## 核心功能
1. `detect_pump_and_dump()`: 检测"单日大吸+隔日反卖"模式
2. `detect_hot_money_raid()`: 检测"游资突袭"模式
3. `detect_self_trading()`: 检测"对倒"风险
4. `comprehensive_trap_scan()`: 综合扫描

## 输入格式
```python
daily_data = [
    {
        'date': '2026-02-02',
        'institution': 5025.1,
        'super_large': 3861.92,
        'large': 1163.18,
        'retail': -5025.1,
        'pct_chg': 2.52
    },
    ...
]
```

## 输出格式
```python
{
    'detected': True/False,
    'type': 'PUMP_AND_DUMP' | 'HOT_MONEY_RAID' | 'SELF_TRADING_RISK',
    'confidence': 0.85,
    'evidence': '前日吸筒6692万，今日反手卖2961万'
}
```

## 测试用例
1. 300997: 1月29日 +6692万，1月30日 -2961万 → 应检测为 PUMP_AND_DUMP（置信度 0.85+）
2. 603697: 2月2日 +5025万，前期累计 -6438万 → 应检测为 HOT_MONEY_RAID（置信度 0.70+）

## 交付物
1. `logic/trap_detector.py`
2. 单元测试 `tests/test_trap_detector.py`
3. 使用示例 `examples/trap_detection_demo.py`
```

---

### Prompt 3: 集成新模块到主流程

```markdown
# 任务：集成诱多检测到主分析流程

## 需求
修改 `enhanced_stock_analyzer.py` 的 `comprehensive_analysis()` 方法，
集成 `TrapDetector`, `RollingMetricsCalculator`, `CapitalClassifier`。

## 修改点
1. 在 `__init__()` 中初始化新模块
2. 在数据获取后，先调用 `RollingMetricsCalculator.add_rolling_metrics()`
3. 然后调用 `TrapDetector.comprehensive_trap_scan()`
4. 添加 `CapitalClassifier.classify()` 调用
5. 计算综合风险评分
6. 整合到返回的 JSON 中

## 新增 JSON 结构
```python
{
    'stock_code': '603697',
    'analyze_time': '2026-02-02 19:34:00',
    
    # 原有字段（保留）
    'fund_flow': {...},
    'qmt': {...},
    
    # 新增字段
    'trap_detection': {
        'detected_traps': [{...}],
        'trap_count': 1,
        'highest_severity': 0.70
    },
    'capital_analysis': {
        'type': 'HOT_MONEY',
        'confidence': 0.75,
        'evidence': '...'
    },
    'risk_assessment': {
        'trap_risk_score': 0.75,
        'risk_level': 'HIGH',
        'recommendation': 'WAIT_AND_WATCH - ...'
    }
}
```

## 测试
使用 300997 和 603697 的真实数据测试。

## 交付物
1. 修改后的 `enhanced_stock_analyzer.py`
2. 回归测试
3. 新功能的集成测试
```

---

### Prompt 4: 更新 `stock_ai_tool.py` 主接口

```markdown
# 任务：更新主接口支持增强分析模式

## 需求
修改 `stock_ai_tool.py` 的 `analyze_stock()` 函数，
添加新的 `mode='enhanced'` 模式。

## 新增模式
```python
def analyze_stock(
    stock_code: str,
    days: int = 90,
    mode: str = 'json',  # 新增 'enhanced' 选项
    pure_data: bool = False,
    auto_save: bool = True,
    use_qmt: bool = True
) -> dict:
```

## 文件命名
```
data/stock_analysis/{code}/{code}_{date}_{days}days_enhanced.json
```

## 示例调用
```python
# 原有调用（向后兼容）
result = analyze_stock('603697', days=90, mode='json')

# 新调用（增强模式）
result = analyze_stock('603697', days=90, mode='enhanced')

# 批量分析
results = batch_analyze_stocks(['300997', '603697'], mode='enhanced')
```

## 日志输出
```
[WARN] 603697: 检测到 HOT_MONEY_RAID 陷阱（置信度 70%）
[WARN] 603697: 风险评分 0.75 (HIGH)
[INFO] 603697: 建议 WAIT_AND_WATCH
```

## 交付物
1. 修改后的 `stock_ai_tool.py`
2. 更新的 README.md
3. 示例脚本 `examples/enhanced_analysis_demo.py`
```

---

## 🎯 优先级和时间规划

### 第 1 周（立刻实现）

- **Day 1-2**: 实现 RollingMetricsCalculator
  - 原因: 其他模块都依赖它
  
- **Day 3-4**: 实现 TrapDetector
  - 原因: 这是核心功能
  
- **Day 5**: 集成到 enhanced_stock_analyzer.py
  - 原因: 验证整体流程

- **Day 6-7**: 测试 + 修复 bug
  - 使用 300997/603697 真实数据验证

### 第 2 周（优化完善）

- 实现 CapitalClassifier
- 实现风险评分系统
- 更新 stock_ai_tool.py 接口
- 编写文档和示例

### 第 3 周（扩展功能）

- 添加分时线数据采集
- 添加异常检测器
- 性能优化
- 批量分析优化

---

## 📋 验收标准（用真实案例）

### 测试用例 1: 300997（欢乐家）
```python
result = analyze_stock('300997', days=90, mode='enhanced')

# 应该检测到诱多
assert '诱多' in result['trap_detection']['detected_traps'][0]['type']
assert result['risk_assessment']['risk_score'] >= 0.85
assert 'AVOID' in result['risk_assessment']['recommendation']
```

### 测试用例 2: 603697（有友食品）
```python
result = analyze_stock('603697', days=90, mode='enhanced')

# 应该检测到游资
assert result['capital_analysis']['type'] == 'HOT_MONEY'
assert result['risk_assessment']['risk_score'] >= 0.70
assert 'WAIT' in result['risk_assessment']['recommendation']
```

### 性能验收
- 单只股票分析: < 5 秒
- 批量 10 只股票: < 30 秒
- 数据缓存命中: > 80%

---

## 🚀 立刻开始的行动

1. **选择一个 Prompt** 并复制给 AI 助手
2. **使用 603697 数据测试** 第一个模块的输出
3. **逐步实现** Prompt 1 → 2 → 3 → 4

**最终效果**:
```
之前: 看到 +5025万 → 觉得是"填坑" → 追进 → 被套
之后: 系统自动检测 HOT_MONEY_RAID + 风险评分 0.75 → WAIT_AND_WATCH → 避开陷阱
```

---

**版本**: v1.0  
**生成时间**: 2026-02-02 19:40  
**项目**: MyQuantTool (commit e234a21)  
**用途**: 系统化架构优化 + AI 团队执行 Prompt
