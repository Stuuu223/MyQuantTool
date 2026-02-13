@echo off
setlocal enabledelayedexpansion

chcp 65001 >nul 2>&1

REM Go to project root
cd /d "%~dp0.."
set PROJECT_ROOT=%CD%

echo ========================================
echo Auction Collector (QMT venv)
echo ========================================
echo.

REM Set QMT venv path
set VENV_QMT=%PROJECT_ROOT%\venv_qmt
set PYTHON_QMT=%VENV_QMT%\Scripts\python.exe

REM Check venv
if not exist "%PYTHON_QMT%" (
    echo ERROR: QMT venv not found
    echo Expected: %PYTHON_QMT%
    echo.
    echo Please create venv:
    echo   python -m venv venv_qmt
    echo   venv_qmt\Scripts\activate
    echo   pip install xtquant
    echo.
    pause
    exit /b 1
)

echo INFO: QMT venv: %VENV_QMT%
echo INFO: Python: %PYTHON_QMT%
echo.

REM Check xtquant
"%PYTHON_QMT%" -c "import xtquant" >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: xtquant not installed in QMT venv
    echo.
    echo Please install xtquant:
    echo   venv_qmt\Scripts\activate
    echo   pip install xtquant
    echo.
    pause
    exit /b 1
)

echo INFO: xtquant module OK
echo.

REM Start collector
echo INFO: Starting auction collector...
echo.
"%PYTHON_QMT%" tasks\scheduled_auction_collector.py

echo.
echo INFO: Auction collector exited
pause