# Auction Collector Test - PowerShell Script

$ErrorActionPreference = "Stop"

# Go to project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Auction Collector Test (QMT venv)" -ForegroundColor Cyan
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
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "INFO: QMT venv: $VenvQmt" -ForegroundColor Green
Write-Host "INFO: Python: $PythonQmt" -ForegroundColor Green
Write-Host ""

# Run test
Write-Host "INFO: Running tests..." -ForegroundColor Cyan
Write-Host ""

& $PythonQmt (Join-Path $ProjectRoot "tools\test_auction_collector.py")

Write-Host ""
Write-Host "INFO: Test completed" -ForegroundColor Yellow
Read-Host "Press Enter to exit"