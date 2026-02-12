@echo off
chcp 65001 >nul
echo ========================================
echo Stock Analysis Tool
echo ========================================
echo.

call %~dp0venv_qmt\Scripts\python.exe %~dp0quick_analyze.py %*

pause