# logic/execution/trade_gatekeeper.py
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TradeGatekeeper:
    def __init__(self, max_spread_ratio: float = 0.02):
        """
        微观盘口防线 - 发单前的物理检查闸门
        
        核心宗旨：Fail-Close（默认拒绝）
        绝不允许任何带有毒性微观结构的订单穿透到交易所
        
        :param max_spread_ratio: 买卖一档最大容忍价差。超过此阈值意味着盘口极度稀疏。
        """
        self.is_active = True
        self.max_spread_ratio = max_spread_ratio
        logger.info(f"[OK] TradeGatekeeper 物理防线启动 | 最大滑点阈值: {self.max_spread_ratio:.1%} (Fail-Close)")

    def check_micro_structure(self, stock_code: str, tick_data: Dict[str, Any]) -> bool:
        """
        微观防线：实盘发单前的最后一次物理盘口查验。
        
        拦截条件：
        1. 涨跌停板（买不进/卖不出）
        2. 盘口极度稀疏（滑点成本过高）
        3. 数据异常
        """
        if not self.is_active:
            logger.error(f"[FATAL] {stock_code} Gatekeeper已关闭，防线失效，拒绝开仓！")
            return False

        try:
            last_price = float(tick_data.get('lastPrice', 0.0))
            limit_up = float(tick_data.get('limitUpPrice', 0.0))
            limit_down = float(tick_data.get('limitDownPrice', 0.0))
            
            if last_price <= 0:
                logger.warning(f"[拦截] {stock_code} 现价数据异常 ({last_price})，拒绝发单！")
                return False

            # 防线 1：封板物理隔离 (买不进/卖不出)
            if limit_up > 0 and last_price >= limit_up:
                logger.warning(f"[拦截] {stock_code} 已触及涨停 ({last_price})，市价单极易成废单，拒绝开火！")
                return False
                
            if limit_down > 0 and last_price <= limit_down:
                logger.warning(f"[拦截] {stock_code} 已触及跌停 ({last_price})，流动性丧失，拒绝开火！")
                return False

            # 防线 2：盘口黑洞防御
            ask1 = float(tick_data.get('askPrice1', 0.0))
            bid1 = float(tick_data.get('bidPrice1', 0.0))
            if ask1 > 0 and bid1 > 0:
                spread_ratio = (ask1 - bid1) / bid1
                if spread_ratio > self.max_spread_ratio:
                    logger.warning(f"[拦截] {stock_code} 盘口极度稀疏 (价差率 {spread_ratio:.2%})，一票否决！")
                    return False

            # 所有防线均未触发，放行
            logger.debug(f"[OK] {stock_code} 微观防线检查通过")
            return True

        except Exception as e:
            logger.error(f"[FATAL] {stock_code} 微观防线计算崩溃: {e}，触发 Fail-Close！")
            return False

    def check_capital_flow(self, stock_code: str, volume_ratio: float, tick_data: Dict[str, Any]) -> bool:
        """资金流检查（扩展接口）"""
        # TODO: 实现更复杂的资金流分析
        return True

    def check_sector_resonance(self, stock_code: str, tick_data: Dict[str, Any]) -> bool:
        """板块共振检查（扩展接口）"""
        # TODO: 实现板块共振分析
        return True
