#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V13 第二阶段：板块轮动检测模块 (Sector Rotation Detector)
实时检测板块轮动信号，识别主线切换时机
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from logic.utils.logger import get_logger
from logic.database_manager import get_db_manager

logger = get_logger(__name__)


class SectorRotationDetector:
    """
    V13 第二阶段：板块轮动检测器
    
    功能：
    1. 实时检测板块轮动信号
    2. 识别主线切换时机
    3. 预警板块切换风险
    """
    
    def __init__(self):
        self.db = get_db_manager()
        self.rotation_threshold = 0.3  # 轮动阈值（30%的板块变化）
    
    def detect_rotation(self, current_top_sectors: List[str]) -> Dict[str, any]:
        """
        检测板块轮动信号
        
        Args:
            current_top_sectors: 当前热度最高的板块列表
        
        Returns:
            dict: {
                'is_rotating': 是否正在轮动,
                'rotation_strength': 轮动强度 (0-1),
                'old_main': 旧主线板块,
                'new_main': 新主线板块,
                'rotation_type': '主线切换' | '板块扩散' | '无轮动',
                'recommendation': '建议操作',
                'alert_level': '高' | '中' | '低'
            }
        """
        try:
            # 获取昨日领涨板块
            yesterday_stats = self._get_yesterday_top_sectors()
            
            if not yesterday_stats:
                logger.warning("⚠️ 无历史板块数据，无法检测轮动")
                return self._get_no_rotation_result(current_top_sectors)
            
            yesterday_top_sectors = yesterday_stats.get('top_sectors', [])
            
            # 计算板块变化率
            rotation_strength = self._calculate_rotation_strength(
                yesterday_top_sectors, 
                current_top_sectors
            )
            
            # 判断轮动类型
            rotation_type, old_main, new_main = self._determine_rotation_type(
                yesterday_top_sectors,
                current_top_sectors
            )
            
            # 判断是否正在轮动
            is_rotating = rotation_strength > self.rotation_threshold
            
            # 生成建议
            recommendation, alert_level = self._generate_recommendation(
                is_rotating,
                rotation_type,
                rotation_strength
            )
            
            return {
                'timestamp': datetime.now().isoformat(),
                'is_rotating': is_rotating,
                'rotation_strength': rotation_strength,
                'old_main': old_main,
                'new_main': new_main,
                'rotation_type': rotation_type,
                'recommendation': recommendation,
                'alert_level': alert_level,
                'yesterday_sectors': yesterday_top_sectors,
                'today_sectors': current_top_sectors
            }
            
        except Exception as e:
            logger.error(f"检测板块轮动失败: {e}")
            return self._get_no_rotation_result(current_top_sectors)
    
    def _get_yesterday_top_sectors(self) -> Optional[Dict]:
        """获取昨日领涨板块"""
        try:
            sql = "SELECT date, top_sectors FROM market_summary ORDER BY date DESC LIMIT 1"
            results = self.db.sqlite_query(sql)
            
            if not results:
                return None
            
            row = results[0]
            import json
            top_sectors = json.loads(row[1]) if row[1] else []
            
            return {
                'date': row[0],
                'top_sectors': top_sectors
            }
            
        except Exception as e:
            logger.error(f"获取昨日板块数据失败: {e}")
            return None
    
    def _calculate_rotation_strength(self, yesterday: List[str], today: List[str]) -> float:
        """
        计算轮动强度
        
        逻辑：计算昨日和今日板块的重叠度，重叠度越低，轮动强度越高
        
        Args:
            yesterday: 昨日板块列表
            today: 今日板块列表
        
        Returns:
            float: 轮动强度 (0-1)
        """
        if not yesterday or not today:
            return 0.0
        
        # 计算重叠板块数量
        overlap_count = len(set(yesterday) & set(today))
        
        # 计算轮动强度（重叠度越低，轮动强度越高）
        rotation_strength = 1.0 - (overlap_count / min(len(yesterday), len(today)))
        
        return round(rotation_strength, 2)
    
    def _determine_rotation_type(self, yesterday: List[str], today: List[str]) -> Tuple[str, str, str]:
        """
        判断轮动类型
        
        Args:
            yesterday: 昨日板块列表
            today: 今日板块列表
        
        Returns:
            tuple: (轮动类型, 旧主线, 新主线)
        """
        if not yesterday or not today:
            return '无轮动', '', ''
        
        # 识别旧主线（昨日排名第一的板块）
        old_main = yesterday[0] if yesterday else ''
        
        # 识别新主线（今日排名第一的板块）
        new_main = today[0] if today else ''
        
        # 判断轮动类型
        if old_main != new_main:
            # 主线切换
            return '主线切换', old_main, new_main
        elif len(set(yesterday) & set(today)) < len(yesterday) * 0.5:
            # 板块扩散（新板块进入 Top 3）
            return '板块扩散', old_main, new_main
        else:
            # 无轮动
            return '无轮动', old_main, new_main
    
    def _generate_recommendation(self, is_rotating: bool, rotation_type: str, rotation_strength: float) -> Tuple[str, str]:
        """
        生成操作建议
        
        Args:
            is_rotating: 是否正在轮动
            rotation_type: 轮动类型
            rotation_strength: 轮动强度
        
        Returns:
            tuple: (建议, 预警级别)
        """
        if not is_rotating:
            return '主线稳定，可继续持有主线核心', '低'
        
        if rotation_type == '主线切换':
            if rotation_strength > 0.7:
                return '主线切换强烈，建议减仓观望，等待新主线确认', '高'
            else:
                return '主线切换中，建议关注新主线，谨慎参与旧主线', '中'
        
        elif rotation_type == '板块扩散':
            return '板块扩散，市场情绪活跃，可关注新进板块', '中'
        
        else:
            return '市场稳定，按原策略操作', '低'
    
    def _get_no_rotation_result(self, current_top_sectors: List[str]) -> Dict:
        """返回无轮动结果"""
        return {
            'timestamp': datetime.now().isoformat(),
            'is_rotating': False,
            'rotation_strength': 0.0,
            'old_main': '',
            'new_main': current_top_sectors[0] if current_top_sectors else '',
            'rotation_type': '无轮动',
            'recommendation': '数据不足，无法判断轮动',
            'alert_level': '低',
            'yesterday_sectors': [],
            'today_sectors': current_top_sectors
        }


# 单例测试
if __name__ == "__main__":
    srd = SectorRotationDetector()
    
    # 测试板块轮动检测
    current_sectors = ['人工智能', '新能源', '医药']
    rotation = srd.detect_rotation(current_sectors)
    
    print("🔄 板块轮动检测")
    print(f"时间戳: {rotation['timestamp']}")
    print(f"是否轮动: {rotation['is_rotating']}")
    print(f"轮动强度: {rotation['rotation_strength']:.2f}")
    print(f"轮动类型: {rotation['rotation_type']}")
    print(f"旧主线: {rotation['old_main']}")
    print(f"新主线: {rotation['new_main']}")
    print(f"建议: {rotation['recommendation']}")
    print(f"预警级别: {rotation['alert_level']}")