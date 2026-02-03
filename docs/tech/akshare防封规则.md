# AkShare 防封规则

**最后更新**: 2026-02-03

## 概述

AkShare 虽然完全免费且稳定性高，但过度频繁调用仍可能触发数据源限制导致 IP 封禁。

## 项目内置防封机制

### 1. RateLimiter 速率限制器

**文件位置**: `logic/rate_limiter.py`

```python
from logic.rate_limiter import get_rate_limiter, safe_request

# 获取全局限流器实例
limiter = get_rate_limiter()

# 默认配置：
# - 每分钟最多 20 次请求
# - 每小时最多 200 次请求
# - 最小请求间隔 3 秒
```

**功能**:
- 限制每分钟请求数
- 限制每小时请求数
- 自动请求间隔
- 请求队列管理
- 请求历史记录

### 2. robust_api_call 装饰器

**文件位置**: `logic/api_robust.py`

```python
from logic.api_robust import robust_api_call

@robust_api_call(max_retries=3, delay=2)
def get_stock_data(code):
    import akshare as ak
    return ak.stock_zh_a_hist(symbol=code, period="daily")

# 特性：
# - 自动重试（最多3次）
# - 递增等待时间（2s, 4s, 6s）
# - 捕获所有异常，防止程序崩溃
```

### 3. rate_limit_decorator 装饰器

```python
from logic.api_robust import rate_limit_decorator

@rate_limit_decorator(calls_per_second=5)  # 每秒最多5次
def get_realtime_data():
    import akshare as ak
    return ak.stock_zh_a_spot_em()
```

## AkShare 推荐调用频率

根据官方文档和实战经验：

| 数据类型 | 推荐间隔 | 说明 |
|---|---|---|
| 历史日线数据 | 3-5 秒 | 单次请求返回多日数据，无需频繁调用 |
| 实时行情数据 | 1-2 秒 | 监控模式下使用 |
| 分时数据 | 2-3 秒 | 1分钟/5分钟K线数据 |
| 财务数据 | 5-10 秒 | 批量获取后本地缓存 |

## 防封最佳实践

### ✅ 正确做法

```python
# 使用 safe_request 包装
from logic.rate_limiter import safe_request
import akshare as ak

def get_stock_history(code):
    return safe_request(
        lambda: ak.stock_zh_a_hist(symbol=code, period="daily")
    )

# 批量获取减少请求次数（使用循环+速率限制）
def get_multiple_stocks(codes):
    results = []
    for code in codes:
        results.append(get_stock_history(code))
    return results
```

### ❌ 错误做法

```python
# 无限制并发请求可能导致 IP 封禁！
import concurrent.futures
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    futures = [executor.submit(ak.stock_zh_a_hist, code) for code in codes]
```

## 降级与缓存策略

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

## 监控与调试

### 查看速率限制统计

```python
from logic.rate_limiter import get_rate_limiter

limiter = get_rate_limiter()
limiter.print_stats()

# 输出示例：
# 📊 RateLimiter 统计信息
# ============================================================
#   最近1分钟: 5/20 次
#   最近1小时: 45/200 次
#   剩余配额: 15 (分钟) | 155 (小时)
#   最后请求: 2026-02-03T10:30:15
# ============================================================
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

## 错误处理

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

## 常见问题

### Q1: 为什么我的 IP 被封了？

**A**: 可能原因：
- 并发请求过多
- 请求间隔过短
- 短时间内请求次数过多

**解决方案**:
- 使用 `safe_request` 包装所有 AkShare 调用
- 减少并发线程数
- 增加请求间隔
- 使用本地缓存减少重复请求

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

**A**: 推荐方法：
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

## 相关文档

- [QMT 虚拟环境配置指南](../setup/qmt_venv_setup.md)
- [数据源架构设计文档](数据源架构设计文档.md)
- [速率限制说明](速率限制说明.md)