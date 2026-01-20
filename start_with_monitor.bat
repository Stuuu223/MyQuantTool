@echo off
chcp 65001 >nul
echo ========================================
echo MyQuantTool Start Script (With Monitor)
echo ========================================
echo.

REM ========================================
REM Step 1: 启动定时任务监控
REM ========================================
echo [1/5] Starting scheduled task monitor...
start /B python logic/scheduled_task_monitor.py > logs/monitor.log 2>&1
echo Scheduled task monitor started
echo.

REM ========================================
REM Step 2: 激活虚拟环境
REM ========================================
echo [2/5] Activating virtual environment...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo Virtual environment activated
) else (
    echo Warning: Virtual environment not found
    echo Please run install_dependencies.bat first
    pause
    exit /b 1
)
echo.

REM ========================================
REM Step 3: 检查 Python
REM ========================================
echo [3/5] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo Error: Python not found
    pause
    exit /b 1
)
echo Python check passed
echo.

REM ========================================
REM Step 4: 检查依赖
REM ========================================
echo [4/5] Checking dependencies...
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

REM ========================================
REM Step 5: 启动应用
REM ========================================
echo [5/5] Starting application...
echo.
echo ========================================
echo MyQuantTool is starting...
echo ========================================
echo.
echo Application will open in browser
echo Press Ctrl+C to stop
echo.
echo 📅 Scheduled tasks:
echo    - 09:10: 早盘前检查 (Redis + 竞价快照)
echo    - 15:30: 收盘后复盘
echo    - 周日 20:00: 每周系统检查
echo.
echo 📊 Monitor logs: logs/monitor.log
echo.

python -m streamlit run main.py

pause