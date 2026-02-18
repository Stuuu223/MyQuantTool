#!/bin/bash
# 顽主杯定时任务设置

echo "设置顽主杯每日自动采集..."

# 添加定时任务（每天16:30采集）
(crontab -l 2>/dev/null; echo "30 16 * * * cd /root/wanzhu_data && /usr/bin/python3 crawl_wanzhu_production.py 1 >> crawl_wanzhu.log 2>&1") | crontab -

echo "✓ 定时任务已设置"
echo "每天16:30自动采集顽主杯数据"
echo ""
echo "查看定时任务: crontab -l"
echo "查看日志: tail -f /root/wanzhu_data/crawl_wanzhu.log"