# Auction Collector - PowerShell Startup Script

$ErrorActionPreference = "Stop"

# Go to project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Auction Collector (QMT venv)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set QMT venv path
$VenvQmt = Join-Path $ProjectRoot "venv_qmt"
$PythonQmt = Join-Path $VenvQmt "Scripts\python.exe"

# Check venv
if (-not (Test-Path $PythonQmt)) {
    Write-Host "ERROR: QMT venv not found" -ForegroundColor Red
    Write-Host "Expected: $PythonQmt" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please create venv:" -ForegroundColor Yellow
    Write-Host "  python -m venv venv_qmt" -ForegroundColor White
    Write-Host "  venv_qmt\Scripts\activate" -ForegroundColor White
    Write-Host "  pip install xtquant" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "INFO: QMT venv: $VenvQmt" -ForegroundColor Green
Write-Host "INFO: Python: $PythonQmt" -ForegroundColor Green
Write-Host ""

# Check xtquant
try {
    & $PythonQmt -c "import xtquant" 2>$null
} catch {
    Write-Host "ERROR: xtquant not installed in QMT venv" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install xtquant:" -ForegroundColor Yellow
    Write-Host "  venv_qmt\Scripts\activate" -ForegroundColor White
    Write-Host "  pip install xtquant" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "INFO: xtquant module OK" -ForegroundColor Green
Write-Host ""

# Start collector
Write-Host "INFO: Starting auction collector..." -ForegroundColor Cyan
Write-Host ""

& $PythonQmt (Join-Path $ProjectRoot "tasks\scheduled_auction_collector.py")

Write-Host ""
Write-Host "INFO: Auction collector exited" -ForegroundColor Yellow
Read-Host "Press Enter to exit"