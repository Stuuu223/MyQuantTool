"""
板块情绪计算器 - V20物理势能重构版 (剿灭散户基因)

【CTO重构宣言】
删除所有散户逻辑: green_stocks/red_board/change_pct等红绿盘计算
植入微观势能判定: volume_ratio > 3 且 turnover_rate_per_min > 0.2 → kinetic_leaders

功能：
- 构建股票到板块的映射索引
- 计算板块动能领袖(kinetic_energy) - 基于量能微观势能
- 计算板块势能密度(potential_energy) - kinetic_leaders占比

Author: AI总监 (CTO规划)
Date: 2026-02-27
Version: V20物理势能重构
"""
import pandas as pd
from typing import Dict, List, Tuple, Any
from datetime import datetime
import time
import logging

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


class SectorEmotionCalculator:
    """
    板块情绪计算器 - V20物理势能重构版
    
    【CTO重构链路 - 剿灭散户基因】
    1. 全市场拉取: 拿到N只股票的volume_ratio + turnover_rate_per_min
    2. 瞬间归位: 通过stock_to_sectors映射到各板块篮子 (向量化explode)
    3. 计算Kinetic: volume_ratio>3 且 turnover_rate_per_min>0.2 的票数 (微观势能)
    4. 计算Potential: kinetic_leaders / total_stocks (势能密度)
    
    【物理术语映射】
    - kinetic_energy: 动能领袖数 (原leaders/涨停先锋)
    - potential_energy: 势能密度 (原breadth/红盘比例)
    - sector_temperature: 板块温度 (kinetic_energy加权)
    """
    
    def __init__(self):
        """初始化计算器"""
        self.stock_to_sectors: Dict[str, List[str]] = {}
        self.sector_stocks: Dict[str, List[str]] = {}
        self._last_build_time = None
        logger.info("✅ [SectorEmotionCalculator] 初始化完成")
    
    def build_stock_sector_index(self, sector_list: List[str] = None) -> Dict[str, List[str]]:
        """
        构建股票到板块的索引 (盘前执行)
        
        Args:
            sector_list: 板块列表，如果为None则使用QMT所有板块
            
        Returns:
            Dict: 股票代码到板块列表的映射 {'300730': ['固态电池', '华为概念', ...]}
        """
        start_time = time.time()
        logger.info("🔄 开始构建股票-板块索引...")
        
        try:
            from xtquant import xtdata
            
            if sector_list is None:
                # 获取所有板块
                sector_list = xtdata.get_sector_list()
            
            stock_to_sectors = {}
            sector_stocks = {}
            
            # 遍历每个板块，获取其股票列表
            for sector in sector_list:
                try:
                    stocks = xtdata.get_stock_list_in_sector(sector)
                    if stocks:  # 只处理有股票的板块
                        sector_stocks[sector] = stocks
                        
                        # 为每只股票添加板块信息
                        for stock in stocks:
                            if stock not in stock_to_sectors:
                                stock_to_sectors[stock] = []
                            if sector not in stock_to_sectors[stock]:
                                stock_to_sectors[stock].append(sector)
                except Exception as e:
                    logger.warning(f"⚠️ 获取板块 {sector} 数据失败: {e}")
                    continue
            
            # 保存到实例变量
            self.stock_to_sectors = stock_to_sectors
            self.sector_stocks = sector_stocks
            self._last_build_time = datetime.now()
            
            logger.info(f"✅ 股票-板块索引构建完成: {len(stock_to_sectors)} 只股票, {len(sector_stocks)} 个板块")
            logger.info(f"📊 耗时: {time.time() - start_time:.2f}s")
            
            return stock_to_sectors
            
        except Exception as e:
            logger.error(f"❌ 股票-板块索引构建失败: {e}")
            return {}
    
    def calculate_sector_emotion(self, market_snapshot: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        计算全市场板块情绪 (V20物理势能重构版)
        
        【CTO铁律】剿灭散户基因 - 删除所有green_stocks/red_board等红绿盘逻辑
        【物理建模】植入微观势能 - volume_ratio + turnover_rate_per_min判定动能
        
        Args:
            market_snapshot: 市场快照DataFrame，包含stock_code, volume_ratio, turnover_rate_per_min等字段
            
        Returns:
            Dict: 板块情绪数据 (物理术语命名)
                  {
                      '固态电池': {
                          'kinetic_energy': 5,      # 动能领袖数 (volume_ratio>3且turnover_rate_per_min>0.2)
                          'potential_energy': 0.25, # 势能密度 (kinetic_energy/total_stocks)
                          'sector_temperature': 2.5,# 板块温度 (kinetic_energy加权)
                          'total_stocks': 20        # 总股票数
                      },
                      ...
                  }
        """
        if market_snapshot.empty:
            logger.warning("⚠️ 市场快照为空，无法计算板块情绪")
            return {}
        
        if not self.stock_to_sectors:
            logger.warning("⚠️ 股票-板块索引未构建，先调用build_stock_sector_index")
            return {}
        
        start_time = time.time()
        logger.info(f"🔄 [V20物理势能] 开始计算板块情绪: {len(market_snapshot)} 只股票")
        
        # V20重构: 向量化计算 - 严禁使用循环遍历个股
        # 步骤1: 为market_snapshot添加板块信息 (explode展开多对多关系)
        snapshot_with_sectors = market_snapshot.copy()
        snapshot_with_sectors['sectors'] = snapshot_with_sectors['stock_code'].map(
            lambda x: self.stock_to_sectors.get(x, [])
        )
        
        # 步骤2: 过滤掉没有板块信息的股票，然后explode展开
        snapshot_with_sectors = snapshot_with_sectors[snapshot_with_sectors['sectors'].apply(len) > 0]
        snapshot_exploded = snapshot_with_sectors.explode('sectors').rename(columns={'sectors': 'sector'})
        
        if snapshot_exploded.empty:
            logger.warning("⚠️ 没有股票能映射到板块")
            return {}
        
        # 步骤3: 物理势能判定 - 动能领袖 (volume_ratio > 3 且 turnover_rate_per_min > 0.2)
        snapshot_exploded['is_kinetic_leader'] = (
            (snapshot_exploded.get('volume_ratio', 0) > 3) & 
            (snapshot_exploded.get('turnover_rate_per_min', 0) > 0.2)
        ).astype(int)
        
        # 步骤4: 向量化聚合计算每个板块的物理指标
        sector_grouped = snapshot_exploded.groupby('sector').agg({
            'stock_code': 'count',           # 总股票数
            'is_kinetic_leader': 'sum'       # 动能领袖数
        }).rename(columns={
            'stock_code': 'total_stocks',
            'is_kinetic_leader': 'kinetic_energy'
        })
        
        # 步骤5: 计算派生物理指标
        sector_grouped['potential_energy'] = sector_grouped['kinetic_energy'] / sector_grouped['total_stocks']
        sector_grouped['sector_temperature'] = sector_grouped['kinetic_energy'] * 0.5  # 温度系数
        
        # 步骤6: 转换为返回格式
        sector_emotions = {}
        for sector, row in sector_grouped.iterrows():
            sector_emotions[sector] = {
                'kinetic_energy': int(row['kinetic_energy']),      # 动能领袖数 (原leaders)
                'potential_energy': float(row['potential_energy']), # 势能密度 (原breadth)
                'sector_temperature': float(row['sector_temperature']), # 板块温度
                'total_stocks': int(row['total_stocks']),          # 总股票数
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
        
        # 统计日志
        total_kinetic = sum(e['kinetic_energy'] for e in sector_emotions.values())
        logger.info(f"✅ [V20物理势能] 板块情绪计算完成: {len(sector_emotions)} 个板块")
        logger.info(f"⚡ 全市场总动能领袖: {total_kinetic} 只")
        logger.info(f"📊 耗时: {time.time() - start_time:.3f}s")
        
        return sector_emotions
    
    def get_sector_for_stock(self, stock_code: str) -> List[str]:
        """
        获取股票所属的板块列表
        
        Args:
            stock_code: 股票代码
            
        Returns:
            List[str]: 所属板块列表
        """
        return self.stock_to_sectors.get(stock_code, [])
    
    def filter_sector_resonance(self, sector_emotions: Dict[str, Dict[str, Any]], 
                              min_kinetic_energy: int = 3, min_potential: float = 0.15) -> List[str]:
        """
        筛选共振板块 (V20物理势能版)
        
        【CTO铁律】使用物理术语判定共振 - kinetic_energy(动能) + potential_energy(势能)
        
        Args:
            sector_emotions: 板块情绪数据 (物理术语版)
            min_kinetic_energy: 最少动能领袖数 (原min_leaders)
            min_potential: 最少势能密度 (原min_breadth)
            
        Returns:
            List[str]: 共振板块列表
        """
        resonance_sectors = []
        
        for sector, emotion in sector_emotions.items():
            kinetic = emotion.get('kinetic_energy', 0)
            potential = emotion.get('potential_energy', 0)
            temperature = emotion.get('sector_temperature', 0)
            
            # V20物理共振标准: 动能充足 + 势能密集
            if kinetic >= min_kinetic_energy and potential >= min_potential:
                resonance_sectors.append(sector)
                logger.debug(f"🎯 [V20共振板块] {sector} (动能:{kinetic}, 势能:{potential:.2f}, 温度:{temperature:.2f})")
        
        # 按动能排序返回
        resonance_sectors.sort(
            key=lambda x: sector_emotions[x].get('kinetic_energy', 0), 
            reverse=True
        )
        
        if resonance_sectors:
            logger.info(f"🎯 [V20共振板块] 筛选完成: {len(resonance_sectors)} 个板块共振")
        
        return resonance_sectors


# 便捷函数
def create_sector_emotion_calculator() -> SectorEmotionCalculator:
    """
    创建板块情绪计算器实例
    
    Returns:
        SectorEmotionCalculator: 计算器实例
    """
    return SectorEmotionCalculator()


if __name__ == "__main__":
    # V20物理势能重构版测试
    print("🧪 [V20物理势能] 板块情绪计算器测试")
    print("=" * 60)
    
    calc = create_sector_emotion_calculator()
    
    # 测试构建索引
    print("🔍 1. 测试构建股票-板块索引...")
    stock_sector_map = calc.build_stock_sector_index(['沪深A股', '创业板', '科创板'])
    print(f"   索引构建完成: {len(stock_sector_map)} 只股票")
    
    if stock_sector_map:
        # 取几个测试股票
        test_stocks = list(stock_sector_map.keys())[:10]
        print(f"   测试股票: {test_stocks}")
        
        # 测试股票板块查询
        test_stock = test_stocks[0]
        sectors = calc.get_sector_for_stock(test_stock)
        print(f"   {test_stock} 所属板块: {sectors}")
    
    # 模拟市场快照数据 (V20物理势能字段)
    print("\n🔍 2. 模拟市场快照计算板块情绪 [物理势能版]...")
    print("   判定标准: volume_ratio > 3 且 turnover_rate_per_min > 0.2 → kinetic_leader")
    
    import numpy as np
    np.random.seed(42)
    
    mock_snapshot = pd.DataFrame({
        'stock_code': test_stocks,
        # 删除change_pct散户字段，改用物理势能字段
        'volume_ratio': np.random.uniform(0.5, 8.0, 10),           # 量比
        'turnover_rate_per_min': np.random.uniform(0.05, 0.5, 10)  # 每分钟换手率%
    })
    
    print(f"   模拟数据:\n{mock_snapshot}")
    
    emotions = calc.calculate_sector_emotion(mock_snapshot)
    print(f"\n   计算情绪完成: {len(emotions)} 个板块")
    
    # 显示前几个板块情绪 (物理术语)
    print("\n   [物理指标展示]")
    for sector, data in list(emotions.items())[:5]:
        print(f"   ⚡ {sector}: 动能={data['kinetic_energy']}, 势能={data['potential_energy']:.2f}, 温度={data['sector_temperature']:.1f}")
    
    # 测试共振板块筛选 (物理标准)
    resonance = calc.filter_sector_resonance(emotions, min_kinetic_energy=1, min_potential=0.1)
    print(f"\n🎯 [V20共振板块] 动能≥1 且 势能≥0.1: {resonance}")
    
    print("\n✅ [V20物理势能] 测试完成 - 散户基因已剿灭")
