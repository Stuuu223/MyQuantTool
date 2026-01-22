"""
竞价快照管理器

功能：
1. 在 9:25-9:30 竞价期间，保存竞价数据到 Redis
2. 在 9:30 以后，如果 API 没有竞价数据，从 Redis 恢复
3. 解决重启程序后竞价数据丢失的问题

原理：
- 竞价期间（9:25-9:30）：API 返回的 volume 就是竞价量，保存到 Redis
- 盘中/盘后（9:30 以后）：API 返回的是全天总成交量，从 Redis 恢复竞价量
"""

import json
import time
from datetime import datetime
from typing import Dict, Optional, Any
from logic.logger import get_logger

logger = get_logger(__name__)


class AuctionSnapshotManager:
    """
    竞价快照管理器
    
    用于保存和恢复竞价数据，防止重启程序后数据丢失
    """
    
    def __init__(self, db_manager=None):
        """
        初始化竞价快照管理器
        
        Args:
            db_manager: DatabaseManager 实例（用于访问 Redis）
        """
        self.db_manager = db_manager
        self.is_available = False
        
        if db_manager and db_manager._redis_client:
            try:
                # 测试 Redis 连接
                db_manager._redis_client.ping()
                self.is_available = True
                logger.info("✅ 竞价快照管理器初始化成功（Redis 可用）")
            except Exception as e:
                logger.warning(f"⚠️ Redis 连接失败，竞价快照功能不可用: {e}")
        else:
            logger.warning("⚠️ 未提供 DatabaseManager 或 Redis 未连接，竞价快照功能不可用")
    
    def get_today_str(self) -> str:
        """获取今天的日期字符串（格式：YYYYMMDD）"""
        return datetime.now().strftime("%Y%m%d")
    
    def is_auction_time(self) -> bool:
        """
        判断当前是否在竞价时间（9:15-9:30）
        
        Returns:
            bool: 是否在竞价时间
        """
        now = datetime.now()
        current_time = now.time()
        
        # 竞价时间：9:15:00 - 9:30:00（包含集合竞价 9:15-9:25 和竞价真空期 9:25-9:30）
        auction_start = current_time.replace(hour=9, minute=15, second=0, microsecond=0)
        auction_end = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        
        return auction_start <= current_time < auction_end
    
    def is_after_market_open(self) -> bool:
        """
        判断当前是否在开盘之后（9:30 以后）
        
        Returns:
            bool: 是否在开盘之后
        """
        now = datetime.now()
        current_time = now.time()
        
        # 开盘时间：9:30:00
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        
        return current_time >= market_open
    
    def save_auction_snapshot(self, stock_code: str, auction_data: Dict[str, Any]) -> bool:
        """
        保存竞价快照到 Redis
        
        Args:
            stock_code: 股票代码（6位数字，如 '600058'）
            auction_data: 竞价数据字典，包含：
                - auction_volume: 竞价量（手）
                - auction_amount: 竞价金额（元）
                - auction_aggression: 竞价抢筹度（%）
                - timestamp: 时间戳
        
        Returns:
            bool: 是否保存成功
        """
        if not self.is_available:
            logger.debug("Redis 不可用，跳过保存竞价快照")
            return False
        
        try:
            today = self.get_today_str()
            # Key 格式: auction:20260115:600058
            key = f"auction:{today}:{stock_code}"
            
            # 添加保存时间戳
            auction_data['snapshot_time'] = time.time()
            
            # 存为 JSON 字符串
            value = json.dumps(auction_data, ensure_ascii=False)
            
            # 设置过期时间：24小时后自动删除（第二天就是新数据了）
            expire_seconds = 86400
            
            success = self.db_manager.redis_set(key, value, expire=expire_seconds)
            
            if success:
                logger.debug(f"✅ [竞价快照] 已保存 {stock_code} 的竞价数据")
            
            return success
        
        except Exception as e:
            logger.error(f"❌ 保存竞价快照失败 {stock_code}: {e}")
            return False
    
    def load_auction_snapshot(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        从 Redis 加载竞价快照
        
        Args:
            stock_code: 股票代码（6位数字，如 '600058'）
        
        Returns:
            dict: 竞价数据字典，如果不存在则返回 None
        """
        if not self.is_available:
            return None
        
        try:
            today = self.get_today_str()
            # Key 格式: auction:20260115:600058
            key = f"auction:{today}:{stock_code}"
            
            raw_data = self.db_manager.redis_get(key)
            
            if raw_data:
                auction_data = json.loads(raw_data)
                logger.debug(f"✅ [竞价快照] 已从 Redis 恢复 {stock_code} 的竞价数据")
                return auction_data
            else:
                logger.debug(f"⚠️ [竞价快照] 未找到 {stock_code} 的竞价数据")
                return None
        
        except Exception as e:
            logger.error(f"❌ 加载竞价快照失败 {stock_code}: {e}")
            return None
    
    def delete_auction_snapshot(self, stock_code: str) -> bool:
        """
        删除竞价快照
        
        Args:
            stock_code: 股票代码（6位数字，如 '600058'）
        
        Returns:
            bool: 是否删除成功
        """
        if not self.is_available:
            return False
        
        try:
            today = self.get_today_str()
            key = f"auction:{today}:{stock_code}"
            
            success = self.db_manager.redis_delete(key)
            
            if success:
                logger.debug(f"✅ [竞价快照] 已删除 {stock_code} 的竞价数据")
            
            return success
        
        except Exception as e:
            logger.error(f"❌ 删除竞价快照失败 {stock_code}: {e}")
            return False
    
    def clear_today_snapshots(self) -> int:
        """
        清除今天的所有竞价快照（用于测试或重置）
        
        Returns:
            int: 清除的数量
        """
        if not self.is_available:
            return 0
        
        try:
            # 注意：这个操作需要 Redis 的 SCAN 命令，比较复杂
            # 这里暂时不实现，因为 Redis 会自动过期
            logger.warning("⚠️ clear_today_snapshots 功能暂未实现（Redis 会自动过期）")
            return 0
        
        except Exception as e:
            logger.error(f"❌ 清除竞价快照失败: {e}")
            return 0
    
    def get_snapshot_status(self) -> Dict[str, Any]:
        """
        获取快照管理器的状态信息
        
        Returns:
            dict: 状态信息
        """
        return {
            'is_available': self.is_available,
            'is_auction_time': self.is_auction_time(),
            'is_after_market_open': self.is_after_market_open(),
            'today': self.get_today_str(),
            'redis_connected': self.is_available
        }