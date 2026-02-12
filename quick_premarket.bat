@echo off
REM Quick launch script for MyQuantTool pre-market tasks
REM No Chinese characters to avoid encoding issues

call venv_qmt\Scripts\python.exe tasks\scheduled_premarket.py %*