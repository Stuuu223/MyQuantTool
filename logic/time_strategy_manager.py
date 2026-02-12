#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V17 Time-Lord - 时间策略管理器
实现分时段策略：黄金半小时、垃圾时间、尾盘偷袭
V17.1: 时区校准 - 统一使用北京时间
V17.2: 时空融合 - 情绪覆盖时间策略
"""

from datetime import datetime, time
from typing import Dict, Optional
from enum import Enum
from logic.utils.logger import get_logger
from logic.utils import Utils

logger = get_logger(__name__)


class TradingMode(Enum):
    """交易模式"""
    AGGRESSIVE = "进攻模式"  # 全功率运行，进攻模式
    DEFENSIVE = "防守模式"  # 低功耗监控，只卖不买
    SNIPE = "尾盘偷袭"  # 扫描首板或尾盘抢筹机会


class TimeStrategyManager:
    """
    V17 时间策略管理器 (Time-Lord)
    
    实现分时段策略：
    - 09:25 - 10:00 (黄金半小时)：全功率运行，进攻模式
    - 10:00 - 14:30 (垃圾时间)：进入低功耗监控模式。只卖不买，或者只做 T
    - 14:30 - 15:00 (尾盘偷袭)：重新唤醒，扫描"首板"或"尾盘抢筹"机会
    
    V17.2 时空融合：
    - 当市场情绪极热（>80）时，即使是在垃圾时间，也要强制切换为进攻模式
    - 当市场情绪极冷（<20）时，即使是在黄金时间，也要强制切换为防守模式
    """
    
    # 时间段配置
    GOLDEN_HALF_HOUR_START = time(9, 25)  # 09:25
    GOLDEN_HALF_HOUR_END = time(10, 0)    # 10:00
    
    GARBAGE_TIME_START = time(10, 0)      # 10:00
    GARBAGE_TIME_END = time(14, 30)       # 14:30
    
    SNIPE_TIME_START = time(14, 30)       # 14:30
    SNIPE_TIME_END = time(15, 0)          # 15:00
    
    def __init__(self):
        """初始化时间策略管理器"""
        self.current_mode = TradingMode.AGGRESSIVE
        self.mode_history = []
        
        # 🆕 V18 深度迭代 3：国家队指纹监控器
        try:
            from logic.national_team_detector import get_national_team_detector
            self.national_team = get_national_team_detector()
            logger.info("✅ 国家队指纹监控系统集成成功")
        except Exception as e:
            logger.warning(f"⚠️ 国家队指纹监控系统集成失败: {e}")
            self.national_team = None
    
    def get_current_mode(self, current_time: Optional[datetime] = None, sentiment_score: float = 50.0) -> Dict[str, any]:
        """
        获取当前交易模式（V17.2 时空融合版本）
        
        Args:
            current_time: 当前时间，如果为 None 则使用北京时间
            sentiment_score: 市场情绪分数（0-100），V17.2 新增
        
        Returns:
            dict: {
                'mode': TradingMode,  # 交易模式
                'mode_name': str,     # 模式名称
                'description': str,   # 模式描述
                'allow_buy': bool,    # 是否允许买入
                'allow_sell': bool,   # 是否允许卖出
                'scan_interval': int, # 扫描间隔（秒）
                'recommendation': str, # 操作建议
                'sentiment_override': bool, # V17.2: 是否被情绪覆盖
                'sentiment_score': float  # V17.2: 情绪分数
            }
        """
        if current_time is None:
            current_time = Utils.get_beijing_time()
        
        current_time_only = current_time.time()
        
        # 判断当前时间段（基础模式）
        if self.GOLDEN_HALF_HOUR_START <= current_time_only < self.GOLDEN_HALF_HOUR_END:
            # 黄金半小时：09:25 - 10:00
            mode = TradingMode.AGGRESSIVE
            mode_name = "进攻模式"
            description = "黄金半小时：全功率运行，进攻模式"
            allow_buy = True
            allow_sell = True
            scan_interval = 30  # 30秒扫描一次
            recommendation = "🔥 积极寻找买入机会，关注弱转强、龙虎榜反制"
            
        elif self.GARBAGE_TIME_START <= current_time_only < self.GARBAGE_TIME_END:
            # 垃圾时间：10:00 - 14:30
            mode = TradingMode.DEFENSIVE
            mode_name = "防守模式"
            description = "垃圾时间：低功耗监控，只卖不买"
            allow_buy = False
            allow_sell = True
            scan_interval = 120  # 2分钟扫描一次
            recommendation = "🛡️ 只卖不买，或者做 T，避免在震荡中被磨损"
            
        elif self.SNIPE_TIME_START <= current_time_only < self.SNIPE_TIME_END:
            # 尾盘偷袭：14:30 - 15:00
            mode = TradingMode.SNIPE
            mode_name = "尾盘偷袭"
            description = "尾盘偷袭：扫描首板或尾盘抢筹机会"
            allow_buy = True
            allow_sell = True
            scan_interval = 15  # 15秒扫描一次
            recommendation = "🎯 扫描首板或尾盘抢筹机会，准备明日竞价"
            
        else:
            # 非交易时间
            mode = TradingMode.DEFENSIVE
            mode_name = "休眠模式"
            description = "非交易时间：系统休眠"
            allow_buy = False
            allow_sell = False
            scan_interval = 300  # 5分钟扫描一次
            recommendation = "😴 系统休眠，等待交易时间"
        
        # V17.2: 情绪覆盖逻辑 (Chronos-Kairos Fusion)
        sentiment_override = False
        
        if sentiment_score >= 80.0:
            # 情绪爆发：强制进攻
            if mode != TradingMode.AGGRESSIVE:
                logger.warning(f"🔥 [V17.2 情绪爆发] 市场情绪({sentiment_score:.1f})极热，打破时间限制，强制进攻！")
                mode = TradingMode.AGGRESSIVE
                mode_name = "情绪爆发模式"
                description = f"情绪爆发({sentiment_score:.1f})：无视垃圾时间，强制进攻"
                allow_buy = True
                allow_sell = True
                scan_interval = 15  # 15秒扫描一次
                recommendation = "🚀 市场情绪爆发，抓住主升浪机会，积极买入！"
            # 无论当前模式是什么，只要情绪分数 >= 80，就标记为情绪覆盖
            sentiment_override = True
                
        elif sentiment_score <= 20.0:
            # 情绪冰点：强制防守
            if mode != TradingMode.DEFENSIVE:
                logger.warning(f"❄️ [V17.2 情绪冰点] 市场情绪({sentiment_score:.1f})极冷，强制防守。")
                mode = TradingMode.DEFENSIVE
                mode_name = "情绪冰点模式"
                description = f"情绪冰点({sentiment_score:.1f})：市场恐慌，强制防守"
                allow_buy = False
                allow_sell = True
                scan_interval = 300  # 5分钟扫描一次
                recommendation = "🛡️ 市场情绪冰点，规避风险，只卖不买"
            # 无论当前模式是什么，只要情绪分数 <= 20，就标记为情绪覆盖
            sentiment_override = True
        
        # 🆕 V18 深度迭代 3：MARKET_RESCUE_MODE 判断
        if self.national_team and self.national_team.is_rescue_mode():
            rescue_info = self.national_team.get_rescue_mode_info()
            logger.warning(f"🚨 [MARKET_RESCUE_MODE] {rescue_info['reason']}")
            
            # 救援模式：优先选择价值标的或 ETF
            mode = TradingMode.AGGRESSIVE
            mode_name = "救援模式"
            description = f"MARKET_RESCUE_MODE：{rescue_info['reason']}"
            allow_buy = True
            allow_sell = True
            scan_interval = 10  # 10秒扫描一次
            recommendation = "🚨 国家队入场救援，优先选择价值标的或 ETF，规避妖股"
        
        # 更新当前模式
        self.current_mode = mode
        
        # 记录模式历史
        self.mode_history.append({
            'timestamp': current_time,
            'mode': mode,
            'mode_name': mode_name,
            'sentiment_score': sentiment_score,
            'sentiment_override': sentiment_override
        })
        
        # 只保留最近 10 条记录
        if len(self.mode_history) > 10:
            self.mode_history.pop(0)
        
        result = {
            'mode': mode,
            'mode_name': mode_name,
            'description': description,
            'allow_buy': allow_buy,
            'allow_sell': allow_sell,
            'scan_interval': scan_interval,
            'recommendation': recommendation,
            'sentiment_override': sentiment_override,  # V17.2 新增
            'sentiment_score': sentiment_score  # V17.2 新增
        }
        
        logger.info(f"⏰ [Time-Lord] {mode_name}: {description}")
        if sentiment_override:
            logger.info(f"🔥 [V17.2 时空融合] 情绪({sentiment_score:.1f})覆盖时间策略")
        
        return result
    
    def should_filter_signal(self, signal: str, current_time: Optional[datetime] = None, sentiment_score: float = 50.0) -> tuple:
        """
        根据当前时间策略过滤交易信号（V17.2 时空融合版本）
        
        Args:
            signal: 原始交易信号 (BUY/SELL/WAIT)
            current_time: 当前时间
            sentiment_score: 市场情绪分数（0-100），V17.2 新增
        
        Returns:
            tuple: (filtered_signal, reason)
        """
        mode_info = self.get_current_mode(current_time, sentiment_score)
        
        mode = mode_info['mode']
        mode_name = mode_info['mode_name']
        
        # V17.2: 情绪爆发时，即使是在防守模式也允许买入
        if mode_info['sentiment_override'] and mode_info['sentiment_score'] >= 80.0:
            # 情绪覆盖，保留原信号
            if signal == "BUY":
                return (signal, f"🔥 [V17.2 时空融合] 情绪爆发({sentiment_score:.1f})，允许买入")
        
        # 防守模式：过滤所有 BUY 信号
        if mode == TradingMode.DEFENSIVE and signal == "BUY":
            return ("WAIT", f"⏰ [时间过滤] {mode_name}：禁止买入，建议改为观望")
        
        # 休眠模式：过滤所有信号
        if mode_name == "休眠模式":
            return ("WAIT", f"⏰ [时间过滤] {mode_name}：系统休眠，禁止操作")
        
        # 其他情况：保留原信号
        return (signal, "")
    
    def get_next_mode_switch(self, current_time: Optional[datetime] = None) -> Dict[str, any]:
        """
        获取下一次模式切换时间
        
        Args:
            current_time: 当前时间
        
        Returns:
            dict: {
                'next_mode': TradingMode,
                'next_mode_name': str,
                'switch_time': time,
                'remaining_seconds': int,
                'remaining_minutes': int
            }
        """
        if current_time is None:
            current_time = Utils.get_beijing_time()
        
        current_time_only = current_time.time()
        
        # 计算下一次切换时间
        if current_time_only < self.GOLDEN_HALF_HOUR_START:
            next_time = self.GOLDEN_HALF_HOUR_START
            next_mode = TradingMode.AGGRESSIVE
            next_mode_name = "进攻模式"
        elif current_time_only < self.GOLDEN_HALF_HOUR_END:
            next_time = self.GOLDEN_HALF_HOUR_END
            next_mode = TradingMode.DEFENSIVE
            next_mode_name = "防守模式"
        elif current_time_only < self.GARBAGE_TIME_END:
            next_time = self.GARBAGE_TIME_END
            next_mode = TradingMode.SNIPE
            next_mode_name = "尾盘偷袭"
        elif current_time_only < self.SNIPE_TIME_END:
            next_time = self.SNIPE_TIME_END
            next_mode = TradingMode.DEFENSIVE
            next_mode_name = "休眠模式"
        else:
            # 下一个交易日的黄金半小时
            next_time = self.GOLDEN_HALF_HOUR_START
            next_mode = TradingMode.AGGRESSIVE
            next_mode_name = "进攻模式"
        
        # 计算剩余时间
        current_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
        next_seconds = next_time.hour * 3600 + next_time.minute * 60
        
        if next_seconds > current_seconds:
            remaining_seconds = next_seconds - current_seconds
        else:
            # 跨天了
            remaining_seconds = (24 * 3600 - current_seconds) + next_seconds
        
        remaining_minutes = remaining_seconds // 60
        
        return {
            'next_mode': next_mode,
            'next_mode_name': next_mode_name,
            'switch_time': next_time,
            'remaining_seconds': remaining_seconds,
            'remaining_minutes': remaining_minutes
        }


# 全局实例
_time_strategy_manager = None

def get_time_strategy_manager() -> TimeStrategyManager:
    """获取时间策略管理器实例（单例）"""
    global _time_strategy_manager
    if _time_strategy_manager is None:
        _time_strategy_manager = TimeStrategyManager()
    return _time_strategy_manager


if __name__ == "__main__":
    # 测试
    manager = TimeStrategyManager()
    
    # 测试不同时间点的模式
    test_times = [
        datetime(2026, 1, 18, 9, 30),   # 黄金半小时
        datetime(2026, 1, 18, 10, 30),  # 垃圾时间
        datetime(2026, 1, 18, 14, 45),  # 尾盘偷袭
        datetime(2026, 1, 18, 16, 0),   # 休眠模式
    ]
    
    print("=" * 80)
    print("V17 Time-Lord 时间策略测试")
    print("=" * 80)
    
    for test_time in test_times:
        mode_info = manager.get_current_mode(test_time)
        print(f"\n时间: {test_time.strftime('%H:%M')}")
        print(f"模式: {mode_info['mode_name']}")
        print(f"描述: {mode_info['description']}")
        print(f"建议: {mode_info['recommendation']}")
        
        # 测试信号过滤
        for signal in ["BUY", "SELL", "WAIT"]:
            filtered_signal, reason = manager.should_filter_signal(signal, test_time)
            if reason:
                print(f"  {signal} -> {filtered_signal}: {reason}")
            else:
                print(f"  {signal} -> {filtered_signal}: 保留")
        
        # 测试下一次切换
        next_switch = manager.get_next_mode_switch(test_time)
        print(f"  下次切换: {next_switch['next_mode_name']} @ {next_switch['switch_time'].strftime('%H:%M')} (剩余 {next_switch['remaining_minutes']} 分钟)")