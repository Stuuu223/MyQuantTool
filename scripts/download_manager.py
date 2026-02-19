#!/usr/bin/env python3
"""
下载管理器 - 统一入口 (Download Manager) V2.0

功能特性：
- 后台守护进程（start/stop/status/monitor）
- Rich实时进度条（进度、速度、剩余时间）
- 断点续传（自动恢复未完成的下载）
- 时间估算（基于实测速度动态计算）

取代脚本：
- tick_download.py（后台管理+监控）
- estimate_tick_download_time.py（时间估算）
- shutdown_after_download.py（自动关机）

Author: AI Project Director
Version: V2.0
Date: 2026-02-19
"""

import sys
import os
import time
import json
import signal
import subprocess
import atexit
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 状态文件
PID_FILE = PROJECT_ROOT / 'logs' / 'download_manager.pid'
STATUS_FILE = PROJECT_ROOT / 'logs' / 'download_manager_status.json'
RESUME_FILE = PROJECT_ROOT / 'logs' / 'download_manager_resume.json'

# 尝试导入Rich
HAS_RICH = False
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.live import Live
    HAS_RICH = True
    console = Console()
except ImportError:
    console = None

from logic.data_providers.tick_provider import TickProvider
from logic.services.config_service import ConfigService

# 默认配置
DEFAULT_CONFIG = {
    'ticks_per_second': 3,
    'seconds_per_stock': 60,  # 每只股票平均下载时间（秒）
    'sleep_interval': 0.2,
    'trading_hours_per_day': 4,
}


@dataclass
class DownloadState:
    """下载状态"""
    universe: str = ''
    source: str = ''
    mode: str = ''
    start_date: str = ''
    end_date: str = ''
    total_stocks: int = 0
    completed_stocks: int = 0
    failed_stocks: int = 0
    start_time: Optional[str] = None
    current_stock: str = ''
    status: str = 'idle'  # idle, running, paused, completed, error
    message: str = ''
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DownloadState':
        return cls(**data)


