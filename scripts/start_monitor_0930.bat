@echo off
setlocal enabledelayedexpansion

echo ========================================
echo CLI Monitor Launcher V1.0
echo ========================================
echo.

REM Change to project root
cd /d E:\MyQuantTool

REM === Target time: 09:30:00 => 9*3600 + 30*60 ===
set TARGET_HH=9
set TARGET_MM=30
set TARGET_SS=0
set /a TARGET_SECONDS=%TARGET_HH%*3600+%TARGET_MM%*60+%TARGET_SS%

:CHECK_TIME
REM Use delims=:. to correctly separate HH:MM:SS.ms
for /f "tokens=1-4 delims=:." %%a in ("%TIME%") do (
    set HH=%%a
    set MM=%%b
    set SS=%%c
)

REM Remove leading spaces (DO NOT pad with zeros - causes octal error)
set HH=%HH: =%
set MM=%MM: =%
set SS=%SS: =%
set SS=%SS:~0,2%

REM Calculate current seconds using 1%HH% to force decimal interpretation
set /a CURRENT_SECONDS=1%HH%*3600+1%MM%*60+1%SS%

echo [INFO] Target time: 09:30:00
echo [INFO] Current time: %HH%:%MM%:%SS%  -> %CURRENT_SECONDS% seconds

REM Use GEQ to check if past 09:30
if %CURRENT_SECONDS% GEQ %TARGET_SECONDS% (
    echo.
    echo [INFO] Past 09:30, starting monitor now...
    goto START_MONITOR
) else (
    echo [WAIT] Current time: %HH%:%MM%:%SS% - Waiting...
    timeout /t 5 /nobreak >nul
    goto CHECK_TIME
)

:START_MONITOR
echo.
echo ========================================
echo [START] Starting CLI monitor - %TIME%
echo ========================================
echo.

REM Activate virtual environment and start monitor
call venv_qmt\Scripts\activate.bat

echo [INFO] Starting CLI monitor panel...
echo [INFO] Monitor content:
echo   - [Timing Axe] Sector Radar
echo   - [Qualification Axe] Sniper Scope
echo   - [Defensive Axe] Interception Net
echo.
echo [TIP] Press Ctrl+C to exit monitor
echo.

REM Run CLI monitor
python tools/cli_monitor.py

echo.
echo ========================================
echo [DONE] Monitor exited - %TIME%
echo ========================================
echo.

pause