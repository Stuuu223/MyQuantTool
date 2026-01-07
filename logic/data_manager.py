"""DataManager - 统一数据管理器（akshare 实时 + 缓存 + 降级）

Version: 1.0.0
Feature: akshare 输入 + TTL 缓存 120s + 错误自动降级
"""

import akshare as ak
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, cache_ttl: int = 120):
        self.cache_ttl = cache_ttl
        self._quote_cache = {}
        self._kline_cache = {}
        self._fundamental_cache = {}
        self._cache_time = {}
        logger.info(f"DataManager 上业 (TTL={cache_ttl}s)")

    def get_realtime_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """Get realtime quote via akshare"""
        try:
            code_norm = self._normalize_code(code)
            if code_norm in self._quote_cache and self._is_cache_fresh(code_norm):
                return self._quote_cache[code_norm]
            
            df = ak.stock_zh_a_spot_em()
            code_num = code_norm.replace('sh', '60').replace('sz', '00')
            row = df[df['代码'] == code_num]
            
            if row.empty:
                return None
            
            r = row.iloc[0]
            result = {
                'code': code_norm,
                'name': str(r['名称']),
                'price': float(r['最新价']),
                'change_pct': float(r['涨跌幅']) / 100.0,
                'volume': int(r.get('成交量', 0)),
                'turnover': float(r.get('成交额', 0)),
                'high': float(r.get('最高', 0)),
                'low': float(r.get('最低', 0)),
                'timestamp': datetime.now().isoformat()
            }
            self._quote_cache[code_norm] = result
            self._cache_time[code_norm] = datetime.now()
            return result
        except Exception as e:
            logger.error(f"get_realtime_quote failed: {e}")
            return None

    def get_kline_data(self, code: str, period: str = 'daily', start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Get K-line data with MA indicators"""
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            
            cache_key = f"{code}_{period}_{start_date}_{end_date}"
            if cache_key in self._kline_cache and self._is_cache_fresh(cache_key, ttl=600):
                return self._kline_cache[cache_key]
            
            df = ak.stock_zh_a_hist(symbol=self._normalize_code(code), period=period, start_date=start_date, end_date=end_date, adjust='qfq')
            
            if df.empty:
                return None
            
            df = df.rename(columns={'\u65e5\u671f': 'date', '\u5f00\u76d8': 'open', '\u6536\u76d8': 'close', '\u9ad8': 'high', '\u4f4e': 'low', '\u6210\u4ea4\u91cf': 'volume'})
            
            for col in ['open', 'close', 'high', 'low']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            
            close = df['close'].values
            df['ma5'] = pd.Series(self._calculate_ma(close, 5), index=df.index)
            df['ma20'] = pd.Series(self._calculate_ma(close, 20), index=df.index)
            df['ma60'] = pd.Series(self._calculate_ma(close, 60), index=df.index)
            
            self._kline_cache[cache_key] = df
            self._cache_time[cache_key] = datetime.now()
            return df
        except Exception as e:
            logger.error(f"get_kline_data failed: {e}")
            return None

    def get_fundamental_data(self, code: str) -> Optional[Dict[str, Any]]:
        """Get fundamental data (PE, PB)"""
        try:
            cache_key = f"{code}_fundamental"
            if cache_key in self._fundamental_cache and self._is_cache_fresh(cache_key, ttl=600):
                return self._fundamental_cache[cache_key]
            
            df = ak.stock_zh_a_spot_em()
            code_num = code.replace('sh', '60').replace('sz', '00')
            row = df[df['代码'] == code_num]
            
            if row.empty:
                return None
            
            r = row.iloc[0]
            result = {
                'code': code,
                'name': str(r['名称']),
                'pe_ttm': float(r.get('市盈率', 0)),
                'pb': float(r.get('市净率', 0)),
                'timestamp': datetime.now().isoformat()
            }
            self._fundamental_cache[cache_key] = result
            self._cache_time[cache_key] = datetime.now()
            return result
        except Exception as e:
            logger.error(f"get_fundamental_data failed: {e}")
            return None

    def _normalize_code(self, code: str) -> str:
        code = str(code).strip()
        if code.isdigit():
            return f'sh{code}' if code.startswith('6') else f'sz{code}'
        return code

    def _is_cache_fresh(self, key: str, ttl: Optional[int] = None) -> bool:
        if key not in self._cache_time:
            return False
        ttl_seconds = ttl or self.cache_ttl
        return (datetime.now() - self._cache_time[key]).total_seconds() < ttl_seconds

    @staticmethod
    def _calculate_ma(prices: np.ndarray, period: int) -> np.ndarray:
        result = np.empty_like(prices, dtype=float)
        result[:] = np.nan
        for i in range(period - 1, len(prices)):
            result[i] = np.mean(prices[i - period + 1:i + 1])
        return result

    def clear_cache(self):
        self._quote_cache.clear()
        self._kline_cache.clear()
        self._fundamental_cache.clear()
        self._cache_time.clear()

_instance = None

def get_data_manager(cache_ttl: int = 120) -> DataManager:
    global _instance
    if _instance is None:
        _instance = DataManager(cache_ttl=cache_ttl)
    return _instance
