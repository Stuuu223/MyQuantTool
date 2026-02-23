"""
🧮 算法数学库 - V8.5 修复版本

核心功能：
1. 标准竞价抢筹度计算器（修复 6900% BUG）
2. 量比计算器
3. 换手率计算器
4. 封单金额计算器

设计原则：
- 强制对齐分子分母的维度
- 采用业界标准的定义
- 防止异常值复现
"""

from typing import Optional
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_true_auction_aggression(auction_vol: float, 
                                     prev_day_vol: Optional[float] = None,
                                     circulating_share_capital: Optional[float] = None,
                                     is_new_stock: bool = False) -> float:
    """
    终极竞价抢筹度计算器 (修复 6900% BUG)
    
    定义：竞价成交量 / 昨日全天成交量
    单位：必须统统转换为【手】(Lots)
    
    Args:
        auction_vol: 竞价成交量（手数，已经过 DataSanitizer 清洗）
        prev_day_vol: 昨日全天成交量（手数）
        circulating_share_capital: 流通股本（股数）
        is_new_stock: 是否为新股
    
    Returns:
        float: 竞价抢筹度（百分比）
    
    正常范围：
    - 5% - 10%：正常抢筹
    - 10% - 20%：强势抢筹
    - 20% - 50%：妖股级别
    - > 50%：极端抢筹（通常是新股首日）
    """
    # 1. 安全性检查
    if not auction_vol or auction_vol == 0:
        return 0.0
    
    # 2. 如果没有昨日量，使用兜底逻辑
    if not prev_day_vol or prev_day_vol == 0:
        if circulating_share_capital and circulating_share_capital > 0:
            # 流通盘(股) -> 流通盘(手)
            cap_lots = circulating_share_capital / 100
            # 假设基准量为流通盘的 1%（老股）或 5%（新股）
            fallback_ratio = 0.05 if is_new_stock else 0.01
            fallback_vol = cap_lots * fallback_ratio
            logger.warning(f"使用兜底逻辑计算抢筹度：流通盘{cap_lots:.0f}手，基准量{fallback_vol:.0f}手")
            return round((auction_vol / fallback_vol) * 100, 2)
        else:
            logger.warning(f"无法计算抢筹度：缺少昨日成交量和流通盘数据")
            return 0.0
    
    # 3. 维度对齐检查
    # 计算初步比值
    ratio = auction_vol / prev_day_vol
    
    # 【核心修复逻辑】：检测异常值
    # 如果比值 > 10（即 1000%），说明分母可能有问题：
    # - 可能是单位错了（股 vs 手）
    # - 可能是分钟均量而不是全天量
    # - 可能是数据异常
    
    if ratio > 10:
        logger.warning(f"检测到异常抢筹度比值：{ratio:.2f}，竞价量{auction_vol:.0f}手，昨日量{prev_day_vol:.0f}手")
        
        # 尝试修正：假设分母小了 100 倍（股转手）
        corrected_ratio = ratio / 100
        
        # 如果修正后的比值在合理范围内（< 5 即 500%），使用修正值
        if corrected_ratio < 5:
            logger.info(f"应用单位修正：抢筹度从 {ratio*100:.2f}% 修正为 {corrected_ratio*100:.2f}%")
            ratio = corrected_ratio
        else:
            # 如果修正后仍然异常，尝试其他修正方式
            # 可能是分母是分钟均量，需要乘以 240
            corrected_ratio_240 = ratio / 240
            if corrected_ratio_240 < 5:
                logger.info(f"应用分钟量修正：抢筹度从 {ratio*100:.2f}% 修正为 {corrected_ratio_240*100:.2f}%")
                ratio = corrected_ratio_240
            else:
                # 所有修正都失败，强制归零
                logger.error(f"抢筹度计算失败：所有修正方式都失败，强制归零")
                return 0.0
    
    # 4. 计算最终抢筹度
    real_ratio = ratio * 100
    
    # 5. 再次数据清洗（防止 6900% 复现）
    if real_ratio > 1000:
        logger.error(f"抢筹度仍然异常：{real_ratio:.2f}%，强制归零")
        return 0.0
    
    # 6. 记录日志
    if real_ratio > 20:
        logger.info(f"强势抢筹：{real_ratio:.2f}%，竞价量{auction_vol:.0f}手，昨日量{prev_day_vol:.0f}手")
    
    return round(real_ratio, 2)


