@echo off
REM Predator Guard V10.1.9.1 - 快速启动脚本
REM 作者: iFlow CLI
REM 日期: 2026年1月17日

echo ============================================================
echo Predator Guard V10.1.9.1 - 系统启动
echo ============================================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Python未安装或未配置到PATH
    pause
    exit /b 1
)

echo [1/4] 检查Python环境... OK

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo [2/4] 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo [2/4] 警告: 虚拟环境未找到，使用系统Python
)

REM 清理缓存
echo [3/4] 清理Python缓存...
python -c "import os, shutil; [shutil.rmtree(os.path.join(root, d), ignore_errors=True) for root, dirs, _ in os.walk('.') for d in dirs if d == '__pycache__']" 2>nul

REM 启动系统
echo [4/4] 启动Predator Guard系统...
echo.
echo ============================================================
echo 系统正在启动，请稍候...
echo 浏览器将自动打开 http://localhost:8501
echo ============================================================
echo.

REM 启动Streamlit应用
streamlit run main.py

pause