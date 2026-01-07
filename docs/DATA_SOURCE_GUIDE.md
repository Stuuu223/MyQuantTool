# 📊 真实龙虎榜数据获取指南

## 一、akshare 龙虎榜数据源（推荐 ⭐⭐⭐⭐⭐）

### 1.1 基础龙虎榜数据

```python
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def get_lhb_data(date_str: str):
    """
    获取指定日期的龙虎榜日数据
    
    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
    
    Returns:
        DataFrame: 龙虎榜数据
        
    列字段:
        - 排名: 排名位置
        - 代码: 股票代码
        - 名称: 股票名称
        - 最新价: 当前股价
        - 涨跌幅: 涨跌幅百分比
        - 成交额: 龙虎榜成交额（万元）
        - 成交量: 龙虎榜成交量（万股）
        - 游资名称: 上榜游资名称
        - 操作方向: '买' / '卖'
    """
    try:
        df = ak.stock_lgb_daily(date=date_str)
        return df
    except Exception as e:
        print(f"获取 {date_str} 龙虎榜失败: {str(e)}")
        return None


# 使用示例
today = datetime.now().strftime('%Y-%m-%d')
df_lhb = get_lhb_data(today)

if df_lhb is not None:
    print(f"获取了 {len(df_lhb)} 条龙虎榜记录")
    print(df_lhb.head())
```

### 1.2 批量获取历史龙虎榜数据

```python
def get_lhb_history(
    start_date: str,
    end_date: str,
    skip_holidays: bool = True
) -> pd.DataFrame:
    """
    批量获取龙虎榜历史数据
    
    Args:
        start_date: 开始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        skip_holidays: 是否跳过节假日和周末
    
    Returns:
        合并后的 DataFrame
    """
    from datetime import datetime, timedelta
    
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    all_data = []
    current = start
    
    while current <= end:
        # 跳过周末
        if skip_holidays and current.weekday() >= 5:
            current += timedelta(days=1)
            continue
        
        date_str = current.strftime('%Y-%m-%d')
        print(f"正在获取 {date_str}...")
        
        df = get_lhb_data(date_str)
        if df is not None and len(df) > 0:
            df['date'] = date_str
            all_data.append(df)
        
        current += timedelta(days=1)
    
    if all_data:
        result = pd.concat(all_data, ignore_index=True)
        return result
    else:
        return pd.DataFrame()


# 使用示例
start = '2025-12-01'
end = '2026-01-07'

df_history = get_lhb_history(start, end)
print(f"获取了 {len(df_history)} 条历史记录")

# 保存为 CSV（缓存加速后续分析）
df_history.to_csv('data/lhb_history.csv', index=False, encoding='utf-8')
```

### 1.3 获取龙虎榜详情（游资详细对手）

```python
def get_lhb_detail(
    stock_code: str,
    date_str: str
) -> pd.DataFrame:
    """
    获取单只股票的龙虎榜详细对手信息
    
    Args:
        stock_code: 股票代码，例如 '000001'
        date_str: 日期 'YYYY-MM-DD'
    
    Returns:
        该股票在该日期的所有上榜游资详情
    """
    try:
        df = ak.stock_lgb_detail(code=stock_code, date=date_str)
        return df
    except Exception as e:
        print(f"获取 {stock_code} 详情失败: {str(e)}")
        return None


# 使用示例
df_detail = get_lhb_detail('000001', '2026-01-07')
if df_detail is not None:
    print(f"获取了 {len(df_detail)} 个游资的详情")
```

---

## 二、其他数据源对比

### 2.1 东方财富 API（有限制）

```python
# 网页爬虫方式（易被反爬虫封杀）
import requests
from bs4 import BeautifulSoup

def get_lhb_from_eastmoney(date_str: str):
    """
    从东方财富爬龙虎榜（不推荐）
    缺点：
    - 容易被反爬虫封禁
    - 速度慢
    - 数据解析复杂
    """
    url = f"http://vip.stock.finance.sina.com.cn/q/go.php/vInvestConsult/kind/xjl/index.phtml?symbol=sz000001&date={date_str}"
    # ... 复杂爬虫逻辑
    pass
```

### 2.2 新浪财经龙虎榜（过时）

```python
# 已停止更新，不推荐
def get_lhb_from_sina(date_str: str):
    """
    新浪龙虎榜接口已关闭（2023年+）
    改用 akshare
    """
    pass
```

### 2.3 Wind 数据库（商业版）

