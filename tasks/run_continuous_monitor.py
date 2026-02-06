#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持续监控脚本 - 第一阶段基础框架

功能：
1. 在交易时间内持续运行（9:25-15:00）
2. 每5分钟执行一次全市场扫描
3. 生成状态指纹，检测信号变化
4. 只有在状态变化时才保存快照
5. 输出实时日志到命令行

Author: iFlow CLI
Version: V1.0
"""

import time
import os
import sys
import json
from datetime import datetime, time as dt_time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.full_market_scanner import FullMarketScanner
from logic.market_status import MarketStatusChecker
from logic.logger import get_logger

logger = get_logger(__name__)


class ContinuousMonitor:
    """
    持续监控器 - 第一阶段基础框架
    
    核心功能：
    - 定时扫描（每5分钟）
    - 状态指纹对比
    - 智能快照保存
    """
    
    def __init__(self, scan_interval: int = 300):
        """
        初始化持续监控器
        
        Args:
            scan_interval: 扫描间隔（秒），默认300秒（5分钟）
        """
        self.scan_interval = scan_interval
        self.scanner = FullMarketScanner()
        self.market_checker = MarketStatusChecker()
        self.last_signature = None
        self.scan_count = 0
        self.save_count = 0
        self.start_time = None
        
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
    
    def run(self):
        """运行持续监控"""
        self.start_time = datetime.now()
        
        logger.info("=" * 80)
        logger.info("🚀 持续监控启动 - 第一阶段基础框架")
        logger.info("=" * 80)
        logger.info(f"📅 启动时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"⏱️  扫描间隔: {self.scan_interval} 秒 ({self.scan_interval/60:.1f} 分钟)")
        logger.info(f"🎯 模式: 智能快照（仅在状态变化时保存）")
        logger.info("=" * 80)
        
        print("\n🎯 持续监控已启动，按 Ctrl+C 停止")
        print("=" * 80 + "\n")
        
        try:
            while True:
                # 检查是否在交易时间（使用 IntraDayMonitor 判断）
                from logic.intraday_monitor import IntraDayMonitor
                monitor = IntraDayMonitor()
                phase = monitor.get_trading_phase()
                
                # 非交易时间：收盘后、周末
                if phase in ['AFTER_HOURS', 'WEEKEND']:
                    current_time = datetime.now()
                    logger.info(f"⏰ 当前阶段: {phase} ({current_time.strftime('%H:%M:%S')})，等待中...")
                    time.sleep(60)  # 每分钟检查一次
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
                
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 80)
            logger.info("🛑 持续监控已停止")
            logger.info("=" * 80)
            logger.info(f"📊 运行统计:")
            logger.info(f"   总扫描次数: {self.scan_count}")
            logger.info(f"   快照保存次数: {self.save_count}")
            logger.info(f"   运行时长: {datetime.now() - self.start_time}")
            logger.info("=" * 80)


if __name__ == "__main__":
    # 创建监控器（扫描间隔5分钟）
    monitor = ContinuousMonitor(scan_interval=300)
    
    # 运行监控
    monitor.run()