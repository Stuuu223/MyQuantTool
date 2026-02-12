# -*- coding: utf-8 -*-
"""
信号管理器 - 信号去重和通知系统

功能：
1. 信号去重 - 避免重复触发相同信号
2. 信号缓存 - 保存最近的信号历史
3. 信号通知 - UI弹窗、日志、邮件等
4. 信号统计 - 统计信号触发次数和成功率

作者: iFlow CLI
版本: V1.0
日期: 2026-02-05
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

from logic.utils.logger import get_logger
from logic.strategies.triple_funnel_scanner import TradingSignal, SignalType, RiskLevel

logger = get_logger(__name__)


class NotificationChannel(Enum):
    """通知渠道"""
    UI_POPUP = "UI_POPUP"       # UI弹窗
    LOG = "LOG"                 # 日志
    EMAIL = "EMAIL"             # 邮件
    WECHAT = "WECHAT"           # 微信
    DINGTALK = "DINGTALK"       # 钉钉


@dataclass
class SignalHistory:
    """信号历史记录"""
    signal_id: str
    stock_code: str
    stock_name: str
    signal_type: str
    timestamp: str
    price: float
    trigger_price: float
    signal_strength: float
    risk_level: str
    details: Dict
    executed: bool = False
    execution_time: Optional[str] = None
    execution_price: Optional[float] = None


class SignalDeduplicator:
    """
    信号去重器
    
    去重策略：
    1. 时间窗口去重 - 同一股票同一信号类型在N分钟内只触发一次
    2. 价格阈值去重 - 价格变化超过阈值才触发新信号
    3. 冷却期 - 高频信号设置冷却期
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.signal_cache: Dict[str, SignalHistory] = {}
        self.cooldown_cache: Dict[str, float] = {}  # 信号类型 -> 最后触发时间

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "time_window_minutes": 5,      # 时间窗口 (分钟)
            "price_threshold_pct": 0.5,    # 价格阈值 (0.5%)
            "cooldown_period_minutes": {   # 冷却期 (分钟)
                SignalType.VWAP_BREAKOUT.value: 10,
                SignalType.VOLUME_SURGE.value: 5,
                SignalType.AUCTION_SPIKE.value: 3,
            }
        }

    def should_trigger(self, signal: TradingSignal) -> bool:
        """
        判断是否应该触发信号
        
        Args:
            signal: 交易信号
        
        Returns:
            是否触发
        """
        # 1. 检查冷却期
        if not self._check_cooldown(signal):
            logger.debug(f"🚫 信号冷却中: {signal.signal_type.value}")
            return False

        # 2. 检查时间窗口去重
        if not self._check_time_window(signal):
            logger.debug(f"🚫 时间窗口内已有信号: {signal.signal_type.value}")
            return False

        # 3. 检查价格阈值
        if not self._check_price_threshold(signal):
            logger.debug(f"🚫 价格变化未达阈值: {signal.signal_type.value}")
            return False

        return True

    def _check_cooldown(self, signal: TradingSignal) -> bool:
        """检查冷却期"""
        signal_type = signal.signal_type.value
        cooldown_minutes = self.config["cooldown_period_minutes"].get(signal_type, 0)

        if cooldown_minutes == 0:
            return True

        last_trigger = self.cooldown_cache.get(signal_type, 0)
        if time.time() - last_trigger < cooldown_minutes * 60:
            return False

        return True

    def _check_time_window(self, signal: TradingSignal) -> bool:
        """检查时间窗口"""
        key = f"{signal.stock_code}_{signal.signal_type.value}"
        last_signal = self.signal_cache.get(key)

        if not last_signal:
            return True

        last_time = datetime.fromisoformat(last_signal.timestamp)
        current_time = datetime.fromisoformat(signal.timestamp)

        if (current_time - last_time) < timedelta(minutes=self.config["time_window_minutes"]):
            return False

        return True

    def _check_price_threshold(self, signal: TradingSignal) -> bool:
        """检查价格阈值"""
        key = f"{signal.stock_code}_{signal.signal_type.value}"
        last_signal = self.signal_cache.get(key)

        if not last_signal:
            return True

        price_change_pct = abs(signal.price - last_signal.price) / last_signal.price * 100

        if price_change_pct < self.config["price_threshold_pct"]:
            return False

        return True

    def add_signal(self, signal: TradingSignal):
        """添加信号到缓存"""
        # 保存到信号缓存
        history = SignalHistory(
            signal_id=signal.id,
            stock_code=signal.stock_code,
            stock_name=signal.stock_name,
            signal_type=signal.signal_type.value,
            timestamp=signal.timestamp,
            price=signal.price,
            trigger_price=signal.trigger_price,
            signal_strength=signal.signal_strength,
            risk_level=signal.risk_level.value,
            details=signal.details,
            executed=signal.executed,
            execution_time=signal.execution_time,
            execution_price=signal.execution_price
        )

        key = f"{signal.stock_code}_{signal.signal_type.value}"
        self.signal_cache[key] = history

        # 更新冷却期
        self.cooldown_cache[signal.signal_type.value] = time.time()

        logger.debug(f"✅ 信号已添加到缓存: {signal.id}")

    def get_recent_signals(self, stock_code: Optional[str] = None,
                         hours: int = 24) -> List[SignalHistory]:
        """
        获取最近的信号
        
        Args:
            stock_code: 股票代码 (None则返回所有)
            hours: 时间范围 (小时)
        
        Returns:
            信号列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        signals = []
        for signal in self.signal_cache.values():
            signal_time = datetime.fromisoformat(signal.timestamp)

            if signal_time < cutoff_time:
                continue

            if stock_code and signal.stock_code != stock_code:
                continue

            signals.append(signal)

        # 按时间排序
        signals.sort(key=lambda x: x.timestamp, reverse=True)

        return signals


class SignalNotifier:
    """
    信号通知器
    
    通知渠道：
    1. UI弹窗 - 通过Streamlit显示
    2. 日志 - 记录到日志文件
    3. 邮件 - 发送邮件通知
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.enabled_channels = self._init_channels()

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "channels": ["UI_POPUP", "LOG"],
            "email": {
                "enabled": False,
                "smtp_server": "",
                "smtp_port": 587,
                "from_addr": "",
                "to_addrs": [],
                "username": "",
                "password": ""
            }
        }

    def _init_channels(self) -> Set[NotificationChannel]:
        """初始化通知渠道"""
        channels = set()
        for channel_name in self.config["channels"]:
            try:
                channel = NotificationChannel[channel_name]
                channels.add(channel)
            except KeyError:
                logger.warning(f"⚠️ 未知的通知渠道: {channel_name}")

        return channels

    def notify(self, signal: TradingSignal):
        """
        发送通知
        
        Args:
            signal: 交易信号
        """
        message = self._format_message(signal)

        for channel in self.enabled_channels:
            try:
                if channel == NotificationChannel.UI_POPUP:
                    self._notify_ui(signal, message)
                elif channel == NotificationChannel.LOG:
                    self._notify_log(signal, message)
                elif channel == NotificationChannel.EMAIL:
                    self._notify_email(signal, message)
            except Exception as e:
                logger.error(f"❌ 发送通知失败 ({channel.value}): {e}")

    def _format_message(self, signal: TradingSignal) -> str:
        """格式化消息"""
        message = f"""
🚀 交易信号触发
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
股票: {signal.stock_name} ({signal.stock_code})
信号: {signal.signal_type.value}
时间: {signal.timestamp}
价格: {signal.price:.2f} (触发价: {signal.trigger_price:.2f})
强度: {signal.signal_strength:.2f}
风险: {signal.risk_level.value}

详情:
"""
        for key, value in signal.details.items():
            message += f"  {key}: {value}\n"

        return message

    def _notify_ui(self, signal: TradingSignal, message: str):
        """UI弹窗通知"""
        # 保存到UI通知队列，由UI组件读取
        self._save_to_ui_queue(signal, message)
        logger.info(f"✅ UI通知已发送: {signal.id}")

    def _notify_log(self, signal: TradingSignal, message: str):
        """日志通知"""
        logger.info(f"🚀 交易信号: {signal.stock_name} {signal.signal_type.value}")
        logger.info(message)

    def _notify_email(self, signal: TradingSignal, message: str):
        """邮件通知"""
        if not self.config["email"]["enabled"]:
            return

        # TODO: 实现邮件发送
        logger.info(f"📧 邮件通知暂未实现: {signal.id}")

    def _save_to_ui_queue(self, signal: TradingSignal, message: str):
        """保存到UI通知队列"""
        try:
            queue_dir = Path("data/signal_queue")
            queue_dir.mkdir(parents=True, exist_ok=True)

            queue_file = queue_dir / "notifications.jsonl"

            notification = {
                "id": signal.id,
                "stock_code": signal.stock_code,
                "stock_name": signal.stock_name,
                "signal_type": signal.signal_type.value,
                "timestamp": signal.timestamp,
                "message": message,
                "read": False
            }

            with open(queue_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(notification, ensure_ascii=False) + '\n')

        except Exception as e:
            logger.error(f"❌ 保存UI通知失败: {e}")


