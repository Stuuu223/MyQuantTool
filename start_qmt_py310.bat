@echo off
chcp 65001 >nul
echo ========================================
echo   MyQuantTool (QMT Python 3.10)
echo ========================================
echo.
echo 正在启动虚拟环境 Python 3.10...
echo.
E:\MyQuantTool\venv_qmt\Scripts\streamlit.exe run main.py --server.headless true
pause
