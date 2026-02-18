# 顽主杯小程序数据采集系统

## 架构概述

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   本地抓包      │────▶│  Linux服务器    │────▶│  MyQuantTool    │
│ (Charles/Proxyman)│    │ (Python+cron)   │    │  (量化分析)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │  CSV历史数据    │
                        │  日文件+总表    │
                        └─────────────────┘
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `wanzhu_miniprogram_config.json` | API配置（需根据抓包结果填写） |
| `crawl_wanzhu_miniprogram.py` | 主采集脚本 |
| `setup.sh` | 环境安装脚本 |
| `wanzhu_miniprogram_YYYYMMDD.csv` | 每日数据文件 |
| `wanzhu_miniprogram_history.csv` | 历史总表 |
| `wanzhu_history_from_miniprogram.csv` | MyQuantTool兼容格式 |

## 快速开始

### 1. 本地抓包（一次性）

使用 Charles 或 Proxyman 抓取顽主杯小程序API：

```
目标接口: 榜单查询接口
关键信息: URL + Headers + 参数
```

### 2. 服务器部署

```bash
# 运行安装脚本
cd /root/wanzhu_data
bash setup.sh

# 编辑配置文件
vim wanzhu_miniprogram_config.json
```

### 3. 配置说明

```json
{
  "base_url": "https://api.hunanwanzhu.com/miniprogram/rankings",
  "default_params": {
    "page": 1,
    "size": 200
  },
  "headers": {
    "User-Agent": "...",
    "Referer": "..."
  }
}
```

### 4. 测试运行

```bash
cd /root/wanzhu_data
./venv/bin/python crawl_wanzhu_miniprogram.py
```

### 5. 设置定时任务

```bash
crontab -e

# 添加以下行（每天16:10执行）
10 16 * * * cd /root/wanzhu_data && /root/wanzhu_data/venv/bin/python crawl_wanzhu_miniprogram.py >> crawl.log 2>&1
```

## 数据格式

### 标准字段

| 字段 | 说明 |
|------|------|
| date | 日期 (YYYYMMDD) |
| code | 股票代码 (6位) |
| name | 股票名称 |
| rank | 排名 |
| sector | 所属板块/行业 |
| holder_count | 持股人数 |
| holding_amount | 持仓金额 |
| change_pct | 涨跌幅 |
| score | 得分 |

## 注意事项

1. **抓包合规**: 只抓取公开榜单数据，不涉及敏感信息
2. **频率控制**: 脚本内置随机延时，避免触发风控
3. **数据备份**: 建议定期备份 `wanzhu_miniprogram_history.csv`
4. **配置更新**: 如API变更，只需更新配置文件，无需修改代码

## 故障排查

```bash
# 查看日志
tail -f /root/wanzhu_data/crawl.log

# 手动测试指定日期
./venv/bin/python crawl_wanzhu_miniprogram.py 20260218

# 检查配置文件格式
python3 -m json.tool wanzhu_miniprogram_config.json
```