class SignalManager:
    """
    信号管理器主类
    
    整合去重和通知功能
    """

    def __init__(self, config_path: str = "config/signal_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

        self.deduplicator = SignalDeduplicator(self.config.get("deduplication", {}))
        self.notifier = SignalNotifier(self.config.get("notification", {}))

        # 信号统计
        self.signal_stats: Dict[str, Dict] = {}

        logger.info("✅ 信号管理器初始化完成")

    def _load_config(self) -> Dict:
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ 加载信号配置失败: {e}")

        return self._default_config()

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "deduplication": {},
            "notification": {
                "channels": ["UI_POPUP", "LOG"]
            }
        }

    def process_signal(self, signal: TradingSignal) -> bool:
        """
        处理信号
        
        Args:
            signal: 交易信号
        
        Returns:
            是否触发
        """
        # 1. 去重检查
        if not self.deduplicator.should_trigger(signal):
            return False

        # 2. 添加到缓存
        self.deduplicator.add_signal(signal)

        # 3. 发送通知
        self.notifier.notify(signal)

        # 4. 更新统计
        self._update_stats(signal)

        logger.info(f"✅ 信号已触发: {signal.id}")
        return True

    def _update_stats(self, signal: TradingSignal):
        """更新信号统计"""
        key = f"{signal.stock_code}_{signal.signal_type.value}"

        if key not in self.signal_stats:
            self.signal_stats[key] = {
                "stock_code": signal.stock_code,
                "stock_name": signal.stock_name,
                "signal_type": signal.signal_type.value,
                "count": 0,
                "last_triggered": None,
                "last_price": 0
            }

        stats = self.signal_stats[key]
        stats["count"] += 1
        stats["last_triggered"] = signal.timestamp
        stats["last_price"] = signal.price

    def get_signal_stats(self, stock_code: Optional[str] = None) -> List[Dict]:
        """
        获取信号统计
        
        Args:
            stock_code: 股票代码 (None则返回所有)
        
        Returns:
            统计列表
        """
        if stock_code:
            return [stats for stats in self.signal_stats.values() if stats["stock_code"] == stock_code]
        else:
            return list(self.signal_stats.values())

    def get_recent_signals(self, stock_code: Optional[str] = None,
                         hours: int = 24) -> List[SignalHistory]:
        """获取最近的信号"""
        return self.deduplicator.get_recent_signals(stock_code, hours)


