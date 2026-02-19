@echo off
chcp 65001
cls

echo ============================================
echo  Tick数据磁盘占用统计
echo ============================================
echo.

cd /d E:\MyQuantTool

:: 检查datadir目录
set DATADIR=data\qmt_data\datadir

if not exist %DATADIR% (
    echo [WARN] 数据目录不存在: %DATADIR%
    pause
    exit /b 1
)

echo 正在统计，请稍候...
echo.

:: 统计SZ目录
set SZ_DIR=%DATADIR%\SZ\0
if exist %SZ_DIR% (
    echo --- 深证股票 (SZ) ---
    for /f %%a in ('dir /b %SZ_DIR% 2^>nul ^| find /c /v ""') do (
        echo 股票数量: %%a 只
    )
    
    :: 计算总大小
    for /f "tokens=3" %%a in ('dir /s %SZ_DIR% 2^>nul ^| findstr "个文件"') do (
        echo 总大小: %%a
    )
    
    :: 显示前10只占用最大的股票
    echo.
    echo 占用空间Top10 (深证):
    powershell -Command "Get-ChildItem -Path '%SZ_DIR%' -Directory | ForEach-Object { $size = (Get-ChildItem -Path $_.FullName -File -Recurse | Measure-Object -Property Length -Sum).Sum; [PSCustomObject]@{Code=$_.Name; SizeGB=[math]::Round($size/1GB,2)} } | Sort-Object SizeGB -Descending | Select-Object -First 10 | Format-Table -AutoSize"
) else (
    echo [WARN] 深证目录不存在
)

echo.

:: 统计SH目录
set SH_DIR=%DATADIR%\SH\0
if exist %SH_DIR% (
    echo --- 上证股票 (SH) ---
    for /f %%a in ('dir /b %SH_DIR% 2^>nul ^| find /c /v ""') do (
        echo 股票数量: %%a 只
    )
    
    for /f "tokens=3" %%a in ('dir /s %SH_DIR% 2^>nul ^| findstr "个文件"') do (
        echo 总大小: %%a
    )
) else (
    echo [WARN] 上证目录不存在
)

echo.
echo ============================================
echo  磁盘空间总览
echo ============================================
echo.

for /f "tokens=3" %%a in ('dir /s %DATADIR% 2^>nul ^| findstr "个文件"') do (
    echo Tick数据总占用: %%a
)

echo.
for /f "tokens=3" %%a in ('wmic logicaldisk where "DeviceID='E:'" get FreeSpace /value 2^>nul ^| find "="') do (
    set FREE_SPACE=%%a
)

echo E盘剩余空间: %FREE_SPACE:~0,-9% GB
echo.
pause
