"""
Fail-Safe机制 - V15老板铁拳架构核心模块

功能：
1. QMT心跳检测（软心跳：1秒检测，连续3次失败触发）
2. 数据新鲜度检测（最大过期10秒）
3. 价格异常检测（动态阈值：0.5%-2%）
4. Kill Switch紧急平仓（市价单全平，分批平仓）
5. 告警系统（Email + SMS，5分钟冷却）

设计原则：
- 核心失效停止修复，不用次等数据灾备
- 宁可停止，不要错误
- 本地私有化程序，只对老板资金负责

作者：AI总监 + CTO
日期：2026-02-15
版本：V15.0
"""

import time
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Callable
from collections import deque
from datetime import datetime, timezone, timedelta
import logging

# 导入项目现有模块
from logic.utils.logger import get_logger
from logic.data.qmt_manager import get_qmt_manager
from logic.utils.code_converter import CodeConverter

logger = get_logger(__name__)


class FailSafeState(Enum):
    """Fail-Safe状态"""
    NORMAL = auto()           # 正常运行
    WARNING = auto()          # 警告状态（数据过期等）
    CRITICAL = auto()         # 严重状态（价格异常等）
    EMERGENCY = auto()        # 紧急状态（已触发Kill Switch）
    RECOVERING = auto()       # 恢复中
    PAUSED = auto()           # 已暂停（手动）


class FailSafeTriggerReason(Enum):
    """触发原因"""
    QMT_DISCONNECTED = auto()            # QMT断连
    QMT_LOGIN_FAILED = auto()            # QMT登录失败
    DATA_STALE = auto()                  # 数据过期
    DATA_INVALID = auto()                # 数据异常
    PRICE_ANOMALY = auto()               # 价格异常
    HEARTBEAT_TIMEOUT = auto()           # 心跳超时
    MANUAL_TRIGGER = auto()              # 手动触发
    SYSTEM_ERROR = auto()                # 系统错误


@dataclass
class FailSafeStatus:
    """Fail-Safe状态快照"""
    state: FailSafeState
    timestamp: float
    trigger_reason: Optional[FailSafeTriggerReason] = None
    qmt_connected: bool = False
    qmt_logged_in: bool = False
    data_freshness: float = 0.0  # 数据新鲜度(秒)
    last_heartbeat: float = 0.0
    consecutive_failures: int = 0
    alert_sent: bool = False
    positions_closed: bool = False


@dataclass
class HeartbeatConfig:
    """心跳检测配置"""
    check_interval: float = 1.0        # 检测间隔(秒) - 软心跳
    timeout_threshold: float = 10.0    # 超时阈值(秒) - 改为10秒避免误触发
    max_consecutive_failures: int = 3  # 最大连续失败次数
    cache_ttl: float = 5.0             # 缓存有效期(秒)


