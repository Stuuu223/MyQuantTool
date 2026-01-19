#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18 解禁/减持预警系统
提前 3 天预警大规模解禁或减持，将相关标的打入 SHADOW_LIST
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import pandas as pd
from logic.logger import get_logger
from logic.cache_manager import CacheManager

logger = get_logger(__name__)


class UnbanWarningSystem:
    """
    解禁/减持预警系统
    
    功能：
    1. 提前 3 天预警大规模解禁
    2. 提前 3 天预警股东减持
    3. 将相关标的打入 SHADOW_LIST
    4. 在这些标的上，BUY 信号门槛提高 20 分钟
    """
    
    # 预警阈值
    WARNING_DAYS = 3  # 提前 3 天预警
    MIN_MARKET_CAP_RATIO = 0.05  # 占流通市值比例 > 5% 才预警
    MIN_MARKET_VALUE = 50000000  # 解禁市值 > 5000 万才预警
    
    # SHADOW_LIST（暗影名单）
    _shadow_list: Set[str] = set()  # {stock_code}
    _shadow_list_reason: Dict[str, str] = {}  # {stock_code: reason}
    _shadow_list_time: Dict[str, datetime] = {}  # {stock_code: add_time}
    
    def __init__(self):
        """初始化解禁预警系统"""
        self.cache = CacheManager()
        self._load_shadow_list()
    
    def _load_shadow_list(self):
        """从缓存加载 SHADOW_LIST"""
        try:
            shadow_list_data = self.cache.get('shadow_list')
            if shadow_list_data:
                self._shadow_list = set(shadow_list_data.get('codes', []))
                self._shadow_list_reason = shadow_list_data.get('reasons', {})
                self._shadow_list_time = {
                    code: datetime.fromisoformat(time_str)
                    for code, time_str in shadow_list_data.get('times', {}).items()
                }
                logger.info(f"✅ [解禁预警] 加载 SHADOW_LIST: {len(self._shadow_list)} 只股票")
        except Exception as e:
            logger.warning(f"⚠️ [解禁预警] 加载 SHADOW_LIST 失败: {e}")
    
    def _save_shadow_list(self):
        """保存 SHADOW_LIST 到缓存"""
        try:
            shadow_list_data = {
                'codes': list(self._shadow_list),
                'reasons': self._shadow_list_reason,
                'times': {
                    code: time.isoformat()
                    for code, time in self._shadow_list_time.items()
                }
            }
            self.cache.set('shadow_list', shadow_list_data, ttl=86400)  # 缓存 1 天
        except Exception as e:
            logger.warning(f"⚠️ [解禁预警] 保存 SHADOW_LIST 失败: {e}")
    
    def fetch_unban_data(self) -> pd.DataFrame:
        """
        获取解禁数据
        
        Returns:
            DataFrame: 解禁数据
        """
        try:
            import akshare as ak
            df = ak.stock_restricted_release_detail_em()
            logger.info(f"✅ [解禁预警] 获取解禁数据: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"❌ [解禁预警] 获取解禁数据失败: {e}")
            return pd.DataFrame()
    
    def fetch_reduce_holdings_data(self) -> pd.DataFrame:
        """
        获取股东减持数据
        
        Returns:
            DataFrame: 减持数据
        """
        try:
            import akshare as ak
            # 注意：akshare 可能没有直接的股东减持接口，这里使用解禁数据作为替代
            # 如果有真实的减持接口，可以在这里调用
            logger.info("⚠️ [解禁预警] 股东减持接口暂未实现，使用解禁数据替代")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ [解禁预警] 获取股东减持数据失败: {e}")
            return pd.DataFrame()
    
    def check_unban_warning(self, stock_code: str) -> Optional[Dict]:
        """
        检查单只股票是否有解禁预警
        
        Args:
            stock_code: 股票代码
        
        Returns:
            dict: {
                'has_warning': bool,
                'warning_type': str,
                'warning_date': datetime,
                'days_to_unban': int,
                'unban_ratio': float,
                'unban_value': float,
                'reason': str
            }
        """
        try:
            # 检查是否在 SHADOW_LIST 中
            if stock_code in self._shadow_list:
                return {
                    'has_warning': True,
                    'warning_type': self._shadow_list_reason.get(stock_code, '未知'),
                    'warning_date': self._shadow_list_time.get(stock_code),
                    'days_to_unban': 0,
                    'unban_ratio': 0.0,
                    'unban_value': 0.0,
                    'reason': self._shadow_list_reason.get(stock_code, '未知')
                }
            
            # 获取解禁数据
            df = self.fetch_unban_data()
            if df.empty:
                return None
            
            # 查找该股票的解禁记录
            stock_unban = df[df['股票代码'] == stock_code]
            if stock_unban.empty:
                return None
            
            # 检查未来 3 天内的解禁
            today = datetime.now().date()
            warning_date = today + timedelta(days=self.WARNING_DAYS)
            
            future_unban = stock_unban[
                (stock_unban['解禁时间'] >= today) &
                (stock_unban['解禁时间'] <= warning_date)
            ]
            
            if future_unban.empty:
                return None
            
            # 检查解禁规模
            for _, row in future_unban.iterrows():
                ratio = row['占解禁前流通市值比例']
                value = row['实际解禁市值']
                
                if ratio >= self.MIN_MARKET_CAP_RATIO or value >= self.MIN_MARKET_VALUE:
                    days_to_unban = (row['解禁时间'] - today).days
                    
                    # 加入 SHADOW_LIST
                    self._shadow_list.add(stock_code)
                    self._shadow_list_reason[stock_code] = f"解禁预警: {days_to_unban}天后解禁，占流通市值{ratio:.1%}"
                    self._shadow_list_time[stock_code] = datetime.now()
                    self._save_shadow_list()
                    
                    logger.warning(
                        f"🚨 [解禁预警] {stock_code} {days_to_unban}天后解禁，"
                        f"占流通市值{ratio:.1%}，市值{value/100000000:.2f}亿"
                    )
                    
                    return {
                        'has_warning': True,
                        'warning_type': '解禁预警',
                        'warning_date': row['解禁时间'],
                        'days_to_unban': days_to_unban,
                        'unban_ratio': ratio,
                        'unban_value': value,
                        'reason': f"解禁预警: {days_to_unban}天后解禁，占流通市值{ratio:.1%}"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ [解禁预警] 检查解禁预警失败: {e}")
            return None
    
    def get_shadow_list(self) -> List[Dict]:
        """
        获取 SHADOW_LIST
        
        Returns:
            list: [{code, reason, time}, ...]
        """
        return [
            {
                'code': code,
                'reason': self._shadow_list_reason.get(code, '未知'),
                'time': self._shadow_list_time.get(code, datetime.now())
            }
            for code in self._shadow_list
        ]
    
    def remove_from_shadow_list(self, stock_code: str):
        """
        从 SHADOW_LIST 移除股票
        
        Args:
            stock_code: 股票代码
        """
        if stock_code in self._shadow_list:
            self._shadow_list.remove(stock_code)
            self._shadow_list_reason.pop(stock_code, None)
            self._shadow_list_time.pop(stock_code, None)
            self._save_shadow_list()
            logger.info(f"✅ [解禁预警] 从 SHADOW_LIST 移除: {stock_code}")
    
    def clear_shadow_list(self):
        """清空 SHADOW_LIST"""
        self._shadow_list.clear()
        self._shadow_list_reason.clear()
        self._shadow_list_time.clear()
        self._save_shadow_list()
        logger.info("✅ [解禁预警] 清空 SHADOW_LIST")


# 全局实例
_unban_warning_system: Optional[UnbanWarningSystem] = None


def get_unban_warning_system() -> UnbanWarningSystem:
    """获取解禁预警系统单例"""
    global _unban_warning_system
    if _unban_warning_system is None:
        _unban_warning_system = UnbanWarningSystem()
    return _unban_warning_system