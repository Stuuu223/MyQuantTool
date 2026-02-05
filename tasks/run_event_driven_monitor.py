#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件驱动持续监控脚本 - 第二阶段框架

功能：
1. 支持两种模式：固定间隔扫描、事件驱动扫描
2. 在交易时间内持续运行（9:25-15:00）
3. 固定间隔模式：每N分钟执行一次全市场扫描
4. 事件驱动模式：检测到事件时触发扫描
5. 生成状态指纹，检测信号变化
6. 只有在状态变化时才保存快照
7. 输出实时日志到命令行

Author: iFlow CLI
Version: V2.0
"""

import time
import os
import sys
import json
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.full_market_scanner import FullMarketScanner
from logic.market_status import MarketStatusChecker
from logic.event_detector import EventManager, EventType
from logic.auction_event_detector import AuctionEventDetector
from logic.halfway_event_detector import HalfwayEventDetector
from logic.dip_buy_event_detector import DipBuyEventDetector
from logic.leader_event_detector import LeaderEventDetector
from logic.qmt_tick_monitor import get_tick_monitor
from logic.event_recorder import get_event_recorder
from logic.logger import get_logger

logger = get_logger(__name__)


class EventDrivenMonitor:
    """
    事件驱动持续监控器 - 第二阶段框架
    
    核心功能：
    - 事件驱动扫描（推荐）
    - 固定间隔扫描（备用）
    - 状态指纹对比
    - 智能快照保存
    """
    
    def __init__(
        self,
        scan_interval: int = 300,
        mode: str = "event_driven",
        monitor_stocks: List[str] = None
    ):
        """
        初始化事件驱动监控器
        
        Args:
            scan_interval: 扫描间隔（秒），默认300秒（5分钟）
            mode: 运行模式
                  - "event_driven": 事件驱动模式（推荐）
                  - "fixed_interval": 固定间隔模式
            monitor_stocks: 监控的股票列表（事件驱动模式下使用）
        """
        self.scan_interval = scan_interval
        self.mode = mode
        self.monitor_stocks = monitor_stocks or []
        
        # 初始化核心组件
        self.scanner = FullMarketScanner()
        self.market_checker = MarketStatusChecker()
        self.event_manager = EventManager()
        self.event_recorder = get_event_recorder()  # 初始化事件记录器
        
        # 状态管理
        self.last_signature = None
        self.scan_count = 0
        self.event_count = 0
        self.save_count = 0
        self.start_time = None
        
        # 初始化事件检测器
        self._init_event_detectors()
        
        # 初始化QMT Tick监控器（事件驱动模式）
        self.tick_monitor = None
        if self.mode == "event_driven":
            self._init_tick_monitor()
    
    def _init_event_detectors(self):
        """初始化所有事件检测器"""
        # 集合竞价战法事件检测器
        auction_detector = AuctionEventDetector()
        self.event_manager.register_detector(auction_detector)
        
        # 半路战法事件检测器
        halfway_detector = HalfwayEventDetector()
        self.event_manager.register_detector(halfway_detector)
        
        # 低吸战法事件检测器
        dip_detector = DipBuyEventDetector()
        self.event_manager.register_detector(dip_detector)
        
        # 龙头战法事件检测器
        leader_detector = LeaderEventDetector()
        self.event_manager.register_detector(leader_detector)
        
        logger.info(f"✅ 事件检测器初始化完成: {len(self.event_manager.detectors)} 个")
    
    def _init_tick_monitor(self):
        """初始化QMT Tick监控器"""
        try:
            self.tick_monitor = get_tick_monitor()
            
            # 添加事件回调
            self.tick_monitor.add_event_callback(self._on_tick_update)
            
            logger.info("✅ QMT Tick监控器初始化成功")
        except Exception as e:
            logger.error(f"❌ QMT Tick监控器初始化失败: {e}")
            self.tick_monitor = None
    
    def _on_tick_update(self, stock_code: str, tick_data: Dict[str, Any]):
        """
        Tick数据更新回调
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
        """
        try:
            # 构建上下文信息
            context = self._build_context(stock_code, tick_data)
            
            # 检测事件
            events = self.event_manager.detect_events(tick_data, context)
            
            if events:
                self.event_count += len(events)
                for event in events:
                    logger.info(f"🔔 检测到事件: {event.stock_code} - {event.description}")
                    
                    # 自动记录事件到数据库
                    try:
                        record_id = self.event_recorder.record_event(event, tick_data)
                        logger.info(f"💾 事件已记录到数据库 (ID: {record_id})")
                    except Exception as e:
                        logger.error(f"❌ 记录事件失败: {e}")
        
        except Exception as e:
            logger.error(f"❌ 处理Tick更新失败: {e}")
    
    def _build_context(self, stock_code: str, tick_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建上下文信息
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
        
        Returns:
            上下文字典
        """
        context = {
            'yesterday_close': tick_data.get('close', 0),
            'yesterday_volume': 0,  # 需要从其他地方获取
            'ma5': 0,  # 需要从K线数据获取
            'ma10': 0,
            'ma20': 0,
            'sector_data': {},  # 需要从板块数据获取
            'yesterday_data': {}  # 需要从历史数据获取
        }
        
        return context
    
    def is_trading_time(self) -> bool:
        """判断当前是否在交易时间内"""
        return self.market_checker.is_trading_time()
    
    def save_snapshot(self, results: dict, mode: str):
        """
        保存快照（带状态指纹对比）
        
        Args:
            results: 扫描结果
            mode: 扫描模式
        """
        # 生成状态指纹
        current_signature = self.scanner.generate_state_signature(results)
        
        # 对比状态指纹
        if current_signature != self.last_signature:
            # 状态发生变化，保存快照
            os.makedirs('data/scan_results', exist_ok=True)
            
            # 使用时间戳命名，避免覆盖
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filename = f"data/scan_results/{timestamp}_{mode}.json"
            
            output = {
                'scan_time': datetime.now().isoformat(),
                'mode': mode,
                'state_signature': current_signature,
                'state_changed': True,
                'summary': {
                    'opportunities': len(results['opportunities']),
                    'watchlist': len(results['watchlist']),
                    'blacklist': len(results['blacklist'])
                },
                'results': results
            }
            
            # 自定义 JSON 编码器处理 datetime.date 对象
            class DateTimeEncoder(json.JSONEncoder):
                def default(self, obj):
                    if hasattr(obj, 'strftime'):
                        return obj.strftime('%Y-%m-%d')
                    elif hasattr(obj, 'isoformat'):
                        return obj.isoformat()
                    return super().default(obj)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
            
            self.last_signature = current_signature
            self.save_count += 1
            
            logger.info(f"💾 [状态变化] 快照已保存: {filename}")
            logger.info(f"   状态指纹: {current_signature[:8]}...")
        else:
            logger.info(f"⏭️  [状态未变] 跳过保存，状态指纹: {current_signature[:8]}...")
    
    def print_summary(self, results: dict):
        """打印扫描结果摘要"""
        print("\n" + "=" * 80)
        print(f"📊 扫描完成 #{self.scan_count} - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)
        print(f"✅ 机会池: {len(results['opportunities'])} 只")
        print(f"⚠️  观察池: {len(results['watchlist'])} 只")
        print(f"❌ 黑名单: {len(results['blacklist'])} 只")
        print(f"📈 系统置信度: {results['confidence']*100:.1f}%")
        print(f"💰 今日建议最大总仓位: {results['position_limit']*100:.1f}%")
        print(f"🎯 累计保存快照: {self.save_count} 次")
        print(f"🔔 累计检测事件: {self.event_count} 次")
        
        # 显示机会池前3只
        if results['opportunities']:
            print(f"\n🔥 机会池 TOP3:")
            for item in results['opportunities'][:3]:
                risk_score = item.get('risk_score', 0)
                capital_type = item.get('capital_type', 'UNKNOWN')
                trap_signals = item.get('trap_signals', [])
                signal_str = f" 诱多信号: {', '.join(trap_signals)}" if trap_signals else ""
                print(f"   {item['code']} - 风险: {risk_score:.2f} - 类型: {capital_type}{signal_str}")
        
        print("=" * 80 + "\n")
    
    def run_fixed_interval(self):
        """运行固定间隔模式"""
        logger.info("🔄 切换到固定间隔模式")
        
        while True:
            # 检查是否在交易时间
            if not self.is_trading_time():
                logger.info(f"⏰ 当前不在交易时间，等待中...")
                time.sleep(60)
                continue
            
            # 执行扫描
            logger.info(f"\n🔍 开始扫描 #{self.scan_count + 1}")
            logger.info("-" * 80)
            
            try:
                results = self.scanner.scan_with_risk_management(mode='intraday')
                self.scan_count += 1
                
                # 打印摘要
                self.print_summary(results)
                
                # 保存快照（带状态指纹对比）
                self.save_snapshot(results, mode='intraday')
                
            except Exception as e:
                logger.error(f"❌ 扫描失败: {e}")
                import traceback
                traceback.print_exc()
            
            # 等待下一次扫描
            logger.info(f"⏱️  等待 {self.scan_interval} 秒后进行下一次扫描...")
            time.sleep(self.scan_interval)
    
    def run_event_driven(self):
        """运行事件驱动模式"""
        logger.info("🎯 切换到事件驱动模式")
        
        # 订阅监控股票
        if self.tick_monitor and self.monitor_stocks:
            try:
                self.tick_monitor.subscribe(self.monitor_stocks)
                self.tick_monitor.start()
            except Exception as e:
                logger.error(f"❌ 启动Tick监控失败: {e}")
                # 回退到固定间隔模式
                logger.info("🔄 回退到固定间隔模式")
                self.run_fixed_interval()
                return
        
        while True:
            # 检查是否在交易时间
            if not self.is_trading_time():
                logger.info(f"⏰ 当前不在交易时间，等待中...")
                time.sleep(60)
                continue
            
            # 检查是否有事件触发
            if self.event_manager.should_trigger_scan():
                logger.info(f"\n🔥 事件触发扫描！")
                logger.info("-" * 80)
                
                try:
                    results = self.scanner.scan_with_risk_management(mode='intraday')
                    self.scan_count += 1
                    
                    # 打印摘要
                    self.print_summary(results)
                    
                    # 保存快照（带状态指纹对比）
                    self.save_snapshot(results, mode='intraday')
                    
                    # 标记扫描完成
                    self.event_manager.mark_scan_complete()
                    
                except Exception as e:
                    logger.error(f"❌ 扫描失败: {e}")
                    import traceback
                    traceback.print_exc()
                    self.event_manager.mark_scan_complete()
            else:
                # 显示心跳日志
                logger.info(f"💓 监控中... (累计事件: {self.event_count})")
            
            # 等待下一次检查
            time.sleep(10)  # 每10秒检查一次
    
    def run(self):
        """运行持续监控"""
        self.start_time = datetime.now()
        
        logger.info("=" * 80)
        logger.info("🚀 事件驱动持续监控启动 - 第二阶段框架")
        logger.info("=" * 80)
        logger.info(f"📅 启动时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"⏱️  扫描间隔: {self.scan_interval} 秒 ({self.scan_interval/60:.1f} 分钟)")
        logger.info(f"🎯 模式: {self.mode}")
        logger.info(f"🎯 智能快照: 仅在状态变化时保存")
        
        if self.mode == "event_driven":
            logger.info(f"🎯 事件驱动: 支持 {len(self.event_manager.detectors)} 个事件检测器")
            logger.info(f"📊 监控股票: {len(self.monitor_stocks)} 只")
        
        logger.info("=" * 80)
        
        print("\n🎯 事件驱动监控已启动，按 Ctrl+C 停止")
        print("=" * 80 + "\n")
        
        try:
            if self.mode == "event_driven":
                self.run_event_driven()
            else:
                self.run_fixed_interval()
                
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 80)
            logger.info("🛑 持续监控已停止")
            logger.info("=" * 80)
            logger.info(f"📊 运行统计:")
            logger.info(f"   总扫描次数: {self.scan_count}")
            logger.info(f"   总检测事件: {self.event_count}")
            logger.info(f"   快照保存次数: {self.save_count}")
            logger.info(f"   运行时长: {datetime.now() - self.start_time}")
            logger.info("=" * 80)
            
            # 停止Tick监控器
            if self.tick_monitor:
                self.tick_monitor.stop()


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='事件驱动持续监控')
    parser.add_argument(
        '--mode',
        type=str,
        default='event_driven',
        choices=['event_driven', 'fixed_interval'],
        help='运行模式'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='扫描间隔（秒），仅在固定间隔模式下生效'
    )
    parser.add_argument(
        '--stocks',
        type=str,
        nargs='+',
        default=[],
        help='监控的股票列表，仅在事件驱动模式下生效'
    )
    
    args = parser.parse_args()
    
    # 创建监控器
    monitor = EventDrivenMonitor(
        scan_interval=args.interval,
        mode=args.mode,
        monitor_stocks=args.stocks
    )
    
    # 运行监控
    monitor.run()