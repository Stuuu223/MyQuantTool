# API 防封与速率限制指南

**最后更新**: 2026-02-09

## 📊 概述

为了防止频繁请求导致被封 IP，项目集成了完整的**速率限制系统**和**防封机制**。本指南适用于所有外部 API 调用，包括 AkShare、Tushare、东方财富等数据源。

### 为什么需要防封？

- **IP 封禁风险**: 过度频繁请求会导致 IP 被数据源封禁
- **服务稳定性**: 遵守 API 调用限制可以保证服务稳定运行
- **数据质量**: 适当的请求间隔可以获取更准确的数据

## 🚀 内置防封机制

### 1. RateLimiter 速率限制器

**文件位置**: `logic/rate_limiter.py`

#### 功能特性

- ✅ 自动速率限制（每分钟/每小时）
- ✅ 智能队列管理（自动等待）
- ✅ 实时配额监控
- ✅ 请求历史记录
- ✅ 单例模式（全局共享）
- ✅ 线程安全（使用 Lock）

#### 默认配置

```python
RateLimiter(
    max_requests_per_minute=20,  # 每分钟最多 20 次请求
    max_requests_per_hour=200,   # 每小时最多 200 次请求
    min_request_interval=3,       # 最小请求间隔 3 秒
    enable_logging=True
)
```

#### 使用方式

**方式1：自动限制（推荐）**

所有工具都已经自动集成了速率限制，无需额外配置：

```python
from stock_ai_tool import analyze_stock

# 自动应用速率限制
result = analyze_stock('300997', 10, mode='full')
```

**方式2：手动控制**

```python
from logic.rate_limiter import get_rate_limiter

limiter = get_rate_limiter()

# 检查是否可以请求
can_request, reason = limiter.can_request()
if not can_request:
    print(f"⏳ {reason}")

# 等待直到可以请求
limiter.wait_if_needed()

# 执行请求
result = your_api_call()

# 记录请求
limiter.record_request()

# 查看统计信息
limiter.print_stats()
```

**方式3：使用 safe_request 包装**

```python
from logic.rate_limiter import safe_request
import akshare as ak

def get_stock_history(code):
    return safe_request(
        lambda: ak.stock_zh_a_hist(symbol=code, period="daily")
    )
```

### 2. robust_api_call 装饰器

**文件位置**: `logic/api_robust.py`

```python
from logic.api_robust import robust_api_call

@robust_api_call(max_retries=3, delay=2, return_empty_df=True)
def get_stock_data(code):
    import akshare as ak
    return ak.stock_zh_a_hist(symbol=code, period="daily")

# 特性：
# - 自动重试（最多3次）
# - 递增等待时间（2s, 4s, 6s）
# - 捕获所有异常，防止程序崩溃
# - 可选返回空 DataFrame（不抛出异常）
```

### 3. rate_limit_decorator 装饰器

```python
from logic.api_robust import rate_limit_decorator

@rate_limit_decorator(calls_per_second=5)  # 每秒最多5次
def get_realtime_data():
    import akshare as ak
    return ak.stock_zh_a_spot_em()
```

## 📋 AkShare 推荐调用频率

根据官方文档和实战经验：

| 数据类型 | 推荐间隔 | 说明 |
|---|---|---|
| 历史日线数据 | 3-5 秒 | 单次请求返回多日数据，无需频繁调用 |
| 实时行情数据 | 1-2 秒 | 监控模式下使用 |
| 分时数据 | 2-3 秒 | 1分钟/5分钟K线数据 |
| 财务数据 | 5-10 秒 | 批量获取后本地缓存 |

## 📊 监控与调试

### 查看实时统计

```python
from logic.rate_limiter import get_rate_limiter

limiter = get_rate_limiter()
limiter.print_stats()
```

### 输出示例

```
============================================================
📊 RateLimiter 统计信息
============================================================
  最近1分钟: 6/20 次
  最近1小时: 6/200 次
  剩余配额: 14 (分钟) | 194 (小时)
  最后请求: 2026-02-02T17:29:15.153453
============================================================
```

### 获取详细统计

```python
stats = limiter.get_stats()
print(stats)

# 返回：
# {
#     'recent_minute': 5,
#     'recent_hour': 45,
#     'max_per_minute': 20,
#     'max_per_hour': 200,
#     'remaining_minute': 15,
#     'remaining_hour': 155,
#     'last_request': '2026-02-03T10:30:15'
# }
```

### 请求历史记录

**文件路径**: `data/rate_limiter_history.json`

**内容**: 最近100次请求记录

**格式**: JSON