```python
# 需要付费订阅
from windpy import w

def get_lhb_from_wind(date_str: str):
    """
    Wind 数据库（金融机构专用）
    
    优点：
    - 数据最准确、更新最快
    - 支持高频查询
    
    缺点：
    - 需要付费（≥5000元/年）
    - 仅供机构用户
    
    推荐：个人/小规模团队不推荐
    """
    pass
```

---

## 三、本地缓存策略（加速开发）

### 3.1 CSV 缓存

```python
import os
import pandas as pd
from datetime import datetime

def load_or_fetch_lhb(
    date_str: str,
    cache_dir: str = 'data/cache'
) -> pd.DataFrame:
    """
    优先从本地缓存读取，缓存不存在时实时获取
    """
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = f"{cache_dir}/lhb_{date_str}.csv"
    
    # 先查缓存
    if os.path.exists(cache_path):
        print(f"✅ 从缓存读取: {cache_path}")
        return pd.read_csv(cache_path)
    
    # 实时获取
    print(f"🔄 实时获取: {date_str}")
    df = get_lhb_data(date_str)
    
    if df is not None and len(df) > 0:
        df.to_csv(cache_path, index=False, encoding='utf-8')
        print(f"💾 缓存保存: {cache_path}")
    
    return df


# 使用示例
df = load_or_fetch_lhb('2026-01-07')
```

### 3.2 SQLite 本地数据库

```python
import sqlite3
from datetime import datetime

class LHBDatabase:
    def __init__(self, db_path: str = 'data/lhb.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lhb (
                    id INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT,
                    capital_name TEXT,
                    direction TEXT,  -- '买' 或 '卖'
                    amount REAL,  -- 成交额（万元）
                    price REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, code, capital_name, direction)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_date_code 
                ON lhb(date, code)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_capital 
                ON lhb(capital_name)
            """)
    
    def insert_batch(self, df: pd.DataFrame):
        """批量插入龙虎榜数据"""
        with sqlite3.connect(self.db_path) as conn:
            df.to_sql('lhb', conn, if_exists='append', index=False)
    
    def query_by_date(self, date_str: str) -> pd.DataFrame:
        """查询指定日期的龙虎榜"""
        with sqlite3.connect(self.db_path) as conn:
            query = f"""
                SELECT * FROM lhb 
                WHERE date = '{date_str}'
                ORDER BY amount DESC
            """
            return pd.read_sql(query, conn)
    
    def query_by_capital(self, capital_name: str, days: int = 30) -> pd.DataFrame:
        """查询游资近N天的操作"""
        with sqlite3.connect(self.db_path) as conn:
            query = f"""
                SELECT * FROM lhb 
                WHERE capital_name = '{capital_name}'
                AND date >= date('now', '-{days} days')
                ORDER BY date DESC
            """
            return pd.read_sql(query, conn)
    
    def get_capital_pairs(self, days: int = 30):
        """获取常见对手游资对"""
        with sqlite3.connect(self.db_path) as conn:
            query = f"""
                SELECT 
                    c1.capital_name as capital_a,
                    c2.capital_name as capital_b,
                    COUNT(*) as battle_count
                FROM lhb c1
                JOIN lhb c2 ON c1.code = c2.code 
                    AND c1.date = c2.date
                    AND c1.direction != c2.direction
                    AND c1.date >= date('now', '-{days} days')
                WHERE c1.capital_name < c2.capital_name
                GROUP BY c1.capital_name, c2.capital_name
                ORDER BY battle_count DESC
                LIMIT 50
            """
            return pd.read_sql(query, conn)


# 使用示例
db = LHBDatabase()

# 插入数据
df_history = get_lhb_history('2025-12-01', '2026-01-07')
db.insert_batch(df_history)

# 查询指定日期
df_today = db.query_by_date('2026-01-07')
print(f"今日上榜 {len(df_today)} 条")

# 查询游资近30天操作
df_capital = db.query_by_capital('中泰证券杭州庆春路营业部', days=30)
print(f"该游资近30天上榜 {len(df_capital)} 次")

# 获取常见对手对
df_pairs = db.get_capital_pairs(days=30)
print("常见对手配对:")
print(df_pairs.head())
```

---

## 四、数据预处理（接入 MyQuantTool）

### 4.1 标准化数据格式

