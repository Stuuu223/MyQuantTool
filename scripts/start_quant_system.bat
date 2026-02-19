@echo off
chcp 65001 >nul
REM 统一量化系统启动器 (CTO-V1)
REM 取代: start_*.bat 系列分散脚本

set MODE=%1
set CONFIG=%2

if "%MODE%"=="" (
    echo 用法: start_quant_system.bat [mode] [config]
    echo.
    echo 模式:
    echo   auction          - 启动竞价收集器
    echo   download         - 启动Tick下载(后台)
    echo   event            - 启动EventDriven监控
    echo   app              - 启动主应用程序
    echo.
    echo 示例:
    echo   start_quant_system.bat auction
    echo   start_quant_system.bat download config\download_wanzhu.json
    exit /b 1
)

REM 激活虚拟环境
call venv_qmt\Scripts\activate.bat

REM 根据模式启动对应服务
if "%MODE%"=="auction" (
    echo [启动] 竞价收集器...
    python tasks\auction_manager.py --action collect
) else if "%MODE%"=="download" (
    echo [启动] Tick下载(后台模式)...
    if "%CONFIG%"=="" (
        python scripts\download_manager.py --source wanzhu --mode background
    ) else (
        python scripts\download_manager.py --config %CONFIG% --mode background
    )
) else if "%MODE%"=="event" (
    echo [启动] EventDriven监控...
    python tasks\run_event_driven_monitor.py
) else if "%MODE%"=="app" (
    echo [启动] 主应用程序...
    python main.py
) else (
    echo [错误] 未知模式: %MODE%
    exit /b 1
)

echo [完成] 服务已启动
