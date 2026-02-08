#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMT 历史数据拉取脚本（后台进程）
每 10 分钟输出一次进度
"""

import sys
sys.path.append('E:/MyQuantTool')

import os
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict
from threading import Event

from logic.logger import get_logger
from logic.code_converter import CodeConverter

logger = get_logger(__name__)

# Configuration
PROGRESS_FILE = "E:/MyQuantTool/data/qmt_download_progress.json"
LOG_FILE = "E:/MyQuantTool/logs/qmt_download.log"

# Stock lists
STOCK_LISTS = {
    'test': ['600519.SH', '000001.SZ', '600000.SH'],  # 测试列表
    'sh50': None,  # 上证前50（需要从文件读取）
    'sz50': None,  # 深证前50（需要从文件读取）
    'all': None,  # 全市场（需要从文件读取）
}

# Periods to download
PERIODS = ['1d', '1m', '5m']  # 日线、1分钟、5分钟

# Date range
START_DATE = '20240101'
END_DATE = '20251231'

# Progress interval (seconds)
PROGRESS_INTERVAL = 600  # 10分钟


class QMTDataDownloader:
    """QMT 历史数据下载器"""
    
    def __init__(self):
        self.logger = logger
        self.code_converter = CodeConverter()
        self.stop_event = Event()
        
        # Load QMT
        try:
            from xtquant import xtdata
            self.xtdata = xtdata
            self.qmt_available = True
            self.logger.info("✅ QMT 接口加载成功")
        except ImportError as e:
            self.qmt_available = False
            self.logger.error(f"❌ QMT 接口加载失败: {e}")
    
    def load_progress(self) -> Dict:
        """加载进度"""
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'total_stocks': 0,
            'completed_stocks': 0,
            'total_periods': len(PERIODS),
            'completed_periods': 0,
            'current_batch': '',
            'start_time': None,
            'last_update': None,
            'failed_stocks': []
        }
    
    def save_progress(self, progress: Dict):
        """保存进度"""
        progress['last_update'] = datetime.now().isoformat()
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    
    def download_stock_data(self, stock_code: str, period: str, start_date: str, end_date: str) -> bool:
        """
        下载单只股票的历史数据
        
        Args:
            stock_code: 股票代码
            period: 周期（1d, 1m, 5m）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        
        Returns:
            bool: 是否成功
        """
        if not self.qmt_available:
            self.logger.error("❌ QMT 接口不可用")
            return False
        
        try:
            # 转换为 QMT 格式
            qmt_code = self.code_converter.to_qmt(stock_code)
            
            self.logger.info(f"📥 开始下载: {stock_code} ({period}) [{start_date} - {end_date}]")
            
            # 下载历史数据
            self.xtdata.download_history_data(
                stock_code=qmt_code,
                period=period,
                start_time=start_date,
                end_time=end_date
            )
            
            self.logger.info(f"✅ 下载成功: {stock_code} ({period})")
            return True
        
        except Exception as e:
            self.logger.error(f"❌ 下载失败: {stock_code} ({period}) - {e}")
            return False
    
    def verify_data(self, stock_code: str, period: str) -> bool:
        """
        验证数据是否下载成功
        
        Args:
            stock_code: 股票代码
            period: 周期
        
        Returns:
            bool: 是否验证成功
        """
        if not self.qmt_available:
            return False
        
        try:
            qmt_code = self.code_converter.to_qmt(stock_code)
            
            # 获取本地数据
            data = self.xtdata.get_local_data(
                field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=[qmt_code],
                period=period,
                start_time=START_DATE,
                end_time=END_DATE,
                count=-1
            )
            
            if data and qmt_code in data:
                df = data[qmt_code]
                if df is not None and len(df) > 0:
                    self.logger.info(f"✅ 验证成功: {stock_code} ({period}) - {len(df)} 条记录")
                    return True
            
            self.logger.warning(f"⚠️ 验证失败: {stock_code} ({period}) - 数据为空")
            return False
        
        except Exception as e:
            self.logger.error(f"❌ 验证失败: {stock_code} ({period}) - {e}")
            return False
    
    def download_batch(self, stock_list: List[str], period: str, batch_name: str) -> Dict:
        """
        下载一批股票的历史数据
        
        Args:
            stock_list: 股票代码列表
            period: 周期
            batch_name: 批次名称
        
        Returns:
            Dict: 下载结果
        """
        progress = self.load_progress()
        
        results = {
            'success': [],
            'failed': [],
            'total': len(stock_list),
            'period': period,
            'batch_name': batch_name
        }
        
        self.logger.info(f"📦 开始下载批次: {batch_name} ({period}) - {len(stock_list)} 只股票")
        
        for i, stock_code in enumerate(stock_list, 1):
            if self.stop_event.is_set():
                self.logger.info("⚠️ 收到停止信号，终止下载")
                break
            
            # 下载数据
            success = self.download_stock_data(stock_code, period, START_DATE, END_DATE)
            
            if success:
                results['success'].append(stock_code)
            else:
                results['failed'].append(stock_code)
            
            # 更新进度
            progress['completed_stocks'] += 1
            progress['current_batch'] = f"{batch_name}_{period}"
            progress['failed_stocks'] = results['failed']
            self.save_progress(progress)
            
            # 每 10 只股票输出一次进度
            if i % 10 == 0:
                self.logger.info(f"📊 进度: {i}/{len(stock_list)} ({batch_name}_{period})")
        
        self.logger.info(f"✅ 批次下载完成: {batch_name} ({period}) - 成功 {len(results['success'])}, 失败 {len(results['failed'])}")
        
        return results
    
    def print_progress(self):
        """打印进度信息"""
        progress = self.load_progress()
        
        print("\n" + "=" * 60)
        print(f"QMT 历史数据下载进度")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        print(f"📊 总进度:")
        print(f"  总股票数: {progress['total_stocks']}")
        print(f"  已完成: {progress['completed_stocks']}")
        print(f"  完成率: {progress['completed_stocks'] / max(progress['total_stocks'], 1) * 100:.1f}%")
        
        print(f"\n📅 周期进度:")
        print(f"  总周期数: {progress['total_periods']}")
        print(f"  已完成周期: {progress['completed_periods']}")
        
        print(f"\n📁 当前批次: {progress['current_batch']}")
        print(f"📅 开始时间: {progress.get('start_time', 'N/A')}")
        print(f"📅 最后更新: {progress['last_update']}")
        
        if progress['failed_stocks']:
            print(f"\n❌ 失败股票 ({len(progress['failed_stocks'])}):")
            for stock in progress['failed_stocks'][:10]:
                print(f"  - {stock}")
            if len(progress['failed_stocks']) > 10:
                print(f"  ... 还有 {len(progress['failed_stocks']) - 10} 只")
        
        print("=" * 60)
    
    def run_background_download(self, stock_list: List[str] = None, periods: List[str] = None):
        """
        运行后台下载任务
        
        Args:
            stock_list: 股票代码列表
            periods: 周期列表
        """
        # 设置默认值
        if stock_list is None:
            stock_list = STOCK_LISTS['test']
        
        if periods is None:
            periods = PERIODS
        
        # 初始化进度
        progress = self.load_progress()
        progress['total_stocks'] = len(stock_list)
        progress['total_periods'] = len(periods)
        progress['start_time'] = datetime.now().isoformat()
        self.save_progress(progress)
        
        self.logger.info(f"🚀 开始后台下载任务: {len(stock_list)} 只股票 x {len(periods)} 个周期")
        
        last_print_time = time.time()
        
        # 遍历所有周期
        for i, period in enumerate(periods):
            if self.stop_event.is_set():
                self.logger.info("⚠️ 收到停止信号，终止下载")
                break
            
            period_name = f"Period_{i+1}_{period}"
            
            # 下载该周期
            results = self.download_batch(stock_list, period, period_name)
            
            # 更新进度
            progress['completed_periods'] += 1
            progress['current_batch'] = f"{period_name}_completed"
            self.save_progress(progress)
        
        # 完成所有下载
        progress['current_batch'] = "All_completed"
        progress['completed_stocks'] = progress['total_stocks']
        self.save_progress(progress)
        
        self.logger.info(f"✅ 所有下载任务完成!")
        self.print_progress()
    
    def run_with_progress_monitor(self, stock_list: List[str] = None, periods: List[str] = None):
        """
        运行下载任务，并每 10 分钟输出一次进度
        
        Args:
            stock_list: 股票代码列表
            periods: 周期列表
        """
        import threading
        
        # 设置默认值
        if stock_list is None:
            stock_list = STOCK_LISTS['test']
        
        if periods is None:
            periods = PERIODS
        
        # 创建下载线程
        download_thread = threading.Thread(
            target=self.run_background_download,
            args=(stock_list, periods)
        )
        
        download_thread.daemon = True
        download_thread.start()
        
        self.logger.info(f"✅ 后台下载任务已启动，PID: {download_thread.ident}")
        self.logger.info(f"📊 每 {PROGRESS_INTERVAL} 秒输出一次进度")
        self.logger.info(f"⚠️ 按 Ctrl+C 停止下载")
        
        # 初始化进度打印时间
        last_print_time = time.time()
        
        # 进度监控循环
        try:
            while download_thread.is_alive():
                # 每隔一段时间打印进度
                if time.time() - last_print_time >= PROGRESS_INTERVAL:
                    self.print_progress()
                    last_print_time = time.time()
                
                # 检查是否停止
                if self.stop_event.is_set():
                    self.logger.info("⚠️ 收到停止信号")
                    break
                
                # 等待一段时间
                time.sleep(10)
        
        except KeyboardInterrupt:
            self.logger.info("⚠️ 用户中断下载")
            self.stop_event.set()
        
        # 等待线程结束
        download_thread.join(timeout=5)
        
        self.logger.info("✅ 下载任务已结束")
        self.print_progress()


def main():
    """主函数"""
    downloader = QMTDataDownloader()
    
    # 检查 QMT 是否可用
    if not downloader.qmt_available:
        print("❌ QMT 接口不可用，无法执行下载任务")
        print("请确保:")
        print("  1. QMT 环境已正确配置")
        print("  2. xtquant 库已正确安装")
        print("  3. QMT 客户端正在运行")
        return
    
    # 打印配置信息
    print("=" * 60)
    print("QMT 历史数据下载任务")
    print("=" * 60)
    print(f"📅 时间范围: {START_DATE} - {END_DATE}")
    print(f"📊 周期: {', '.join(PERIODS)}")
    print(f"📈 股票数: {len(STOCK_LISTS['test'])} (测试模式)")
    print(f"⏱️  进度输出间隔: {PROGRESS_INTERVAL} 秒")
    print(f"📁 进度文件: {PROGRESS_FILE}")
    print(f"📝 日志文件: {LOG_FILE}")
    print("=" * 60)
    
    # 运行下载任务
    downloader.run_with_progress_monitor(
        stock_list=STOCK_LISTS['test'],
        periods=PERIODS
    )


if __name__ == "__main__":
    main()