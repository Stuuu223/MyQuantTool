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
import threading
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

    # CTO修复：删除硬编码VIP Token，强制从环境变量读取
    # 请在.env文件中配置: QMT_VIP_TOKEN=your_token_here

    # ============================================================
    # 【并发安全重构】CTO Phase 6.3 - 2026-03-01
    # ============================================================
    # 问题：原布尔锁_vip_global_lock=False不是线程安全的
    # 方案：使用threading.Lock()保护临界区 + threading.Event()实现初始化通知
    # ============================================================
    
    # 类级别单例状态
    _vip_global_initialized: bool = False
    _vip_global_port: Optional[Tuple[str, int]] = None
    
    # 线程安全同步原语（类级别共享）
    _vip_lock = threading.Lock()  # 保护临界区
    _vip_init_event = threading.Event()  # 初始化完成事件通知

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
        # 【CTO架构修复】防呆机制：禁止直接实例化，必须通过get_qmt_manager()获取单例
        global _qmt_manager
        if _qmt_manager is not None:
            # 允许第一次初始化，后续实例化直接警告
            import warnings
            warnings.warn(
                "QmtDataManager为全局单例，请通过get_qmt_manager()获取实例，"
                "直接实例化可能导致状态不一致",
                RuntimeWarning
            )
        
        self.vip_token = vip_token or self._load_vip_token()
        # CTO修复：优先从环境变量读取，删除硬编码
        env_data_dir = os.getenv("QMT_PATH", "")
        self.data_dir = Path(data_dir or env_data_dir or self._detect_qmt_path())
        self.use_vip = use_vip and XT_AVAILABLE
        self.port_range = port_range
        self.listen_port: Optional[Tuple[str, int]] = None
        # 【CTO架构修复】删除实例级_vip_initialized，统一使用类级别状态
        # VIP初始化状态只存在于 QmtDataManager._vip_global_initialized

        logger.info(
            f"[QmtDataManager] 初始化完成 | VIP: {use_vip} | 数据目录: {self.data_dir}"
        )

    def _detect_qmt_path(self) -> str:
        """
        【Boss钦定：极简智能路径解析】
        不穷举盘符！只看环境变量，如果没有或无效，直接在项目内建沙盒！
        """
        # 首先尝试从环境变量获取
        env_path = os.getenv("QMT_PATH", "")
        if env_path and os.path.exists(env_path):
            logger.info(f"[QmtDataManager] 从环境变量获取到QMT路径: {env_path}")
            return env_path
        
        # 如果环境变量配了但不存在，记录警告，降级到沙盒
        if env_path:
            logger.warning(f"⚠️ 环境变量 QMT_PATH [{env_path}] 不存在，系统将使用内部沙盒。")
        
        # 极简智能降级：在当前运行的MyQuantTool根目录下创建沙盒
        # 这样无论代码拷到哪个盘，永远不会报错！
        sandbox_dir = Path.cwd() / ".qmt_userdata_sandbox"
        
        # Python智能创建，存在则忽略
        try:
            sandbox_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[QmtDataManager] 使用项目内沙盒路径: {sandbox_dir}")
        except Exception as e:
            logger.error(f"❌ 无法创建沙盒目录: {e}")
            # 最后一道防线：使用temp目录
            import tempfile
            sandbox_dir = Path(tempfile.gettempdir()) / "myquanttool_qmt_sandbox"
            sandbox_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"[QmtDataManager] 降级到临时目录: {sandbox_dir}")
        
        return str(sandbox_dir)

    def _load_vip_token(self) -> str:
        """从配置文件加载VIP Token - 严格使用环境变量"""
        # 从环境变量读取（唯一正确的方式）
        env_token = os.getenv('QMT_VIP_TOKEN')
        if env_token and env_token.strip():
            logger.info("[QmtDataManager] 从环境变量读取VIP Token")
            return env_token.strip()
        
        # CTO修复：如果环境变量未设置，直接报错！
        logger.error("❌ 致命错误：未在 .env 文件中配置 QMT_VIP_TOKEN！")
        logger.error("请在项目根目录创建.env文件，并写入: QMT_VIP_TOKEN=您的VIP_Token")
        raise ValueError("QMT_VIP_TOKEN未配置，请检查.env文件")

    def start_vip_service(self) -> Optional[Tuple[str, int]]:
        """
        启动VIP行情服务 (CTO Phase 6.3 并发安全重构版)

        【并发安全设计】
        - 使用 threading.Lock() 保护临界区
        - 使用 threading.Event() 实现初始化完成通知
        - 等待线程使用 Event.wait(timeout=30) 实现超时
        - 避免忙等待，提高CPU效率

        Returns:
            监听地址和端口元组，启动失败返回None
        """
        # ============================================================
        # 快速路径：如果已初始化完成，直接返回
        # ============================================================
        if QmtDataManager._vip_global_initialized and QmtDataManager._vip_global_port:
            logger.info("[QmtDataManager] VIP服务已在运行，复用现有连接")
            self.listen_port = QmtDataManager._vip_global_port
            return self.listen_port

        # ============================================================
        # 加锁进入临界区 - 只有一个线程能执行初始化
        # ============================================================
        acquired = QmtDataManager._vip_lock.acquire(blocking=False)
        
        if not acquired:
            # 当前锁被其他线程持有，说明正在初始化
            logger.info("[QmtDataManager] VIP服务正在启动中，等待初始化完成...")
            
            # 使用Event等待初始化完成，最多等待30秒
            # Event.wait() 是阻塞操作，不消耗CPU（比忙等待更高效）
            init_completed = QmtDataManager._vip_init_event.wait(timeout=30)
            
            if init_completed and QmtDataManager._vip_global_initialized:
                # 初始化成功，复用结果
                self.listen_port = QmtDataManager._vip_global_port
                logger.info(f"[QmtDataManager] VIP服务初始化完成，复用连接: {self.listen_port}")
                return self.listen_port
            else:
                # 等待超时或初始化失败
                logger.error("[QmtDataManager] 等待VIP服务初始化超时(30秒)")
                return None

        # ============================================================
        # 当前线程获取到锁，执行初始化
        # ============================================================
        try:
            # P1级修复：每次开始初始化前，clear() Event，确保重新初始化时等待线程能正确等待
            QmtDataManager._vip_init_event.clear()
            
            # 双重检查：防止在等待锁期间其他线程已完成初始化
            if QmtDataManager._vip_global_initialized:
                self.listen_port = QmtDataManager._vip_global_port
                QmtDataManager._vip_init_event.set()  # 通知等待线程
                return self.listen_port

            # 检查XT模块可用性
            if not XT_AVAILABLE or not self.use_vip:
                logger.warning("[QmtDataManager] VIP服务不可用或已禁用")
                return None

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
            # 【CTO架构修复】使用官方推荐模式：先关闭自动监听，再手动指定端口范围
            xtdc.init(False)  # False = 不自动监听
            listen_result = xtdc.listen(port=self.port_range)
            
            # 解析监听结果
            if isinstance(listen_result, tuple) and len(listen_result) == 2:
                ip, port = listen_result
                self.listen_port = (ip, int(port))
            else:
                # 兼容旧版本返回单个port的情况
                self.listen_port = ("127.0.0.1", int(listen_result))
            
            # 【CTO架构修复】不再设置实例级_vip_initialized，只使用类级状态

            # ============================================================
            # 设置全局单例状态 + 通知等待线程
            # ============================================================
            QmtDataManager._vip_global_initialized = True
            QmtDataManager._vip_global_port = self.listen_port
            
            # 通知所有等待的线程：初始化完成！
            QmtDataManager._vip_init_event.set()

            logger.info(f"🚀 VIP行情服务已启动，监听端口: {port}")
            logger.info("=" * 60)

            return self.listen_port

        except Exception as e:
            # 【CTO架构修复】删除58609幽灵端口处理
            # 官方文档说明：端口冲突时应使用自定义端口范围重新listen，而非回退到默认端口
            # 任何启动失败都应明确返回None，由上层决定是否熔断
            
            logger.warning(f"⚠️ VIP L2服务启动失败: {e}")
            logger.warning("VIP服务不可用，download_tick_data将抛出RuntimeError熔断！")
            
            # 重置全局状态
            QmtDataManager._vip_global_initialized = False
            QmtDataManager._vip_global_port = None
            
            # 通知等待线程：初始化完成（虽然失败，但避免死锁）
            QmtDataManager._vip_init_event.set()
            
            return None  # 明确返回None，由上层处理
            
        finally:
            # 确保锁一定被释放
            QmtDataManager._vip_lock.release()

    def stop_vip_service(self) -> bool:
        """
        停止VIP行情服务（逻辑层标记重置）
        
        注意：xtdatacenter没有公开stop API，端口真正释放需依赖Python进程退出
        或手工杀掉后台进程。这里只做逻辑层重置，确保下次start_vip_service()会重新初始化。
        
        Returns:
            是否成功停止
        """
        # 【CTO架构修复】重置类级状态，确保下次start_vip_service()重新初始化
        QmtDataManager._vip_global_initialized = False
        QmtDataManager._vip_global_port = None
        QmtDataManager._vip_init_event.clear()
        self.listen_port = None
        
        logger.info("[QmtDataManager] VIP服务标记已重置（xtdc进程需依赖Python进程退出释放端口）")
        return True

    # 【CTO架构修复】_ensure_vip_connection()已删除
    # 原因：此方法是僵尸方法，从未被调用
    # 内部逻辑错误：xtdata.connect()会切换到实时Level-2服务器
    # 导致download_history_data请求发错地方，返回ErrorID: 200005
    # 正确做法：只用start_vip_service()启动本地代理，不需要xtdata.connect()

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

        # 如果需要VIP服务，确保本地代理已启动
        # CTO架构修复：只需要start_vip_service()，不需要xtdata.connect()
        # xtdata.connect()会把连接切换到实时Level-2服务器（55310端口）
        # 导致download_history_data请求发到实时服务器而非历史数据服务器
        if use_vip and self.use_vip:
            # 【CTO架构修复】使用类级别状态判断，而非实例变量
            if not QmtDataManager._vip_global_initialized:
                result = self.start_vip_service()
                if not result:
                    raise RuntimeError(
                        "[QmtDataManager] VIP本地代理启动失败"
                    )

        results = {}
        logger.info(
            f"【下载Tick数据】{trade_date} | {len(stock_list)}只股票 | VIP: {use_vip}"
        )

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
                        and len(existing[stock_code]) > 0
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





# 全局 QMT 管理器实例
_qmt_manager: Optional['QmtDataManager'] = None


def get_qmt_manager() -> 'QmtDataManager':
    """
    获取全局 QMT 管理器实例（CTO修复：返回正确的QmtDataManager）

    Returns:
        QmtDataManager: QMT 数据管理器实例
    """
    global _qmt_manager
    if _qmt_manager is None:
        _qmt_manager = QmtDataManager()
    return _qmt_manager



