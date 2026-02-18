@echo off
chcp 65001 >nul
echo ================================================================================
echo 🚀 Tick下载 + 自动关机 启动脚本
echo ================================================================================
echo.
echo 正在启动Python脚本...
echo.

cd /d "%~dp0.."
python scripts\start_download_and_shutdown.py

if errorlevel 1 (
    echo.
    echo ❌ 脚本执行失败
    pause
)