def calculate_volume_ratio(current_vol: float, 
                           avg_vol: float,
                           period: int = 5) -> float:
    """
    标准量比计算器
    
    定义：当前成交量 / 历史平均成交量
    单位：必须统统转换为【手】(Lots)
    
    Args:
        current_vol: 当前成交量（手数）
        avg_vol: 历史平均成交量（手数）
        period: 平均周期（默认5天）
    
    Returns:
        float: 量比
    
    正常范围：
    - < 0.5：缩量
    - 0.5 - 1.5：正常
    - 1.5 - 3.0：温和放量
    - 3.0 - 5.0：放量
    - > 5.0：攻击性放量
    """
    # 1. 安全性检查
    if not current_vol or current_vol == 0:
        return 1.0
    
    if not avg_vol or avg_vol == 0:
        logger.warning("量比计算失败：平均成交量为0")
        return 1.0
    
    # 2. 异常值检测
    # 如果平均成交量太小（< 1000手），可能是停牌或数据异常
    if avg_vol < 1000:
        logger.warning(f"平均成交量过小：{avg_vol:.0f}手，量比设为1")
        return 1.0
    
    # 3. 计算量比
    ratio = current_vol / avg_vol
    
    # 4. 异常值清洗
    if ratio > 100:
        logger.warning(f"量比异常：{ratio:.2f}，强制修正为100")
        ratio = 100.0
    
    return round(ratio, 2)


def calculate_turnover_rate(volume: float, 
                           circulating_share_capital: float) -> float:
    """
    标准换手率计算器
    
    定义：成交量 / 流通股本
    单位：成交量【手】，流通股本【股】
    
    Args:
        volume: 成交量（手数）
        circulating_share_capital: 流通股本（股数）
    
    Returns:
        float: 换手率（百分比）
    
    正常范围：
    - < 2%：低换手
    - 2% - 10%：正常换手
    - 10% - 20%：高换手
    - 20% - 50%：极高换手
    - > 50%：死亡换手（通常是新股或妖股）
    """
    # 1. 安全性检查
    if not volume or volume == 0:
        return 0.0
    
    if not circulating_share_capital or circulating_share_capital == 0:
        logger.warning("换手率计算失败：流通股本为0")
        return 0.0
    
    # 2. 计算换手率
    # 成交量（手）* 100（股/手） / 流通股本（股）
    turnover = (volume * 100) / circulating_share_capital * 100
    
    # 3. 异常值清洗
    if turnover > 200:
        logger.warning(f"换手率异常：{turnover:.2f}%，强制修正为200%")
        turnover = 200.0
    
    return round(turnover, 2)


def calculate_seal_amount(bid1_volume: float, 
                         price: float,
                         source_type: str = 'easyquotation') -> float:
    """
    标准封单金额计算器
    
    定义：买一量（手）× 100（股/手）× 价格 / 10000（转换为万）
    
    Args:
        bid1_volume: 买一量（手数）
        price: 当前价格
        source_type: 数据源类型
    
    Returns:
        float: 封单金额（万元）
    """
    # 1. 安全性检查
    if not bid1_volume or bid1_volume == 0:
        return 0.0
    
    if not price or price == 0:
        return 0.0
    
    # 2. 计算封单金额
    # Easyquotation 的 bid1_volume 已经是手数
    seal_amount = bid1_volume * 100 * price / 10000
    
    # 3. 异常值清洗
    if seal_amount > 1_000_000:  # > 1000亿
        logger.warning(f"封单金额异常：{seal_amount:.2f}万，尝试修正")
        seal_amount = seal_amount / 100
    
    return round(seal_amount, 2)


def calculate_auction_amount(auction_volume: float, 
                            price: float) -> float:
    """
    标准竞价金额计算器
    
    定义：竞价成交量（手）× 100（股/手）× 价格 / 10000（转换为万）
    
    Args:
        auction_volume: 竞价成交量（手数）
        price: 当前价格
    
    Returns:
        float: 竞价金额（万元）
    """
    # 1. 安全性检查
    if not auction_volume or auction_volume == 0:
        return 0.0
    
    if not price or price == 0:
        return 0.0
    
    # 2. 计算竞价金额
    auction_amount = auction_volume * 100 * price / 10000
    
    return round(auction_amount, 2)