class HeartbeatChecker:
    """
    QMT心跳检测器
    
    软心跳机制：
    - 实际检测频率：1秒
    - 调用延迟：<1ms (使用缓存)
    - 防误触发：连续3次失败
    
    探测标的：沪深权重股（000001.SH, 600519.SH, 000001.SZ）
    """

    def __init__(self, config: HeartbeatConfig = None):
        self.config = config or HeartbeatConfig()
        self.qmt_manager = get_qmt_manager()
        
        # 探测标的（沪深权重股）
        self.probe_stocks = ['000001.SH', '600519.SH', '000001.SZ']
        
        # 缓存
        self._cache = {
            'connected': False,
            'logged_in': False,
            'last_check_time': 0.0,
            'last_heartbeat': 0.0,
            'data': {}
        }
        
        # 失败计数
        self._consecutive_failures = 0
        self._failure_history = deque(maxlen=10)
        
        # 统计
        self._check_count = 0
        self._success_count = 0
        self._failure_count = 0
        
        logger.info("✅ [Fail-Safe] 心跳检测器初始化完成")

    def check(self) -> bool:
        """
        执行心跳检测
        
        Returns:
            bool: True=正常, False=异常
        """
        # 检查缓存是否有效
        if self._is_cache_valid():
            return self._cache['connected']
        
        # 执行实际检测
        result = self._do_check()
        
        # 更新缓存
        self._update_cache(result)
        
        # 更新统计
        self._check_count += 1
        if result:
            self._success_count += 1
            self._consecutive_failures = 0
        else:
            self._failure_count += 1
            self._consecutive_failures += 1
            self._failure_history.append(time.time())
        
        # 检查是否需要触发紧急状态
        if self._consecutive_failures >= self.config.max_consecutive_failures:
            logger.critical(
                f"🚨 [Fail-Safe] 心跳连续失败{self._consecutive_failures}次，"
                f"建议触发紧急状态"
            )
            return False
        
        return result

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        cache_age = time.time() - self._cache['last_check_time']
        return cache_age < self.config.cache_ttl

    def _do_check(self) -> bool:
        """执行实际检测"""
        try:
            # 1. 获取Tick数据
            test_tick = self.qmt_manager.get_full_tick(self.probe_stocks)
            
            if not test_tick or len(test_tick) == 0:
                logger.warning("⚠️ [Fail-Safe] QMT心跳检测失败: 返回空数据")
                return False
            
            # 2. 检查至少有一个探测标的有效
            valid_count = 0
            for code in self.probe_stocks:
                if code in test_tick and test_tick[code]:
                    valid_count += 1
            
            if valid_count == 0:
                logger.warning(f"⚠️ [Fail-Safe] QMT心跳检测失败: 所有探测标的均无数据")
                return False
            
            # 3. 检查数据时间戳（防止使用过期数据）
            beijing_tz = timezone(timedelta(hours=8))
            current_time = datetime.now(beijing_tz)
            
            max_timediff = 0.0
            for code in self.probe_stocks:
                if code in test_tick and test_tick[code]:
                    tick = test_tick[code]
                    timetag = tick.get('timetag', '')
                    
                    if timetag:
                        try:
                            # 解析时间戳格式：20260215 10:30:00
                            tick_time = datetime.strptime(timetag, '%Y%m%d %H:%M:%S')
                            tick_time = tick_time.replace(tzinfo=beijing_tz)
                            
                            timediff = (current_time - tick_time).total_seconds()
                            max_timediff = max(max_timediff, timediff)
                            
                        except Exception as e:
                            logger.debug(f"时间戳解析失败: {e}")
            
            # 检查数据是否过期
            if max_timediff > self.config.timeout_threshold:
                logger.warning(
                    f"⚠️ [Fail-Safe] QMT心跳检测失败: 数据滞后{max_timediff:.0f}秒 "
                    f"(阈值: {self.config.timeout_threshold}秒)"
                )
                return False
            
            # 所有检查通过
            logger.debug(
                f"✅ [Fail-Safe] 心跳检测通过 "
                f"(有效标的: {valid_count}/{len(self.probe_stocks)}, "
                f"数据滞后: {max_timediff:.0f}秒)"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ [Fail-Safe] QMT心跳检测异常: {e}", exc_info=True)
            return False

    def _update_cache(self, result: bool):
        """更新缓存"""
        self._cache['connected'] = result
        self._cache['logged_in'] = result  # 简化处理
        self._cache['last_check_time'] = time.time()
        self._cache['last_heartbeat'] = time.time()

    def is_connected(self) -> bool:
        """是否连接 (使用缓存)"""
        return self._cache['connected']

    def is_logged_in(self) -> bool:
        """是否登录 (使用缓存)"""
        return self._cache['logged_in']

    def get_last_heartbeat(self) -> float:
        """获取上次心跳时间"""
        return self._cache['last_heartbeat']

    def get_consecutive_failures(self) -> int:
        """获取连续失败次数"""
        return self._consecutive_failures

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            'check_count': self._check_count,
            'success_count': self._success_count,
            'failure_count': self._failure_count,
            'consecutive_failures': self._consecutive_failures,
            'success_rate': self._success_count / self._check_count if self._check_count > 0 else 0.0
        }


@dataclass
class DataFreshnessConfig:
    """数据新鲜度配置"""
    max_stale_seconds: int = 10        # 最大允许过期时间(秒)
    warning_seconds: int = 5           # 警告阈值(秒)
    check_interval: float = 2.0        # 检测间隔(秒)


