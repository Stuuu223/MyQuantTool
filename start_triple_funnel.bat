@echo off
chcp 65001 > nul
echo ========================================
echo   Triple Funnel Scanner - Startup
echo ========================================
echo.

REM Check if venv_qmt exists
if not exist "venv_qmt\Scripts\activate.bat" (
    echo [ERROR] QMT virtual environment not found: venv_qmt
    echo Please run: C:\Python310\python.exe -m venv venv_qmt
    pause
    exit /b 1
)

REM Activate virtual environment
call venv_qmt\Scripts\activate.bat

REM Check Python environment
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in virtual environment
    pause
    exit /b 1
)

echo [INFO] Using QMT virtual environment: venv_qmt
echo [INFO] Starting Triple Funnel Scanner UI...
echo.

REM Start Streamlit app (no auto-open browser)
python -m streamlit run ui/triple_funnel_tab.py --server.headless true

if errorlevel 1 (
    echo.
    echo [ERROR] Startup failed
    pause
    exit /b 1
)

pause