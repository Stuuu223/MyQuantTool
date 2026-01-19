# 🛑 严重 Bug 报告

## 📅 报告时间
2026-01-19 09:30

---

## 🚨 Bug #1: 通用缓存管理器失效

### 文件
`logic/cache_manager.py`

### 问题描述
`get` 方法完全忽略了 `set` 方法中设置的自定义 TTL。

### 后果
- 所有设置了特定过期时间的缓存（例如短时缓存），实际上都会使用默认的 5 分钟（`_default_ttl`）过期
- 这会导致数据更新不及时或缓存无法按预期清除

### 错误代码
```python
@staticmethod
def get(key):
    # ...
    timestamp = CacheManager._cache_timestamps.get(key, 0)
    # ❌ BUG: 这里只判断了 _default_ttl，完全忽略了可能存在的自定义 ttl
    if time.time() - timestamp > CacheManager._default_ttl:
        # ...
```

### 修复方案
在 `get` 方法中优先检查是否存在自定义 TTL 键（`f"{key}_ttl"`）。

### 修复状态
✅ **已修复** - 所有测试通过

### 测试结果
```
✅ 自定义 TTL 测试通过！
✅ 默认 TTL 测试通过！
✅ 内存泄漏修复测试通过！
✅ 缓存信息测试通过！
```

---

## 🚨 Bug #2: 架构断裂 - DataManager 未集成 V10.1.9.1 新特性

### 文件
`logic/data_manager.py`

### 问题描述
根据 `GIT_COMMIT_LOG_20260117.md`，V10.1.9.1 版本的一大核心改进是 Mock 数据源（时光机）和数据提供者工厂模式 (`DataProviderFactory`)。

然而，`logic/data_manager.py` 代码中：
- ❌ 未使用工厂模式：依然直接硬编码导入和使用了 akshare 和 easyquotation
- ❌ 不支持历史回放：代码逻辑全是针对实盘（Live）的，没有任何切换到 Mock/Replay 模式的逻辑

### 后果
- DataManager 是系统的核心数据入口，但它没有被重构以支持"历史回放"功能
- 如果 `ui/historical_replay.py` 使用了新的 Provider，而主系统逻辑还走这个旧的 DataManager，会导致系统分裂（一部分走回放，一部分走实盘数据）

### 影响范围
**163 个文件**正在使用旧的 `DataManager`：
- `main.py`
- `logic/sector_analysis_streamlit.py`
- `logic/signal_generator.py`
- `ui/v18_navigator.py`
- 所有测试文件
- 等等...

### 修复建议
1. 确认 V10.1.9.1 是否应该废弃 `DataManager` 改用 `DataProviderFactory`
2. 如果是，需要重构所有使用 `DataManager` 的模块（163 个文件）
3. 如果否，需要在 `DataManager` 中集成 `DataProviderFactory`

### 修复状态
⚠️ **待确认** - 需要指挥官确认架构方向

---

## 🚨 Bug #3: 版本号混乱/超前

### 文件
`logic/data_manager.py`

### 问题描述
- 提交日志显示当前版本是 **V10.1.9.1** (2026-01-17)
- 但在 `data_manager.py` 中却出现了 **V11** 的功能注释：

```python
# [新增功能] V11 阶段二：数据库自动瘦身 (第 147 行)
```

### 后果
- 代码库中可能混入了未提交的开发中代码（V11）
- 版本管理出现了混乱

### 修复建议
1. 确认当前版本号
2. 移除未提交的 V11 代码，或者更新版本号到 V11
3. 建立严格的版本管理流程

### 修复状态
⚠️ **待确认** - 需要指挥官确认版本号

---

## 🚨 Bug #4: 内存泄漏风险

### 文件
`logic/cache_manager.py`

### 问题描述
在 `clear_expired` 和 `clear` 的删除逻辑中，只删除了 key 和 key 的时间戳，**没有删除对应的 ttl 记录**（`f"{key}_ttl"`）。

### 后果
- `_cache_timestamps` 字典中会残留大量的 `_ttl` 键
- 虽然占用内存不大，但属于逻辑不严谨
- 长期运行可能导致内存缓慢增长

### 修复方案
在删除缓存时，同时删除对应的 TTL 记录。

### 修复状态
✅ **已修复** - 所有测试通过

### 测试结果
```
📊 清除过期后 TTL 记录数: 1
📊 剩余 TTL 记录: ['key2_ttl']
📊 清除 key2 后 TTL 记录数: 0
📊 剩余 TTL 记录: []
```

---

## 📊 修复总结

| Bug | 严重程度 | 状态 | 影响范围 |
|-----|---------|------|---------|
| Bug #1: 缓存管理器失效 | 🔴 严重 | ✅ 已修复 | 全局 |
| Bug #2: 架构断裂 | 🔴 严重 | ⚠️ 待确认 | 163 个文件 |
| Bug #3: 版本号混乱 | 🟡 中等 | ⚠️ 待确认 | 版本管理 |
| Bug #4: 内存泄漏 | 🟡 中等 | ✅ 已修复 | 缓存管理 |

---

## 🎯 建议行动

### 立即执行
1. ✅ Bug #1: 缓存管理器失效 - **已修复**
2. ✅ Bug #4: 内存泄漏风险 - **已修复**

### 需要确认
1. ⚠️ Bug #2: 架构断裂 - 需要指挥官确认是否重构 `DataManager`
2. ⚠️ Bug #3: 版本号混乱 - 需要指挥官确认当前版本号

---

## 📝 修改文件

- `logic/cache_manager.py` - 修复 TTL 判断逻辑和内存泄漏
- `test_cache_manager_fix.py` - 测试脚本

---

## 🚀 下一步

指挥官，请确认以下问题：

1. **Bug #2**: 是否应该废弃 `DataManager` 改用 `DataProviderFactory`？如果是，需要重构 163 个文件。
2. **Bug #3**: 当前版本号是 V10.1.9.1 还是 V11？

请指示下一步行动。🎯