@echo off
chcp 65001 >nul
cd /d "%~dp0.."
python scripts\estimate_tick_download_time.py
pause