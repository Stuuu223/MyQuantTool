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
    
    # 【CTO I-1】source白名单（已知所有QMT来源=手，需×100）
    _KNOWN_HAND_SOURCES = frozenset({
        'full_tick', 'subscribe_quote', 'daily_kline',
        'tick_kline', 'live_tick', 'tick_history'
    })
    
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
        
        if source in QMTNormalizer._KNOWN_HAND_SOURCES:
            return float(raw_volume * 100)  # 手 → 股
        
        # 【CTO I-1】未知来源：白盒告警，原样返回（不静默处理！）
        logger.warning(
            f"[QMTNormalizer] normalize_volume: 未知source='{source}'，"
            f"raw_volume={raw_volume}，原样返回！请检查调用方！"
        )
        return float(raw_volume)
    
    @staticmethod
    def normalize_float_shares(raw_float: float, price: float = 0.0) -> float:
        """
        将QMT的流通股本统一洗为"股"
        
        【CTO I-3修正】实测结论：
        - QMT V9.x实测返回【股】（2026-03-17实测000001.SZ≈194亿）
        - 但历史上曾返回【万股】，保留自适应逻辑以防接口回退
        
        判断逻辑（两级判断）：
        1. 如果 raw_float > 1e8，直接判定为"股"（覆盖99%场景）
        2. 否则判定为"万股"，需要×10000升维
           - 升维后检查市值是否在合理范围（1亿~5万亿）
        
        Args:
            raw_float: QMT get_instrument_detail 返回的 FloatVolume 原始值
            price: 当前价格（用于市值合理性检查），可选
        
        Returns:
            float: 统一为"股"单位的流通股本
        """
        if raw_float <= 0:
            return 0.0
        
        # 第一级判断：大数值直接判定为"股"
        # A股流通股本 > 1亿股的股票占99%以上
        if raw_float > 1e8:  # 1亿
            return raw_float
        
        # 第二级判断：判定为"万股"，执行升维
        upgraded = raw_float * 10000
        
        # 【CTO I-3】升维后市值合理性检查
        if price > 0:
            est_market_cap = upgraded * price
            if est_market_cap < 1e8:  # 升维后市值<1亿？异常！
                logger.error(
                    f"[QMTNormalizer] 升维后市值异常！raw={raw_float:,.0f}, "
                    f"×10000后={upgraded:,.0f}股, ×price={price:.2f}后"
                    f"市值={est_market_cap:,.0f}元 < 1亿，疑似数据源异常，请人工核查！"
                )
                return float(raw_float)  # 拒绝升维，原样返回
        
        # 【白盒可观测】每次升维必须打WARNING日志
        logger.warning(
            f"[QMTNormalizer] FloatVolume升维触发: raw={raw_float:,.0f}, "
            f"price={price:.2f}, 执行×10000升维 → {upgraded:,.0f}股"
        )
        
        return float(upgraded)
    
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
