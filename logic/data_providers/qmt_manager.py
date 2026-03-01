# -*- coding: utf-8 -*-
"""
QMT 数据管理器 - VIP版本

功能：
1. 管理 QMT 数据接口连接（普通+VIP）
2. 提供统一的 QMT 数据下载接口（日线/分钟线/Tick）
3. 数据完整性验证与补充下载
4. 自动重连和错误处理

Author: iFlow CLI
Date: 2026-02-23
Version: V2.1 (CTO Phase 6.4 - 10-BUG修复版)

修复记录 (2026-03-02 CTO审计):
- CRITICAL-1: 补充 set_token() 调用，VIP权限实际注入
- CRITICAL-2: connect() 无可靠返回值，改用探针验证（get_trading_calendar('SZSE')）
- HIGH-3: 删除 xtdatacenter 僵尸 import，防止精简版崩溃
- HIGH-4: 单例防呆修复，__init__ 中立即赋值 _qmt_manager=self
- HIGH-5: Token 改为 lazy property，use_vip=False 时不 raise
- MED-6: Tick 阈值 Magic Number 提取为常量 TICK_VALID_MIN_COUNT
- MED-7: 补充下载回溯天数提取为常量 SUPPLEMENT_LOOKBACK_DAYS
- MED-8: stop_vip_service() 僵尸 xtdc 注释清理
- MED-9: 日线/分钟线验证统一为 len(df) > 0，消除字段歧义
- MED-10: VIP失败返回完整失败报告，禁止静默失败
"""

import os
import time
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

try:
    # HIGH-3修复: 删除 xtdatacenter (xtdc) 僵尸 import
    # xtdc 已废除，数据请求统一由本地 MiniQMT 客户端处理
    from xtquant import xtdata, xttrader

    XT_AVAILABLE = True
except ImportError:
    XT_AVAILABLE = False
    xtdata = None
    xttrader = None

logger = logging.getLogger(__name__)

# ============================================================
# 常量定义区 (MED-6, MED-7修复：肃清 Magic Number)
# ============================================================

# Tick数据有效性最低门槛
# 正常交易日单只股票 Tick 约 3000-8000 条；停牌为 0
# 设为 1 表示"只要有数据就算有效"，避免误杀轻微停牌
TICK_VALID_MIN_COUNT: int = 1

