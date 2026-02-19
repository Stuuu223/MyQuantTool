@echo off
chcp 65001
cls

echo ============================================
echo  停止Tick下载任务
echo ============================================
echo.

set PID_FILE=E:\MyQuantTool\logs\tick_download_150.pid

if not exist %PID_FILE% (
    echo [WARN] 未找到PID文件，可能未在运行
    echo.
    echo 是否要强制结束所有Python进程?
    choice /C YN /M "确认"
    if %ERRORLEVEL% == 1 (
        echo 正在结束python.exe进程...
        taskkill /F /IM python.exe 2>nul
        echo [OK] 已结束
    )
    pause
    exit /b
)

set /p PID=<%PID_FILE%
echo [INFO] 找到下载进程 (PID: %PID%)
echo.

:: 检查进程是否存在
tasklist /FI "PID eq %PID%" 2>nul | findstr "python.exe" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] 进程已不存在 (PID: %PID%)
    del %PID_FILE%
    pause
    exit /b
)

:: 尝试优雅终止
echo [INFO] 正在停止下载进程...
taskkill /PID %PID% 2>nul

:: 等待进程结束
echo [INFO] 等待进程结束...
timeout /t 3 /nobreak >nul

:: 检查是否还在运行
tasklist /FI "PID eq %PID%" 2>nul | findstr "python.exe" >nul
if %ERRORLEVEL% == 0 (
    echo [WARN] 进程未响应，强制终止...
    taskkill /F /PID %PID%
)

:: 清理PID文件
del %PID_FILE%

echo.
echo [OK] 下载任务已停止
echo.
pause
