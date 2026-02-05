@echo off
chcp 65001 > nul
echo ========================================
echo   三漏斗扫描系统 - 启动脚本
echo ========================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python环境，请先安装Python
    pause
    exit /b 1
)

echo [信息] 启动三漏斗扫描系统UI...
echo.

REM 启动Streamlit应用
python -m streamlit run ui/triple_funnel_tab.py

if errorlevel 1 (
    echo.
    echo [错误] 启动失败
    pause
    exit /b 1
)

pause