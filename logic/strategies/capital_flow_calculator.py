"""
资金流计算器 - CTO双模自适应版 (VIP/L1降级)

功能：
- 自动嗅探QMT权限级别 (L2 VIP / L1 基础)
- L2模式：逐笔成交精确计算
- L1模式：行为学推演算法
  * 价格推力背离检测
  * 内外盘Delta逼近
  * 五档盘口压迫系数

CTO加固要点:
- 策略模式自动切换
- L1历史快照缓存
- 量价异常行为捕捉
- 无L2时不崩溃降级

Author: AI总监 (CTO双模架构)
Date: 2026-02-24
Version: Phase 21 - 双模自适应
"""
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import time
import logging
import threading

try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging as log_mod
    logger = log_mod.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = log_mod.StreamHandler()
    handler.setFormatter(log_mod.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(handler)


@dataclass
class SnapShotData:
    """L1快照数据结构"""
    stock_code: str
    timestamp: datetime
    price: float
    volume: int
    amount: float
    bid1: float = 0.0
    ask1: float = 0.0
    bid_vol1: int = 0
    ask_vol1: int = 0
    change_pct: float = 0.0


@dataclass
class FlowResult:
    """资金流计算结果"""
    stock_code: str
    mode: str  # 'L2' or 'L1'
    inflow: float = 0.0
    outflow: float = 0.0
    net_flow: float = 0.0
    flow_score: float = 50.0  # 0-100
    price_thrust: float = 0.0  # 价格推力系数
    pressure_ratio: float = 1.0  # 盘口压迫系数
    is_trap: bool = False
    trap_type: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime('%H:%M:%S'))


