"""
K线数据缓存系统 (Kline Cache System)

功能:
1. 缓存当日K线数据，避免重复请求AkShare
2. 支持自动过期清理
3. 减少API限流风险

作者: MyQuantTool Team
版本: v1.0
创建日期: 2026-02-03
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class KlineCache:
    """K线数据缓存器（单例模式）
    
    缓存当日K线数据，避免重复请求AkShare，减少API限流风险。
    缓存文件存储在 data/kline_cache/ 目录下。
    
    Attributes:
        cache_dir: 缓存目录路径
        ttl: 缓存过期时间（天）
        
    Example:
        >>> cache = KlineCache()
        >>> kline_data = cache.get_cached_kline("300997", "20260203")
        >>> if kline_data is not None:
        >>>     print("使用缓存数据")
        >>> else:
        >>>     kline_data = akshare.get_kline(...)
        >>>     cache.save_kline("300997", "20260203", kline_data)
    """
    
    _instance: Optional['KlineCache'] = None
    _initialized: bool = False
    
    def __init__(self, cache_dir: str = "data/kline_cache", ttl: int = 1):
        """
        初始化K线缓存器
        
        Args:
            cache_dir: 缓存目录路径
            ttl: 缓存过期时间（天），默认1天
        """
        if KlineCache._initialized:
            return
        
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl  # 缓存过期时间（天）
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 启动时自动清理过期缓存
        self.clear_expired_cache()
        
        KlineCache._initialized = True
        logger.info(f"✅ KlineCache 初始化成功，缓存目录: {self.cache_dir}, TTL: {ttl}天")
    
    @staticmethod
    def get_instance() -> 'KlineCache':
        """获取KlineCache单例实例"""
        if KlineCache._instance is None:
            KlineCache._instance = KlineCache()
        return KlineCache._instance
    
    def get_cache_key(self, stock_code: str, date: str) -> str:
        """
        生成缓存键名
        
        Args:
            stock_code: 股票代码
            date: 日期（YYYYMMDD）
            
        Returns:
            缓存键名
        """
        return f"{stock_code}_{date}.csv"
    
    def get_cache_path(self, stock_code: str, date: str) -> Path:
        """
        获取缓存文件路径
        
        Args:
            stock_code: 股票代码
            date: 日期（YYYYMMDD）
            
        Returns:
            缓存文件路径
        """
        cache_key = self.get_cache_key(stock_code, date)
        return self.cache_dir / cache_key
    
    def get_cached_kline(self, stock_code: str, date: str) -> Optional[pd.DataFrame]:
        """
        获取缓存的K线数据
        
        Args:
            stock_code: 股票代码
            date: 日期（YYYYMMDD）
            
        Returns:
            K线数据（DataFrame），如果缓存不存在或已过期则返回None
        """
        cache_path = self.get_cache_path(stock_code, date)
        
        # 检查缓存文件是否存在
        if not cache_path.exists():
            logger.debug(f"缓存不存在: {cache_path}")
            return None
        
        # 检查缓存是否过期
        if self.is_expired(stock_code, date):
            logger.debug(f"缓存已过期: {cache_path}")
            # 删除过期缓存
            try:
                cache_path.unlink()
                logger.debug(f"已删除过期缓存: {cache_path}")
            except Exception as e:
                logger.warning(f"删除过期缓存失败: {e}")
            return None
        
        # 读取缓存
        try:
            df = pd.read_csv(cache_path)
            logger.debug(f"✅ 从缓存读取K线数据: {stock_code} {date}")
            return df
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            return None
    
    def save_kline(self, stock_code: str, date: str, data: pd.DataFrame) -> bool:
        """
        保存K线数据到缓存
        
        Args:
            stock_code: 股票代码
            date: 日期（YYYYMMDD）
            data: K线数据（DataFrame）
            
        Returns:
            是否保存成功
        """
        cache_path = self.get_cache_path(stock_code, date)
        
        try:
            # 确保缓存目录存在
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存到CSV
            data.to_csv(cache_path, index=False, encoding='utf-8')
            
            logger.info(f"✅ K线数据已缓存: {stock_code} {date}")
            return True
        except Exception as e:
            logger.error(f"保存K线缓存失败: {e}")
            return False
    
    def is_expired(self, stock_code: str, date: str) -> bool:
        """
        检查缓存是否过期
        
        Args:
            stock_code: 股票代码
            date: 日期（YYYYMMDD）
            
        Returns:
            是否过期
        """
        cache_path = self.get_cache_path(stock_code, date)
        
        if not cache_path.exists():
            return True
        
        try:
            # 获取文件修改时间
            file_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
            
            # 计算过期时间
            expiry_time = file_mtime + timedelta(days=self.ttl)
            
            # 检查是否过期
            is_expired = datetime.now() > expiry_time
            
            if is_expired:
                logger.debug(f"缓存已过期: {cache_path} (过期时间: {expiry_time})")
            
            return is_expired
        except Exception as e:
            logger.warning(f"检查缓存过期时间失败: {e}")
            return True
    
    def clear_cache(self, stock_code: str = None, date: str = None, days: int = None) -> int:
        """
        清理缓存
        
        Args:
            stock_code: 股票代码（可选，如果指定则只清理该股票的缓存）
            date: 日期（可选，如果指定则只清理该日期的缓存）
            days: 清理N天前的缓存（可选，如果指定则清理所有早于N天的缓存）
            
        Returns:
            清理的缓存文件数量
        """
        cleaned_count = 0
        
        try:
            # 遍历缓存目录
            for cache_file in self.cache_dir.glob("*.csv"):
                # 提取股票代码和日期
                cache_key = cache_file.stem  # 去掉.csv后缀
                parts = cache_key.split("_")
                
                if len(parts) < 2:
                    continue
                
                cached_code = parts[0]
                cached_date = parts[1]
                
                # 检查是否符合清理条件
                should_delete = False
                
                # 按股票代码清理
                if stock_code and cached_code != stock_code:
                    continue
                
                # 按日期清理
                if date and cached_date != date:
                    continue
                
                # 按天数清理
                if days:
                    try:
                        cached_datetime = datetime.strptime(cached_date, "%Y%m%d")
                        if cached_datetime < datetime.now() - timedelta(days=days):
                            should_delete = True
                    except:
                        continue
                else:
                    should_delete = True
                
                # 删除缓存文件
                if should_delete:
                    cache_file.unlink()
                    cleaned_count += 1
                    logger.debug(f"已删除缓存: {cache_file.name}")
            
            if cleaned_count > 0:
                logger.info(f"✅ 已清理 {cleaned_count} 个缓存文件")
            
            return cleaned_count
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return 0
    
    def clear_expired_cache(self) -> int:
        """
        清理所有过期缓存
        
        Returns:
            清理的缓存文件数量
        """
        logger.debug("开始清理过期缓存...")
        return self.clear_cache(days=self.ttl)
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        cache_files = list(self.cache_dir.glob("*.csv"))
        
        total_size = sum(f.stat().st_size for f in cache_files)
        total_count = len(cache_files)
        
        # 按股票代码统计
        stock_stats = {}
        for cache_file in cache_files:
            cache_key = cache_file.stem
            parts = cache_key.split("_")
            if len(parts) >= 2:
                stock_code = parts[0]
                stock_stats[stock_code] = stock_stats.get(stock_code, 0) + 1
        
        return {
            'total_count': total_count,
            'total_size': total_size,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'stock_stats': stock_stats,
            'cache_dir': str(self.cache_dir),
            'ttl': self.ttl
        }
    
    def clear_all(self) -> int:
        """
        清理所有缓存
        
        Returns:
            清理的缓存文件数量
        """
        logger.info("开始清理所有缓存...")
        return self.clear_cache()


# 便捷函数
def get_kline_cache() -> KlineCache:
    """获取KlineCache单例实例的便捷函数"""
    return KlineCache.get_instance()


# 导出
__all__ = ['KlineCache', 'get_kline_cache']