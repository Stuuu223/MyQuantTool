# 数据库系统使用指南

## 📊 数据库架构

本项目使用**混合数据库架构**，根据数据类型自动选择最优数据库：

```
Redis    → 实时数据、缓存、会话（最快）
MongoDB  → 历史数据、训练数据（大容量）
SQLite   → 配置、元数据（轻量级）
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install redis pymongo
```

### 2. 配置数据库

编辑 `config_database.json`：

```json
{
  "redis": {
    "host": "localhost",
    "port": 6379,
    "db": 0
  },
  "mongodb": {
    "host": "localhost",
    "port": 27017,
    "db": "myquant"
  },
  "sqlite": {
    "path": "data/myquant.db"
  }
}
```

### 3. 使用数据库管理器

```python
from logic.database_manager import get_db_manager

# 获取数据库管理器（单例）
db = get_db_manager()

# 保存实时数据（自动路由到Redis）
db.save_realtime_data('000001', {
    'price': 10.50,
    'volume': 1000000
}, expire=60)

# 获取实时数据（从Redis）
data = db.get_realtime_data('000001')

# 保存历史数据（自动路由到MongoDB）
db.save_historical_data('stock_daily', [
    {'symbol': '000001', 'date': '2024-01-01', 'close': 10.5},
    {'symbol': '000001', 'date': '2024-01-02', 'close': 10.3}
])

# 获取历史数据（从MongoDB）
historical = db.get_historical_data('stock_daily', '000001')

# 保存配置（自动路由到SQLite）
db.save_config('strategy_params', {'fast': 5, 'slow': 20})

# 获取配置（从SQLite）
config = db.get_config('strategy_params')

# 缓存预测（Redis）
db.cache_prediction('model_1', {'symbol': '000001'}, prediction, expire=3600)

# 获取缓存的预测
cached = db.get_cached_prediction('model_1', {'symbol': '000001'})
```

## 📊 性能对比

| 操作 | SQLite | MongoDB | Redis |
|------|--------|---------|-------|
| 读取 | ~5ms | ~2ms | **~0.1ms** ⚡ |
| 写入 | ~10ms | ~3ms | **~0.5ms** ⚡ |
| 查询 | ~20ms | ~5ms | **~1ms** ⚡ |

## 🎯 使用场景

### Redis（最快）
- ✅ 实时股价数据
- ✅ 模型预测缓存
- ✅ 会话状态
- ✅ 训练进度

### MongoDB（大容量）
- ✅ 历史K线数据
- ✅ 训练数据集
- ✅ 模型版本管理
- ✅ 学习历史

### SQLite（轻量级）
- ✅ 系统配置
- ✅ 用户设置
- ✅ 小规模元数据

## 🔧 性能优化

### 1. 缓存预测结果
```python
# 检查缓存
cached = db.get_cached_prediction(model_id, input_data)
if cached:
    return cached

# 计算预测
prediction = model.predict(input_data)

# 缓存结果
db.cache_prediction(model_id, input_data, prediction, expire=3600)
```

### 2. 批量操作
```python
# 批量保存历史数据
historical_data = generate_historical_data()
db.save_historical_data('stock_daily', historical_data)
```

### 3. 过期策略
```python
# 实时数据：60秒过期
db.save_realtime_data(symbol, data, expire=60)

# 预测缓存：1小时过期
db.cache_prediction(model_id, input_data, prediction, expire=3600)

# 会话数据：1天过期
db.redis_set('session', session_data, expire=86400)
```

## 📈 性能监控

```python
# 获取性能统计
stats = db.get_performance_stats()

# 打印性能报告
print(db.get_performance_report())

# 输出示例：
# 📊 数据库性能报告
# ===================================================
#
# 🔹 REDIS
#   读取次数: 1523
#   写入次数: 856
#   错误次数: 0
#   总耗时: 0.2345秒
#   平均耗时: 0.000098秒
#   吞吐量: 10234.56 ops/秒
#
# 🔹 MONGODB
#   读取次数: 234
#   写入次数: 123
#   错误次数: 2
#   总耗时: 0.5678秒
#   平均耗时: 0.001567秒
#   吞吐量: 638.34 ops/秒
```

## 🧪 测试

运行测试：

```bash
python test_database_manager.py
```

测试内容：
- ✅ Redis读写测试
- ✅ MongoDB读写测试
- ✅ SQLite读写测试
- ✅ 高级API测试
- ✅ 性能监控测试
- ✅ 性能对比测试

## 💡 最佳实践

### 1. 选择合适的数据库
```python
# 实时数据 → Redis
db.save_realtime_data(symbol, realtime_data, expire=60)

# 历史数据 → MongoDB
db.save_historical_data('stock_daily', historical_data)

# 配置数据 → SQLite
db.save_config('strategy_params', params)
```

### 2. 使用缓存
```python
# 检查缓存
cached = db.get_cached_prediction(model_id, input_data)
if cached:
    return cached

# 计算并缓存
prediction = model.predict(input_data)
db.cache_prediction(model_id, input_data, prediction)
```

### 3. 批量操作
```python
# 批量保存
for item in large_dataset:
    db.mongodb_insert('collection', item)

# 批量读取
results = db.mongodb_find('collection', limit=1000)
```

### 4. 错误处理
```python
# 检查连接
if db._redis_client:
    # 使用Redis
    pass
else:
    # 回退到SQLite
    pass
```

## 🔍 故障排查

### Redis连接失败
```bash
# 检查Redis是否运行
redis-cli ping

# 启动Redis
redis-server
```

### MongoDB连接失败
```bash
# 检查MongoDB是否运行
mongod

# 启动MongoDB
mongod --dbpath /path/to/data
```

### 性能问题
```python
# 查看性能统计
print(db.get_performance_report())

# 优化建议：
# - 使用Redis缓存热点数据
# - 批量操作减少网络往返
# - 设置合理的过期时间
```

## 📝 迁移指南

### 从纯SQLite迁移

```python
# 旧代码
sqlite_conn.execute("INSERT INTO stock_data VALUES (...)")
data = sqlite_conn.execute("SELECT * FROM stock_data")

# 新代码（自动路由）
db.save_historical_data('stock_daily', data_list)
data = db.get_historical_data('stock_daily', symbol)
```

### 渐进式迁移

1. **阶段1**: 添加Redis缓存（性能提升10-100倍）
2. **阶段2**: 添加MongoDB存储历史数据（容量提升100倍）
3. **阶段3**: 保留SQLite用于配置（轻量级）

## 🎓 总结

- ✅ **Redis**: 实时数据、缓存（最快）
- ✅ **MongoDB**: 历史数据、训练数据（大容量）
- ✅ **SQLite**: 配置、元数据（轻量级）
- ✅ **自动路由**: 透明切换，代码无需修改
- ✅ **性能监控**: 实时监控，优化决策

通过这个混合架构，你可以获得：
- ⚡ **极致性能**: Redis提供微秒级响应
- 💾 **无限容量**: MongoDB支持海量数据
- 🎯 **灵活切换**: 自动选择最优数据库
- 📊 **实时监控**: 性能数据一目了然