```python
def preprocess_lhb_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    预处理龙虎榜原始数据，转换为 MyQuantTool 标准格式
    """
    df = df_raw.copy()
    
    # 列重命名
    rename_map = {
        '代码': 'stock_code',
        '名称': 'stock_name',
        '游资名称': 'capital_name',
        '操作方向': 'direction',
        '成交额': 'amount',  # 单位：万元
        '最新价': 'price',
        'date': 'trade_date'
    }
    df.rename(columns=rename_map, inplace=True)
    
    # 数据类型转换
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    
    # 标准化方向（'买' → 1, '卖' → -1）
    df['direction_code'] = df['direction'].map({'买': 1, '卖': -1})
    
    # 移除缺失值
    df.dropna(subset=['stock_code', 'capital_name', 'amount'], inplace=True)
    
    # 按日期排序
    df.sort_values('trade_date', inplace=True)
    
    return df


# 使用示例
df_processed = preprocess_lhb_data(df_history)
print(df_processed.head())
```

### 4.2 直接集成到 CapitalNetworkBuilder

```python
from logic.capital_network import CapitalNetworkBuilder

# 加载龙虎榜数据
db = LHBDatabase()
df_lhb = db.query_by_date('2026-01-07')
df_lhb = preprocess_lhb_data(df_lhb)

# 构建网络
builder = CapitalNetworkBuilder(lookback_days=30)
G = builder.build_graph_from_lhb(df_lhb, include_competitive=True)

# 分析
node_metrics = builder.calculate_node_metrics()
competitive = builder.analyze_competitive_landscape(df_lhb)
clusters = builder.get_capital_clusters(k=3)

print(f"✅ 网络构建成功: {G.number_of_nodes()} 节点, {G.number_of_edges()} 边")
```

---

## 五、完整集成脚本

### 5.1 日常自动更新脚本

```python
#!/usr/bin/env python3
# update_lhb_daily.py

import logging
from datetime import datetime
from data_loader import LHBDatabase, get_lhb_data, preprocess_lhb_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_daily():
    """
    每日更新龙虎榜数据（建议在收盘后 15:30 运行）
    """
    db = LHBDatabase()
    
    today = datetime.now().strftime('%Y-%m-%d')
    logger.info(f"🔄 正在更新 {today} 龙虎榜...")
    
    try:
        # 获取今日数据
        df_today = get_lhb_data(today)
        
        if df_today is None or len(df_today) == 0:
            logger.warning(f"❌ {today} 无龙虎榜数据（可能是周末或节假日）")
            return
        
        # 预处理
        df_processed = preprocess_lhb_data(df_today)
        
        # 入库
        db.insert_batch(df_processed)
        logger.info(f"✅ 成功插入 {len(df_processed)} 条记录")
        
        # 统计
        capitals = df_processed['capital_name'].nunique()
        stocks = df_processed['stock_code'].nunique()
        logger.info(f"📊 今日: {stocks} 只股票, {capitals} 个游资")
        
    except Exception as e:
        logger.error(f"❌ 更新失败: {str(e)}")


if __name__ == '__main__':
    update_daily()
```

### 5.2 定时任务（cron/Windows任务计划）

```bash
# Linux crontab -e
# 每天 15:35 自动更新（A股收盘15:00）
35 15 * * 1-5 /usr/bin/python3 /path/to/update_lhb_daily.py

# Windows Task Scheduler
# 任务：每工作日 15:35 运行 python update_lhb_daily.py
```

---

## 六、推荐数据获取流程

```
┌─────────────────────────────┐
│  akshare 实时获取            │
│  (stock_lgb_daily)          │
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│  本地 SQLite 数据库入库       │
│  (缓存 + 索引优化)           │
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│  数据预处理和标准化           │
│  (列重命名 + 类型转换)       │
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│  输入 MyQuantTool 各模块      │
│  (网络分析 + LSTM + 融合)    │
└─────────────────────────────┘
```

---

## 七、常见问题 (FAQ)

### Q1: akshare 更新频率是多少？
**A**: 每天 16:00 后更新前一交易日数据，与官方同步。

### Q2: 如何获取历史数据（如2年前）？
**A**: `get_lhb_history()` 可批量获取，但需要等待网络请求（建议用缓存）。

### Q3: 数据有时缺失怎么办？
**A**: akshare 依赖官方数据源，偶尔会有延迟。建议用 `try-except` + 重试机制。

### Q4: 能否本地存储所有历史龙虎榜？
**A**: 可以，用 SQLite 数据库，建议每周备份到 CSV/Parquet。

### Q5: 游资名称有时不一致怎么办？
**A**: 建议维护一个「游资别名映射表」，用 `replace()` 统一名称。
