@echo off
chcp 65001 >nul
echo ========================================
echo MyQuantTool Start Script
echo ========================================
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo Virtual environment activated
    echo.
)

echo [1/5] Checking Redis service...
sc query Redis | find /I "RUNNING" >nul
if %errorlevel%==0 (
    echo Redis service is already running
) else (
    echo Redis service is not running, attempting to start...
    sc start Redis >nul 2>&1
    if %errorlevel%==0 (
        echo Redis service started successfully
    ) else (
        echo.
        echo ========================================
        echo WARNING: Redis service failed to start
        echo ========================================
        echo.
        echo Possible reasons:
        echo   - Redis is not installed as a Windows service
        echo   - Redis service name is not "Redis"
        echo   - Insufficient permissions
        echo.
        echo Impact:
        echo   - Real-time data caching will be disabled
        echo   - System will use SQLite as fallback
        echo   - Some features may run slower
        echo.
        echo To fix this issue:
        echo   1. Install Redis as Windows service, OR
        echo   2. Run Redis manually: redis-server.exe, OR
        echo   3. Ignore this warning (system will work with degraded features)
        echo.
        set /p continue="Continue without Redis? (y/n): "
        if /i not "%continue%"=="y" (
            pause
            exit /b 1
        )
    )
)
echo.

echo [2/5] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo Error: Python not found
    pause
    exit /b 1
)
echo Python check passed
echo.

echo [3/5] Checking dependencies...
python -c "import pandas, streamlit, plotly, akshare, sqlalchemy"
if %errorlevel% neq 0 (
    echo Warning: Some dependencies missing, please run install_dependencies.bat
    echo.
    set /p continue="Continue? (y/n): "
    if /i not "%continue%"=="y" (
        pause
        exit /b 1
    )
)
echo Dependencies check passed
echo.

echo [4/5] Checking database...
if not exist "data\stock_data.db" (
    echo Warning: Database not found, will be created on first run
)
echo Database check passed
echo.

echo [5/5] Starting scheduled task monitor...
echo.
echo ========================================
echo MyQuantTool is starting...
echo ========================================
echo.
echo 📅 Scheduled tasks:
echo    - 09:10: 早盘前检查 (Redis + 竞价快照)
echo    - 09:20: 盘前MA4预计算
echo    - 09:25: 竞价快照自动保存 ⭐
echo    - 15:30: 收盘后复盘
echo    - 周日 20:00: 每周系统检查
echo.
echo 🚀 Starting scheduled task monitor in separate window...
start "MyQuantTool - 定时任务监控" /min python logic/scheduled_task_monitor.py
echo ✅ Scheduled task monitor started (minimized window)
echo 💡 提示: 定时任务监控器在独立窗口运行，关闭本窗口不会影响定时任务
echo.
echo Application will open in browser
echo Press Ctrl+C to stop
echo.
echo Auto-reload enabled:
echo    - Code changes trigger automatic reload
echo    - No manual restart needed
echo    - Press R or click "Rerun" to refresh
echo.

python -m streamlit run main.py

pause