# CASE: Tick数据通路统一封装（TickProvider）

**ID**: CASE_2026_02_TICK_PROVIDER  
**创建日期**: 2026-02-18  
**状态**: 规划中（规范已输出，待实现）  
**负责人**: AI项目总监

---

## 0. 背景 & 目标

### 为什么开始这条探索？
在网宿科技验证过程中，发现Tick下载逻辑散落在5+个脚本中，每次都要重新踩坑（VIP直连错误、端口占用、日期格式混乱）。

### 想回答的关键问题
1. 为什么每次Tick相关开发都要"重新发明轮子"？
2. 如何建立唯一的、稳定的Tick数据通路？
3. 如何防止团队重复踩同样的坑？

---

## 1. 进展记录

### Day 1 (2026-02-18)

#### 1.1 做了什么
- 梳理现有Tick相关脚本，发现分散在多处
- 复盘本次网宿验证中踩的坑（VIP直连、端口占用、日期格式）
- 输出TickProvider封装规范 `.iflow/tick_provider_spec.md`
- 制定Code Review红线：禁止直接import xtdata

#### 1.2 关键发现

**1.2.1 Tick逻辑散落在哪**

| 脚本 | 问题 | 状态 |
|-----|------|------|
| `tasks/data_prefetch.py` | xtdatacenter初始化逻辑 | 生产在用 |
| `scripts/download_wanzhu_tick_data.py` | 又一套connect/download | 新增 |
| `temp/test_wangsu_*.py` | 临时脚本各写各的 | 临时 |
| `backtest/t1_tick_backtester.py` | 独立路径处理 | 核心引擎 |
| `tools/download_from_list.py` | 只处理1m K线 | 不完整 |

**1.2.2 本次踩坑记录**

| 坑 | 错误尝试 | 正确做法 | 浪费 time |
|---|---------|---------|----------|
| VIP直连 | `xtdata.connect(vipsxmd1...)` | `xtdatacenter.listen()`本地转发 | 30min |
| 端口占用 | 不知道58609被占用 | 查进程/换端口范围 | 20min |
| 日期格式 | 2025 vs 2026混淆 | 标准化为YYYYMMDD | 15min |
| 列名不一致 | `price` vs `lastPrice` | 统一字段映射 | 10min |
| 数据估算 | `prev_close*0.99` | 使用真实preclose字段 | 20min |

**累计浪费**: 约1.5小时（单次验证）
**影响**: 每次Tick相关开发都重复踩坑，效率低下

#### 1.3 决策 / 动作

**规范输出**：
- ✅ `.iflow/tick_provider_spec.md` - 接口规范
- ✅ `docs/MyQuantTool-Architecture-Iron-Laws.md` - 第2.1条（铁律）

**Code Review红线**：
```python
# ❌ 禁止
import xtdata
import xtdatacenter
xtdata.connect('vipsxmd1...')

# ✅ 必须
from logic.data_providers.tick_provider import TickProvider
provider = TickProvider(config)
```

---

## 2. TickProvider设计规范

### 2.1 核心接口

```python
class TickProvider:
    """
    Tick数据统一提供者
    
    职责：
    1. 管理xtdatacenter生命周期（初始化、Token、监听端口）
    2. 封装datadir路径操作（QMT_DATA_DIR/SZ/0/code/date）
    3. 提供统一数据读取接口（字段标准化）
    4. 记录数据覆盖范围（哪些日期有tick）
    """
    
    def __init__(self, config: TickConfig):
        """初始化，自动启动xtdatacenter"""
        pass
    
    def ensure_history(self, code: str, start: str, end: str) -> None:
        """
        确保本地有[start, end]的tick数据
        必要时触发download_history_data下载
        """
        pass
    
    def load_ticks(self, code: str, start: str, end: str) -> pd.DataFrame:
        """
        从本地datadir读取tick，返回统一字段：
        - time: 时间戳
        - lastPrice: 最新价
        - volume: 成交量
        - amount: 成交额
        - bidPrice/askPrice: 买卖一档价格
        - bidVol/askVol: 买卖一档量
        """
        pass
    
    def get_coverage(self, code: str) -> List[str]:
        """
        返回该股票tick数据可用的日期列表
        如: ['20251113', '20251114', ...]
        """
        pass
    
    def check_data_freshness(self, code: str) -> Dict:
        """
        检查数据新鲜度
        返回: {
            'has_tick': bool,
            'latest_date': str,
            'record_count': int,
            'source': 'recorded' | 'backfill' | 'unavailable'
        }
        """
        pass
```

