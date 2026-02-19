#!/usr/bin/env python3
"""
Tick下载管理工具 - 一站式封装
用法:
    python scripts/tick_download.py start     # 启动下载
    python scripts/tick_download.py status    # 查看状态
    python scripts/tick_download.py stop      # 停止下载
    python scripts/tick_download.py monitor   # 实时监控
"""

import sys
import os
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PID_FILE = PROJECT_ROOT / 'logs' / 'tick_download.pid'
STATUS_FILE = PROJECT_ROOT / 'logs' / 'tick_download_status.json'

def is_running():
    """检查下载进程是否在运行"""
    if not PID_FILE.exists():
        return False, None
    
    try:
        pid = int(PID_FILE.read_text().strip())
        # Windows检查进程是否存在
        result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], 
                              capture_output=True, text=True)
        if 'python.exe' in result.stdout:
            return True, pid
        else:
            # 进程已死，清理PID文件
            PID_FILE.unlink(missing_ok=True)
            return False, None
    except:
        return False, None

def start():
    """启动下载"""
    running, pid = is_running()
    if running:
        print(f"⚠️  下载已在运行中 (PID: {pid})")
        print(f"   使用: python scripts/tick_download.py monitor 查看进度")
        return
    
    print("=" * 60)
    print("🚀 启动Tick数据下载")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 构建命令
    venv_python = PROJECT_ROOT / 'venv_qmt' / 'Scripts' / 'python.exe'
    script = PROJECT_ROOT / 'scripts' / 'download_wanzhu_top150_tick.py'
    
    log_file = PROJECT_ROOT / 'logs' / f'tick_download_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # 创建startupinfo来隐藏窗口
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    # 启动后台进程
    process = subprocess.Popen(
        [str(venv_python), str(script)],
        stdout=open(log_file, 'w'),
        stderr=subprocess.STDOUT,
        startupinfo=startupinfo,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    
    # 记录PID
    PID_FILE.write_text(str(process.pid))
    
    # 初始化状态文件
    status = {
        'pid': process.pid,
        'start_time': datetime.now().isoformat(),
        'status': 'running',
        'log_file': str(log_file)
    }
    STATUS_FILE.write_text(json.dumps(status, indent=2))
    
    print(f"✅ 下载已启动")
    print(f"   PID: {process.pid}")
    print(f"   日志: {log_file}")
    print()
    print("查看进度:")
    print(f"   python scripts/tick_download.py monitor")
    print()

def stop():
    """停止下载"""
    running, pid = is_running()
    
    if not running:
        print("ℹ️  下载未在运行")
        # 尝试结束所有相关的python进程
        print("是否强制结束所有Python下载进程?")
        response = input("(y/N): ").strip().lower()
        if response == 'y':
            os.system('taskkill /F /IM python.exe 2>nul')
            print("✅ 已结束")
        return
    
    print(f"🛑 正在停止下载进程 (PID: {pid})...")
    
    try:
        # 先尝试优雅终止
        subprocess.run(['taskkill', '/PID', str(pid)], check=False)
        time.sleep(2)
        
        # 检查是否还在运行
        running, _ = is_running()
        if running:
            # 强制终止
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=False)
        
        # 清理文件
        PID_FILE.unlink(missing_ok=True)
        
        # 更新状态
        if STATUS_FILE.exists():
            status = json.loads(STATUS_FILE.read_text())
            status['status'] = 'stopped'
            status['stop_time'] = datetime.now().isoformat()
            STATUS_FILE.write_text(json.dumps(status, indent=2))
        
        print("✅ 已停止")
    except Exception as e:
        print(f"❌ 停止失败: {e}")

def parse_log_progress(log_file):
    """解析日志获取进度"""
    if not log_file or not log_file.exists():
        return None
    
    try:
        content = log_file.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        # 查找最新的进度行
        for line in reversed(lines):
            if '[' in line and '/' in line and '%' in line and '✅' in line:
                try:
                    parts = line.split('|')
                    progress_part = parts[0].strip()
                    counts_part = parts[2].strip() if len(parts) > 2 else ""
                    
                    # 解析 [50/150] 33.3%
                    current_total = progress_part.split(']')[0].strip('[')
                    current, total = map(int, current_total.split('/'))
                    
                    # 解析 ✅50 ❌0
                    success = int(counts_part.split('✅')[1].split()[0]) if '✅' in counts_part else 0
                    fail = int(counts_part.split('❌')[1].split()[0]) if '❌' in counts_part else 0
                    
                    return {
                        'current': current,
                        'total': total,
                        'success': success,
                        'fail': fail,
                        'progress': current / total * 100 if total > 0 else 0
                    }
                except:
                    continue
        
        return None
    except:
        return None