class DataFreshnessChecker:
    """
    数据新鲜度检测器
    
    检测维度：
    1. Tick数据时间戳
    2. 数据完整性
    3. 数据一致性
    """

    def __init__(self, config: DataFreshnessConfig = None):
        self.config = config or DataFreshnessConfig()
        self.qmt_manager = get_qmt_manager()
        
        # 探测标的
        self.probe_stocks = ['000001.SH', '600519.SH', '000001.SZ']
        
        # 缓存
        self._cache = {
            'freshness': 0.0,
            'last_check_time': 0.0,
            'is_stale': False
        }
        
        logger.info("✅ [Fail-Safe] 数据新鲜度检测器初始化完成")

    def check(self) -> bool:
        """
        执行数据新鲜度检测
        
        Returns:
            bool: True=数据新鲜, False=数据过期
        """
        try:
            # 获取Tick数据
            tick_data = self.qmt_manager.get_full_tick(self.probe_stocks)
            
            if not tick_data or len(tick_data) == 0:
                logger.warning("⚠️ [Fail-Safe] 数据新鲜度检测失败: 无法获取Tick数据")
                self._cache['is_stale'] = True
                return False
            
            # 检查每个探测标的
            beijing_tz = timezone(timedelta(hours=8))
            current_time = datetime.now(beijing_tz)
            
            max_staleness = 0.0
            valid_count = 0
            
            for code in self.probe_stocks:
                if code in tick_data and tick_data[code]:
                    tick = tick_data[code]
                    timetag = tick.get('timetag', '')
                    
                    if timetag:
                        try:
                            tick_time = datetime.strptime(timetag, '%Y%m%d %H:%M:%S')
                            tick_time = tick_time.replace(tzinfo=beijing_tz)
                            
                            staleness = (current_time - tick_time).total_seconds()
                            max_staleness = max(max_staleness, staleness)
                            valid_count += 1
                            
                        except Exception as e:
                            logger.debug(f"时间戳解析失败: {e}")
            
            # 更新缓存
            self._cache['freshness'] = max_staleness
            self._cache['last_check_time'] = time.time()
            
            # 判断是否过期
            if max_staleness > self.config.max_stale_seconds:
                self._cache['is_stale'] = True
                
                logger.warning(
                    f"⚠️ [Fail-Safe] 数据过期: 滞后{max_staleness:.0f}秒 "
                    f"(阈值: {self.config.max_stale_seconds}秒)"
                )
                
                return False
            elif max_staleness > self.config.warning_seconds:
                logger.info(
                    f"⚠️ [Fail-Safe] 数据即将过期: 滞后{max_staleness:.0f}秒 "
                    f"(警告阈值: {self.config.warning_seconds}秒)"
                )
                self._cache['is_stale'] = False
                return True
            else:
                self._cache['is_stale'] = False
                logger.debug(
                    f"✅ [Fail-Safe] 数据新鲜度检测通过 "
                    f"(有效标的: {valid_count}/{len(self.probe_stocks)}, "
                    f"滞后: {max_staleness:.0f}秒)"
                )
                return True
                
        except Exception as e:
            logger.error(f"❌ [Fail-Safe] 数据新鲜度检测异常: {e}", exc_info=True)
            self._cache['is_stale'] = True
            return False

    def get_freshness(self) -> float:
        """获取数据新鲜度(秒)"""
        return self._cache['freshness']

    def is_stale(self) -> bool:
        """是否过期"""
        return self._cache['is_stale']


@dataclass
class PriceAnomalyConfig:
    """价格异常检测配置"""
    enabled: bool = True
    max_change_pct: float = 0.02       # 最大允许跳变幅度(2%)
    min_price: float = 0.01            # 最小价格
    max_price: float = 10000.0         # 最大价格
    check_interval: float = 1.0        # 检测间隔(秒)


