"""
【CTO V188 白盒防腐层】QMT数据单位归一化器

设计原则：
1. 所有量纲转换必须且只能在这里发生
2. 每次升维触发必须打WARNING日志（白盒可观测）
3. 禁止业务代码直接写 *100 或 *10000

使用方式：
    from logic.data_providers.qmt_normalizer import QMTNormalizer
    
    clean_volume = QMTNormalizer.normalize_volume(raw_volume, 'live_tick')
    clean_float = QMTNormalizer.normalize_float_shares(raw_float, pre_close)
"""
import logging
from typing import Literal

logger = logging.getLogger(__name__)


class QMTNormalizer:
    """
    QMT数据单位归一化器（静态类）
    
    职责：将QMT各数据源的单位统一为项目标准单位
    - volume → 股
    - float_volume → 股
    """
    
    # =====================================================
    # 量纲真理表（唯一真理源）
    # =====================================================
    # get_instrument_detail FloatVolume → 万股（原始）
    # get_full_tick volume → 手
    # get_local_data(period='1d') volume → 手
    # get_local_data(period='tick') volume → 手
    # subscribe_quote volume → 手
    # =====================================================
    
    @staticmethod
    def normalize_volume(raw_volume: float, source: str) -> float:
        """
        将QMT的成交量统一洗为"股"
        
        Args:
            raw_volume: QMT原始成交量值
            source: 数据来源，可选值：
                - 'live_tick': 实盘Tick订阅/快照（单位=手）
                - 'daily_kline': 日K线（单位=手）
                - 'tick_history': 历史Tick（单位=手）
        
        Returns:
            float: 统一为"股"单位的成交量
        """
        if raw_volume <= 0:
            return 0.0
        
        # 所有QMT数据源的volume单位都是"手"
        # 需要乘100转换为"股"
        clean_volume = raw_volume * 100
        
        return clean_volume
    
    @staticmethod
    def normalize_float_shares(raw_float: float, price: float = 0.0) -> float:
        """
        将QMT的流通股本统一洗为"股"
        
        QMT的get_instrument_detail返回的FloatVolume单位可能是：
        - 万股（大多数情况，如平安银行≈192万）
        - 股（少数情况）
        
        判断逻辑（两级判断）：
        1. 如果 raw_float > 1e8，直接判定为"股"（覆盖99%场景）
        2. 否则用市值法兜底：est_market_cap = raw_float * price
           - 如果 est_market_cap 在 [2亿, 5万亿] 区间，判定为"股"
           - 否则判定为"万股"，需要×10000升维
        
        Args:
            raw_float: QMT get_instrument_detail 返回的 FloatVolume 原始值
            price: 当前价格（用于市值推断），可选
        
        Returns:
            float: 统一为"股"单位的流通股本
        """
        if raw_float <= 0:
            return 0.0
        
        # 第一级判断：大数值直接判定为"股"
        # A股流通股本 > 1亿股的股票占99%以上
        if raw_float > 1e8:  # 1亿
            return raw_float
        
        # 第二级判断：市值推断法
        if price > 0:
            est_market_cap = raw_float * price
            
            # A股流通市值范围：2亿 ~ 5万亿
            # 如果市值在这个区间，说明单位已经是"股"
            if 2e8 <= est_market_cap <= 5e12:
                return raw_float
        
        # 市值不在合理区间，判定为"万股"，需要升维
        # 【白盒可观测】每次升维必须打WARNING日志
        logger.warning(
            f"[QMTNormalizer] FloatVolume升维触发: raw={raw_float:,.0f}, "
            f"price={price:.2f}, est_cap={raw_float * price:,.0f}元, "
            f"判定单位=万股, 执行×10000升维"
        )
        
        return raw_float * 10000
    
    @staticmethod
    def calculate_turnover_rate(
        volume_raw: float, 
        float_volume_raw: float, 
        price: float,
        volume_source: str = 'live_tick'
    ) -> float:
        """
        计算换手率（统一入口）
        
        Args:
            volume_raw: QMT原始成交量
            float_volume_raw: QMT原始流通股本
            price: 当前价格
            volume_source: 成交量数据来源
        
        Returns:
            float: 换手率百分比（如 5.5 表示 5.5%）
        """
        clean_volume = QMTNormalizer.normalize_volume(volume_raw, volume_source)
        clean_float = QMTNormalizer.normalize_float_shares(float_volume_raw, price)
        
        if clean_float <= 0:
            return 0.0
        
        turnover_rate = (clean_volume / clean_float) * 100.0
        return turnover_rate
    
    @staticmethod
    def calculate_volume_ratio(
        today_volume_raw: float,
        avg_volume_5d_raw: float,
        volume_source: str = 'live_tick'
    ) -> float:
        """
        计算量比（无量纲，单位自消除）
        
        注意：量比公式 today_volume / avg_volume_5d
        只要分子分母单位一致，量纲自然消除，无需额外转换
        
        Args:
            today_volume_raw: 今日成交量（QMT原始值）
            avg_volume_5d_raw: 5日平均成交量（QMT原始值）
            volume_source: 数据来源
        
        Returns:
            float: 量比倍数（如 2.5 表示 2.5倍）
        """
        if avg_volume_5d_raw <= 0:
            return 0.0
        
        # 量纲自消除：分子分母单位相同（都是手或都是股）
        # 所以不需要归一化，直接计算
        volume_ratio = today_volume_raw / avg_volume_5d_raw
        return volume_ratio


# 便捷函数
def normalize_volume(raw_volume: float, source: str = 'live_tick') -> float:
    """便捷函数：归一化成交量"""
    return QMTNormalizer.normalize_volume(raw_volume, source)


def normalize_float_shares(raw_float: float, price: float = 0.0) -> float:
    """便捷函数：归一化流通股本"""
    return QMTNormalizer.normalize_float_shares(raw_float, price)
