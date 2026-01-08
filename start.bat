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

echo [1/4] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo Error: Python not found
    pause
    exit /b 1
)
echo Python check passed
echo.

echo [2/4] Checking dependencies...
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

echo [3/4] Checking database...
if not exist "data\stock_data.db" (
    echo Warning: Database not found, will be created on first run
)
echo Database check passed
echo.

echo [4/4] Starting application...
echo.
echo ========================================
echo MyQuantTool is starting...
echo ========================================
echo.
echo Application will open in browser
echo Press Ctrl+C to stop
echo.

python -m streamlit run main.py

pause