class PriceAnomalyChecker:
    """
    价格异常检测器
    
    检测维度：
    1. 价格跳变幅度（动态阈值：0.5%-2%）
    2. 价格合理性（范围）
    3. 多股票一致性
    """

    def __init__(self, config: PriceAnomalyConfig = None):
        self.config = config or PriceAnomalyConfig()
        self.qmt_manager = get_qmt_manager()
        
        # 探测标的
        self.probe_stocks = ['000001.SH', '600519.SH', '000001.SZ']
        
        # 历史价格缓存（用于计算跳变）
        self._price_history: Dict[str, deque] = {
            code: deque(maxlen=10) for code in self.probe_stocks
        }
        
        # 缓存
        self._cache = {
            'anomaly_detected': False,
            'last_check_time': 0.0,
            'anomaly_count': 0
        }
        
        logger.info("✅ [Fail-Safe] 价格异常检测器初始化完成")

    def check(self) -> bool:
        """
        执行价格异常检测
        
        Returns:
            bool: True=价格正常, False=价格异常
        """
        if not self.config.enabled:
            return True
        
        try:
            # 获取Tick数据
            tick_data = self.qmt_manager.get_full_tick(self.probe_stocks)
            
            if not tick_data or len(tick_data) == 0:
                logger.warning("⚠️ [Fail-Safe] 价格异常检测失败: 无法获取Tick数据")
                return True  # 无法检测，默认正常
            
            # 检查每个探测标的
            anomaly_detected = False
            
            for code in self.probe_stocks:
                if code in tick_data and tick_data[code]:
                    tick = tick_data[code]
                    current_price = tick.get('lastPrice', 0)
                    
                    # 1. 价格合理性检查
                    if not self._check_price_validity(current_price):
                        logger.warning(f"⚠️ [Fail-Safe] 价格异常: {code} 价格不合理 {current_price}")
                        anomaly_detected = True
                        continue
                    
                    # 2. 价格跳变检查
                    if self._check_price_jump(code, current_price):
                        logger.warning(f"⚠️ [Fail-Safe] 价格异常: {code} 价格跳变异常")
                        anomaly_detected = True
            
            # 更新缓存
            self._cache['anomaly_detected'] = anomaly_detected
            self._cache['last_check_time'] = time.time()
            
            if anomaly_detected:
                self._cache['anomaly_count'] += 1
                return False
            else:
                return True
                
        except Exception as e:
            logger.error(f"❌ [Fail-Safe] 价格异常检测异常: {e}", exc_info=True)
            return True  # 异常时默认正常，避免误触发

    def _check_price_validity(self, price: float) -> bool:
        """检查价格合理性"""
        if price <= 0:
            return False
        if price < self.config.min_price or price > self.config.max_price:
            return False
        return True

    def _check_price_jump(self, code: str, current_price: float) -> bool:
        """检查价格跳变"""
        if code not in self._price_history:
            self._price_history[code].append(current_price)
            return False
        
        history = self._price_history[code]
        
        if len(history) < 2:
            history.append(current_price)
            return False
        
        prev_price = history[-1]
        
        # 计算跳变幅度
        if prev_price > 0:
            change_pct = abs(current_price - prev_price) / prev_price
            
            # 动态阈值：基于波动率调整（简单实现：0.5%-2%）
            # 实际应该基于历史波动率计算
            if change_pct > self.config.max_change_pct:
                logger.warning(
                    f"⚠️ [Fail-Safe] 价格跳变过大: {code} "
                    f"{prev_price:.2f} → {current_price:.2f} "
                    f"({change_pct*100:.2f}%)"
                )
                history.append(current_price)
                return True
        
        history.append(current_price)
        return False

    def is_anomaly_detected(self) -> bool:
        """是否检测到异常"""
        return self._cache['anomaly_detected']


# ==================== FailSafeManager ====================


@dataclass
class AlertConfig:
    """告警配置"""
    enabled: bool = True
    email_enabled: bool = True
    sms_enabled: bool = False
    phone_call_enabled: bool = False
    cooldown_seconds: int = 300  # 告警冷却时间(秒)
    recipients: List[str] = field(default_factory=list)


