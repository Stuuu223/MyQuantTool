"""
板块情绪计算器 - 实现CTO规划的板块共振计算 (Leaders & Breadth)

功能：
- 构建股票到板块的映射索引
- 计算板块内涨停先锋(Leaders)数量
- 计算板块赚钱效应(Breadth)比例

Author: AI总监 (CTO规划)
Date: 2026-02-24
Version: Phase 21
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
    板块情绪计算器
    
    CTO规划的实时运算链路:
    1. 全市场拉取: 拿到N只股票的change_pct
    2. 瞬间归位: 通过stock_to_sectors映射到各板块篮子
    3. 计算Leaders: 涨幅>9.5%的票数
    4. 计算Breadth: 红盘票占比
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
        计算全市场板块情绪 (CTO规划的实时运算)
        
        Args:
            market_snapshot: 市场快照DataFrame，包含stock_code, change_pct等字段
            
        Returns:
            Dict: 板块情绪数据
                  {
                      '固态电池': {
                          'leaders': 3,      # 涨停先锋数
                          'breadth': 0.6,    # 赚钱效应比例
                          'avg_change': 3.5, # 平均涨幅
                          'total_stocks': 20 # 总股票数
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
        logger.info(f"🔄 开始计算板块情绪: {len(market_snapshot)} 只股票")
        
        # CTO加固: 将股票数据按板块分组
        sector_data = {}
        
        for _, row in market_snapshot.iterrows():
            stock_code = row.get('stock_code', '')
            change_pct = row.get('change_pct', 0)
            
            if stock_code in self.stock_to_sectors:
                sectors = self.stock_to_sectors[stock_code]
                
                for sector in sectors:
                    if sector not in sector_data:
                        sector_data[sector] = {
                            'change_pct_list': [],
                            'leaders': 0,  # 涨停先锋(涨幅>9.5%)
                            'green_stocks': 0,  # 红盘股票数
                            'total_stocks': 0
                        }
                    
                    sector_data[sector]['change_pct_list'].append(change_pct)
                    sector_data[sector]['total_stocks'] += 1
                    
                    # 统计涨停先锋 (涨幅>9.5%)
                    if change_pct > 9.5:
                        sector_data[sector]['leaders'] += 1
                    
                    # 统计红盘股票 (涨幅>0%)
                    if change_pct > 0:
                        sector_data[sector]['green_stocks'] += 1
        
        # 计算每个板块的情绪指标
        sector_emotions = {}
        for sector, data in sector_data.items():
            total_stocks = data['total_stocks']
            if total_stocks == 0:
                continue
                
            # CTO加固: 计算情绪指标
            avg_change = sum(data['change_pct_list']) / len(data['change_pct_list']) if data['change_pct_list'] else 0
            leaders_count = data['leaders']
            breadth_ratio = data['green_stocks'] / total_stocks
            
            sector_emotions[sector] = {
                'leaders': leaders_count,           # 涨停先锋数
                'breadth': breadth_ratio,           # 赚钱效应比例
                'avg_change': avg_change,           # 平均涨幅
                'total_stocks': total_stocks,       # 总股票数
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
        
        logger.info(f"✅ 板块情绪计算完成: {len(sector_emotions)} 个板块")
        logger.info(f"📊 耗时: {time.time() - start_time:.2f}s")
        
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
                              min_leaders: int = 3, min_breadth: float = 0.4) -> List[str]:
        """
        筛选共振板块 (CTO规划的时机斧判断标准)
        
        Args:
            sector_emotions: 板块情绪数据
            min_leaders: 最少涨停先锋数
            min_breadth: 最少赚钱效应比例
            
        Returns:
            List[str]: 共振板块列表
        """
        resonance_sectors = []
        
        for sector, emotion in sector_emotions.items():
            leaders = emotion.get('leaders', 0)
            breadth = emotion.get('breadth', 0)
            
            # CTO加固: 使用严格的共振标准
            if leaders >= min_leaders and breadth >= min_breadth:
                resonance_sectors.append(sector)
                logger.debug(f"🎯 共振板块: {sector} (Leaders:{leaders}, Breadth:{breadth:.2f})")
        
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
    # 测试板块情绪计算器
    print("🧪 板块情绪计算器测试")
    print("=" * 50)
    
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
    
    # 模拟市场快照数据
    print("\n🔍 2. 模拟市场快照计算板块情绪...")
    mock_snapshot = pd.DataFrame({
        'stock_code': test_stocks,
        'change_pct': [3.2, 5.1, 10.2, -1.5, 9.8, 2.3, 12.1, 8.7, -0.5, 9.6]
    })
    
    emotions = calc.calculate_sector_emotion(mock_snapshot)
    print(f"   计算情绪完成: {len(emotions)} 个板块")
    
    # 显示前几个板块情绪
    for sector, data in list(emotions.items())[:5]:
        print(f"   {sector}: Leaders={data['leaders']}, Breadth={data['breadth']:.2f}, AvgChange={data['avg_change']:.2f}%")
    
    # 测试共振板块筛选
    resonance = calc.filter_sector_resonance(emotions, min_leaders=1, min_breadth=0.3)
    print(f"\n🎯 共振板块: {resonance}")
    
    print("\n✅ 测试完成")