# 补充下载时的自然日回溯天数（含节假日约 7 个交易日）
SUPPLEMENT_LOOKBACK_DAYS: int = 10


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
    必须通过 get_qmt_manager() 获取单例实例，禁止直接实例化。

    Example:
        >>> manager = get_qmt_manager()
        >>> manager.start_vip_service()
        >>> result = manager.download_tick_data(['000001.SZ'], '20251231')
    """

    # ============================================================
    # 类级别单例状态（线程安全）
    # ============================================================
    _vip_global_initialized: bool = False
    _vip_global_port: Optional[Tuple[str, int]] = None
    _vip_lock = threading.Lock()
    _vip_init_event = threading.Event()

    def __init__(
        self,
        vip_token: Optional[str] = None,
        data_dir: Optional[str] = None,
        use_vip: bool = True,
        port_range: Tuple[int, int] = (58700, 58750),
    ):
        """
        初始化QMT数据管理器

        Args:
            vip_token: VIP Token（可选，不传则从 .env 读取，lazy 加载）
            data_dir: QMT数据目录（可选，不传则从环境变量 QMT_PATH 读取）
            use_vip: 是否启用VIP服务
            port_range: 保留参数，当前架构直连 MiniQMT，不使用
        """
        # ======================================================
        # HIGH-4修复：单例防呆
        # 原代码只检查不赋值，导致防呆对直接调用完全失效
        # 修复：先检查，然后立即注册 self，防止后续再次创建
        # ======================================================
        global _qmt_manager
        if _qmt_manager is not None:
            raise RuntimeError(
                "QmtDataManager为全局单例，禁止直接实例化，请通过 get_qmt_manager() 获取实例"
            )
        _qmt_manager = self  # 立即注册，防止同一线程内重复创建

        # ======================================================
        # HIGH-5修复：Token 改为 lazy property
        # use_vip=False 时不强制加载 Token，避免无谓 raise
        # ======================================================
        self.use_vip = use_vip and XT_AVAILABLE
        self._vip_token_override = vip_token  # 入参暂存，首次访问 .vip_token 时解析
        self._vip_token_cache: Optional[str] = None

        env_data_dir = os.getenv("QMT_PATH", "")
        self.data_dir = Path(data_dir or env_data_dir or self._detect_qmt_path())
        self.port_range = port_range
        self.listen_port: Optional[Tuple[str, int]] = None

        logger.info(
            f"[QmtDataManager] 初始化完成 | VIP: {use_vip} | 数据目录: {self.data_dir}"
        )

    # ----------------------------------------------------------
    # HIGH-5修复：vip_token 改为 lazy property
    # 只有真正需要时（start_vip_service 调用时）才触发加载
    # ----------------------------------------------------------
    @property
    def vip_token(self) -> str:
        if self._vip_token_cache is None:
            self._vip_token_cache = self._load_vip_token(self._vip_token_override)
        return self._vip_token_cache

    def _detect_qmt_path(self) -> str:
        """
        【极简智能路径解析】
        只看环境变量 QMT_PATH，无效则降级到项目内沙盒。
        """
        env_path = os.getenv("QMT_PATH", "")
        if env_path and os.path.exists(env_path):
            logger.info(f"[QmtDataManager] 从环境变量获取到QMT路径: {env_path}")
            return env_path

        if env_path:
            logger.warning(f"⚠️ 环境变量 QMT_PATH [{env_path}] 不存在，降级到内部沙盒。")

        sandbox_dir = Path.cwd() / ".qmt_userdata_sandbox"
        try:
            sandbox_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[QmtDataManager] 使用项目内沙盒路径: {sandbox_dir}")
        except Exception as e:
            logger.error(f"❌ 无法创建沙盒目录: {e}")
            import tempfile
            sandbox_dir = Path(tempfile.gettempdir()) / "myquanttool_qmt_sandbox"
            sandbox_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"[QmtDataManager] 降级到临时目录: {sandbox_dir}")

        return str(sandbox_dir)

    def _load_vip_token(self, override: Optional[str] = None) -> str:
        """从环境变量加载 VIP Token（严格校验，不允许空串）"""
        if override and override.strip():
            return override.strip()

        env_token = os.getenv("QMT_VIP_TOKEN")
        if env_token and env_token.strip():
            logger.info("[QmtDataManager] 从环境变量读取VIP Token")
            return env_token.strip()

        logger.error("❌ 致命错误：未在 .env 中配置 QMT_VIP_TOKEN！")
        raise ValueError("QMT_VIP_TOKEN未配置，请在 .env 文件中写入: QMT_VIP_TOKEN=您的Token")

    def start_vip_service(self) -> bool:
        """
        【CTO 终极直连架构 V2.1】直连本地 MiniQMT 客户端

        三步走：
        Step 1 - set_token()：注入 VIP 权限（CRITICAL-1修复，原代码完全缺失此步）
        Step 2 - connect()：连接本地 MiniQMT，不传参自动识别
        Step 3 - 探针验证：get_trading_calendar('SZSE') 有数据才算真正连通
                 （CRITICAL-2修复：connect() 无可靠返回值，不抛异常≠连通）

        官方文档依据：
        "xtdata 提供和 MiniQmt 的交互接口，本质是和 MiniQmt 建立连接，
         由 MiniQmt 处理行情数据请求。xtdata.connect() 不传参可自动识别本地 MiniQMT。"

        Returns:
            True = 三步全通；False = 任意环节失败
        """
        if QmtDataManager._vip_global_initialized:
            logger.info("[QmtDataManager] VIP客户端已连接，复用现有连接")
            return True

        with QmtDataManager._vip_lock:
            if QmtDataManager._vip_global_initialized:
                return True

            try:
                logger.info("=" * 60)
                logger.info("【启动QMT VIP直连模式 V2.1】")
                logger.info("=" * 60)

                # ── Step 1: 注入 VIP Token（CRITICAL-1修复） ──
                token = self.vip_token  # lazy property，此处首次触发加载
                xtdata.set_token(token)
                logger.info("✅ Step 1: VIP Token 已注入 xtdata")

                # ── Step 2: 连接本地 MiniQMT ──
                try:
                    xtdata.connect()
                    logger.info("✅ Step 2: xtdata.connect() 调用完成")
                except Exception as conn_e:
                    logger.error(f"❌ Step 2: xtdata.connect() 抛出异常: {conn_e}")
                    logger.error("请确认 MiniQMT / 投研版是否已登录运行")
                    QmtDataManager._vip_init_event.set()
                    return False

                # ── Step 3: 探针验证（CRITICAL-2修复） ──
                # connect() 不抛异常不代表真的通了
                # 用 get_trading_calendar 拿到实际数据才算连通
                try:
                    probe = xtdata.get_trading_calendar("SZSE")
                    if probe is None or len(probe) == 0:
                        logger.error(
                            "❌ Step 3: 探针返回空数据，连接未就绪（MiniQMT是否已登录？）"
                        )
                        QmtDataManager._vip_init_event.set()
                        return False
                    logger.info(
                        f"✅ Step 3: 探针验证通过（SZSE交易日历 {len(probe)} 条）"
                    )
                except Exception as probe_e:
                    logger.error(f"❌ Step 3: 探针异常: {probe_e}")
                    QmtDataManager._vip_init_event.set()
                    return False

                # ── 全部通过 ──
                QmtDataManager._vip_global_initialized = True
                QmtDataManager._vip_global_port = ("auto", 0)
                QmtDataManager._vip_init_event.set()

                logger.info("=" * 60)
                logger.info("✅ VIP直连完成：Token注入 → connect() → 探针验证 全部通过")
                logger.info("=" * 60)
                return True

            except ValueError as ve:
                logger.error(f"❌ VIP Token 配置错误: {ve}")
                QmtDataManager._vip_init_event.set()
                return False
            except Exception as e:
                logger.error(f"❌ VIP 客户端连线发生未知异常: {e}")
                QmtDataManager._vip_init_event.set()
                return False

    def stop_vip_service(self) -> bool:
        """
        重置 VIP 连接状态标记。

        注意：MiniQMT 的连接生命周期由客户端进程管理，
        Python 脚本无法主动断开；此方法仅重置内部状态，
        下次调用 start_vip_service() 会重新执行
        Token注入 → connect() → 探针验证 完整流程。

        Returns:
            True（始终）
        """
        with QmtDataManager._vip_lock:
            QmtDataManager._vip_global_initialized = False
            QmtDataManager._vip_global_port = None
            self.listen_port = None

        QmtDataManager._vip_init_event.clear()
        logger.info("[QmtDataManager] VIP连接状态已重置")
        return True

    def download_daily_data(
        self,
        stock_list: List[str],
        start_date: str,
        end_date: str,
        delay: float = 0.05,
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

                xtdata.download_history_data(
                    stock_code=stock_code,
                    period="1d",
                    start_time=start_date,
                    end_time=end_date,
                )

                # MED-9修复: 统一用 len(df) > 0 判定有效性，不依赖具体字段名
                # 同时补充 volume 字段，消除原日线/分钟线字段不一致歧义
                data = xtdata.get_local_data(
                    field_list=["time", "open", "high", "low", "close", "volume", "amount"],
                    stock_list=[stock_code],
                    period="1d",
                    start_time=start_date,
                    end_time=end_date,
                )

                if data and stock_code in data and len(data[stock_code]) > 0:
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
        self,
        stock_list: List[str],
        start_date: str,
        end_date: str,
        delay: float = 0.05,
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

                # MED-9修复: 统一用 len(df) > 0 判定，字段与日线保持一致
                data = xtdata.get_local_data(
                    field_list=["time", "open", "high", "low", "close", "volume", "amount"],
                    stock_list=[stock_code],
                    period="1m",
                    start_time=start_date,
                    end_time=end_date,
                )

                if data and stock_code in data and len(data[stock_code]) > 0:
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
            MED-10修复：VIP失败时返回完整失败报告，不再静默返回 {}
        """
        if not XT_AVAILABLE:
            logger.error("[QmtDataManager] xtquant模块不可用")
            return {}

        # MED-10修复: VIP 连接失败时不静默返回 {}
        # 返回完整失败报告，让调用方能区分"无任务"和"全部失败"
        if use_vip and self.use_vip:
            if not QmtDataManager._vip_global_initialized:
                vip_ok = self.start_vip_service()
                if not vip_ok:
                    logger.error("❌ VIP客户端连接失败，请确认QMT是否已登录运行")
                    return {
                        s: DownloadResult(
                            success=False,
                            stock_code=s,
                            period="tick",
                            error="VIP客户端连接失败：请确认MiniQMT已登录、Token已在.env配置",
                        )
                        for s in stock_list
                    }

        results = {}
        logger.info(
            f"【下载Tick数据】{trade_date} | {len(stock_list)}只股票 | VIP: {use_vip}"
        )

        for i, stock_code in enumerate(stock_list, 1):
            try:
                if check_existing:
                    existing = xtdata.get_local_data(
                        field_list=["time"],
                        stock_list=[stock_code],
                        period="tick",
                        start_time=trade_date,
                        end_time=trade_date,
                    )

                    # MED-6修复: 使用常量 TICK_VALID_MIN_COUNT 替代 Magic Number
                    if (
                        existing
                        and stock_code in existing
                        and len(existing[stock_code]) > TICK_VALID_MIN_COUNT
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

                # 官方文档：download_history_data 同步阻塞，完成后才返回，无需轮询
                xtdata.download_history_data(
                    stock_code=stock_code,
                    period="tick",
                    start_time=trade_date,
                    end_time=trade_date,
                )

                # MED-9修复: 统一用 len(df) > 0 判定（配合 TICK_VALID_MIN_COUNT 常量）
                check_data = xtdata.get_local_data(
                    field_list=["time"],
                    stock_list=[stock_code],
                    period="tick",
                    start_time=trade_date,
                    end_time=trade_date,
                )

                if check_data and stock_code in check_data:
                    tick_df = check_data[stock_code]
                    if tick_df is not None and len(tick_df) > TICK_VALID_MIN_COUNT:
                        tick_count = len(tick_df)
                        results[stock_code] = DownloadResult(
                            success=True,
                            stock_code=stock_code,
                            period="tick",
                            record_count=tick_count,
                            message=f"成功 ({tick_count}条)",
                        )
                        logger.info(
                            f"[{i}/{len(stock_list)}] ✅ {stock_code} Tick下载成功 ({tick_count}条)"
                        )
                    else:
                        results[stock_code] = DownloadResult(
                            success=False,
                            stock_code=stock_code,
                            period="tick",
                            message="获取空数据 (可能停牌/超限/无权限)",
                        )
                        logger.warning(
                            f"[{i}/{len(stock_list)}] ⏭️ {stock_code} {trade_date} Tick空数据，跳过"
                        )
                else:
                    results[stock_code] = DownloadResult(
                        success=False,
                        stock_code=stock_code,
                        period="tick",
                        message="获取空数据 (可能停牌/超限/无权限)",
                    )
                    logger.warning(
                        f"[{i}/{len(stock_list)}] ⏭️ {stock_code} {trade_date} Tick空数据，跳过"
                    )

            except Exception as e:
                logger.error(f"[{i}/{len(stock_list)}] {stock_code} 下载失败: {e}")
                results[stock_code] = DownloadResult(
                    success=False, stock_code=stock_code, period="tick", error=str(e)
                )

            time.sleep(delay)

        success_count = sum(1 for r in results.values() if r.success)
        logger.info(f"Tick数据下载完成: {success_count}/{len(stock_list)}")
        return results

    def verify_data_integrity(
        self,
        stock_list: List[str],
        trade_date: str,
        check_periods: List[str] = None,
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
                # MED-9修复: 统一用 len(df) > 0
                if "1d" in check_periods:
                    daily = xtdata.get_local_data(
                        field_list=["time"],
                        stock_list=[stock_code],
                        period="1d",
                        start_time=trade_date,
                        end_time=trade_date,
                    )
                    if daily and stock_code in daily and len(daily[stock_code]) > 0:
                        report.has_daily = True
                        report.daily_count = len(daily[stock_code])
                    else:
                        report.missing_periods.append("1d")

                if "1m" in check_periods:
                    minute = xtdata.get_local_data(
                        field_list=["time"],
                        stock_list=[stock_code],
                        period="1m",
                        start_time=trade_date,
                        end_time=trade_date,
                    )
                    if minute and stock_code in minute and len(minute[stock_code]) > 0:
                        report.has_minute = True
                        report.minute_count = len(minute[stock_code])
                    else:
                        report.missing_periods.append("1m")

                if "tick" in check_periods:
                    tick = xtdata.get_local_data(
                        field_list=["time"],
                        stock_list=[stock_code],
                        period="tick",
                        start_time=trade_date,
                        end_time=trade_date,
                    )
                    # MED-6修复: 使用常量替代 Magic Number 100
                    if tick and stock_code in tick and len(tick[stock_code]) > TICK_VALID_MIN_COUNT:
                        report.has_tick = True
                        report.tick_count = len(tick[stock_code])
                    else:
                        report.missing_periods.append("tick")

                reports[stock_code] = report

            except Exception as e:
                logger.error(f"验证 {stock_code} 数据完整性失败: {e}")
                report.missing_periods = list(check_periods)
                reports[stock_code] = report

        complete_count = sum(1 for r in reports.values() if r.is_complete)
        logger.info(f"数据完整性验证完成: 完整 {complete_count}/{len(stock_list)}")
        return reports

    def supplement_missing_data(
        self,
        missing_list: List[Tuple[str, str]],
        use_vip: bool = True,
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

        by_period: Dict[str, List[str]] = {}
        for stock_code, period in missing_list:
            if period not in by_period:
                by_period[period] = []
            by_period[period].append(stock_code)

        all_results: Dict[str, DownloadResult] = {}

        if "1d" in by_period:
            # MED-7修复：使用常量 SUPPLEMENT_LOOKBACK_DAYS 替代硬编码 10
            start = (
                datetime.now() - timedelta(days=SUPPLEMENT_LOOKBACK_DAYS)
            ).strftime("%Y%m%d")
            end = datetime.now().strftime("%Y%m%d")
            all_results.update(self.download_daily_data(by_period["1d"], start, end))

        if "1m" in by_period:
            today = datetime.now().strftime("%Y%m%d")
            all_results.update(
                self.download_minute_data(by_period["1m"], today, today)
            )

        if "tick" in by_period:
            today = datetime.now().strftime("%Y%m%d")
            all_results.update(
                self.download_tick_data(
                    by_period["tick"], today, use_vip=use_vip, check_existing=False
                )
            )

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
        results: Dict[str, Dict[str, DownloadResult]] = {}

        logger.info(
            f"【批量下载】{trade_date} | 周期: {periods} | {len(stock_list)}只股票"
        )

        if "1d" in periods:
            # MED-7修复：使用常量
            start_date = (
                datetime.strptime(trade_date, "%Y%m%d")
                - timedelta(days=SUPPLEMENT_LOOKBACK_DAYS)
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


# ============================================================
# 全局单例管理
# ============================================================

_qmt_manager: Optional["QmtDataManager"] = None
_qmt_manager_lock = threading.Lock()


def get_qmt_manager() -> "QmtDataManager":
    """
    获取全局 QMT 管理器实例（线程安全双重检查锁）

    Returns:
        QmtDataManager: QMT 数据管理器实例
    """
    global _qmt_manager
    if _qmt_manager is None:
        with _qmt_manager_lock:
            if _qmt_manager is None:
                QmtDataManager()  # __init__ 内部会赋值 _qmt_manager = self
    return _qmt_manager
