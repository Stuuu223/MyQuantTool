@echo off
setlocal enabledelayedexpansion

chcp 65001 >nul 2>&1

REM Go to project root
cd /d "%~dp0.."
set PROJECT_ROOT=%CD%

echo ========================================
echo Auction Collector Test (QMT venv)
echo ========================================
echo.

REM Set QMT venv path
set VENV_QMT=%PROJECT_ROOT%\venv_qmt
set PYTHON_QMT=%VENV_QMT%\Scripts\python.exe

REM Check venv
if not exist "%PYTHON_QMT%" (
    echo ERROR: QMT venv not found
    echo Expected: %PYTHON_QMT%
    pause
    exit /b 1
)

echo INFO: QMT venv: %VENV_QMT%
echo INFO: Python: %PYTHON_QMT%
echo.

REM Run test
echo INFO: Running tests...
echo.
"%PYTHON_QMT%" tools\test_auction_collector.py

echo.
echo INFO: Test completed
pause