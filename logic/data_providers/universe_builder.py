"""
股票池构建器 - CTO全息克隆版

【CTO铁令】：直接复用全息下载器的安全股票池！
原因：get_local_data会触发BSON崩溃
方案：读取download_state_holographic_*.json中的completed列表

Author: CTO & AI总监
Date: 2026-03-01
Version: 6.0.0 - 全息克隆版（复用下载器遗产）
"""
import os
import json
import logging
from typing import List

logger = logging.getLogger(__name__)


class UniverseBuilder:
    """
    股票池构建器 - CTO全息克隆版
    
    【核心策略】：直接读取全息下载器留下的JSON遗产
    """
    
    def __init__(self, strategy: str = 'universe_build'):
        self.strategy = strategy
        self.logger = logging.getLogger(__name__)
        
    def get_daily_universe(self, date: str) -> List[str]:
        """
        【CTO全息克隆】粗筛
        
        第一优先级：读取全息下载器的JSON缓存
        第二优先级：极简降级扫描
        """
        self.logger.info(f"⚡ [CTO全息克隆] 启动安全降级扫描 ({date})...")
        
        # =================================================================
        # 🛡️ 终极护盾：直接读取全息下载器留下的JSON遗产！
        # =================================================================
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, 'data', f'download_state_holographic_{date}.json')
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    
                if 'completed' in state and state['completed']:
                    holographic_pool = state['completed']
                    self.logger.info(f"🎉 发现全息下载器遗产！直接借库 {len(holographic_pool)} 只安全股票！")
                    print(f"🎉 [CTO全息克隆] 从JSON遗产借库: {len(holographic_pool)} 只安全股票")
                    
                    # 过滤掉北交所股票（8开头、4开头）
                    filtered_pool = [s for s in holographic_pool if not s.startswith(('8', '4'))]
                    self.logger.info(f"✅ 过滤北交所后: {len(filtered_pool)} 只")
                    
                    if len(filtered_pool) > 10:
                        return filtered_pool
            except Exception as e:
                self.logger.warning(f"读取全息缓存失败: {e}")
        
        # =================================================================
        # 🛡️ 备用方案：极简扫描
        # =================================================================
        self.logger.warning("未找到全息缓存，执行极简扫描...")
        
        try:
            from xtquant import xtdata
            all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        except Exception:
            return []
            
        if not all_stocks: 
            return []

        # 极简过滤：只排除北交所和科创板
        valid_stocks = []
        for stock in all_stocks:
            if stock.startswith(('8', '4', '688')): 
                continue
            valid_stocks.append(stock)
        
        # 取前200个
        final_pool = valid_stocks[:200]
        self.logger.info(f"✅ 极简扫描完成: {len(final_pool)} 只")
        return final_pool


# 便捷函数
def get_daily_universe(date: str) -> List[str]:
    """获取当日股票池 (便捷函数)"""
    builder = UniverseBuilder()
    return builder.get_daily_universe(date)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    universe = get_daily_universe('20260226')
    print(f"股票池: {len(universe)} 只")
    print(f"前10只: {universe[:10]}")
