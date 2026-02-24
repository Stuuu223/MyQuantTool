# 资金流情绪计算器 - 实现CTO规划的资金流情绪计算

功能：
- 计算个股资金流入流出
- 计算板块资金情绪
- 提供防守斧判断依据

Author: AI总监 (CTO规划)  
Date: 2026-02-24
Version: Phase 21
"
import pandas as pd
from typing import Dict, List, Any
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


class CapitalFlowCalculator:
    "
    资金流情绪计算器
    
    CTO规划的防守斧判断依据:
    - 识别主力资金流入流出
    - 检测诱多陷阱
    - 提供交易时机判断
    "
    
    def __init__(self):
        "初始化计算器"
        self._last_calc_time = None
        logger.info("✅ [CapitalFlowCalculator] 初始化完成")
    
    def calculate_stock_flow(self, stock_data: Dict[str, Any]) -> Dict[str, float]:
        "
        计算个股资金流情绪
        
        Args:
            stock_data: 股票数据，包含price, volume, amount等
            
        Returns:
            Dict: 资金流情绪指标
        "
        try:
            price = stock_data.get('price', 0)
            volume = stock_data.get('volume', 0)
            amount = stock_data.get('amount', 0)
            prev_close = stock_data.get('prev_close', 0)
            change_pct = stock_data.get('change_pct', 0)
            
            # 计算基础指标
            flow_data = {
                'price': price,
                'volume': volume,
                'amount': amount,
                'change_pct': change_pct,
                'prev_close': prev_close
            }
            
            # CTO加固: 计算资金流情绪指标
            # 1. 成交额强度 (衡量资金关注度)
            flow_intensity = amount / 1e6  # 以万元为单位
            
            # 2. 价量配合度 (衡量资金真假)
            if prev_close > 0 and volume > 0:
                vol_price_ratio = change_pct / (volume / 1e6) if volume > 0 else 0
            else:
                vol_price_ratio = 0
            
            # 3. 资金流入流出估算 (简化版)
            # 假设上涨时大部分资金为流入，下跌时大部分资金为流出
            if change_pct > 0:
                estimated_inflow = amount * (change_pct / 10)  # 简化计算
                estimated_outflow = amount - estimated_inflow
            else:
                estimated_outflow = amount * (abs(change_pct) / 10)  # 简化计算
                estimated_inflow = amount - estimated_outflow
            
            # 保证估算值不为负
            estimated_inflow = max(0, estimated_inflow)
            estimated_outflow = max(0, estimated_outflow)
            
            # 资金净流入
            net_flow = estimated_inflow - estimated_outflow
            
            # 资金情绪得分 (0-100, 100表示极度流入)
            if amount > 0:
                flow_score = max(0, min(100, 50 + net_flow / amount * 50))
            else:
                flow_score = 50  # 无成交时中性
            
            return {
                'flow_intensity': flow_intensity,      # 成交额强度
                'vol_price_ratio': vol_price_ratio,    # 价量配合度
                'estimated_inflow': estimated_inflow,  # 估算流入
                'estimated_outflow': estimated_outflow, # 估算流出
                'net_flow': net_flow,                  # 净流入
                'flow_score': flow_score,              # 资金情绪得分
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"❌ 计算个股资金流失败: {e}")
            return {
                'flow_intensity': 0,
                'vol_price_ratio': 0,
                'estimated_inflow': 0,
                'estimated_outflow': 0,
                'net_flow': 0,
                'flow_score': 50,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
    
    def calculate_sector_flow(self, sector_stocks_data: List[Dict[str, Any]]) -> Dict[str, float]:
        "
        计算板块资金情绪
        
        Args:
            sector_stocks_data: 板块内股票数据列表
            
        Returns:
            Dict: 板块资金情绪指标
        "
        if not sector_stocks_data:
            return {
                'avg_flow_score': 50,
                'total_amount': 0,
                'net_flow': 0,
                'inflow_stocks_ratio': 0,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
        
        total_amount = 0
        total_net_flow = 0
        positive_flow_count = 0
        
        for stock_data in sector_stocks_data:
            flow_info = self.calculate_stock_flow(stock_data)
            
            total_amount += stock_data.get('amount', 0)
            total_net_flow += flow_info['net_flow']
            
            if flow_info['net_flow'] > 0:
                positive_flow_count += 1
        
        avg_flow_score = sum([self.calculate_stock_flow(sd)['flow_score'] for sd in sector_stocks_data]) / len(sector_stocks_data)
        inflow_stocks_ratio = positive_flow_count / len(sector_stocks_data)
        
        return {
            'avg_flow_score': avg_flow_score,          # 平均资金情绪得分
            'total_amount': total_amount,              # 总成交额
            'net_flow': total_net_flow,                # 净流入
            'inflow_stocks_ratio': inflow_stocks_ratio, # 资金流入股票比例
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
    
    def detect_flow_trap(self, stock_data: Dict[str, Any], flow_info: Dict[str, float]) -> bool:
        "
        检测资金流陷阱 (CTO规划的防守斧功能)
        
        Args:
            stock_data: 股票数据
            flow_info: 资金流信息
            
        Returns:
            bool: 是否为陷阱
        "
        try:
            change_pct = stock_data.get('change_pct', 0)
            flow_score = flow_info.get('flow_score', 50)
            vol_price_ratio = flow_info.get('vol_price_ratio', 0)
            
            # CTO加固: 检测多种陷阱模式
            # 1. 高涨幅 + 低资金流得分 (诱多)
            if change_pct > 8 and flow_score < 40:
                logger.warning(f"⚠️ 检测到诱多陷阱: {stock_data.get('stock_code', 'N/A')} "
                              f"涨幅{change_pct:.2f}% 资金情绪{flow_score:.2f}")
                return True
            
            # 2. 价量背离 (价格涨但资金流出)
            if change_pct > 5 and flow_info.get('net_flow', 0) < 0:
                logger.warning(f"⚠️ 检测到价量背离: {stock_data.get('stock_code', 'N/A')} "
                              f"涨幅{change_pct:.2f}% 净流出{flow_info.get('net_flow', 0):.2f}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 检测资金陷阱失败: {e}")
            return False


# 便捷函数
def create_capital_flow_calculator() -> CapitalFlowCalculator:
    "
    创建资金流计算器实例
    
    Returns:
        CapitalFlowCalculator: 计算器实例
    "
    return CapitalFlowCalculator()


if __name__ == "__main__":
    # 测试资金流计算器
    print("🧪 资金流计算器测试")
    print("=" * 50)
    
    calc = create_capital_flow_calculator()
    
    # 测试个股资金流计算
    print("🔍 1. 测试个股资金流计算...")
    mock_stock_data = {
        'stock_code': '300986.SZ',
        'price': 13.42,
        'volume': 1000000,
        'amount': 13420000,
        'change_pct': 5.2,
        'prev_close': 12.76
    }
    
    flow_info = calc.calculate_stock_flow(mock_stock_data)
    print(f"   {mock_stock_data['stock_code']} 资金流信息:")
    for key, value in flow_info.items():
        print(f"   {key}: {value}")
    
    # 测试陷阱检测
    print(f"\n🔍 2. 测试陷阱检测...")
    trap_detected = calc.detect_flow_trap(mock_stock_data, flow_info)
    print(f"   陷阱检测结果: {'是' if trap_detected else '否'}")
    
    # 测试板块资金流
    print(f"\n🔍 3. 测试板块资金流计算...")
    mock_sector_data = [mock_stock_data, mock_stock_data.copy(), mock_stock_data.copy()]
    mock_sector_data[1]['change_pct'] = -2.1
    mock_sector_data[2]['change_pct'] = 8.5
    
    sector_flow = calc.calculate_sector_flow(mock_sector_data)
    print(f"   板块资金流信息:")
    for key, value in sector_flow.items():
        print(f"   {key}: {value}")
    
    print("\n✅ 测试完成")
