@echo off
chcp 65001 >nul
echo ========================================
echo MyQuantTool Start Script (Redis Service)
echo ========================================
echo.

REM 这个脚本假设 Redis 已安装为 Windows 服务
REM 如果没有，请使用 start_with_redis.bat 或手动安装 Redis 服务

REM ========================================
REM Step 1: 启动 Redis 服务
REM ========================================
echo [1/5] Starting Redis service...
sc query Redis | find /I "RUNNING" >nul
if %errorlevel%==0 (
    echo Redis service is already running
) else (
    sc start Redis >nul 2>&1
    if %errorlevel%==0 (
        echo Redis service started successfully
    ) else (
        echo Warning: Failed to start Redis service
        echo Please ensure Redis is installed as a Windows service
        echo Or use start_with_redis.bat instead
        echo.
        set /p continue="Continue without Redis? (y/n): "
        if /i not "%continue%"=="y" (
            pause
            exit /b 1
        )
    )
)
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
REM Step 5: 检查数据库
REM ========================================
echo [5/5] Checking database...
if not exist "data\stock_data.db" (
    echo Warning: Database not found, will be created on first run
)
echo Database check passed
echo.

REM ========================================
REM 启动应用
REM ========================================
echo ========================================
echo MyQuantTool is starting...
echo ========================================
echo.
echo Application will open in browser
echo Press Ctrl+C to stop
echo.

python -m streamlit run main.py

pause