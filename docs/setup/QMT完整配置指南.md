# QMT 完整配置指南

## 📖 概述

QMT (迅投量化交易系统) 是一款专业的量化交易平台，提供数据接口和交易接口。本指南将帮助你完整配置 QMT 环境，包括环境准备、虚拟环境配置、模块安装和接口配置。

### 🎯 为什么使用 QMT

**性能提升预期**：
- 实时数据延迟：3秒 → 0.05秒（60倍提升）
- 数据源：EasyQuotation（HTTP轮询）→ QMT（推流模式）

**核心优势**：
- 官方数据源，数据质量优秀
- 毫秒级数据延迟
- 支持实盘交易功能
- 支持历史数据和实时tick数据

### ⚠️ 重要提示

- QMT 模块需要 **Python 3.10.11**
- QMT 的编译模块（`.pyd` 文件）是为 Python 3.10 编译的
- 系统已实现多数据源架构，QMT 是可选数据源
- 即使 QMT 不可用，系统仍可正常运行（自动降级到 EasyQuotation + AkShare）

---

## 📋 目录

1. [环境准备](#1-环境准备)
2. [虚拟环境配置](#2-虚拟环境配置)
3. [QMT 模块安装](#3-qmt-模块安装)
4. [接口配置](#4-接口配置)
5. [验证安装](#5-验证安装)
6. [使用指南](#6-使用指南)
7. [常见问题](#7-常见问题)
8. [数据源说明](#8-数据源说明)

---

## 1. 环境准备

### 1.1 安装 QMT 客户端

1. 下载并安装 QMT 客户端（迅投量化交易终端）
2. 安装完成后，启动 QMT 客户端
3. 在 QMT 客户端中登录你的交易账户

**QMT 客户端默认安装路径**：
- `C:\QMT\QMT客户端\`
- `D:\QMT\QMT\`
- `E:\qmt\`

### 1.2 下载 Python 3.10.11

#### 官方下载链接
https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe

#### 安装步骤

1. **运行安装程序**
   - 双击运行下载的 python-3.10.11-amd64.exe

2. **初始界面**
   - 不要勾选 Add Python 3.10 to PATH
   - 点击 Customize installation

3. **Optional Features**
   - 勾选所有选项
   - 点击 Next

4. **Advanced Options**
   - 安装路径设置为：**C:\Python310**
   - 勾选所有选项
   - 点击 Install

5. **等待安装完成**
   - 看到 Setup was successful 即表示安装成功

6. **点击 Close 完成安装**

### 1.3 验证 Python 3.10.11 安装

打开 PowerShell 或 CMD，执行：

```bash
C:\Python310\python.exe --version
```

**预期输出**：`Python 3.10.11`

---

## 2. 虚拟环境配置

### 2.1 为什么需要虚拟环境

- QMT 的编译模块（`.pyd` 文件）是为 Python 3.10 编译的
- 系统可能是 Python 3.14 或其他版本，无法加载 QMT 模块
- 虚拟环境确保每个设备都有相同的 Python 3.10.11 环境

### 2.2 创建虚拟环境

```bash
cd E:\MyQuantTool

# 使用 Python 3.10 创建虚拟环境
C:\Python310\python.exe -m venv venv_qmt

# 激活虚拟环境
.\venv_qmt\Scripts\activate

# 验证虚拟环境
python --version
```

**预期输出**：`Python 3.10.11`

### 2.3 升级 pip

```bash
python -m pip install --upgrade pip
```

### 2.4 安装项目依赖

```bash
pip install -r requirements.txt
```

或手动安装核心依赖：

```bash
pip install akshare pandas numpy requests
```

---

## 3. QMT 模块安装

### 3.1 安装 xtquant 包

```bash
pip install xtquant
```

### 3.2 复制 QMT 底层通信模块

QMT 的 xtquant 模块包含一些底层通信模块（IPythonApiClient 和 xtpythonclient），这些模块需要从 QMT 客户端安装目录复制到项目中。

#### 找到 QMT 安装目录

通常位于以下路径之一：
- `C:\QMT\QMT客户端\bin.x64\Lib\site-packages\`
- `D:\QMT\QMT\bin.x64\Lib\site-packages\`
- `E:\qmt\bin.x64\Lib\site-packages\`

#### 复制必要文件

从 QMT 安装目录的 `Lib\site-packages` 中复制以下文件到项目的 `xtquant` 目录：

```
QMT/bin.x64/Lib/site-packages/xtquant/        →  E:\MyQuantTool\xtquant\
├── IPythonApiClient.cp310-win_amd64.pyd     →  IPythonApiClient.cp310-win_amd64.pyd
├── xtpythonclient.cp310-win_amd64.pyd       →  xtpythonclient.cp310-win_amd64.pyd
└── xtdata.py                                 →  xtdata.py
```

#### 批量复制命令（Windows CMD）

```bash
copy "E:\qmt\bin.x64\Lib\site-packages\xtquant\IPythonApiClient.cp310-win_amd64.pyd" "E:\MyQuantTool\xtquant\"
copy "E:\qmt\bin.x64\Lib\site-packages\xtquant\xtpythonclient.cp310-win_amd64.pyd" "E:\MyQuantTool\xtquant\"
copy "E:\qmt\bin.x64\Lib\site-packages\xtquant\xtdata.py" "E:\MyQuantTool\xtquant\"
```

#### 使用软链接（Linux/WSL）

```bash
cd E:\MyQuantTool\xtquant
ln -s /mnt/c/qmt/bin.x64/Lib/site-packages/xtquant/IPythonApiClient.cp310-win_amd64.pyd
ln -s /mnt/c/qmt/bin.x64/Lib/site-packages/xtquant/xtpythonclient.cp310-win_amd64.pyd
ln -s /mnt/c/qmt/bin.x64/Lib/site-packages/xtquant/xtdata.py
```

### 3.3 验证模块文件

检查 `xtquant` 目录中是否有以下文件：

```bash
dir E:\MyQuantTool\xtquant\*.pyd
dir E:\MyQuantTool\xtquant\xtdata.py
```

### 3.4 设置 PYTHONPATH（可选）

如果不想复制文件，可以设置 PYTHONPATH 环境变量：

#### 临时设置（当前会话）

```powershell
$env:PYTHONPATH = "E:\qmt\bin.x64\Lib\site-packages;$env:PYTHONPATH"
```

#### 永久设置

- 右键"此电脑" → 属性 → 高级系统设置 → 环境变量
- 在"系统变量"中新建 `PYTHONPATH`
- 值：`E:\qmt\bin.x64\Lib\site-packages`

---

## 4. 接口配置

### 4.1 配置数据接口

编辑 `config/qmt_config.json` 文件：

```json
{
  "qmt_data": {
    "enabled": true,
    "ip": "127.0.0.1",
    "port": 58610,
    "timeout": 10,
    "auto_connect": true,
    "retry_times": 3,
    "retry_interval": 2
  }
}
```

**重要参数说明**：
- `enabled`: 是否启用数据接口
- `ip`: QMT 客户端 IP 地址（本地使用 127.0.0.1）
- `port`: QMT 数据接口端口（默认 58610）
- `timeout`: 连接超时时间（秒）
- `retry_times`: 连接失败重试次数
- `retry_interval`: 重试间隔（秒）

### 4.2 配置交易接口（可选）

如果需要使用实盘交易功能，需要配置交易接口：

```json
{
  "qmt_trader": {
    "enabled": true,
    "ip": "127.0.0.1",
    "port": 58611,
    "session_id": 123456,
    "account_id": "你的账户ID",
    "account_type": "STOCK",
    "username": "你的用户名",
    "password": "你的密码"
  }
}
```

**重要参数说明**：
- `enabled`: 是否启用交易接口
- `port`: QMT 交易接口端口（默认 58611）
- `session_id`: 会话 ID（自定义，用于标识不同的客户端）
- `account_id`: 交易账户 ID
- `account_type`: 账户类型（STOCK: 股票账户）
- `username`: QMT 登录用户名
- `password`: QMT 登录密码

---

## 5. 验证安装

### 5.1 测试 QMT 模块导入

```bash
python -c "from xtquant import xtdata; print('QMT 模块已加载')"
```

**期望输出**：`QMT 模块已加载`

### 5.2 运行初始化脚本

确保 QMT 客户端已启动并登录，然后执行：

```bash
python scripts/init_qmt.py
```

该脚本会：
- ✅ 检查配置文件
- ✅ 测试数据接口连接
- ✅ 测试数据获取功能
- ✅ 测试交易接口连接（如果启用）

**期望输出**：
```
============================================================
🧪 QMT 基础连接测试
============================================================

1️⃣  导入 xtdata 模块...
   ✅ 导入成功

2️⃣  获取沪深A股股票列表...
   ✅ 成功获取 XXXX 只股票

3️⃣  测试获取tick数据...
   ✅ 成功获取tick数据

============================================================
✅ QMT 基础连接测试完成
============================================================
```

### 5.3 运行测试脚本

```bash
python test_qmt_connection.py
```

---

## 6. 使用指南

### 6.1 使用虚拟环境

#### 方式1: VSCode 自动使用（推荐）

**VSCode 已配置默认使用 `venv_qmt` 虚拟环境**：

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv_qmt/Scripts/python.exe"
}
```

直接在 VSCode 终端运行即可：

```bash
# 自动使用虚拟环境
python analyze.py 300997 90 --supplement
```

#### 方式2: 命令行激活

**Windows CMD**:
```bash
E:\MyQuantTool\venv_qmt\Scripts\activate.bat
python --version  # 应显示 Python 3.10.11
```

**Windows PowerShell**:
```bash
E:\MyQuantTool\venv_qmt\Scripts\Activate.ps1
python --version  # 应显示 Python 3.10.11
```

#### 方式3: 使用启动脚本

项目提供了便捷启动脚本：

```bash
# 运行分析（自动使用虚拟环境）
analyze_supplement.bat 300997 90 --supplement
```

**启动脚本内容**:
```batch
@echo off
E:\MyQuantTool\venv_qmt\Scripts\python.exe analyze.py %*
pause
```

### 6.2 获取股票数据示例

```python
from xtquant import xtdata

# 获取股票列表
stock_list = xtdata.get_stock_list_in_sector('沪深A股')

# 下载历史数据
xtdata.download_history_data('600519.SH', period='1d', start_time='20240101', end_time='20240131')

# 获取本地数据
data = xtdata.get_local_data(
    field_list=['time', 'open', 'high', 'low', 'close'],
    stock_list=['600519.SH'],
    period='1d',
    start_time='20240101',
    end_time='20240131'
)

# 获取实时tick数据
tick_data = xtdata.get_full_tick(['600519.SH'])
```

### 6.3 使用交易接口示例

```python
from xtquant import xttrader

# 创建回调类
class MyCallback(xttrader.XtQuantTraderCallback):
    def on_stock_order(self, order):
        print(f"订单状态: {order}")

# 创建交易客户端
trader = xttrader.XtQuantTrader(MyCallback(), session_id=123456)

# 连接交易接口
trader.connect()

# 查询账户资产
asset = trader.query_stock_asset()

# 下单
order_id = trader.order_stock(
    account='你的账户ID',
    stock_code='600519.SH',
    order_type=xttrader.STOCK_BUY,
    order_volume=100,
    price_type=xttrader.FIX_PRICE,
    price=1800.0
)
```

### 6.4 启动系统

```bash
# 激活虚拟环境
.\venv_qmt\Scripts\activate

# 启动系统
python main.py
```

---

## 7. 常见问题

### 7.1 Python 版本不兼容

**错误**：`DLL load failed while importing IPythonApiClient: 找不到指定的模块`

**原因**：使用了错误的 Python 版本（如 Python 3.14）

**解决方案**：
- 确保使用虚拟环境中的 Python 3.10.11
- 检查 Python 版本：`venv_qmt\Scripts\python.exe --version`

### 7.2 找不到 QMT 安装目录

**解决方法**：
- 打开 QMT 客户端，查看"帮助" → "关于"中的安装路径
- 或者搜索 `xtdata.py` 文件的位置

### 7.3 复制文件后仍然报错

**可能原因**：
1. 文件复制不完整
2. QMT 版本不兼容
3. 缺少依赖的 DLL 文件

**解决方法**：
- 确保复制了所有必要文件
- 检查 QMT 客户端版本是否与项目兼容
- 复制 `bin.x64` 目录下的所有 DLL 文件到项目根目录

### 7.4 连接失败

**问题**：`rpc初始化失败` 或连接超时

**解决方案**：
- 检查 QMT 客户端是否已启动
- 检查端口配置是否正确（数据端口 58610，交易端口 58611）
- 检查防火墙设置
- 尝试重启 QMT 客户端

### 7.5 无法获取数据

**问题**：`无法获取股票列表` 或 `tick数据为空`

**解决方案**：
- 确保已下载基础数据（在 QMT 客户端中）
- 检查网络连接
- 确保在交易时间内（9:30-15:00）

### 7.6 交易接口连接失败

**问题**：`交易接口连接失败`

**解决方案**：
- 检查账户配置是否正确
- 确保已开通实盘交易权限
- 检查 session_id 是否唯一
- 确保在 QMT 客户端中已登录

### 7.7 VSCode 中看不到虚拟环境

**原因**：`files.exclude` 配置隐藏了虚拟环境文件夹

**解决**：`.vscode/settings.json` 中已移除隐藏配置

```json
{
  "files.exclude": {
    // 不再隐藏 venv_qmt
  }
}
```

### 7.8 跨设备开发需要重复配置吗？

**是的**，因为虚拟环境（277 MB）已加入 `.gitignore`，不会提交到 Git。

**建议**：
- 保留本文档作为配置参考
- 每次在新设备上按步骤重新配置
- 约 10 分钟完成配置

---

## 8. 数据源说明

### 8.1 多数据源架构

你的系统支持多数据源自动切换，确保系统稳定运行：

#### 实时行情数据源优先级

1. **优先**：QMT tick 数据（毫秒级延迟）
2. **备用**：easyquotation（秒级延迟）
3. **降级**：AkShare 实时数据
4. **兜底**：本地文件

#### 历史数据数据源优先级

1. **优先**：AkShare 历史数据
2. **备用**：QMT 历史数据
3. **降级**：本地缓存
4. **兜底**：核心资产列表

### 8.2 灾备机制

```
如果 easyquotation 失败 → 降级到 AkShare
如果 AkShare 失败 → 降级到本地文件
如果本地文件不存在 → 返回核心资产列表
```

### 8.3 数据源对比

| 指标 | Python 3.14 + EasyQuotation | Python 3.10 + QMT |
|------|----------------------------|-------------------|
| 数据延迟 | 2-3秒 | 50-100毫秒 |
| 数据质量 | 依赖网络 | 官方数据 |
| 连接方式 | HTTP 轮询 | 推流模式 |
| 交易功能 | 不支持 | 支持 |

### 8.4 QMT 是可选的

**重要**：QMT 模块是可选的，不是必需的！

- 如果你有 QMT 客户端 → 按上述步骤安装，可以获得更好的数据质量
- 如果没有 QMT 客户端 → 完全不影响系统运行，继续使用 easyquotation + AkShare

你的系统已经设计好了多数据源架构，不会因为缺少 QMT 而无法运行。

### 8.5 使用 QMT 自带的 Python 环境（备选方案）

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

---

## ⚠️ 注意事项

1. **交易风险**: 使用实盘交易接口前，请充分测试策略
2. **权限限制**: 某些功能需要特定的交易权限
3. **数据限制**: 历史数据需要提前下载
4. **网络依赖**: 需要保持稳定的网络连接
5. **时间限制**: 某些功能只在交易时间内可用

---

## 🎯 快速开始

1. 安装 Python 3.10.11 到 `C:\Python310`
2. 创建虚拟环境：`C:\Python310\python.exe -m venv venv_qmt`
3. 安装依赖：`pip install -r requirements.txt`
4. 复制 QMT 模块文件到 `xtquant` 目录
5. 编辑 `config/qmt_config.json`
6. 启动 QMT 客户端并登录
7. 运行 `python scripts/init_qmt.py` 测试连接
8. 参考示例代码开始使用

---

## 📊 性能对比

| 指标 | Python 3.14 + EasyQuotation | Python 3.10 + QMT |
|------|----------------------------|-------------------|
| 数据延迟 | 2-3秒 | 50-100毫秒 |
| 数据质量 | 依赖网络 | 官方数据 |
| 连接方式 | HTTP 轮询 | 推流模式 |
| 交易功能 | 不支持 | 支持 |

---

## 📚 更多资源

- [QMT 官方文档](xtquant/doc/)
- [xtdata API 参考](xtquant/xtdata.py)
- [xttrader API 参考](xtquant/xttrader.py)
- [EasyQuotation 文档](https://github.com/zhidev/easyquotation)
- [AkShare 文档](https://akshare.akfamily.xyz/)

---

## 🎉 完成

恭喜！你已经成功配置了 QMT 环境，系统将使用毫秒级数据延迟的 QMT 接口。

**创建时间**：2026-02-09
**版本**：V2.0
**作者**：iFlow CLI
**状态**：已完成

---

## 📝 更新日志

### V2.0 (2026-02-09)
- 合并 5 个 QMT 配置文档
- 优化文档结构和逻辑顺序
- 添加多数据源架构说明
- 添加常见问题解决方案

### V1.0 (2026-01-28)
- 初始版本
- 包含基础配置步骤