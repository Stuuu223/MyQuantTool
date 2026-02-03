@echo off
chcp 65001 >nul
echo ========================================
echo    一键式股票分析工具
echo ========================================
echo.

%~dp0venv_qmt\Scripts\python.exe %~dp0quick_analyze.py %*

pause