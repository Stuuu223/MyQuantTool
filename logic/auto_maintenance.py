#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动维护系统 (AutoMaintenance) - V19.17.2

功能：
- 盘后自动下载历史数据（数据预热）
- 支持增量下载策略（只下载当天数据）
- 防止重复下载（通过日期标记）
- 支持多周期数据下载（1m, 1d, tick）

架构：
- 可集成到主程序（方案一）
- 也可作为独立脚本运行（方案二）
- 增量下载策略（避免磁盘爆炸）

Author: iFlow CLI
Version: V19.17.2
"""

import time
from datetime import datetime, timedelta
from typing import Optional, List
from logic.logger import get_logger

logger = get_logger(__name__)


class AutoMaintenance:
    """
    自动维护系统

    功能：
    - 盘后自动下载历史数据（数据预热）
    - 支持增量下载策略（只下载当天数据）
    - 防止重复下载（通过日期标记）
    - 支持多周期数据下载（1m, 1d, tick）

    使用方式：

    方案一：集成到主程序（实时检查）
    ```python
    maintainer = AutoMaintenance()
    while True:
        scan_market()
        maintainer.run_daily_job()  # 每次循环检查
        time.sleep(1)
    ```

    方案二：作为独立脚本运行
    ```python
    maintainer = AutoMaintenance()
    maintainer.run_daily_job()  # 一次性执行
    ```
    """

    def __init__(self):
        """初始化自动维护系统"""
        self.last_run_date = None
        self.qmt_available = False
        self.xtdata = None

        # 尝试加载 QMT
        self._load_qmt()

    def _load_qmt(self):
        """加载 QMT xtdata 模块"""
        try:
            import sys
            import os

            # 获取项目根目录（向上两级：logic -> MyQuantTool）
            # __file__ 应该是类似 C:\Users\pc\Desktop\Astock\MyQuantTool\logic\auto_maintenance.py
            current_file = os.path.abspath(__file__)
            logic_dir = os.path.dirname(current_file)
            project_root = os.path.dirname(logic_dir)

            # xtquant 路径
            xtquant_path = os.path.join(project_root, 'xtquant')

            logger.info(f"   当前文件: {current_file}")
            logger.info(f"   项目根目录: {project_root}")
            logger.info(f"   xtquant 路径: {xtquant_path}")

            # 添加到 sys.path
            if xtquant_path not in sys.path:
                sys.path.insert(0, xtquant_path)

            # 确保 xtquant 的父目录也在 sys.path 中
            parent_path = os.path.dirname(xtquant_path)
            if parent_path not in sys.path:
                sys.path.insert(0, parent_path)

            # 方法2：创建虚拟包结构，解决相对导入问题
            import importlib.util

            # 加载 xtbson 模块
            xtbson_spec = importlib.util.spec_from_file_location(
                "xtquant.xtbson",
                os.path.join(xtquant_path, "xtbson", "__init__.py")
            )
            xtbson_module = importlib.util.module_from_spec(xtbson_spec)
            xtbson_spec.loader.exec_module(xtbson_module)
            sys.modules['xtquant.xtbson'] = xtbson_module

            # 加载 xtdata_config 模块
            xtdata_config_spec = importlib.util.spec_from_file_location(
                "xtquant.xtdata_config",
                os.path.join(xtquant_path, "xtdata_config.py")
            )
            xtdata_config_module = importlib.util.module_from_spec(xtdata_config_spec)
            xtdata_config_spec.loader.exec_module(xtdata_config_module)
            sys.modules['xtquant.xtdata_config'] = xtdata_config_module

            # 加载 IPythonApiClient 模块
            ipython_api_spec = importlib.util.spec_from_file_location(
                "xtquant.IPythonApiClient",
                os.path.join(xtquant_path, "IPythonApiClient.py")
            )
            ipython_api_module = importlib.util.module_from_spec(ipython_api_spec)
            ipython_api_spec.loader.exec_module(ipython_api_module)
            sys.modules['xtquant.IPythonApiClient'] = ipython_api_module

            # 加载 xtdata 模块
            xtdata_spec = importlib.util.spec_from_file_location(
                "xtquant.xtdata",
                os.path.join(xtquant_path, "xtdata.py")
            )

            if xtdata_spec and xtdata_spec.loader:
                self.xtdata = importlib.util.module_from_spec(xtdata_spec)
                xtdata_spec.loader.exec_module(self.xtdata)
                self.qmt_available = True
                logger.info("✅ [AutoMaintenance] QMT xtdata 模块加载成功")
            else:
                raise ImportError("无法加载 xtdata 模块")

        except Exception as e:
            logger.warning(f"⚠️ [AutoMaintenance] QMT xtdata 模块未加载: {e}")
            import traceback
            traceback.print_exc()
            self.qmt_available = False

    def is_runnable(self) -> bool:
        """检查是否可以运行（QMT 是否可用）"""
        return self.qmt_available

    def run_daily_job(self, target_date: Optional[str] = None):
        """
        执行每日维护任务

        Args:
            target_date: 目标日期（格式：YYYYMMDD），None 表示今天

        触发条件：
        1. 时间在下午 15:30 之后（确保收盘数据已归档）
        2. 今天还没有运行过（防止重复下载）
        3. QMT 接口可用

        注意：
        - 如果指定了 target_date，会跳过时间检查，直接下载
        - 适合作为独立脚本运行
        """
        now = datetime.now()
        today_str = now.strftime('%Y%m%d')

        # 如果指定了目标日期，使用目标日期
        date_to_download = target_date if target_date else today_str

        # 检查是否已经运行过
        if self.last_run_date == date_to_download:
            logger.info(f"📅 [AutoMaintenance] {date_to_download} 数据预热已完成，跳过")
            return

        # 检查时间条件（仅在未指定 target_date 时检查）
        if target_date is None:
            if now.hour < 15 or (now.hour == 15 and now.minute < 30):
                logger.info(f"⏰ [AutoMaintenance] 等待收盘后运行（当前时间：{now.strftime('%H:%M:%S')}）")
                return

        logger.info(f">>> 🌅 [AutoMaintenance] 收盘作业启动：开始预热 {date_to_download} 的数据...")

        try:
            success = self.download_all_data(date_to_download)

            if success:
                self.last_run_date = date_to_download  # 标记今天已完成
                logger.info(f">>> ✅ [AutoMaintenance] {date_to_download} 数据预热完成！晚上复盘可以直接用。")
            else:
                logger.warning(f">>> ⚠️ [AutoMaintenance] {date_to_download} 数据预热部分失败")

        except Exception as e:
            logger.error(f">>> ❌ [AutoMaintenance] 自动下载失败: {e}")

    def download_all_data(self, date_str: str) -> bool:
        """
        下载所有需要的数据

        Args:
            date_str: 日期字符串（格式：YYYYMMDD）

        Returns:
            bool: 是否全部成功
        """
        if not self.qmt_available:
            logger.error("❌ [AutoMaintenance] QMT 接口不可用，无法下载数据")
            return False

        logger.info(f"📥 [AutoMaintenance] 开始下载 {date_str} 的数据...")

        # 1. 获取全市场代码（沪深A股）
        try:
            sector_list = self.xtdata.get_stock_list_in_sector('沪深A股')
            logger.info(f"    - 📊 目标股票数: {len(sector_list)}")
        except Exception as e:
            logger.error(f"❌ [AutoMaintenance] 获取股票列表失败: {e}")
            return False

        if not sector_list:
            logger.error("❌ [AutoMaintenance] 未获取到股票列表")
            return False

        # 2. 增量下载（只下载当天）
        # 这样速度极快，几分钟就搞定，不要每次都下'start_time=20200101'
        success_1m = self._download_period_data(sector_list, '1m', date_str)
        success_1d = self._download_period_data(sector_list, '1d', date_str)

        # Tick 数据可选（如果需要极精细复盘，文件会很大，按需开启）
        # success_tick = self._download_period_data(sector_list, 'tick', date_str)

        overall_success = success_1m and success_1d

        if overall_success:
            logger.info(f"✅ [AutoMaintenance] 所有数据下载完成（1m: {success_1m}, 1d: {success_1d}）")
        else:
            logger.warning(f"⚠️ [AutoMaintenance] 部分数据下载失败（1m: {success_1m}, 1d: {success_1d}）")

        return overall_success

    def _download_period_data(self, stock_list: List[str], period: str, date_str: str) -> bool:
        """
        下载指定周期的数据

        Args:
            stock_list: 股票代码列表
            period: 周期（'1m', '1d', 'tick'）
            date_str: 日期字符串（格式：YYYYMMDD）

        Returns:
            bool: 是否成功
        """
        period_names = {
            '1m': '1分钟K线',
            '1d': '日K线',
            'tick': 'Tick数据'
        }

        period_name = period_names.get(period, period)
        logger.info(f"    - 📥 正在下载 {period_name}...")

        try:
            self.xtdata.download_history_data(
                stock_list=stock_list,
                period=period,
                start_time=date_str,
                end_time=date_str
            )
            logger.info(f"    - ✅ {period_name} 下载成功")
            return True

        except Exception as e:
            logger.error(f"    - ❌ {period_name} 下载失败: {e}")
            return False

    def check_data_availability(self, date_str: str) -> dict:
        """
        检查指定日期的数据是否已下载

        Args:
            date_str: 日期字符串（格式：YYYYMMDD）

        Returns:
            dict: 各周期数据的可用性
                {
                    '1m': bool,
                    '1d': bool,
                    'tick': bool
                }
        """
        if not self.qmt_available:
            return {'1m': False, '1d': False, 'tick': False}

        result = {'1m': False, '1d': False, 'tick': False}

        # 随机选一只股票测试
        test_stock = '000001.SZ'

        try:
            # 测试 1分钟线
            data_1m = self.xtdata.get_market_data_ex(
                stock_list=[test_stock],
                period='1m',
                start_time=date_str + '093000',
                end_time=date_str + '150000',
                count=1
            )
            if data_1m and len(data_1m.get(test_stock, {})) > 0:
                result['1m'] = True

            # 测试 日线
            data_1d = self.xtdata.get_market_data_ex(
                stock_list=[test_stock],
                period='1d',
                start_time=date_str + '000000',
                end_time=date_str + '235959',
                count=1
            )
            if data_1d and len(data_1d.get(test_stock, {})) > 0:
                result['1d'] = True

        except Exception as e:
            logger.warning(f"⚠️ [AutoMaintenance] 检查数据可用性失败: {e}")

        return result

    def get_download_status(self, date_str: Optional[str] = None) -> dict:
        """
        获取下载状态

        Args:
            date_str: 日期字符串（格式：YYYYMMDD），None 表示今天

        Returns:
            dict: 下载状态
                {
                    'date': str,
                    'last_run_date': Optional[str],
                    'qmt_available': bool,
                    'data_available': dict
                }
        """
        now = datetime.now()
        today_str = now.strftime('%Y%m%d')
        date_to_check = date_str if date_str else today_str

        return {
            'date': date_to_check,
            'last_run_date': self.last_run_date,
            'qmt_available': self.qmt_available,
            'data_available': self.check_data_availability(date_to_check)
        }


if __name__ == '__main__':
    """作为独立脚本运行"""
    import sys

    print("=" * 60)
    print("🌅 QMT 数据自动预热系统")
    print("=" * 60)

    # 创建维护实例
    maintainer = AutoMaintenance()

    # 检查 QMT 是否可用
    if not maintainer.is_runnable():
        print("❌ QMT 接口不可用，请检查 QMT 客户端是否已启动")
        sys.exit(1)

    # 检查命令行参数
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        if not target_date.isdigit() or len(target_date) != 8:
            print(f"❌ 日期格式错误：{target_date}，请使用 YYYYMMDD 格式")
            sys.exit(1)
        print(f"📅 目标日期：{target_date}")
    else:
        now = datetime.now()
        print(f"📅 当前日期：{now.strftime('%Y-%m-%d')}")

    # 检查下载状态
    print("\n📊 检查下载状态...")
    status = maintainer.get_download_status(target_date)
    print(f"  - QMT 可用: {'✅' if status['qmt_available'] else '❌'}")
    print(f"  - 上次运行: {status['last_run_date'] or '未运行'}")
    print(f"  - 1m 数据: {'✅' if status['data_available']['1m'] else '❌'}")
    print(f"  - 1d 数据: {'✅' if status['data_available']['1d'] else '❌'}")

    # 执行下载
    print("\n🚀 开始执行数据预热...")
    maintainer.run_daily_job(target_date)

    # 再次检查下载状态
    print("\n📊 最终状态...")
    final_status = maintainer.get_download_status(target_date)
    print(f"  - 1m 数据: {'✅' if final_status['data_available']['1m'] else '❌'}")
    print(f"  - 1d 数据: {'✅' if final_status['data_available']['1d'] else '❌'}")

    print("\n" + "=" * 60)
    print("✅ 数据预热完成！")
    print("=" * 60)