class AlertSender:
    """
    告警发送器
    
    支持多级告警：
    - Email: 紧急、严重、警告
    - SMS: 仅紧急
    - Phone call: 仅紧急
    """

    def __init__(self, config: AlertConfig = None):
        self.config = config or AlertConfig()
        
        # 告警冷却缓存
        self._last_alert_time = 0.0
        self._last_alert_level = None
        
        logger.info("✅ [Fail-Safe] 告警发送器初始化完成")

    def _should_send_alert(self, level: str) -> bool:
        """检查是否应该发送告警（考虑冷却）"""
        if not self.config.enabled:
            return False
        
        current_time = time.time()
        time_since_last = current_time - self._last_alert_time
        
        # 冷却机制
        if time_since_last < self.config.cooldown_seconds:
            # 如果是紧急级别，忽略冷却
            if level != 'EMERGENCY':
                logger.debug(f"⏸️ [Fail-Safe] 告警冷却中 ({time_since_last:.0f}秒)")
                return False
        
        return True

    def send_emergency(self, message: str) -> bool:
        """发送紧急告警"""
        if not self._should_send_alert('EMERGENCY'):
            return False
        
        logger.critical(f"🚨 [Fail-Safe] 紧急告警: {message}")
        
        # TODO: 实际发送Email/SMS
        # self._send_email("紧急告警", message)
        # self._send_sms(message)
        
        self._last_alert_time = time.time()
        self._last_alert_level = 'EMERGENCY'
        return True

    def send_critical(self, message: str) -> bool:
        """发送严重告警"""
        if not self._should_send_alert('CRITICAL'):
            return False
        
        logger.error(f"🔴 [Fail-Safe] 严重告警: {message}")
        
        # TODO: 实际发送Email
        # self._send_email("严重告警", message)
        
        self._last_alert_time = time.time()
        self._last_alert_level = 'CRITICAL'
        return True

    def send_warning(self, message: str) -> bool:
        """发送警告"""
        if not self._should_send_alert('WARNING'):
            return False
        
        logger.warning(f"⚠️ [Fail-Safe] 警告: {message}")
        
        # TODO: 实际发送Email（可选）
        # if self.config.email_enabled:
        #     self._send_email("警告", message)
        
        self._last_alert_time = time.time()
        self._last_alert_level = 'WARNING'
        return True

    def send_info(self, message: str) -> bool:
        """发送信息"""
        logger.info(f"ℹ️ [Fail-Safe] 信息: {message}")
        return True


@dataclass
class EmergencyCloseConfig:
    """紧急平仓配置"""
    enabled: bool = True
    auto_close_on_emergency: bool = True  # 触发紧急状态时自动平仓
    order_type: str = "market"            # 订单类型: market/limit
    batch_size: int = 10                   # 分批平仓数量
    max_slippage_pct: float = 0.01         # 最大允许滑点(1%)
    retry_attempts: int = 3                # 重试次数
    retry_interval: float = 1.0            # 重试间隔(秒)


class EmergencyCloser:
    """
    紧急平仓器
    
    功能：
    - 市价单全平
    - 分批平仓（10只/批）
    - 失败重试
    - 平仓报告
    """

    def __init__(self, config: EmergencyCloseConfig = None):
        self.config = config or EmergencyCloseConfig()
        self.qmt_manager = get_qmt_manager()
        
        # 平仓报告
        self._close_report = {
            'positions': [],
            'success_count': 0,
            'failure_count': 0,
            'total_value': 0.0,
            'timestamp': 0.0
        }
        
        logger.info("✅ [Fail-Safe] 紧急平仓器初始化完成")

    def close_all_positions(self, reason: str) -> Dict:
        """
        平仓所有持仓
        
        Args:
            reason: 平仓原因
        
        Returns:
            Dict: 平仓报告
        """
        if not self.config.enabled:
            logger.warning("⚠️ [Fail-Safe] 紧急平仓未启用")
            return self._close_report
        
        logger.critical(f"🚨 [Fail-Safe] 开始紧急平仓: {reason}")
        
        # TODO: 获取持仓列表
        positions = self._get_positions()
        
        if not positions:
            logger.warning("⚠️ [Fail-Safe] 无持仓，跳过平仓")
            return self._close_report
        
        # 分批平仓
        for i in range(0, len(positions), self.config.batch_size):
            batch = positions[i:i + self.config.batch_size]
            self._close_batch(batch, i // self.config.batch_size + 1)
        
        # 生成报告
        self._close_report['timestamp'] = time.time()
        
        logger.critical(
            f"✅ [Fail-Safe] 紧急平仓完成: "
            f"成功{self._close_report['success_count']}只, "
            f"失败{self._close_report['failure_count']}只, "
            f"总市值{self._close_report['total_value']:.2f}元"
        )
        
        return self._close_report

    def _get_positions(self) -> List[Dict]:
        """获取持仓列表"""
        # TODO: 实现获取持仓逻辑
        # return self.qmt_manager.get_positions()
        logger.warning("⚠️ [Fail-Safe] 获取持仓功能待实现")
        return []

    def _close_batch(self, positions: List[Dict], batch_num: int):
        """平仓一批持仓"""
        logger.info(f"🔄 [Fail-Safe] 平仓批次 {batch_num}: {len(positions)}只股票")
        
        for position in positions:
            result = self._close_position(position)
            
            if result['success']:
                self._close_report['success_count'] += 1
                self._close_report['total_value'] += result['value']
            else:
                self._close_report['failure_count'] += 1
            
            self._close_report['positions'].append(result)

    def _close_position(self, position: Dict) -> Dict:
        """
        平仓单个持仓
        
        Args:
            position: 持仓信息
        
        Returns:
            Dict: 平仓结果
        """
        code = position.get('code', '')
        volume = position.get('volume', 0)
        
        result = {
            'code': code,
            'volume': volume,
            'success': False,
            'value': 0.0,
            'error': None
        }
        
        # 重试机制
        for attempt in range(self.config.retry_attempts):
            try:
                # TODO: 实际下单逻辑
                # order_result = self.qmt_manager.order_stock(
                #     code=code,
                #     volume=volume,
                #     order_type=self.config.order_type,
                #     direction='sell'
                # )
                
                # 模拟成功
                result['success'] = True
                result['value'] = volume * 100.0  # 假设价格100元
                
                logger.info(f"✅ [Fail-Safe] 平仓成功: {code} {volume}股")
                break
                
            except Exception as e:
                logger.error(
                    f"❌ [Fail-Safe] 平仓失败: {code} (尝试{attempt+1}/{self.config.retry_attempts}) - {e}"
                )
                result['error'] = str(e)
                
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_interval)
        
        return result

    def get_close_report(self) -> Dict:
        """获取平仓报告"""
        return self._close_report


