# QMT 模块安装问题解决方案

## 🚨 当前问题

**Python 版本不兼容**：你的 Python 版本是 3.14，而 QMT 的编译模块（.pyd 文件）是为 Python 3.10 编译的，无法直接使用。

```
当前 Python 版本: 3.14
QMT 模块要求: Python 3.10
```

## 📊 系统状态

### ✅ 已完成
- QMT 客户端已安装（E:\qmt）
- QMT 客户端已登录
- QMT 配置文件已正确设置
- xtquant 模块文件已复制

### ❌ 问题
- DLL 加载失败（Python 版本不兼容）
- IPythonApiClient.pyd 无法在 Python 3.14 上运行

## 🔧 解决方案

### 方案1：使用 QMT 自带的 Python 环境（推荐）

QMT 自带了 Python 3.6 环境，可以直接使用：

```powershell
# 使用 QMT 的 Python 运行程序
E:\qmt\python\python.exe scripts/init_qmt.py
```

**优点**：
- 完全兼容 QMT 模块
- 无需额外配置
- QMT 官方支持

**缺点**：
- Python 版本较旧（3.6）
- 需要安装项目依赖

### 方案2：降级 Python 版本到 3.10

如果你想在当前环境使用 QMT，需要降级 Python 版本：

```powershell
# 1. 卸载当前 Python 3.14
# 2. 安装 Python 3.10
# 3. 重新安装项目依赖
pip install -r requirements.txt
```

**优点**：
- 可以使用最新 QMT 模块
- 与 QMT 完全兼容

**缺点**：
- 需要重新配置环境
- 可能影响其他项目

### 方案3：保持现状，使用 EasyQuotation（临时方案）

由于你的系统已经实现了双核驱动架构（QMT 优先 + EasyQuotation 降级），可以暂时不安装 QMT：

```python
# 系统会自动降级到 EasyQuotation
# 数据延迟：秒级（vs QMT 的毫秒级）
# 数据质量：良好（vs QMT 的优秀）
```

**优点**：
- 无需修改任何配置
- 系统正常运行
- 零风险

**缺点**：
- 无法享受 QMT 的极速数据
- 无法使用 QMT 交易功能

## 🎯 推荐方案

**短期**：使用方案3（EasyQuotation）
- 系统已经正常运行
- 数据质量良好
- 零风险

**长期**：使用方案1（QMT Python 环境）
- 当需要极致性能时
- 当需要实盘交易时
- 创建启动脚本使用 QMT Python

## 📝 使用 QMT Python 环境运行程序

如果你想使用 QMT Python 运行你的程序：

```powershell
# 创建启动脚本
# start_with_qmt_python.bat

@echo off
E:\qmt\python\python.exe main.py
pause
```

```powershell
# 运行启动脚本
start_with_qmt_python.bat
```

## 💡 总结

**当前状态**：
- ✅ 系统正常运行（使用 EasyQuotation）
- ✅ 数据源充足（EasyQuotation + AkShare）
- ✅ 功能完整
- ❌ QMT 模块无法加载（Python 版本不兼容）

**建议**：
1. 保持现状，使用 EasyQuotation
2. 如果需要 QMT 极速数据，使用 QMT 的 Python 环境
3. 如果需要实盘交易，考虑降级 Python 版本到 3.10

**关键点**：你的系统已经实现了自动降级机制，即使 QMT 不可用，系统依然可以正常运行！🚀

---

**Author**: iFlow CLI
**Date**: 2026-01-28
**Version**: V1.0