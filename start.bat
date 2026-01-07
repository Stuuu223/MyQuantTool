@echo off
echo ========================================
echo MyQuantTool 启动脚本
echo ========================================
echo.

echo [1/4] 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: 未找到Python
    pause
    exit /b 1
)
echo Python环境检查通过
echo.

echo [2/4] 检查依赖...
python -c "import pandas, streamlit, plotly, akshare, sqlalchemy"
if %errorlevel% neq 0 (
    echo 警告: 部分依赖缺失，请运行 install_dependencies.bat
    echo.
    set /p continue="是否继续启动? (y/n): "
    if /i not "%continue%"=="y" (
        pause
        exit /b 1
    )
)
echo 依赖检查通过
echo.

echo [3/4] 检查数据库...
if not exist "data\stock_data.db" (
    echo 警告: 数据库不存在，首次运行将自动创建
)
echo 数据库检查通过
echo.

echo [4/4] 启动应用...
echo.
echo ========================================
echo MyQuantTool 正在启动...
echo ========================================
echo.
echo 应用将在浏览器中打开
echo 按 Ctrl+C 停止应用
echo.

streamlit run main.py

pause