# -*- coding: utf-8 -*-
"""
统一卖点守门人 (ExitManager) - CTO架构大一统核心组件

【CTO终极真理】所测即所得！实盘和回测必须使用同一套卖点逻辑！
无论是Live实盘引擎还是Scan回测沙盘，都调用这个唯一的ExitManager！

止损法则（Boss亲自审定）：
1. 法则1：Tick级VWAP止损 - 价格跌破实时VWAP 1%立即斩仓！
2. 法则2：高水位动态止盈 - 真龙(>=3000分)赚30%给15%回撤，平民赚10%给6%回撤
3. 法则3：利润回撤30%止盈 - 最大收益回撤超过30%立即退出

Author: AI总监 (CTO架构大一统)
Date: 2026-03-09
Version: V1.0 - 事件驱动型大一统架构
"""

from typing import Dict, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ExitManager:
    """
    统一卖点守门人 - 实盘和回测共享的唯一大脑！
    
    核心接口：
    - on_tick(tick_data) -> {'action': 'hold'|'sell', 'reason': str}
    
    使用方式：
    ```python
    # 初始化（买入时创建）
    exit_mgr = ExitManager(entry_price=10.0, entry_time='20260309', entry_score=3500)
    
    # 每收到一个Tick调用一次
    for tick in ticks:
        result = exit_mgr.on_tick(tick)
        if result['action'] == 'sell':
            print(f"触发卖出: {result['reason']}")
            break
    ```
    """
    
    # ==================== 阈值常量（SSOT原则） ====================
    VWAP_BREAK_THRESHOLD = 0.99      # VWAP止损阈值：跌破1%斩仓
    
    TRUE_DRAGON_SCORE = 3000.0       # 真龙分数线：>=3000分
    TRUE_DRAGON_MIN_PROFIT = 0.30    # 真龙：至少赚30%才启用追踪止盈
    TRUE_DRAGON_TRAILING = 0.85      # 真龙：最高点回撤15%触发卖出
    
    COMMON_MIN_PROFIT = 0.10         # 平民：至少赚10%才启用追踪止盈
    COMMON_TRAILING = 0.94           # 平民：最高点回撤6%触发卖出
    COMMON_FLOOR = 1.02              # 平民：保底线至少2%盈利
    
    PROFIT_PULLBACK_THRESHOLD = 0.30 # 利润回撤阈值：回撤30%触发卖出
    PROFIT_MIN_FOR_PULLBACK = 0.15   # 启用利润回撤止盈的最低盈利：15%
    
    def __init__(
        self,
        entry_price: float,
        entry_time: str,
        entry_score: float = 0.0,
        stock_code: str = ""
    ):
        """
        初始化卖点守门人
        
        Args:
            entry_price: 买入价格
            entry_time: 买入时间（格式：YYYYMMDD 或 YYYYMMDDHHMMSS）
            entry_score: 入场时的打分（用于区分真龙/平民）
            stock_code: 股票代码（用于日志）
        """
        self.entry_price = entry_price
        self.entry_time = str(entry_time)[:8]  # 只保留日期部分
        self.entry_score = entry_score
        self.stock_code = stock_code
        
        # 状态跟踪
        self.max_price = entry_price          # 持仓期间最高价
        self.current_price = entry_price      # 当前价格
        self.current_day = self.entry_time    # 当前日期（用于跨日重置）
        
        # 累计数据（用于计算VWAP）
        self.daily_amount = 0.0    # 今日累计成交额（元）
        self.daily_volume = 0.0    # 今日累计成交量（股）
        self.current_vwap = entry_price  # 当前VWAP
        
        # 卖出状态
        self.has_sold = False
        self.exit_reason = ""
        self.exit_price = None
        self.exit_time = None
        
        logger.debug(f"[ExitManager] 初始化: {stock_code} @ {entry_price:.2f}, 分数={entry_score:.0f}")
    
    def on_tick(self, tick_data: Dict) -> Dict:
        """
        统一的卖点判定引擎！无论是 Live 还是 Scan，都喂 Tick 给这个函数。
        
        Args:
            tick_data: Tick数据字典，必须包含：
                - 'price' 或 'lastPrice': 当前价格
                - 'amount' 或 'tick_amount': 成交额（累计或增量）
                - 'volume' 或 'tick_volume': 成交量（累计或增量）
                - 'time' 或 'timetag': 时间戳
                
        Returns:
            {
                'action': 'hold' | 'sell',
                'reason': str,
                'price': float,      # 当前价格
                'vwap': float,       # 当前VWAP
                'max_profit': float, # 最大收益率
                'curr_profit': float # 当前收益率
            }
        """
        if self.has_sold:
            return self._build_result('hold', '已卖出')
        
        # 1. 提取标准化数据
        price = float(tick_data.get('price', tick_data.get('lastPrice', 0)))
        amount = float(tick_data.get('amount', tick_data.get('tick_amount', 0)))
        volume = float(tick_data.get('volume', tick_data.get('tick_volume', 0)))
        tick_time = str(tick_data.get('time', tick_data.get('timetag', '')))
        
        if price <= 0:
            return self._build_result('hold', '价格无效')
        
        # 2. 更新当前价格和最高价
        self.current_price = price
        if price > self.max_price:
            self.max_price = price
        
        # 3. 跨日重置累计数据
        tick_day = tick_time[:8] if len(tick_time) >= 8 else self.current_day
        if tick_day != self.current_day:
            self.daily_amount = 0.0
            self.daily_volume = 0.0
            self.current_day = tick_day
            logger.debug(f"[ExitManager] {self.stock_code} 跨日重置VWAP基准: {tick_day}")
        
        # 【CTO修复】QMT底层送过来的 amount 和 volume 本身就是全天累计绝对值，无需任何增量运算！
        self.daily_amount = amount
        self.daily_volume = volume
        
        # 5. 计算实时VWAP
        if self.daily_volume > 0:
            vwap = self.daily_amount / self.daily_volume
            # 【量纲校验】VWAP应该在价格的合理范围内
            if not (price * 0.5 <= vwap <= price * 2.0):
                # 可能是手/股量纲问题，尝试修正
                vwap = self.daily_amount / (self.daily_volume * 100)
                if not (price * 0.5 <= vwap <= price * 2.0):
                    # 还是异常，使用上一帧VWAP
                    vwap = self.current_vwap
        else:
            vwap = self.current_vwap
        
        self.current_vwap = vwap
        
        # 6. 计算收益率
        max_profit = (self.max_price - self.entry_price) / self.entry_price if self.entry_price > 0 else 0
        curr_profit = (price - self.entry_price) / self.entry_price if self.entry_price > 0 else 0
        
        # ==================== 统一防守法则 ====================
        
        # 法则1：Tick级VWAP止损（核心！）
        # 价格跌破实时VWAP 1%立即斩仓！
        if price < vwap * self.VWAP_BREAK_THRESHOLD:
            return self._trigger_sell(
                f'VWAP止损(价{price:.2f}<VWAP{vwap:.2f}*0.99)',
                price, tick_time
            )
        
        # 法则2：高水位动态止盈
        # 真龙(>=3000分)：赚30%给15%回撤
        # 平民：赚10%给6%回撤
        if self.entry_score >= self.TRUE_DRAGON_SCORE:
            # 真龙策略
            if max_profit > self.TRUE_DRAGON_MIN_PROFIT:
                trailing_stop = self.max_price * self.TRUE_DRAGON_TRAILING
                if price < trailing_stop:
                    return self._trigger_sell(
                        f'真龙高位止盈(最高{max_profit*100:.1f}%->当前{curr_profit*100:.1f}%)',
                        price, tick_time
                    )
        else:
            # 平民策略
            if max_profit > self.COMMON_MIN_PROFIT:
                trailing_stop = max(self.max_price * self.COMMON_TRAILING, self.entry_price * self.COMMON_FLOOR)
                if price < trailing_stop:
                    return self._trigger_sell(
                        f'平民高位止盈(最高{max_profit*100:.1f}%->当前{curr_profit*100:.1f}%)',
                        price, tick_time
                    )
        
        # 法则3：利润回撤30%止盈
        if max_profit > self.PROFIT_MIN_FOR_PULLBACK:
            if max_profit > 0 and (max_profit - curr_profit) / max_profit > self.PROFIT_PULLBACK_THRESHOLD:
                return self._trigger_sell(
                    f'利润回撤止盈(回撤{(max_profit-curr_profit)/max_profit*100:.0f}%)',
                    price, tick_time
                )
        
        # 持有
        return self._build_result('hold', '')
    
    def _trigger_sell(self, reason: str, price: float, time: str) -> Dict:
        """触发卖出"""
        self.has_sold = True
        self.exit_reason = reason
        self.exit_price = price
        self.exit_time = time
        
        logger.info(f"🔴 [ExitManager] {self.stock_code} 触发卖出: {reason} @ {price:.2f}")
        
        return self._build_result('sell', reason)
    
    def _build_result(self, action: str, reason: str) -> Dict:
        """构建返回结果"""
        max_profit = (self.max_price - self.entry_price) / self.entry_price if self.entry_price > 0 else 0
        curr_profit = (self.current_price - self.entry_price) / self.entry_price if self.entry_price > 0 else 0
        
        return {
            'action': action,
            'reason': reason,
            'price': self.current_price,
            'vwap': self.current_vwap,
            'max_profit': max_profit,
            'curr_profit': curr_profit,
            'exit_price': self.exit_price,
            'exit_reason': self.exit_reason
        }
    
    def get_state(self) -> Dict:
        """获取当前状态（用于调试和持久化）"""
        return {
            'stock_code': self.stock_code,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time,
            'entry_score': self.entry_score,
            'max_price': self.max_price,
            'current_price': self.current_price,
            'current_vwap': self.current_vwap,
            'has_sold': self.has_sold,
            'exit_reason': self.exit_reason,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time
        }


