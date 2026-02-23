#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tushare Pro 数据提供者 (Phase 6.1.1)
=====================================
统一封装Tushare Pro API，提供基础数据获取功能。

功能：
- 全市场股票基础信息（stock_basic）
- 每日行情数据（daily）
- 流通股本、昨收价等关键字段
- 与QMT数据格式对齐

注意：
- 需要配置Tushare Pro Token（老板有8000积分）
- 所有数据返回统一格式的DataFrame
- 支持本地缓存，减少API调用

Author: AI开发专家
Date: 2026-02-23
Version: 1.0.0
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Union
import pandas as pd

# Windows编码卫士
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 导入logger
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


class TushareProvider:
    """
    Tushare Pro 数据提供者
    ======================
    封装Tushare基础数据获取，与QMT数据格式对齐
    """
    
    _instance = None
    _pro = None
    _token = None
    
    # 缓存配置
    CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "tushare"
    CACHE_TTL = {
        'stock_basic': 7 * 24 * 3600,  # 7天
        'daily': 24 * 3600,             # 1天
        'daily_basic': 24 * 3600,       # 1天
        'trade_cal': 30 * 24 * 3600,    # 30天
    }
    
    def __new__(cls, token: str = None):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, token: str = None):
        if self._initialized:
            return
            
        self._initialized = True
        self._cache_enabled = True
        
        # 确保缓存目录存在
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 初始化Tushare
        self._init_tushare(token)
    
    def _init_tushare(self, token: str = None):
        """初始化Tushare Pro API"""
        try:
            import tushare as ts
            
            # 优先使用传入的token
            if token:
                self._token = token
            else:
                # 尝试从配置文件读取
                self._token = self._load_token_from_config()
            
            if not self._token:
                logger.warning("[TushareProvider] ⚠️ 未配置Tushare Token，请在config/tushare_token.txt中配置")
                return
            
            # 设置token并初始化pro接口
            ts.set_token(self._token)
            self._pro = ts.pro_api()
            
            logger.info(f"[TushareProvider] ✅ Tushare Pro初始化成功")
            
            # 测试连接
            self._test_connection()
            
        except ImportError:
            logger.error("[TushareProvider] ❌ tushare库未安装，请执行: pip install tushare")
            self._pro = None
        except Exception as e:
            logger.error(f"[TushareProvider] ❌ Tushare初始化失败: {e}")
            self._pro = None
    
    def _load_token_from_config(self) -> Optional[str]:
        """从配置文件加载Token"""
        # 尝试多个路径
        possible_paths = [
            Path(__file__).resolve().parents[2] / "config" / "tushare_token.txt",
            Path(__file__).resolve().parents[2] / "config" / "tushare_token",
            Path("config/tushare_token.txt"),
            Path("config/tushare_token"),
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    token = path.read_text(encoding='utf-8').strip()
                    logger.info(f"[TushareProvider] 从 {path} 加载Token")
                    return token
                except Exception as e:
                    logger.warning(f"[TushareProvider] 读取Token文件失败 {path}: {e}")
        
        # 尝试从环境变量读取
        token = os.environ.get('TUSHARE_TOKEN')
        if token:
            logger.info("[TushareProvider] 从环境变量加载Token")
            return token
        
        return None
    
    def _test_connection(self):
        """测试Tushare连接"""
        try:
            # 尝试获取交易日期测试连接
            df = self._pro.trade_cal(exchange='SSE', limit=1)
            if df is not None and not df.empty:
                logger.info("[TushareProvider] ✅ Tushare连接测试成功")
            else:
                logger.warning("[TushareProvider] ⚠️ Tushare连接测试返回空数据")
        except Exception as e:
            logger.error(f"[TushareProvider] ❌ Tushare连接测试失败: {e}")
    
    # ==================== 缓存相关方法 ====================
    
    def _get_cache_path(self, data_type: str, key: str) -> Path:
        """获取缓存文件路径"""
        cache_file = f"{data_type}_{key}.json"
        return self.CACHE_DIR / cache_file
    
    def _load_from_cache(self, data_type: str, key: str) -> Optional[pd.DataFrame]:
        """从缓存加载数据"""
        if not self._cache_enabled:
            return None
        
        cache_path = self._get_cache_path(data_type, key)
        if not cache_path.exists():
            return None
        
        try:
            # 检查缓存是否过期
            mtime = cache_path.stat().st_mtime
            ttl = self.CACHE_TTL.get(data_type, 3600)
            
            if time.time() - mtime > ttl:
                logger.debug(f"[TushareProvider] 缓存过期: {data_type}/{key}")
                return None
            
            # 读取缓存
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            df = pd.DataFrame(data)
            logger.debug(f"[TushareProvider] 从缓存加载: {data_type}/{key}, 共{len(df)}条")
            return df
            
        except Exception as e:
            logger.warning(f"[TushareProvider] 读取缓存失败: {e}")
            return None
    
    def _save_to_cache(self, data_type: str, key: str, df: pd.DataFrame):
        """保存数据到缓存"""
        if not self._cache_enabled or df is None or df.empty:
            return
        
        try:
            cache_path = self._get_cache_path(data_type, key)
            
            # 转换DataFrame为JSON可序列化格式
            data = df.to_dict(orient='records')
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"[TushareProvider] 保存到缓存: {data_type}/{key}, 共{len(df)}条")
            
        except Exception as e:
            logger.warning(f"[TushareProvider] 保存缓存失败: {e}")
    
    def clear_cache(self, data_type: str = None):
        """清除缓存"""
        try:
            if data_type:
                # 清除指定类型的缓存
                for cache_file in self.CACHE_DIR.glob(f"{data_type}_*.json"):
                    cache_file.unlink()
                logger.info(f"[TushareProvider] 清除缓存: {data_type}")
            else:
                # 清除所有缓存
                for cache_file in self.CACHE_DIR.glob("*.json"):
                    cache_file.unlink()
                logger.info("[TushareProvider] 清除所有缓存")
        except Exception as e:
            logger.error(f"[TushareProvider] 清除缓存失败: {e}")
    
    # ==================== 核心数据接口 ====================
    
    def get_stock_basic(self, exchange: str = '', list_status: str = 'L', 
                        fields: str = '') -> Optional[pd.DataFrame]:
        """
        获取股票基础信息
        
        Args:
            exchange: 交易所 SSE/SZSE/BSE，默认全部
            list_status: 上市状态 L上市/D退市/P暂停，默认L
            fields: 指定字段，默认全部
        
        Returns:
            DataFrame: 包含股票基础信息
                - ts_code: TS代码
                - symbol: 股票代码
                - name: 股票名称
                - area: 地域
                - industry: 所属行业
                - fullname: 股票全称
                - enname: 英文全称
                - cnspell: 拼音缩写
                - market: 市场类型
                - exchange: 交易所代码
                - curr_type: 交易货币
                - list_status: 上市状态
                - list_date: 上市日期
                - delist_date: 退市日期
                - is_hs: 是否沪深港通标的
        """
        if self._pro is None:
            logger.error("[TushareProvider] Tushare未初始化")
            return None
        
        # 构建缓存key
        cache_key = f"{exchange}_{list_status}"
        
        # 尝试从缓存加载
        df = self._load_from_cache('stock_basic', cache_key)
        if df is not None:
            return df
        
        try:
            logger.info("[TushareProvider] 从API获取股票基础信息...")
            
            df = self._pro.stock_basic(
                exchange=exchange,
                list_status=list_status,
                fields=fields
            )
            
            if df is None or df.empty:
                logger.warning("[TushareProvider] 股票基础信息返回空数据")
                return None
            
            # 保存到缓存
            self._save_to_cache('stock_basic', cache_key, df)
            
            logger.info(f"[TushareProvider] ✅ 获取股票基础信息成功，共{len(df)}只股票")
            return df
            
        except Exception as e:
            logger.error(f"[TushareProvider] 获取股票基础信息失败: {e}")
            return None
    
    def get_daily(self, ts_code: str = '', trade_date: str = '', 
                  start_date: str = '', end_date: str = '') -> Optional[pd.DataFrame]:
        """
        获取日线行情数据
        
        Args:
            ts_code: TS代码（如000001.SZ）
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        
        Returns:
            DataFrame: 日线行情数据
                - ts_code: TS代码
                - trade_date: 交易日期
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - pre_close: 昨收价
                - change: 涨跌额
                - pct_chg: 涨跌幅
                - vol: 成交量（手）
                - amount: 成交额（千元）
        """
        if self._pro is None:
            logger.error("[TushareProvider] Tushare未初始化")
            return None
        
        # 构建缓存key
        if trade_date:
            cache_key = f"{ts_code}_{trade_date}"
        else:
            cache_key = f"{ts_code}_{start_date}_{end_date}"
        
        # 尝试从缓存加载
        df = self._load_from_cache('daily', cache_key)
        if df is not None:
            return df
        
        try:
            logger.debug(f"[TushareProvider] 从API获取日线数据: {ts_code}")
            
            df = self._pro.daily(
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                logger.warning(f"[TushareProvider] 日线数据返回空: {ts_code}")
                return None
            
            # 保存到缓存
            self._save_to_cache('daily', cache_key, df)
            
            logger.debug(f"[TushareProvider] ✅ 获取日线数据成功: {ts_code}, 共{len(df)}条")
            return df
            
        except Exception as e:
            logger.error(f"[TushareProvider] 获取日线数据失败 {ts_code}: {e}")
            return None
    
    def get_daily_basic(self, ts_code: str = '', trade_date: str = '',
                        start_date: str = '', end_date: str = '') -> Optional[pd.DataFrame]:
        """
        获取每日指标（包含流通股本等）
        
        Args:
            ts_code: TS代码
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame: 每日指标数据
                - ts_code: TS代码
                - trade_date: 交易日期
                - close: 收盘价
                - turnover_rate: 换手率
                - turnover_rate_f: 换手率（自由流通股）
                - volume_ratio: 量比
                - pe: 市盈率
                - pe_ttm: 市盈率TTM
                - pb: 市净率
                - ps: 市销率
                - ps_ttm: 市销率TTM
                - dv_ratio: 股息率
                - dv_ttm: 股息率TTM
                - total_share: 总股本（万股）
                - float_share: 流通股本（万股）
                - free_share: 自由流通股本（万股）
                - total_mv: 总市值（万元）
                - circ_mv: 流通市值（万元）
        """
        if self._pro is None:
            logger.error("[TushareProvider] Tushare未初始化")
            return None
        
        # 构建缓存key
        if trade_date:
            cache_key = f"{ts_code}_{trade_date}"
        else:
            cache_key = f"{ts_code}_{start_date}_{end_date}"
        
        # 尝试从缓存加载
        df = self._load_from_cache('daily_basic', cache_key)
        if df is not None:
            return df
        
        try:
            logger.debug(f"[TushareProvider] 从API获取每日指标: {ts_code}")
            
            df = self._pro.daily_basic(
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                logger.warning(f"[TushareProvider] 每日指标返回空: {ts_code}")
                return None
            
            # 保存到缓存
            self._save_to_cache('daily_basic', cache_key, df)
            
            logger.debug(f"[TushareProvider] ✅ 获取每日指标成功: {ts_code}, 共{len(df)}条")
            return df
            
        except Exception as e:
            logger.error(f"[TushareProvider] 获取每日指标失败 {ts_code}: {e}")
            return None
    
    def get_trade_cal(self, exchange: str = 'SSE', start_date: str = '', 
                      end_date: str = '') -> Optional[pd.DataFrame]:
        """
        获取交易日历
        
        Args:
            exchange: 交易所 SSE/SZSE
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        
        Returns:
            DataFrame: 交易日历
                - exchange: 交易所
                - cal_date: 日历日期
                - is_open: 是否开市 0休市 1交易
                - pretrade_date: 上一个交易日
        """
        if self._pro is None:
            logger.error("[TushareProvider] Tushare未初始化")
            return None
        
        # 默认获取最近一年的交易日历
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        if not end_date:
            end_date = (datetime.now() + timedelta(days=30)).strftime('%Y%m%d')
        
        cache_key = f"{exchange}_{start_date}_{end_date}"
        
        # 尝试从缓存加载
        df = self._load_from_cache('trade_cal', cache_key)
        if df is not None:
            return df
        
        try:
            logger.info("[TushareProvider] 从API获取交易日历...")
            
            df = self._pro.trade_cal(
                exchange=exchange,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                logger.warning("[TushareProvider] 交易日历返回空")
                return None
            
            # 保存到缓存
            self._save_to_cache('trade_cal', cache_key, df)
            
            logger.info(f"[TushareProvider] ✅ 获取交易日历成功，共{len(df)}条")
            return df
            
        except Exception as e:
            logger.error(f"[TushareProvider] 获取交易日历失败: {e}")
            return None
    
    # ==================== 便捷方法 ====================
    
    def get_all_stocks(self) -> Optional[pd.DataFrame]:
        """
        获取所有上市股票列表
        
        Returns:
            DataFrame: 所有上市股票基础信息
        """
        return self.get_stock_basic(list_status='L')
    
    def get_stock_daily(self, code: str, start_date: str = '', end_date: str = '') -> Optional[pd.DataFrame]:
        """
        获取单只股票日线数据（支持多种代码格式）
        
        Args:
            code: 股票代码（支持000001.SZ或000001格式）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        
        Returns:
            DataFrame: 日线数据
        """
        # 统一转换为TS代码格式
        ts_code = self._to_ts_code(code)
        return self.get_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    
    def get_stock_daily_basic(self, code: str, trade_date: str = '') -> Optional[pd.DataFrame]:
        """
        获取单只股票每日指标
        
        Args:
            code: 股票代码
            trade_date: 交易日期，默认最新
        
        Returns:
            DataFrame: 每日指标
        """
        ts_code = self._to_ts_code(code)
        
        if not trade_date:
            # 获取最近一个交易日
            trade_date = self.get_latest_trade_date()
        
        return self.get_daily_basic(ts_code=ts_code, trade_date=trade_date)
    
    def get_latest_trade_date(self) -> str:
        """
        获取最近一个交易日
        
        Returns:
            str: 最近交易日（YYYYMMDD）
        """
        try:
            df = self.get_trade_cal()
            if df is not None and not df.empty:
                # 筛选交易日且日期<=今天
                today = datetime.now().strftime('%Y%m%d')
                df = df[df['is_open'] == 1]
                df = df[df['cal_date'] <= today]
                if not df.empty:
                    return df['cal_date'].iloc[-1]
        except Exception as e:
            logger.warning(f"[TushareProvider] 获取最近交易日失败: {e}")
        
        # 默认返回昨天
        return (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    
    def get_next_trade_date(self, date: str = '') -> str:
        """
        获取下一个交易日
        
        Args:
            date: 基准日期，默认今天
        
        Returns:
            str: 下一个交易日（YYYYMMDD）
        """
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        try:
            df = self.get_trade_cal()
            if df is not None and not df.empty:
                df = df[df['is_open'] == 1]
                df = df[df['cal_date'] > date]
                if not df.empty:
                    return df['cal_date'].iloc[0]
        except Exception as e:
            logger.warning(f"[TushareProvider] 获取下一个交易日失败: {e}")
        
        # 默认返回后天
        return (datetime.now() + timedelta(days=2)).strftime('%Y%m%d')
    
    # ==================== 工具方法 ====================
    
    def _to_ts_code(self, code: str) -> str:
        """
        转换为TS代码格式
        
        Args:
            code: 股票代码（如000001或000001.SZ）
        
        Returns:
            str: TS代码格式（000001.SZ）
        """
        if '.' in code:
            return code
        
        # 根据代码前缀判断交易所
        if code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith('0') or code.startswith('3'):
            return f"{code}.SZ"
        elif code.startswith('68'):
            return f"{code}.SH"
        elif code.startswith('8') or code.startswith('4'):
            return f"{code}.BJ"
        else:
            # 默认深交所
            return f"{code}.SZ"
    
    def _from_ts_code(self, ts_code: str) -> str:
        """
        从TS代码提取纯数字代码
        
        Args:
            ts_code: TS代码（000001.SZ）
        
        Returns:
            str: 纯数字代码（000001）
        """
        return ts_code.split('.')[0]
    
    def get_float_share(self, code: str, trade_date: str = '') -> Optional[float]:
        """
        获取流通股本（万股）
        
        Args:
            code: 股票代码
            trade_date: 交易日期
        
        Returns:
            float: 流通股本（万股）
        """
        df = self.get_stock_daily_basic(code, trade_date)
        if df is not None and not df.empty:
            return float(df['float_share'].iloc[0])
        return None
    
    def get_circ_mv(self, code: str, trade_date: str = '') -> Optional[float]:
        """
        获取流通市值（万元）
        
        Args:
            code: 股票代码
            trade_date: 交易日期
        
        Returns:
            float: 流通市值（万元）
        """
        df = self.get_stock_daily_basic(code, trade_date)
        if df is not None and not df.empty:
            return float(df['circ_mv'].iloc[0])
        return None
    
    def get_pre_close(self, code: str, trade_date: str = '') -> Optional[float]:
        """
        获取昨收价
        
        Args:
            code: 股票代码
            trade_date: 交易日期，默认最新
        
        Returns:
            float: 昨收价
        """
        if not trade_date:
            trade_date = self.get_latest_trade_date()
        
        # 获取当日日线数据
        df = self.get_stock_daily(code, trade_date, trade_date)
        if df is not None and not df.empty:
            return float(df['pre_close'].iloc[0])
        return None
    
    # ==================== 批量接口 ====================
    
    def get_daily_all(self, trade_date: str) -> Optional[pd.DataFrame]:
        """
        获取全市场日线数据（单日）
        
        Args:
            trade_date: 交易日期（YYYYMMDD）
        
        Returns:
            DataFrame: 全市场日线数据
        """
        if self._pro is None:
            logger.error("[TushareProvider] Tushare未初始化")
            return None
        
        cache_key = f"all_{trade_date}"
        
        # 尝试从缓存加载
        df = self._load_from_cache('daily', cache_key)
        if df is not None:
            return df
        
        try:
            logger.info(f"[TushareProvider] 从API获取全市场日线数据: {trade_date}")
            
            df = self._pro.daily(trade_date=trade_date)
            
            if df is None or df.empty:
                logger.warning(f"[TushareProvider] 全市场日线数据返回空: {trade_date}")
                return None
            
            # 保存到缓存
            self._save_to_cache('daily', cache_key, df)
            
            logger.info(f"[TushareProvider] ✅ 获取全市场日线数据成功: {trade_date}, 共{len(df)}条")
            return df
            
        except Exception as e:
            logger.error(f"[TushareProvider] 获取全市场日线数据失败 {trade_date}: {e}")
            return None
    
    def get_daily_basic_all(self, trade_date: str) -> Optional[pd.DataFrame]:
        """
        获取全市场每日指标（单日）
        
        Args:
            trade_date: 交易日期（YYYYMMDD）
        
        Returns:
            DataFrame: 全市场每日指标
        """
        if self._pro is None:
            logger.error("[TushareProvider] Tushare未初始化")
            return None
        
        cache_key = f"all_{trade_date}"
        
        # 尝试从缓存加载
        df = self._load_from_cache('daily_basic', cache_key)
        if df is not None:
            return df
        
        try:
            logger.info(f"[TushareProvider] 从API获取全市场每日指标: {trade_date}")
            
            df = self._pro.daily_basic(trade_date=trade_date)
            
            if df is None or df.empty:
                logger.warning(f"[TushareProvider] 全市场每日指标返回空: {trade_date}")
                return None
            
            # 保存到缓存
            self._save_to_cache('daily_basic', cache_key, df)
            
            logger.info(f"[TushareProvider] ✅ 获取全市场每日指标成功: {trade_date}, 共{len(df)}条")
            return df
            
        except Exception as e:
            logger.error(f"[TushareProvider] 获取全市场每日指标失败 {trade_date}: {e}")
            return None


# ==================== 便捷函数 ====================

def get_tushare_provider(token: str = None) -> TushareProvider:
    """
    获取TushareProvider单例
    
    Args:
        token: Tushare Pro Token
    
    Returns:
        TushareProvider实例
    """
    return TushareProvider(token)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("TushareProvider 测试")
    print("=" * 80)
    
    # 初始化Provider
    provider = TushareProvider()
    
    # 测试1: 获取股票基础信息
    print("\n1. 测试获取股票基础信息（前5条）:")
    df_basic = provider.get_stock_basic()
    if df_basic is not None:
        print(df_basic.head())
        print(f"   共 {len(df_basic)} 只股票")
    
    # 测试2: 获取日线数据
    print("\n2. 测试获取日线数据（贵州茅台 最近5天）:")
    df_daily = provider.get_stock_daily('600519', start_date='20260210', end_date='20260223')
    if df_daily is not None:
        print(df_daily[['trade_date', 'open', 'high', 'low', 'close', 'pre_close']].head())
    
    # 测试3: 获取每日指标
    print("\n3. 测试获取每日指标:")
    df_basic_daily = provider.get_stock_daily_basic('000001')
    if df_basic_daily is not None:
        print(df_basic_daily[['ts_code', 'trade_date', 'float_share', 'circ_mv']].head())
    
    # 测试4: 获取交易日历
    print("\n4. 测试获取交易日历（最近5个交易日）:")
    df_cal = provider.get_trade_cal()
    if df_cal is not None:
        df_open = df_cal[df_cal['is_open'] == 1].tail(5)
        print(df_open[['cal_date', 'is_open', 'pretrade_date']])
    
    # 测试5: 获取流通股本
    print("\n5. 测试获取流通股本:")
    float_share = provider.get_float_share('000001')
    if float_share:
        print(f"   000001 流通股本: {float_share:.2f} 万股")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
