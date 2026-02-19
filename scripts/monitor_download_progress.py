#!/usr/bin/env python3
"""
Tick下载进度监控工具
实时监控150只股票的下载进度和成功率
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def get_latest_log():
    """获取最新的日志文件"""
    log_dir = PROJECT_ROOT / 'logs'
    log_files = list(log_dir.glob('tick_download_150_*.log'))
    if not log_files:
        return None
    return max(log_files, key=lambda x: x.stat().st_mtime)

def parse_log_progress(log_file):
    """解析日志文件获取进度"""
    if not log_file or not log_file.exists():
        return None
    
    try:
        content = log_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # 查找最新的进度行
        for line in reversed(lines):
            if '[' in line and '/' in line and '%' in line:
                # 解析类似: [50/150] 33.3% | 股票名 (000001.SZ) | ✅50 ❌0
                try:
                    parts = line.split('|')
                    progress_part = parts[0].strip()
                    counts_part = parts[2].strip() if len(parts) > 2 else ""
                    
                    # 解析 [50/150] 33.3%
                    current_total = progress_part.split(']')[0].strip('[')
                    current, total = map(int, current_total.split('/'))
                    
                    # 解析 ✅50 ❌0
                    success = 0
                    fail = 0
                    if '✅' in counts_part:
                        success_str = counts_part.split('✅')[1].split()[0]
                        success = int(success_str)
                    if '❌' in counts_part:
                        fail_str = counts_part.split('❌')[1].split()[0]
                        fail = int(fail_str)
                    
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
    except Exception as e:
        print(f"解析日志失败: {e}")
        return None

def count_downloaded_stocks():
    """统计已下载的股票数量"""
    datadir = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir'
    
    sz_dir = datadir / 'SZ' / '0'
    sh_dir = datadir / 'SH' / '0'
    
    sz_count = len(list(sz_dir.glob('*'))) if sz_dir.exists() else 0
    sh_count = len(list(sh_dir.glob('*'))) if sh_dir.exists() else 0
    
    return {'SZ': sz_count, 'SH': sh_count, 'total': sz_count + sh_count}

def format_duration(seconds):
    """格式化持续时间"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}小时{minutes}分钟"

def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='Tick下载进度监控')
    parser.add_argument('--watch', '-w', action='store_true', help='持续监控模式')
    parser.add_argument('--interval', '-i', type=int, default=10, help='刷新间隔(秒)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Tick下载进度监控")
    print("=" * 60)
    print()
    
    target_total = 150
    start_time = time.time()
    
    while True:
        # 清屏
        if args.watch:
            print("\033[2J\033[H", end='')
        
        print("=" * 60)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()
        
        # 获取日志进度
        log_file = get_latest_log()
        progress = parse_log_progress(log_file)
        
        if progress:
            print(f"下载进度: {progress['current']}/{progress['total']} ({progress['progress']:.1f}%)")
            print(f"成功: {progress['success']} 只")
            print(f"失败: {progress['fail']} 只")
            print()
            
            # 估算剩余时间
            elapsed = time.time() - start_time
            if progress['current'] > 0:
                avg_time_per_stock = elapsed / progress['current']
                remaining_stocks = progress['total'] - progress['current']
                eta_seconds = avg_time_per_stock * remaining_stocks
                print(f"已用时: {format_duration(elapsed)}")
                print(f"预计剩余: {format_duration(eta_seconds)}")
        else:
            print("尚未获取到进度信息")
        
        print()
        
        # 统计磁盘数据
        counts = count_downloaded_stocks()
        print(f"磁盘数据:")
        print(f"  深证(SZ): {counts['SZ']} 只")
        print(f"  上证(SH): {counts['SH']} 只")
        print(f"  总计: {counts['total']} 只 / 目标 {target_total} 只")
        
        if counts['total'] >= target_total:
            print()
            print("=" * 60)
            print("✅ 下载任务已完成!")
            print("=" * 60)
            break
        
        print()
        print("=" * 60)
        print(f"日志文件: {log_file.name if log_file else '无'}")
        print("=" * 60)
        
        if not args.watch:
            break
        
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print()
            print("\n监控已停止")
            break

if __name__ == '__main__':
    main()
