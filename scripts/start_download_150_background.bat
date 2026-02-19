@echo off
chcp 65001
cls

echo ============================================
echo  顽主杯Top150股票Tick数据下载 - 后台模式
echo  日期范围: 2025-11-15 至 2026-02-13
echo ============================================
echo.

:: 设置工作目录
cd /d E:\MyQuantTool

:: 创建日志目录
if not exist logs mkdir logs

:: 获取当前时间戳
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

:: 日志文件路径
set LOG_FILE=logs\tick_download_150_%TIMESTAMP%.log
set PID_FILE=logs\tick_download_150.pid

echo [INFO] 启动后台下载任务...
echo [INFO] 日志文件: %LOG_FILE%
echo [INFO] PID文件: %PID_FILE%
echo.

:: 在后台启动Python脚本（使用start命令）
start /B "TickDownload150" cmd /c "E:\MyQuantTool\venv_qmt\Scripts\python.exe scripts\download_wanzhu_top150_tick.py ^> %LOG_FILE% 2^>^&1"

:: 记录PID
for /f "tokens=2" %%a in ('tasklist ^| findstr "python.exe"') do (
    echo %%a > %PID_FILE%
    echo [INFO] 下载进程PID: %%a
    goto :done
)

:done
echo.
echo ============================================
echo  下载任务已在后台启动!
echo ============================================
echo.
echo 常用检查命令:
echo   1. 查看实时日志:    tail_logs.bat
echo   2. 检查进度:        check_download_status.bat
echo   3. 查看数据量:      check_data_size.bat
echo   4. 停止下载:        stop_download.bat
echo.
echo 注意: 下载150只股票×3个月数据约需2-4小时
echo       预计占用磁盘空间: 50-100GB
echo.
pause
