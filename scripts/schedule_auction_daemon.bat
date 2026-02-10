@echo off
REM ========================================
REM 竞价快照守护进程定时任务脚本
REM ========================================
REM 用途：Windows计划任务每天9:15自动运行竞价快照守护进程
REM ========================================

echo %date% %time% - 启动竞价快照守护进程

REM 切换到项目目录
cd /d "%~dp0.."

REM 激活虚拟环境
call venv_qmt\Scripts\activate.bat

REM 运行竞价快照守护进程
python scripts\auction_snapshot_daemon.py

REM 退出虚拟环境
call venv_qmt\Scripts\deactivate.bat

echo %date% %time% - 竞价快照守护进程结束