# 全局单例
_signal_manager: Optional[SignalManager] = None


def get_signal_manager() -> SignalManager:
    """获取全局信号管理器实例"""
    global _signal_manager
    if _signal_manager is None:
        _signal_manager = SignalManager()
    return _signal_manager


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 信号管理器 - 演示")
    print("=" * 80)

    # 创建信号管理器
    manager = get_signal_manager()

    # 创建测试信号
    from logic.strategies.triple_funnel_scanner import TradingSignal, SignalType, RiskLevel

    signal1 = TradingSignal(
        id="TEST_001",
        stock_code="000001",
        stock_name="平安银行",
        signal_type=SignalType.VWAP_BREAKOUT,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        price=12.50,
        trigger_price=12.20,
        signal_strength=0.8,
        risk_level=RiskLevel.MEDIUM,
        details={"vwap": 12.20, "breakout_pct": 0.025}
    )

    # 处理信号
    print("\n📡 处理第一个信号...")
    triggered1 = manager.process_signal(signal1)
    print(f"触发: {triggered1}")

    # 重复信号 (应该被去重)
    print("\n📡 处理重复信号...")
    signal2 = TradingSignal(
        id="TEST_002",
        stock_code="000001",
        stock_name="平安银行",
        signal_type=SignalType.VWAP_BREAKOUT,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        price=12.50,
        trigger_price=12.20,
        signal_strength=0.8,
        risk_level=RiskLevel.MEDIUM,
        details={"vwap": 12.20, "breakout_pct": 0.025}
    )
    triggered2 = manager.process_signal(signal2)
    print(f"触发: {triggered2} (应该为False)")

    # 查看统计
    print("\n📊 信号统计:")
    for stats in manager.get_signal_stats():
        print(f"  {stats['stock_name']} {stats['signal_type']}: {stats['count']}次")

    # 查看历史
    print("\n📜 信号历史:")
    for history in manager.get_recent_signals(hours=1):
        print(f"  {history.stock_name} {history.signal_type} @ {history.timestamp}")

    print("\n" + "=" * 80)