## 🎯 防封最佳实践

### ✅ 正确做法

**1. 使用内置工具**

```python
from stock_ai_tool import analyze_stock

# 自动应用速率限制，无需担心
result = analyze_stock('300997', 10, mode='full')
```

**2. 批量分析**

```python
from batch_analyze import batch_analyze

stocks = ['300997', '301171', '600000', '000001']
results = batch_analyze(stocks, days=10, mode='full')
```

**3. 分批处理大量股票**

```python
from batch_analyze import batch_analyze

# 分成小批，每批10只
all_stocks = ['300997', '301171', ...]  # 假设有100只

batch_size = 10
for i in range(0, len(all_stocks), batch_size):
    batch = all_stocks[i:i+batch_size]
    results = batch_analyze(batch, days=10, mode='full')

    # 每批之间休息1分钟
    import time
    time.sleep(60)
```

**4. 使用装饰器保护**

```python
from logic.api_robust import robust_api_call, rate_limit_decorator

@rate_limit_decorator(calls_per_second=5)
@robust_api_call(max_retries=3, delay=2)
def get_stock_data(code):
    import akshare as ak
    return ak.stock_zh_a_hist(symbol=code, period="daily")
```

### ❌ 错误做法

**1. 直接调用 API（绕过速率限制）**

```python
# ❌ 错误：直接调用 API，绕过速率限制
import akshare as ak
df = ak.stock_individual_fund_flow(stock='300997', market='sz')

# ✅ 正确：使用带速率限制的工具
from stock_ai_tool import analyze_stock
result = analyze_stock('300997', 10, mode='full')
```

**2. 高频并发**

```python
# ❌ 错误：并发调用可能导致 IP 封禁
from concurrent.futures import ThreadPoolExecutor

stocks = ['300997', '301171', '600000']
with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(analyze_stock, stocks))

# ✅ 正确：使用批量分析工具
from batch_analyze import batch_analyze
results = batch_analyze(stocks, days=10, mode='full')
```

**3. 无限制并发请求**

```python
# ❌ 错误：无限制并发请求可能导致 IP 封禁！
import concurrent.futures
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    futures = [executor.submit(ak.stock_zh_a_hist, code) for code in codes]
```

## 💾 缓存策略

### 使用 Redis 缓存

```python
from logic.cache_manager import CacheManager
cache = CacheManager()

def get_data_with_cache(code):
    cache_key = f"stock_hist_{code}"

    # 先查缓存
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    # 缓存未命中，调用 AkShare
    data = get_stock_history(code)

    # 缓存24小时
    cache.set(cache_key, data, ttl=86400)

    return data
```

### 本地缓存策略

```python
# 将历史数据保存到本地文件
import os
import pandas as pd

def save_to_cache(code, data):
    cache_dir = "data/cache/stock_history"
    os.makedirs(cache_dir, exist_ok=True)

    file_path = os.path.join(cache_dir, f"{code}.csv")
    data.to_csv(file_path, index=False)

def load_from_cache(code):
    cache_dir = "data/cache/stock_history"
    file_path = os.path.join(cache_dir, f"{code}.csv")

    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None
```

## 🔧 错误处理

### 使用 robust_api_call

```python
from logic.api_robust import robust_api_call
from requests.exceptions import ProxyError

@robust_api_call(max_retries=3, delay=2, return_empty_df=True)
def safe_akshare_call():
    import akshare as ak
    return ak.stock_zh_a_spot_em()

# 网络问题（ProxyError）时返回空 DataFrame，不抛出异常
```

### 手动错误处理

```python
import time
import akshare as ak

def get_with_retry(code, max_retries=3):
    for i in range(max_retries):
        try:
            return ak.stock_zh_a_hist(symbol=code, period="daily")
        except Exception as e:
            if i < max_retries - 1:
                print(f"第{i+1}次重试: {e}")
                time.sleep(2 * (i + 1))  # 递增等待
            else:
                print(f"最终失败: {e}")
                return None
```

## ⚙️ 配置参数

### 自定义 RateLimiter 配置

如果需要修改配置，请编辑 `logic/rate_limiter.py` 文件：

```python
# 更保守的配置
RateLimiter(
    max_requests_per_minute=10,  # 每分钟最多10次
    max_requests_per_hour=100,   # 每小时最多100次
    min_request_interval=5,       # 最小间隔5秒
    enable_logging=True
)
```

### 自定义 robust_api_call 参数

