# QMT 历史数据下载使用说明

## 📋 概述

`qmt_background_downloader.py` 是一个后台数据下载脚本，用于从 QMT 下载历史 K 线数据。

## 🚀 快速开始

### 前置条件

**重要：QMT 客户端必须正在运行！**

在运行下载脚本之前，请确保：
1. ✅ QMT 客户端已安装（QMT-投研版或 QMT-极速版）
2. ✅ QMT 客端正在运行
3. ✅ 数据服务已开启
4. ✅ xtquant 库已正确安装

### 检查 QMT 连接

运行测试脚本检查 QMT 连接：

```bash
python temp\test_qmt_interface.py
```

如果看到以下错误：
```
❌ 无法连接xtquant服务，请检查QMT-投研版或QMT-极简版是否开启
```

请：
1. 启动 QMT 客户端
2. 确保数据服务已开启
3. 重新运行测试脚本

### 方式 1：使用批处理文件（推荐）

```bash
E:\MyQuantTool\run_qmt_downloader.bat
```

### 方式 2：使用 Python 命令

```bash
cd E:\MyQuantTool
python tasks\qmt_background_downloader.py
```

## ⚙️ 配置

### 1. 股票列表

编辑 `config/qmt_download_config.json`：

```json
{
  "stock_lists": {
    "test": ["600519.SH", "000001.SZ", "600000.SH"],
    "sh50": [],
    "sz50": [],
    "all": []
  }
}
```

### 2. 下载周期

```json
{
  "periods": ["1d", "1m", "5m"]
}
```

- `1d`: 日线
- `1m`: 1 分钟线
- `5m`: 5 分钟线

### 3. 时间范围

```json
{
  "date_range": {
    "start_date": "20240101",
    "end_date": "20251231"
  }
}
```

### 4. 进度输出

```json
{
  "progress_settings": {
    "progress_interval": 600,
    "progress_file": "data/qmt_download_progress.json",
    "log_file": "logs/qmt_download.log"
  }
}
```

- `progress_interval`: 进度输出间隔（秒），默认 600 秒（10 分钟）

## 📊 进度监控

### 方式 1：查看进度文件

```bash
python -c "import json; print(json.dumps(json.load(open('data/qmt_download_progress.json', 'r', encoding='utf-8')), indent=2))"
```

### 方式 2：查看日志文件

```bash
tail -f logs/qmt_download.log
```

### 方式 3：查看终端输出

脚本会每 10 分钟自动输出一次进度到终端：

```
============================================================
QMT 历史数据下载进度
时间: 2026-02-08 11:00:00
============================================================
📊 总进度:
  总股票数: 3
  已完成: 6
  完成率: 66.7%

📅 周期进度:
  总周期数: 3
  已完成周期: 2

📁 当前批次: Period_2_1m
📅 开始时间: 2026-02-08 10:50:00
📅 最后更新: 2026-02-08 11:00:00

============================================================
```

## 🛑 停止下载

### 方式 1：Ctrl+C

在运行脚本的终端按 `Ctrl+C` 停止下载。

### 方式 2：停止脚本

脚本支持后台运行，可以使用任务管理器停止。

## 📁 数据存储

### 存储位置

QMT 数据存储在 QMT 客户端的 `userdata_mini/datadir` 目录中。

### 查看数据目录

运行以下命令查看数据目录：

```python
from xtquant import xtdata
print(xtdata.get_data_dir())
```

## 🔍 验证数据

### 验证下载的数据

```python
from xtquant import xtdata
from logic.code_converter import CodeConverter

code_converter = CodeConverter()
qmt_code = code_converter.to_qmt('600519.SH')

data = xtdata.get_local_data(
    field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
    stock_list=[qmt_code],
    period='1d',
    start_time='20240101',
    end_time='20251231',
    count=-1
)

if data and qmt_code in data:
    df = data[qmt_code]
    print(f"✅ 验证成功: {len(df)} 条记录")
    print(df.head())
else:
    print("❌ 验证失败: 数据为空")
```

## 📈 数据用途

### 1. 日内回测

使用 1 分钟或 5 分钟 K 线进行日内回测：

```python
# 获取 1 分钟线
data = xtdata.get_local_data(
    field_list=['time', 'open', 'high', 'low', 'close', 'volume'],
    stock_list=[qmt_code],
    period='1m',
    start_time='20240101',
    end_time='20240131',
    count=-1
)
```

### 2. 日内决策增强

- 盘中止损/止盈
- 分批卖出
- 追踪日内价格走势

### 3. 与 Tushare 日线对比

```python
# Tushare 日线
import tushare as ts
ts_data = ts.pro_bar(ts_code='600519.SH', start_date='20240101', end_date='20240131', adj='qfq')

# QMT 日线
qmt_data = xtdata.get_local_data(...)

# 对比分析
```

## ⚠️ 注意事项

### 1. QMT 客户端必须运行

- 确保 QMT 客户端正在运行
- 确保数据服务已开启

### 2. 存储空间

- 全市场两年 1 分钟线数据量很大
- 建议使用大盘存储
- 定期清理旧数据

### 3. 下载时间

- 全市场下载可能需要几天时间
- 建议分批下载

### 4. 网络连接

- 保持网络稳定
- 避免频繁断开

## 📞 常见问题

### Q1: QMT 接口不可用

**错误信息：**
```
❌ QMT 接口加载失败
```

**解决方案：**
1. 检查 QMT 客户端是否运行
2. 检查 xtquant 库是否正确安装
3. 检查 QMT 数据服务是否开启

### Q2: 下载失败

**错误信息：**
```
❌ 下载失败: 600519.SH (1d) - ...
```

**解决方案：**
1. 检查网络连接
2. 检查 QMT 客户端状态
3. 检查股票代码是否正确

### Q3: 数据验证失败

**错误信息：**
```
⚠️ 验证失败: 600519.SH (1d) - 数据为空
```

**解决方案：**
1. 检查时间范围是否正确
2. 检查股票代码是否正确
3. 重新下载数据

## 📝 下一步

下载完成后，可以：

1. **验证数据**：使用验证脚本检查数据完整性
2. **接入系统**：将 QMT 数据接入现有系统
3. **回测框架**：使用 QMT 数据进行回测
4. **日内决策**：增强日内决策逻辑

---

**最后更新：2026-02-08**