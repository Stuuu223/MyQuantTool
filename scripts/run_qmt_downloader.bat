@echo off
echo ========================================
echo QMT History Data Downloader
echo ========================================
echo Start time: %date% %time%
echo.

cd /d E:\MyQuantTool

python tasks\qmt_background_downloader.py

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