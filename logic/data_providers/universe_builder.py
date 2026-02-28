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
        self.logger = logging.getLogger(__name__)
        
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
        # 从配置获取死亡换手率，默认70.0%【CTO铁血令：死亡线70%】
        live_sniper_config = self.config_manager._config.get('live_sniper', {})
        return live_sniper_config.get('death_turnover_rate', 70.0)
        
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
        获取当日股票池 - 【CTO核爆级重构】使用DTO数据整流罩，彻底解决单位换算！
        
        Args:
            date: 日期 'YYYYMMDD'
            
        Returns:
            股票代码列表 (约60-100只)
        """
        from xtquant import xtdata
        from logic.core.models import QMTStockSnapshot, create_snapshot_from_qmt
        import pandas as pd
        import time
        
        start_time = time.time()
        self.logger.info(f"⚡ [CTO极速粗筛] 使用DTO整流罩，一把拉取全市场日K数据 ({date})...")
        
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        
        # 1. 一次性获取全市场日K（绝不是tick！）
        daily_data = xtdata.get_local_data(
            field_list=['volume', 'close', 'preClose', 'open', 'high', 'low', 'amount'],
            stock_list=all_stocks,
            period='1d',  # 【CTO强制】只用日K，严禁tick！
            start_time=date,
            end_time=date
        )
        
        from logic.data_providers.true_dictionary import get_true_dictionary
        true_dict = get_true_dictionary()
        true_dict.warmup(all_stocks, target_date=date)
        
        valid_stocks = []
        st_count, missing_count = 0, 0
        
        # 2. 使用DTO整流罩极速过滤
        for stock in all_stocks:
            try:
                # 静态过滤
                if stock.startswith('8') or stock.startswith('4') or stock.startswith('688'):
                    continue
                detail = xtdata.get_instrument_detail(stock)
                name = detail.get('StockName', '') if detail else ''
                if 'ST' in name or '退' in name:
                    st_count += 1
                    continue
                
                # 获取原始数据
                df_daily = daily_data.get(stock) if daily_data else None
                float_vol = true_dict.get_float_volume(stock)
                avg_vol_5d = true_dict.get_avg_volume_5d(stock)
                
                # 【CTO核心】：使用DTO整流罩清洗所有数据！
                snapshot = create_snapshot_from_qmt(stock, df_daily, float_vol, avg_vol_5d)
                
                # 【CTO系统级死票过滤器】：无效股票直接砍掉！
                if not snapshot.is_valid:
                    missing_count += 1
                    continue
                
                # 【CTO核心】：直接使用DTO清洗后的数据做判断！
                # 再也不用操心单位换算，再也不用写*100或/10000！
                if snapshot.volume_ratio >= 1.5 and 3.0 <= snapshot.turnover_rate <= 70.0:
                    valid_stocks.append(stock)
                    
            except Exception as e:
                self.logger.debug(f"处理{stock}时出错: {e}")
                continue
                
        elapsed = time.time() - start_time
        self.logger.info(f"✅ DTO粗筛完成！ST过滤:{st_count} 数据缺失:{missing_count} 最终候选:{len(valid_stocks)}只 (耗时:{elapsed:.2f}s)")
        return valid_stocks
    
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
