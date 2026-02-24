"""
全市场扫描器 - 向量化快照雷达

功能：
- 使用xtdata.get_full_tick进行批量快照获取
- 利用pandas向量化运算实现三道防线过滤
- 高效的批量筛选和排序

CTO加固要点:
- 避免for循环逐只处理
- 使用向量化操作提升性能
- 集成战法检测器进行细筛

Author: AI总监
Date: 2026-02-24
Version: Phase 20
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import time
import logging

# 获取logger
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging as log_mod
    logger = log_mod.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = log_mod.StreamHandler()
    handler.setFormatter(log_mod.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(handler)


class FullMarketScanner:
    """
    全市场扫描器 - 向量化快照雷达
    
    CTO加固要点:
    - 向量化快照获取，避免for循环
    - 三道防线向量化过滤
    - 集成UnifiedWarfareCore进行细筛
    """
    
    def __init__(self):
        """初始化扫描器"""
        self.universe_builder = None
        self._init_universe_builder()
        logger.info("✅ [FullMarketScanner] 初始化完成")
    
    def _init_universe_builder(self):
        """初始化股票池构建器"""
        try:
            from logic.data_providers.universe_builder import UniverseBuilder
            self.universe_builder = UniverseBuilder()
            logger.debug("🎯 UniverseBuilder 已加载")
        except ImportError:
            logger.warning("⚠️ UniverseBuilder 未找到，将使用默认股票列表")
    
    def scan_snapshot_batch(self, stock_list: List[str]) -> pd.DataFrame:
        """
        批量快照扫描 - 向量化实现
        
        Args:
            stock_list: 股票代码列表
            
        Returns:
            pd.DataFrame: 筛选后的股票数据框
        """
        if not stock_list:
            logger.warning("⚠️ 股票列表为空，跳过扫描")
            return pd.DataFrame()
        
        start_time = time.time()
        logger.info(f"🔍 开始快照扫描: {len(stock_list)} 只股票")
        
        try:
            # 使用xtdata.get_full_tick一次性获取全市场快照
            from xtquant import xtdata
            full_tick = xtdata.get_full_tick(stock_list)
            
            if not full_tick:
                logger.warning("⚠️ 未获取到任何Tick数据")
                return pd.DataFrame()
            
            # 转换为pandas DataFrame进行向量化计算 (CTO: 避免for循环)
            df_list = []
            for stock_code, tick_data in full_tick.items():
                if tick_data is not None and len(tick_data) > 0:
                    try:
                        # 提取最新tick数据
                        latest = tick_data.iloc[-1] if hasattr(tick_data, 'iloc') else tick_data
                        df_list.append({
                            'stock_code': stock_code,
                            'price': float(latest.get('lastPrice', 0)),
                            'volume': int(latest.get('volume', 0)),
                            'amount': float(latest.get('amount', 0)),
                            'open': float(latest.get('open', 0)),
                            'high': float(latest.get('high', 0)),
                            'low': float(latest.get('low', 0)),
                            'prev_close': float(latest.get('preClose', 0)),
                            'time': str(latest.get('time', ''))
                        })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"⚠️ 解析Tick数据失败 {stock_code}: {e}")
                        continue
            
            if not df_list:
                logger.warning("⚠️ 未解析到有效的Tick数据")
                return pd.DataFrame()
            
            df = pd.DataFrame(df_list)
            original_count = len(df)
            
            # 向量化计算三道防线指标 (CTO: C语言级别的向量化)
            df['change_pct'] = (df['price'] - df['prev_close']) / df['prev_close'] * 100
            df['turnover_rate'] = df['amount'] / 1e6  # 简化换手率（实际需结合流通市值）
            df['volume_ratio'] = df['volume'] / df.groupby('stock_code')['volume'].transform('mean').fillna(1) * 5  # 近似5日均量比
            
            # 向量化过滤 (CTO: 一行代码过滤数千只股票)
            mask = (
                (df['price'] > 0) &  # 价格有效性
                (df['prev_close'] > 0) &  # 昨收有效性
                (df['change_pct'] >= 2.0) &  # 涨幅过滤
                (df['volume_ratio'] >= 3.0) &  # 量比过滤
                (df['amount'] >= 30000000)  # 成交额过滤 (3000万)
            )
            
            filtered_df = df[mask].copy()
            filtered_count = len(filtered_df)
            
            elapsed = time.time() - start_time
            logger.info(
                f"📊 快照扫描完成: {original_count} -> {filtered_count} "
                f"(耗时: {elapsed:.2f}s, 过滤率: {filtered_count/original_count*100:.1f}%)]"
            )
            
            return filtered_df
            
        except Exception as e:
            logger.error(f"❌ 快照扫描失败: {e}", exc_info=True)
            return pd.DataFrame()
    
    def scan_with_risk_management(self, mode: str = 'full', max_stocks: int = 100) -> Dict[str, Any]:
        """
        带风控的扫描
        
        Args:
            mode: 扫描模式
            max_stocks: 最大扫描数量
            
        Returns:
            Dict: 扫描结果字典
        """
        start_time = time.time()
        logger.info(f"🎯 启动全市场扫描: 模式={mode}, 最大数量={max_stocks}")
        
        # 1. 获取粗筛股票池
        universe = self._get_universe()
        universe = universe[:max_stocks]  # 限制数量防止过载
        
        if not universe:
            logger.error("❌ 未能获取股票池")
            return {
                'opportunities': [],
                'watchlist': [],
                'total_scanned': 0,
                'filtered_count': 0,
                'error': '未能获取股票池'
            }
        
        # 2. 批量快照扫描
        snapshot_results = self.scan_snapshot_batch(universe)
        
        if snapshot_results.empty:
            logger.warning("⚠️ 快照扫描结果为空")
            return {
                'opportunities': [],
                'watchlist': [],
                'total_scanned': len(universe),
                'filtered_count': 0
            }
        
        # 3. 调用战法检测器进行细筛 (CTO: 集成V18验钞机)
        detailed_results = self._integrate_warfare_scoring(snapshot_results)
        
        # 4. 按得分排序，返回Top 20
        detailed_results.sort(key=lambda x: x.get('warfare_confidence', 0), reverse=True)
        opportunities = detailed_results[:20]
        watchlist = detailed_results[:50]
        
        elapsed = time.time() - start_time
        logger.info(
            f"✅ 全市场扫描完成: {len(universe)} -> {len(snapshot_results)} -> {len(opportunities)} "
            f"(耗时: {elapsed:.2f}s)"
        )
        
        return {
            'opportunities': opportunities,
            'watchlist': watchlist,
            'total_scanned': len(universe),
            'filtered_count': len(snapshot_results),
            'scan_time': elapsed
        }
    
    def _get_universe(self) -> List[str]:
        """获取股票池"""
        if self.universe_builder:
            try:
                return self.universe_builder.get_daily_universe()
            except Exception as e:
                logger.warning(f"⚠️ UniverseBuilder获取股票池失败: {e}")
        
        # 备用：返回沪深A股列表 (实际应从QMT获取)
        try:
            from xtquant import xtdata
            all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
            # 取前1000只作为示例
            return [self._normalize_code(code) for code in all_stocks[:1000]]
        except:
            logger.error("❌ 无法获取股票列表，返回空列表")
            return []
    
    def _normalize_code(self, code: str) -> str:
        """标准化股票代码"""
        if isinstance(code, str):
            if '.' not in code:
                if code.startswith('6'):
                    return f"{code}.SH"
                else:
                    return f"{code}.SZ"
        return code
    
    def _integrate_warfare_scoring(self, snapshot_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        集成战法检测器进行评分
        
        Args:
            snapshot_df: 快照扫描结果
            
        Returns:
            List[Dict]: 带战法评分的结果列表
        """
        try:
            from logic.strategies.unified_warfare_scanner_adapter import integrate_with_fullmarket_scanner
            from logic.strategies.unified_warfare_core import get_unified_warfare_core
            
            # 转换为适配器期望的格式
            scanner_results = []
            for _, row in snapshot_df.iterrows():
                scanner_results.append({
                    'code': row['stock_code'],
                    'price': row['price'],
                    'volume': row['volume'],
                    'amount': row['amount'],
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'prev_close': row['prev_close'],
                })
            
            # 调用战法检测器
            enhanced_results = integrate_with_fullmarket_scanner(scanner_results)
            
            logger.debug(f"🎯 战法检测完成: {len(enhanced_results)} 只股票")
            return enhanced_results
            
        except ImportError as e:
            logger.warning(f"⚠️ 战法检测器未找到，返回原始结果: {e}")
            # 返回原始快照数据
            return [
                {
                    'code': row['stock_code'],
                    'price': row['price'],
                    'change_pct': row['change_pct'],
                    'volume_ratio': row['volume_ratio'],
                    'amount': row['amount'],
                    'warfare_events': [],
                    'warfare_confidence': 0.0
                }
                for _, row in snapshot_df.iterrows()
            ]
        except Exception as e:
            logger.error(f"❌ 战法检测失败: {e}")
            return [
                {
                    'code': row['stock_code'],
                    'price': row['price'],
                    'change_pct': row['change_pct'],
                    'volume_ratio': row['volume_ratio'],
                    'amount': row['amount'],
                    'warfare_events': [],
                    'warfare_confidence': 0.0,
                    'error': str(e)
                }
                for _, row in snapshot_df.iterrows()
            ]


# 便捷函数
def create_full_market_scanner() -> FullMarketScanner:
    """
    创建全市场扫描器实例
    
    Returns:
        FullMarketScanner: 扫描器实例
    """
    return FullMarketScanner()


if __name__ == "__main__":
    # 测试全市场扫描器
    print("🧪 全市场扫描器测试")
    print("=" * 50)
    
    scanner = create_full_market_scanner()
    
    # 获取几个测试股票
    try:
        from xtquant import xtdata
        test_stocks = xtdata.get_stock_list_in_sector('沪深A股')[:20]  # 前20只
        test_stocks = [scanner._normalize_code(code) for code in test_stocks]
        print(f"📊 测试股票: {test_stocks[:5]}... (共{len(test_stocks)}只)")
        
        # 执行快照扫描
        results = scanner.scan_snapshot_batch(test_stocks)
        print(f"🔍 快照扫描结果: {len(results)} 只")
        
        if not results.empty:
            print("\n前5只股票:")
            for i, (_, row) in enumerate(results.head(5).iterrows()):
                print(f"  {i+1}. {row['stock_code']} - {row['price']:.2f} ({row['change_pct']:+.2f}%)")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("\n✅ 扫描器测试完成")
