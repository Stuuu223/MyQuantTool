#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V13 第二阶段：板块资金流向追踪模块 (Sector Capital Tracker)
实时追踪板块资金流向，识别主力资金动向
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from logic.utils.logger import get_logger
import akshare as ak

logger = get_logger(__name__)


class SectorCapitalTracker:
    """
    V13 第二阶段：板块资金流向追踪器
    
    功能：
    1. 实时追踪各板块的资金净流入/流出
    2. 识别主力资金动向
    3. 预警资金撤离信号
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_expire_seconds = 60
    
    def get_sector_capital_flow(self) -> Dict[str, any]:
        """
        获取实时板块资金流向数据
        
        Returns:
            dict: {
                'timestamp': 时间戳,
                'sectors': [
                    {
                        'name': 板块名称,
                        'net_inflow': 净流入（亿元）,
                        'inflow_rank': 流入排名,
                        'capital_status': '流入' | '流出' | '持平'
                    },
                    ...
                ],
                'top_inflow': 净流入最多的板块,
                'top_outflow': 净流出最多的板块,
                'alert_sectors': 需要预警的板块
            }
        """
        try:
            # 获取行业板块资金流向数据
            # 注意：AkShare 可能没有直接的板块资金流向接口，这里使用成交额作为代理指标
            sector_df = ak.stock_board_industry_name_em()
            
            if sector_df is None or sector_df.empty:
                logger.warning("⚠️ 无法获取板块资金流向数据")
                return self._get_empty_result()
            
            # 处理数据
            sectors = []
            for _, row in sector_df.iterrows():
                sector_name = row['板块名称']
                amount = row.get('成交额', 0)  # 成交额（元）
                
                # 将成交额转换为亿元
                amount_billion = amount / 1e8
                
                # 计算净流入（这里简化处理，实际应该使用真实资金流向数据）
                # 暂时使用涨跌幅作为资金流向的代理指标
                change_pct = row.get('涨跌幅', 0)
                net_inflow = amount_billion * (change_pct / 100)
                
                # 判断资金状态
                if net_inflow > 0.1:
                    capital_status = '流入'
                elif net_inflow < -0.1:
                    capital_status = '流出'
                else:
                    capital_status = '持平'
                
                sectors.append({
                    'name': sector_name,
                    'amount_billion': amount_billion,
                    'change_pct': change_pct,
                    'net_inflow': net_inflow,
                    'capital_status': capital_status
                })
            
            # 按净流入排序
            sectors.sort(key=lambda x: x['net_inflow'], reverse=True)
            
            # 添加排名
            for i, sector in enumerate(sectors):
                sector['inflow_rank'] = i + 1
            
            # 识别净流入最多和最少的板块
            top_inflow = sectors[0] if sectors else None
            top_outflow = sectors[-1] if sectors else None
            
            # 识别需要预警的板块
            alert_sectors = self._detect_alert_sectors(sectors)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'sectors': sectors,
                'top_inflow': top_inflow,
                'top_outflow': top_outflow,
                'alert_sectors': alert_sectors,
                'total_sectors': len(sectors)
            }
            
        except Exception as e:
            logger.error(f"获取板块资金流向数据失败: {e}")
            return self._get_empty_result()
    
    def _detect_alert_sectors(self, sectors: List[Dict]) -> List[Dict]:
        """
        检测需要预警的板块
        
        逻辑：
        1. 净流入 > 5亿元 → 资金大幅流入预警
        2. 净流出 < -3亿元 → 资金大幅流出预警
        
        Args:
            sectors: 板块列表
        
        Returns:
            list: 需要预警的板块列表
        """
        alert_sectors = []
        
        for sector in sectors:
            net_inflow = sector['net_inflow']
            
            # 资金大幅流入预警
            if net_inflow > 5:
                sector['alert_type'] = '资金大幅流入'
                sector['alert_level'] = '高'
                alert_sectors.append(sector)
            
            # 资金大幅流出预警
            elif net_inflow < -3:
                sector['alert_type'] = '资金大幅流出'
                sector['alert_level'] = '高'
                alert_sectors.append(sector)
        
        return alert_sectors
    
    def _get_empty_result(self) -> Dict:
        """返回空结果"""
        return {
            'timestamp': datetime.now().isoformat(),
            'sectors': [],
            'top_inflow': None,
            'top_outflow': None,
            'alert_sectors': [],
            'total_sectors': 0
        }
    
    def get_sector_capital_history(self, sector_name: str, days: int = 5) -> Dict:
        """
        获取板块资金流向历史趋势
        
        Args:
            sector_name: 板块名称
            days: 历史天数
        
        Returns:
            dict: 板块资金流向历史趋势数据
        """
        # 这里可以扩展为从数据库读取历史资金流向数据
        # 目前先返回空数据
        return {
            'sector': sector_name,
            'history': [],
            'message': '历史资金流向数据积累中...'
        }


# 单例测试
if __name__ == "__main__":
    sct = SectorCapitalTracker()
    capital_flow = sct.get_sector_capital_flow()
    
    print("💰 板块资金流向追踪")
    print(f"时间戳: {capital_flow['timestamp']}")
    print(f"总板块数: {capital_flow['total_sectors']}")
    
    if capital_flow['top_inflow']:
        print(f"\n💵 净流入最多: {capital_flow['top_inflow']['name']} ({capital_flow['top_inflow']['net_inflow']:.2f}亿元)")
    
    if capital_flow['top_outflow']:
        print(f"💸 净流出最多: {capital_flow['top_outflow']['name']} ({capital_flow['top_outflow']['net_inflow']:.2f}亿元)")
    
    if capital_flow['alert_sectors']:
        print("\n⚠️ 资金预警板块:")
        for sector in capital_flow['alert_sectors']:
            print(f"  {sector['name']}: {sector['alert_type']} ({sector['alert_level']})")