@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================
echo CLI监控自动启动器 V1.0
echo ========================================
echo.

REM 切换到项目根目录
cd /d E:\MyQuantTool

echo [INFO] 目标时间: 09:30:00
echo [INFO] 当前时间: %TIME%
echo.

REM 等待到09:30:00
:WAIT_LOOP
for /f "tokens=1-3 delims=:" %%a in ("%TIME%") do (
    set HH=%%a
    set MM=%%b
    set SS=%%c
)

REM 去除前导空格
set HH=%HH: =0%
set MM=%MM: =0%
set SS=%SS:~0,2%

REM 计算当前秒数
set /a CURRENT_SECONDS=(%HH%*3600)+(%MM%*60)+%SS%
set /a TARGET_SECONDS=(9*3600)+(30*60)+0

REM 显示当前时间
echo [WAIT] 当前时间: %HH%:%MM%:%SS% - 等待中...

if %CURRENT_SECONDS% LSS %TARGET_SECONDS% (
    timeout /t 5 /nobreak > nul
    goto WAIT_LOOP
)

echo.
echo ========================================
echo [START] 启动CLI监控 - %TIME%
echo ========================================
echo.

REM 激活虚拟环境并启动监控
call venv_qmt\Scripts\activate.bat

echo [INFO] 正在启动CLI监控面板...
echo [INFO] 监控内容：
echo   - 🛡️ 时机斧：板块雷达
echo   - 🎯 资格斧：狙击镜
echo   - 🚫 防守斧：拦截网
echo.
echo [TIP] 按 Ctrl+C 退出监控
echo.

REM 运行CLI监控
python tools/cli_monitor.py

echo.
echo ========================================
echo [DONE] 监控已退出 - %TIME%
echo ========================================
echo.

pause