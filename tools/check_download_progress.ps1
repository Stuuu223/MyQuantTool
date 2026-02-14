# Data Download Progress Check Script
# Usage: ./tools/check_download_progress.ps1

$projectRoot = "E:\MyQuantTool"
$logFile = "$projectRoot\logs\app_20260214.log"
$dataDir = "$projectRoot\data\qmt_data"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "     Tick Data Download Progress" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check if task is running
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "[OK] Background task is running" -ForegroundColor Green
} else {
    Write-Host "[WARNING] No Python process detected" -ForegroundColor Yellow
}
Write-Host ""

# 2. Check data size
if (Test-Path $dataDir) {
    $size = (Get-ChildItem $dataDir -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $count = (Get-ChildItem $dataDir -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count
    $sizeGB = [math]::Round($size / 1GB, 2)
    $sizeMB = [math]::Round($size / 1MB, 2)
    Write-Host "Data Statistics:" -ForegroundColor Cyan
    Write-Host "   Size: $sizeGB GB ($sizeMB MB)"
    Write-Host "   Files: $count"
} else {
    Write-Host "[ERROR] Data directory not found" -ForegroundColor Red
}
Write-Host ""

# 3. Check log progress
if (Test-Path $logFile) {
    Write-Host "Download Progress:" -ForegroundColor Cyan
    $latestLog = Get-Content $logFile -Tail 5
    $latestLog | ForEach-Object {
        if ($_ -match "\[(\d+)/472\]") {
            $progress = [int]$matches[1]
            $pct = [math]::Round($progress / 472 * 100, 1)
            Write-Host "   Progress: $progress/472 ($pct%)" -ForegroundColor Green
        }
    }
    Write-Host ""
    Write-Host "Latest logs (last 5 lines):" -ForegroundColor Gray
    $latestLog | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
} else {
    Write-Host "[ERROR] Log file not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Check Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan