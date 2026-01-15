@echo off
chcp 65001 >nul
echo ========================================
echo MyQuantTool Start Script (with Redis)
echo ========================================
echo.

REM 设置 Redis 路径（根据你的实际安装路径修改）
set REDIS_PATH=C:\redis
set REDIS_SERVER=%REDIS_PATH%\redis-server.exe
set REDIS_CONFIG=%REDIS_PATH%\redis.windows.conf

REM ========================================
REM Step 1: 检查并启动 Redis
REM ========================================
echo [1/5] Checking Redis...
if exist "%REDIS_SERVER%" (
    echo Redis found at: %REDIS_SERVER%
    
    REM 检查 Redis 是否正在运行
    tasklist /FI "IMAGENAME eq redis-server.exe" 2>NUL | find /I /N "redis-server.exe">NUL
    if "%ERRORLEVEL%"=="0" (
        echo Redis is already running
    ) else (
        echo Starting Redis...
        start /B "" "%REDIS_SERVER%" "%REDIS_CONFIG%"
        timeout /t 2 /nobreak >nul
        
        REM 检查 Redis 是否成功启动
        tasklist /FI "IMAGENAME eq redis-server.exe" 2>NUL | find /I /N "redis-server.exe">NUL
        if "%ERRORLEVEL%"=="0" (
            echo Redis started successfully
        ) else (
            echo Warning: Redis failed to start, auction snapshot feature will be unavailable
        )
    )
    echo.
) else (
    echo Warning: Redis not found at %REDIS_PATH%
    echo Please install Redis or modify REDIS_PATH in this script
    echo Download Redis for Windows: https://github.com/microsoftarchive/redis/releases
    echo Auction snapshot feature will be unavailable
    echo.
    set /p continue="Continue without Redis? (y/n): "
    if /i not "%continue%"=="y" (
        pause
        exit /b 1
    )
    echo.
)

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

REM ========================================
REM 清理：关闭 Redis（可选）
REM ========================================
echo.
echo Stopping Redis...
taskkill /F /IM redis-server.exe >nul 2>&1
echo Redis stopped

pause