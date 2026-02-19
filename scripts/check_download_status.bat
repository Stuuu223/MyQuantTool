@echo off
chcp 65001
cls

echo ============================================
echo  Tick下载进度检查
echo ============================================
echo.
cd /d E:\MyQuantTool

:: 检查进程是否存在
set PID_FILE=logs\tick_download_150.pid
if exist %PID_FILE% (
    set /p PID=<%PID_FILE%
    tasklist /FI "PID eq %PID%" 2>nul | findstr "python.exe" >nul
    if %ERRORLEVEL% == 0 (
        echo [状态] 下载进程运行中 (PID: %PID%)
    ) else (
        echo [状态] 下载进程已结束 (PID: %PID% 不存在)
    )
) else (
    echo [状态] 未找到PID文件，可能尚未启动
)
echo.

:: 检查日志
echo --- 最新日志 (最后20行) ---
echo.
set LOG_DIR=E:\MyQuantTool\logs
set LATEST_LOG=

for /f "delims=" %%a in ('dir /b /o-d %LOG_DIR%\tick_download_150_*.log 2^>nul') do (
    set LATEST_LOG=%LOG_DIR%\%%a
    goto :show_log
)

echo [WARN] 未找到日志文件
goto :check_data

:show_log
powershell -Command "Get-Content -Path '%LATEST_LOG%' -Tail 20"
echo.

:check_data
echo ============================================
echo  数据目录统计
echo ============================================
echo.

:: 统计深证股票数量
set SZ_DIR=data\qmt_data\datadir\SZ\0
set SH_DIR=data\qmt_data\datadir\SH\0

if exist %SZ_DIR% (
    for /f %%a in ('dir /b %SZ_DIR% 2^>nul ^| find /c /v ""') do (
        echo 深证股票数量: %%a 只
    )
) else (
    echo 深证股票数量: 0 只 (目录不存在)
)

if exist %SH_DIR% (
    for /f %%a in ('dir /b %SH_DIR% 2^>nul ^| find /c /v ""') do (
        echo 上证股票数量: %%a 只
    )
) else (
    echo 上证股票数量: 0 只 (目录不存在)
)

:: 统计磁盘占用
echo.
echo --- 磁盘空间占用 ---
if exist data\qmt_data\datadir (
    for /f "tokens=3" %%a in ('dir /s data\qmt_data\datadir 2^>nul ^| findstr "个文件"') do (
        echo 数据文件总大小: %%a
    )
) else (
    echo 数据目录不存在
)

echo.
pause
