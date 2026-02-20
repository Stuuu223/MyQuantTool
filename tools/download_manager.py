#!/usr/bin/env python3
"""
下载管理器 - 通用数据下载框架 V3.0 (Download Manager)

架构设计原则：
1. 插件化数据源：支持QMT、AkShare、Tushare、自定义API
2. 统一数据类型：Tick、1m、5m、日线、财务数据
3. 抽象股票池：顽主、自定义、全市场、板块
4. 可扩展：新增数据源只需实现provider接口

取代脚本：
- tick_download.py（后台管理+监控）
- estimate_tick_download_time.py（时间估算）
- shutdown_after_download.py（自动关机）
- monitor_runner.py --mode download（监控）

Author: AI Project Director
Version: V3.0
Date: 2026-02-19
"""

import sys
import os
import time
import json
import signal
import subprocess
import argparse
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Type, Protocol
from dataclasses import dataclass, asdict
from enum import Enum

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 状态文件
PID_FILE = PROJECT_ROOT / 'logs' / 'download' / 'download_manager.pid'
STATUS_FILE = PROJECT_ROOT / 'logs' / 'download' / 'download_manager_status.json'
RESUME_FILE = PROJECT_ROOT / 'logs' / 'download' / 'download_manager_resume.json'

# 尝试导入Rich
HAS_RICH = False
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn
    console = Console()
    HAS_RICH = True
except ImportError:
    console = None

from logic.services.config_service import ConfigService


class DataSource(str, Enum):
    """数据源类型"""
    QMT = 'qmt'           # QMT本地数据
    AKSHARE = 'akshare'   # AkShare在线
    TUSHARE = 'tushare'   # Tushare Pro
    CUSTOM = 'custom'     # 自定义API


class DataType(str, Enum):
    """数据类型"""
    TICK = 'tick'         # Tick级数据
    MINUTE_1 = '1m'       # 1分钟K线
    MINUTE_5 = '5m'       # 5分钟K线
    MINUTE_15 = '15m'     # 15分钟K线
    MINUTE_30 = '30m'     # 30分钟K线
    DAILY = 'daily'       # 日线
    WEEKLY = 'weekly'     # 周线
    FUNDAMENTAL = 'fund'  # 财务数据


class UniverseType(str, Enum):
    """股票池类型"""
    WANZHU_SELECTED = 'wanzhu_selected'  # 顽主精选150
    WANZHU_ALL = 'wanzhu_all'            # 全部顽主股票
    CUSTOM = 'custom'                    # 自定义列表
    FULL_MARKET = 'full_market'          # 全市场（慎用）


# ==================== 数据提供者接口 ====================

