#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V13 第二阶段：实时板块热度监控模块 (Sector Pulse Monitor)
实时感知板块的"心跳"，检测板块热度突增/突降
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from logic.utils.logger import get_logger
import akshare as ak

logger = get_logger(__name__)


class SectorPulseMonitor:
    """
    V13 第二阶段：实时板块热度监控器
    
    功能：
    1. 实时监控各板块的涨跌幅、成交量变化
    2. 检测板块热度突增/突降
    3. 预警板块轮动信号
    """
    
    def __init__(self):
        self.cache = {}  # 板块数据缓存
        self.cache_expire_seconds = 60  # 缓存60秒
        
    def get_sector_pulse(self) -> Dict[str, any]:
        """
        获取实时板块热度数据
        
        Returns:
            dict: {
                'timestamp': 时间戳,
                'sectors': [
                    {
                        'name': 板块名称,
                        'change_pct': 涨跌幅,
                        'volume_ratio': 量比,
                        'pulse_score': 心跳分数,
                        'pulse_status': '加速' | '减速' | '平稳'
                    },
                    ...
                ],
                'top_sectors': 热度最高的板块列表,
                'alert_sectors': 需要预警的板块列表
            }
        """
        try:
            # 获取行业板块行情
            sector_df = ak.stock_board_industry_name_em()
            
            if sector_df is None or sector_df.empty:
                logger.warning("⚠️ 无法获取板块数据")
                return self._get_empty_result()
            
            # 处理数据
            sectors = []
            for _, row in sector_df.iterrows():
                sector_name = row['板块名称']
                change_pct = row.get('涨跌幅', 0)
                volume = row.get('成交量', 0)
                amount = row.get('成交额', 0)
                
                # 计算心跳分数（基于涨跌幅和成交量）
                pulse_score = self._calculate_pulse_score(change_pct, volume, amount)
                
                # 判断心跳状态
                pulse_status = self._determine_pulse_status(pulse_score, change_pct)
                
                sectors.append({
                    'name': sector_name,
                    'change_pct': change_pct,
                    'volume': volume,
                    'amount': amount,
                    'pulse_score': pulse_score,
                    'pulse_status': pulse_status
                })
            
            # 按心跳分数排序
            sectors.sort(key=lambda x: x['pulse_score'], reverse=True)
            
            # 识别热点板块和预警板块
            top_sectors = sectors[:5]  # 热度最高的5个板块
            alert_sectors = self._detect_alert_sectors(sectors)  # 需要预警的板块
            
            return {
                'timestamp': datetime.now().isoformat(),
                'sectors': sectors,
                'top_sectors': top_sectors,
                'alert_sectors': alert_sectors,
                'total_sectors': len(sectors)
            }
            
        except Exception as e:
            logger.error(f"获取板块热度数据失败: {e}")
            return self._get_empty_result()
    
    def _calculate_pulse_score(self, change_pct: float, volume: float, amount: float) -> float:
        """
        计算板块心跳分数
        
        逻辑：
        - 涨跌幅越高，分数越高
        - 成交量越大，分数越高
        - 综合评分：0-100
        
        Args:
            change_pct: 涨跌幅
            volume: 成交量
            amount: 成交额
        
        Returns:
            float: 心跳分数 (0-100)
        """
        # 涨跌幅贡献（最高50分）
        change_score = min(50, max(0, change_pct * 5))
        
        # 成交额贡献（最高50分）
        # 对数缩放，避免大额成交额影响过大
        amount_score = min(50, np.log10(max(1, amount)) * 10)
        
        # 综合评分
        pulse_score = change_score + amount_score
        
        return round(pulse_score, 2)
    
    def _determine_pulse_status(self, pulse_score: float, change_pct: float) -> str:
        """
        判断心跳状态
        
        Args:
            pulse_score: 心跳分数
            change_pct: 涨跌幅
        
        Returns:
            str: '加速' | '减速' | '平稳'
        """
        if pulse_score >= 70:
            return '加速'
        elif pulse_score >= 40:
            return '平稳'
        else:
            return '减速'
    
    def _detect_alert_sectors(self, sectors: List[Dict]) -> List[Dict]:
        """
        检测需要预警的板块
        
        逻辑：
        1. 涨跌幅 > 5% 且心跳分数 > 80 → 热度过高预警
        2. 涨跌幅 < -3% → 回调预警
        
        Args:
            sectors: 板块列表
        
        Returns:
            list: 需要预警的板块列表
        """
        alert_sectors = []
        
        for sector in sectors:
            change_pct = sector['change_pct']
            pulse_score = sector['pulse_score']
            
            # 热度过高预警
            if change_pct > 5 and pulse_score > 80:
                sector['alert_type'] = '热度过高'
                sector['alert_level'] = '高'
                alert_sectors.append(sector)
            
            # 回调预警
            elif change_pct < -3:
                sector['alert_type'] = '回调'
                sector['alert_level'] = '中'
                alert_sectors.append(sector)
        
        return alert_sectors
    
    def _get_empty_result(self) -> Dict:
        """返回空结果"""
        return {
            'timestamp': datetime.now().isoformat(),
            'sectors': [],
            'top_sectors': [],
            'alert_sectors': [],
            'total_sectors': 0
        }
    
    def get_sector_trend(self, sector_name: str, days: int = 5) -> Dict:
        """
        获取板块历史趋势
        
        Args:
            sector_name: 板块名称
            days: 历史天数
        
        Returns:
            dict: 板块历史趋势数据
        """
        # 这里可以扩展为从数据库读取历史板块数据
        # 目前先返回空数据
        return {
            'sector': sector_name,
            'trend': [],
            'message': '历史趋势数据积累中...'
        }


# 单例测试
if __name__ == "__main__":
    spm = SectorPulseMonitor()
    pulse = spm.get_sector_pulse()
    
    print("📊 实时板块热度监控")
    print(f"时间戳: {pulse['timestamp']}")
    print(f"总板块数: {pulse['total_sectors']}")
    
    print("\n🔥 热度最高的板块:")
    for sector in pulse['top_sectors']:
        print(f"  {sector['name']}: {sector['change_pct']:.2f}% (心跳: {sector['pulse_score']:.1f})")
    
    if pulse['alert_sectors']:
        print("\n⚠️ 预警板块:")
        for sector in pulse['alert_sectors']:
            print(f"  {sector['name']}: {sector['alert_type']} ({sector['alert_level']})")