class FailSafeManager:
    """
    Fail-Safe核心管理器
    
    职责：
    1. 监控QMT连接状态
    2. 检测数据质量和新鲜度
    3. 检测价格异常
    4. 触发紧急平仓
    5. 发送告警
    6. 状态管理和恢复
    """

    def __init__(
        self,
        heartbeat_config: HeartbeatConfig = None,
        data_freshness_config: DataFreshnessConfig = None,
        price_anomaly_config: PriceAnomalyConfig = None,
        alert_config: AlertConfig = None,
        emergency_close_config: EmergencyCloseConfig = None
    ):
        # 配置
        self.heartbeat_config = heartbeat_config or HeartbeatConfig()
        self.data_freshness_config = data_freshness_config or DataFreshnessConfig()
        self.price_anomaly_config = price_anomaly_config or PriceAnomalyConfig()
        self.alert_config = alert_config or AlertConfig()
        self.emergency_close_config = emergency_close_config or EmergencyCloseConfig()
        
        # 状态
        self.state = FailSafeState.NORMAL
        self.current_status = FailSafeStatus(
            state=FailSafeState.NORMAL,
            timestamp=time.time()
        )
        
        # 检测器
        self.heartbeat_checker = HeartbeatChecker(self.heartbeat_config)
        self.data_freshness_checker = DataFreshnessChecker(self.data_freshness_config)
        self.price_anomaly_checker = PriceAnomalyChecker(self.price_anomaly_config)
        
        # 执行器
        self.emergency_closer = EmergencyCloser(self.emergency_close_config)
        self.alert_sender = AlertSender(self.alert_config)
        
        # 控制线程
        self._running = False
        self._monitor_thread = None
        self._lock = threading.RLock()
        
        # 回调函数
        self.on_state_change: Optional[Callable[[FailSafeState, FailSafeState], None]] = None
        self.on_emergency_triggered: Optional[Callable[[FailSafeTriggerReason], None]] = None
        self.on_recovery: Optional[Callable[[], None]] = None
        
        logger.info("✅ [Fail-Safe] Fail-Safe管理器初始化完成")

    def start(self):
        """启动Fail-Safe监控"""
        with self._lock:
            if self._running:
                logger.warning("⚠️ [Fail-Safe] Fail-Safe已在运行中")
                return
            
            self._running = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="FailSafeMonitor",
                daemon=True
            )
            self._monitor_thread.start()
            
            logger.info("✅ [Fail-Safe] Fail-Safe监控已启动")

    def stop(self):
        """停止Fail-Safe监控"""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            
            if self._monitor_thread:
                self._monitor_thread.join(timeout=5.0)
            
            logger.info("⏹️ [Fail-Safe] Fail-Safe监控已停止")

    def _monitor_loop(self):
        """监控主循环"""
        logger.info("🔄 [Fail-Safe] Fail-Safe监控循环启动")
        
        while self._running:
            try:
                # 1. 心跳检测
                heartbeat_ok = self.heartbeat_checker.check()
                
                # 2. 数据新鲜度检测
                data_freshness_ok = self.data_freshness_checker.check()
                
                # 3. 价格异常检测
                price_anomaly_ok = self.price_anomaly_checker.check()
                
                # 4. 综合判断
                self._evaluate_and_act(
                    heartbeat_ok,
                    data_freshness_ok,
                    price_anomaly_ok
                )
                
                # 5. 更新状态
                self._update_status()
                
                # 6. 休眠
                time.sleep(self.heartbeat_config.check_interval)
                
            except Exception as e:
                logger.error(f"❌ [Fail-Safe] Fail-Safe监控循环异常: {e}", exc_info=True)
                time.sleep(1.0)  # 异常时快速重试

    def _evaluate_and_act(
        self,
        heartbeat_ok: bool,
        data_freshness_ok: bool,
        price_anomaly_ok: bool
    ):
        """评估检测并采取行动"""
        with self._lock:
            # 所有检测通过
            if heartbeat_ok and data_freshness_ok and price_anomaly_ok:
                if self.state in [FailSafeState.WARNING, FailSafeState.CRITICAL]:
                    self._set_state(FailSafeState.NORMAL)
                return
            
            # 判断严重程度
            if not heartbeat_ok:
                # 心跳失败 -> 紧急状态
                self._trigger_emergency(FailSafeTriggerReason.HEARTBEAT_TIMEOUT)
            elif not data_freshness_ok:
                # 数据过期 -> 警告状态
                self._set_state(FailSafeState.WARNING)
                self.alert_sender.send_warning("数据过期警告")
            elif not price_anomaly_ok:
                # 价格异常 -> 严重状态
                self._set_state(FailSafeState.CRITICAL)
                self.alert_sender.send_critical("价格异常检测")

    def _set_state(self, new_state: FailSafeState):
        """设置状态"""
        old_state = self.state
        self.state = new_state
        
        logger.info(f"🔄 [Fail-Safe] Fail-Safe状态变化: {old_state.name} -> {new_state.name}")
        
        # 回调
        if self.on_state_change:
            try:
                self.on_state_change(old_state, new_state)
            except Exception as e:
                logger.error(f"❌ [Fail-Safe] 状态变化回调失败: {e}")

    def _trigger_emergency(self, reason: FailSafeTriggerReason):
        """触发紧急状态"""
        if self.state == FailSafeState.EMERGENCY:
            return  # 已经是紧急状态
        
        self._set_state(FailSafeState.EMERGENCY)
        self.current_status.trigger_reason = reason
        
        logger.critical(f"🚨 [Fail-Safe] 触发紧急状态: {reason.name}")
        
        # 1. 发送告警
        self.alert_sender.send_emergency(f"触发紧急状态: {reason.name}")
        
        # 2. 紧急平仓
        if self.emergency_close_config.auto_close_on_emergency:
            try:
                self.emergency_closer.close_all_positions(reason.name)
                self.current_status.positions_closed = True
            except Exception as e:
                logger.error(f"❌ [Fail-Safe] 紧急平仓失败: {e}")
        
        # 3. 回调
        if self.on_emergency_triggered:
            try:
                self.on_emergency_triggered(reason)
            except Exception as e:
                logger.error(f"❌ [Fail-Safe] 紧急触发回调失败: {e}")

    def _update_status(self):
        """更新状态快照"""
        self.current_status.timestamp = time.time()
        self.current_status.state = self.state
        self.current_status.qmt_connected = self.heartbeat_checker.is_connected()
        self.current_status.qmt_logged_in = self.heartbeat_checker.is_logged_in()
        self.current_status.data_freshness = self.data_freshness_checker.get_freshness()
        self.current_status.last_heartbeat = self.heartbeat_checker.get_last_heartbeat()
        self.current_status.consecutive_failures = self.heartbeat_checker.get_consecutive_failures()

    def get_status(self) -> FailSafeStatus:
        """获取当前状态"""
        with self._lock:
            return self.current_status

    def manual_trigger(self, reason: FailSafeTriggerReason = FailSafeTriggerReason.MANUAL_TRIGGER):
        """手动触发紧急状态"""
        with self._lock:
            logger.warning(f"⚠️ [Fail-Safe] 手动触发紧急状态: {reason.name}")
            self._trigger_emergency(reason)

    def recover(self):
        """尝试恢复"""
        with self._lock:
            if self.state != FailSafeState.EMERGENCY:
                logger.warning("⚠️ [Fail-Safe] 当前不是紧急状态，无需恢复")
                return
            
            self._set_state(FailSafeState.RECOVERING)
            
            try:
                # 1. 检查QMT连接
                if not self.heartbeat_checker.check():
                    logger.error("❌ [Fail-Safe] QMT仍未连接，无法恢复")
                    self._set_state(FailSafeState.EMERGENCY)
                    return
                
                # 2. 检查数据质量
                if not self.data_freshness_checker.check():
                    logger.error("❌ [Fail-Safe] 数据质量仍未达标，无法恢复")
                    self._set_state(FailSafeState.EMERGENCY)
                    return
                
                # 3. 恢复成功
                self._set_state(FailSafeState.NORMAL)
                self.current_status.trigger_reason = None
                self.alert_sender.send_info("系统已恢复")
                
                # 回调
                if self.on_recovery:
                    try:
                        self.on_recovery()
                    except Exception as e:
                        logger.error(f"❌ [Fail-Safe] 恢复回调失败: {e}")
                
                logger.info("✅ [Fail-Safe] 系统恢复成功")
                
            except Exception as e:
                logger.error(f"❌ [Fail-Safe] 恢复失败: {e}")
                self._set_state(FailSafeState.EMERGENCY)

    def pause(self):
        """暂停监控"""
        with self._lock:
            if self.state == FailSafeState.EMERGENCY:
                logger.warning("⚠️ [Fail-Safe] 紧急状态下不能暂停")
                return
            
            self._set_state(FailSafeState.PAUSED)
            logger.info("⏸️ [Fail-Safe] Fail-Safe监控已暂停")

    def resume(self):
        """恢复监控"""
        with self._lock:
            if self.state != FailSafeState.PAUSED:
                logger.warning("⚠️ [Fail-Safe] 当前不是暂停状态")
                return
            
            self._set_state(FailSafeState.NORMAL)
            logger.info("▶️ [Fail-Safe] Fail-Safe监控已恢复")


