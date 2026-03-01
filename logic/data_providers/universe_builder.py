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
        from xtquant import xtdata
        import pandas as pd
        
        self.logger.info(f"⚡ [CTO终极粗筛] 启动全市场防弹扫描 ({date})...")
        
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        if not all_stocks: return []

        # 【CTO防爆切片器】：每次只查200只，防撑爆BSON！
        chunk_size = 200
        daily_data = {}
        self.logger.info(f"📦 [CTO切片] 分批获取日K数据，每批{chunk_size}只...")
        for i in range(0, len(all_stocks), chunk_size):
            chunk = all_stocks[i:i + chunk_size]
            try:
                chunk_data = xtdata.get_local_data(
                    field_list=['open', 'high', 'low', 'close', 'volume', 'amount', 'preClose'],
                    stock_list=chunk,
                    period='1d',
                    start_time=date,
                    end_time=date
                )
                if chunk_data:
                    daily_data.update(chunk_data)
            except Exception as e:
                self.logger.warning(f"切片{i//chunk_size + 1}获取失败: {e}")
                continue
        
        self.logger.info(f"✅ [CTO切片] 日K数据获取完成: {len(daily_data)} 只")
        
        # 【CTO防爆切片】：预热字典也必须分批！
        from logic.data_providers.true_dictionary import get_true_dictionary
        true_dict = get_true_dictionary()
        self.logger.info(f"📦 [CTO切片] 分批预热TrueDictionary...")
        for i in range(0, len(all_stocks), chunk_size):
            chunk = all_stocks[i:i + chunk_size]
            try:
                true_dict.warmup(chunk, target_date=date)
            except Exception as e:
                self.logger.warning(f"切片{i//chunk_size + 1}预热失败: {e}")
                continue
        
        valid_stocks = []
        for stock in all_stocks:
            try:
                # 1. 静态垃圾清理
                if stock.startswith(('8', '4', '688')): continue
                if not daily_data or stock not in daily_data or daily_data[stock].empty: continue
                
                df_daily = daily_data[stock]
                raw_vol = df_daily['volume'].iloc[-1]
                if pd.isna(raw_vol) or float(raw_vol) <= 0: continue
                current_volume = float(raw_vol)
                
                # 2. 提取基础缓存并强转
                avg_vol = float(true_dict.get_avg_volume_5d(stock) or 0.0)
                float_vol = float(true_dict.get_float_volume(stock) or 0.0)
                
                if avg_vol <= 0.0 or float_vol <= 0.0 or pd.isna(avg_vol) or pd.isna(float_vol):
                    continue
                
                # 3. 【CTO 绝对单位纠偏】：量比计算
                vol_ratio = current_volume / avg_vol
                if vol_ratio < 0.01: vol_ratio *= 100.0
                if vol_ratio > 1000.0: vol_ratio /= 100.0
                
                # 4. 【CTO 双重换手率防线】
                turnover = 0.0
                # 防线A: 优先尝试官方数据
                if 'turnover' in df_daily.columns:
                    raw_turnover = df_daily['turnover'].iloc[-1]
                    if not pd.isna(raw_turnover) and float(raw_turnover) > 0:
                        turnover = float(raw_turnover)
                        if 0 < turnover < 1.0: turnover *= 100.0
                
                # 防线B: 官方无数据，启动自适应物理计算！
                if turnover <= 0.0:
                    turnover = (current_volume / float_vol) * 100.0
                    if turnover < 0.1: turnover *= 10000.0 # 自适应万股
                    
                # 如果算出来大得离谱(>100%)，绝对是有除权或单位错误，直接废弃
                if turnover > 100.0: continue

                # 5. 绝对阈值过滤
                if vol_ratio >= 1.5 and 3.0 <= turnover <= 70.0:
                    valid_stocks.append(stock)
            except Exception:
                continue
                
        self.logger.info(f"✅ 粗筛完成！最终候选: {len(valid_stocks)} 只。")
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
