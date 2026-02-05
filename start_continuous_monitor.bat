@echo off
chcp 65001 >nul
echo ========================================
echo 持续监控启动脚本
echo ========================================
echo.
echo 功能：
echo - 在交易时间内持续运行（9:25-15:00）
echo - 每5分钟执行一次全市场扫描
echo - 生成状态指纹，检测信号变化
echo - 只有在状态变化时才保存快照
echo.
echo 按 Ctrl+C 停止监控
echo ========================================
echo.

python tasks\run_continuous_monitor.py

pause