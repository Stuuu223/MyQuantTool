#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18 国家队指纹监控器
监控 ETF 异常脉冲，触发 MARKET_RESCUE_MODE
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from logic.utils.logger import get_logger
from logic.data_manager import DataManager
from logic.cache_manager import CacheManager

logger = get_logger(__name__)


class NationalTeamDetector:
    """
    国家队指纹监控器
    
    功能：
    1. 监控沪深 300 ETF、上证 50 ETF 的异常脉冲
    2. 识别国家队入场信号
    3. 触发 MARKET_RESCUE_MODE
    4. 在救援模式下，优先选择价值标的或 ETF
    """
    
    # ETF 代码
    HS300_ETFS = ['510300', '159919', '510330']  # 沪深 300 ETF
    SZ50_ETFS = ['510050', '510100', '510500']  # 上证 50 ETF
    
    # 国家队入场阈值
    ETF_PULSE_THRESHOLD = 0.5  # ETF 涨幅 > 0.5% 认为异常脉冲
    ETF_VOLUME_RATIO_THRESHOLD = 1.5  # ETF 量比 > 1.5 认为放量
    MARKET_BLEED_THRESHOLD = -1.0  # 大盘跌幅 > -1.0% 认为失血
    
    # MARKET_RESCUE_MODE 状态
    _is_rescue_mode = False
    _rescue_mode_start_time: Optional[datetime] = None
    _rescue_mode_reason = ''
    
    def __init__(self):
        """初始化国家队指纹监控器"""
        self.data_manager = DataManager()
        self.cache = CacheManager()
    
    def get_etf_performance(self, etf_code: str) -> Dict:
        """
        获取 ETF 表现
        
        Args:
            etf_code: ETF 代码
        
        Returns:
            dict: {
                'change_pct': float,  # 涨跌幅
                'volume_ratio': float,  # 量比
                'amount': float,  # 成交额
                'is_pulse': bool  # 是否异常脉冲
            }
        """
        try:
            realtime_data = self.data_manager.get_realtime_data(etf_code)
            if not realtime_data:
                return {
                    'change_pct': 0.0,
                    'volume_ratio': 0.0,
                    'amount': 0.0,
                    'is_pulse': False
                }
            
            change_pct = realtime_data.get('change_pct', 0.0)
            volume_ratio = realtime_data.get('volume_ratio', 0.0)
            amount = realtime_data.get('amount', 0.0)
            
            # 判断是否异常脉冲
            is_pulse = (change_pct > self.ETF_PULSE_THRESHOLD) and (volume_ratio > self.ETF_VOLUME_RATIO_THRESHOLD)
            
            return {
                'change_pct': change_pct,
                'volume_ratio': volume_ratio,
                'amount': amount,
                'is_pulse': is_pulse
            }
        except Exception as e:
            logger.error(f"❌ [国家队指纹] 获取 ETF {etf_code} 表现失败: {e}")
            return {
                'change_pct': 0.0,
                'volume_ratio': 0.0,
                'amount': 0.0,
                'is_pulse': False
            }
    
    def get_market_status(self) -> Dict:
        """
        获取大盘状态
        
        Returns:
            dict: {
                'is_bleeding': bool,  # 是否失血
                'avg_change': float,  # 平均涨跌幅
                'fall_count': int,  # 下跌股票数
                'total_count': int  # 总股票数
            }
        """
        try:
            # 获取主要指数
            indices = ['000001', '399001', '000300']  # 上证指数、深证成指、沪深300
            
            total_change = 0.0
            valid_count = 0
            
            for index_code in indices:
                try:
                    realtime_data = self.data_manager.get_realtime_data(index_code)
                    if realtime_data:
                        change_pct = realtime_data.get('change_pct', 0.0)
                        total_change += change_pct
                        valid_count += 1
                except Exception as e:
                    continue
            
            if valid_count == 0:
                return {
                    'is_bleeding': False,
                    'avg_change': 0.0,
                    'fall_count': 0,
                    'total_count': 0
                }
            
            avg_change = total_change / valid_count
            is_bleeding = avg_change < self.MARKET_BLEED_THRESHOLD
            
            return {
                'is_bleeding': is_bleeding,
                'avg_change': avg_change,
                'fall_count': 0,
                'total_count': 0
            }
        except Exception as e:
            logger.error(f"❌ [国家队指纹] 获取大盘状态失败: {e}")
            return {
                'is_bleeding': False,
                'avg_change': 0.0,
                'fall_count': 0,
                'total_count': 0
            }
    
    def check_national_team_signal(self) -> Dict:
        """
        检查国家队入场信号
        
        Returns:
            dict: {
                'has_signal': bool,  # 是否有国家队信号
                'signal_type': str,  # 信号类型（救援/护盘）
                'etf_pulse_count': int,  # 异常脉冲 ETF 数量
                'market_status': str,  # 大盘状态
                'reason': str  # 原因
            }
        """
        try:
            # 获取大盘状态
            market_status = self.get_market_status()
            
            # 获取 ETF 表现
            etf_pulse_count = 0
            etf_details = []
            
            all_etfs = self.HS300_ETFS + self.SZ50_ETFS
            for etf_code in all_etfs:
                etf_perf = self.get_etf_performance(etf_code)
                if etf_perf['is_pulse']:
                    etf_pulse_count += 1
                    etf_details.append({
                        'code': etf_code,
                        'change_pct': etf_perf['change_pct'],
                        'volume_ratio': etf_perf['volume_ratio']
                    })
            
            # 判断国家队信号
            has_signal = False
            signal_type = ''
            reason = ''
            
            # 大盘失血 + ETF 异常脉冲 = 国家队救援
            if market_status['is_bleeding'] and etf_pulse_count >= 2:
                has_signal = True
                signal_type = '救援'
                reason = f"大盘失血({market_status['avg_change']:.2f}%)，{etf_pulse_count}只ETF异常脉冲，国家队入场救援"
                
                # 触发 MARKET_RESCUE_MODE
                self._is_rescue_mode = True
                self._rescue_mode_start_time = datetime.now()
                self._rescue_mode_reason = reason
                
                logger.warning(f"🚨 [国家队指纹] {reason}")
            
            # ETF 异常脉冲但大盘未失血 = 国家队护盘
            elif etf_pulse_count >= 2:
                has_signal = True
                signal_type = '护盘'
                reason = f"{etf_pulse_count}只ETF异常脉冲，国家队护盘"
                
                logger.info(f"✅ [国家队指纹] {reason}")
            
            return {
                'has_signal': has_signal,
                'signal_type': signal_type,
                'etf_pulse_count': etf_pulse_count,
                'market_status': '失血' if market_status['is_bleeding'] else '正常',
                'reason': reason,
                'etf_details': etf_details
            }
        except Exception as e:
            logger.error(f"❌ [国家队指纹] 检查国家队信号失败: {e}")
            return {
                'has_signal': False,
                'signal_type': '',
                'etf_pulse_count': 0,
                'market_status': 'unknown',
                'reason': f'检查失败: {e}'
            }
    
    def is_rescue_mode(self) -> bool:
        """
        判断是否处于 MARKET_RESCUE_MODE
        
        Returns:
            bool: 是否处于救援模式
        """
        # 检查救援模式是否过期（2小时后自动退出）
        if self._is_rescue_mode and self._rescue_mode_start_time:
            if (datetime.now() - self._rescue_mode_start_time).total_seconds() > 7200:  # 2小时
                self._is_rescue_mode = False
                self._rescue_mode_start_time = None
                self._rescue_mode_reason = ''
                logger.info("✅ [国家队指纹] MARKET_RESCUE_MODE 自动退出")
        
        return self._is_rescue_mode
    
    def get_rescue_mode_info(self) -> Dict:
        """
        获取救援模式信息
        
        Returns:
            dict: {
                'is_rescue_mode': bool,
                'start_time': datetime,
                'reason': str,
                'duration': int  # 持续时间（秒）
            }
        """
        if not self._is_rescue_mode:
            return {
                'is_rescue_mode': False,
                'start_time': None,
                'reason': '',
                'duration': 0
            }
        
        duration = (datetime.now() - self._rescue_mode_start_time).total_seconds() if self._rescue_mode_start_time else 0
        
        return {
            'is_rescue_mode': True,
            'start_time': self._rescue_mode_start_time,
            'reason': self._rescue_mode_reason,
            'duration': duration
        }
    
    def exit_rescue_mode(self):
        """退出救援模式"""
        self._is_rescue_mode = False
        self._rescue_mode_start_time = None
        self._rescue_mode_reason = ''
        logger.info("✅ [国家队指纹] 手动退出 MARKET_RESCUE_MODE")


# 全局实例
_national_team_detector: Optional[NationalTeamDetector] = None


def get_national_team_detector() -> NationalTeamDetector:
    """获取国家队指纹监控器单例"""
    global _national_team_detector
    if _national_team_detector is None:
        _national_team_detector = NationalTeamDetector()
    return _national_team_detector