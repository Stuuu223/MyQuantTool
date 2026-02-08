# THS Collector 快速使用指南

## 📋 概述

`daily_tushare_ths_collector.py` 是一个定时任务脚本，每天收盘后自动收集 Tushare THS 资金流向数据。

## 🚀 使用方法

### 手动运行

```bash
cd E:\MyQuantTool
python tasks\daily_tushare_ths_collector.py
```

### 设置定时任务

#### Windows 任务计划程序

1. 打开任务计划程序（`taskschd.msc`）
2. 创建基本任务
3. 设置触发器：每天 22:30（晚上 10:30）
4. 设置操作：
   - 程序：`E:\MyQuantTool\run_daily_ths_collector.bat`
   - 起始于：`E:\MyQuantTool`

#### 推荐执行时间

- **最佳时间**：22:30（晚上 10:30）
  - 收盘后，数据已更新
  - 避开 Tushare 高峰期
  - 不影响白天开发

## 📊 输出文件

### 文件位置

```
data/tushare_ths_moneyflow/ths_moneyflow_YYYYMMDD.json
```

### 文件格式

```json
{
  "trade_date": "20250812",
  "collect_time": "2026-02-08 22:30:00",
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

## 🔔 通知

### 通知方式

- ✅ **微信通知**：企业微信群
- ✅ **邮件通知**：stu223@qq.com

### 通知内容

- **成功**：记录数量、收集时间、文件位置
- **失败**：错误信息、重试时间

## ⚠️ 注意事项

### 1. Tushare 限流

- THS 接口有限流（每分钟/每小时最多 2 次）
- 如果触发限流，脚本会记录日志，明天重试
- 不要在短时间内多次运行

### 2. 执行频率

- **每天最多执行 1 次**
- 如果失败，不重试
- 第二天定时任务会自动重试

### 3. 数据存储

- 数据保存在 `data/tushare_ths_moneyflow/` 目录
- 每天一个文件
- 建议定期清理旧数据（保留最近 30 天）

## 📝 日志

### 日志位置

```
logs/app.log
```

### 日志级别

- INFO：正常执行
- WARNING：限流警告
- ERROR：执行失败

## 🔍 故障排查

### 1. 脚本执行失败

**检查步骤：**
1. 查看日志：`logs/app.log`
2. 检查网络连接
3. 确认 Tushare token 有效

### 2. 未收到通知

**微信通知：**
- 确认 Webhook URL 正确
- 确认机器人未被封禁
- 检查网络连接

**邮件通知：**
- 检查垃圾邮件箱
- 确认授权码有效
- 检查 SMTP 配置

### 3. 限流错误

**处理方式：**
- 等待第二天定时任务自动重试
- 不要手动多次运行
- 限流是 Tushare 的正常风控机制

## 📞 配置

### 微信通知

编辑 `tasks/daily_tushare_ths_collector.py`：

```python
wechat_service.configure("your_webhook_url")
```

### 邮件通知

编辑 `tasks/daily_tushare_ths_collector.py`：

```python
email_service = EmailAlertService(
    smtp_server='smtp.qq.com',
    smtp_port=587,
    sender_email='your_email@qq.com',
    sender_password='your_authorization_code'
)
```

## 🎯 下一步

### 数据用途

1. **离线研究**：积累样本后，做三源方向一致率分析
2. **回测增强**：未来可能用于回测
3. **特征工程**：作为额外特征，提升模型性能

### 三源对比

当积累了足够样本后，运行：

```bash
python temp/test_moneyflow_ths_final.py
```

对比 eastmoney、标准 moneyflow、THS 三种数据源的方向一致率。

---

**最后更新：2026-02-08**