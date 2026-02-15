"""
Level-1资金流推断
Source: logic/data_providers/level1_provider.py
Extracted: 1771140137.4132237
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Level-1 资金流推断提供者（基于QMT Tick数据）

从免费Tick数据推断主力资金流向

Author: MyQuantTool Team
Date: 2026-02-12
"""

from datetime import datetime
from typing import Optional

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

from .base import (
    ICapitalFlowProvider,
    CapitalFlowSignal,
    DataNotAvailableError
)
from .dongcai_provider import DongCaiT1Provider
from logic.utils.code_converter import CodeConverter
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class Level1InferenceProvider(ICapitalFlowProvider):
    """
    Level-1 推断提供者（免费方案）

    推断逻辑：
    1. 基础：昨日资金流（东方财富T-1）
    2. 修正：当日买卖压力（QMT Tick）
    3. 修正：价格强度（涨跌幅）
    4. 修正：成交量放大系数

    置信度：0.5-0.6（推断精度中等）

    适用场景：
    - 竞价阶段（09:20-09:25）
    - 盘中实时监控
    - 无Level-2权限时
    """

    def __init__(self):
        if not QMT_AVAILABLE:
            raise ImportError("xtquant未安装，无法使用Level1推断")

        self.dongcai_provider = DongCaiT1Provider()  # 降级数据源
        self._cache = {}
        self._cache_ttl = 10  # Tick缓存10秒
        self._qmt_connected = False  # QMT连接状态
        self._last_connection_check = None  # 上次连接检查时间
        self._tick_validation_warning_count = 0  # Tick验证警告计数器

    def _check_qmt_connection(self) -> bool:
        """
        检查QMT连接状态

        Returns:
            bool: True=连接正常, False=连接失败
        """
        # 如果最近5秒检查过，使用缓存结果
        now = datetime.now()
        if self._last_connection_check:
            age = (now - self._last_connection_check).total_seconds()
            if age < 5 and self._qmt_connected:
                return True

        try:
            # 测试获取一个常见股票的Tick数据
            test_tick = xtdata.get_full_tick(['000001.SZ'])
            
            if test_tick is not None and len(test_tick) > 0:
                self._qmt_connected = True
                self._last_connection_check = now
                logger.debug("✅ QMT连接检查通过")
                return True
            else:
                self._qmt_connected = False
                self._last_connection_check = now
                logger.warning("⚠️ QMT连接检查失败：返回空数据")
                return False

        except Exception as e:
            self._qmt_connected = False
            self._last_connection_check = now
            logger.error(f"❌ QMT连接检查异常: {e}")
            return False

    def get_realtime_flow(self, code: str) -> CapitalFlowSignal:
        """
        推断实时资金流

        Args:
            code: 股票代码（6位）

        Returns:
            CapitalFlowSignal: 推断的资金流数据
        """
        try:
            # 🔥 P0-2: 检查QMT连接状态
            if not self._check_qmt_connection():
                logger.warning(f"⚠️ QMT连接异常，{code} 降级到东方财富T-1数据")
                return self.dongcai_provider.get_realtime_flow(code)

            # 检查缓存
            if code in self._cache:
                cached_signal, cache_time = self._cache[code]
                age = (datetime.now() - cache_time).total_seconds()
                if age < self._cache_ttl:
                    return cached_signal

            # 1. 获取昨日资金流（基础）
            dongcai_signal = self.dongcai_provider.get_realtime_flow(code)

            # 2. 获取当前Tick数据
            code_qmt = CodeConverter.to_qmt(code)
            tick_data = xtdata.get_full_tick([code_qmt])

            if not tick_data or code_qmt not in tick_data:
                logger.warning(f"⚠️ {code} Tick数据获取失败，降级到东方财富")
                return dongcai_signal

            tick = tick_data[code_qmt]

            # 3. 推断当前资金流
            inferred_flow = self._infer_from_tick(tick, dongcai_signal)

            # 4. 构建信号
            signal = CapitalFlowSignal(
                code=code,
                main_net_inflow=inferred_flow['main_net_inflow'],
                super_large_inflow=inferred_flow['super_large_net'],
                large_inflow=inferred_flow['large_net'],
                timestamp=datetime.now().timestamp(),
                confidence=inferred_flow['confidence'],
                source='Level1'
            )

            # 更新缓存
            self._cache[code] = (signal, datetime.now())

            return signal

        except Exception as e:
            logger.warning(f"⚠️ {code} Level1推断失败: {e}，降级到东方财富")
            return self.dongcai_provider.get_realtime_flow(code)

    def _validate_tick_data(self, tick: dict) -> tuple[bool, str]:
        """
        验证Tick数据的完整性和有效性

        Args:
            tick: QMT Tick数据

        Returns:
            tuple: (是否有效, 错误消息)
        """
        required_fields = ['lastPrice', 'lastClose', 'amount', 'buyVol', 'sellVol']

        # 1. 检查必需字段是否存在
        for field in required_fields:
            if field not in tick:
                return False, f"缺少必需字段: {field}"

        # 2. 检查数值类型和范围
        last_price = tick.get('lastPrice', 0)
        last_close = tick.get('lastClose', 0)
        amount = tick.get('amount', 0)
        buy_vol = tick.get('buyVol', [])
        sell_vol = tick.get('sellVol', [])

        # 价格检查：必须为正数且在合理范围内（0.1-10000元）
        if not isinstance(last_price, (int, float)) or last_price <= 0:
            return False, f"lastPrice无效: {last_price}"

        if not isinstance(last_close, (int, float)) or last_close <= 0:
            return False, f"lastClose无效: {last_close}"

        if last_price < 0.1 or last_price > 10000:
            return False, f"lastPrice超出合理范围: {last_price}"

        # 涨跌幅检查：单日涨跌不能超过20%（主板）或30%（科创板/创业板）
        if last_close > 0:
            pct_change = abs((last_price - last_close) / last_close)
            if pct_change > 0.3:
                return False, f"涨跌幅异常: {pct_change:.2%}"

        # 成交额检查：必须为非负数
        if not isinstance(amount, (int, float)) or amount < 0:
            return False, f"amount无效: {amount}"

        # 买卖盘检查：必须是列表且长度≥0
        if not isinstance(buy_vol, list):
            return False, f"buyVol不是列表: {type(buy_vol)}"

        if not isinstance(sell_vol, list):
            return False, f"sellVol不是列表: {type(sell_vol)}"

        # 买卖盘量检查：所有值必须为非负数
        for i, vol in enumerate(buy_vol):
            if not isinstance(vol, (int, float)) or vol < 0:
                return False, f"buyVol[{i}]无效: {vol}"

        for i, vol in enumerate(sell_vol):
            if not isinstance(vol, (int, float)) or vol < 0:
                return False, f"sellVol[{i}]无效: {vol}"

        return True, ""

    def _infer_from_tick(self, tick: dict, dongcai_signal: CapitalFlowSignal) -> dict:
        """
        从Tick数据推断资金流

        核心算法：
        estimated_flow = base_flow * volume_ratio * bid_pressure * price_strength

        Args:
            tick: QMT Tick数据
            dongcai_signal: 昨日资金流（基础值）

        Returns:
            dict: 推断结果
        """
        # 🔥 P0-3: 验证Tick数据
        is_valid, error_msg = self._validate_tick_data(tick)
        if not is_valid:
            self._tick_validation_warning_count += 1  # 只计数，不打印
            return {
                'main_net_inflow': dongcai_signal.main_net_inflow,
                'super_large_net': dongcai_signal.super_large_inflow,
                'large_net': dongcai_signal.large_inflow,
                'confidence': dongcai_signal.confidence * 0.5,  # 降低置信度
                'flow_direction': 'INFLOW' if dongcai_signal.main_net_inflow > 0 else 'OUTFLOW'
            }
        # 提取Tick字段
        last_price = tick.get('lastPrice', 0)
        last_close = tick.get('lastClose', 0)
        amount = tick.get('amount', 0)
        buy_vol = tick.get('buyVol', [0]*5)
        sell_vol = tick.get('sellVol', [0]*5)

        # 1. 成交量放大系数
        yesterday_amount = dongcai_signal.amount if hasattr(dongcai_signal, 'amount') and dongcai_signal.amount else 1
        volume_ratio = amount / yesterday_amount if yesterday_amount > 0 else 1.0
        volume_ratio = min(volume_ratio, 3.0)  # 限制最大3倍

        # 2. 买卖盘压力比
        total_buy = sum(buy_vol) if isinstance(buy_vol, list) else 0
        total_sell = sum(sell_vol) if isinstance(sell_vol, list) else 0

        if total_sell > 0:
            bid_pressure = total_buy / total_sell
        else:
            bid_pressure = 1.0

        # 归一化到 0.5-1.5
        bid_pressure = max(0.5, min(bid_pressure, 1.5))

        # 3. 价格强度
        if last_close > 0:
            price_strength = (last_price - last_close) / last_close
        else:
            price_strength = 0.0

        # 归一化到 -0.1 到 +0.1
        price_strength = max(-0.1, min(price_strength, 0.1))
        price_factor = 1.0 + price_strength * 10  # 转换为 0.0-2.0

        # 4. 综合推断（加权）
        base_flow = dongcai_signal.main_net_inflow

        # 推断公式
        estimated_main_flow = (
            base_flow * 0.4 +                      # 历史基础 40%
            amount * (bid_pressure - 1.0) * 0.3 +  # 买卖压力 30%
            amount * price_strength * 0.3          # 价格强度 30%
        )

        # 5. 计算置信度
        confidence = self._calculate_confidence(
            volume_ratio,
            bid_pressure,
            abs(price_strength),
            dongcai_signal.confidence
        )

        # 6. 按比例分配超大单/大单（简化处理）
        super_large_ratio = 0.6  # 假设超大单占60%
        large_ratio = 0.4

        return {
            'main_net_inflow': estimated_main_flow,
            'super_large_net': estimated_main_flow * super_large_ratio,
            'large_net': estimated_main_flow * large_ratio,
            'confidence': confidence,
            'flow_direction': 'INFLOW' if estimated_main_flow > 0 else 'OUTFLOW'
        }

    def _calculate_confidence(
        self,
        volume_ratio: float,
        bid_pressure: float,
        price_strength: float,
        base_confidence: float
    ) -> float:
        """
        计算推断置信度

        规则：
        - 成交量放大 → 提高置信度
        - 买卖压力极端 → 提高置信度
        - 价格强度明显 → 提高置信度

        Returns:
            float: 0.3-0.7
        """
        confidence = 0.4  # 基础置信度

        # 成交量因子
        if volume_ratio > 2.0:
            confidence += 0.1
        elif volume_ratio > 1.5:
            confidence += 0.05

        # 买卖压力因子
        if bid_pressure > 1.3 or bid_pressure < 0.7:
            confidence += 0.1

        # 价格强度因子
        if price_strength > 0.05:  # 涨幅>5%
            confidence += 0.1

        # 基础数据质量
        confidence *= base_confidence

        return min(confidence, 0.7)  # 上限0.7

    def get_data_freshness(self, code: str) -> int:
        """Tick数据延迟约3秒"""
        return 3

    def get_full_tick(self, code_list):
        """获取全推Tick数据"""
        try:
            qmt_codes = [CodeConverter.to_qmt(c) for c in code_list]
            return xtdata.get_full_tick(qmt_codes)
        except Exception as e:
            logger.error(f"[Level1] get_full_tick error: {e}")
            return {}

    def get_kline_data(self, code_list, period='1d', start_time='', end_time='', count=-1):
        """获取K线数据"""
        try:
            qmt_codes = [CodeConverter.to_qmt(c) for c in code_list]
            return xtdata.get_market_data_ex(
                field_list=[],
                stock_list=qmt_codes,
                period=period,
                start_time=start_time,
                end_time=end_time,
                count=count
            )
        except Exception as e:
            logger.error(f"[Level1] get_kline_data error: {e}")
            return {}

    def get_stock_list_in_sector(self, sector_name):
        """获取板块成分股"""
        try:
            return xtdata.get_stock_list_in_sector(sector_name)
        except Exception as e:
            logger.error(f"[Level1] get_stock_list_in_sector error: {e}")
            return []

    def get_historical_flow(self, code: str, days: int = 30):
        """Level-1不支持历史数据，返回空"""
        return None

    def get_market_data(self, field_list, stock_list, period='1d', start_time='', end_time='', dividend_type='none', fill_data=False):
        """获取市场数据"""
        try:
            qmt_codes = [CodeConverter.to_qmt(c) for c in stock_list]
            return xtdata.get_market_data(
                field_list=field_list,
                stock_list=qmt_codes,
                period=period,
                start_time=start_time,
                end_time=end_time,
                dividend_type=dividend_type,
                fill_data=fill_data
            )
        except Exception as e:
            logger.error(f"[Level1] get_market_data error: {e}")
            return {}

    def get_instrument_detail(self, code):
        """获取合约详情"""
        try:
            qmt_code = CodeConverter.to_qmt(code)
            return xtdata.get_instrument_detail(qmt_code)
        except Exception as e:
            logger.error(f"[Level1] get_instrument_detail error: {e}")
            return {}

    def get_tick_validation_warning_count(self) -> int:
        """获取 Tick 验证警告计数"""
        return self._tick_validation_warning_count

    def reset_tick_validation_warning_count(self):
        """重置 Tick 验证警告计数"""
        self._tick_validation_warning_count = 0

    def download_history_data(self, code, period='1m', count=-1, incrementally=False):
        """下载历史数据"""
        try:
            qmt_code = CodeConverter.to_qmt(code)
            xtdata.download_history_data(qmt_code, period=period, incrementally=incrementally)
            return {'success': True}
        except Exception as e:
            logger.error(f"[Level1] download_history_data error: {e}")
            return {'success': False, 'error': str(e)}

    def is_available(self) -> bool:
        """检查QMT是否可用"""
        if not QMT_AVAILABLE:
            return False

        try:
            # 测试获取一个常见股票
            test_tick = xtdata.get_full_tick(['000001.SZ'])
            return test_tick is not None and len(test_tick) > 0
        except Exception as e:
            logger.error(f"❌ QMT不可用: {e}")
            return False

    def get_provider_name(self) -> str:
        return "Level1Inference"