#!/bin/bash
# 设置定时任务 - 每天自动采集股票数据

echo "设置股票数据采集定时任务..."

# 获取当前目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 添加到 crontab
crontab -l > /tmp/current_cron 2>/dev/null || true

# 添加定时任务（每天 15:30 收盘后采集）
echo "30 15 * * * cd ${SCRIPT_DIR} && /usr/bin/python3 ${SCRIPT_DIR}/crawl_all_sources.py >> ${SCRIPT_DIR}/cron.log 2>&1" >> /tmp/current_cron

# 去重并安装
sort /tmp/current_cron | uniq | crontab -

echo "定时任务设置完成！"
echo "查看任务: crontab -l"
echo "查看日志: tail -f ${SCRIPT_DIR}/cron.log"
