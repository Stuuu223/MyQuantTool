@echo off
echo ========================================
echo 顽主杯Top 50股票Tick数据下载
echo ========================================
echo.
echo 日期范围: 2025-01-25 至 2026-02-13
echo.

cd /d E:\MyQuantTool

start /B venv_qmt\Scripts\python.exe scripts\download_wanzhu_tick_data.py > logs\wanzhu_tick_download.log 2>&1

echo 下载任务已在后台启动
echo 查看日志: logs\wanzhu_tick_download.log
echo.
pause
