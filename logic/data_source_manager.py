#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据源管理器 - V19.8

功能：
- 管理多个数据源（AkShare, eFinance等）
- 实现降级策略（Failover）
- 自动切换到备用数据源
- 统一的数据接口

Author: iFlow CLI
Version: V19.8
"""

import pandas as pd
from typing import Optional, Dict, Any
from logic.logger import get_logger
from logic.api_robust import robust_api_call, rate_limit_decorator

logger = get_logger(__name__)


class DataSourceManager:
    """
    数据源管理器
    
    功能：
    1. 管理多个数据源
    2. 实现降级策略（Failover）
    3. 自动切换到备用数据源
    4. 统一的数据接口
    """
    
    def __init__(self):
        """初始化数据源管理器"""
        self.primary_source = "akshare"
        self.fallback_source = "efinance"
        self.current_source = self.primary_source
        
        # 初始化数据源
        self._init_akshare()
        self._init_efinance()
        
        logger.info(f"✅ [数据源管理器] 初始化完成，主源: {self.primary_source}, 备用源: {self.fallback_source}")
    
    def _init_akshare(self):
        """初始化AkShare数据源"""
        try:
            import akshare as ak
            self.akshare = ak
            logger.info("✅ [数据源管理器] AkShare 初始化成功")
        except ImportError:
            logger.warning("⚠️ [数据源管理器] AkShare 未安装，请运行: pip install akshare")
            self.akshare = None
    
    def _init_efinance(self):
        """初始化eFinance数据源"""
        try:
            import efinance as ef
            self.efinance = ef
            logger.info("✅ [数据源管理器] eFinance 初始化成功")
        except ImportError:
            logger.warning("⚠️ [数据源管理器] eFinance 未安装，请运行: pip install efinance")
            self.efinance = None
    
    @robust_api_call(max_retries=3, delay=2, return_empty_df=True)
    def get_stock_realtime_data(self, code: Optional[str] = None) -> pd.DataFrame:
        """
        获取股票实时数据（支持降级策略）
        
        Args:
            code: 股票代码（可选，不传则获取全市场数据）
        
        Returns:
            DataFrame: 股票实时数据
        """
        # 尝试主数据源
        if self.akshare is not None:
            try:
                if code:
                    df = self.akshare.stock_zh_a_spot_em()
                    df = df[df['代码'] == code]
                else:
                    df = self.akshare.stock_zh_a_spot_em()
                
                if not df.empty:
                    logger.debug(f"✅ [AkShare] 获取实时数据成功")
                    return df
            except Exception as e:
                logger.warning(f"⚠️ [AkShare] 获取实时数据失败: {e}")
        
        # 切换到备用数据源
        if self.efinance is not None:
            try:
                logger.info(f"🔄 [降级策略] 切换到 eFinance 获取实时数据")
                if code:
                    df = self.efinance.stock.get_realtime_quotes([code])
                else:
                    df = self.efinance.stock.get_realtime_quotes()
                
                if not df.empty:
                    logger.info(f"✅ [eFinance] 获取实时数据成功")
                    return df
            except Exception as e:
                logger.error(f"❌ [eFinance] 获取实时数据失败: {e}")
        
        # 所有数据源都失败
        logger.error(f"💀 [数据源管理器] 所有数据源均失效")
        return pd.DataFrame()
    
    @robust_api_call(max_retries=3, delay=2, return_empty_df=True)
    def get_stock_history_data(self, code: str, period: str = "daily", 
                               adjust: str = "qfq") -> pd.DataFrame:
        """
        获取股票历史数据（支持降级策略）
        
        Args:
            code: 股票代码
            period: 周期（daily, weekly, monthly）
            adjust: 复权方式（qfq: 前复权, hfq: 后复权, none: 不复权）
        
        Returns:
            DataFrame: 历史数据
        """
        # 尝试主数据源
        if self.akshare is not None:
            try:
                df = self.akshare.stock_zh_a_hist(
                    symbol=code,
                    period=period,
                    adjust=adjust
                )
                
                if not df.empty:
                    logger.debug(f"✅ [AkShare] 获取历史数据成功: {code}")
                    return df
            except Exception as e:
                logger.warning(f"⚠️ [AkShare] 获取历史数据失败: {code}, {e}")
        
        # 切换到备用数据源
        if self.efinance is not None:
            try:
                logger.info(f"🔄 [降级策略] 切换到 eFinance 获取历史数据: {code}")
                df = self.efinance.stock.get_quote_history(code)
                
                if not df.empty:
                    logger.info(f"✅ [eFinance] 获取历史数据成功: {code}")
                    return df
            except Exception as e:
                logger.error(f"❌ [eFinance] 获取历史数据失败: {code}, {e}")
        
        # 所有数据源都失败
        logger.error(f"💀 [数据源管理器] 所有数据源均失效: {code}")
        return pd.DataFrame()
    
    @robust_api_call(max_retries=3, delay=2, return_empty_df=True)
    def get_sector_data(self) -> pd.DataFrame:
        """
        获取板块数据（支持降级策略）
        
        Returns:
            DataFrame: 板块数据
        """
        # 尝试主数据源
        if self.akshare is not None:
            try:
                df = self.akshare.stock_board_industry_name_em()
                
                if not df.empty:
                    logger.debug(f"✅ [AkShare] 获取板块数据成功")
                    return df
            except Exception as e:
                logger.warning(f"⚠️ [AkShare] 获取板块数据失败: {e}")
        
        # 切换到备用数据源
        if self.efinance is not None:
            try:
                logger.info(f"🔄 [降级策略] 切换到 eFinance 获取板块数据")
                df = self.efinance.stock.get_industry_list()
                
                if not df.empty:
                    logger.info(f"✅ [eFinance] 获取板块数据成功")
                    return df
            except Exception as e:
                logger.error(f"❌ [eFinance] 获取板块数据失败: {e}")
        
        # 所有数据源都失败
        logger.error(f"💀 [数据源管理器] 所有数据源均失效")
        return pd.DataFrame()
    
    @rate_limit_decorator(calls_per_second=3)
    def get_stock_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票信息（带速率限制）
        
        Args:
            code: 股票代码
        
        Returns:
            Dict: 股票信息
        """
        # 尝试主数据源
        if self.akshare is not None:
            try:
                df = self.akshare.stock_zh_a_spot_em()
                df = df[df['代码'] == code]
                
                if not df.empty:
                    return df.iloc[0].to_dict()
            except Exception as e:
                logger.warning(f"⚠️ [AkShare] 获取股票信息失败: {code}, {e}")
        
        # 切换到备用数据源
        if self.efinance is not None:
            try:
                logger.info(f"🔄 [降级策略] 切换到 eFinance 获取股票信息: {code}")
                df = self.efinance.stock.get_realtime_quotes([code])
                
                if not df.empty:
                    return df.iloc[0].to_dict()
            except Exception as e:
                logger.error(f"❌ [eFinance] 获取股票信息失败: {code}, {e}")
        
        # 所有数据源都失败
        logger.error(f"💀 [数据源管理器] 所有数据源均失效: {code}")
        return None


# 全局单例
_data_source_manager = None


def get_data_source_manager() -> DataSourceManager:
    """
    获取数据源管理器单例
    
    Returns:
        DataSourceManager: 数据源管理器实例
    """
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = DataSourceManager()
    return _data_source_manager