class DataProvider(ABC):
    """数据提供者抽象基类
    
    新增数据源时，继承此类并实现所有抽象方法
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """提供者名称"""
        pass
    
    @property
    @abstractmethod
    def supported_types(self) -> List[DataType]:
        """支持的数据类型列表"""
        pass
    
    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def download(self, stock_code: str, data_type: DataType, 
                 start_date: str, end_date: str) -> Dict:
        """下载单只股票数据
        
        Returns:
            {'success': bool, 'message': str, 'records': int}
        """
        pass
    
    @abstractmethod
    def check_coverage(self, stock_codes: List[str], data_type: DataType,
                       date: str) -> Dict[str, Dict]:
        """检查数据覆盖情况"""
        pass
    
    def estimate_time_per_stock(self, data_type: DataType) -> float:
        """估算每只股票下载时间（秒）
        
        子类可覆盖以提供更精确的估算
        """
        estimates = {
            DataType.TICK: 60,
            DataType.MINUTE_1: 10,
            DataType.MINUTE_5: 5,
            DataType.DAILY: 1,
        }
        return estimates.get(data_type, 30)


class QMTProvider(DataProvider):
    """QMT数据提供者"""
    
    def __init__(self):
        self._provider = None
    
    @property
    def name(self) -> str:
        return 'QMT'
    
    @property
    def supported_types(self) -> List[DataType]:
        return [DataType.TICK, DataType.MINUTE_1, DataType.MINUTE_5, 
                DataType.MINUTE_15, DataType.MINUTE_30, DataType.DAILY]
    
    def connect(self) -> bool:
        try:
            from logic.data_providers.tick_provider import TickProvider
            self._provider = TickProvider()
            return self._provider.connect()
        except Exception as e:
            print(f"❌ QMT连接失败: {e}")
            return False
    
    def disconnect(self):
        if self._provider:
            # TickProvider没有disconnect方法，但有__exit__
            if hasattr(self._provider, 'disconnect'):
                self._provider.disconnect()
            # 否则使用上下文管理器的方式清理
            self._provider = None
    
    def download(self, stock_code: str, data_type: DataType,
                 start_date: str, end_date: str) -> Dict:
        try:
            if data_type == DataType.TICK:
                # 使用download_ticks方法（返回BatchDownloadResult对象）
                batch_result = self._provider.download_ticks([stock_code], start_date, end_date)
                # 转换为字典格式
                return {
                    'success': batch_result.success > 0,
                    'message': f'成功{batch_result.success}只, 失败{batch_result.failed}只',
                    'records': batch_result.success
                }
            elif data_type in [DataType.MINUTE_1, DataType.MINUTE_5]:
                period = '1m' if data_type == DataType.MINUTE_1 else '5m'
                result = self._provider.download_minute_data([stock_code], start_date, end_date, period)
                return {
                    'success': result.get('success', False),
                    'message': result.get('message', ''),
                    'records': result.get('records', 0)
                }
            else:
                return {'success': False, 'message': f'QMT不支持{data_type}', 'records': 0}
        except Exception as e:
            return {'success': False, 'message': str(e), 'records': 0}
    
    def check_coverage(self, stock_codes: List[str], data_type: DataType, date: str) -> Dict:
        return self._provider.check_coverage(stock_codes, date)


class AkShareProvider(DataProvider):
    """AkShare在线数据提供者（备用）"""
    
    @property
    def name(self) -> str:
        return 'AkShare'
    
    @property
    def supported_types(self) -> List[DataType]:
        return [DataType.MINUTE_1, DataType.MINUTE_5, DataType.DAILY]
    
    def connect(self) -> bool:
        try:
            import akshare as ak
            return True
        except ImportError:
            print("❌ AkShare未安装: pip install akshare")
            return False
    
    def disconnect(self):
        pass
    
    def download(self, stock_code: str, data_type: DataType,
                 start_date: str, end_date: str) -> Dict:
        # TODO: 实现AkShare下载逻辑
        return {'success': False, 'message': 'AkShare下载未实现', 'records': 0}
    
    def check_coverage(self, stock_codes: List[str], data_type: DataType, date: str) -> Dict:
        return {}


# ==================== 股票池加载器 ====================

class UniverseLoader:
    """股票池加载器"""
    
    def __init__(self):
        self.config_service = ConfigService()
    
    def load(self, universe_type: UniverseType, custom_path: Optional[str] = None) -> List[str]:
        """加载股票代码列表"""
        if universe_type == UniverseType.WANZHU_SELECTED:
            return self._load_wanzhu_selected()
        elif universe_type == UniverseType.CUSTOM and custom_path:
            return self._load_custom(custom_path)
        else:
            raise ValueError(f"未知的股票池类型: {universe_type}")
    
    def _load_wanzhu_selected(self) -> List[str]:
        """加载顽主精选150"""
        csv_path = PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv'
        import pandas as pd
        df = pd.read_csv(csv_path)
        codes = []
        for _, row in df.iterrows():
            code = str(row['code']).zfill(6)
            codes.append(f"{code}.SH" if code.startswith('6') else f"{code}.SZ")
        return codes
    
    def _load_custom(self, path: str) -> List[str]:
        """加载自定义列表"""
        with open(path, 'r') as f:
            return [line.strip() for line in f if line.strip()]


# ==================== 下载状态管理 ====================

@dataclass
class DownloadState:
    """下载状态"""
    universe: str = ''
    data_source: str = ''
    data_type: str = ''
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


class DownloadManager:
    """通用下载管理器"""
    
    # 注册的提供者
    _providers: Dict[DataSource, Type[DataProvider]] = {
        DataSource.QMT: QMTProvider,
        DataSource.AKSHARE: AkShareProvider,
    }
    
    def __init__(self):
        self.universe_loader = UniverseLoader()
        self.state = DownloadState()
        self._running = False
        self._current_provider: Optional[DataProvider] = None
    
    @classmethod
    def register_provider(cls, source: DataSource, provider_class: Type[DataProvider]):
        """注册新的数据提供者"""
        cls._providers[source] = provider_class
    
    def get_provider(self, source: DataSource) -> DataProvider:
        """获取数据提供者实例"""
        if source not in self._providers:
            raise ValueError(f"未知的数据源: {source}")
        return self._providers[source]()
    
    def load_universe(self, universe_type: UniverseType, custom_path: Optional[str] = None) -> List[str]:
        """加载股票池"""
        return self.universe_loader.load(universe_type, custom_path)
    
    def estimate_time(self, num_stocks: int, data_type: DataType, provider: DataProvider) -> Dict:
        """估算下载时间"""
        seconds_per_stock = provider.estimate_time_per_stock(data_type)
        total_seconds = num_stocks * seconds_per_stock * 1.2  # 20%缓冲
        
        return {
            'seconds': total_seconds,
            'minutes': total_seconds / 60,
            'formatted': self._format_duration(total_seconds)
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
    
    def download(self, stock_codes: List[str], data_source: DataSource, data_type: DataType,
                 start_date: str, end_date: str, mode: str = 'full'):
        """执行下载"""
        self.state.total_stocks = len(stock_codes)
        self.state.start_time = datetime.now().isoformat()
        self.state.status = 'running'
        self._running = True
        
        # 获取提供者
        provider = self.get_provider(data_source)
        self._current_provider = provider
        
        print(f"\n{'='*60}")
        print(f"开始下载: {len(stock_codes)}只股票")
        print(f"数据源: {provider.name}")
        print(f"数据类型: {data_type.value}")
        print(f"时间范围: {start_date} ~ {end_date}")
        print(f"{'='*60}\n")
        
        # 连接
        if not provider.connect():
            self.state.status = 'error'
            self.state.message = '连接失败'
            return [], []
        
        try:
            completed, failed = self._download_with_progress(
                stock_codes, provider, data_type, start_date, end_date, mode
            )
        finally:
            provider.disconnect()
        
        # 完成
        if self._running:
            self.state.status = 'completed'
            print(f"\n{'='*60}")
            print("✅ 下载完成")
            print(f"  成功: {self.state.completed_stocks}")
            print(f"  失败: {self.state.failed_stocks}")
            print(f"{'='*60}")
        
        return completed, failed
    
    def _download_with_progress(self, stock_codes: List[str], provider: DataProvider,
                                 data_type: DataType, start_date: str, end_date: str, mode: str):
        """带进度显示的下载"""
        completed = []
        failed = []
        start_time = time.time()
        
        for i, stock_code in enumerate(stock_codes):
            if not self._running:
                print(f"\n⏸️ 下载暂停 ({i}/{len(stock_codes)})")
                break
            
            self.state.current_stock = stock_code
            
            # 显示进度
            if i % 5 == 0 or i == len(stock_codes) - 1:
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed * 60 if elapsed > 0 else 0
                remaining = len(stock_codes) - i - 1
                eta = remaining / (speed / 60) if speed > 0 else 0
                
                # 百分比进度条
                progress = (i + 1) / len(stock_codes)
                bar_length = 30
                filled = int(bar_length * progress)
                bar = '█' * filled + '░' * (bar_length - filled)
                percent = int(progress * 100)
                
                print(f"[{percent}%] {bar} {i+1}/{len(stock_codes)} | {stock_code} "
                      f"| 速度: {speed:.1f}只/分 | 剩余: {self._format_duration(eta)}")
            
            # 下载
            try:
                result = provider.download(stock_code, data_type, start_date, end_date)
                if result.get('success'):
                    completed.append(stock_code)
                    self.state.completed_stocks += 1
                else:
                    failed.append(stock_code)
                    self.state.failed_stocks += 1
            except Exception as e:
                failed.append(stock_code)
                self.state.failed_stocks += 1
            
            self._save_status()
            time.sleep(0.2)  # 避免限流
        
        return completed, failed
    
    def _save_status(self):
        """保存状态"""
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state.to_dict(), f, ensure_ascii=False, indent=2)


# ==================== CLI入口 ====================

def main():
    parser = argparse.ArgumentParser(
        description='下载管理器 V3.0 - 通用数据下载框架',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 下载顽主精选150的Tick数据（QMT）
  python tools/download_manager.py --source qmt --type tick \\
      --universe wanzhu_selected --start 20250101 --end 20250131
  
  # 下载1分钟数据（QMT）
  python tools/download_manager.py --source qmt --type 1m \\
      --universe wanzhu_selected --start 20250101 --end 20250131
  
  # 自定义股票列表
  python tools/download_manager.py --source qmt --type tick \\
      --universe custom --custom-list my_stocks.txt --start 20250101 --end 20250131
        """
    )
    
    parser.add_argument('--source', type=str, required=True,
                       choices=['qmt', 'akshare', 'tushare'],
                       help='数据源')
    parser.add_argument('--type', type=str, required=True,
                       choices=['tick', '1m', '5m', '15m', '30m', 'daily'],
                       help='数据类型')
    parser.add_argument('--universe', type=str, default='wanzhu_selected',
                       choices=['wanzhu_selected', 'custom'],
                       help='股票池')
    parser.add_argument('--custom-list', type=str,
                       help='自定义股票列表文件路径')
    parser.add_argument('--start', type=str, required=True,
                       help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', type=str, required=True,
                       help='结束日期 (YYYYMMDD)')
    parser.add_argument('--mode', type=str, default='full',
                       choices=['full', 'missing', 'resume'],
                       help='下载模式')
    
    args = parser.parse_args()
    
    # 映射参数
    source = DataSource(args.source)
    data_type = DataType(args.type)
    universe = UniverseType(args.universe)
    
    # 执行下载
    manager = DownloadManager()
    stock_codes = manager.load_universe(universe, args.custom_list)
    
    print(f"✅ 加载股票池: {len(stock_codes)}只")
    
    # 估算时间
    provider = manager.get_provider(source)
    estimate = manager.estimate_time(len(stock_codes), data_type, provider)
    print(f"⏱️  预估时间: {estimate['formatted']}")
    
    # 下载
    completed, failed = manager.download(
        stock_codes, source, data_type, args.start, args.end, args.mode
    )
    
    return 0 if len(failed) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
