# 定时任务设置指南

## 📋 概述

本文档说明如何设置定时任务，每天收盘后自动收集 Tushare THS 资金流向数据。

## 🎯 功能

- **自动执行**：每天收盘后自动执行
- **邮件通知**：收集成功/失败后发送邮件通知
- **微信通知**：通过企业微信机器人发送通知
- **数据存储**：数据保存至 `data/tushare_ths_moneyflow/` 目录

---

## 🔧 配置步骤

### 1. 配置邮件通知

编辑 `tasks/daily_tushare_ths_collector.py`：

```python
# 邮件配置
EMAIL_RECIPIENT = "your_email@gmail.com"  # 改为你的邮箱

# 初始化邮件服务
email_service = EmailAlertService(
    smtp_server='smtp.gmail.com',
    smtp_port=587,
    sender_email="your_email@gmail.com",  # 改为你的邮箱
    sender_password="your_app_password"   # 改为你的应用密码
)
```

**Gmail 应用密码获取方法：**
1. 打开 Google 账户设置
2. 进入"安全性" → "两步验证"
3. 启用"应用密码"
4. 生成一个应用密码（用于脚本）

**其他邮箱配置：**
- **QQ邮箱**: `smtp.qq.com`, 端口 `587`
- **163邮箱**: `smtp.163.com`, 端口 `465`
- **Outlook**: `smtp-mail.outlook.com`, 端口 `587`

---

### 2. 配置微信通知（可选）

编辑 `tasks/daily_tushare_ths_collector.py`，添加：

```python
from logic.wechat_notification_service import wechat_service

# 配置微信通知
wechat_service.configure("your_webhook_url")
```

**企业微信机器人 Webhook 获取方法：**
1. 打开企业微信群
2. 点击右上角 "..." → "群机器人" → "添加机器人"
3. 选择 "新建机器人"
4. 复制 Webhook URL

---

### 3. 设置 Windows 任务计划程序

#### 方法一：使用任务计划程序（推荐）

**步骤：**

1. **打开任务计划程序**
   - 按 `Win + R`，输入 `taskschd.msc`，回车

2. **创建基本任务**
   - 右侧点击"创建基本任务"
   - 名称：`Daily THS Moneyflow Collector`
   - 描述：`每天收盘后收集 Tushare THS 资金流向数据`
   - 点击"下一步"

3. **设置触发器**
   - 选择"每天"
   - 开始时间：`15:30:00`（下午 3:30，收盘后）
   - 重复周期：`每天`
   - 点击"下一步"

4. **设置操作**
   - 选择"启动程序"
   - 程序或脚本：`C:\Python310\python.exe`（你的 Python 路径）
   - 添加参数：`E:\MyQuantTool\tasks\daily_tushare_ths_collector.py`
   - 起始于：`E:\MyQuantTool`
   - 点击"下一步"

5. **完成**
   - 点击"完成"
   - 勾选"打开此任务属性的对话框"
   - 点击"完成"

6. **高级设置（可选）**
   - 在"条件"标签页：
     - 勾选"只有在计算机连接到网络时才启动此任务"
     - 勾选"如果计算机使用电池电源则停止"
   - 在"设置"标签页：
     - 勾选"如果任务失败，按以下频率重新启动"
     - 间隔：`5分钟`
     - 重试次数：`3次`

---

#### 方法二：使用批处理文件

**创建批处理文件 `run_daily_ths_collector.bat`：**

```batch
@echo off
cd /d E:\MyQuantTool
python tasks\daily_tushare_ths_collector.py
pause
```

**设置任务计划程序：**
- 程序或脚本：`E:\MyQuantTool\run_daily_ths_collector.bat`
- 其他步骤同上

---

#### 方法三：使用 PowerShell

**创建 PowerShell 脚本 `run_daily_ths_collector.ps1`：**

```powershell
cd E:\MyQuantTool
python tasks\daily_tushare_ths_collector.py
```

**设置任务计划程序：**
- 程序或脚本：`powershell.exe`
- 添加参数：`-ExecutionPolicy Bypass -File "E:\MyQuantTool\run_daily_ths_collector.ps1"`
- 其他步骤同上

---

### 4. 测试定时任务

**手动测试：**

```bash
cd E:\MyQuantTool
python tasks\daily_tushare_ths_collector.py
```

**检查输出：**
- 日志文件：`logs/app.log`
- 数据文件：`data/tushare_ths_moneyflow/ths_moneyflow_YYYYMMDD.json`
- 邮件/微信通知

---

## 📊 数据格式

### JSON 文件结构

```json
{
  "trade_date": "20250812",
  "collect_time": "2026-02-08 15:30:00",
  "record_count": 1234,
  "data": [
    {
      "trade_date": "20250812",
      "ts_code": "000001.SZ",
      "name": "平安银行",
      "pct_change": 2.5,
      "latest": 10.5,
      "net_amount": 123456.78,
      "net_d5_amount": 987654.32,
      "buy_lg_amount": 500000.0,
      "buy_lg_amount_rate": 45.5,
      "buy_md_amount": 300000.0,
      "buy_md_amount_rate": 27.3,
      "buy_sm_amount": 200000.0,
      "buy_sm_amount_rate": 18.2
    }
  ]
}
```

---

## 🔍 故障排查

### 1. 任务未执行

**检查步骤：**
1. 打开任务计划程序
2. 找到任务"Daily THS Moneyflow Collector"
3. 查看历史记录
4. 检查"上次运行结果"

**常见问题：**
- ❌ Python 路径错误 → 检查 `程序或脚本` 路径
- ❌ 文件路径错误 → 检查 `添加参数` 和 `起始于` 路径
- ❌ 权限不足 → 右键任务 → 属性 → 勾选"使用最高权限运行"

---

### 2. 脚本执行失败

**检查日志：**
```bash
tail -f logs/app.log
```

**常见问题：**
- ❌ Tushare 限流 → 等待明天再试
- ❌ 邮件配置错误 → 检查邮箱和密码
- ❌ 网络问题 → 检查网络连接

---

### 3. 未收到通知

**邮件通知：**
- 检查垃圾邮件箱
- 确认邮箱和密码正确
- 确认 SMTP 服务器配置正确

**微信通知：**
- 确认 Webhook URL 正确
- 确认机器人未被封禁
- 检查网络连接

---

## 📝 注意事项

1. **Tushare 限流**
   - THS 接口有限流（每分钟/每小时最多 2 次）
   - 如果触发限流，脚本会记录日志，明天重试
   - 不要在短时间内多次运行

2. **数据存储**
   - 数据保存在 `data/tushare_ths_moneyflow/` 目录
   - 每天一个文件，文件名格式：`ths_moneyflow_YYYYMMDD.json`
   - 建议定期清理旧数据

3. **通知频率**
   - 每天只发送一次通知
   - 成功和失败都会通知
   - 避免通知过于频繁

---

## 🚀 后续扩展

### 1. 添加更多通知渠道

- **钉钉机器人**：参考微信通知实现
- **飞书机器人**：参考微信通知实现
- **Slack**：使用 Slack API

### 2. 添加数据处理逻辑

- 数据清洗
- 数据分析
- 数据可视化

### 3. 集成到主系统

- 历史快照重建
- 回测框架
- 决策树

---

## 📞 支持

如有问题，请查看：
1. 日志文件：`logs/app.log`
2. 错误信息：邮件/微信通知
3. Tushare 文档：https://tushare.pro/document/2

---

**最后更新：2026-02-08**