@echo off
echo ========================================
echo Daily THS Moneyflow Collector
echo ========================================
echo Start time: %date% %time%
echo.

cd /d E:\MyQuantTool

python tasks\daily_tushare_ths_collector.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Task completed successfully
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Task failed with error code: %ERRORLEVEL%
    echo ========================================
)

echo.
echo End time: %date% %time%
echo.
pause