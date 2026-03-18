# -*- coding: utf-8 -*-
"""
Tick适配器 - Live/Mock模式统一数据入口

【CTO V213 大一统引擎核心组件】
- LiveTickAdapter: 实盘QMT数据 → StandardTick
- MockTickAdapter: 本地历史数据 → StandardTick

设计原则：
1. 数据防腐：所有数据源必须经过Adapter清洗
2. 依赖注入：主引擎通过Adapter获取数据，不直接调用xtdata
3. 量纲统一：输出永远是StandardTick，量纲100%确定

Author: CTO架构组
Date: 2026-03-18
Version: 1.0.0
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from logic.data_providers.standard_tick import StandardTick, TickAdapterBase

logger = logging.getLogger(__name__)


class LiveTickAdapter(TickAdapterBase):
    """
    实盘Tick适配器 - 从QMT获取实时数据
    
    用途：
    - mode='live'时注入主引擎
    - 直接调用xtdata.get_full_tick
    - 输出StandardTick
    """
    
    def __init__(self):
        """初始化实盘适配器"""
        self._xtdata = None
        self._is_initialized = False
        self._subscribed_codes = set()
    
    def initialize(self) -> bool:
        """
        初始化QMT连接
        
        Returns:
            bool: 是否成功
        """
        try:
            from xtquant import xtdata
            xtdata.enable_hello = False
            self._xtdata = xtdata
            self._is_initialized = True
            logger.info("[OK] [LiveTickAdapter] QMT连接成功")
            return True
        except ImportError:
            logger.error("[X] [LiveTickAdapter] 无法导入xtquant")
            return False
        except Exception as e:
            logger.error(f"[X] [LiveTickAdapter] 初始化失败: {e}")
            return False
    
    def subscribe(self, stock_codes: List[str]) -> bool:
        """
        订阅股票Tick
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            bool: 是否成功
        """
        if not self._is_initialized:
            if not self.initialize():
                return False
        
        try:
            # 订阅全推行情
            self._xtdata.subscribe_whole_quote(stock_codes)
            self._subscribed_codes.update(stock_codes)
            logger.info(f"[OK] [LiveTickAdapter] 订阅成功: {len(stock_codes)}只")
            return True
        except Exception as e:
            logger.error(f"[X] [LiveTickAdapter] 订阅失败: {e}")
            return False
    
    def get_ticks(self, stock_codes: List[str]) -> Dict[str, StandardTick]:
        """
        获取多只股票的实时Tick
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            {stock_code: StandardTick}
        """
        if not self._is_initialized:
            if not self.initialize():
                return {}
        
        result = {}
        try:
            raw_ticks = self._xtdata.get_full_tick(stock_codes)
            if raw_ticks:
                for code, tick in raw_ticks.items():
                    if tick:
                        result[code] = StandardTick.from_qmt_tick(code, tick)
        except Exception as e:
            logger.error(f"[X] [LiveTickAdapter] get_ticks失败: {e}")
        
        return result
    
    def get_full_tick_snapshot(self, stock_codes: List[str]) -> Dict[str, StandardTick]:
        """
        获取全市场快照（与get_ticks相同，兼容接口）
        """
        return self.get_ticks(stock_codes)
    
    def get_stock_list(self, sector: str = '沪深A股') -> List[str]:
        """
        获取股票列表
        
        Args:
            sector: 板块名称
            
        Returns:
            股票代码列表
        """
        if not self._is_initialized:
            if not self.initialize():
                return []
        
        try:
            return self._xtdata.get_stock_list_in_sector(sector)
        except Exception as e:
            logger.error(f"[X] [LiveTickAdapter] get_stock_list失败: {e}")
            return []


class MockTickAdapter(TickAdapterBase):
    """
    Mock Tick适配器 - 从本地历史数据读取
    
    用途：
    - mode='mock'时注入主引擎
    - 从本地Tick文件或QMT历史数据读取
    - 输出StandardTick
    """
    
    def __init__(self, target_date: str = None):
        """
        初始化Mock适配器
        
        Args:
            target_date: 目标日期 (格式: 'YYYYMMDD')
        """
        self.target_date = target_date or datetime.now().strftime('%Y%m%d')
        self._xtdata = None
        self._is_initialized = False
        self._tick_cache = {}  # {stock_code: DataFrame}
        self._time_axis = []  # 时间轴
        self._current_index = 0  # 当前时间索引
    
    def initialize(self) -> bool:
        """
        初始化Mock环境
        
        Returns:
            bool: 是否成功
        """
        try:
            from xtquant import xtdata
            xtdata.enable_hello = False
            self._xtdata = xtdata
            self._is_initialized = True
            logger.info(f"[OK] [MockTickAdapter] 初始化成功，目标日期: {self.target_date}")
            return True
        except ImportError:
            logger.error("[X] [MockTickAdapter] 无法导入xtquant")
            return False
        except Exception as e:
            logger.error(f"[X] [MockTickAdapter] 初始化失败: {e}")
            return False
    
    def load_tick_data(self, stock_codes: List[str]) -> int:
        """
        预加载历史Tick数据
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            int: 成功加载数量
        """
        if not self._is_initialized:
            if not self.initialize():
                return 0
        
        loaded = 0
        for code in stock_codes:
            try:
                # 从QMT本地读取历史Tick
                df = self._xtdata.get_local_data(
                    stock_code=code,
                    period='tick',
                    start_time=f'{self.target_date}093000',
                    end_time=f'{self.target_date}150000'
                )
                if df is not None and len(df) > 0:
                    self._tick_cache[code] = df
                    loaded += 1
            except Exception as e:
                logger.debug(f"[MockTickAdapter] {code} 无Tick数据: {e}")
        
        # 构建时间轴
        if self._tick_cache:
            first_code = list(self._tick_cache.keys())[0]
            self._time_axis = self._tick_cache[first_code].index.tolist()
            self._current_index = 0
        
        logger.info(f"[OK] [MockTickAdapter] 加载Tick数据: {loaded}/{len(stock_codes)}")
        return loaded
    
    def get_ticks(self, stock_codes: List[str]) -> Dict[str, StandardTick]:
        """
        获取当前时间点的Tick数据
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            {stock_code: StandardTick}
        """
        result = {}
        
        if not self._time_axis or self._current_index >= len(self._time_axis):
            return result
        
        for code in stock_codes:
            if code in self._tick_cache:
                try:
                    df = self._tick_cache[code]
                    if self._current_index < len(df):
                        row = df.iloc[self._current_index]
                        tick_dict = row.to_dict() if hasattr(row, 'to_dict') else dict(row)
                        time_str = str(self._time_axis[self._current_index])
                        result[code] = StandardTick.from_local_tick(code, tick_dict, time_str)
                except Exception as e:
                    logger.debug(f"[MockTickAdapter] {code} 提取失败: {e}")
        
        return result
    
    def get_full_tick_snapshot(self, stock_codes: List[str]) -> Dict[str, StandardTick]:
        """
        获取全市场快照（与get_ticks相同）
        """
        return self.get_ticks(stock_codes)
    
    def advance_frame(self) -> bool:
        """
        推进时间帧
        
        Returns:
            bool: 是否还有下一帧
        """
        if self._current_index < len(self._time_axis) - 1:
            self._current_index += 1
            return True
        return False
    
    def get_current_time(self) -> Optional[str]:
        """
        获取当前时间戳
        
        Returns:
            str: 当前时间字符串
        """
        if self._time_axis and self._current_index < len(self._time_axis):
            return str(self._time_axis[self._current_index])
        return None
    
    def get_progress(self) -> float:
        """
        获取播放进度
        
        Returns:
            float: 0.0-1.0
        """
        if not self._time_axis:
            return 0.0
        return self._current_index / len(self._time_axis)
    
    def get_stock_list(self, sector: str = '沪深A股') -> List[str]:
        """
        获取股票列表
        
        Args:
            sector: 板块名称
            
        Returns:
            股票代码列表
        """
        if not self._is_initialized:
            if not self.initialize():
                return []
        
        try:
            return self._xtdata.get_stock_list_in_sector(sector)
        except Exception as e:
            logger.error(f"[X] [MockTickAdapter] get_stock_list失败: {e}")
            return []


def create_tick_adapter(mode: str, target_date: str = None) -> TickAdapterBase:
    """
    工厂函数 - 创建Tick适配器
    
    Args:
        mode: 'live' 或 'scan'/'mock'
        target_date: 目标日期（scan/mock模式必需）
        
    Returns:
        TickAdapterBase实例
    """
    if mode == 'live':
        return LiveTickAdapter()
    elif mode in ('scan', 'mock'):  # 【V215】scan等同于mock
        return MockTickAdapter(target_date)
    else:
        raise ValueError(f"未知的mode: {mode}，必须是 'live' 或 'scan'/'mock'")
