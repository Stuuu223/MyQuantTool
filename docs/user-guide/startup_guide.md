# MyQuantTool 启动指南

## 启动方式总览

MyQuantTool 提供了多种启动方式，你可以根据自己的需求选择：

| 启动脚本 | 说明 | Redis 支持 | 推荐度 |
|---------|------|-----------|--------|
| `quick_start.bat` | 快速启动（自动检测 Redis） | ✅ 自动检测 | ⭐⭐⭐⭐⭐ |
| `start_with_redis.bat` | 完整启动（包含 Redis 配置） | ✅ 完整支持 | ⭐⭐⭐⭐ |
| `start_redis_service.bat` | 服务模式启动（Redis 作为 Windows 服务） | ✅ 服务模式 | ⭐⭐⭐ |
| `start.bat` | 基础启动（不包含 Redis） | ❌ 不支持 | ⭐⭐ |

## 快速开始

### 方式 1：使用 quick_start.bat（推荐，最简单）

```cmd
quick_start.bat
```

**特点**：
- 自动检测 Redis 是否已安装
- 自动启动 Redis（如果找到）
- 自动激活虚拟环境
- 一键启动项目

**适用场景**：
- Redis 安装在系统路径或默认路径 `C:\redis`
- 需要快速启动，不想配置太多

### 方式 2：使用 start_with_redis.bat（推荐，功能完整）

```cmd
start_with_redis.bat
```

**特点**：
- 可以自定义 Redis 安装路径
- 自动检查 Redis 是否运行
- 自动启动 Redis（如果未运行）
- 完整的错误处理和提示

**适用场景**：
- Redis 安装在自定义路径
- 需要完整的错误提示
- 需要手动控制 Redis 启动

**配置方法**：

编辑 `start_with_redis.bat`，修改 Redis 路径：

```batch
set REDIS_PATH=C:\Program Files\Redis
set REDIS_SERVER=%REDIS_PATH%\redis-server.exe
set REDIS_CONFIG=%REDIS_PATH%\redis.windows.conf
```

### 方式 3：使用 start_redis_service.bat（服务模式）

```cmd
start_redis_service.bat
```

**特点**：
- 假设 Redis 已安装为 Windows 服务
- 自动启动 Redis 服务
- 适合长期运行的系统

**适用场景**：
- Redis 已安装为 Windows 服务
- 需要系统启动时自动运行 Redis

**安装 Redis 服务**：

```cmd
cd C:\Program Files\Redis
redis-server --service-install redis.windows.conf
redis-server --service-start
```

### 方式 4：使用 start.bat（基础模式）

```cmd
start.bat
```

**特点**：
- 不包含 Redis 支持
- 只启动项目
- 竞价快照功能不可用

**适用场景**：
- 不需要竞价快照功能
- 只想快速测试项目
- Redis 未安装

## 安装 Redis

### 方法 1：下载 Redis for Windows（推荐）

1. **下载 Redis**
   - 访问：https://github.com/microsoftarchive/redis/releases
   - 下载 `Redis-x64-3.2.100.msi`

2. **安装 Redis**
   - 双击 `.msi` 文件，按照提示安装
   - 默认安装路径：`C:\Program Files\Redis`

3. **验证安装**
   ```cmd
   redis-server --version
   ```

### 方法 2：使用 Chocolatey

```cmd
choco install redis-64
```

### 方法 3：使用 WSL

```bash
sudo apt-get update
sudo apt-get install redis-server
sudo service redis-server start
```

详细说明请参考：[Redis 安装和配置指南](../setup/redis_setup_guide.md)

## 测试 Redis

运行测试脚本，验证 Redis 是否正常工作：

```cmd
python test_redis.py
```

测试内容包括：
- ✅ Redis 模块是否安装
- ✅ Redis 连接是否成功
- ✅ 竞价快照功能是否可用
- ✅ Redis 状态信息
- ✅ 配置信息

## 验证竞价快照功能

启动项目后，查看日志：

```
✅ 竞价快照管理器初始化成功（Redis 可用）
```

如果看到这个消息，说明竞价快照功能已启用。

## 常见问题

### Q1: Redis 启动失败

**解决方案**：
1. 检查 Redis 是否已安装
2. 检查 Redis 路径是否正确
3. 检查端口 6379 是否被占用
4. 以管理员身份运行启动脚本

### Q2: 竞价快照功能不可用

**解决方案**：
1. 运行 `python test_redis.py` 测试 Redis 连接
2. 检查日志中的错误信息
3. 确认 `config_database.json` 中的 Redis 配置正确

### Q3: 没有 Redis 能用吗？

**答案**：可以，但竞价快照功能不可用。

- **有 Redis**：竞价数据会保存到 Redis，重启程序后可以恢复
- **没有 Redis**：竞价数据只在内存中，重启程序后会丢失

系统会自动检测 Redis 是否可用，如果没有 Redis，会显示警告但不影响其他功能。

### Q4: 如何手动启动 Redis？

```cmd
# 启动 Redis
redis-server

# 在另一个窗口启动项目
python -m streamlit run main.py
```

### Q5: 如何查看 Redis 是否运行？

```cmd
tasklist | findstr redis-server
```

如果看到 `redis-server.exe`，说明 Redis 正在运行。

## 推荐启动流程

### 第一次使用

1. **安装 Redis**
   ```cmd
   # 下载并安装 Redis for Windows
   # 或运行: choco install redis-64
   ```

2. **配置 Redis 路径**（如果需要）
   ```cmd
   # 编辑 start_with_redis.bat
   # 修改 REDIS_PATH 为你的 Redis 安装路径
   ```

3. **测试 Redis**
   ```cmd
   python test_redis.py
   ```

4. **启动项目**
   ```cmd
   quick_start.bat
   ```

### 日常使用

```cmd
# 快速启动（推荐）
quick_start.bat

# 或使用完整启动
start_with_redis.bat
```

### 明天实盘使用（竞价快照）

1. **在 9:25 之前启动**
   ```cmd
   quick_start.bat
   ```

2. **系统会自动保存竞价数据**
   - 9:25-9:30：自动保存竞价数据到 Redis
   - 9:30 以后：自动从 Redis 恢复竞价数据

3. **即使重启程序**
   - 竞价数据不会丢失
   - 竞价量、竞价抢筹度、竞价金额都能正确显示

## 文件说明

| 文件 | 说明 |
|------|------|
| `quick_start.bat` | 快速启动脚本（推荐） |
| `start_with_redis.bat` | 完整启动脚本（包含 Redis 配置） |
| `start_redis_service.bat` | 服务模式启动脚本 |
| `start.bat` | 基础启动脚本（不包含 Redis） |
| `test_redis.py` | Redis 测试脚本 |
| `config_database.json` | 数据库配置文件 |
| `logic/auction_snapshot_manager.py` | 竞价快照管理器 |

## 相关文档

- [Redis 安装和配置指南](../setup/redis_setup_guide.md)
- [数据库使用指南](../setup/database_guide.md)

## 总结

- **推荐启动方式**：`quick_start.bat`
- **推荐 Redis 安装**：Redis for Windows (MSI)
- **竞价快照过期时间**：24 小时
- **Redis 端口**：6379

如果有任何问题，请查看日志文件或运行 `python test_redis.py` 测试。