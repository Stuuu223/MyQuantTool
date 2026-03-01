# -*- coding: utf-8 -*-
"""
股票池构建器 - JSON遗产安全版

【CTO终极方案】：
QMT本地数据存在损坏文件，导致get_local_data触发C++ BSON崩溃。
由于Python无法捕获C++层面的崩溃，直接使用全息下载器的JSON遗产。

安全策略：
1. 读取全息下载器的JSON文件获取已成功下载的股票列表
2. 只保留深市股票（.SZ），沪市数据有损坏风险
3. 不调用任何get_local_data，避免BSON崩溃

Author: CTO & AI总监
Date: 2026-03-01
Version: 10.0.0 - JSON遗产安全版
"""
import os
import json
import logging
from typing import List

logger = logging.getLogger(__name__)


class UniverseBuilder:
    """
    股票池构建器 - JSON遗产安全版
    
    【铁律】：不调用get_local_data，只用JSON遗产！
    """
    
    def __init__(self, strategy: str = 'universe_build'):
        self.strategy = strategy
        self.logger = logging.getLogger(__name__)
        
    def get_daily_universe(self, date: str) -> List[str]:
        """
        JSON遗产粗筛 - 安全可靠
        
        从全息下载器的JSON文件中读取已下载的股票列表
        只保留深市股票，过滤掉有风险的沪市
        
        Args:
            date: 日期 YYYYMMDD
            
        Returns:
            候选股票列表
        """
        self.logger.info(f"⚡ [JSON遗产粗筛] 启动 ({date})...")
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 尝试全息下载器的JSON
        holo_path = os.path.join(base_dir, 'data', f'download_state_holographic_{date}.json')
        all_stocks = []
        
        if os.path.exists(holo_path):
            try:
                with open(holo_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    
                if 'completed' in state and state['completed']:
                    all_stocks = state['completed']
                    self.logger.info(f"📄 读取全息遗产: {len(all_stocks)} 只")
            except Exception as e:
                self.logger.error(f"读取全息JSON失败: {e}")
        
        if not all_stocks:
            # 尝试Tick下载器的JSON
            tick_path = os.path.join(base_dir, 'data', f'download_state_tick_{date}_{date}.json')
            if os.path.exists(tick_path):
                try:
                    with open(tick_path, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                    if 'completed' in state and state['completed']:
                        completed = state['completed']
                        all_stocks = list(completed.keys()) if isinstance(completed, dict) else completed
                        self.logger.info(f"📄 读取Tick遗产: {len(all_stocks)} 只")
                except Exception as e:
                    self.logger.error(f"读取Tick JSON失败: {e}")
        
        if not all_stocks:
            self.logger.error(f"❌ 找不到 {date} 的JSON遗产！请先运行下载器！")
            return []
        
        # ═══════════════════════════════════════════════════════════════
        # 过滤：只保留深市股票，剔除沪市、北交所、科创板
        # ═══════════════════════════════════════════════════════════════
        valid_stocks = []
        for stock in all_stocks:
            # 【安全第一】：剔除所有沪市股票(.SH)，数据有损坏风险
            if stock.endswith('.SH'):
                continue
            # 剔除北交所(8开头、4开头)和科创板(688开头)
            if stock.startswith(('8', '4', '688')):
                continue
            valid_stocks.append(stock)
        
        # 统计
        sh_count = len([s for s in all_stocks if s.endswith('.SH')])
        sz_count = len(valid_stocks)
        
        self.logger.info(f"🚫 剔除沪市: {sh_count} 只（数据风险）")
        self.logger.info(f"✅ 保留深市: {sz_count} 只")
        print(f"🚫 剔除沪市: {sh_count} 只（数据风险）")
        print(f"✅ 保留深市: {sz_count} 只")
        
        # 限制最大数量
        max_output = 100
        if len(valid_stocks) > max_output:
            self.logger.info(f"📏 限制输出: {len(valid_stocks)} → {max_output}")
            valid_stocks = valid_stocks[:max_output]
        
        return valid_stocks


# 便捷函数
def get_daily_universe(date: str) -> List[str]:
    """获取当日股票池 (便捷函数)"""
    builder = UniverseBuilder()
    return builder.get_daily_universe(date)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    universe = get_daily_universe('20260226')
    print(f"\n股票池: {len(universe)} 只")
    print(f"前10只: {universe[:10]}")