# ==================== 单元测试 ====================

def test_exit_manager():
    """单元测试：ExitManager止损逻辑"""
    print("\n" + "=" * 60)
    print("📊 ExitManager 单元测试")
    print("=" * 60)
    
    # 测试1：VWAP止损
    print("\n[Test 1] VWAP止损测试")
    mgr = ExitManager(entry_price=10.0, entry_time='20260309', entry_score=2000, stock_code='TEST1')
    
    # 模拟Tick数据
    ticks = [
        {'price': 10.0, 'amount': 100000, 'volume': 10000, 'time': '20260309093000'},
        {'price': 10.2, 'amount': 200000, 'volume': 20000, 'time': '20260309093100'},
        {'price': 10.1, 'amount': 300000, 'volume': 30000, 'time': '20260309093200'},
        {'price': 9.9, 'amount': 400000, 'volume': 40000, 'time': '20260309093300'},  # VWAP≈10.0，跌破
    ]
    
    for tick in ticks:
        result = mgr.on_tick(tick)
        print(f"  {tick['time'][-6:]} 价格={tick['price']:.2f} VWAP={result['vwap']:.2f} 动作={result['action']}")
        if result['action'] == 'sell':
            print(f"  ✅ VWAP止损触发: {result['reason']}")
            break
    
    # 测试2：真龙高水位止盈
    print("\n[Test 2] 真龙高水位止盈测试")
    mgr2 = ExitManager(entry_price=10.0, entry_time='20260309', entry_score=3500, stock_code='TEST2')
    
    ticks2 = [
        {'price': 10.0, 'amount': 100000, 'volume': 10000, 'time': '20260309093000'},
        {'price': 12.0, 'amount': 200000, 'volume': 20000, 'time': '20260309093500'},  # 涨20%
        {'price': 13.5, 'amount': 300000, 'volume': 30000, 'time': '20260309094000'},  # 涨35%，触发追踪
        {'price': 11.5, 'amount': 400000, 'volume': 40000, 'time': '20260309094500'},  # 回撤到15%
    ]
    
    for tick in ticks2:
        result = mgr2.on_tick(tick)
        print(f"  {tick['time'][-6:]} 价格={tick['price']:.2f} 最高收益={result['max_profit']*100:.1f}% 动作={result['action']}")
        if result['action'] == 'sell':
            print(f"  ✅ 真龙止盈触发: {result['reason']}")
            break
    
    # 测试3：平民高水位止盈
    print("\n[Test 3] 平民高水位止盈测试")
    mgr3 = ExitManager(entry_price=10.0, entry_time='20260309', entry_score=1500, stock_code='TEST3')
    
    ticks3 = [
        {'price': 10.0, 'amount': 100000, 'volume': 10000, 'time': '20260309093000'},
        {'price': 11.2, 'amount': 200000, 'volume': 20000, 'time': '20260309093500'},  # 涨12%，触发追踪
        {'price': 10.5, 'amount': 300000, 'volume': 30000, 'time': '20260309094000'},  # 回撤到5%
    ]
    
    for tick in ticks3:
        result = mgr3.on_tick(tick)
        print(f"  {tick['time'][-6:]} 价格={tick['price']:.2f} 最高收益={result['max_profit']*100:.1f}% 动作={result['action']}")
        if result['action'] == 'sell':
            print(f"  ✅ 平民止盈触发: {result['reason']}")
            break
    
    print("\n" + "=" * 60)
    print("✅ ExitManager 单元测试完成")
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_exit_manager()
