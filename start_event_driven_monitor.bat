@echo off
chcp 65001 >nul
echo ========================================
echo 事件驱动持续监控启动脚本
echo ========================================
echo.
echo 功能：
echo - 支持两种模式：固定间隔扫描、事件驱动扫描
echo - 在交易时间内持续运行（9:25-15:00）
echo - 检测四大战法事件（集合竞价、半路、低吸、龙头）
echo - 生成状态指纹，检测信号变化
echo - 只有在状态变化时才保存快照
echo.
echo 使用方法：
echo 1. 固定间隔模式（推荐新手）：默认每5分钟扫描一次
echo    start_event_driven_monitor.bat fixed
echo.
echo 2. 事件驱动模式（推荐高级用户）：只在检测到事件时扫描
echo    start_event_driven_monitor.bat event
echo.
echo 按 Ctrl+C 停止监控
echo ========================================
echo.

if "%1"=="" (
    set MODE=fixed
) else (
    set MODE=%1
)

if "%MODE%"=="fixed" (
    echo 🔄 启动固定间隔模式...
    python tasks\run_event_driven_monitor.py --mode fixed_interval
) else if "%MODE%"=="event" (
    echo 🎯 启动事件驱动模式...
    echo 注意：事件驱动模式需要指定监控股票列表
    echo 示例：start_event_driven_monitor.bat event 000001.SZ 000002.SZ
    python tasks\run_event_driven_monitor.py --mode event_driven %2 %3 %4 %5 %6 %7 %8 %9
) else (
    echo ❌ 未知模式: %MODE%
    echo 请使用: fixed 或 event
    pause
)

pause