@echo off
chcp 65001 >nul
echo ========================================
echo    一键式股票分析工具 (Python 3.10)
echo ========================================
echo.

E:\MyQuantTool\venv_qmt\Scripts\python.exe %~dp0quick_analyze.py %*

pause