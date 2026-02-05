@echo off
chcp 65001 >nul
echo ========================================
echo 导出事件记录表格
echo ========================================
echo.
echo 功能：
echo - 导出事件记录为Excel表格
echo - 显示事件统计信息
echo - 支持筛选和排序
echo.
echo 输出文件：
echo - data/event_records.xlsx (Excel表格)
echo - data/event_records.csv (CSV表格)
echo.
echo 按任意键开始导出...
pause >nul

python export_event_records.py

echo.
echo 按任意键退出...
pause >nul