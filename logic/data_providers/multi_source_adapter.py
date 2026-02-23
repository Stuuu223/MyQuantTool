"""
多数据源适配器 - 统一 akshare / tushare / baostock / demo 数据接口
支持自动降级、缓存、性能优化

⚠️ Phase 6.1.1 更新:
- AkShare数据源已弃用，建议切换到Tushare
- 推荐使用 TushareProvider 替代 AkshareDataSource
- 保留AkshareDataSource用于兼容性，不再维护
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from abc import ABC, abstractmethod
import logging
import time
from functools import wraps

import akshare as ak

from logic.data_quality_validator import (
    validate_kline,
    validate_tick,
    DataQualityError
)

logger = logging.getLogger(__name__)


class DataSourceConfig:
    """数据源配置"""
    
    def __init__(self):
        self.primary_source = "akshare"  # 优先数据源
        self.fallback_source = "demo"    # 降级数据源
        self.cache_ttl = 300  # 缓存时间(秒)
        self.retry_times = 3  # 重试次数
        self.timeout = 10  # 超时时间(秒)
        self.enable_cache = True


class PerformanceTracker:
    """性能追踪器"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
    
    def record(self, operation: str, elapsed: float) -> None:
        """记录操作耗时"""
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(elapsed)
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """获取统计信息"""
        if operation not in self.metrics or not self.metrics[operation]:
            return {}
        
        times = self.metrics[operation]
        return {
            'mean': np.mean(times),
            'median': np.median(times),
            'min': np.min(times),
            'max': np.max(times),
            'std': np.std(times),
            'count': len(times)
        }


class BaseDataSource(ABC):
    """基础数据源类"""
    
    def __init__(self, name: str):
        self.name = name
        self.perf_tracker = PerformanceTracker()
    
    @abstractmethod
    def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览"""
        pass
    
    @abstractmethod
    def get_stock_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """获取股票报价"""
        pass
    
    @abstractmethod
    def get_kline(self, code: str, start_date: str, end_date: str, period: str = '1d') -> Optional[pd.DataFrame]:
        """获取K线数据"""
        pass
    
    @abstractmethod
    def get_lhb(self, date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """获取龙虎榜数据"""
        pass
    
    @abstractmethod
    def get_limit_up_stocks(self, count: int = 50) -> Optional[pd.DataFrame]:
        """获取涨停股票"""
        pass
    
    @abstractmethod
    def get_sector_performance(self) -> Optional[pd.DataFrame]:
        """获取行业涨幅"""
        pass
    
    def record_performance(self, operation: str):
        """装饰器: 记录性能"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    elapsed = time.time() - start
                    self.perf_tracker.record(operation, elapsed)
                    logger.debug(f"{self.name}.{operation} took {elapsed:.3f}s")
            return wrapper
        return decorator


