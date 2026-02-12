@echo off
chcp 65001 > nul

echo ========================================
echo 历史竞价回放验证器 V1.0
echo ========================================
echo.

REM 切换到项目根目录
cd /d E:\MyQuantTool

REM 激活虚拟环境
call venv_qmt\Scripts\activate.bat

echo [INFO] 请选择要回放的日期：
echo.
echo 1. 2026-02-11 (昨天)
echo 2. 2026-02-10
echo 3. 2026-02-09
echo 4. 2026-02-08
echo 5. 2026-02-07
echo 6. 自定义日期
echo.

set /p CHOICE=请输入选项 (1-6): 

if "%CHOICE%"=="1" set REPLAY_DATE=2026-02-11
if "%CHOICE%"=="2" set REPLAY_DATE=2026-02-10
if "%CHOICE%"=="3" set REPLAY_DATE=2026-02-09
if "%CHOICE%"=="4" set REPLAY_DATE=2026-02-08
if "%CHOICE%"=="5" set REPLAY_DATE=2026-02-07
if "%CHOICE%"=="6" (
    set /p REPLAY_DATE=请输入日期 (YYYY-MM-DD): 
)

if "%REPLAY_DATE%"=="" (
    echo [ERROR] 未选择日期，退出。
    pause
    exit /b 1
)

echo.
echo ========================================
echo [START] 开始回放 %REPLAY_DATE% 的绞价数据
echo ========================================
echo.

REM 运行回放脚本
python tasks/replay_auction_snapshot.py --date %REPLAY_DATE%

echo.
echo ========================================
echo [DONE] 回放完成
echo ========================================
echo.

pause