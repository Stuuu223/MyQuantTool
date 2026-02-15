"""
EasyQuotation适配器 - V15数据源渐进式替换

功能：
1. 兼容easyquotation接口（stocks, market_snapshot）
2. 内部使用QMT get_full_tick()获取数据
3. 数据格式转换（QMT → easyquotation）
4. 渐进式替换策略（平滑过渡）

设计原则：
- 对外接口不变，内部实现替换
- 保证数据质量（QMT > easyquotation）
- 降低迁移风险（适配器模式）

作者：AI总监
日期：2026-02-15
版本：V15.0
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import logging

# 导入项目现有模块
from logic.utils.logger import get_logger
from logic.data_providers.qmt_manager import get_qmt_manager
from logic.utils.code_converter import CodeConverter

logger = get_logger(__name__)


class EasyQuotationAdapter:
    """
    EasyQuotation适配器
    
    功能：
    1. 兼容easyquotation.stocks()接口
    2. 兼容easyquotation.market_snapshot()接口
    3. 数据格式转换（QMT → easyquotation）
    4. 性能优化（批量获取、缓存）
    
    使用方法：
    >>> adapter = EasyQuotationAdapter()
    >>> data = adapter.stocks(['000001', '600000'])
    """

    def __init__(self):
        self.qmt_manager = get_qmt_manager()
        self.code_converter = CodeConverter()
        
        # 缓存
        self._cache = {
            'data': {},
            'timestamp': 0.0,
            'ttl': 1.0  # 缓存1秒
        }
        
        # 统计
        self._call_count = 0
        self._cache_hit_count = 0
        self._qmt_call_count = 0
        
        logger.info("✅ [EasyQuotation适配器] 初始化完成")
        logger.warning("⚠️ [EasyQuotation适配器] easyquotation已废弃，自动降级到QMT")

    def stocks(self, stock_list: List[str], prefix: bool = False) -> Dict[str, Dict]:
        """
        获取股票实时数据（兼容easyquotation接口）
        
        Args:
            stock_list: 股票代码列表
                      - easyquotation格式: '000001', '600000'
                      - QMT格式: '000001.SZ', '600000.SH'
            prefix: 是否添加交易所前缀（默认False）
        
        Returns:
            Dict[str, Dict]: 股票数据字典
                key: 股票代码（easyquotation格式：000001）
                value: 股票数据字典
                    {
                        'name': 股票名称,
                        'code': 股票代码,
                        'now': 当前价格,
                        'close': 昨收,
                        'open': 今开,
                        'high': 最高,
                        'low': 最低,
                        'volume': 成交量,
                        'amount': 成交额,
                        'turnover': 换手率,
                        'ratio': 量比,
                        'amplitude': 振幅,
                        'rise_percent': 涨跌幅,
                        'rise': 涨跌额,
                        'time': 时间戳,
                        ... 其他字段
                    }
        
        Example:
            >>> adapter = EasyQuotationAdapter()
            >>> data = adapter.stocks(['000001', '600000'])
            >>> print(data['000001'])
        """
        self._call_count += 1
        
        # 检查缓存
        if self._is_cache_valid(stock_list):
            self._cache_hit_count += 1
            logger.debug(f"✅ [EasyQuotation适配器] 缓存命中 ({len(stock_list)}只股票)")
            return self._cache['data']
        
        # 转换股票代码（easyquotation格式 → QMT格式）
        qmt_codes = self._convert_to_qmt_codes(stock_list)
        
        # 获取QMT数据
        qmt_data = self._get_qmt_data(qmt_codes)
        
        # 转换数据格式（QMT → easyquotation）
        eq_data = self._convert_qmt_to_easy_format(qmt_data, prefix)
        
        # 更新缓存
        self._cache['data'] = eq_data
        self._cache['timestamp'] = time.time()
        
        logger.info(
            f"✅ [EasyQuotation适配器] 获取成功 "
            f"({len(eq_data)}只股票, "
            f"缓存{self._cache_hit_count}/{self._call_count})"
        )
        
        return eq_data

    def market_snapshot(self, prefix: bool = False) -> Dict[str, Dict]:
        """
        获取市场快照（兼容easyquotation接口）
        
        Args:
            prefix: 是否添加交易所前缀（默认False）
        
        Returns:
            Dict[str, Dict]: 市场快照数据
        """
        logger.info("📊 [EasyQuotation适配器] 获取市场快照")
        
        # TODO: 实现市场快照逻辑
        # 可以获取市场指数、涨停股票、跌停股票等
        
        logger.warning("⚠️ [EasyQuotation适配器] market_snapshot功能待实现")
        return {}

    def _is_cache_valid(self, stock_list: List[str]) -> bool:
        """检查缓存是否有效"""
        cache_age = time.time() - self._cache['timestamp']
        if cache_age > self._cache['ttl']:
            return False
        
        # 检查缓存中的股票数量是否匹配
        if len(self._cache['data']) != len(stock_list):
            return False
        
        return True

    def _convert_to_qmt_codes(self, stock_list: List[str]) -> List[str]:
        """
        转换股票代码（easyquotation格式 → QMT格式）
        
        Args:
            stock_list: easyquotation格式 ['000001', '600000']
        
        Returns:
            List[str]: QMT格式 ['000001.SZ', '600000.SH']
        """
        qmt_codes = []
        
        for code in stock_list:
            # 如果已经是QMT格式，直接使用
            if '.' in code:
                qmt_codes.append(code)
            else:
                # 转换为QMT格式
                qmt_code = self.code_converter.to_qmt(code)
                qmt_codes.append(qmt_code)
        
        return qmt_codes

    def _get_qmt_data(self, qmt_codes: List[str]) -> Dict[str, Dict]:
        """
        获取QMT数据
        
        Args:
            qmt_codes: QMT格式股票代码列表
        
        Returns:
            Dict[str, Dict]: QMT Tick数据
        """
        self._qmt_call_count += 1
        
        try:
            # 批量获取Tick数据
            tick_data = self.qmt_manager.get_full_tick(qmt_codes)
            
            if not tick_data:
                logger.warning(f"⚠️ [EasyQuotation适配器] QMT数据获取失败: 返回空数据")
                return {}
            
            logger.debug(f"✅ [EasyQuotation适配器] QMT数据获取成功 ({len(tick_data)}只股票)")
            return tick_data
            
        except Exception as e:
            logger.error(f"❌ [EasyQuotation适配器] QMT数据获取异常: {e}", exc_info=True)
            return {}

    def _convert_qmt_to_easy_format(
        self,
        qmt_data: Dict[str, Dict],
        prefix: bool = False
    ) -> Dict[str, Dict]:
        """
        转换数据格式（QMT → easyquotation）
        
        Args:
            qmt_data: QMT Tick数据
            prefix: 是否添加交易所前缀
        
        Returns:
            Dict[str, Dict]: easyquotation格式数据
        """
        eq_data = {}
        
        for qmt_code, tick in qmt_data.items():
            if not tick:
                continue
            
            # 转换股票代码（QMT格式 → easyquotation格式）
            if prefix:
                # 保留交易所前缀
                eq_code = qmt_code
            else:
                # 去除交易所前缀
                eq_code = self.code_converter.to_standard(qmt_code)
            
            # 转换数据格式
            eq_stock = {
                'name': tick.get('name', ''),
                'code': eq_code,
                'now': tick.get('lastPrice', 0),          # 当前价格
                'close': tick.get('lastClose', 0),         # 昨收
                'open': tick.get('open', 0),               # 今开
                'high': tick.get('high', 0),               # 最高
                'low': tick.get('low', 0),                 # 最低
                'volume': tick.get('volume', 0),           # 成交量（手）
                'amount': tick.get('amount', 0),           # 成交额（元）
                'turnover': self._calculate_turnover(tick),  # 换手率
                'ratio': self._calculate_ratio(tick),        # 量比
                'amplitude': self._calculate_amplitude(tick), # 振幅
                'rise_percent': self._calculate_rise_percent(tick), # 涨跌幅
                'rise': self._calculate_rise(tick),           # 涨跌额
                'time': tick.get('timetag', ''),           # 时间戳
                
                # QMT扩展字段
                'bid1': tick.get('bid1', 0),   # 买一价
                'bid1_vol': tick.get('bidVol1', 0),  # 买一量
                'ask1': tick.get('ask1', 0),   # 卖一价
                'ask1_vol': tick.get('askVol1', 0),  # 卖一量
                
                # 成交信息
                'numTrades': tick.get('numTrades', 0),  # 成交笔数
                'bidVol': tick.get('bidVol', [0]*5),   # 买盘量
                'askVol': tick.get('askVol', [0]*5),   # 卖盘量
            }
            
            eq_data[eq_code] = eq_stock
        
        return eq_data

    def _calculate_turnover(self, tick: Dict) -> float:
        """计算换手率"""
        try:
            # QMT Tick数据中没有直接提供换手率
            # 可以通过 成交量 / 流通股本 计算
            # 这里返回0，实际使用时可以从其他数据源获取
            return 0.0
        except Exception:
            return 0.0

    def _calculate_ratio(self, tick: Dict) -> float:
        """计算量比"""
        try:
            # QMT Tick数据中没有直接提供量比
            # 量比 = 当前成交量 / 过去5天平均成交量
            # 这里返回0，实际使用时可以从历史数据计算
            return 0.0
        except Exception:
            return 0.0

    def _calculate_amplitude(self, tick: Dict) -> float:
        """计算振幅"""
        try:
            high = tick.get('high', 0)
            low = tick.get('low', 0)
            last_close = tick.get('lastClose', 0)
            
            if last_close > 0:
                return (high - low) / last_close * 100
            return 0.0
        except Exception:
            return 0.0

    def _calculate_rise_percent(self, tick: Dict) -> float:
        """计算涨跌幅"""
        try:
            last_price = tick.get('lastPrice', 0)
            last_close = tick.get('lastClose', 0)
            
            if last_close > 0:
                return (last_price - last_close) / last_close * 100
            return 0.0
        except Exception:
            return 0.0

    def _calculate_rise(self, tick: Dict) -> float:
        """计算涨跌额"""
        try:
            last_price = tick.get('lastPrice', 0)
            last_close = tick.get('lastClose', 0)
            
            return last_price - last_close
        except Exception:
            return 0.0

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            'call_count': self._call_count,
            'cache_hit_count': self._cache_hit_count,
            'qmt_call_count': self._qmt_call_count,
            'cache_hit_rate': self._cache_hit_count / self._call_count if self._call_count > 0 else 0.0
        }


# ==================== 单例模式 ====================

_adapter_instance: Optional[EasyQuotationAdapter] = None
_adapter_lock = None  # type: ignore


def get_easyquotation_adapter() -> EasyQuotationAdapter:
    """获取EasyQuotation适配器单例"""
    global _adapter_instance
    
    if _adapter_instance is None:
        _adapter_instance = EasyQuotationAdapter()
    
    return _adapter_instance


# ==================== 兼容层 ====================

def use(source: str = 'tencent') -> EasyQuotationAdapter:
    """
    兼容easyquotation.use()接口
    
    Args:
        source: 数据源（忽略，强制使用QMT）
    
    Returns:
        EasyQuotationAdapter: 适配器实例
    """
    logger.warning(
        f"⚠️ [EasyQuotation适配器] use('{source}') 调用被忽略，"
        f"强制使用QMT数据源"
    )
    return get_easyquotation_adapter()


# ==================== 测试入口 ====================

if __name__ == "__main__":
    # 测试适配器
    print("=" * 60)
    print("EasyQuotation适配器测试")
    print("=" * 60)
    
    # 创建适配器
    adapter = EasyQuotationAdapter()
    
    # 测试stocks接口
    print("\n测试stocks接口...")
    test_codes = ['000001', '600000', '600519']
    data = adapter.stocks(test_codes)
    
    print(f"获取到 {len(data)} 只股票数据:")
    for code, stock in data.items():
        print(f"  {code} ({stock.get('name', '')}): "
              f"价格{stock.get('now', 0):.2f}, "
              f"涨跌{stock.get('rise_percent', 0):.2f}%")
    
    # 获取统计信息
    stats = adapter.get_statistics()
    print(f"\n统计信息: 调用{stats['call_count']}次, "
          f"缓存命中{stats['cache_hit_count']}次, "
          f"QMT调用{stats['qmt_call_count']}次, "
          f"缓存命中率{stats['cache_hit_rate']*100:.1f}%")
    
    # 测试market_snapshot接口
    print("\n测试market_snapshot接口...")
    snapshot = adapter.market_snapshot()
    print(f"市场快照: {len(snapshot)} 条数据")
    
    print("\n✅ EasyQuotation适配器测试完成")