def get_data_stats():
    """获取数据目录统计"""
    datadir = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir'
    
    sz_dir = datadir / 'SZ' / '0'
    sh_dir = datadir / 'SH' / '0'
    
    sz_count = len([d for d in sz_dir.glob('*') if d.is_dir()]) if sz_dir.exists() else 0
    sh_count = len([d for d in sh_dir.glob('*') if d.is_dir()]) if sh_dir.exists() else 0
    
    return {'SZ': sz_count, 'SH': sh_count, 'total': sz_count + sh_count}

def status():
    """显示状态"""
    running, pid = is_running()
    
    print("=" * 60)
    print("📊 Tick下载状态")
    print("=" * 60)
    print()
    
    if running:
        print(f"🟢 状态: 运行中")
        print(f"   PID: {pid}")
        
        # 获取启动时间
        if STATUS_FILE.exists():
            try:
                status_data = json.loads(STATUS_FILE.read_text())
                start_time = datetime.fromisoformat(status_data.get('start_time', ''))
                elapsed = datetime.now() - start_time
                print(f"   已运行: {elapsed.seconds // 3600}小时{(elapsed.seconds % 3600) // 60}分钟")
            except:
                pass
    else:
        print(f"🔴 状态: 未运行")
    
    print()
    
    # 获取日志进度
    log_dir = PROJECT_ROOT / 'logs'
    log_files = sorted(log_dir.glob('tick_download*.log'), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if log_files:
        progress = parse_log_progress(log_files[0])
        if progress:
            print(f"📈 下载进度:")
            print(f"   {progress['current']}/{progress['total']} ({progress['progress']:.1f}%)")
            print(f"   ✅ 成功: {progress['success']} 只")
            print(f"   ❌ 失败: {progress['fail']} 只")
            
            if progress['current'] > 0 and running:
                # 估算剩余时间
                elapsed_minutes = (datetime.now() - datetime.fromisoformat(json.loads(STATUS_FILE.read_text()).get('start_time', datetime.now().isoformat()))).total_seconds() / 60
                avg_time = elapsed_minutes / progress['current']
                remaining = avg_time * (progress['total'] - progress['current'])
                print(f"   ⏱️  预计剩余: {remaining:.0f}分钟")
        else:
            print("📄 日志存在但未获取到进度")
    
    print()
    
    # 磁盘统计
    stats = get_data_stats()
    print(f"💾 磁盘数据:")
    print(f"   深证: {stats['SZ']} 只")
    print(f"   上证: {stats['SH']} 只")
    print(f"   总计: {stats['total']} 只 / 目标 150 只")
    
    if stats['total'] >= 150:
        print()
        print("=" * 60)
        print("🎉 下载任务已完成!")
        print("=" * 60)
    
    print()

def monitor():
    """实时监控"""
    print("=" * 60)
    print("👁️  实时监控模式 (按 Ctrl+C 停止)")
    print("=" * 60)
    print()
    
    try:
        while True:
            # 清屏
            os.system('cls' if os.name == 'nt' else 'clear')
            
            status()
            
            if not is_running()[0]:
                print("⏹️  监控结束 - 进程已停止")
                break
            
            time.sleep(10)
    except KeyboardInterrupt:
        print()
        print("\n⏹️  监控已停止")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print(__doc__)
        print()
        print("示例:")
        print("  python scripts/tick_download.py start")
        print("  python scripts/tick_download.py status")
        print("  python scripts/tick_download.py monitor")
        print("  python scripts/tick_download.py stop")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        start()
    elif command == 'stop':
        stop()
    elif command == 'status':
        status()
    elif command == 'monitor':
        monitor()
    else:
        print(f"❌ 未知命令: {command}")
        print(__doc__)

if __name__ == '__main__':
    main()
