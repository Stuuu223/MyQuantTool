@echo off
chcp 65001 >nul
echo ========================================
echo MyQuantTool 快速启动脚本
echo ========================================
echo.

REM 激活虚拟环境
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [1/3] 虚拟环境已激活
) else (
    echo [1/3] 警告: 虚拟环境未找到
)
echo.

REM 检查Redis
echo [2/3] 检查Redis服务...
tasklist | findstr redis-server >nul
if %errorlevel%==0 (
    echo ✅ Redis服务正在运行
) else (
    echo ⚠️  Redis服务未运行
    echo 💡 建议运行: start_with_redis.bat
)
echo.

REM 启动应用
echo [3/3] 启动应用...
echo.
echo ========================================
echo 🚀 应用正在启动...
echo ========================================
echo.
echo 💡 提示:
echo   - 首次启动可能需要10-30秒
echo   - 复盘操作将在后台异步执行
echo   - 如遇卡顿，请等待或刷新页面
echo.

python -m streamlit run main.py

pause