### 2.2 字段标准化映射

```python
# QMT原始字段 -> 标准字段
FIELD_MAPPING = {
    'time': 'time',
    'lastPrice': 'lastPrice',  # 有些版本用'price'
    'volume': 'volume',
    'amount': 'amount',
    'open': 'open',
    'high': 'high',
    'low': 'low',
    'bidPrice': 'bidPrice',
    'askPrice': 'askPrice',
    'bidVol': 'bidVol',
    'askVol': 'askVol',
    # 兼容性处理
    'price': 'lastPrice',  # 旧版本兼容
}
```

### 2.3 数据降级策略

```python
def load_ticks_with_fallback(self, code: str, start: str, end: str) -> pd.DataFrame:
    """
    优先tick，不足时降级到1m
    """
    coverage = self.get_coverage(code)
    target_dates = self._get_date_range(start, end)
    
    missing_dates = [d for d in target_dates if d not in coverage]
    
    if missing_dates:
        logger.warning(f"Tick数据缺失日期: {missing_dates}，降级到1m")
        return self._load_1m(code, start, end)
    
    return self._load_tick(code, start, end)
```

---

## 3. 迁移计划

### 阶段1：实现TickProvider（本周）
- [ ] 创建 `logic/data_providers/tick_provider.py`
- [ ] 实现核心接口（ensure_history/load_ticks/get_coverage）
- [ ] 单元测试（网宿科技数据验证）

### 阶段2：迁移现有脚本（下周）
- [ ] `tasks/data_prefetch.py` -> 使用TickProvider
- [ ] `scripts/download_wanzhu_tick_data.py` -> 使用TickProvider
- [ ] `backtest/t1_tick_backtester.py` -> 使用TickProvider
- [ ] 清理temp/test_wangsu_*.py临时脚本

### 阶段3：Code Review enforcement（持续）
- [ ] PR模板添加检查项："无直接xtdata调用"
- [ ] CI检查：扫描`import xtdata`直接报错
- [ ] 团队培训：TickProvider使用规范

---

## 4. 未解决问题

- [ ] xtdatacenter端口管理（自动发现可用端口）
- [ ] 多进程并发下载时的资源竞争
- [ ] Tick数据压缩/归档策略（长期存储优化）
- [ ] 与EventDrivenMonitor实时录制的数据合并

---

## 5. 相关资源

### 规范文档
- `.iflow/tick_provider_spec.md` - 详细接口规范
- `docs/MyQuantTool-Architecture-Iron-Laws.md` - 第2.1条铁律

### 参考实现
- `logic/qmt_historical_provider.py` - 现有部分实现（需抽象）
- `tasks/data_prefetch.py` - xtdatacenter初始化参考

### 测试数据
- `data/qmt_data/datadir/SZ/0/300017/` - 网宿科技65天tick
- `data/qmt_data/datadir/SZ/0/` - 深证344只股票

---

## 6. 经验教训

### 已确认
1. **封装债必须还**: 每次不封装，每次都要重复踩坑
2. **唯一入口原则**: 核心能力必须中心化，禁止各自为政
3. **知识沉淀**: 不能靠"记忆"，要靠"架构约束"

### 待验证
1. TickProvider性能是否能满足实时+回测双重需求
2. 多股票并发下载时的稳定性
3. 团队是否能遵守"禁止直接import xtdata"红线

---

## 7. 下一步（本周任务）

- [ ] 实现TickProvider核心类（Day 1-2）
- [ ] 网宿科技数据验证测试（Day 2）
- [ ] 迁移data_prefetch.py（Day 3）
- [ ] 迁移download_wanzhu_tick_data.py（Day 3-4）
- [ ] 迁移t1_tick_backtester.py（Day 4-5）
- [ ] Code Review流程更新（Day 5）
