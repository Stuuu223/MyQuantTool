"""
股票池构建器 - CTO快照防弹衣版

【CTO铁令】：抛弃get_local_data历史K线查询！
原因：get_local_data会触发BSON C++崩溃
方案：使用get_full_tick内存快照切片，500只一批防爆！

Author: CTO
Date: 2026-03-01
Version: 5.0.0 - 快照防弹衣版
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging
from dotenv import load_dotenv

from logic.core.path_resolver import PathResolver
from logic.core.config_manager import get_config_manager

# 加载.env文件
load_dotenv()

logger = logging.getLogger(__name__)


class UniverseBuilder:
    """
    股票池构建器 - CTO快照防弹衣版
    
    【CTO核心防御】：放弃get_local_data，改用get_full_tick获取内存快照！
    """
    
    def __init__(self, strategy: str = 'universe_build'):
        """初始化"""
        self.strategy = strategy
        self.config_manager = get_config_manager()
        self.logger = logging.getLogger(__name__)
        
    @property
    def MIN_AMOUNT(self) -> int:
        """最小金额阈值"""
        return 30000000  # 3000万

    @property
    def MIN_VOLUME_MULTIPLIER(self) -> float:
        """量比阈值 - 从配置获取"""
        live_sniper_config = self.config_manager._config.get('live_sniper', {})
        return live_sniper_config.get('min_volume_multiplier', 1.5)

    @property
    def MIN_ACTIVE_TURNOVER_RATE(self) -> float:
        """大哥起步线 - 最小换手率"""
        live_sniper_config = self.config_manager._config.get('live_sniper', {})
        return live_sniper_config.get('min_active_turnover_rate', 3.0)

    @property
    def DEATH_TURNOVER_RATE(self) -> float:
        """死亡换手率"""
        live_sniper_config = self.config_manager._config.get('live_sniper', {})
        return live_sniper_config.get('death_turnover_rate', 70.0)
        
    def get_daily_universe(self, date: str) -> List[str]:
        """
        【CTO快照防弹衣版】粗筛
        
        使用get_full_tick快照切片，彻底避开get_local_data的BSON崩溃！
        """
        from xtquant import xtdata
        
        self.logger.info(f"⚡ [CTO快照防弹衣] 启动全市场快照切片扫描 ({date})...")
        
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        if not all_stocks: 
            return []

        from logic.data_providers.true_dictionary import get_true_dictionary
        true_dict = get_true_dictionary()
        
        # 【CTO核心防御】：放弃get_local_data，改用get_full_tick获取内存快照！
        # 且必须500只一批，防止BSON溢出！
        tick_dict = {}
        chunk_size = 500
        
        for i in range(0, len(all_stocks), chunk_size):
            chunk = all_stocks[i:i + chunk_size]
            try:
                chunk_snap = xtdata.get_full_tick(chunk)
                if chunk_snap:
                    tick_dict.update(chunk_snap)
                    self.logger.info(f"  📦 快照切片 {i//chunk_size + 1}: 获取{len(chunk_snap)}只股票快照")
            except Exception as e:
                self.logger.error(f"快照切片拉取失败，跳过该切片: {e}")
                continue
        
        self.logger.info(f"📊 快照获取完成: {len(tick_dict)}/{len(all_stocks)} 只股票")
        
        valid_stocks = []
        success_count = 0
        fail_count = 0
        
        for stock in all_stocks:
            try:
                # 1. 静态垃圾清理
                if stock.startswith(('8', '4', '688')): 
                    continue
                    
                if stock not in tick_dict: 
                    fail_count += 1
                    continue
                
                tick_snap = tick_dict[stock]
                
                # 从快照提取当前成交量
                raw_vol = tick_snap.get('volume', 0)
                if raw_vol <= 0: 
                    continue
                current_volume = float(raw_vol)
                
                # 2. 取流通盘和均量
                avg_vol = float(true_dict.get_avg_volume_5d(stock) or 0.0)
                float_vol = float(true_dict.get_float_volume(stock) or 0.0)
                
                if avg_vol <= 0.0 or float_vol <= 0.0 or pd.isna(avg_vol) or pd.isna(float_vol):
                    continue
                
                # 3. 量比计算
                vol_ratio = current_volume / avg_vol
                if vol_ratio < 0.01: vol_ratio *= 100.0
                if vol_ratio > 1000.0: vol_ratio /= 100.0
                
                # 4. 换手率计算
                turnover = (current_volume / float_vol) * 100.0
                if turnover < 0.1: turnover *= 10000.0
                if turnover > 100.0: continue

                # 5. 绝对阈值过滤
                if vol_ratio >= 1.5 and 3.0 <= turnover <= 70.0:
                    valid_stocks.append(stock)
                    success_count += 1
                    
            except Exception:
                fail_count += 1
                continue
        
        self.logger.info(f"✅ 快照防弹衣粗筛完成！成功:{success_count}, 失败:{fail_count}, 最终候选:{len(valid_stocks)} 只。")
        return valid_stocks


# 便捷函数
def get_daily_universe(date: str) -> List[str]:
    """获取当日股票池 (便捷函数)"""
    builder = UniverseBuilder()
    return builder.get_daily_universe(date)


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    try:
        universe = get_daily_universe('20260226')
        print(f"股票池: {len(universe)} 只")
        print(f"前10只: {universe[:10]}")
    except Exception as e:
        print(f"错误: {e}")