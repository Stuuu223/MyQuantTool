@echo off
REM 每周优化检查提醒批处理文件

echo ========================================
echo MyQuantTool 每周优化检查
echo ========================================
echo.

REM 运行 Python 脚本
python scripts\weekly_check_reminder.py

echo.
echo ========================================
echo 按任意键退出...
pause > nul