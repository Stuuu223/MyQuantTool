# MyQuantTool 盘前自动执行脚本 (PowerShell版本)
# 
# 功能：
# - 定时执行盘前预热（08:00）
# - 定时检查QMT环境（09:15）
# - 定时采集竞价数据（09:25）
# - 定时启动监控（09:30）
#
# 使用方法：
#   .\start_premarket.ps1              # 定时模式（默认）
#   .\start_premarket.ps1 -Immediate   # 立即执行所有任务
#   .\start_premarket.ps1 -Once warmup # 只执行指定任务

param(
    [string]$Date = "",
    [switch]$Immediate,
    [string]$Once = ""
)

# 设置项目根目录
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptPath
$VenvPython = Join-Path $ProjectRoot "venv_qmt\Scripts\python.exe"

# 颜色函数
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# 显示标题
Write-ColorOutput "========================================" "Cyan"
Write-ColorOutput "  MyQuantTool 盘前自动执行" "Cyan"
Write-ColorOutput "========================================" "Cyan"
Write-Host ""

# 检查虚拟环境
if (-not (Test-Path $VenvPython)) {
    Write-ColorOutput "[ERROR] 虚拟环境不存在: venv_qmt" "Red"
    Write-ColorOutput "请先创建虚拟环境" "Yellow"
    Read-Host "按回车键退出"
    exit 1
}

Write-ColorOutput "[INFO] 使用虚拟环境: venv_qmt" "Green"
Write-Host ""

# 构建命令参数
$ArgsList = @()
if ($Date -ne "") {
    $ArgsList += "--date"
    $ArgsList += $Date
}
if ($Immediate) {
    $ArgsList += "--immediate"
}
if ($Once -ne "") {
    $ArgsList += "--once"
    $ArgsList += $Once
}

# 显示使用说明
if ($ArgsList.Count -eq 0) {
    Write-ColorOutput "[INFO] 定时模式: 等待触发时间" "Yellow"
    Write-Host ""
    Write-ColorOutput "使用方法:" "Cyan"
    Write-Host "  .\start_premarket.ps1              - 定时模式（默认）"
    Write-Host "  .\start_premarket.ps1 -Immediate   - 立即执行所有任务"
    Write-Host "  .\start_premarket.ps1 -Once warmup - 只执行数据预热"
    Write-Host "  .\start_premarket.ps1 -Once check  - 只执行QMT检查"
    Write-Host "  .\start_premarket.ps1 -Once auction - 只执行竞价采集"
    Write-Host "  .\start_premarket.ps1 -Once monitor - 只启动监控"
    Write-Host ""
    Write-ColorOutput "按任意键继续，或 Ctrl+C 退出..." "Yellow"
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# 切换到项目目录
Set-Location $ProjectRoot

# 运行Python脚本
try {
    & $VenvPython "tasks\scheduled_premarket.py" @ArgsList
    $ExitCode = $LASTEXITCODE
}
catch {
    Write-ColorOutput "[ERROR] 执行失败: $_" "Red"
    $ExitCode = 1
}

# 显示退出信息
Write-Host ""
Write-ColorOutput "========================================" "Cyan"
Write-ColorOutput "  程序已退出 (退出码: $ExitCode)" "Cyan"
Write-ColorOutput "========================================" "Cyan"

if ($ExitCode -ne 0) {
    Read-Host "按回车键退出"
}