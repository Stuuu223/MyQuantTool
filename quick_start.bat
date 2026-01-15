@echo off
chcp 65001 >nul
echo ========================================
echo MyQuantTool Quick Start
echo ========================================
echo.

REM 检查 Redis 是否已安装
where redis-server >nul 2>&1
if %errorlevel%==0 (
    echo [1/3] Redis 已安装，正在启动...
    start /B redis-server >nul 2>&1
    timeout /t 2 /nobreak >nul
    echo ✅ Redis 已启动
) else (
    echo [1/3] Redis 未安装，尝试从默认路径启动...
    if exist "C:\redis\redis-server.exe" (
        start /B "C:\redis\redis-server.exe" >nul 2>&1
        timeout /t 2 /nobreak >nul
        echo ✅ Redis 已启动
    ) else (
        echo ⚠️  Redis 未找到，竞价快照功能将不可用
        echo 请运行 start_with_redis.bat 或安装 Redis
    )
)
echo.

REM 激活虚拟环境
echo [2/3] 激活虚拟环境...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo ✅ 虚拟环境已激活
) else (
    echo ❌ 虚拟环境未找到
    pause
    exit /b 1
)
echo.

REM 启动应用
echo [3/3] 启动 MyQuantTool...
echo.
echo ========================================
echo MyQuantTool is starting...
echo ========================================
echo.
echo Press Ctrl+C to stop
echo.

python -m streamlit run main.py

REM 清理
echo.
echo Stopping Redis...
taskkill /F /IM redis-server.exe >nul 2>&1
echo ✅ Redis 已停止

pause