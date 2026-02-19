@echo off
chcp 65001
cls

echo ============================================
echo  查看Tick下载实时日志
echo ============================================
echo.

:: 查找最新的日志文件
set LOG_DIR=E:\MyQuantTool\logs
set LATEST_LOG=

for /f "delims=" %%a in ('dir /b /o-d %LOG_DIR%\tick_download_150_*.log 2^>nul') do (
    set LATEST_LOG=%LOG_DIR%\%%a
    goto :found
)

echo [WARN] 未找到日志文件
pause
exit /b 1

:found
echo [INFO] 正在监控日志文件:
echo %LATEST_LOG%
echo.
echo 按 Ctrl+C 退出监控
echo.

:: 使用PowerShell的Get-Content -Wait来实时监控
powershell -Command "Get-Content -Path '%LATEST_LOG%' -Wait -Tail 50"
