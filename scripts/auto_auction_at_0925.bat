@echo off
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

REM === 目标时间：09:24:50 => 9*3600 + 24*60 + 50 ===
set TARGET_HH=9
set TARGET_MM=24
set TARGET_SS=50
set /a TARGET_SECONDS=%TARGET_HH%*3600+%TARGET_MM%*60+%TARGET_SS%

echo [INFO] 当前日期: %TODAY%
echo [INFO] 目标时间: 09:24:50
echo.

:CHECK_TIME
REM 使用 delims=:. 正确分隔时分秒和小数秒
for /f "tokens=1-4 delims=:." %%a in ("%TIME%") do (
    set HH=%%a
    set MM=%%b
    set SS=%%c
)

REM 去掉前导空格并补零
set HH=%HH: =0%
set MM=%MM: =0%
set SS=%SS: =0%
set SS=%SS:~0,2%

REM 这里只允许纯数字，不与if混合
set /a CURRENT_SECONDS=%HH%*3600+%MM%*60+%SS%

REM 使用 GEQ 判断是否已过 09:24:50
if %CURRENT_SECONDS% GEQ %TARGET_SECONDS% (
    echo [WAIT] 当前时间: %HH%:%MM%:%SS% - 已过目标时间，立即启动...
    goto START_AUCTION
) else (
    echo [WAIT] 当前时间: %HH%:%MM%:%SS% - 等待中...
    timeout /t 5 /nobreak >nul
    goto CHECK_TIME
)

:START_AUCTION
echo.
echo ========================================
echo [START] 启动竞价采集 - %TIME%
echo ========================================
echo.

REM 激活虚拟环境并启动采集
call venv_qmt\Scripts\activate.bat

REM 创建日志目录
if not exist "logs\auction" mkdir logs\auction

REM 运行竞价采集（Windows CMD不支持tee，改用重定向）
echo [RUN] python tasks/collect_auction_snapshot.py --date %TODAY%
echo.

python tasks/collect_auction_snapshot.py --date %TODAY% > logs\auction\%TODAY%.log 2>&1
type logs\auction\%TODAY%.log

echo.
echo ========================================
echo [DONE] 竞价采集完成 - %TIME%
echo ========================================
echo.
echo [INFO] 日志已保存到: logs\auction\%TODAY%.log
echo.

pause