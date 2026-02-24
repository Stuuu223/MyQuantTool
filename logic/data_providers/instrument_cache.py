"""
InstrumentCache - 股票静态数据内存缓存 (紧急修复P0级事故)

功能:
- 缓存流通股本(FloatVolume) - 从xtdata.get_instrument_detail获取
- 缓存5日历史均量 - 从xtdata.get_market_data计算
- 提供O(1)查询接口
- 盘前装弹机制 - 09:25前预热全市场数据

Author: AI总监 (紧急修复版)
Date: 2026-02-24
Version: 1.0.0
"""
import time
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

# 获取logger
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging as log_mod
    logger = log_mod.getLogger(__name__)
    logger.setLevel(logging.INFO)


class InstrumentCache:
    """
    股票静态数据内存缓存
    
    缓存结构:
    - _float_volume_cache: {stock_code: float_volume(股)}
    - _avg_volume_5d_cache: {stock_code: avg_volume_5d(股)}
    
    使用单例模式确保全局唯一缓存实例
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if InstrumentCache._initialized:
            return
        
        # 内存缓存结构
        self._float_volume_cache: Dict[str, int] = {}  # 流通股本(股)
        self._avg_volume_5d_cache: Dict[str, float] = {}  # 5日平均成交量(股)
        self._cache_metadata: Dict[str, any] = {
            'last_warmup_time': None,
            'cached_count': 0,
            'cache_date': None
        }
        
        InstrumentCache._initialized = True
        logger.info("✅ [InstrumentCache] 初始化完成")
    
    def warmup_cache(self, stock_list: List[str], force: bool = False) -> Dict[str, any]:
        """
        盘前装弹 - 预热全市场数据缓存
        
        Args:
            stock_list: 股票代码列表
            force: 是否强制刷新缓存
            
        Returns:
            Dict: 预热结果统计
        """
        start_time = time.time()
        today = datetime.now().strftime('%Y%m%d')
        
        # 检查是否已缓存当日数据
        if not force and self._cache_metadata['cache_date'] == today:
            logger.info(f"📦 [InstrumentCache] 当日数据已缓存，跳过预热"
                      f"(缓存股票数: {self._cache_metadata['cached_count']})")
            return {
                'success': True,
                'cached_count': self._cache_metadata['cached_count'],
                'skipped': True,
                'elapsed_time': 0
            }
        
        logger.info(f"🔥 [InstrumentCache] 开始盘前装弹，预热 {len(stock_list)} 只股票...")
        
        # 清空旧缓存
        self._float_volume_cache.clear()
        self._avg_volume_5d_cache.clear()
        
        # 批量获取数据
        success_count = 0
        failed_stocks = []
        
        for i, stock_code in enumerate(stock_list):
            try:
                # 获取流通股本
                float_volume = self._fetch_float_volume(stock_code)
                if float_volume and float_volume > 0:
                    self._float_volume_cache[stock_code] = float_volume
                
                # 获取5日平均成交量
                avg_volume = self._fetch_5d_avg_volume(stock_code)
                if avg_volume and avg_volume > 0:
                    self._avg_volume_5d_cache[stock_code] = avg_volume
                
                if float_volume > 0 or avg_volume > 0:
                    success_count += 1
                
                # 每100只记录一次进度
                if (i + 1) % 100 == 0:
                    logger.info(f"📊 [InstrumentCache] 预热进度: {i+1}/{len(stock_list)}")
                    
            except Exception as e:
                failed_stocks.append((stock_code, str(e)))
                if len(failed_stocks) <= 5:  # 只记录前5个错误
                    logger.warning(f"⚠️ [InstrumentCache] 获取 {stock_code} 数据失败: {e}")
        
        # 更新元数据
        self._cache_metadata['last_warmup_time'] = datetime.now()
        self._cache_metadata['cached_count'] = len(self._float_volume_cache)
        self._cache_metadata['cache_date'] = today
        
        elapsed = time.time() - start_time
        
        logger.info(
            f"✅ [InstrumentCache] 盘前装弹完成: "
            f"FloatVolume缓存 {len(self._float_volume_cache)} 只, "
            f"5日均量缓存 {len(self._avg_volume_5d_cache)} 只, "
            f"失败 {len(failed_stocks)} 只, "
            f"耗时 {elapsed:.2f}秒"
        )
        
        return {
            'success': True,
            'cached_count': len(self._float_volume_cache),
            'avg_volume_cached': len(self._avg_volume_5d_cache),
            'failed_count': len(failed_stocks),
            'failed_samples': failed_stocks[:5],
            'elapsed_time': elapsed
        }
    
    def _fetch_float_volume(self, stock_code: str) -> int:
        """
        获取流通股本(FloatVolume)
        
        Args:
            stock_code: 股票代码 (如 '000001.SZ')
            
        Returns:
            int: 流通股本(股)，失败返回0
        """
        try:
            from xtquant import xtdata
            
            # 使用get_instrument_detail获取股票详情
            # 第二个参数True表示返回DataFrame格式
            detail = xtdata.get_instrument_detail(stock_code, True)
            
            if detail is not None and len(detail) > 0:
                # FloatVolume字段即为流通股本(股)
                if hasattr(detail, 'get'):
                    float_volume = detail.get('FloatVolume', 0)
                elif isinstance(detail, dict) and 'FloatVolume' in detail:
                    float_volume = detail['FloatVolume']
                elif hasattr(detail, 'iloc'):
                    float_volume = detail.iloc[0].get('FloatVolume', 0)
                else:
                    # 尝试属性访问
                    float_volume = getattr(detail, 'FloatVolume', 0)
                
                # 确保返回整数
                return int(float_volume) if float_volume else 0
            
            return 0
            
        except Exception as e:
            logger.debug(f"[InstrumentCache] 获取FloatVolume失败 {stock_code}: {e}")
            return 0
    
    def _fetch_5d_avg_volume(self, stock_code: str) -> float:
        """
        获取5日平均成交量
        
        Args:
            stock_code: 股票代码 (如 '000001.SZ')
            
        Returns:
            float: 5日平均成交量(股)，失败返回0
        """
        try:
            from xtquant import xtdata
            
            # 计算5个交易日的日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=10)  # 多取几天避开周末
            
            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')
            
            # 获取历史日线数据
            hist_data = xtdata.get_market_data(
                field_list=['volume'],
                stock_list=[stock_code],
                period='1d',
                start_time=start_date_str,
                end_time=end_date_str,
                count=-1
            )
            
            if hist_data is not None and stock_code in hist_data:
                volume_data = hist_data[stock_code]
                if hasattr(volume_data, 'values'):
                    volumes = volume_data.values
                elif isinstance(volume_data, list):
                    volumes = volume_data
                elif isinstance(volume_data, dict):
                    volumes = list(volume_data.values())
                else:
                    volumes = []
                
                # 取最近5个有效交易日的均值
                valid_volumes = [v for v in volumes if v > 0]
                if len(valid_volumes) >= 5:
                    return sum(valid_volumes[-5:]) / 5
                elif len(valid_volumes) > 0:
                    return sum(valid_volumes) / len(valid_volumes)
            
            return 0
            
        except Exception as e:
            logger.debug(f"[InstrumentCache] 获取5日均量失败 {stock_code}: {e}")
            return 0
    
    def get_float_volume(self, stock_code: str) -> int:
        """
        获取流通股本 - O(1)查询
        
        Args:
            stock_code: 股票代码
            
        Returns:
            int: 流通股本(股)，未缓存返回0
        """
        # 标准化代码格式
        stock_code = self._normalize_code(stock_code)
        
        # 先从缓存查询
        if stock_code in self._float_volume_cache:
            return self._float_volume_cache[stock_code]
        
        # 缓存未命中，实时获取并缓存
        float_volume = self._fetch_float_volume(stock_code)
        if float_volume > 0:
            self._float_volume_cache[stock_code] = float_volume
        
        return float_volume
    
    def get_5d_avg_volume(self, stock_code: str) -> float:
        """
        获取5日平均成交量 - O(1)查询
        
        Args:
            stock_code: 股票代码
            
        Returns:
            float: 5日平均成交量(股)，未缓存返回0
        """
        # 标准化代码格式
        stock_code = self._normalize_code(stock_code)
        
        # 先从缓存查询
        if stock_code in self._avg_volume_5d_cache:
            return self._avg_volume_5d_cache[stock_code]
        
        # 缓存未命中，实时获取并缓存
        avg_volume = self._fetch_5d_avg_volume(stock_code)
        if avg_volume > 0:
            self._avg_volume_5d_cache[stock_code] = avg_volume
        
        return avg_volume
    
    def get_both(self, stock_code: str) -> tuple:
        """
        同时获取FloatVolume和5日均量
        
        Args:
            stock_code: 股票代码
            
        Returns:
            tuple: (float_volume, avg_5d_volume)
        """
        stock_code = self._normalize_code(stock_code)
        return (
            self.get_float_volume(stock_code),
            self.get_5d_avg_volume(stock_code)
        )
    
    def _normalize_code(self, code: str) -> str:
        """标准化股票代码格式"""
        if isinstance(code, str):
            if '.' not in code:
                if code.startswith('6'):
                    return f"{code}.SH"
                else:
                    return f"{code}.SZ"
        return code
    
    def is_cached(self, stock_code: str) -> bool:
        """检查股票是否已缓存"""
        stock_code = self._normalize_code(stock_code)
        return (
            stock_code in self._float_volume_cache or
            stock_code in self._avg_volume_5d_cache
        )
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        return {
            'float_volume_cached': len(self._float_volume_cache),
            'avg_volume_cached': len(self._avg_volume_5d_cache),
            'last_warmup': self._cache_metadata['last_warmup_time'],
            'cache_date': self._cache_metadata['cache_date']
        }
    
    def clear_cache(self):
        """清空缓存"""
        self._float_volume_cache.clear()
        self._avg_volume_5d_cache.clear()
        self._cache_metadata['last_warmup_time'] = None
        self._cache_metadata['cached_count'] = 0
        self._cache_metadata['cache_date'] = None
        logger.info("🗑️ [InstrumentCache] 缓存已清空")


# 全局单例实例
_instrument_cache_instance: Optional[InstrumentCache] = None


def get_instrument_cache() -> InstrumentCache:
    """
    获取InstrumentCache单例实例
    
    Returns:
        InstrumentCache: 缓存实例
    """
    global _instrument_cache_instance
    if _instrument_cache_instance is None:
        _instrument_cache_instance = InstrumentCache()
    return _instrument_cache_instance


def warmup_instrument_cache(stock_list: List[str], force: bool = False) -> Dict:
    """
    便捷函数: 预热InstrumentCache
    
    Args:
        stock_list: 股票代码列表
        force: 是否强制刷新
        
    Returns:
        Dict: 预热结果
    """
    cache = get_instrument_cache()
    return cache.warmup_cache(stock_list, force)


# 便捷查询函数
def get_float_volume(stock_code: str) -> int:
    """便捷函数: 获取流通股本"""
    return get_instrument_cache().get_float_volume(stock_code)


def get_5d_avg_volume(stock_code: str) -> float:
    """便捷函数: 获取5日平均成交量"""
    return get_instrument_cache().get_5d_avg_volume(stock_code)


if __name__ == "__main__":
    # 测试InstrumentCache
    print("🧪 InstrumentCache测试 (紧急修复版)")
    print("=" * 50)
    
    # 创建缓存实例
    cache = get_instrument_cache()
    
    # 测试股票
    test_stocks = ['000001.SZ', '600000.SH', '000002.SZ']
    
    print(f"\n📊 测试股票: {test_stocks}")
    
    # 预热缓存
    result = cache.warmup_cache(test_stocks)
    print(f"\n预热结果: {result}")
    
    # 查询测试
    print("\n🔍 查询测试:")
    for stock in test_stocks:
        fv = cache.get_float_volume(stock)
        avg = cache.get_5d_avg_volume(stock)
        print(f"  {stock}: FloatVolume={fv:,}, 5日AvgVolume={avg:,.0f}")
    
    # 缓存统计
    print(f"\n📈 缓存统计: {cache.get_cache_stats()}")
    
    print("\n✅ InstrumentCache测试完成")