class CapitalFlowCalculator:
    """
    资金流计算器 - 双模自适应
    
    CTO架构：
    - 启动时自动嗅探QMT权限
    - L2可用时：逐笔精确计算
    - L2不可用时：无缝降级到L1行为学推演
    """
    
    # 模式常量
    MODE_L2 = 'L2'  # VIP精确模式
    MODE_L1 = 'L1'  # 降级推演模式
    
    def __init__(self, max_history: int = 20):
        """
        初始化计算器
        
        Args:
            max_history: L1模式下最大历史快照缓存数
        """
        self.mode = None
        self.max_history = max_history
        
        # L1模式：历史快照缓存 {stock_code: deque([SnapShotData, ...])}
        self._snapshot_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._history_lock = threading.Lock()
        
        # 统计信息
        self._calc_count = {'L2': 0, 'L1': 0}
        
        # 自动嗅探模式
        self._detect_mode()
        
        logger.info(f"✅ [CapitalFlowCalculator] 初始化完成，模式: {self.mode}")
    
    def _detect_mode(self):
        """
        CTO加固: 自动嗅探QMT权限级别
        检测是否支持L2逐笔数据
        """
        try:
            from xtquant import xtdata
            
            # 检查是否有L2逐笔接口
            if hasattr(xtdata, 'get_l2_ticks') or hasattr(xtdata, 'subscribe_l2'):
                self.mode = self.MODE_L2
                logger.info("🎯 检测到L2 VIP权限，启用精确计算模式")
            else:
                self.mode = self.MODE_L1
                logger.info("⚠️ 未检测到L2权限，启用L1行为学推演模式")
                
        except Exception as e:
            logger.warning(f"⚠️ 权限检测失败，默认使用L1模式: {e}")
            self.mode = self.MODE_L1
    
    def set_mode(self, mode: str):
        """
        手动设置计算模式 (用于测试或强制降级)
        
        Args:
            mode: 'L2' 或 'L1'
        """
        if mode in [self.MODE_L2, self.MODE_L1]:
            self.mode = mode
            logger.info(f"🔄 手动切换模式: {mode}")
        else:
            logger.error(f"❌ 无效模式: {mode}")
    
    def calculate(self, stock_code: str, tick_data: Dict[str, Any]) -> FlowResult:
        """
        统一计算入口 - 自动根据模式分发
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
            
        Returns:
            FlowResult: 资金流计算结果
        """
        if self.mode == self.MODE_L2:
            return self._calculate_l2(stock_code, tick_data)
        else:
            return self._calculate_l1(stock_code, tick_data)
    
    def _calculate_l2(self, stock_code: str, tick_data: Dict[str, Any]) -> FlowResult:
        """
        L2 VIP模式：逐笔成交精确计算
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据 (包含逐笔成交)
            
        Returns:
            FlowResult: 精确资金流结果
        """
        try:
            # L2模式下可以直接获取买卖方向数据
            # 假设tick_data包含 buy_volume 和 sell_volume
            buy_volume = tick_data.get('buy_volume', 0)
            sell_volume = tick_data.get('sell_volume', 0)
            price = tick_data.get('price', 0)
            
            inflow = buy_volume * price
            outflow = sell_volume * price
            net_flow = inflow - outflow
            
            # 计算资金流得分
            total = inflow + outflow
            flow_score = 50 + (net_flow / total * 50) if total > 0 else 50
            flow_score = max(0, min(100, flow_score))
            
            self._calc_count['L2'] += 1
            
            return FlowResult(
                stock_code=stock_code,
                mode=self.MODE_L2,
                inflow=inflow,
                outflow=outflow,
                net_flow=net_flow,
                flow_score=flow_score,
                is_trap=False
            )
            
        except Exception as e:
            logger.error(f"❌ L2计算失败 {stock_code}: {e}")
            # L2失败时降级到L1
            return self._calculate_l1(stock_code, tick_data)
    
    def _calculate_l1(self, stock_code: str, tick_data: Dict[str, Any]) -> FlowResult:
        """
        L1降级模式：行为学推演算法
        
        CTO核心算法:
        1. 价格推力背离检测
        2. 内外盘Delta逼近
        3. 五档盘口压迫系数
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据 (3秒快照)
            
        Returns:
            FlowResult: 推演资金流结果
        """
        try:
            # 构建当前快照
            current_snap = SnapShotData(
                stock_code=stock_code,
                timestamp=datetime.now(),
                price=tick_data.get('price', 0),
                volume=tick_data.get('volume', 0),
                amount=tick_data.get('amount', 0),
                bid1=tick_data.get('bid1', tick_data.get('price', 0) * 0.99),
                ask1=tick_data.get('ask1', tick_data.get('price', 0) * 1.01),
                bid_vol1=tick_data.get('bid_vol1', 0),
                ask_vol1=tick_data.get('ask_vol1', 0),
                change_pct=tick_data.get('change_pct', 0)
            )
            
            # 获取历史快照
            with self._history_lock:
                history = self._snapshot_history[stock_code]
                
                # 计算Delta数据
                if len(history) >= 1:
                    prev_snap = history[-1]
                    delta_volume = current_snap.volume - prev_snap.volume
                    delta_amount = current_snap.amount - prev_snap.amount
                    time_diff = (current_snap.timestamp - prev_snap.timestamp).total_seconds()
                else:
                    delta_volume = 0
                    delta_amount = 0
                    time_diff = 3  # 默认3秒
                
                # 保存当前快照
                history.append(current_snap)
            
            # ===== CTO算法1: 内外盘Delta逼近 =====
            inflow, outflow = self._estimate_bid_ask_flow(
                current_snap, prev_snap if len(history) > 1 else None, 
                delta_volume, delta_amount
            )
            
            # ===== CTO算法2: 价格推力背离检测 =====
            price_thrust, is_thrust_anomaly = self._detect_price_thrust_divergence(
                stock_code, current_snap, history, delta_volume
            )
            
            # ===== CTO算法3: 五档盘口压迫系数 =====
            pressure_ratio = self._calculate_order_book_pressure(current_snap)
            
            # 综合计算
            net_flow = inflow - outflow
            total_flow = inflow + outflow
            flow_score = 50 + (net_flow / total_flow * 50) if total_flow > 0 else 50
            flow_score = max(0, min(100, flow_score))
            
            # 陷阱检测
            is_trap, trap_type = self._detect_l1_trap(
                current_snap, price_thrust, pressure_ratio, is_thrust_anomaly
            )
            
            self._calc_count['L1'] += 1
            
            return FlowResult(
                stock_code=stock_code,
                mode=self.MODE_L1,
                inflow=inflow,
                outflow=outflow,
                net_flow=net_flow,
                flow_score=flow_score,
                price_thrust=price_thrust,
                pressure_ratio=pressure_ratio,
                is_trap=is_trap,
                trap_type=trap_type
            )
            
        except Exception as e:
            logger.error(f"❌ L1计算失败 {stock_code}: {e}")
            return FlowResult(
                stock_code=stock_code,
                mode=self.MODE_L1,
                is_trap=False,
                trap_type="计算错误"
            )
    
    def _estimate_bid_ask_flow(self, current: SnapShotData, prev: Optional[SnapShotData],
                               delta_volume: int, delta_amount: float) -> Tuple[float, float]:
        """
        CTO算法1: 内外盘Delta逼近
        
        通过价格与买卖盘关系，估算内外盘比例
        """
        if not prev or delta_volume <= 0:
            return 0.0, 0.0
        
        # 价格相对于中轴的位置
        mid_price = (current.bid1 + current.ask1) / 2 if current.bid1 > 0 and current.ask1 > 0 else current.price
        
        # 计算价格偏离度 (-1到1，1表示接近卖一，-1表示接近买一)
        price_deviation = (current.price - mid_price) / (mid_price * 0.01) if mid_price > 0 else 0
        price_deviation = max(-1, min(1, price_deviation))
        
        # 估算买盘比例 (0-1)
        # 价格越接近卖一，主动买盘越多
        buy_ratio = 0.5 + price_deviation * 0.3  # 基础0.5，根据偏离度调整
        buy_ratio = max(0.2, min(0.8, buy_ratio))  # 限制在0.2-0.8
        
        # 根据涨跌修正
        if current.change_pct > 2:  # 大涨时，买盘比例更高
            buy_ratio = min(0.8, buy_ratio + 0.1)
        elif current.change_pct < -2:  # 大跌时，卖盘比例更高
            buy_ratio = max(0.2, buy_ratio - 0.1)
        
        inflow = delta_amount * buy_ratio
        outflow = delta_amount * (1 - buy_ratio)
        
        return inflow, outflow
    
    def _detect_price_thrust_divergence(self, stock_code: str, current: SnapShotData,
                                        history: deque, delta_volume: int) -> Tuple[float, bool]:
        """
        CTO算法2: 价格推力背离检测
        
        检测"放量滞涨"或"缩量大涨"等异常行为
        
        Returns:
            (price_thrust, is_anomaly)
            price_thrust: 推力系数 (正值表示上涨有力，负值表示滞涨)
            is_anomaly: 是否异常
        """
        if len(history) < 3 or delta_volume <= 0:
            return 0.0, False
        
        # 获取最近3个快照
        recent_snaps = list(history)[-3:]
        
        # 计算累计变化
        total_volume_change = sum([s.volume for s in recent_snaps[1:]]) - recent_snaps[0].volume
        price_change = current.price - recent_snaps[0].price
        price_change_pct = price_change / recent_snaps[0].price * 100 if recent_snaps[0].price > 0 else 0
        
        # 计算平均成交量 (过去1分钟的平均)
        if len(history) >= 20:  # 约1分钟数据
            avg_volume = sum([list(history)[i].volume - list(history)[i-1].volume 
                             for i in range(-19, 0)]) / 19
        else:
            avg_volume = delta_volume
        
        # 价格推力 = 价格变化 / 成交量放大倍数
        volume_ratio = delta_volume / avg_volume if avg_volume > 0 else 1
        price_thrust = price_change_pct / volume_ratio if volume_ratio > 0 else price_change_pct
        
        # 检测异常
        is_anomaly = False
        
        # 异常1: 放量滞涨 (成交量暴增但价格不动或下跌)
        if volume_ratio > 3 and price_change_pct < 0.5:
            is_anomaly = True
            logger.warning(f"🚨 [{stock_code}] L1陷阱检测: 放量滞涨 "
                          f"(量倍率:{volume_ratio:.2f}, 涨幅:{price_change_pct:.2f}%)")
        
        # 异常2: 量价背离 (价格微涨但成交量异常放大)
        elif volume_ratio > 5 and price_change_pct < 2:
            is_anomaly = True
            logger.warning(f"⚠️ [{stock_code}] L1陷阱检测: 量价背离 "
                          f"(量倍率:{volume_ratio:.2f}, 涨幅:{price_change_pct:.2f}%)")
        
        return price_thrust, is_anomaly
    
    def _calculate_order_book_pressure(self, current: SnapShotData) -> float:
        """
        CTO算法3: 五档盘口压迫系数
        
        通过买卖盘力量对比，判断抛压
        
        Returns:
            pressure_ratio: >1表示买盘强，<1表示卖盘强
        """
        bid_vol = current.bid_vol1
        ask_vol = current.ask_vol1
        
        if bid_vol + ask_vol == 0:
            return 1.0
        
        # 压迫系数 = 买盘量 / 卖盘量
        pressure_ratio = bid_vol / ask_vol if ask_vol > 0 else 10.0
        
        # 限制范围
        pressure_ratio = max(0.1, min(10.0, pressure_ratio))
        
        return pressure_ratio
    
    def _detect_l1_trap(self, current: SnapShotData, price_thrust: float,
                       pressure_ratio: float, is_thrust_anomaly: bool) -> Tuple[bool, str]:
        """
        L1模式陷阱综合判断
        
        Returns:
            (is_trap, trap_type)
        """
        # 陷阱1: 放量滞涨 (价格推力异常)
        if is_thrust_anomaly:
            return True, "L1_放量滞涨"
        
        # 陷阱2: 盘口压迫异常 (买盘突然撤单)
        if pressure_ratio < 0.3 and current.change_pct > 3:
            # 大涨但买盘很弱，可能是诱多
            return True, "L1_盘口诱多"
        
        # 陷阱3: 价格推力为负但股价在涨 (滞涨信号)
        if price_thrust < -0.5 and current.change_pct > 2:
            return True, "L1_上涨乏力"
        
        return False, ""
    
    def detect_trap(self, stock_code: str, tick_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        对外接口：检测资金陷阱
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
            
        Returns:
            (is_trap, trap_type)
        """
        result = self.calculate(stock_code, tick_data)
        return result.is_trap, result.trap_type
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'mode': self.mode,
            'calc_count': self._calc_count,
            'history_size': {k: len(v) for k, v in self._snapshot_history.items()}
        }


# 便捷函数
def create_capital_flow_calculator(max_history: int = 20) -> CapitalFlowCalculator:
    """
    创建资金流计算器实例
    
    Args:
        max_history: L1模式下最大历史快照缓存数
        
    Returns:
        CapitalFlowCalculator: 计算器实例
    """
    return CapitalFlowCalculator(max_history=max_history)


if __name__ == "__main__":
    # 测试双模资金流计算器
    print("🧪 双模资金流计算器测试")
    print("=" * 60)
    
    # 创建计算器
    calc = create_capital_flow_calculator(max_history=10)
    
    print(f"\n🎯 当前模式: {calc.mode}")
    
    # 模拟L1数据测试
    print("\n🔍 模拟L1数据测试...")
    
    # 模拟正常上涨
    for i in range(5):
        mock_tick = {
            'price': 10.0 + i * 0.1,
            'volume': 100000 + i * 50000,
            'amount': 1000000 + i * 500000,
            'bid1': 10.0 + i * 0.1 - 0.01,
            'ask1': 10.0 + i * 0.1 + 0.01,
            'bid_vol1': 1000 + i * 100,
            'ask_vol1': 800 + i * 50,
            'change_pct': i * 0.5
        }
        result = calc.calculate('TEST001', mock_tick)
        print(f"  第{i+1}次: 推力={result.price_thrust:.2f}, "
              f"压迫比={result.pressure_ratio:.2f}, "
              f"陷阱={result.is_trap}")
    
    # 模拟放量滞涨 (陷阱)
    print("\n🚨 模拟放量滞涨陷阱...")
    for i in range(3):
        mock_tick = {
            'price': 10.5 + i * 0.02,  # 价格几乎不动
            'volume': 500000 + i * 200000,  # 成交量暴增
            'amount': 5000000 + i * 2000000,
            'bid1': 10.5,
            'ask1': 10.52,
            'bid_vol1': 500,  # 买盘减少
            'ask_vol1': 3000,  # 卖盘增加
            'change_pct': 0.1
        }
        result = calc.calculate('TEST001', mock_tick)
        print(f"  第{i+1}次: 推力={result.price_thrust:.2f}, "
              f"压迫比={result.pressure_ratio:.2f}, "
              f"陷阱={result.is_trap}, 类型={result.trap_type}")
    
    # 打印统计
    stats = calc.get_stats()
    print(f"\n📊 统计信息: {stats}")
    
    print("\n✅ 测试完成")