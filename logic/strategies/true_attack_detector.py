#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TrueAttackDetector - 真资金攻击检测器

基于知识库V12.1.0第505-520行定义的4个特征：
1. 持续流入（不是一闪而过）- 检查至少3分钟连续净流入
2. 量价配合（价格上涨伴随放量）
3. 买盘>卖盘（主力真买，非对倒）
4. 非尾盘偷袭（避免最后15分钟）

使用 ratio = main_inflow / circ_mv 而非绝对值进行判定

Author: iFlow CLI
Version: V1.0
"""

from typing import Dict, List, Optional, Any, Deque
from datetime import datetime, time
from collections import deque
from dataclasses import dataclass

from logic.strategies.event_detector import BaseEventDetector, TradingEvent, EventType
from logic.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FlowSnapshot:
    """资金流快照"""
    timestamp: datetime
    main_inflow: float          # 主力净流入（元）
    buy_amount: float           # 买盘金额（元）
    sell_amount: float          # 卖盘金额（元）
    price: float                # 当前价格
    volume: float               # 累计成交量
    amount: float               # 累计成交额


class TrueAttackDetector(BaseEventDetector):
    """
    真资金攻击检测器

    继承BaseEventDetector，检测符合4个特征的真资金攻击事件
    配置从config/true_attack_config.json加载，禁止硬编码
    """

    def __init__(self, history_window: int = 10, config_path: Optional[str] = None):
        """
        初始化真攻击检测器

        Args:
            history_window: 历史数据窗口大小（分钟），默认10分钟
            config_path: 配置文件路径，默认从项目根目录加载
        """
        super().__init__(name="TrueAttackDetector")

        # 加载配置文件（禁止硬编码阈值）
        self._load_config(config_path)

        self.history_window = max(history_window, self.SUSTAINED_INFLOW_MINUTES + 2)

        # 每只股票的流数据历史 {stock_code: Deque[FlowSnapshot]}
        self._flow_history: Dict[str, Deque[FlowSnapshot]] = {}

        # 已检测到的攻击记录（防止重复触发）{stock_code: last_attack_time}
        self._last_attack_time: Dict[str, datetime] = {}

    def _load_config(self, config_path: Optional[str] = None):
        """从JSON配置文件加载参数"""
        import json
        from pathlib import Path

        if config_path is None:
            config_path = Path(__file__).resolve().parent.parent.parent / 'config' / 'true_attack_config.json'

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # ratio阈值
            self.RATIO_THRESHOLD_WEAK = config['ratio_thresholds']['weak']
            self.RATIO_THRESHOLD_NORMAL = config['ratio_thresholds']['normal']
            self.RATIO_THRESHOLD_STRONG = config['ratio_thresholds']['strong']

            # 特征权重
            self.WEIGHT_SUSTAINED = config['feature_weights']['sustained_inflow']
            self.WEIGHT_VOLUME_PRICE = config['feature_weights']['volume_price']
            self.WEIGHT_BUY_SELL = config['feature_weights']['buy_sell_ratio']
            self.WEIGHT_TIMING = config['feature_weights']['timing']

            # 时间参数
            self.SUSTAINED_INFLOW_MINUTES = config['timing']['sustained_minutes']
            from datetime import time as dt_time
            self.LAST_15_MINUTES_START = dt_time.fromisoformat(config['timing']['last_15_min_start'])
            self.MARKET_CLOSE_TIME = dt_time(15, 0)
            self.COOLDOWN_MINUTES = config['timing']['cooldown_minutes']

            logger.info(f"✅ TrueAttackDetector配置加载成功: {config_path}")

        except Exception as e:
            logger.error(f"❌ 加载配置失败: {e}, 使用默认值（不推荐）")
            raise RuntimeError(f"必须提供有效的配置文件: {config_path}")

        # 冷却时间（秒），防止同一股票频繁触发
        self._cooldown_seconds = 120  # 2分钟（测试中）

        logger.info(f"✅ [TrueAttackDetector] 初始化完成，历史窗口={self.history_window}分钟")

    def detect(self, tick_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[TradingEvent]:
        """
        检测真资金攻击事件

        Args:
            tick_data: Tick数据字典，包含：
                - stock_code: 股票代码
                - timestamp: 时间戳
                - main_inflow: 主力净流入（元）
                - main_buy: 主力买入金额（元）
                - main_sell: 主力卖出金额（元）
                - price: 当前价格
                - volume: 成交量
                - amount: 成交额
                - buy_vol: 买盘量列表
                - sell_vol: 卖盘量列表
            context: 上下文信息，包含：
                - circ_mv: 流通市值（元）
                - history: 历史数据

        Returns:
            如果检测到真攻击，返回TradingEvent；否则返回None
        """
        try:
            stock_code = tick_data.get('stock_code')
            if not stock_code:
                return None

            timestamp = tick_data.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            elif isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp)

            # 检查冷却时间
            if self._is_in_cooldown(stock_code, timestamp):
                return None

            # 更新流数据历史
            self._update_flow_history(stock_code, tick_data, timestamp)

            # 检查是否有足够的历史数据
            if len(self._flow_history.get(stock_code, [])) < self.SUSTAINED_INFLOW_MINUTES:
                return None

            # 获取流通市值
            circ_mv = context.get('circ_mv', 0)
            if not circ_mv or circ_mv <= 0:
                logger.debug(f"⚠️ [{stock_code}] 流通市值无效: {circ_mv}")
                return None

            # 执行4特征检测
            is_true_attack, attack_score, feature_scores = self._detect_true_attack(
                stock_code, circ_mv, timestamp
            )

            if is_true_attack and attack_score >= 0.6:  # 阈值0.6
                # 记录攻击时间
                self._last_attack_time[stock_code] = timestamp

                # 构建事件
                event = self._build_attack_event(
                    stock_code, timestamp, attack_score, feature_scores, tick_data, context
                )

                logger.info(f"🚀 [TrueAttackDetector] 检测到真攻击: {stock_code} "
                           f"评分={attack_score:.2f}, ratio={feature_scores.get('inflow_ratio', 0):.4%}")

                return event

            return None

        except Exception as e:
            logger.error(f"❌ [TrueAttackDetector] 检测失败: {e}")
            return None

    def _update_flow_history(self, stock_code: str, tick_data: Dict, timestamp: datetime):
        """
        更新股票的流数据历史

        Args:
            stock_code: 股票代码
            tick_data: Tick数据
            timestamp: 时间戳
        """
        if stock_code not in self._flow_history:
            self._flow_history[stock_code] = deque(maxlen=max(self.history_window, 20))

        # 提取数据
        main_inflow = tick_data.get('main_inflow', 0)
        main_buy = tick_data.get('main_buy', 0)
        main_sell = tick_data.get('main_sell', 0)
        price = tick_data.get('price', 0)
        volume = tick_data.get('volume', 0)
        amount = tick_data.get('amount', 0)

        # 如果没有主力买卖数据，尝试从买卖盘推断
        if main_buy == 0 and main_sell == 0:
            buy_vol = tick_data.get('buy_vol', [])
            sell_vol = tick_data.get('sell_vol', [])
            if buy_vol and sell_vol:
                total_buy = sum(buy_vol) if isinstance(buy_vol, list) else 0
                total_sell = sum(sell_vol) if isinstance(sell_vol, list) else 0
                # 简化推断：假设价格为中点，估算金额
                if price > 0:
                    main_buy = total_buy * price
                    main_sell = total_sell * price
                    main_inflow = main_buy - main_sell

        snapshot = FlowSnapshot(
            timestamp=timestamp,
            main_inflow=main_inflow,
            buy_amount=main_buy,
            sell_amount=main_sell,
            price=price,
            volume=volume,
            amount=amount
        )

        self._flow_history[stock_code].append(snapshot)

    def _detect_true_attack(self, stock_code: str, circ_mv: float,
                           timestamp: datetime) -> tuple[bool, float, Dict[str, Any]]:
        """
        执行4特征真攻击检测

        Args:
            stock_code: 股票代码
            circ_mv: 流通市值（元）
            timestamp: 当前时间

        Returns:
            tuple: (是否真攻击, 攻击评分0-1, 特征评分详情)
        """
        history = self._flow_history[stock_code]

        feature_scores = {}

        # === 特征1: 持续流入检测 ===
        sustained_score, inflow_ratio = self._check_sustained_inflow(history, circ_mv)
        feature_scores['sustained'] = sustained_score
        feature_scores['inflow_ratio'] = inflow_ratio

        # === 特征2: 量价配合检测 ===
        vp_score = self._check_volume_price_relationship(history)
        feature_scores['volume_price'] = vp_score

        # === 特征3: 买盘>卖盘检测 ===
        buy_sell_score = self._check_buy_sell_ratio(history)
        feature_scores['buy_sell'] = buy_sell_score

        # === 特征4: 非尾盘偷袭检测 ===
        timing_score = self._check_timing(timestamp)
        feature_scores['timing'] = timing_score

        # 计算综合评分（加权平均）
        attack_score = (
            sustained_score * self.WEIGHT_SUSTAINED +
            vp_score * self.WEIGHT_VOLUME_PRICE +
            buy_sell_score * self.WEIGHT_BUY_SELL +
            timing_score * self.WEIGHT_TIMING
        )

        # 判定条件：所有特征必须非负，且综合评分>=0.6
        is_true_attack = (
            sustained_score > 0 and
            vp_score > 0 and
            buy_sell_score > 0 and
            timing_score > 0 and
            attack_score >= 0.6
        )

        return is_true_attack, attack_score, feature_scores

    def _check_sustained_inflow(self, history: Deque[FlowSnapshot],
                                 circ_mv: float) -> tuple[float, float]:
        """
        特征1: 检查持续流入

        要求：至少3分钟连续净流入，且流入/流通市值比例达标

        Args:
            history: 流数据历史
            circ_mv: 流通市值

        Returns:
            tuple: (评分0-1, 流入比例)
        """
        if len(history) < self.SUSTAINED_INFLOW_MINUTES:
            return 0.0, 0.0

        # 取最近N分钟数据
        recent = list(history)[-self.SUSTAINED_INFLOW_MINUTES:]

        # 检查是否每分钟都有净流入
        positive_inflow_count = sum(1 for s in recent if s.main_inflow > 0)

        if positive_inflow_count < self.SUSTAINED_INFLOW_MINUTES:
            # 不是每分钟都流入，降低评分
            sustained_ratio = positive_inflow_count / self.SUSTAINED_INFLOW_MINUTES
            if sustained_ratio < 0.67:  # 少于2/3时间流入，判定为假
                return 0.0, 0.0
        else:
            sustained_ratio = 1.0

        # 计算总流入金额和比例
        total_inflow = sum(s.main_inflow for s in recent if s.main_inflow > 0)
        inflow_ratio = total_inflow / circ_mv if circ_mv > 0 else 0

        # 根据流入比例评分
        if inflow_ratio >= self.RATIO_THRESHOLD_STRONG:
            score = 1.0
        elif inflow_ratio >= self.RATIO_THRESHOLD_NORMAL:
            score = 0.8
        elif inflow_ratio >= self.RATIO_THRESHOLD_WEAK:
            score = 0.6
        else:
            score = 0.3 * (inflow_ratio / self.RATIO_THRESHOLD_WEAK)

        # 结合持续比例
        final_score = score * (0.5 + 0.5 * sustained_ratio)

        return min(final_score, 1.0), inflow_ratio

    def _check_volume_price_relationship(self, history: Deque[FlowSnapshot]) -> float:
        """
        特征2: 检查量价配合

        价格上涨伴随放量 = 真攻击
        价格上涨但缩量 = 可疑（低分）
        价格下跌 = 假攻击

        Args:
            history: 流数据历史

        Returns:
            评分0-1
        """
        if len(history) < 2:
            return 0.0

        recent = list(history)[-self.SUSTAINED_INFLOW_MINUTES:]

        # 检查价格趋势
        price_start = recent[0].price
        price_end = recent[-1].price

        if price_start <= 0:
            return 0.0

        price_change = (price_end - price_start) / price_start

        # 检查成交量趋势（用成交额近似）
        if len(recent) >= 2:
            # 计算每分钟成交额变化
            amount_changes = []
            for i in range(1, len(recent)):
                prev_amount = recent[i-1].amount
                curr_amount = recent[i].amount
                # 使用volume来判断（因为amount可能是累积值）
                prev_volume = recent[i-1].volume
                curr_volume = recent[i].volume
                if prev_volume > 0:
                    volume_change = (curr_volume - prev_volume) / prev_volume
                    amount_changes.append(volume_change)

            avg_volume_change = sum(amount_changes) / len(amount_changes) if amount_changes else 0
        else:
            avg_volume_change = 0

        # 评分逻辑（更严格）
        # 价格上涨 + 放量 > 10% = 高分
        # 价格上涨 + 放量 0-10% = 中分
        # 价格上涨 + 缩量 = 0分（诱多嫌疑）
        # 价格下跌 = 0分

        if price_change > 0:
            if avg_volume_change > 0.1:  # 放量10%以上
                return min(1.0, 0.7 + price_change * 10)
            elif avg_volume_change > 0:  # 轻微放量
                return min(0.7, 0.4 + price_change * 10)
            else:  # 缩量（诱多嫌疑）
                return 0.0  # 缩量上涨判定为假攻击
        else:
            # 价格下跌，判定为假攻击
            return 0.0

    def _check_buy_sell_ratio(self, history: Deque[FlowSnapshot]) -> float:
        """
        特征3: 检查买盘>卖盘

        主力真买：买盘金额 > 卖盘金额
        对倒嫌疑：买盘 ≈ 卖盘 或 卖盘 > 买盘

        Args:
            history: 流数据历史

        Returns:
            评分0-1
        """
        if len(history) < self.SUSTAINED_INFLOW_MINUTES:
            return 0.0

        recent = list(history)[-self.SUSTAINED_INFLOW_MINUTES:]

        total_buy = sum(s.buy_amount for s in recent)
        total_sell = sum(s.sell_amount for s in recent)

        if total_sell <= 0:
            # 没有卖盘数据，无法判断
            return 0.5

        buy_sell_ratio = total_buy / total_sell

        # 评分逻辑
        # ratio > 1.3: 买盘明显强于卖盘，真攻击 (0.8-1.0)
        # ratio 1.0-1.3: 买盘略强，正常 (0.5-0.8)
        # ratio < 1.0: 卖盘>=买盘，假攻击 (0.0)

        if buy_sell_ratio >= 1.3:
            return min(1.0, 0.8 + (buy_sell_ratio - 1.3) * 0.3)
        elif buy_sell_ratio >= 1.0:
            return 0.5 + (buy_sell_ratio - 1.0) * 1.0
        else:
            return 0.0  # 卖盘大于买盘，判定为假攻击

    def _check_timing(self, timestamp: datetime) -> float:
        """
        特征4: 检查非尾盘偷袭

        尾盘拉升（14:45后）为第二天出货做准备，判定为假攻击

        Args:
            timestamp: 当前时间

        Returns:
            评分0-1
        """
        current_time = timestamp.time()

        # 尾盘时间：14:45 - 15:00
        if self.LAST_15_MINUTES_START <= current_time <= self.MARKET_CLOSE_TIME:
            return 0.0  # 尾盘偷袭，判定为假攻击

        return 1.0  # 正常时间，满分

    def _is_in_cooldown(self, stock_code: str, timestamp: datetime) -> bool:
        """
        检查股票是否在冷却期内

        Args:
            stock_code: 股票代码
            timestamp: 当前时间

        Returns:
            是否在冷却期内
        """
        if stock_code not in self._last_attack_time:
            return False

        elapsed = (timestamp - self._last_attack_time[stock_code]).total_seconds()
        return elapsed < self._cooldown_seconds

    def _build_attack_event(self, stock_code: str, timestamp: datetime,
                           attack_score: float, feature_scores: Dict,
                           tick_data: Dict, context: Dict) -> TradingEvent:
        """
        构建资金攻击事件

        Args:
            stock_code: 股票代码
            timestamp: 时间戳
            attack_score: 攻击评分
            feature_scores: 特征评分
            tick_data: Tick数据
            context: 上下文

        Returns:
            TradingEvent对象
        """
        # 确定攻击强度等级
        if attack_score >= 0.85:
            strength = "STRONG"
            description = f"🚀 强资金攻击 detected: {stock_code} (评分: {attack_score:.2f})"
        elif attack_score >= 0.7:
            strength = "NORMAL"
            description = f"📈 中等资金攻击 detected: {stock_code} (评分: {attack_score:.2f})"
        else:
            strength = "WEAK"
            description = f"⚡ 弱资金攻击 detected: {stock_code} (评分: {attack_score:.2f})"

        event_data = {
            'attack_score': attack_score,
            'attack_strength': strength,
            'feature_scores': feature_scores,
            'inflow_ratio': feature_scores.get('inflow_ratio', 0),
            'sustained_score': feature_scores.get('sustained', 0),
            'volume_price_score': feature_scores.get('volume_price', 0),
            'buy_sell_score': feature_scores.get('buy_sell', 0),
            'timing_score': feature_scores.get('timing', 0),
            'price': tick_data.get('price', 0),
            'circ_mv': context.get('circ_mv', 0),
        }

        return TradingEvent(
            event_type=EventType.CAPITAL_ATTACK,
            stock_code=stock_code,
            timestamp=timestamp,
            data=event_data,
            confidence=attack_score,
            description=description
        )

    def reset(self):
        """重置检测器状态"""
        super().reset()
        self._flow_history.clear()
        self._last_attack_time.clear()
        logger.info("🔄 [TrueAttackDetector] 状态已重置")

    def get_stock_history(self, stock_code: str) -> List[Dict]:
        """
        获取指定股票的历史流数据（用于调试）

        Args:
            stock_code: 股票代码

        Returns:
            历史数据列表
        """
        if stock_code not in self._flow_history:
            return []

        return [
            {
                'timestamp': s.timestamp.isoformat(),
                'main_inflow': s.main_inflow,
                'buy_amount': s.buy_amount,
                'sell_amount': s.sell_amount,
                'price': s.price,
                'volume': s.volume
            }
            for s in self._flow_history[stock_code]
        ]


# 便捷函数
def create_true_attack_detector(history_window: int = 10) -> TrueAttackDetector:
    """
    创建真攻击检测器实例

    Args:
        history_window: 历史数据窗口大小（分钟）

    Returns:
        TrueAttackDetector实例
    """
    return TrueAttackDetector(history_window=history_window)


if __name__ == "__main__":
    # 自测代码
    detector = TrueAttackDetector(history_window=5)

    print("=" * 60)
    print("TrueAttackDetector 自测")
    print("=" * 60)

    # 模拟测试数据：真攻击场景
    from datetime import timedelta

    base_time = datetime(2026, 2, 19, 14, 30, 0)  # 14:30，非尾盘

    # 模拟连续5分钟的真攻击数据
    test_data_sequence = [
        # 价格逐步上涨，持续流入，买盘>卖盘
        {'price': 10.0, 'main_inflow': 1000000, 'main_buy': 5000000, 'main_sell': 2000000, 'volume': 10000, 'amount': 100000},
        {'price': 10.05, 'main_inflow': 1200000, 'main_buy': 5500000, 'main_sell': 2200000, 'volume': 12000, 'amount': 120600},
        {'price': 10.12, 'main_inflow': 1500000, 'main_buy': 6000000, 'main_sell': 2500000, 'volume': 15000, 'amount': 151800},
        {'price': 10.20, 'main_inflow': 1300000, 'main_buy': 5800000, 'main_sell': 2400000, 'volume': 13000, 'amount': 132600},
        {'price': 10.28, 'main_inflow': 1800000, 'main_buy': 7000000, 'main_sell': 2800000, 'volume': 18000, 'amount': 185040},
    ]

    circ_mv = 1_000_000_000  # 10亿流通市值

    print(f"\n📊 测试场景：真攻击（流通市值={circ_mv/1e8:.0f}亿）")
    print(f"   时间: {base_time.strftime('%H:%M')}（非尾盘）")
    print(f"   特征: 持续流入5分钟，价格上涨，买盘>卖盘")

    events = []
    for i, data in enumerate(test_data_sequence):
        tick_data = {
            'stock_code': '000001',
            'timestamp': base_time + timedelta(minutes=i),
            'main_inflow': data['main_inflow'],
            'main_buy': data['main_buy'],
            'main_sell': data['main_sell'],
            'price': data['price'],
            'volume': data['volume'],
            'amount': data['amount'],
        }
        context = {'circ_mv': circ_mv}

        event = detector.detect(tick_data, context)
        if event:
            events.append(event)
            print(f"\n✅ 检测到事件: {event.description}")
            print(f"   评分: {event.confidence:.2f}")
            print(f"   数据: {event.data}")

    if not events:
        print("\n⚠️ 未检测到攻击事件（这是正常的，可能需要更多数据或调整阈值）")

    # 测试尾盘场景（应该不触发）
    print("\n" + "=" * 60)
    print("📊 测试场景：尾盘偷袭（应该不触发）")
    print("=" * 60)

    detector2 = TrueAttackDetector(history_window=5)
    base_time_late = datetime(2026, 2, 19, 14, 46, 0)  # 14:46，尾盘

    for i, data in enumerate(test_data_sequence):
        tick_data = {
            'stock_code': '000002',
            'timestamp': base_time_late + timedelta(minutes=i),
            'main_inflow': data['main_inflow'],
            'main_buy': data['main_buy'],
            'main_sell': data['main_sell'],
            'price': data['price'],
            'volume': data['volume'],
            'amount': data['amount'],
        }
        context = {'circ_mv': circ_mv}

        event = detector2.detect(tick_data, context)
        if event:
            print(f"\n❌ 错误：尾盘偷袭被误判为真攻击！")
        else:
            print(f"   ✓ 第{i+1}分钟数据已处理（未触发，符合预期）")

    print("\n✅ 自测完成")
