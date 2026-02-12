@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================
echo 竞价采集自动化启动器 V1.0
echo ========================================
echo.

REM 切换到项目根目录
cd /d E:\MyQuantTool

REM 获取当前日期
for /f "tokens=1-3 delims=/- " %%a in ("%DATE%") do (
    set YEAR=%%a
    set MONTH=%%b
    set DAY=%%c
)

REM 格式化日期为YYYY-MM-DD
set TODAY=%YEAR%-%MONTH%-%DAY%

echo [INFO] 当前日期: %TODAY%
echo [INFO] 目标时间: 09:24:50
echo.

REM 等待到09:24:50
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
set /a TARGET_SECONDS=(9*3600)+(24*60)+50

REM 显示当前时间
echo [WAIT] 当前时间: %HH%:%MM%:%SS% - 等待中...

if %CURRENT_SECONDS% LSS %TARGET_SECONDS% (
    timeout /t 5 /nobreak > nul
    goto WAIT_LOOP
)

echo.
echo ========================================
echo [START] 启动竞价采集 - %TIME%
echo ========================================
echo.

REM 激活虚拟环境并启动采集
call venv_qmt\Scripts\activate.bat

REM 创建日志目录
if not exist "logs\auction" mkdir logs\auction

REM 运行竞价采集
echo [RUN] python tasks/collect_auction_snapshot.py --date %TODAY%
echo.

python tasks/collect_auction_snapshot.py --date %TODAY% 2>&1 | tee logs\auction\%TODAY%.log

echo.
echo ========================================
echo [DONE] 竞价采集完成 - %TIME%
echo ========================================
echo.
echo [INFO] 日志已保存到: logs\auction\%TODAY%.log
echo.

pause