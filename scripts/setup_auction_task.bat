@echo off
REM 竞价快照自动采集 - Windows任务计划程序配置脚本

echo ========================================
echo 竞价快照自动采集 - 任务计划程序配置
echo ========================================
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] 已获得管理员权限
) else (
    echo [ERROR] 请以管理员身份运行此脚本
    pause
    exit /b 1
)

REM 设置变量
set TASK_NAME=MyQuantTool_AuctionCollector
set PYTHON_PATH=python
set SCRIPT_PATH=E:\MyQuantTool\tools\auto_auction_collector.py
set WORK_DIR=E:\MyQuantTool

echo.
echo 任务配置信息:
echo   任务名称: %TASK_NAME%
echo   Python路径: %PYTHON_PATH%
echo   脚本路径: %SCRIPT_PATH%
echo   工作目录: %WORK_DIR%
echo.

REM 删除旧任务（如果存在）
echo [1/3] 删除旧任务...
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
if %errorLevel% == 0 (
    echo   [OK] 旧任务已删除
) else (
    echo   [INFO] 不存在旧任务
)

REM 创建新任务
echo [2/3] 创建新任务...
schtasks /Create /TN "%TASK_NAME%" ^
    /TR "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" ^
    /SC DAILY ^
    /ST 09:25 ^
    /RL HIGHEST ^
    /RU "%USERNAME%" ^
    /RP "" ^
    /F ^
    /SD 2026/02/13

if %errorLevel% == 0 (
    echo   [OK] 任务创建成功
) else (
    echo   [ERROR] 任务创建失败
    pause
    exit /b 1
)

REM 显示任务信息
echo [3/3] 显示任务信息...
schtasks /Query /TN "%TASK_NAME%" /V /FO LIST

echo.
echo ========================================
echo 配置完成！
echo ========================================
echo.
echo 任务将在每个交易日 9:25 自动运行
echo.
echo 手动测试任务:
echo   schtasks /Run /TN "%TASK_NAME%"
echo.
echo 查看任务状态:
echo   schtasks /Query /TN "%TASK_NAME%"
echo.
echo 删除任务:
echo   schtasks /Delete /TN "%TASK_NAME%" /F
echo.
pause