#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能数据源管理器 - V19.9 混合动力架构

功能：
- 三级火箭架构：极速层/基础层/增强层
- 自动选择最优数据源
- 接口分层，降低单点故障风险

Author: iFlow CLI
Version: V19.9
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from logic.logger import get_logger
from logic.api_robust import robust_api_call, rate_limit_decorator
from logic.proxy_manager import get_proxy_manager, record_failure, record_success

logger = get_logger(__name__)


class SmartDataManager:
    """
    智能数据源管理器 - 三级火箭架构
    
    架构设计：
    1. 极速层（用于盯盘/半路战法）-> 使用 easyquotation
       - 特点：速度快（毫秒级），不封IP，数据包小
       - 用途：实时监控现价、监控瞬间成交量、半路战法
    
    2. 基础层（用于复盘/低吸战法）-> 使用 efinance
       - 特点：极其稳定，提供标准的OHLC历史数据
       - 用途：获取过去N天的均线、计算RSI/KDJ指标、低吸战法
    
    3. 增强层（用于DDE/龙头战法）-> 使用 akshare（带缓存）
       - 特点：数据最全，能爬到"东方财富"算好的DDE和板块资金流
       - 用途：个股资金流排名、板块资金分析
    """
    
    def __init__(self):
        """初始化智能数据源管理器"""
        self._init_fast_layer()      # 极速层
        self._init_basic_layer()     # 基础层
        self._init_enhanced_layer()  # 增强层
        
        logger.info("✅ [智能数据源管理器] 三级火箭架构初始化完成")
        logger.info("   - 极速层: easyquotation（半路战法）")
        logger.info("   - 基础层: efinance（低吸战法）")
        logger.info("   - 增强层: akshare（龙头战法，带缓存）")
    
    def _init_fast_layer(self):
        """初始化极速层（easyquotation）"""
        try:
            import easyquotation as eq
            self.easy_q = eq.use('sina')  # 使用新浪行情源
            
            # 🆕 V19.12: 给easyquotation穿上"浏览器马甲"（伪装头）
            # 模拟Chrome浏览器的请求头，避免被反爬防火墙识别
            browser_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
                "Referer": "http://quote.eastmoney.com/"
            }
            
            # 给easyquotation内部的session穿上马甲
            if hasattr(self.easy_q, 'session'):
                self.easy_q.session.headers.update(browser_headers)
                logger.info("✅ [极速层] easyquotation 初始化成功（已穿上浏览器马甲）")
            else:
                logger.info("✅ [极速层] easyquotation 初始化成功")
                
        except ImportError:
            logger.warning("⚠️ [极速层] easyquotation 未安装，请运行: pip install easyquotation")
            self.easy_q = None
    
    def _init_basic_layer(self):
        """初始化基础层（efinance）"""
        try:
            import efinance as ef
            self.efinance = ef
            logger.info("✅ [基础层] efinance 初始化成功")
        except ImportError:
            logger.warning("⚠️ [基础层] efinance 未安装，请运行: pip install efinance")
            self.efinance = None
    
    def _init_enhanced_layer(self):
        """初始化增强层（akshare）"""
        try:
            # 🆕 V19.10: 使用代理管理器设置直连模式，绕过Clash
            # 这可以避免因为使用共享VPN节点而被封IP的问题
            proxy_mgr = get_proxy_manager()
            proxy_mgr.set_direct_mode()
            
            import akshare as ak
            self.akshare = ak
            logger.info("✅ [增强层] akshare 初始化成功（直连模式）")
        except ImportError:
            logger.warning("⚠️ [增强层] akshare 未安装，请运行: pip install akshare")
            self.akshare = None
    
    # ==================== 极速层接口（半路战法） ====================
    
    @rate_limit_decorator(calls_per_second=10)
    def get_realtime_price_fast(self, stock_list: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        极速层：获取实时价格（半路战法专用）
        
        特点：
        - 只返回价格和瞬时量，速度最快
        - 使用easyquotation，毫秒级响应
        - 不封IP，适合高频调用
        
        Args:
            stock_list: 股票代码列表
        
        Returns:
            Dict: 股票实时数据字典
        """
        if self.easy_q is None:
            logger.error("❌ [极速层] easyquotation 未初始化")
            return {}
        
        try:
            # easyquotation 返回格式：{'sh600000': {'name': '浦发银行', 'now': 10.5, ...}}
            data = self.easy_q.stocks(stock_list)
            
            # 转换为统一格式
            result = {}
            for code, info in data.items():
                result[code] = {
                    'code': code,
                    'name': info.get('name', ''),
                    'price': info.get('now', 0),
                    'now': info.get('now', 0),  # 兼容easyquotation原始格式
                    'open': info.get('open', 0),
                    'close': info.get('close', 0),  # 昨日收盘价
                    'high': info.get('high', 0),
                    'low': info.get('low', 0),
                    'volume': info.get('volume', 0),
                    'turnover': info.get('turnover', 0),
                    'time': info.get('time', '')
                }
            
            logger.debug(f"✅ [极速层] 获取实时数据成功: {len(result)} 只股票")
            return result
            
        except Exception as e:
            logger.error(f"❌ [极速层] 获取实时数据失败: {e}")
            return {}
    
    # ==================== 基础层接口（低吸战法） ====================
    
    @robust_api_call(max_retries=3, delay=2, return_empty_df=True)
    def get_history_kline(self, stock_code: str, period: str = "daily") -> pd.DataFrame:
        """
        基础层：获取历史K线数据（低吸战法专用）
        
        策略：
        - 优先用 efinance（更稳，不封IP）
        - 失败了再用 akshare（备用）
        
        Args:
            stock_code: 股票代码
            period: 周期（daily, weekly, monthly）
        
        Returns:
            DataFrame: 历史K线数据
        """
        # 优先使用 efinance
        if self.efinance is not None:
            try:
                df = self.efinance.stock.get_quote_history(stock_code)
                
                if not df.empty:
                    logger.debug(f"✅ [基础层-efinance] 获取K线数据成功: {stock_code}")
                    return df
            except Exception as e:
                logger.warning(f"⚠️ [基础层-efinance] 获取K线数据失败: {stock_code}, {e}")
        
        # 切换到 akshare（备用）
        if self.akshare is not None:
            try:
                logger.info(f"🔄 [基础层] 切换到 akshare 获取K线数据: {stock_code}")

                # 🆕 V19.10: 添加sleep规避IP封禁
                import time
                time.sleep(0.5)

                # 🆕 V19.13: 临时清空环境变量，防止 akshare 读到残留的代理配置
                env_backup = os.environ.copy()
                os.environ.pop('HTTP_PROXY', None)
                os.environ.pop('HTTPS_PROXY', None)
                os.environ.pop('http_proxy', None)
                os.environ.pop('https_proxy', None)
                os.environ['NO_PROXY'] = '*'

                # 🆕 V19.13: 禁用requests的代理
                try:
                    import requests
                    requests.Session().proxies = {}
                    requests.Session().trust_env = False
                except ImportError:
                    pass

                # 🔧 修复：分钟线使用专门的接口
                if period == '1min':
                    df = self.akshare.stock_zh_a_hist_min_em(
                        symbol=stock_code,
                        period='1',  # 1分钟
                        adjust='qfq',
                        start_date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                        end_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                else:
                    # 日线等其他周期使用 stock_zh_a_hist
                    df = self.akshare.stock_zh_a_hist(
                        symbol=stock_code,
                        period=period,
                        adjust="qfq"
                    )

                # 恢复环境变量（如果需要的话，但在你的场景下不恢复也没事）
                # os.environ.update(env_backup)

                if not df.empty:
                    logger.info(f"✅ [基础层-akshare] 获取K线数据成功: {stock_code}")
                    record_success()
                    return df
                else:
                    logger.warning(f"⚠️ [基础层-akshare] 获取K线数据返回空: {stock_code}")
                    record_failure()
            except Exception as e:
                logger.error(f"❌ [基础层-akshare] 获取K线数据失败: {stock_code}, {e}")
                record_failure()
        
        # 所有数据源都失败
        logger.error(f"💀 [基础层] 所有数据源均失效: {stock_code}")
        return pd.DataFrame()
    
    @robust_api_call(max_retries=3, delay=2, return_empty_df=True)
    def get_realtime_quotes(self, stock_list: List[str]) -> pd.DataFrame:
        """
        基础层：获取实时行情（低吸战法专用）
        
        使用 efinance，获取更详细的实时数据
        
        Args:
            stock_list: 股票代码列表
        
        Returns:
            DataFrame: 实时行情数据
        """
        if self.efinance is not None:
            try:
                df = self.efinance.stock.get_realtime_quotes(stock_list)
                
                if not df.empty:
                    logger.debug(f"✅ [基础层-efinance] 获取实时行情成功: {len(df)} 只股票")
                    return df
            except Exception as e:
                logger.warning(f"⚠️ [基础层-efinance] 获取实时行情失败: {e}")
        
        # 切换到 akshare（备用）
        if self.akshare is not None:
            try:
                logger.info(f"🔄 [基础层] 切换到 akshare 获取实时行情")
                
                # 🆕 V19.10: 添加sleep规避IP封禁
                import time
                time.sleep(0.5)
                
                df = self.akshare.stock_zh_a_spot_em()
                
                if not df.empty:
                    # 过滤出目标股票
                    df = df[df['代码'].isin(stock_list)]
                    logger.info(f"✅ [基础层-akshare] 获取实时行情成功: {len(df)} 只股票")
                    record_success()
                    return df
                else:
                    logger.warning("⚠️ [基础层-akshare] 获取实时行情返回空数据")
                    record_failure()
            except Exception as e:
                logger.error(f"❌ [基础层-akshare] 获取实时行情失败: {e}")
                record_failure()
        
        return pd.DataFrame()
    
    # ==================== 增强层接口（龙头战法） ====================
    
    @robust_api_call(max_retries=3, delay=2, return_empty_df=True)
    def get_money_flow(self, stock_code: str, market: str = "sh") -> Optional[Dict[str, Any]]:
        """
        增强层：获取个股资金流（龙头战法专用）
        
        策略：
        - 只能用 AkShare（因为它能爬到东方财富算好的DDE）
        - 必须接受延迟（通过requests_cache缓存3分钟）
        
        Args:
            stock_code: 股票代码
            market: 市场（sh/sz）
        
        Returns:
            Dict: 资金流数据
        """
        if self.akshare is None:
            logger.error("❌ [增强层] akshare 未初始化")
            record_failure()
            return None
        
        try:
            # 🆕 V19.10: 添加sleep规避IP封禁
            import time
            time.sleep(0.5)
            
            # AkShare 资金流接口
            df = self.akshare.stock_individual_fund_flow(
                stock=stock_code,
                market=market
            )
            
            if not df.empty:
                logger.debug(f"✅ [增强层] 获取资金流成功: {stock_code}")
                record_success()
                return df.iloc[0].to_dict()
            
            logger.warning(f"⚠️ [增强层] 获取资金流返回空数据: {stock_code}")
            record_failure()
            return None
            
        except Exception as e:
            logger.error(f"❌ [增强层] 获取资金流失败: {stock_code}, {e}")
            record_failure()
            return None
    
    @robust_api_call(max_retries=3, delay=2, return_empty_df=True)
    def get_sector_fund_flow(self) -> pd.DataFrame:
        """
        增强层：获取板块资金流（龙头战法专用）
        
        Args:
            None
        
        Returns:
            DataFrame: 板块资金流数据
        """
        if self.akshare is None:
            logger.error("❌ [增强层] akshare 未初始化")
            record_failure()
            return pd.DataFrame()
        
        try:
            # 🆕 V19.10: 添加sleep规避IP封禁
            import time
            time.sleep(0.5)
            
            df = self.akshare.stock_sector_fund_flow()
            
            if not df.empty:
                logger.debug(f"✅ [增强层] 获取板块资金流成功: {len(df)} 个板块")
                record_success()
                return df
            
            logger.warning("⚠️ [增强层] 获取板块资金流返回空数据")
            record_failure()
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"❌ [增强层] 获取板块资金流失败: {e}")
            record_failure()
            return pd.DataFrame()
    
    # ==================== 通用接口（兼容旧代码） ====================
    
    @robust_api_call(max_retries=3, delay=2, return_empty_df=True)
    def get_stock_realtime_data(self, code: Optional[str] = None) -> pd.DataFrame:
        """
        获取股票实时数据（兼容旧代码）
        
        策略：
        - 优先使用极速层（easyquotation）
        - 失败后使用基础层（efinance）
        - 最后使用增强层（akshare）
        
        Args:
            code: 股票代码（可选，不传则获取全市场数据）
        
        Returns:
            DataFrame: 股票实时数据
        """
        # 1. 尝试极速层（最快）
        if code and self.easy_q is not None:
            try:
                data = self.easy_q.stocks([code])
                if data and code in data:
                    info = data[code]
                    df = pd.DataFrame([{
                        '代码': code,
                        '名称': info.get('name', ''),
                        '现价': info.get('now', 0),
                        '开盘价': info.get('open', 0),
                        '最高价': info.get('high', 0),
                        '最低价': info.get('low', 0),
                        '成交量': info.get('volume', 0),
                        '成交额': info.get('turnover', 0),
                        '时间': info.get('time', '')
                    }])
                    return df
            except Exception as e:
                logger.debug(f"⚠️ [极速层] 获取实时数据失败: {e}")
        
        # 2. 尝试基础层
        if self.efinance is not None:
            try:
                if code:
                    df = self.efinance.stock.get_realtime_quotes([code])
                else:
                    df = self.efinance.stock.get_realtime_quotes()
                
                if not df.empty:
                    logger.debug(f"✅ [基础层] 获取实时数据成功")
                    return df
            except Exception as e:
                logger.warning(f"⚠️ [基础层] 获取实时数据失败: {e}")
        
        # 3. 尝试增强层
        if self.akshare is not None:
            try:
                # 🆕 V19.10: 添加sleep规避IP封禁
                import time
                time.sleep(0.5)
                
                df = self.akshare.stock_zh_a_spot_em()
                
                if not df.empty:
                    if code:
                        df = df[df['代码'] == code]
                    
                    logger.debug(f"✅ [增强层] 获取实时数据成功")
                    record_success()
                    return df
                else:
                    logger.warning("⚠️ [增强层] 获取实时数据返回空数据")
                    record_failure()
            except Exception as e:
                logger.error(f"❌ [增强层] 获取实时数据失败: {e}")
                record_failure()
        
        return pd.DataFrame()


# 全局单例
_smart_data_manager = None


def get_smart_data_manager() -> SmartDataManager:
    """
    获取智能数据源管理器单例
    
    Returns:
        SmartDataManager: 智能数据源管理器实例
    """
    global _smart_data_manager
    if _smart_data_manager is None:
        _smart_data_manager = SmartDataManager()
    return _smart_data_manager


def get_data_source_manager() -> SmartDataManager:
    """
    获取数据源管理器单例（向后兼容别名）
    
    Returns:
        SmartDataManager: 智能数据源管理器实例
    """
    return get_smart_data_manager()


# 为了兼容性，保留旧的 DataSourceManager 类名
DataSourceManager = SmartDataManager