class AkshareDataSource(BaseDataSource):
    """
    ⚠️ [已弃用] Akshare 数据源
    
    本数据源已在Phase 6.1.1中弃用，请使用TushareProvider替代。
    保留用于兼容性，不再维护。
    """
    
    def __init__(self):
        import warnings
        warnings.warn(
            "AkshareDataSource 已在Phase 6.1.1中弃用，请使用 TushareProvider 替代",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__("akshare")
    
    def get_market_overview(self) -> Dict[str, Any]:
        """从 akshare 获取市场概览"""
        start = time.time()
        try:
            # 三大指数
            sh_index = ak.stock_zh_index_spot()[ak.stock_zh_index_spot()['symbol'] == 'sh000001'].iloc[0]
            sz_index = ak.stock_zh_index_spot()[ak.stock_zh_index_spot()['symbol'] == 'sz399001'].iloc[0]
            cy_index = ak.stock_zh_index_spot()[ak.stock_zh_index_spot()['symbol'] == 'sz399006'].iloc[0]
            
            result = {
                'sh': {
                    'price': float(sh_index['price']),
                    'change': float(sh_index['percent']),
                    'name': '上证指数'
                },
                'sz': {
                    'price': float(sz_index['price']),
                    'change': float(sz_index['percent']),
                    'name': '深证成指'
                },
                'cy': {
                    'price': float(cy_index['price']),
                    'change': float(cy_index['percent']),
                    'name': '创业板指'
                },
                'timestamp': datetime.now().isoformat()
            }
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_market_overview", elapsed)
            logger.debug(f"{self.name}.get_market_overview took {elapsed:.3f}s")
            return result
        except Exception as e:
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_market_overview", elapsed)
            logger.debug(f"{self.name}.get_market_overview took {elapsed:.3f}s")
            logger.error(f"akshare market_overview failed: {e}")
            return None
    
    def get_stock_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """从 akshare 获取股票报价"""
        start = time.time()
        try:
            # 确保代码格式正确
            if len(code) == 6:
                if code.startswith('6'):
                    symbol = f"sh{code}"
                else:
                    symbol = f"sz{code}"
            else:
                symbol = code
            
            df = ak.stock_individual_info_em(symbol=symbol)
            if df.empty:
                result = None
            else:
                row = df.iloc[0]
                result = {
                    'code': code,
                    'name': row.get('股票简称', 'N/A'),
                    'price': float(row.get('最新价', 0)),
                    'change_percent': float(row.get('涨跌幅', 0)),
                    'volume': float(row.get('成交量', 0)),
                    'amount': float(row.get('成交额', 0)),
                }
            
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_stock_quote", elapsed)
            logger.debug(f"{self.name}.get_stock_quote took {elapsed:.3f}s")
            return result
        except Exception as e:
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_stock_quote", elapsed)
            logger.debug(f"{self.name}.get_stock_quote took {elapsed:.3f}s")
            logger.warning(f"akshare quote for {code} failed: {e}")
            return None
    
    def get_kline(self, code: str, start_date: str, end_date: str, period: str = '1d') -> Optional[pd.DataFrame]:
        """从 akshare 获取K线数据"""
        start = time.time()
        try:
            # 转换代码格式
            if len(code) == 6:
                if code.startswith('6'):
                    symbol = f"sh{code}"
                else:
                    symbol = f"sz{code}"
            else:
                symbol = code
            
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust=''
            )
            
            if df.empty:
                result = None
            else:
                result = df[['日期', '开盘', '最高', '最低', '收盘', '成交量']].rename(columns={
                    '日期': 'Date',
                    '开盘': 'Open',
                    '最高': 'High',
                    '最低': 'Low',
                    '收盘': 'Close',
                    '成交量': 'Volume'
                })
            
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_kline", elapsed)
            logger.debug(f"{self.name}.get_kline took {elapsed:.3f}s")
            return result
        except Exception as e:
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_kline", elapsed)
            logger.debug(f"{self.name}.get_kline took {elapsed:.3f}s")
            logger.warning(f"akshare kline for {code} failed: {e}")
            return None
    
    def get_lhb(self, date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """从 akshare 获取龙虎榜"""
        start = time.time()
        try:
            if date is None:
                date = datetime.now().strftime('%Y%m%d')
            else:
                date = date.replace('-', '')
            
            df = ak.stock_lhb_detail_sina(date=date)
            result = df if not df.empty else None
            
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_lhb", elapsed)
            logger.debug(f"{self.name}.get_lhb took {elapsed:.3f}s")
            return result
        except Exception as e:
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_lhb", elapsed)
            logger.debug(f"{self.name}.get_lhb took {elapsed:.3f}s")
            logger.warning(f"akshare lhb failed: {e}")
            return None
    
    def get_limit_up_stocks(self, count: int = 50) -> Optional[pd.DataFrame]:
        """从 akshare 获取涨停股票"""
        start = time.time()
        try:
            df = ak.stock_zh_a_spot()[ak.stock_zh_a_spot()['涨跌幅'] >= 9.95]
            result = df[['代码', '名称', '最新价', '涨跌幅', '成交量']].head(count) if not df.empty else None
            
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_limit_up_stocks", elapsed)
            logger.debug(f"{self.name}.get_limit_up_stocks took {elapsed:.3f}s")
            return result
        except Exception as e:
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_limit_up_stocks", elapsed)
            logger.debug(f"{self.name}.get_limit_up_stocks took {elapsed:.3f}s")
            logger.warning(f"akshare limit_up failed: {e}")
            return None
    
    def get_sector_performance(self) -> Optional[pd.DataFrame]:
        """从 akshare 获取行业涨幅"""
        start = time.time()
        try:
            df = ak.stock_board_industry_name_em()
            if not df.empty:
                # 使用列索引来避免编码问题
                # 列顺序: 序号, 板块名称, 板块代码, 最新价, 涨跌额, 涨跌幅, 成交额, 换手率, 上涨家数, 下跌家数, 领涨股票, 领涨股票-涨跌幅
                # 我们需要: 板块名称(索引1), 最新价(索引3), 涨跌幅(索引5), 成交额(索引6)
                result = pd.DataFrame({
                    '板块名称': df.iloc[:, 1],  # 板块名称
                    '最新价': df.iloc[:, 3],    # 最新价
                    '涨跌幅': df.iloc[:, 5],    # 涨跌幅
                    '成交量': df.iloc[:, 6]     # 成交额
                })
            else:
                result = None
            
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_sector_performance", elapsed)
            logger.debug(f"{self.name}.get_sector_performance took {elapsed:.3f}s")
            return result
        except Exception as e:
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_sector_performance", elapsed)
            logger.debug(f"{self.name}.get_sector_performance took {elapsed:.3f}s")
            logger.warning(f"akshare sector failed: {e}")
            return None


class DemoDataSource(BaseDataSource):
    """Demo 数据源 (用于测试和降级)"""
    
    def __init__(self):
        super().__init__("demo")
    
    def get_market_overview(self) -> Dict[str, Any]:
        """生成模拟市场概览"""
        start = time.time()
        try:
            result = {
                'sh': {
                    'price': 3250.5 + np.random.randn() * 10,
                    'change': 1.2 + np.random.randn() * 0.5,
                    'name': '上证指数'
                },
                'sz': {
                    'price': 10850.2 + np.random.randn() * 20,
                    'change': 0.8 + np.random.randn() * 0.4,
                    'name': '深证成指'
                },
                'cy': {
                    'price': 2150.8 + np.random.randn() * 15,
                    'change': 2.1 + np.random.randn() * 0.6,
                    'name': '创业板指'
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_market_overview", elapsed)
            logger.debug(f"{self.name}.get_market_overview took {elapsed:.3f}s")
            return result
        except Exception as e:
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_market_overview", elapsed)
            logger.debug(f"{self.name}.get_market_overview took {elapsed:.3f}s")
            logger.warning(f"demo get_market_overview failed: {e}")
            raise
    
    def get_stock_quote(self, code: str) -> Dict[str, Any]:
        """生成模拟股票报价"""
        start = time.time()
        try:
            np.random.seed(hash(code) % 2**32)
            result = {
                'code': code,
                'name': f'股票{code}',
                'price': 100 + np.random.randn() * 50,
                'change_percent': np.random.randn() * 5,
                'volume': np.random.randint(1000000, 10000000),
                'amount': np.random.randint(100000000, 1000000000),
            }
            
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_stock_quote", elapsed)
            logger.debug(f"{self.name}.get_stock_quote took {elapsed:.3f}s")
            return result
        except Exception as e:
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_stock_quote", elapsed)
            logger.debug(f"{self.name}.get_stock_quote took {elapsed:.3f}s")
            logger.warning(f"demo get_stock_quote failed: {e}")
            raise
    
    def get_kline(self, code: str, start_date: str, end_date: str, period: str = '1d') -> pd.DataFrame:
        """生成模拟K线数据"""
        start = time.time()
        try:
            dates = pd.date_range(start_date, end_date, freq='D')
            n = len(dates)
            np.random.seed(hash(code) % 2**32)
            
            prices = 1800 + np.cumsum(np.random.randn(n)) * 10
            result = pd.DataFrame({
                'Date': dates,
                'Open': prices + np.random.randn(n) * 5,
                'High': prices + abs(np.random.randn(n) * 8),
                'Low': prices - abs(np.random.randn(n) * 8),
                'Close': prices,
                'Volume': np.random.randint(1000000, 5000000, n)
            })
            
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_kline", elapsed)
            logger.debug(f"{self.name}.get_kline took {elapsed:.3f}s")
            return result
        except Exception as e:
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_kline", elapsed)
            logger.debug(f"{self.name}.get_kline took {elapsed:.3f}s")
            logger.warning(f"demo get_kline failed: {e}")
            raise
    
    def get_lhb(self, date: Optional[str] = None) -> pd.DataFrame:
        """生成模拟龙虎榜"""
        start = time.time()
        try:
            result = pd.DataFrame({
                '代码': ['600519', '000333', '600036', '601988'],
                '名称': ['贵州茅台', '美的集团', '招商银行', '中国银行'],
                '上榜次数': [3, 2, 1, 2],
                '成交金额': [100000000, 80000000, 50000000, 70000000]
            })
            
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_lhb", elapsed)
            logger.debug(f"{self.name}.get_lhb took {elapsed:.3f}s")
            return result
        except Exception as e:
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_lhb", elapsed)
            logger.debug(f"{self.name}.get_lhb took {elapsed:.3f}s")
            logger.warning(f"demo get_lhb failed: {e}")
            raise
    
    def get_limit_up_stocks(self, count: int = 50) -> pd.DataFrame:
        """生成模拟涨停股票"""
        start = time.time()
        try:
            codes = [f'60{i:04d}' for i in range(1, count + 1)]
            result = pd.DataFrame({
                '代码': codes[:count],
                '名称': [f'股票{c}' for c in codes[:count]],
                '最新价': np.random.uniform(10, 100, count),
                '涨跌幅': [10.0] * count,
                '成交量': np.random.randint(1000000, 10000000, count)
            })
            
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_limit_up_stocks", elapsed)
            logger.debug(f"{self.name}.get_limit_up_stocks took {elapsed:.3f}s")
            return result
        except Exception as e:
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_limit_up_stocks", elapsed)
            logger.debug(f"{self.name}.get_limit_up_stocks took {elapsed:.3f}s")
            logger.warning(f"demo get_limit_up_stocks failed: {e}")
            raise
    
    def get_sector_performance(self) -> pd.DataFrame:
        """生成模拟行业涨幅"""
        start = time.time()
        try:
            # 尝试从真实数据源获取板块列表，如果获取失败则使用默认列表
            try:
                # 尝试获取真实的行业板块数据
                sectors_df = ak.stock_sector_sina()
                if sectors_df is not None and not sectors_df.empty and len(sectors_df) >= 6:
                    sectors = sectors_df['板块名称'].head(6).tolist()
                else:
                    sectors = ['医药生物', '电子', '机械设备', '房地产', '化工', '电气设备']
            except:
                sectors = ['医药生物', '电子', '机械设备', '房地产', '化工', '电气设备']
                
            result = pd.DataFrame({
                '板块名称': sectors,
                '最新价': np.random.uniform(1000, 5000, len(sectors)),
                '涨跌幅': np.random.uniform(-2, 5, len(sectors)),
                '成交量': np.random.randint(10000000, 100000000, len(sectors))
            })
            
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_sector_performance", elapsed)
            logger.debug(f"{self.name}.get_sector_performance took {elapsed:.3f}s")
            return result
        except Exception as e:
            # 记录性能
            elapsed = time.time() - start
            self.perf_tracker.record("get_sector_performance", elapsed)
            logger.debug(f"{self.name}.get_sector_performance took {elapsed:.3f}s")
            logger.warning(f"demo get_sector_performance failed: {e}")
            raise


class MultiSourceDataAdapter:
    """多数据源适配器 - 统一接口"""
    
    def __init__(self, config: Optional[DataSourceConfig] = None):
        self.config = config or DataSourceConfig()
        self.sources: Dict[str, BaseDataSource] = {
            'akshare': AkshareDataSource(),
            'demo': DemoDataSource()
        }
        self._cache: Dict[str, Tuple[Any, float]] = {}
    
    def _get_cache_key(self, operation: str, *args, **kwargs) -> str:
        """生成缓存键"""
        return f"{operation}:{args}:{kwargs}"
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if not self.config.enable_cache or key not in self._cache:
            return None
        
        data, timestamp = self._cache[key]
        if time.time() - timestamp > self.config.cache_ttl:
            del self._cache[key]
            return None
        
        return data
    
    def _set_cache(self, key: str, data: Any) -> None:
        """设置缓存"""
        if self.config.enable_cache:
            self._cache[key] = (data, time.time())
    
    def _get_sources_priority(self) -> List[str]:
        """获取数据源优先级列表"""
        return [self.config.primary_source, self.config.fallback_source]
    
    def _estimate_min_length(self, period: str, start_date: Optional[str]) -> Optional[int]:
        """
        根据周期和起始日期估算最小数据长度
        
        Args:
            period: 周期（如 '1d', '60m'）
            start_date: 起始日期
        
        Returns:
            预期最小长度（None表示不检查）
        """
        if not start_date:
            return None
        
        # 简单实现：根据周期估算
        if period == '1d':
            # 日线：假设一年约 240 个交易日
            # 如果起始日期是 90 天前，预期约 60 条数据
            return 60
        elif period in ['60m', '30m', '15m', '5m', '1m']:
            # 分钟线：暂不检查长度（交易时间复杂）
            return None
        else:
            return None
    
    def _validate_result(self, operation: str, result: Any, *args, **kwargs) -> Any:
        """
        根据操作类型进行数据质量校验
        
        Args:
            operation: 操作名称（如 'get_kline', 'get_tick'）
            result: 数据源返回的结果
            args, kwargs: 原始调用参数
        
        Returns:
            校验通过的数据
        
        Raises:
            DataQualityError: 数据质量不合格
        """
        if operation == 'get_kline':
            # K线数据校验
            code = args[0] if args else kwargs.get('code')
            period = args[1] if len(args) > 1 else kwargs.get('period')
            
            # 根据周期估算最小长度
            min_length = self._estimate_min_length(period, kwargs.get('start_date'))
            
            return validate_kline(result, code, period, min_length)
        
        elif operation == 'get_tick':
            # 分时数据校验
            code = args[0] if args else kwargs.get('code')
            trade_date = args[1] if len(args) > 1 else kwargs.get('trade_date')
            
            return validate_tick(result, code, trade_date)
        
        else:
            # 其他操作：基本校验（不为None）
            if result is None:
                raise DataQualityError(f"操作 {operation} 返回None")
            return result
    
    def _try_sources(self, operation: str, *args, **kwargs) -> Optional[Any]:
        """
        尝试多个数据源，按优先级顺序
        
        Returns:
            成功获取的数据（已通过质量校验）
        
        Raises:
            DataQualityError: 所有数据源均失败或数据质量不合格
        """
        sources_to_try = self._get_sources_priority()
        
        last_error = None
        for source_name in sources_to_try:
            if source_name not in self.sources:
                logger.warning(f"数据源 {source_name} 不可用，跳过")
                continue
            
            try:
                source = self.sources[source_name]
                method = getattr(source, operation, None)
                if not method:
                    logger.warning(f"{source_name} 不支持操作 {operation}")
                    continue
                
                # 获取数据
                result = method(*args, **kwargs)
                
                # ✅ 新增：数据质量硬校验
                result = self._validate_result(operation, result, *args, **kwargs)
                
                logger.info(f"✓ {source_name}.{operation} 成功并通过质量校验")
                return result
                
            except DataQualityError as e:
                # 数据质量不合格，记录后尝试下一个数据源
                logger.warning(f"✗ {source_name}.{operation} 数据质量不合格: {e}")
                last_error = e
                
            except Exception as e:
                # 其他异常，记录后尝试下一个数据源
                logger.warning(f"✗ {source_name}.{operation} 失败: {e}")
                last_error = e
        
        # ❌ 所有数据源都失败
        error_msg = f"所有数据源均失败: {operation}({args}, {kwargs})"
        if last_error:
            error_msg += f", 最后一个错误: {last_error}"
        
        # 🔥 关键改动：不再返回 None，而是抛异常
        raise DataQualityError(error_msg)
    
    def get_market_overview(self) -> Optional[Dict[str, Any]]:
        """获取市场概览"""
        cache_key = self._get_cache_key("market_overview")
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        result = self._try_sources("get_market_overview")
        if result:
            self._set_cache(cache_key, result)
        return result
    
    def get_stock_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """获取股票报价"""
        cache_key = self._get_cache_key("stock_quote", code)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        result = self._try_sources("get_stock_quote", code)
        if result:
            self._set_cache(cache_key, result)
        return result
    
    def get_kline(self, code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取K线数据"""
        cache_key = self._get_cache_key("kline", code, start_date, end_date)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        result = self._try_sources("get_kline", code, start_date, end_date)
        if result is not None:
            self._set_cache(cache_key, result)
        return result
    
    def get_lhb(self, date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """获取龙虎榜"""
        cache_key = self._get_cache_key("lhb", date)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        result = self._try_sources("get_lhb", date)
        if result is not None:
            self._set_cache(cache_key, result)
        return result
    
    def get_limit_up_stocks(self, count: int = 50) -> Optional[pd.DataFrame]:
        """获取涨停股票"""
        cache_key = self._get_cache_key("limit_up", count)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        result = self._try_sources("get_limit_up_stocks", count)
        if result is not None:
            self._set_cache(cache_key, result)
        return result
    
    def get_sector_performance(self) -> Optional[pd.DataFrame]:
        """获取行业涨幅"""
        cache_key = self._get_cache_key("sector")
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        result = self._try_sources("get_sector_performance")
        if result is not None:
            self._set_cache(cache_key, result)
        return result
    
    def get_performance_stats(self, source: str = 'akshare') -> Dict[str, Dict[str, float]]:
        """获取性能统计"""
        if source not in self.sources:
            return {}
        
        tracker = self.sources[source].perf_tracker
        stats = {}
        for operation in tracker.metrics:
            stats[operation] = tracker.get_stats(operation)
        return stats
    
    def clear_cache(self) -> None:
        """清除所有缓存"""
        self._cache.clear()
        logger.info("Cache cleared")


# 全局实例
_adapter_instance: Optional[MultiSourceDataAdapter] = None


def get_adapter(config: Optional[DataSourceConfig] = None) -> MultiSourceDataAdapter:
    """获取适配器实例 (单例)"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = MultiSourceDataAdapter(config)
    return _adapter_instance


if __name__ == "__main__":
    # 示例
    logging.basicConfig(level=logging.INFO)
    adapter = get_adapter()
    
    # 测试市场概览
    market = adapter.get_market_overview()
    print(f"Market: {market}")
    
    # 测试股票报价
    quote = adapter.get_stock_quote("600519")
    print(f"Quote: {quote}")
    
    # 测试涨停股
    limit_ups = adapter.get_limit_up_stocks(10)
    print(f"Limit ups: {limit_ups}")