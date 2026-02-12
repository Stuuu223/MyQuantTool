# 一键式股票分析工具
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Stock Analysis Tool" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$venvPython = Join-Path $PSScriptRoot "venv_qmt\Scripts\python.exe"
$scriptPath = Join-Path $PSScriptRoot "quick_analyze.py"

if (Test-Path $venvPython) {
    & $venvPython $scriptPath $args
} else {
    Write-Host "Error: venv_qmt\Scripts\python.exe not found" -ForegroundColor Red
    exit 1
}

if ($args -notcontains "--no-output") {
    Read-Host "Press Enter to continue..."
}