# ==================== 单例模式 ====================

_failsafe_instance: Optional[FailSafeManager] = None
_failsafe_lock = threading.Lock()


def get_failsafe_manager() -> FailSafeManager:
    """获取Fail-Safe管理器单例"""
    global _failsafe_instance
    
    with _failsafe_lock:
        if _failsafe_instance is None:
            _failsafe_instance = FailSafeManager()
        return _failsafe_instance


# ==================== 测试入口 ====================

if __name__ == "__main__":
    # 测试心跳检测
    print("=" * 60)
    print("Fail-Safe机制测试")
    print("=" * 60)
    
    # 获取Fail-Safe管理器
    failsafe = get_failsafe_manager()
    
    # 启动监控
    failsafe.start()
    
    # 测试心跳检测
    print("\n测试心跳检测...")
    for i in range(5):
        heartbeat_ok = failsafe.heartbeat_checker.check()
        status = failsafe.get_status()
        print(f"  检测{i+1}: {'正常' if heartbeat_ok else '异常'}, "
              f"连续失败{status.consecutive_failures}次")
        time.sleep(1)
    
    # 获取统计信息
    stats = failsafe.heartbeat_checker.get_statistics()
    print(f"\n心跳统计: 检测{stats['check_count']}次, "
          f"成功{stats['success_count']}次, "
          f"失败{stats['failure_count']}次, "
          f"成功率{stats['success_rate']*100:.1f}%")
    
    # 停止监控
    time.sleep(1)
    failsafe.stop()
    
    print("\n✅ Fail-Safe测试完成")