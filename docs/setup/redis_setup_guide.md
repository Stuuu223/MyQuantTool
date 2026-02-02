# Redis 安装和配置指南

## 为什么需要 Redis？

MyQuantTool V9.2 引入了**竞价快照系统**，用于保存和恢复竞价数据，防止重启程序后数据丢失。

- **竞价时间（9:25-9:30）**：系统会自动保存竞价数据到 Redis
- **盘中/盘后（9:30 以后）**：系统会从 Redis 恢复竞价数据
- **效果**：即使重启程序，竞价数据也不会丢失

## 安装 Redis

### 方法 1：下载 Redis for Windows（推荐）

1. **下载 Redis**
   - 访问：https://github.com/microsoftarchive/redis/releases
   - 下载最新的 `.msi` 或 `.zip` 文件
   - 推荐下载 `Redis-x64-3.2.100.msi`

2. **安装 Redis**
   - 双击 `.msi` 文件，按照提示安装
   - 默认安装路径：`C:\Program Files\Redis`
   - 勾选 "Add to PATH" 选项（如果有的话）

3. **验证安装**
   ```cmd
   redis-server --version
   redis-cli --version
   ```

### 方法 2：使用 Chocolatey 安装

如果你已经安装了 Chocolatey，可以直接运行：

```cmd
choco install redis-64
```

### 方法 3：使用 WSL（Windows Subsystem for Linux）

如果你使用 WSL，可以安装 Linux 版本的 Redis：

```bash
sudo apt-get update
sudo apt-get install redis-server
sudo service redis-server start
```

## 配置 Redis

### 修改 start_with_redis.bat

如果你的 Redis 安装路径不是 `C:\redis`，请修改 `start_with_redis.bat` 文件：

```batch
REM 设置 Redis 路径（根据你的实际安装路径修改）
set REDIS_PATH=C:\Program Files\Redis
set REDIS_SERVER=%REDIS_PATH%\redis-server.exe
set REDIS_CONFIG=%REDIS_PATH%\redis.windows.conf
```

### 将 Redis 安装为 Windows 服务（可选）

如果你希望 Redis 作为 Windows 服务自动启动，可以运行：

```cmd
cd C:\Program Files\Redis
redis-server --service-install redis.windows.conf
redis-server --service-start
```

然后使用 `start_redis_service.bat` 启动项目。

## 启动项目

### 方法 1：使用 start_with_redis.bat（推荐）

这个脚本会：
1. 自动检查 Redis 是否安装
2. 自动启动 Redis（如果未运行）
3. 启动 MyQuantTool

```cmd
start_with_redis.bat
```

### 方法 2：使用 start_redis_service.bat

这个脚本假设 Redis 已安装为 Windows服务：

```cmd
start_redis_service.bat
```

### 方法 3：手动启动

如果你想手动控制 Redis：

1. **启动 Redis**
   ```cmd
   redis-server
   ```

2. **在另一个命令行窗口启动项目**
   ```cmd
   start.bat
   ```

## 验证 Redis 是否正常工作

### 1. 检查 Redis 是否运行

```cmd
tasklist | findstr redis-server
```

如果看到 `redis-server.exe`，说明 Redis 正在运行。

### 2. 测试 Redis 连接

```cmd
redis-cli ping
```

如果返回 `PONG`，说明 Redis 正常工作。

### 3. 检查竞价快照功能

启动项目后，查看日志：

```
✅ 竞价快照管理器初始化成功（Redis 可用）
```

如果看到这个消息，说明竞价快照功能已启用。

## 常见问题

### Q1: Redis 启动失败

**解决方案**：
1. 检查 Redis 路径是否正确
2. 检查端口 6379 是否被占用
3. 以管理员身份运行启动脚本

### Q2: 竞价快照功能不可用

**解决方案**：
1. 确认 Redis 正在运行
2. 检查日志中的错误信息
3. 确认 `config_database.json` 中的 Redis 配置正确

### Q3: 没有 Redis 能用吗？

**答案**：可以，但竞价快照功能不可用。

- **有 Redis**：竞价数据会保存到 Redis，重启程序后可以恢复
- **没有 Redis**：竞价数据只在内存中，重启程序后会丢失

系统会自动检测 Redis 是否可用，如果没有 Redis，会显示警告但不影响其他功能。

### Q4: 如何卸载 Redis？

如果安装了 `.msi` 版本：
1. 打开"控制面板" → "程序和功能"
2. 找到 Redis，右键卸载

如果是 `.zip` 版本：
1. 直接删除 Redis 文件夹
2. 如果安装了服务，运行：
   ```cmd
   redis-server --service-uninstall
   ```

## Redis 配置文件

Redis 的配置文件是 `redis.windows.conf`，常用配置：

```conf
# 端口（默认 6379）
port 6379

# 绑定地址（默认只允许本地访问）
bind 127.0.0.1

# 密码（可选）
# requirepass your_password

# 最大内存（可选）
# maxmemory 256mb

# 持久化（可选）
# save 900 1
# save 300 10
# save 60 10000
```

## 性能优化

### 1. 禁用持久化（提高性能）

如果不需要数据持久化（竞价快照只需要临时缓存），可以禁用持久化：

```conf
# 禁用 RDB
save ""

# 禁用 AOF
appendonly no
```

### 2. 设置最大内存

```conf
maxmemory 512mb
maxmemory-policy allkeys-lru
```

### 3. 调整超时时间

```conf
timeout 300
```

## 监控 Redis

### 查看连接数

```cmd
redis-cli info clients
```

### 查看内存使用

```cmd
redis-cli info memory
```

### 查看所有键

```cmd
redis-cli keys "auction:*"
```

### 删除所有竞价快照

```cmd
redis-cli --scan --pattern "auction:*" | xargs redis-cli del
```

## 总结

- **推荐安装**：Redis for Windows (MSI)
- **推荐启动方式**：`start_with_redis.bat`
- **竞价快照过期时间**：24 小时
- **Redis 端口**：6379
- **数据格式**：JSON

如果有任何问题，请查看日志文件或联系技术支持。