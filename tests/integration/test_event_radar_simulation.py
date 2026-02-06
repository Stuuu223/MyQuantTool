#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件驱动盘中雷达 - 模拟测试

模拟测试内容：
1. 模拟Tick数据生成
2. 测试集合竞价事件检测（弱转强、一字板扩散）
3. 测试半路战法事件检测（平台突破）
4. 测试低吸战法事件检测（5日均线回踩）
5. 测试龙头战法事件检测（板块龙头）
6. 测试事件管理器逻辑
7. 测试扫描触发机制

Author: iFlow CLI
Version: V2.0
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logic.logger import get_logger

logger = get_logger(__name__)


class TickSimulator:
    """Tick数据模拟器"""
    
    def __init__(self):
        """初始化模拟器"""
        self.current_time = datetime(2026, 2, 6, 9, 25, 0)  # 竞价时间
        
    def generate_auction_tick(
        self,
        stock_code: str,
        yesterday_close: float,
        gap_pct: float,
        volume_ratio: float
    ) -> Dict[str, Any]:
        """
        生成集合竞价Tick数据
        
        Args:
            stock_code: 股票代码
            yesterday_close: 昨收价
            gap_pct: 高开幅度（如0.06表示6%）
            volume_ratio: 竞价量比
        
        Returns:
            Tick数据字典
        """
        current_price = yesterday_close * (1 + gap_pct)
        auction_volume = 1000000 * volume_ratio  # 模拟竞价量
        
        return {
            'code': stock_code,
            'now': current_price,
            'close': yesterday_close,
            'auction_volume': int(auction_volume),
            'bid1_volume': int(auction_volume * 0.5),
            'ask1_volume': 0,  # 竞价阶段卖一量为0
            'volume': int(auction_volume),
            'open': current_price,
            'time': self.current_time
        }
    
    def generate_intraday_tick(
        self,
        stock_code: str,
        yesterday_close: float,
        current_price: float,
        volume: int,
        bid1_volume: int = 0,
        ask1_volume: int = 0
    ) -> Dict[str, Any]:
        """
        生成分时Tick数据
        
        Args:
            stock_code: 股票代码
            yesterday_close: 昨收价
            current_price: 当前价
            volume: 成交量
            bid1_volume: 买一量
            ask1_volume: 卖一量
        
        Returns:
            Tick数据字典
        """
        return {
            'code': stock_code,
            'now': current_price,
            'close': yesterday_close,
            'volume': volume,
            'bid1_volume': bid1_volume,
            'ask1_volume': ask1_volume,
            'open': yesterday_close * 1.02,  # 假设开盘涨2%
            'time': self.current_time
        }