class DownloadManager:
    """下载管理器 - 后台守护进程版"""
    
    def __init__(self):
        self.config_service = ConfigService()
        self.state = DownloadState()
        self._running = False
        self._paused = False
        
    def load_stock_universe(self, universe: str, custom_path: Optional[str] = None) -> List[str]:
        """加载股票池"""
        if universe == 'wanzhu_top150':
            return self.config_service.get_stock_universe('wanzhu_top150')
        elif universe == 'wanzhu_selected':
            csv_path = PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv'
            import pandas as pd
            df = pd.read_csv(csv_path)
            codes = []
            for _, row in df.iterrows():
                code = str(row['code']).zfill(6)
                if code.startswith('6'):
                    codes.append(f"{code}.SH")
                else:
                    codes.append(f"{code}.SZ")
            return codes
        elif universe == 'custom' and custom_path:
            with open(custom_path, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        else:
            raise ValueError(f"未知股票池: {universe}")
    
    def estimate_download_time(self, num_stocks: int, num_days: int, source: str = 'tick') -> Dict:
        """估算下载时间"""
        if source == 'tick':
            # Tick数据估算
            seconds_per_stock = DEFAULT_CONFIG['seconds_per_stock']
            sleep_interval = DEFAULT_CONFIG['sleep_interval']
            
            total_seconds = num_stocks * (seconds_per_stock + sleep_interval)
            
            # 增加20%缓冲
            optimistic = total_seconds * 0.8
            conservative = total_seconds * 1.2
            
        elif source in ['1m', '5m']:
            # 分钟数据估算（更快）
            seconds_per_stock = 10
            total_seconds = num_stocks * seconds_per_stock
            optimistic = total_seconds * 0.9
            conservative = total_seconds * 1.1
        else:
            total_seconds = num_stocks * 30
            optimistic = conservative = total_seconds
        
        return {
            'optimistic_seconds': optimistic,
            'conservative_seconds': conservative,
            'optimistic_minutes': optimistic / 60,
            'conservative_minutes': conservative / 60,
            'optimistic_formatted': self._format_duration(optimistic),
            'conservative_formatted': self._format_duration(conservative),
        }
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            return f"{int(seconds/60)}分{int(seconds%60)}秒"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}小时{minutes}分"
    
    def save_resume_state(self, remaining_stocks: List[str]):
        """保存断点续传状态"""
        resume_data = {
            'timestamp': datetime.now().isoformat(),
            'state': self.state.to_dict(),
            'remaining_stocks': remaining_stocks,
        }
        with open(RESUME_FILE, 'w', encoding='utf-8') as f:
            json.dump(resume_data, f, ensure_ascii=False, indent=2)
    
    def load_resume_state(self) -> Optional[Dict]:
        """加载断点续传状态"""
        if not RESUME_FILE.exists():
            return None
        try:
            with open(RESUME_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def clear_resume_state(self):
        """清除断点续传状态"""
        if RESUME_FILE.exists():
            RESUME_FILE.unlink()
    
    def _save_status(self):
        """保存状态到文件"""
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state.to_dict(), f, ensure_ascii=False, indent=2)
    
    def _load_status(self) -> Optional[DownloadState]:
        """从文件加载状态"""
        if not STATUS_FILE.exists():
            return None
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                return DownloadState.from_dict(json.load(f))
        except:
            return None
    
    def download_with_progress(self, stock_codes: List[str], start_date: str, end_date: str, 
                               source: str = 'tick', mode: str = 'full'):
        """带进度条的下载"""
        self.state.total_stocks = len(stock_codes)
        self.state.start_time = datetime.now().isoformat()
        self.state.status = 'running'
        self._running = True
        
        # 断点续传：检查是否有未完成的任务
        resume_data = self.load_resume_state()
        if resume_data and mode == 'resume':
            stock_codes = resume_data.get('remaining_stocks', stock_codes)
            print(f"🔄 断点续传: 从上次中断处继续，剩余 {len(stock_codes)} 只股票")
        
        # 计算日期跨度
        try:
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            num_days = (end_dt - start_dt).days + 1
        except:
            num_days = 30
        
        # 估算时间
        estimate = self.estimate_download_time(len(stock_codes), num_days, source)
        
        if HAS_RICH:
            # Rich进度条版本
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=40),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"[cyan]下载 {source} 数据", 
                    total=len(stock_codes)
                )
                
                completed = []
                failed = []
                
                with TickProvider() as provider:
                    for i, stock_code in enumerate(stock_codes):
                        if not self._running:
                            # 保存断点
                            remaining = stock_codes[i:]
                            self.save_resume_state(remaining)
                            print(f"\n⏸️ 下载暂停，已保存断点 ({len(remaining)} 只剩余)")
                            break
                        
                        self.state.current_stock = stock_code
                        progress.update(task, description=f"[cyan]{stock_code}")
                        
                        try:
                            if source == 'tick':
                                result = provider.download_tick_data(stock_code, start_date, end_date)
                            elif source in ['1m', '5m']:
                                result = provider.download_minute_data([stock_code], start_date, end_date, source)
                            else:
                                result = {'success': True}
                            
                            if result.get('success', False):
                                completed.append(stock_code)
                                self.state.completed_stocks += 1
                            else:
                                failed.append(stock_code)
                                self.state.failed_stocks += 1
                                
                        except Exception as e:
                            failed.append(stock_code)
                            self.state.failed_stocks += 1
                        
                        progress.update(task, advance=1)
                        self._save_status()
                        
                        # 短暂休眠避免API限流
                        time.sleep(DEFAULT_CONFIG['sleep_interval'])
                
                progress.update(task, description="[green]下载完成")
        else:
            # 普通版本（无Rich）
            print(f"\n{'='*60}")
            print(f"开始下载: {len(stock_codes)}只股票, {source}数据")
            print(f"预估时间: {estimate['conservative_formatted']}")
            print(f"{'='*60}\n")
            
            completed = []
            failed = []
            start_time = time.time()
            
            with TickProvider() as provider:
                for i, stock_code in enumerate(stock_codes):
                    if not self._running:
                        remaining = stock_codes[i:]
                        self.save_resume_state(remaining)
                        print(f"\n⏸️ 下载暂停，已保存断点")
                        break
                    
                    self.state.current_stock = stock_code
                    
                    # 每10只显示进度
                    if i % 10 == 0 or i == len(stock_codes) - 1:
                        elapsed = time.time() - start_time
                        speed = (i + 1) / elapsed if elapsed > 0 else 0
                        remaining_count = len(stock_codes) - i - 1
                        eta_seconds = remaining_count / speed if speed > 0 else 0
                        
                        print(f"[{i+1}/{len(stock_codes)}] {stock_code} "
                              f"| 速度: {speed:.1f}只/分 "
                              f"| 剩余: {self._format_duration(eta_seconds)}")
                    
                    try:
                        if source == 'tick':
                            result = provider.download_tick_data(stock_code, start_date, end_date)
                        elif source in ['1m', '5m']:
                            result = provider.download_minute_data([stock_code], start_date, end_date, source)
                        else:
                            result = {'success': True}
                        
                        if result.get('success', False):
                            completed.append(stock_code)
                            self.state.completed_stocks += 1
                        else:
                            failed.append(stock_code)
                            self.state.failed_stocks += 1
                    except Exception as e:
                        failed.append(stock_code)
                        self.state.failed_stocks += 1
                    
                    self._save_status()
                    time.sleep(DEFAULT_CONFIG['sleep_interval'])
        
        # 完成处理
        if self._running:  # 如果不是被中断的
            self.state.status = 'completed'
            self.clear_resume_state()
            
            print(f"\n{'='*60}")
            print("✅ 下载完成")
            print(f"  成功: {self.state.completed_stocks}")
            print(f"  失败: {self.state.failed_stocks}")
            print(f"{'='*60}")
        
        self._save_status()
        return completed, failed
    
    def start_daemon(self, universe: str, source: str, start_date: str, end_date: str,
                     mode: str = 'full', custom_path: Optional[str] = None,
                     auto_shutdown: bool = False):
        """启动后台下载进程"""
        # 检查是否已有进程在运行
        if self.is_running():
            print("⚠️  下载进程已在运行中")
            print("   使用: python scripts/download_manager.py monitor 查看进度")
            return False
        
        # 加载股票池
        try:
            stock_codes = self.load_stock_universe(universe, custom_path)
        except Exception as e:
            print(f"❌ 加载股票池失败: {e}")
            return False
        
        # 断点续传模式
        if mode == 'resume':
            resume_data = self.load_resume_state()
            if resume_data:
                stock_codes = resume_data.get('remaining_stocks', stock_codes)
                print(f"🔄 断点续传模式: {len(stock_codes)} 只股票待下载")
            else:
                print("⚠️  没有找到断点记录，将从头开始")
                mode = 'full'
        
        # 估算时间
        num_days = 30  # 简化估算
        estimate = self.estimate_download_time(len(stock_codes), num_days, source)
        
        print(f"\n{'='*60}")
        print("🚀 启动后台下载进程")
        print(f"{'='*60}")
        print(f"股票池: {universe} ({len(stock_codes)}只)")
        print(f"数据源: {source}")
        print(f"时间范围: {start_date} ~ {end_date}")
        print(f"下载模式: {mode}")
        print(f"预估时间: {estimate['optimistic_formatted']} ~ {estimate['conservative_formatted']}")
        if auto_shutdown:
            shutdown_time = datetime.now() + timedelta(seconds=estimate['conservative_seconds'] + 600)
            print(f"自动关机: {shutdown_time.strftime('%H:%M:%S')} (+10分钟缓冲)")
        print(f"{'='*60}\n")
        
        # 初始化状态
        self.state = DownloadState(
            universe=universe,
            source=source,
            mode=mode,
            start_date=start_date,
            end_date=end_date,
            total_stocks=len(stock_codes),
            status='running',
            start_time=datetime.now().isoformat()
        )
        self._save_status()
        
        # Windows后台进程启动
        if sys.platform == 'win32':
            # 使用pythonw.exe启动无窗口进程
            pythonw = Path(sys.executable).parent / 'pythonw.exe'
            if not pythonw.exists():
                pythonw = sys.executable
            
            cmd = [
                str(pythonw), str(__file__), '_daemon',
                '--universe', universe,
                '--source', source,
                '--start-date', start_date,
                '--end-date', end_date,
                '--mode', mode,
            ]
            if custom_path:
                cmd.extend(['--custom-path', custom_path])
            if auto_shutdown:
                cmd.append('--auto-shutdown')
            
            # 启动后台进程
            creationflags = subprocess.CREATE_NEW_CONSOLE if pythonw == sys.executable else 0
            process = subprocess.Popen(
                cmd,
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            # 保存PID
            PID_FILE.write_text(str(process.pid))
            print(f"✅ 后台进程已启动 (PID: {process.pid})")
            print(f"   查看状态: python scripts/download_manager.py status")
            print(f"   实时监控: python scripts/download_manager.py monitor")
            print(f"   停止下载: python scripts/download_manager.py stop")
            
            return True
        else:
            # Linux/Mac使用nohup
            print("⚠️  非Windows系统，请在后台手动运行:")
            print(f"   nohup python {__file__} _daemon ... &")
            return False
    
    def _run_daemon(self, universe: str, source: str, start_date: str, end_date: str,
                    mode: str = 'full', custom_path: Optional[str] = None,
                    auto_shutdown: bool = False):
        """后台进程实际执行"""
        # 加载股票池
        stock_codes = self.load_stock_universe(universe, custom_path)
        
        # 设置信号处理
        def signal_handler(signum, frame):
            print("\n🛑 收到停止信号，保存断点...")
            self._running = False
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            # 执行下载
            completed, failed = self.download_with_progress(
                stock_codes, start_date, end_date, source, mode
            )
            
            # 自动关机
            if auto_shutdown and self.state.status == 'completed':
                print("\n⏰ 下载完成，10分钟后自动关机...")
                time.sleep(600)
                if sys.platform == 'win32':
                    os.system('shutdown /s /t 60 /c "Download completed, auto shutdown"')
                
        except Exception as e:
            self.state.status = 'error'
            self.state.message = str(e)
            self._save_status()
            raise
    
    def is_running(self) -> bool:
        """检查后台进程是否在运行"""
        if not PID_FILE.exists():
            return False
        
        try:
            pid = int(PID_FILE.read_text().strip())
            if sys.platform == 'win32':
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                    capture_output=True, text=True
                )
                is_alive = 'python.exe' in result.stdout or 'pythonw.exe' in result.stdout
            else:
                result = subprocess.run(['ps', '-p', str(pid)], capture_output=True)
                is_alive = result.returncode == 0
            
            if not is_alive:
                PID_FILE.unlink(missing_ok=True)
            
            return is_alive
        except:
            return False
    
    def stop(self):
        """停止后台下载"""
        if not self.is_running():
            print("ℹ️  没有运行中的下载进程")
            return False
        
        try:
            pid = int(PID_FILE.read_text().strip())
            
            if sys.platform == 'win32':
                subprocess.run(['taskkill', '/PID', str(pid), '/T'], capture_output=True)
            else:
                os.kill(pid, signal.SIGTERM)
            
            PID_FILE.unlink(missing_ok=True)
            print("✅ 下载进程已停止")
            print("📝 断点已保存，可使用 --mode resume 续传")
            return True
        except Exception as e:
            print(f"❌ 停止失败: {e}")
            return False
    
    def status(self):
        """显示当前状态"""
        state = self._load_status()
        
        if not state:
            print("ℹ️  没有下载记录")
            return
        
        running = self.is_running()
        
        print(f"\n{'='*60}")
        print("📊 下载状态")
        print(f"{'='*60}")
        print(f"进程状态: {'🟢 运行中' if running else '⚪ 已停止'}")
        print(f"任务状态: {state.status}")
        print(f"股票池: {state.universe}")
        print(f"数据源: {state.source}")
        print(f"时间范围: {state.start_date} ~ {state.end_date}")
        print(f"进度: {state.completed_stocks}/{state.total_stocks} "
              f"({state.completed_stocks/state.total_stocks*100:.1f}% if state.total_stocks > 0 else 0)")
        print(f"失败: {state.failed_stocks}")
        if state.current_stock:
            print(f"当前: {state.current_stock}")
        if state.message:
            print(f"消息: {state.message}")
        
        # 断点续传提示
        if RESUME_FILE.exists() and not running:
            resume_data = self.load_resume_state()
            if resume_data:
                remaining = len(resume_data.get('remaining_stocks', []))
                print(f"\n🔄 断点可用: {remaining} 只股票未完成")
                print(f"   恢复下载: python scripts/download_manager.py start --mode resume")
        
        print(f"{'='*60}\n")
    
    def monitor(self):
        """实时监控（持续刷新）"""
        if not self.is_running():
            print("ℹ️  没有运行中的下载进程")
            self.status()
            return
        
        print("\n📺 实时监控模式（按Ctrl+C退出）\n")
        
        try:
            while self.is_running():
                state = self._load_status()
                if state:
                    # 清屏
                    os.system('cls' if sys.platform == 'win32' else 'clear')
                    
                    print(f"{'='*60}")
                    print(f"🟢 下载进行中 | {datetime.now().strftime('%H:%M:%S')}")
                    print(f"{'='*60}")
                    print(f"进度: {state.completed_stocks}/{state.total_stocks}")
                    
                    if state.total_stocks > 0:
                        pct = state.completed_stocks / state.total_stocks * 100
                        bar_len = 40
                        filled = int(bar_len * pct / 100)
                        bar = '█' * filled + '░' * (bar_len - filled)
                        print(f"[{bar}] {pct:.1f}%")
                    
                    print(f"当前: {state.current_stock}")
                    print(f"失败: {state.failed_stocks}")
                    
                    # 计算速度
                    if state.start_time:
                        start = datetime.fromisoformat(state.start_time)
                        elapsed = (datetime.now() - start).total_seconds()
                        if elapsed > 0 and state.completed_stocks > 0:
                            speed = state.completed_stocks / elapsed * 60  # 只/分钟
                            remaining = state.total_stocks - state.completed_stocks
                            eta = remaining / (state.completed_stocks / elapsed) if state.completed_stocks > 0 else 0
                            print(f"速度: {speed:.1f} 只/分钟")
                            print(f"预计剩余: {self._format_duration(eta)}")
                    
                    print(f"{'='*60}")
                    print("按Ctrl+C退出监控，下载继续在后台运行")
                
                time.sleep(2)
            
            print("\n✅ 下载进程已结束")
            self.status()
            
        except KeyboardInterrupt:
            print("\n\n👋 退出监控模式（下载仍在后台运行）")


