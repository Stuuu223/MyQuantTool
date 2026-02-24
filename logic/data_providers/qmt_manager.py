# -*- coding: utf-8 -*-
"""
QMT 数据管理器 - VIP版本

功能：
1. 管理 QMT 数据接口连接（普通+VIP）
2. 提供统一的 QMT 数据下载接口（日线/分钟线/Tick）
3. 数据完整性验证与补充下载
4. 自动重连和错误处理

CTO Phase 6.2 重构目标：
- 整合 tools/download_tick_with_vip.py
- 整合 tools/download_qmt_history.py
- 整合 tools/supplement_tick_download.py
- 整合 tools/quick_audit_top10.py 中的数据检查逻辑

Author: iFlow CLI
Date: 2026-02-23
Version: V2.0 (CTO Phase 6.2 重构版)
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

try:
    from xtquant import xtdata, xttrader, xtdatacenter as xtdc

    XT_AVAILABLE = True
except ImportError:
    XT_AVAILABLE = False
    xtdc = None
    xtdata = None
    xttrader = None

# 导入QMTRouter - 接入熔断机制
from logic.data_providers.fallback_provider import QMTRouter, CircuitBreakerError

import logging

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """下载结果数据结构"""

    success: bool
    stock_code: str
    period: str
    record_count: int = 0
    message: str = ""
    error: Optional[str] = None


@dataclass
class DataIntegrityReport:
    """数据完整性报告"""

    stock_code: str
    trade_date: str
    has_daily: bool = False
    has_minute: bool = False
    has_tick: bool = False
    daily_count: int = 0
    minute_count: int = 0
    tick_count: int = 0
    missing_periods: List[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """检查是否完整（所有周期都有数据）"""
        return self.has_daily and self.has_minute and self.has_tick

    @property
    def completeness_ratio(self) -> float:
        """完整度比率 (0.0-1.0)"""
        checks = [self.has_daily, self.has_minute, self.has_tick]
        return sum(checks) / len(checks)


class QmtDataManager:
    """
    QMT数据管理器（VIP支持）

    整合所有QMT下载能力，支持VIP服务下载Tick数据。

    Attributes:
        vip_token: VIP服务Token
        data_dir: QMT数据目录
        use_vip: 是否使用VIP服务
        listen_port: VIP服务监听端口

    Example:
        >>> manager = QmtDataManager(vip_token="your_token")
        >>> manager.start_vip_service()
        >>> result = manager.download_tick_data(['000001.SZ'], '20251231')
        >>> print(result)
    """

    # VIP默认配置（从CTO配置中提取）
    DEFAULT_VIP_TOKEN = "6b1446e317ed67596f13d2e808291a01e0dd9839"
    # CTO修复：删除硬编码路径，改为从环境变量读取

    # CTO修复：类级别静态变量实现单例连接
    _vip_global_initialized = False
    _vip_global_port = None
    _vip_global_lock = False

    def __init__(
        self,
        vip_token: Optional[str] = None,
        data_dir: Optional[str] = None,
        use_vip: bool = True,
        port_range: Tuple[int, int] = (58700, 58750),  # CTO修复: 扩大端口范围避免冲突
    ):
        """
        初始化QMT数据管理器

        Args:
            vip_token: VIP服务Token，默认从配置读取
            data_dir: QMT数据目录，默认从环境变量QMT_PATH读取
            use_vip: 是否启用VIP服务
            port_range: VIP服务端口范围
        """
        self.vip_token = vip_token or self._load_vip_token()
        # CTO修复：优先从环境变量读取，删除硬编码
        env_data_dir = os.getenv("QMT_PATH", "")
        self.data_dir = Path(data_dir or env_data_dir or self._detect_qmt_path())
        self.use_vip = use_vip and XT_AVAILABLE
        self.port_range = port_range
        self.listen_port: Optional[Tuple[str, int]] = None
        self._vip_initialized: bool = False

        logger.info(
            f"[QmtDataManager] 初始化完成 | VIP: {use_vip} | 数据目录: {self.data_dir}"
        )

    def _detect_qmt_path(self) -> str:
        """自动检测QMT数据目录"""
        # 首先尝试从环境变量获取，这应该是最优先的
        env_path = os.getenv("QMT_PATH", "")
        if env_path and os.path.exists(env_path):
            logger.info(f"[QmtDataManager] 从环境变量获取到QMT路径: {env_path}")
            return env_path
        
        # 智能检测：通过xtdata获取实际连接的数据路径
        try:
            # 尝试从xtdata获取当前连接的数据路径
            from xtquant import xtdata
            # xtdata连接时会显示数据路径，我们可以利用这个信息
            # 首先获取已连接的信息
            import logging
            # 临时降低日志级别以捕获连接信息
            xtdata.enable_hello = False
        except:
            pass
            
        # 如果环境变量未设置，尝试智能检测常见位置
        # 使用PathResolver获取项目配置，而不是硬编码路径
        from logic.core.path_resolver import PathResolver
        project_root = PathResolver.get_root()
        
        # 尝试基于当前系统环境智能检测
        import platform
        import subprocess
        try:
            # 尝试从注册表或系统信息中获取QMT安装信息（Windows）
            if platform.system() == "Windows":
                # 检查常见位置
                import winreg
                possible_paths = []
                
                # 检查H盘默认位置
                h_drive_default = Path("H:/QMT/userdata_mini")
                if h_drive_default.exists():
                    possible_paths.append(str(h_drive_default))
                    
                h_drive_alt = Path("H:/国金证券QMT交易端/userdata_mini")
                if h_drive_alt.exists():
                    possible_paths.append(str(h_drive_alt))
                
                # 检查其他盘符的常见安装位置
                for drive in ['C', 'D', 'E', 'F']:
                    path1 = Path(f"{drive}:/qmt/userdata_mini")
                    path2 = Path(f"{drive}:/国金证券QMT交易端/userdata_mini")
                    if path1.exists():
                        possible_paths.append(str(path1))
                    if path2.exists():
                        possible_paths.append(str(path2))
                
                # 返回第一个找到的路径
                for path in possible_paths:
                    if os.path.exists(path):
                        logger.info(f"[QmtDataManager] 智能检测到QMT路径: {path}")
                        return path
                        
        except Exception as e:
            logger.debug(f"[QmtDataManager] 智能检测失败: {e}")
        
        # 如果所有检测都失败，返回环境变量中配置的默认路径
        return "H:/QMT/userdata_mini"  # 这个路径在.env文件中有配置

    def _load_vip_token(self) -> str:
        """从配置文件加载VIP Token - 严格使用环境变量"""
        # 从环境变量读取（唯一正确的方式）
        env_token = os.getenv('QMT_VIP_TOKEN')
        if env_token and env_token.strip():
            logger.info("[QmtDataManager] 从环境变量读取VIP Token")
            return env_token.strip()
        
        # 如果环境变量未设置，提醒用户
        logger.warning("[QmtDataManager] QMT_VIP_TOKEN环境变量未设置，请检查.env文件")
        logger.info(f"[QmtDataManager] 使用默认VIP Token")
        return self.DEFAULT_VIP_TOKEN

    def start_vip_service(self) -> Optional[Tuple[str, int]]:
        """
        启动VIP行情服务 (CTO修复: 单例模式)

        Returns:
            监听地址和端口元组，启动失败返回None
        """
        # CTO修复：检查全局单例状态
        if QmtDataManager._vip_global_initialized and QmtDataManager._vip_global_port:
            logger.info("[QmtDataManager] VIP服务已在运行，复用现有连接")
            self._vip_initialized = True
            self.listen_port = QmtDataManager._vip_global_port
            return self.listen_port

        # 防止并发启动
        if QmtDataManager._vip_global_lock:
            logger.info("[QmtDataManager] VIP服务正在启动中，等待...")
            import time

            for _ in range(30):  # 最多等30秒
                time.sleep(1)
                if QmtDataManager._vip_global_initialized:
                    self._vip_initialized = True
                    self.listen_port = QmtDataManager._vip_global_port
                    return self.listen_port
            logger.error("[QmtDataManager] 等待VIP服务启动超时")
            return None

        QmtDataManager._vip_global_lock = True

        if not XT_AVAILABLE or not self.use_vip:
            logger.warning("[QmtDataManager] VIP服务不可用或已禁用")
            QmtDataManager._vip_global_lock = False
            return None

        if self._vip_initialized:
            QmtDataManager._vip_global_lock = False
            return self.listen_port

        try:
            logger.info("=" * 60)
            logger.info("【启动QMT VIP行情服务】")
            logger.info("=" * 60)

            # 1. 设置数据目录
            self.data_dir.mkdir(parents=True, exist_ok=True)
            xtdc.set_data_home_dir(str(self.data_dir))
            logger.info(f"📂 QMT数据目录: {self.data_dir}")

            # 2. 设置VIP Token
            xtdc.set_token(self.vip_token)
            logger.info(f"🔑 VIP Token: {self.vip_token[:6]}...{self.vip_token[-4:]}")

            # 3. 初始化并监听端口
            xtdc.init()
            listen_result = xtdc.listen(port=self.port_range)
            # CTO修复：xtdc.listen返回(ip, port) tuple
            if isinstance(listen_result, tuple) and len(listen_result) == 2:
                ip, port = listen_result
                self.listen_port = (ip, int(port))
            else:
                # 兼容旧版本返回单个port的情况
                self.listen_port = ("127.0.0.1", int(listen_result))
            self._vip_initialized = True

            # CTO修复：设置全局单例状态
            QmtDataManager._vip_global_initialized = True
            QmtDataManager._vip_global_port = self.listen_port
            QmtDataManager._vip_global_lock = False

            logger.info(f"🚀 VIP行情服务已启动，监听端口: {port}")
            logger.info("=" * 60)

            return self.listen_port

        except Exception as e:
            logger.error(f"[QmtDataManager] 启动VIP服务失败: {e}")
            self._vip_initialized = False
            QmtDataManager._vip_global_lock = False
            
            # 检查是否是路径相关错误
            error_msg = str(e)
            if "系统找不到指定的路径" in error_msg or "FileNotFoundError" in error_msg or "path" in error_msg.lower():
                raise RuntimeError(
                    f"❌ VIP服务启动失败：路径配置错误！\n"
                    f"💡 问题诊断：\n"
                    f"   - QMT数据目录路径不存在: {self.data_dir}\n"
                    f"   - 请检查QMT是否已正确安装\n"
                    f"   - 请检查.env文件中的QMT_PATH配置\n\n"
                    f"🔧 解决方案：\n"
                    f"   1. 确认QMT客户端已安装并运行\n"
                    f"   2. 检查环境变量QMT_PATH是否指向正确的QMT数据目录\n"
                    f"   3. 常见路径: H:\\QMT\\userdata_mini, E:\\QMT\\userdata_mini\n"
                    f"   4. 如需帮助，请检查QMT客户端实际数据路径\n\n"
                    f"📋 当前配置路径: {self.data_dir}\n"
                    f"📋 错误详情: {e}"
                )
            else:
                # CTO修复：VIP失败直接熔断，不降级
                raise RuntimeError(
                    f"❌ VIP服务启动失败，系统熔断！\n"
                    f"💡 问题诊断：{e}\n\n"
                    f"🔧 解决方案：\n"
                    f"   1. 检查VIP Token是否正确\n"
                    f"   2. 确认QMT客户端正在运行\n"
                    f"   3. 检查网络连接和防火墙设置\n"
                    f"   4. 尝试重启QMT客户端\n\n"
                    f"📋 错误详情: {e}"
                )

    def stop_vip_service(self) -> bool:
        """
        停止VIP行情服务

        Returns:
            是否成功停止
        """
        if not self._vip_initialized:
            return True

        try:
            # xtquant不直接提供服务停止接口，通过关闭连接实现
            self._vip_initialized = False
            self.listen_port = None
            logger.info("[QmtDataManager] VIP服务已停止")
            return True
        except Exception as e:
            logger.error(f"[QmtDataManager] 停止VIP服务失败: {e}")
            return False

    def _ensure_vip_connection(self) -> bool:
        """确保VIP连接可用"""
        if not self._vip_initialized:
            self.start_vip_service()

        if self._vip_initialized and self.listen_port:
            try:
                _, port = self.listen_port
                # CTO修复：确保port是整数
                if isinstance(port, str):
                    port = int(port)
                xtdata.connect(ip="127.0.0.1", port=port, remember_if_success=False)
                return True
            except Exception as e:
                logger.error(f"[QmtDataManager] VIP连接失败: {e}")
                return False
        return False

    def download_daily_data(
        self, stock_list: List[str], start_date: str, end_date: str, delay: float = 0.05
    ) -> Dict[str, DownloadResult]:
        """
        下载日线数据

        Args:
            stock_list: 股票代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            delay: 下载间隔（秒），避免限流

        Returns:
            下载结果字典 {stock_code: DownloadResult}
        """
        if not XT_AVAILABLE:
            logger.error("[QmtDataManager] xtquant模块不可用")
            return {}

        results = {}
        logger.info(
            f"【下载日线数据】{start_date} 至 {end_date} | {len(stock_list)}只股票"
        )

        for i, stock_code in enumerate(stock_list, 1):
            try:
                logger.debug(f"[{i}/{len(stock_list)}] 下载 {stock_code} 日线数据")

                # 下载数据
                xtdata.download_history_data(
                    stock_code=stock_code,
                    period="1d",
                    start_time=start_date,
                    end_time=end_date,
                )

                # 验证下载
                data = xtdata.get_local_data(
                    field_list=["time", "open", "high", "low", "close", "amount"],
                    stock_list=[stock_code],
                    period="1d",
                    start_time=start_date,
                    end_time=end_date,
                )

                if data and stock_code in data and not data[stock_code].empty:
                    count = len(data[stock_code])
                    results[stock_code] = DownloadResult(
                        success=True,
                        stock_code=stock_code,
                        period="1d",
                        record_count=count,
                        message=f"成功 ({count}条)",
                    )
                else:
                    results[stock_code] = DownloadResult(
                        success=False,
                        stock_code=stock_code,
                        period="1d",
                        message="数据为空",
                    )

            except Exception as e:
                logger.error(f"[{i}/{len(stock_list)}] {stock_code} 下载失败: {e}")
                results[stock_code] = DownloadResult(
                    success=False, stock_code=stock_code, period="1d", error=str(e)
                )

            time.sleep(delay)

        success_count = sum(1 for r in results.values() if r.success)
        logger.info(f"日线数据下载完成: {success_count}/{len(stock_list)}")
        return results

    def download_minute_data(
        self, stock_list: List[str], start_date: str, end_date: str, delay: float = 0.05
    ) -> Dict[str, DownloadResult]:
        """
        下载1分钟线数据

        Args:
            stock_list: 股票代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            delay: 下载间隔（秒）

        Returns:
            下载结果字典
        """
        if not XT_AVAILABLE:
            logger.error("[QmtDataManager] xtquant模块不可用")
            return {}

        results = {}
        logger.info(
            f"【下载分钟线数据】{start_date} 至 {end_date} | {len(stock_list)}只股票"
        )

        for i, stock_code in enumerate(stock_list, 1):
            try:
                logger.debug(f"[{i}/{len(stock_list)}] 下载 {stock_code} 分钟线数据")

                xtdata.download_history_data(
                    stock_code=stock_code,
                    period="1m",
                    start_time=start_date,
                    end_time=end_date,
                )

                data = xtdata.get_local_data(
                    field_list=["time", "open", "high", "low", "close", "volume"],
                    stock_list=[stock_code],
                    period="1m",
                    start_time=start_date,
                    end_time=end_date,
                )

                if data and stock_code in data and not data[stock_code].empty:
                    count = len(data[stock_code])
                    results[stock_code] = DownloadResult(
                        success=True,
                        stock_code=stock_code,
                        period="1m",
                        record_count=count,
                        message=f"成功 ({count}条)",
                    )
                else:
                    results[stock_code] = DownloadResult(
                        success=False,
                        stock_code=stock_code,
                        period="1m",
                        message="数据为空",
                    )

            except Exception as e:
                logger.error(f"[{i}/{len(stock_list)}] {stock_code} 下载失败: {e}")
                results[stock_code] = DownloadResult(
                    success=False, stock_code=stock_code, period="1m", error=str(e)
                )

            time.sleep(delay)

        success_count = sum(1 for r in results.values() if r.success)
        logger.info(f"分钟线数据下载完成: {success_count}/{len(stock_list)}")
        return results

    def download_tick_data(
        self,
        stock_list: List[str],
        trade_date: str,
        use_vip: bool = True,
        check_existing: bool = True,
        delay: float = 0.2,
    ) -> Dict[str, DownloadResult]:
        """
        下载Tick数据（支持VIP服务）

        Args:
            stock_list: 股票代码列表
            trade_date: 交易日期 (YYYYMMDD)
            use_vip: 是否使用VIP服务
            check_existing: 是否检查已有数据
            delay: 下载间隔（秒）

        Returns:
            下载结果字典
        """
        if not XT_AVAILABLE:
            logger.error("[QmtDataManager] xtquant模块不可用")
            return {}

        # 如果需要VIP服务，确保服务已启动
        if use_vip and self.use_vip:
            if not self._ensure_vip_connection():
                # CTO修复：VIP不可用直接熔断，禁止降级
                raise RuntimeError(
                    "[QmtDataManager] VIP服务不可用，直接熔断！禁止降级到普通下载"
                )

        results = {}
        logger.info(
            f"【下载Tick数据】{trade_date} | {len(stock_list)}只股票 | VIP: {use_vip}"
        )

        # 初始化QMTRouter - 接入熔断机制
        router = QMTRouter()

        for i, stock_code in enumerate(stock_list, 1):
            try:
                # 检查是否已有数据
                if check_existing:
                    existing = xtdata.get_local_data(
                        field_list=["time"],
                        stock_list=[stock_code],
                        period="tick",
                        start_time=trade_date,
                        end_time=trade_date,
                    )

                    if (
                        existing
                        and stock_code in existing
                        and len(existing[stock_code]) > 100
                    ):
                        tick_count = len(existing[stock_code])
                        results[stock_code] = DownloadResult(
                            success=True,
                            stock_code=stock_code,
                            period="tick",
                            record_count=tick_count,
                            message=f"已存在 ({tick_count}条)",
                        )
                        logger.debug(
                            f"[{i}/{len(stock_list)}] {stock_code} 已存在，跳过"
                        )
                        continue

                # 下载Tick数据
                xtdata.download_history_data(
                    stock_code=stock_code,
                    period="tick",
                    start_time=trade_date,
                    end_time=trade_date,
                )

                # CTO修复：阻塞等待数据落盘 (异步转同步)
                wait_count = 0
                max_wait = 30  # 最多等30秒
                while wait_count < max_wait:
                    time.sleep(1)
                    wait_count += 1

                    # 检查数据是否已落盘
                    check_data = xtdata.get_local_data(
                        field_list=["time"],
                        stock_list=[stock_code],
                        period="tick",
                        start_time=trade_date,
                        end_time=trade_date,
                    )

                    if check_data and stock_code in check_data:
                        tick_df = check_data[stock_code]
                        if tick_df is not None and len(tick_df) > 0:
                            tick_count = len(tick_df)
                            results[stock_code] = DownloadResult(
                                success=True,
                                stock_code=stock_code,
                                period="tick",
                                record_count=tick_count,
                                message=f"成功 ({tick_count}条, 等待{wait_count}秒)",
                            )
                            logger.info(
                                f"[{i}/{len(stock_list)}] {stock_code} ✓ {tick_count}条 (等待{wait_count}秒)"
                            )
                            break
                else:
                    # 超时
                    results[stock_code] = DownloadResult(
                        success=False,
                        stock_code=stock_code,
                        period="tick",
                        message=f"下载超时 ({max_wait}秒)",
                    )
                    logger.warning(f"[{i}/{len(stock_list)}] {stock_code} 下载超时")
                    continue

            except Exception as e:
                logger.error(f"[{i}/{len(stock_list)}] {stock_code} 下载失败: {e}")
                results[stock_code] = DownloadResult(
                    success=False, stock_code=stock_code, period="tick", error=str(e)
                )

            time.sleep(delay)

        success_count = sum(1 for r in results.values() if r.success)
        circuit_breaker_count = sum(
            1 for r in results.values() if r.error and "熔断" in r.error
        )
        logger.info(
            f"Tick数据下载完成: {success_count}/{len(stock_list)} | 熔断: {circuit_breaker_count}"
        )
        return results

    def verify_data_integrity(
        self, stock_list: List[str], trade_date: str, check_periods: List[str] = None
    ) -> Dict[str, DataIntegrityReport]:
        """
        验证数据完整性

        Args:
            stock_list: 股票代码列表
            trade_date: 交易日期
            check_periods: 要检查的周期列表 ['1d', '1m', 'tick']

        Returns:
            完整性报告字典 {stock_code: DataIntegrityReport}
        """
        if not XT_AVAILABLE:
            logger.error("[QmtDataManager] xtquant模块不可用")
            return {}

        check_periods = check_periods or ["1d", "1m", "tick"]
        reports = {}

        logger.info(f"【数据完整性验证】{trade_date} | {len(stock_list)}只股票")

        for stock_code in stock_list:
            report = DataIntegrityReport(stock_code=stock_code, trade_date=trade_date)

            try:
                # 检查日线数据
                if "1d" in check_periods:
                    daily = xtdata.get_local_data(
                        field_list=["time"],
                        stock_list=[stock_code],
                        period="1d",
                        start_time=trade_date,
                        end_time=trade_date,
                    )
                    if daily and stock_code in daily and not daily[stock_code].empty:
                        report.has_daily = True
                        report.daily_count = len(daily[stock_code])
                    else:
                        report.missing_periods.append("1d")

                # 检查分钟线数据
                if "1m" in check_periods:
                    minute = xtdata.get_local_data(
                        field_list=["time"],
                        stock_list=[stock_code],
                        period="1m",
                        start_time=trade_date,
                        end_time=trade_date,
                    )
                    if minute and stock_code in minute and not minute[stock_code].empty:
                        report.has_minute = True
                        report.minute_count = len(minute[stock_code])
                    else:
                        report.missing_periods.append("1m")

                # 检查Tick数据
                if "tick" in check_periods:
                    tick = xtdata.get_local_data(
                        field_list=["time"],
                        stock_list=[stock_code],
                        period="tick",
                        start_time=trade_date,
                        end_time=trade_date,
                    )
                    if tick and stock_code in tick and len(tick[stock_code]) > 100:
                        report.has_tick = True
                        report.tick_count = len(tick[stock_code])
                    else:
                        report.missing_periods.append("tick")

                reports[stock_code] = report

            except Exception as e:
                logger.error(f"验证 {stock_code} 数据完整性失败: {e}")
                report.missing_periods = check_periods
                reports[stock_code] = report

        # 统计
        complete_count = sum(1 for r in reports.values() if r.is_complete)
        logger.info(f"数据完整性验证完成: 完整 {complete_count}/{len(stock_list)}")
        return reports

    def supplement_missing_data(
        self, missing_list: List[Tuple[str, str]], use_vip: bool = True
    ) -> Dict[str, DownloadResult]:
        """
        补充下载缺失的数据

        Args:
            missing_list: 缺失数据列表 [(stock_code, period), ...]
            use_vip: 是否使用VIP服务（对Tick数据有效）

        Returns:
            下载结果字典
        """
        if not missing_list:
            logger.info("【补充下载】没有缺失的数据")
            return {}

        logger.info(f"【补充下载】共 {len(missing_list)} 项缺失数据")

        # 按周期分组
        by_period: Dict[str, List[str]] = {}
        for stock_code, period in missing_list:
            if period not in by_period:
                by_period[period] = []
            by_period[period].append(stock_code)

        all_results = {}

        # 补充日线数据
        if "1d" in by_period:
            results = self.download_daily_data(
                by_period["1d"],
                (datetime.now() - timedelta(days=10)).strftime("%Y%m%d"),
                datetime.now().strftime("%Y%m%d"),
            )
            all_results.update(results)

        # 补充分钟线数据
        if "1m" in by_period:
            today = datetime.now().strftime("%Y%m%d")
            results = self.download_minute_data(by_period["1m"], today, today)
            all_results.update(results)

        # 补充Tick数据
        if "tick" in by_period:
            today = datetime.now().strftime("%Y%m%d")
            results = self.download_tick_data(
                by_period["tick"], today, use_vip=use_vip, check_existing=False
            )
            all_results.update(results)

        success_count = sum(1 for r in all_results.values() if r.success)
        logger.info(f"补充下载完成: {success_count}/{len(missing_list)}")
        return all_results

    def batch_download(
        self,
        stock_list: List[str],
        trade_date: str,
        periods: List[str] = None,
        use_vip: bool = True,
    ) -> Dict[str, Dict[str, DownloadResult]]:
        """
        批量下载多周期数据

        Args:
            stock_list: 股票代码列表
            trade_date: 交易日期
            periods: 要下载的周期列表 ['1d', '1m', 'tick']
            use_vip: 是否使用VIP服务

        Returns:
            按周期分组的下载结果 {period: {stock_code: DownloadResult}}
        """
        periods = periods or ["1d", "1m", "tick"]
        results = {}

        logger.info(
            f"【批量下载】{trade_date} | 周期: {periods} | {len(stock_list)}只股票"
        )

        if "1d" in periods:
            start_date = (
                datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=10)
            ).strftime("%Y%m%d")
            results["1d"] = self.download_daily_data(stock_list, start_date, trade_date)

        if "1m" in periods:
            results["1m"] = self.download_minute_data(
                stock_list, trade_date, trade_date
            )

        if "tick" in periods:
            results["tick"] = self.download_tick_data(
                stock_list, trade_date, use_vip=use_vip
            )

        return results

    def get_download_summary(
        self, results: Dict[str, DownloadResult]
    ) -> Dict[str, Any]:
        """
        获取下载结果汇总

        Args:
            results: 下载结果字典

        Returns:
            汇总统计信息
        """
        total = len(results)
        success = sum(1 for r in results.values() if r.success)
        failed = total - success

        total_records = sum(r.record_count for r in results.values())

        failed_stocks = [r.stock_code for r in results.values() if not r.success]

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": success / total if total > 0 else 0,
            "total_records": total_records,
            "failed_stocks": failed_stocks,
        }


def init_qmt_data_dir() -> None:
    """
    初始化 QMT 数据目录

    从 Config.qmt_data_dir 读取 QMT 数据目录路径，
    并设置为 xtdata 的默认数据目录

    Raises:
        RuntimeError: 如果 Config.qmt_data_dir 未配置
    """
    try:
        import config.config_system as config
        from xtquant import xtdata

        # 🔥 关键修复：通过实例调用get()方法，而不是通过类
        config_instance = config.Config()
        qmt_dir = config_instance.get("qmt_data_dir")

        if not qmt_dir:
            raise RuntimeError(
                "Config.qmt_data_dir is empty, please set it in config/config.json"
            )

        # 设置 QMT 数据目录
        # 注意：根据 xtquant 版本，可能使用 data_dir 或 set_data_dir
        if hasattr(xtdata, "data_dir"):
            xtdata.data_dir = qmt_dir
        elif hasattr(xtdata, "set_data_dir"):
            xtdata.set_data_dir(qmt_dir)
        else:
            print(
                f"⚠️ [QMT] 无法设置数据目录，xtdata 未提供 data_dir 或 set_data_dir 方法"
            )
            print(f"⚠️ [QMT] 当前数据目录可能指向默认安装目录，而非 {qmt_dir}")

        print(f"✅ [QMT] 数据目录已设置: {qmt_dir}")

    except ImportError as e:
        print(f"❌ [QMT] 导入模块失败: {e}")
    except Exception as e:
        print(f"❌ [QMT] 初始化数据目录失败: {e}")
        import traceback

        traceback.print_exc()
        raise


class QMTManager:
    """QMT 接口管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化 QMT 管理器

        Args:
            config_path: 配置文件路径，默认为 config/config.json
        """
        self.config = self._load_config(config_path)
        self.data_connected = False
        self.trader_connected = False
        self.trader_client = None

        # 🔥 关键修复：暴露 xtdata 模块给外部调用
        if XT_AVAILABLE:
            self.xtdata = xtdata
        else:
            self.xtdata = None

        self._init_data_interface()
        self._init_trader_interface()
        self._init_subscription()

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置文件 - 优先使用主配置文件"""
        if config_path is None:
            # 使用主配置文件
            config_path = Path(__file__).parent.parent.parent / "config" / "config.json"

        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # 如果主配置文件不存在，返回默认配置
            return {
                "qmt_data": {"enabled": True, "ip": "127.0.0.1", "port": 58610},
                "qmt_trader": {"enabled": False},
            }

    def _init_data_interface(self):
        """初始化数据接口"""
        if not XT_AVAILABLE:
            print("❌ xtquant 模块不可用")
            return

        data_config = self.config.get("qmt_data", {})
        if not data_config.get("enabled", False):
            print("⚠️  QMT 数据接口未启用")
            return

        try:
            # 测试连接
            stock_list = xtdata.get_stock_list_in_sector("沪深A股")
            if stock_list is not None:
                self.data_connected = True
                print(f"✅ QMT 数据接口连接成功，获取到 {len(stock_list)} 只股票")
            else:
                print("⚠️  QMT 数据接口连接异常，未获取到股票列表")
        except Exception as e:
            print(f"❌ QMT 数据接口连接失败: {e}")

    def _init_trader_interface(self):
        """初始化交易接口"""
        if not XT_AVAILABLE:
            return

        trader_config = self.config.get("qmt_trader", {})
        if not trader_config.get("enabled", False):
            print("⚠️  QMT 交易接口未启用")
            return

        try:
            # 创建交易回调类
            class DefaultCallback(xttrader.XtQuantTraderCallback):
                def on_connected(self):
                    print("✅ QMT 交易接口连接成功")

                def on_disconnected(self):
                    print("❌ QMT 交易接口连接断开")

            # 修复：将回调保存为实例属性，防止被 GC 回收
            self._trader_callback = DefaultCallback()

            # 创建交易客户端
            self.trader_client = xttrader.XtQuantTrader(
                self._trader_callback, trader_config.get("session_id", 123456)
            )

            # 连接交易接口
            result = self.trader_client.connect()
            if result == 0:
                self.trader_connected = True
                print("✅ QMT 交易接口初始化成功")
            else:
                print(f"❌ QMT 交易接口连接失败，错误码: {result}")

        except Exception as e:
            print(f"❌ QMT 交易接口初始化失败: {e}")

    def is_available(self) -> bool:
        """检查 QMT 接口是否可用"""
        return XT_AVAILABLE and self.data_connected

    def is_trader_available(self) -> bool:
        """检查 QMT 交易接口是否可用"""
        return XT_AVAILABLE and self.trader_connected

    def get_stock_list(self) -> Optional[List[str]]:
        """获取股票列表"""
        if not self.is_available():
            return None

        try:
            return xtdata.get_stock_list_in_sector("沪深A股")
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            return None

    def get_full_tick(self, stock_list: List[str]) -> Optional[Dict[str, Any]]:
        """获取tick数据"""
        if not self.is_available():
            return None

        try:
            return xtdata.get_full_tick(stock_list)
        except Exception as e:
            print(f"❌ 获取tick数据失败: {e}")
            return None

    def download_history_data(
        self,
        stock_code: str,
        period: str = "1d",
        start_time: str = None,
        end_time: str = None,
        async_mode: bool = False,
    ) -> bool:
        """
        下载历史数据

        Args:
            stock_code: 股票代码
            period: 周期（1d, 1h, 1m 等）
            start_time: 开始时间（格式：YYYYMMDD）
            end_time: 结束时间（格式：YYYYMMDD）
            async_mode: 是否异步执行（避免阻塞主线程）

        Returns:
            是否成功
        """
        if not self.is_available():
            return False

        def _download():
            try:
                # 标准化股票代码
                normalized_code = self.normalize_code(stock_code)
                xtdata.download_history_data(
                    normalized_code, period, start_time, end_time
                )
                return True
            except Exception as e:
                print(f"❌ 下载历史数据失败: {e}")
                return False

        if async_mode:
            # 异步执行，避免阻塞
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_download)
                return future.result(timeout=300)  # 5分钟超时
        else:
            return _download()

    def get_local_data(
        self,
        stock_list: List[str],
        field_list: List[str],
        period: str = "1d",
        start_time: str = None,
        end_time: str = None,
    ) -> Optional[Dict[str, Any]]:
        """
        获取本地数据

        Args:
            stock_list: 股票代码列表
            field_list: 字段列表（time, open, high, low, close 等）
            period: 周期
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            数据字典
        """
        if not self.is_available():
            return None

        try:
            return xtdata.get_local_data(
                field_list, stock_list, period, start_time, end_time
            )
        except Exception as e:
            print(f"❌ 获取本地数据失败: {e}")
            return None

    def query_stock_asset(self, account_id: str = None) -> Optional[Any]:
        """
        查询账户资产

        Args:
            account_id: 账户ID

        Returns:
            账户资产信息
        """
        if not self.is_trader_available():
            return None

        try:
            if account_id is None:
                account_id = self.config.get("qmt_trader", {}).get("account_id")
            return self.trader_client.query_stock_asset(account_id)
        except Exception as e:
            print(f"❌ 查询账户资产失败: {e}")
            return None

    def query_stock_position(self, account_id: str = None) -> Optional[Any]:
        """
        查询持仓

        Args:
            account_id: 账户ID

        Returns:
            持仓信息
        """
        if not self.is_trader_available():
            return None

        try:
            if account_id is None:
                account_id = self.config.get("qmt_trader", {}).get("account_id")
            return self.trader_client.query_stock_position(account_id)
        except Exception as e:
            print(f"❌ 查询持仓失败: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """获取 QMT 状态"""
        return {
            "xt_available": XT_AVAILABLE,
            "data_connected": self.data_connected,
            "trader_connected": self.trader_connected,
            "config_loaded": bool(self.config),
        }

    def _init_subscription(self):
        """初始化数据订阅"""
        if not self.is_available():
            return

        subscribe_config = self.config.get("data_subscribe", {})
        if not subscribe_config.get("enabled", False):
            return

        try:
            symbols = subscribe_config.get("symbols", [])
            if symbols:
                # 转换股票代码格式
                formatted_symbols = [self.normalize_code(s) for s in symbols]
                xtdata.subscribe_quote(formatted_symbols)
                print(f"✅ 已订阅 {len(formatted_symbols)} 只股票的行情数据")
        except Exception as e:
            print(f"⚠️  数据订阅失败: {e}")

    @staticmethod
    def normalize_code(code: str) -> str:
        """
        标准化股票代码格式为 QMT 格式（######.SH / ######.SZ）

        Args:
            code: 股票代码，支持多种格式（600519, sh600519, 600519.SH 等）

        Returns:
            QMT 标准格式的股票代码

        Examples:
            >>> QMTManager.normalize_code('600519')
            '600519.SH'
            >>> QMTManager.normalize_code('sh600519')
            '600519.SH'
            >>> QMTManager.normalize_code('300750')
            '300750.SZ'
        """
        if not code:
            return code

        # 移除可能的分隔符
        code = code.strip().replace(".", "")

        # 如果已经包含交易所后缀，直接返回
        if code.endswith(".SH") or code.endswith(".SZ"):
            return code

        # 提取6位数字代码
        if code.startswith("sh"):
            stock_code = code[2:]
            return f"{stock_code}.SH"
        elif code.startswith("sz"):
            stock_code = code[2:]
            return f"{stock_code}.SZ"
        elif code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith(("0", "3")):
            return f"{code}.SZ"
        else:
            # 默认为主板
            return f"{code}.SH"


# 全局 QMT 管理器实例
_qmt_manager: Optional[QMTManager] = None


def get_qmt_manager() -> QMTManager:
    """
    获取全局 QMT 管理器实例

    Returns:
        QMTManager: QMT 管理器实例
    """
    global _qmt_manager
    if _qmt_manager is None:
        # 🔥 关键修复：第一件事就是初始化数据目录
        init_qmt_data_dir()
        _qmt_manager = QMTManager()
    return _qmt_manager


if __name__ == "__main__":
    # 测试 QMT 管理器
    print("=" * 60)
    print("🧪 QMT 管理器测试")
    print("=" * 60)

    manager = get_qmt_manager()
    status = manager.get_status()

    print(f"\n📊 QMT 状态:")
    print(f"  xtquant 可用: {'✅' if status['xt_available'] else '❌'}")
    print(f"  数据接口连接: {'✅' if status['data_connected'] else '❌'}")
    print(f"  交易接口连接: {'✅' if status['trader_connected'] else '❌'}")
    print(f"  配置加载: {'✅' if status['config_loaded'] else '❌'}")

    if manager.is_available():
        print(f"\n✅ QMT 管理器初始化成功")

        # 测试获取股票列表
        stock_list = manager.get_stock_list()
        if stock_list:
            print(f"📈 获取到 {len(stock_list)} 只股票")

        # 测试获取tick数据
        if stock_list and len(stock_list) > 0:
            tick_data = manager.get_full_tick([stock_list[0]])
            if tick_data:
                print(f"⚡ 成功获取tick数据")
    else:
        print(f"\n❌ QMT 管理器初始化失败")

    print("=" * 60)