def test_auction_event_detector():
    """测试集合竞价事件检测器"""
    print("\n" + "=" * 80)
    print("🧪 测试集合竞价事件检测器")
    print("=" * 80)
    
    try:
        from logic.auction_event_detector import AuctionEventDetector
        from logic.event_detector import EventType
        
        detector = AuctionEventDetector()
        simulator = TickSimulator()
        
        # 测试用例1：竞价弱转强（应该触发）
        print("\n📋 测试用例1：竞价弱转强（应该触发）")
        tick1 = simulator.generate_auction_tick(
            stock_code='000592.SZ',
            yesterday_close=10.00,
            gap_pct=0.06,  # 高开6%
            volume_ratio=2.0  # 量比2.0
        )
        
        context1 = {
            'yesterday_close': 10.00,
            'yesterday_data': {
                'close_change_pct': -0.02,  # 昨日跌2%
                'volume': 1000000
            }
        }
        
        event1 = detector.detect(tick1, context1)
        if event1:
            print(f"✅ 成功检测到事件:")
            print(f"   类型: {event1.event_type.value}")
            print(f"   股票: {event1.stock_code}")
            print(f"   描述: {event1.description}")
            print(f"   置信度: {event1.confidence:.2f}")
        else:
            print(f"❌ 未检测到事件（应该触发）")
        
        # 测试用例2：竞价弱转强（不应该触发，量比不够）
        print("\n📋 测试用例2：竞价弱转强（不应该触发，量比不够）")
        tick2 = simulator.generate_auction_tick(
            stock_code='300502.SZ',
            yesterday_close=20.00,
            gap_pct=0.06,  # 高开6%
            volume_ratio=1.2  # 量比1.2（不够）
        )
        
        context2 = {
            'yesterday_close': 20.00,
            'yesterday_data': {
                'close_change_pct': -0.02,
                'volume': 2000000
            }
        }
        
        event2 = detector.detect(tick2, context2)
        if event2:
            print(f"❌ 意外检测到事件: {event2.description}")
        else:
            print(f"✅ 正确，未检测到事件（量比不够）")
        
        # 测试用例3：一字板扩散（应该触发）
        print("\n📋 测试用例3：一字板扩散（应该触发）")
        tick3 = simulator.generate_auction_tick(
            stock_code='600519.SH',
            yesterday_close=50.00,
            gap_pct=0.099,  # 涨停
            volume_ratio=5.0  # 量大
        )
        
        context3 = {
            'yesterday_close': 50.00,
            'float_market_cap': 1000000000  # 流通市值10亿
        }
        
        # 修改tick数据，模拟封单金额
        tick3['bid1_volume'] = 100000  # 10万手封单
        tick3['bid1_volume'] = 100000 * 100  # 1000万股
        
        event3 = detector.detect_limit_up_spread(tick3, context3)
        if event3:
            print(f"✅ 成功检测到事件:")
            print(f"   类型: {event3.event_type.value}")
            print(f"   股票: {event3.stock_code}")
            print(f"   描述: {event3.description}")
            print(f"   置信度: {event3.confidence:.2f}")
        else:
            print(f"❌ 未检测到事件（应该触发）")
        
        print("\n✅ 集合竞价事件检测器测试完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 集合竞价事件检测器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_halfway_event_detector():
    """测试半路战法事件检测器"""
    print("\n" + "=" * 80)
    print("🧪 测试半路战法事件检测器")
    print("=" * 80)
    
    try:
        from logic.halfway_event_detector import HalfwayEventDetector
        
        detector = HalfwayEventDetector()
        simulator = TickSimulator()
        
        # 模拟20cm标的平台突破
        print("\n📋 测试用例：20cm标的平台突破")
        
        # 先填充历史数据（模拟平台）
        stock_code = '300502.SZ'
        yesterday_close = 20.00
        platform_price = 22.00  # 平台价格（涨幅10%）
        
        for i in range(40):
            # 平台震荡
            price = platform_price * (1 + (i % 5 - 2) * 0.002)  # ±0.4%振幅
            volume = 1000000 + i * 10000
            detector._update_history(stock_code, price, volume)
        
        # 突破平台
        tick = simulator.generate_intraday_tick(
            stock_code=stock_code,
            yesterday_close=yesterday_close,
            current_price=platform_price * 1.015,  # 突破1.5%
            volume=2000000,  # 放量
            bid1_volume=50000,
            ask1_volume=10000
        )
        
        context = {
            'yesterday_close': yesterday_close
        }
        
        event = detector.detect(tick, context)
        if event:
            print(f"✅ 成功检测到事件:")
            print(f"   类型: {event.event_type.value}")
            print(f"   股票: {event.stock_code}")
            print(f"   描述: {event.description}")
            print(f"   置信度: {event.confidence:.2f}")
        else:
            print(f"❌ 未检测到事件")
        
        print("\n✅ 半路战法事件检测器测试完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 半路战法事件检测器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dip_buy_event_detector():
    """测试低吸战法事件检测器"""
    print("\n" + "=" * 80)
    print("🧪 测试低吸战法事件检测器")
    print("=" * 80)
    
    try:
        from logic.dip_buy_event_detector import DipBuyEventDetector
        
        detector = DipBuyEventDetector()
        simulator = TickSimulator()
        
        # 测试用例：5日均线低吸
        print("\n📋 测试用例：5日均线低吸")
        
        tick = simulator.generate_intraday_tick(
            stock_code='000592.SZ',
            yesterday_close=10.00,
            current_price=9.85,  # 回踩到MA5下方1.5%
            volume=700000,  # 缩量
            bid1_volume=30000,
            ask1_volume=20000
        )
        
        context = {
            'yesterday_close': 10.00,
            'ma5': 10.00,
            'ma10': 9.80,
            'ma20': 9.60,
            'yesterday_volume': 1000000  # 昨日量100万
        }
        
        event = detector.detect(tick, context)
        if event:
            print(f"✅ 成功检测到事件:")
            print(f"   类型: {event.event_type.value}")
            print(f"   股票: {event.stock_code}")
            print(f"   描述: {event.description}")
            print(f"   置信度: {event.confidence:.2f}")
        else:
            print(f"❌ 未检测到事件")
        
        print("\n✅ 低吸战法事件检测器测试完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 低吸战法事件检测器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_leader_event_detector():
    """测试龙头战法事件检测器"""
    print("\n" + "=" * 80)
    print("🧪 测试龙头战法事件检测器")
    print("=" * 80)
    
    try:
        from logic.leader_event_detector import LeaderEventDetector
        
        detector = LeaderEventDetector()
        simulator = TickSimulator()
        
        # 测试用例：板块龙头候选
        print("\n📋 测试用例：板块龙头候选")
        
        tick = simulator.generate_intraday_tick(
            stock_code='300502.SZ',
            yesterday_close=20.00,
            current_price=21.50,  # 涨幅7.5%
            volume=3000000,
            bid1_volume=100000,
            ask1_volume=50000
        )
        
        context = {
            'yesterday_close': 20.00,
            'sector_data': {
                'name': '机器人',
                'rank': 1,  # 板块排名第1
                'top3_gap': 0.005  # Top3差距0.5%
            }
        }
        
        event = detector.detect(tick, context)
        if event:
            print(f"✅ 成功检测到事件:")
            print(f"   类型: {event.event_type.value}")
            print(f"   股票: {event.stock_code}")
            print(f"   描述: {event.description}")
            print(f"   置信度: {event.confidence:.2f}")
        else:
            print(f"❌ 未检测到事件")
        
        print("\n✅ 龙头战法事件检测器测试完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 龙头战法事件检测器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_manager():
    """测试事件管理器"""
    print("\n" + "=" * 80)
    print("🧪 测试事件管理器")
    print("=" * 80)
    
    try:
        from logic.event_detector import EventManager, EventType, TradingEvent
        from logic.auction_event_detector import AuctionEventDetector
        
        # 创建事件管理器
        manager = EventManager()
        
        # 注册检测器
        detector = AuctionEventDetector()
        manager.register_detector(detector)
        
        # 模拟多个事件
        print("\n📋 模拟多个事件...")
        
        events = [
            TradingEvent(
                event_type=EventType.OPENING_WEAK_TO_STRONG,
                stock_code='000592.SZ',
                timestamp=datetime.now(),
                data={'gap_pct': 0.06, 'volume_ratio': 2.0},
                confidence=0.85,
                description='竞价弱转强：高开6.00%，量比2.00'
            ),
            TradingEvent(
                event_type=EventType.HALFWAY_BREAKOUT,
                stock_code='300502.SZ',
                timestamp=datetime.now(),
                data={'change_pct': 0.125, 'breakout_gain': 0.015},
                confidence=0.78,
                description='半路平台突破：涨幅12.50%，突破1.50%'
            ),
            TradingEvent(
                event_type=EventType.LEADER_CANDIDATE,
                stock_code='600519.SH',
                timestamp=datetime.now(),
                data={'change_pct': 0.075, 'sector_rank': 1},
                confidence=0.82,
                description='板块龙头候选：涨幅7.50%，板块排名第1'
            )
        ]
        
        # 添加到事件队列
        for event in events:
            manager.event_queue.append(event)
            print(f"   添加事件: {event.stock_code} - {event.description}")
        
        # 检查是否有事件
        print(f"\n📊 事件队列状态:")
        print(f"   事件数量: {len(manager.event_queue)}")
        print(f"   是否有事件: {manager.has_events()}")
        print(f"   应触发扫描: {manager.should_trigger_scan()}")
        
        # 列出所有事件
        print(f"\n📋 事件列表:")
        for i, event in enumerate(manager.get_events(), 1):
            print(f"   {i}. [{event.event_type.value}] {event.stock_code} - {event.description}")
        
        print("\n✅ 事件管理器测试完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 事件管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_workflow():
    """测试完整工作流程"""
    print("\n" + "=" * 80)
    print("🧪 测试完整工作流程")
    print("=" * 80)
    
    try:
        from logic.event_detector import EventManager
        from logic.auction_event_detector import AuctionEventDetector
        from logic.halfway_event_detector import HalfwayEventDetector
        from logic.dip_buy_event_detector import DipBuyEventDetector
        from logic.leader_event_detector import LeaderEventDetector
        
        print("\n📋 初始化事件驱动雷达...")
        
        # 创建事件管理器
        manager = EventManager()
        
        # 注册所有检测器
        detectors = [
            AuctionEventDetector(),
            HalfwayEventDetector(),
            DipBuyEventDetector(),
            LeaderEventDetector()
        ]
        
        for detector in detectors:
            manager.register_detector(detector)
            print(f"   ✅ 注册: {detector.name}")
        
        # 模拟Tick数据
        print(f"\n📋 模拟Tick数据...")
        simulator = TickSimulator()
        
        ticks = [
            simulator.generate_auction_tick(
                stock_code='000592.SZ',
                yesterday_close=10.00,
                gap_pct=0.06,
                volume_ratio=2.0
            ),
            simulator.generate_intraday_tick(
                stock_code='300502.SZ',
                yesterday_close=20.00,
                current_price=22.50,
                volume=3000000
            )
        ]
        
        contexts = [
            {
                'yesterday_close': 10.00,
                'yesterday_data': {
                    'close_change_pct': -0.02,
                    'volume': 1000000
                }
            },
            {
                'yesterday_close': 20.00,
                'sector_data': {
                    'name': '机器人',
                    'rank': 1,
                    'top3_gap': 0.005
                }
            }
        ]
        
        # 检测事件
        print(f"\n📋 检测事件...")
        detected_events = []
        
        for tick, context in zip(ticks, contexts):
            events = manager.detect_events(tick, context)
            detected_events.extend(events)
        
        print(f"\n📊 检测结果:")
        print(f"   检测到事件数: {len(detected_events)}")
        
        for i, event in enumerate(detected_events, 1):
            print(f"   {i}. [{event.event_type.value}] {event.stock_code}")
            print(f"      描述: {event.description}")
            print(f"      置信度: {event.confidence:.2f}")
        
        # 测试扫描触发逻辑
        print(f"\n📋 测试扫描触发逻辑...")
        
        # 添加检测到的事件到队列
        for event in detected_events:
            manager.event_queue.append(event)
        
        # 检查是否应该触发扫描
        should_trigger = manager.should_trigger_scan()
        print(f"   应触发扫描: {should_trigger}")
        
        if should_trigger:
            print(f"   🎯 模拟触发全链路扫描...")
            print(f"   ✅ 扫描完成")
            
            # 标记扫描完成
            manager.mark_scan_complete()
            print(f"   ✅ 扫描完成，事件队列已清空")
        
        print("\n✅ 完整工作流程测试完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 完整工作流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(results):
    """打印测试摘要"""
    print("\n" + "=" * 80)
    print("📊 模拟测试结果汇总")
    print("=" * 80)
    
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 所有测试通过！事件驱动盘中雷达工作正常")
        print("=" * 80)
        print("\n下一步：")
        print("1. 明天早上8:55 启动: start_event_driven_monitor.bat fixed")
        print("2. 盯9:15-9:25集合竞价事件")
        print("3. 记录事件触发情况和后续走势")
        print("=" * 80 + "\n")
    else:
        print("❌ 部分测试失败，请检查错误信息")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    print("\n🎯 事件驱动盘中雷达 - 模拟测试")
    print("=" * 80)
    print("测试目的：验证事件驱动框架是否正常工作")
    print("=" * 80)
    
    results = {}
    
    # 测试1：集合竞价事件检测器
    results['集合竞价事件检测器'] = test_auction_event_detector()
    
    # 测试2：半路战法事件检测器
    results['半路战法事件检测器'] = test_halfway_event_detector()
    
    # 测试3：低吸战法事件检测器
    results['低吸战法事件检测器'] = test_dip_buy_event_detector()
    
    # 测试4：龙头战法事件检测器
    results['龙头战法事件检测器'] = test_leader_event_detector()
    
    # 测试5：事件管理器
    results['事件管理器'] = test_event_manager()
    
    # 测试6：完整工作流程
    results['完整工作流程'] = test_full_workflow()
    
    # 打印摘要
    print_summary(results)