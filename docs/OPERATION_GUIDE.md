---
version: V17.0.0
updated: 2026-02-19
scope: 环境搭建与使用指南
author: MyQuantTool Team
---

# MyQuantTool 运维指南

---

## 1. 环境要求

### 必需

- Python 3.10.11（QMT 依赖）
- Windows 10/11

### 推荐

- QMT 客户端（迅投量化交易终端）
- 8GB+ 内存

---

## 2. 安装步骤

### 2.1 克隆项目

```bash
git clone git@github.com:Stuuu223/MyQuantTool.git
cd MyQuantTool
```

### 2.2 创建虚拟环境

```bash
python -m venv venv_qmt
venv_qmt\Scripts\activate
pip install -r requirements.txt
```

### 2.3 安装 QMT SDK

```bash
pip install xtquant
```

---

## 3. 配置

### 3.1 核心配置文件

| 文件 | 用途 |
|------|------|
| `config/config.json` | 主配置（API Key等） |
| `config/portfolio_config.json` | Portfolio层配置 |
| `config/strategy_params.json` | 策略参数 |
| `config/market_scan_config.json` | 扫描配置 |

### 3.2 路径配置

所有路径通过 `config/paths.py` 统一管理，禁止硬编码。

---

## 4. 启动方式

### 4.1 主入口

```bash
# 事件驱动监控（推荐）
python main.py monitor

# 全市场扫描
python main.py scan

# 竞价扫描
python main.py auction

# CLI监控终端
python main.py cli-monitor
```

### 4.2 交互式启动

```bash
python start_app.py
```

---

## 5. QMT 配置

### 5.1 VIP 配置

```
VIP Token: 从本地配置读取
VIP站点: vipsxmd1/2, dxzzmd1/2, ltzzmd1/2
端口: 55310/55300
```

### 5.2 连接验证

```bash
python tools/system_check.py
```

### 5.3 常见问题

| 问题 | 解决方案 |
|------|----------|
| QMT未登录 | 启动QMT客户端并登录 |
| xtquant DLL错误 | 确认Python 3.10 + 虚拟环境 |
| 连接超时 | 检查VIP站点可用性 |

---

## 6. 数据下载

### 6.1 下载管理器

```bash
python tools/download_manager.py --universe wanzhu_selected --start 20260101 --end 20260219
```

### 6.2 数据目录

| 目录 | 内容 |
|------|------|
| `data/qmt_data/` | QMT历史数据（41GB） |
| `data/minute_data/` | 分钟K线（1GB） |
| `data/wanzhu_data/` | 顽主杯数据 |

---

## 7. 故障排查

### 7.1 日志位置

```
logs/application/   # 应用日志
logs/monitor/       # 监控日志
logs/download/      # 下载日志
```

### 7.2 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `DataNotAvailableError` | QMT未连接 | 启动QMT客户端 |
| `RateLimitError` | AkShare限流 | 等待或减少频率 |
| `ImportError: xtquant` | 环境问题 | 确认venv_qmt |

---

## 8. 开发规范

### 8.1 禁止事项

- 禁止硬编码绝对阈值
- 禁止直接访问 config/ 文件（使用 ConfigService）
- 禁止绕过 ICapitalFlowProvider

### 8.2 代码入口

| 模块 | 入口文件 |
|------|----------|
| 监控 | `tasks/run_event_driven_monitor.py` |
| 扫描 | `logic/strategies/full_market_scanner.py` |
| 资金流 | `logic/data_providers/` |
| 策略 | `logic/services/strategy_service.py` |

---

**详细架构**: 参见 `KNOWLEDGE_BASE_V17.md` 和 `CORE_ARCHITECTURE_V17.md`