def main():
    parser = argparse.ArgumentParser(
        description='下载管理器 V2.0 - 后台守护进程版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用方式:
  # 启动后台下载
  python scripts/download_manager.py start --universe wanzhu_selected --source tick \\
      --start-date 20250101 --end-date 20250131

  # 断点续传
  python scripts/download_manager.py start --mode resume

  # 查看状态
  python scripts/download_manager.py status

  # 实时监控（不阻塞）
  python scripts/download_manager.py monitor

  # 停止下载（保存断点）
  python scripts/download_manager.py stop

  # 下载完成后自动关机
  python scripts/download_manager.py start --universe wanzhu_selected --source tick \\
      --start-date 20250101 --end-date 20250131 --auto-shutdown
        """
    )
    
    parser.add_argument('action', choices=['start', 'stop', 'status', 'monitor', '_daemon'],
                       help='操作: start=启动, stop=停止, status=状态, monitor=监控')
    parser.add_argument('--universe', type=str, default='wanzhu_selected',
                       choices=['wanzhu_top150', 'wanzhu_selected', 'custom'],
                       help='股票池')
    parser.add_argument('--source', type=str, default='tick',
                       choices=['tick', '1m', '5m', 'daily'],
                       help='数据源')
    parser.add_argument('--mode', type=str, default='full',
                       choices=['full', 'incremental', 'missing', 'resume'],
                       help='模式: resume=断点续传')
    parser.add_argument('--start-date', type=str, help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end-date', type=str, help='结束日期 (YYYYMMDD)')
    parser.add_argument('--custom-path', type=str, help='自定义股票列表')
    parser.add_argument('--auto-shutdown', action='store_true',
                       help='下载完成后自动关机')
    
    args = parser.parse_args()
    
    manager = DownloadManager()
    
    if args.action == 'start':
        if not args.start_date or not args.end_date:
            if args.mode != 'resume':
                print("❌ 需要指定 --start-date 和 --end-date")
                sys.exit(1)
        manager.start_daemon(
            args.universe, args.source, args.start_date, args.end_date,
            args.mode, args.custom_path, args.auto_shutdown
        )
    
    elif args.action == 'stop':
        manager.stop()
    
    elif args.action == 'status':
        manager.status()
    
    elif args.action == 'monitor':
        manager.monitor()
    
    elif args.action == '_daemon':
        # 内部使用：后台进程入口
        manager._run_daemon(
            args.universe, args.source, args.start_date, args.end_date,
            args.mode, args.custom_path, args.auto_shutdown
        )


if __name__ == '__main__':
    main()
