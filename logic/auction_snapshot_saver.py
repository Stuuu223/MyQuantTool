#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞价快照自动保存器

功能：
- 在竞价期间（9:15-9:30）自动保存竞价快照到Redis
- 支持定时任务调用
- 支持手动调用

Author: iFlow CLI
Version: V19.6
"""

import time
from datetime import datetime
from typing import List, Dict, Any
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.auction_snapshot_manager import AuctionSnapshotManager

logger = get_logger(__name__)


class AuctionSnapshotSaver:
    """竞价快照自动保存器"""
    
    def __init__(self, db_manager=None):
        """
        初始化竞价快照保存器
        
        Args:
            db_manager: DatabaseManager 实例
        """
        self.db_manager = db_manager or DataManager()
        self.snapshot_manager = None
        
        # 初始化竞价快照管理器
        if hasattr(self.db_manager, '_redis_client') and self.db_manager._redis_client:
            try:
                self.snapshot_manager = AuctionSnapshotManager(self.db_manager)
                if self.snapshot_manager.is_available:
                    logger.info("✅ 竞价快照保存器初始化成功")
                else:
                    logger.warning("⚠️ 竞价快照管理器不可用")
            except Exception as e:
                logger.error(f"❌ 竞价快照管理器初始化失败: {e}")
        else:
            logger.warning("⚠️ Redis未连接，竞价快照保存器不可用")
    
    def is_auction_time(self) -> bool:
        """
        判断当前是否在竞价时间（9:15-9:30）
        
        Returns:
            bool: 是否在竞价时间
        """
        now = datetime.now()
        current_time = now.time()
        
        # 竞价时间：9:15:00 - 9:30:00
        from datetime import time as dt_time
        auction_start = dt_time(9, 15, 0)
        auction_end = dt_time(9, 30, 0)
        
        return auction_start <= current_time < auction_end
    
    def save_auction_snapshot_for_stocks(self, stock_list: List[str] = None) -> Dict[str, Any]:
        """
        为指定股票列表保存竞价快照
        
        Args:
            stock_list: 股票代码列表，如果为None则获取全市场股票
        
        Returns:
            dict: 保存结果统计
        """
        if not self.snapshot_manager or not self.snapshot_manager.is_available:
            return {
                'success': False,
                'error': '竞价快照管理器不可用',
                'saved_count': 0,
                'failed_count': 0
            }
        
        if not self.is_auction_time():
            return {
                'success': False,
                'error': '当前不在竞价时间（9:15-9:30）',
                'saved_count': 0,
                'failed_count': 0
            }
        
        logger.info("🚀 开始保存竞价快照...")
        
        # 如果没有提供股票列表，获取全市场股票
        if stock_list is None:
            try:
                import akshare as ak
                stock_list_df = ak.stock_info_a_code_name()
                stock_list = stock_list_df['code'].tolist()
                logger.info(f"获取到 {len(stock_list)} 只股票")
            except Exception as e:
                logger.error(f"获取股票列表失败: {e}")
                return {
                    'success': False,
                    'error': f'获取股票列表失败: {str(e)}',
                    'saved_count': 0,
                    'failed_count': 0
                }
        
        saved_count = 0
        failed_count = 0
        
        # 获取实时数据
        try:
            realtime_data = self.db_manager.get_fast_price(stock_list)
            logger.info(f"获取到 {len(realtime_data)} 只股票的实时数据")
            
            for code, data in realtime_data.items():
                try:
                    # 提取竞价数据
                    auction_data = {
                        'auction_volume': data.get('volume', 0),  # 竞价量（手）
                        'auction_amount': data.get('amount', 0),  # 竞价金额（元）
                        'auction_price': data.get('now', 0),  # 竞价价格
                        'auction_aggression': 0,  # 竞价抢筹度（需要计算）
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # 保存竞价快照
                    success = self.snapshot_manager.save_auction_snapshot(code, auction_data)
                    
                    if success:
                        saved_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    logger.warning(f"保存股票 {code} 竞价快照失败: {e}")
                    failed_count += 1
            
            logger.info(f"✅ 竞价快照保存完成：成功 {saved_count} 只，失败 {failed_count} 只")
            
            return {
                'success': True,
                'saved_count': saved_count,
                'failed_count': failed_count,
                'total_count': len(realtime_data)
            }
            
        except Exception as e:
            logger.error(f"❌ 保存竞价快照失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'saved_count': saved_count,
                'failed_count': failed_count
            }
    
    def run_auction_snapshot_task(self) -> bool:
        """
        运行竞价快照保存任务（用于定时任务）
        
        Returns:
            bool: 是否成功
        """
        logger.info("📅 执行竞价快照保存任务...")
        
        result = self.save_auction_snapshot_for_stocks()
        
        if result['success']:
            logger.info(f"✅ 竞价快照保存任务完成：成功 {result['saved_count']} 只")
            return True
        else:
            logger.error(f"❌ 竞价快照保存任务失败：{result.get('error', '未知错误')}")
            return False


# 便捷函数
def save_auction_snapshot_now(stock_list: List[str] = None) -> Dict[str, Any]:
    """
    立即保存竞价快照（便捷函数）
    
    Args:
        stock_list: 股票代码列表，如果为None则获取全市场股票
    
    Returns:
        dict: 保存结果统计
    """
    saver = AuctionSnapshotSaver()
    return saver.save_auction_snapshot_for_stocks(stock_list)


if __name__ == '__main__':
    print("=" * 80)
    print("🚀 竞价快照自动保存器")
    print("=" * 80)
    
    saver = AuctionSnapshotSaver()
    
    # 检查当前时间
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print(f"\n🕐 当前时间: {current_time}")
    
    # 检查是否在竞价时间
    if saver.is_auction_time():
        print("✅ 当前在竞价时间（9:15-9:30）")
        
        # 询问是否保存
        print("\n开始保存竞价快照...")
        result = saver.save_auction_snapshot_for_stocks()
        
        if result['success']:
            print(f"\n✅ 保存成功！")
            print(f"   成功: {result['saved_count']} 只")
            print(f"   失败: {result['failed_count']} 只")
            if 'total_count' in result:
                print(f"   总计: {result['total_count']} 只")
        else:
            print(f"\n❌ 保存失败: {result.get('error', '未知错误')}")
    else:
        print("⚠️ 当前不在竞价时间（9:15-9:30）")
        print("💡 请在竞价期间运行此程序")
    
    print("\n" + "=" * 80)