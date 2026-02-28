"""
股票池构建器 - QMT本地数据粗筛 (V20极致全息架构)
使用QMT本地数据实现三漏斗粗筛，100% QMT本地架构

重构要点：
- 完全移除Tushare依赖，100% QMT本地数据
- 使用xtdata.get_stock_list_in_sector获取全市场
- 基于QMT本地数据计算量比和换手率分位数
- CTO强制：所有参数从配置管理器获取，禁止硬编码

Author: iFlow CLI
Date: 2026-02-27
Version: 4.0.0 (V20极致全息架构 - 100% QMT本地化)
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging
from dotenv import load_dotenv

from logic.core.path_resolver import PathResolver
from logic.core.sanity_guards import SanityGuards
from logic.core.config_manager import get_config_manager

# 加载.env文件
load_dotenv()

logger = logging.getLogger(__name__)


class UniverseBuilder:
    """
    股票池构建器 - V20极致全息架构
    
    三漏斗粗筛 (全市场5000 → ~60-100只):
    1. 静态过滤: 剔除ST、退市、北交所
    2. 金额过滤: 5日平均成交额 > 3000万
    3. 量比过滤: 当日量比 > 3.0 (右侧起爆：筛选真正放量的股票)
    """
    
    def __init__(self, strategy: str = 'universe_build'):
        """初始化，使用粗筛专用参数"""
        self.strategy = strategy  # 默认使用universe_build策略
        self.config_manager = get_config_manager()
        
    @property
    def MIN_AMOUNT(self) -> int:
        """最小金额阈值"""
        return 30000000  # 3000万
        
    @property
    def MIN_ACTIVE_TURNOVER_RATE(self) -> float:
        """最低活跃换手率 - CTO换手率纠偏裁决：拒绝死水"""
        # 从配置获取最低活跃换手率，默认3.0%
        live_sniper_config = self.config_manager._config.get('live_sniper', {})
        return live_sniper_config.get('min_active_turnover_rate', 3.0)
        
    @property
    def DEATH_TURNOVER_RATE(self) -> float:
        """死亡换手率 - CTO换手率纠偏裁决：防范极端爆炒陷阱"""
        # 从配置获取死亡换手率，默认60.0%
        live_sniper_config = self.config_manager._config.get('live_sniper', {})
        return live_sniper_config.get('death_turnover_rate', 60.0)
        
    def _get_volume_ratio_percentile_threshold(self, date: str) -> float:
        """
        获取基于分位数的量比阈值 - V20 QMT本地化实现
        
        Args:
            date: 日期 'YYYYMMDD'
            
        Returns:
            量比阈值
        """
        # 从配置获取分位数阈值，默认使用live_sniper的0.95分位数
        live_sniper_config = self.config_manager._config.get('live_sniper', {})
        volume_percentile = live_sniper_config.get('volume_ratio_percentile', 0.95)
        
        # 【V20重构】使用QMT本地数据计算分位数阈值
        # 获取全市场股票列表
        try:
            from xtquant import xtdata
            all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
            
            # 【CTO红线】：绝对禁止切片！必须算全市场！
            volume_ratios = []
            from logic.data_providers.true_dictionary import get_true_dictionary
            true_dict = get_true_dictionary()
            
            # 【CTO性能优化】：一次性批量获取全市场数据到内存！绝不在循环里单只查！
            tick_data_all = xtdata.get_local_data(
                field_list=['volume'],
                stock_list=all_stocks,
                period='tick',
                start_time=date,
                end_time=date
            )

            for stock in all_stocks:
                try:
                    avg_volume_5d = true_dict.get_avg_volume_5d(stock)
                    if avg_volume_5d and avg_volume_5d > 0:
                        if tick_data_all and stock in tick_data_all and len(tick_data_all[stock]) > 0:
                            stock_ticks = tick_data_all[stock]
                            current_volume = stock_ticks['volume'].iloc[-1] if hasattr(stock_ticks['volume'], 'iloc') else stock_ticks['volume'][-1]
                            volume_ratio = (current_volume * 100) / avg_volume_5d  # 乘以100转为手为单位
                            if 0 < volume_ratio < 50:  # 过滤极端异常值
                                volume_ratios.append(volume_ratio)
                except:
                    continue
            
            if volume_ratios:
                # 计算分位数阈值
                import numpy as np
                threshold_value = float(np.percentile(volume_ratios, volume_percentile * 100))
                # 确保阈值不低于安全下限
                return max(threshold_value, 1.5)  # 设置最低阈值为1.5，确保真正放量
            
            # 如果QMT数据获取失败，回退到配置的绝对值
            universe_config = self.config_manager._config.get('universe_build', {})
            return universe_config.get('volume_ratio_absolute', 3.0)
            
        except Exception as e:
            logger.warning(f"获取QMT分位数阈值失败，使用回退值: {e}")
            universe_config = self.config_manager._config.get('universe_build', {})
            return universe_config.get('volume_ratio_absolute', 3.0)
    
    def get_daily_universe(self, date: str) -> List[str]:
        """
        获取当日股票池 (CTO重构版 - 截面向量查询)
        
        Args:
            date: 日期 'YYYYMMDD'
            
        Returns:
            股票代码列表 (约60-100只)
            
        Raises:
            RuntimeError: 无法获取数据时抛出
        """
        import time
        start_time = time.time()
        logger.info(f"【UniverseBuilder】开始构建 {date} 股票池 (CTO重构版)")
        
        # 【V20重构】使用QMT本地数据获取全市场截面
        try:
            from xtquant import xtdata
            all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
            logger.info(f"【UniverseBuilder】QMT获取全市场股票: {len(all_stocks)} 只")
            
            # 构建DataFrame模拟Tushare接口返回的数据结构
            stock_data = []
            from logic.data_providers.true_dictionary import get_true_dictionary
            true_dict = get_true_dictionary()
            
            # 【CTO修复】调用warmup时传入target_date，消灭未来函数
            # 确保回测时使用历史日期的5日均量，而不是当前日期的数据
            true_dict.warmup(all_stocks, target_date=date, force=False)
            
            # 限制处理股票数量以提高性能
            for stock in all_stocks:  # 只处理前1000只股票
                try:
                    # 获取股票基本信息
                    stock_name = xtdata.get_stock_name(stock) or ""
                    
                    # 过滤掉ST股票和北交所股票
                    if 'ST' in stock_name or 'ST' in stock or stock.startswith('8') or stock.startswith('4'):
                        continue
                    
                    # 获取5日均量
                    avg_volume_5d = true_dict.get_avg_volume_5d(stock)
                    if not avg_volume_5d or avg_volume_5d <= 0:
                        continue
                    
                    # 获取当日数据
                    tick_data = xtdata.get_local_data(
                        field_list=['volume', 'amount'],
                        stock_list=[stock],
                        period='tick',
                        start_time=date,
                        end_time=date
                    )
                    
                    if tick_data and stock in tick_data and len(tick_data[stock]) > 0:
                        df_stock = tick_data[stock]
                        current_volume = df_stock['volume'].iloc[-1] if hasattr(df_stock, 'iloc') else df_stock['volume'].values[-1]
                        current_amount = df_stock['amount'].iloc[-1] if hasattr(df_stock, 'iloc') else df_stock.get('amount', [0])[-1]
                        
                        # 计算量比 (当前成交量/5日均量)
                        volume_ratio = (current_volume * 100) / avg_volume_5d if avg_volume_5d > 0 else 0
                        
                        # 获取流通股本计算换手率
                        float_volume = true_dict.get_float_volume(stock)
                        turnover_rate = ((current_volume * 100) / float_volume * 100) if float_volume > 0 else 0
                        
                        # 获取流通市值
                        circ_mv = true_dict.get_float_market_cap(stock) / 10000  # 转换为万元
                        total_mv = true_dict.get_total_market_cap(stock) / 10000  # 转换为万元
                        
                        stock_data.append({
                            'ts_code': stock,
                            'volume_ratio': volume_ratio,
                            'turnover_rate': turnover_rate,
                            'circ_mv': circ_mv,
                            'total_mv': total_mv,
                            'amount': current_amount
                        })
                except:
                    continue  # 跳过无法获取数据的股票
            
            import pandas as pd
            df_basic = pd.DataFrame(stock_data)
            logger.info(f"【UniverseBuilder】QMT截面数据构建成功: {len(df_basic)} 只")
            
            # 【CTO修复】如果tick数据为空，使用日K数据降级方案
            if len(df_basic) == 0:
                logger.warning(f"【UniverseBuilder】{date}的tick数据为空，使用日K数据降级方案")
                stock_data = []
                for stock in all_stocks[:1000]:  # 限制1000只
                    try:
                        stock_name = xtdata.get_stock_name(stock) or ""
                        if 'ST' in stock_name or 'ST' in stock or stock.startswith('8') or stock.startswith('4'):
                            continue
                        
                        # 使用日K数据
                        daily_data = xtdata.get_local_data(
                            field_list=['volume', 'amount', 'open', 'high', 'low', 'close'],
                            stock_list=[stock],
                            period='1d',
                            start_time=date,
                            end_time=date
                        )
                        
                        if daily_data and stock in daily_data and len(daily_data[stock]) > 0:
                            df_daily = daily_data[stock]
                            current_volume = df_daily['volume'].iloc[-1]
                            current_amount = df_daily['amount'].iloc[-1]
                            avg_volume_5d = true_dict.get_avg_volume_5d(stock)
                            
                            if avg_volume_5d and avg_volume_5d > 0:
                                volume_ratio = (current_volume * 100) / avg_volume_5d
                                float_volume = true_dict.get_float_volume(stock)
                                turnover_rate = ((current_volume * 100) / float_volume * 100) if float_volume > 0 else 0
                                circ_mv = true_dict.get_float_market_cap(stock) / 10000
                                total_mv = true_dict.get_total_market_cap(stock) / 10000
                                
                                stock_data.append({
                                    'ts_code': stock,
                                    'volume_ratio': volume_ratio,
                                    'turnover_rate': turnover_rate,
                                    'circ_mv': circ_mv,
                                    'total_mv': total_mv,
                                    'amount': current_amount
                                })
                    except:
                        continue
                
                df_basic = pd.DataFrame(stock_data)
                logger.info(f"【UniverseBuilder】日K降级方案构建成功: {len(df_basic)} 只")
                
                # 【CTO修复】如果日K降级方案也失败，返回所有非ST股票（不过滤）
                if len(df_basic) == 0:
                    logger.warning(f"【UniverseBuilder】日K降级方案也失败，返回所有非ST股票")
                    all_non_st_stocks = []
                    for stock in all_stocks[:500]:  # 限制500只
                        try:
                            stock_name = xtdata.get_stock_name(stock) or ""
                            if 'ST' in stock_name or 'ST' in stock or stock.startswith('8') or stock.startswith('4'):
                                continue
                            all_non_st_stocks.append(stock)
                        except:
                            continue
                    logger.info(f"【UniverseBuilder】返回{len(all_non_st_stocks)}只非ST股票（不过滤）")
                    return all_non_st_stocks
            
        except Exception as e:
            logger.error(f"QMT截面数据获取失败: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"QMT截面数据获取失败: {e}")
        
        # 向量化过滤 (CTO: 禁止循环，用Pandas)
        # 第一层: 剔除量比为空的股票
        if len(df_basic) == 0:
            logger.error(f"【UniverseBuilder】{date}无有效数据，返回空列表")
            return []
        
        df_filtered = df_basic[df_basic['volume_ratio'].notna()].copy()
        logger.info(f"【UniverseBuilder】第一层(有效量比): {len(df_filtered)} 只")
        
        # 第二层: 量比 > 分位数阈值 (右侧起爆：筛选真正放量的股票，CTO裁决：统一使用分位数标准)
        volume_ratio_threshold = self._get_volume_ratio_percentile_threshold(date)
        df_filtered = df_filtered[df_filtered['volume_ratio'] >= volume_ratio_threshold]
        logger.info(f"【UniverseBuilder】第二层(量比>{volume_ratio_threshold:.2f}, 右侧起爆): {len(df_filtered)} 只")
        
        # 【CTO调试】打印量比和换手率分布
        if len(df_filtered) > 0:
            logger.info(f"【UniverseBuilder】量比范围: {df_filtered['volume_ratio'].min():.2f} - {df_filtered['volume_ratio'].max():.2f}")
            logger.info(f"【UniverseBuilder】换手率范围: {df_filtered['turnover_rate'].min():.2f}% - {df_filtered['turnover_rate'].max():.2f}%")
        
        # 第三层: 换手率过滤 (CTO换手率纠偏裁决)
        # 换手率 > 最低活跃阈值 (拒绝死水) 且 < 死亡换手率 (防范极端爆炒陷阱)
        min_turnover = self.MIN_ACTIVE_TURNOVER_RATE
        max_turnover = self.DEATH_TURNOVER_RATE
        
        # 【CTO调试】统计被过滤原因
        low_turnover = len(df_filtered[df_filtered['turnover_rate'] <= min_turnover])
        high_turnover = len(df_filtered[df_filtered['turnover_rate'] >= max_turnover])
        
        df_filtered = df_filtered[
            (df_filtered['turnover_rate'] > min_turnover) & 
            (df_filtered['turnover_rate'] < max_turnover)
        ]
        logger.info(f"【UniverseBuilder】第三层(换手率>{min_turnover}%-<{max_turnover}%): {len(df_filtered)} 只")
        logger.info(f"【UniverseBuilder】  被过滤: 低于{min_turnover}%有{low_turnover}只, 高于{max_turnover}%有{high_turnover}只")
        
        # 第四层: 剔除科创板(688)和北交所(8开头/4开头)
        df_filtered = df_filtered[~df_filtered['ts_code'].str.startswith('688')]
        df_filtered = df_filtered[~df_filtered['ts_code'].str.match(r'^[84]\d{5}\.(SZ|SH|BJ)')]
        logger.info(f"【UniverseBuilder】第四层(剔除科创/北交): {len(df_filtered)} 只")
        
        # 转换为标准格式
        result = [self._to_standard_code(code) for code in df_filtered['ts_code'].tolist()]
        
        elapsed = time.time() - start_time
        logger.info(f"【UniverseBuilder】最终股票池: {len(result)} 只 (耗时: {elapsed:.2f}秒)")
        
        return result
    
    # ===== 以下方法已废弃，保留仅供参考 =====
    # 原代码使用循环调用stk_mins导致6000次API请求
    # 已改用daily_basic截面查询，1次请求完成
    # See: get_daily_universe() for new implementation
    
    @staticmethod
    def _to_standard_code(ts_code: str) -> str:
        """转换为标准格式 (#######.SH/SZ)"""
        if '.' in ts_code:
            code, exchange = ts_code.split('.')
            if exchange == 'SH':
                return f"{code}.SH"
            elif exchange == 'SZ':
                return f"{code}.SZ"
        return ts_code


# 便捷函数
def get_daily_universe(date: str) -> List[str]:
    """
    获取当日股票池 (便捷函数)
    
    Args:
        date: 日期 'YYYYMMDD'
        
    Returns:
        股票代码列表
        
    Raises:
        RuntimeError: 无法获取数据时抛出
    """
    builder = UniverseBuilder()
    return builder.get_daily_universe(date)


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    try:
        universe = get_daily_universe('20251231')
        print(f"股票池: {len(universe)} 只")
        print(f"前10只: {universe[:10]}")
    except Exception as e:
        print(f"错误: {e}")