```python
@robust_api_call(
    max_retries=5,           # 最多重试5次
    delay=3,                 # 初始等待3秒
    return_empty_df=True,    # 失败时返回空 DataFrame
    exceptions_to_catch=[    # 捕获特定异常
        ConnectionError,
        TimeoutError,
        ProxyError
    ]
)
def get_stock_data(code):
    import akshare as ak
    return ak.stock_zh_a_hist(symbol=code, period="daily")
```

## ❓ 常见问题

### Q1: 为什么我的 IP 被封了？

**可能原因**:
- 并发请求过多
- 请求间隔过短
- 短时间内请求次数过多
- 绕过了速率限制器

**解决方案**:
- 使用 `safe_request` 包装所有 AkShare 调用
- 减少并发线程数
- 增加请求间隔
- 使用本地缓存减少重复请求
- 不要绕过速率限制器

### Q2: 如何配置 RateLimiter 参数？

**A**: 在 `logic/rate_limiter.py` 中修改默认值：

```python
_global_limiter = RateLimiter(
    max_requests_per_minute=20,   # 每分钟最多20次
    max_requests_per_hour=200,    # 每小时最多200次
    min_request_interval=3,       # 最小间隔3秒
    enable_logging=True
)
```

### Q3: 如何绕过 IP 封禁？

**推荐方法**:
1. **等待**: 通常封禁时间不会太长（几小时到几天）
2. **使用代理**: 可以购买动态代理 IP 池
3. **缓存优先**: 减少对 AkShare 的依赖
4. **批量获取**: 合并多个请求，减少调用次数

**代理示例**:
```python
import requests

proxies = {
    'http': 'http://proxy_ip:proxy_port',
    'https': 'http://proxy_ip:proxy_port'
}

# AkShare 不直接支持代理，需要改写源码
# 参考: docs/tech/akshare_代理配置.md
```

### Q4: 请求太慢怎么办？

**原因**: 达到了速率限制，需要等待

**解决方案**:
- 这是正常行为，速率限制器在保护你的 IP
- 如果需要更快的速度，可以调整配置参数（但不建议）
- 使用批量分析工具自动处理
- 增加本地缓存减少重复请求

### Q5: 配额不足怎么办？

**原因**: 短时间内请求太多

**解决方案**:
- 等待几分钟让配额恢复
- 使用批量分析工具自动处理
- 分批处理大量股票
- 增加本地缓存

## 🔧 故障排查

### 问题1：请求太慢

**症状**: 请求响应时间很长

**原因**: 达到了速率限制，需要等待

**解决**:
- 这是正常行为，速率限制器在保护你的 IP
- 如果需要更快的速度，可以调整配置参数（但不建议）

### 问题2：被封IP

**症状**: 所有 API 请求都失败

**原因**: 绕过了速率限制，请求过于频繁

**解决**:
- 等待1-2小时后重试
- 确保使用带速率限制的工具
- 不要绕过速率限制器
- 检查是否有并发请求

### 问题3：配额不足

**症状**: 提示"配额不足"

**原因**: 短时间内请求太多

**解决**:
- 等待几分钟让配额恢复
- 使用批量分析工具自动处理
- 分批处理大量股票
- 增加本地缓存

### 问题4：装饰器不生效

**症状**: 装饰器没有限制请求频率

**原因**: 装饰器顺序错误或未正确应用

**解决**:
```python
# ✅ 正确顺序：rate_limit 在外层，robust_api_call 在内层
@rate_limit_decorator(calls_per_second=5)
@robust_api_call(max_retries=3, delay=2)
def get_stock_data(code):
    pass

# ❌ 错误顺序
@robust_api_call(max_retries=3, delay=2)
@rate_limit_decorator(calls_per_second=5)
def get_stock_data(code):
    pass
```

## ✅ 总结

### 核心原则

1. ✅ 使用提供的工具（`stock_ai_tool`、`batch_analyze`）
2. ✅ 不要绕过速率限制器
3. ✅ 监控请求频率
4. ✅ 遵守最佳实践
5. ✅ 使用缓存减少重复请求

### 安全保证

- 每分钟最多 20 次请求
- 每小时最多 200 次请求
- 最小请求间隔 3 秒
- 自动等待和队列管理
- 自动重试机制
- 异常捕获和处理

### 三层防护

1. **速率限制层**: RateLimiter 限制请求频率
2. **重试层**: robust_api_call 自动重试失败请求
3. **缓存层**: CacheManager 减少重复请求

这样可以有效避免被封 IP 的风险！

## 📚 相关文档

- [QMT 虚拟环境配置指南](../setup/qmt_venv_setup.md)
- [数据源架构设计文档](数据源架构设计文档.md)
- [数据源管理器说明](../dev/data_source_manager.md)