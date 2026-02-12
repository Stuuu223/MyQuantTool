@echo off
chcp 65001 > nul
title MyQuantTool Pre-Market Auto Execution

echo.
echo ========================================
echo   MyQuantTool Pre-Market Auto Execution
echo ========================================
echo.

REM Check virtual environment
if not exist "venv_qmt\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found: venv_qmt
    echo Please create virtual environment first
    pause
    exit /b 1
)

echo [INFO] Using virtual environment: venv_qmt
echo.

REM Check parameters
if "%1"=="" (
    echo [INFO] Scheduled mode: waiting for trigger time
    echo.
    echo Usage:
    echo   start_premarket.bat           - Scheduled mode (default)
    echo   start_premarket.bat immediate - Execute all tasks immediately
    echo   start_premarket.bat warmup    - Execute data warmup only
    echo   start_premarket.bat check     - Execute QMT check only
    echo   start_premarket.bat auction   - Execute auction collection only
    echo   start_premarket.bat monitor   - Start monitor only
    echo.
    echo Press any key to continue, or Ctrl+C to exit...
    pause > nul
) else (
    echo [INFO] Mode: %1
    echo.
)

REM Run Python script
call venv_qmt\Scripts\python.exe tasks\scheduled_premarket.py %*

echo.
echo ========================================
echo   Program exited
echo ========================================
pause