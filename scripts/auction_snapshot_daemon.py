#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价快照守护进程（独立运行，无UI）

功能：
1. 9:15-9:25 每分钟自动保存全市场竞价数据到 Redis
2. 日志记录到 logs/auction_snapshot.log

运行：
python scripts/auction_snapshot_daemon.py

Author: MyQuantTool Team
Date: 2026-02-10
"""

import sys
import os
import time
import json
from datetime import datetime, time as dt_time
from typing import List, Dict

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from xtquant import xtdata
from logic.auction_snapshot_manager import AuctionSnapshotManager
from logic.database_manager import DatabaseManager
from logic.utils.logger import get_logger

logger = get_logger(__name__)

class AuctionSnapshotDaemon:
    """竞价快照守护进程"""
    
    def __init__(self):
        """初始化守护进程"""
        self.db_manager = DatabaseManager()
        
        # 🔧 修复：强制初始化Redis连接（解决懒加载问题）
        try:
            self.db_manager._init_redis()
            logger.info("✅ Redis连接已强制初始化")
        except Exception as e:
            logger.warning(f"⚠️ Redis初始化失败: {e}")
        
        self.snapshot_manager = AuctionSnapshotManager(self.db_manager)
        
        # 获取全市场股票列表
        try:
            self.all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
            logger.info(f"✅ 获取股票列表成功: {len(self.all_stocks)} 只")
        except Exception as e:
            logger.error(f"❌ 获取股票列表失败: {e}")
            self.all_stocks = []
        
        logger.info("✅ 竞价快照守护进程初始化完成")
    
    def is_auction_time(self) -> bool:
        """
        判断当前是否在竞价时间
        
        Returns:
            bool: 9:15-9:25 返回 True
        """
        now = datetime.now()
        current_time = now.time()
        
        # 竞价时间：9:15-9:25
        auction_start = dt_time(9, 15, 0)
        auction_end = dt_time(9, 25, 0)
        
        # 判断是否为交易日（周一到周五）
        is_trading_day = now.weekday() < 5
        
        return is_trading_day and auction_start <= current_time <= auction_end
    
    def save_market_auction_snapshot(self) -> Dict[str, int]:
        """
        保存全市场竞价快照
        
        Returns:
            {
                'total': 总股票数,
                'saved': 成功保存数,
                'failed': 失败数
            }
        """
        if not self.all_stocks:
            logger.warning("⚠️ 股票列表为空，跳过保存")
            return {'total': 0, 'saved': 0, 'failed': 0}
        
        total = len(self.all_stocks)
        saved = 0
        failed = 0
        batch_size = 1000
        
        logger.info(f"📝 开始保存全市场竞价快照 ({total} 只股票)")
        
        for i in range(0, total, batch_size):
            batch = self.all_stocks[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            try:
                # 获取 Tick 数据
                tick_data = xtdata.get_full_tick(batch)
                
                if not isinstance(tick_data, dict):
                    logger.warning(f"⚠️ 批次 {batch_num} 返回数据异常")
                    failed += len(batch)
                    continue
                
                # 保存每只股票的竞价数据
                for code in batch:
                    tick = tick_data.get(code, {})

                    if not isinstance(tick, dict) or not tick:
                        failed += 1
                        continue

                    # 提取竞价数据
                    volume = (
                        tick.get('totalVolume') or
                        tick.get('volume') or
                        tick.get('total_volume') or
                        0
                    )
                    amount = tick.get('amount', 0)
                    last_price = tick.get('lastPrice', 0)
                    last_close = tick.get('lastClose', 0)

                    # 🔥 紧急修复：竞价期间volume和amount都是0，改为只要有lastPrice就保存
                    # 集合竞价期间（9:15-9:25），QMT的volume和amount都是0，但lastPrice有值
                    if last_price > 0:
                        auction_data = {
                            'auction_volume': volume,
                            'auction_amount': amount,
                            'last_price': last_price,
                            'last_close': last_close,
                            'timestamp': datetime.now().timestamp(),
                            # 额外保存买盘和卖盘信息
                            'bid_vol': tick.get('bidVol', []),
                            'ask_vol': tick.get('askVol', []),
                            'stock_status': tick.get('stockStatus', 0)
                        }

                        # 保存到 Redis
                        self.snapshot_manager.save_auction_snapshot(code, auction_data)
                        saved += 1
                    else:
                        failed += 1
                
                logger.info(f"  批次 {batch_num} 完成: 保存 {len(batch)} 只")
            
            except Exception as e:
                logger.error(f"❌ 批次 {batch_num} 处理异常: {e}")
                failed += len(batch)
                continue
        
        result = {
            'total': total,
            'saved': saved,
            'failed': failed
        }
        
        coverage_rate = (saved / total * 100) if total > 0 else 0
        logger.info(f"✅ 竞价快照保存完成: 成功 {saved}/{total} ({coverage_rate:.1f}%)")
        
        return result
    
    def run(self):
        """
        运行守护进程（优化版）
        
        策略：
        1. 9:15-9:24: 每分钟保存一次（监控用）
        2. 9:25-9:29: 最终保存（高优先级）✅
        3. 9:30 后: 退出
        """
        logger.info("=" * 80)
        logger.info("🚀 竞价快照守护进程启动")
        logger.info("=" * 80)
        
        # 标记是否已完成最终保存
        final_snapshot_saved = False
        
        while True:
            try:
                now = datetime.now()
                current_time = now.time()
                
                # 🔥 关键窗口：9:25-9:30（竞价结束，数据仍可用）
                if dt_time(9, 25, 0) <= current_time < dt_time(9, 30, 0):
                    if not final_snapshot_saved:
                        logger.info(f"\n⏰ 当前时间: {now.strftime('%H:%M:%S')} (竞价已结束，开始最终保存)")
                        logger.info("=" * 80)
                        logger.info("🎯 执行最终竞价快照保存（高优先级）")
                        logger.info("=" * 80)
                        
                        # 保存全市场竞价快照
                        result = self.save_market_auction_snapshot()
                        
                        # 标记已完成
                        final_snapshot_saved = True
                        
                        logger.info("=" * 80)
                        logger.info("✅ 最终竞价快照保存完成，等待连续竞价开始...")
                        logger.info("=" * 80)
                        
                        # 等待到 9:30
                        wait_seconds = (
                            datetime.combine(now.date(), dt_time(9, 30, 0)) - now
                        ).total_seconds()
                        logger.info(f"⏳ 距离连续竞价开始还有 {wait_seconds:.0f} 秒")
                        time.sleep(wait_seconds + 5)  # 等到 9:30:05
                        
                        logger.info("✅ 今日竞价快照任务已完成，程序退出")
                        break
                    else:
                        # 已保存，等待退出
                        time.sleep(30)
                
                # 9:15-9:24: 监控保存（每分钟一次）
                elif dt_time(9, 15, 0) <= current_time < dt_time(9, 25, 0):
                    logger.info(f"\n⏰ 当前时间: {now.strftime('%H:%M:%S')} (竞价进行中)")
                    
                    # 保存一次（监控用）
                    result = self.save_market_auction_snapshot()
                    
                    # 等待 60 秒
                    logger.info(f"⏳ 等待 60 秒...")
                    time.sleep(60)
                
                # 9:30 后：退出
                elif current_time >= dt_time(9, 30, 0):
                    logger.info(f"⏰ 当前时间: {now.strftime('%H:%M:%S')} (连续竞价已开始)")
                    logger.info("✅ 今日竞价快照任务已完成，程序退出")
                    break
                
                # 9:15 前：等待
                else:
                    wait_seconds = (
                        datetime.combine(now.date(), dt_time(9, 15, 0)) - now
                    ).total_seconds()
                    logger.info(f"⏰ 当前时间: {now.strftime('%H:%M:%S')} (等待竞价开始)")
                    logger.info(f"⏳ 距离竞价开始还有 {wait_seconds/60:.1f} 分钟")
                    time.sleep(60)
            
            except KeyboardInterrupt:
                logger.info("\n⚠️ 用户中断，程序退出")
                break
            except Exception as e:
                logger.error(f"❌ 守护进程异常: {e}")
                logger.info("⏳ 等待 60 秒后重试...")
                time.sleep(60)
        
        logger.info("=" * 80)
        logger.info("🛑 竞价快照守护进程停止")
        logger.info("=" * 80)

def main():
    """主函数"""
    daemon = AuctionSnapshotDaemon()
    daemon.run()

if __name__ == "__main__":
    main()