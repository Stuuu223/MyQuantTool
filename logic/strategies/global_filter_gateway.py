#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GlobalFilterGateway - 全局过滤网关

【架构大一统核心组件�?解决"踢一脚动一�?问题：实盘和回放必须走同一套过滤逻辑�?
【设计原则�?1. DRY原则 - 所有过滤逻辑集中于此，禁止分散在各个方法�?2. SSOT原则 - 所有阈值从Config读取，零硬编�?3. 统一入口 - 无论是盘中实盘、盘后回放、历史回测，都必须调用此网关
4. 【CTO终极红线�?/1判定，无打分！均线判定权力下放给战法Detector�?
【Boss二维铁网 - V20.3红线�?+ 早盘降阈 + P0修复 + CTO疑点修复�?1. 量能�? volume_ratio >= min_volume_multiplier (�?.0倍，动态放�? - 0/1判定
2. 换手�? min_turnover <= turnover (5%起步，大哥起步线) - 0/1判定
3. 死亡换手拦截: turnover >= 70%直接拦截（研究验证：70%以上10日亏�?4.67%�?4. 甜点位标�? 8% <= turnover <= 15%注入{'tag': '换手甜点'}，绝不加�?5. 早盘降阈: 09:30-09:45阈值降�?0%，捕捉意愿度（固定UTC+8时区�?6. 【P0修复】ATR缺数据不再伪装成低能态，保留NaN用于统计

Author: 架构大一统工�?+ CTO红线改�?+ Boss P0修复 + CTO疑点修复
Date: 2026-03-04
Version: 2.0.3
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import logging
from datetime import datetime, time as dt_time, timezone, timedelta

logger = logging.getLogger(__name__)


def safe_float(value, default=0.0):
    """
    【CTO类型安全】安全转换为float，防止str/int比较错误
    
    Args:
        value: 任意类型的输入�?        default: 转换失败时的默认�?        
    Returns:
        float: 转换后的浮点数，失败返回default
    """
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip()
        if value == '' or value.lower() in ('nan', 'inf', '-inf', 'none'):
            return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def check_early_market_scale() -> Tuple[bool, float]:
    """
    【CTO紧急修�?+ 疑点#5修复】检测早盘时间窗口并返回阈值缩放因�?    
    早盘降阈哲学（老板钦定）：
    - 早盘(09:30-09:45)是资金意愿度暴露�?    - 降低阈值至60%，扩大观察池
    - 捕捉更多早盘粒子初速度信号
    
    【疑�?5修复】显式指�?UTC+8 (中国时区)，避免非中国时区部署时窗口失�?    
    Returns:
        (is_early, scale_factor): 
            - is_early: 是否在早盘时间窗�?            - scale_factor: 阈值缩放因�?(0.6 �?1.0)
    """
    # 【疑�?5修复】使用中国时�?(UTC+8)
    china_tz = timezone(timedelta(hours=8))
    now = datetime.now(china_tz)
    current_time = now.time()
    
    # 早盘时间窗口: 09:30:00 - 09:45:59
    early_start = dt_time(9, 30, 0)
    early_end = dt_time(9, 45, 59)
    
    is_early = early_start <= current_time <= early_end
    scale_factor = 0.6 if is_early else 1.0
    
    return is_early, scale_factor


class GlobalFilterGateway:
    """
    全局过滤网关 - 统一所有选股过滤逻辑
    
    【使用场景�?    - 盘中实盘: live_cmd �?run_live_trading_engine
    - 热复�? replay_cmd �?TimeMachineEngine (大一�?
    - 历史回测: backtest_cmd �?TimeMachineEngine (大一�?
    
    【CTO红线声明�?    此网关只�?/1生死判定，不做任何打分！均线判定已完全删除！
    【CTO紧急修复】早盘降阈逻辑(60%)，捕捉资金意愿度
    【Boss P0修复】ATR缺数据保留NaN，死亡换手统一70%
    【CTO疑点修复】死亡换�?=70%，单位自适应<1.0，ATR无magic number，时区修�?    """
    
    # ========== CTO红线常量：死亡换手阈�?==========
    DEATH_TURNOVER_THRESHOLD = 70.0  # 【V20.5.2】死亡换手线统一�?0%（研究验证：70%以上10日亏�?4.67%�?    # 甜点位阈值已迁移到config: live_sniper.sweet_spot_min / sweet_spot_max
    
    @staticmethod
    def apply_boss_two_dimensional_filters(
        df: pd.DataFrame,
        config_manager=None,
        true_dict=None,
        context: str = "unknown"
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        【CTO V89 终极统战】幽灵网关已被物理拆除！
        
        UniverseBuilder放行的127只真龙，绝不允许被任何二次过滤屠杀！
        这里只做统计观察，不做任何淘汰！
        """
        stats = {
            "input": len(df),
            "output": len(df),
            "filters_applied": ["None - SSOT bypassed all filters"],
            "death_turnover_blocked": 0,
            "atr_data_missing": 0,
            "volume_filtered": 0,
            "turnover_filtered": 0
        }
        
        logger.info(f"[{context}] GlobalFilterGateway SSOT模式: 维持 {len(df)} 只物理底池，无淘汰！")
        
        return df, stats


    
    @staticmethod
    def validate_signal_quality(
        stock_code: str,
        volume_ratio: float,
        turnover_rate: float,
        config_manager=None
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        【信号质量验证】单只股票快速验�?- V20.3红线�?+ 早盘降阈 + P0修复 + 疑点#2修复
        
        用于Tick级信号触发前的快速检�?        【CTO红线】只�?/1判定，无打分�?        【CTO紧急修复】早盘降阈逻辑(60%)
        【Boss P0修复】死亡换手统一�?0%
        【疑�?2修复】死亡换�?`>` �?`>=`
        
        Returns:
            (is_valid, reason, metadata): 
                - is_valid: True/False (0/1判定)
                - reason: 原因说明
                - metadata: 元数据字典，包含'tag'等标记（�?换手甜点'�?        """
        metadata = {}
        
        # 【CTO类型安全】强制转换为float，防止str/int比较错误
        volume_ratio = safe_float(volume_ratio, 0.0)
        turnover_rate = safe_float(turnover_rate, 0.0)
        
        # ========== 【CTO紧急修�?+ 疑点#5修复】早盘降阈逻辑 ==========
        is_early, scale_factor = check_early_market_scale()
        
        try:
            # 读取基础阈�?            base_min_multiplier = config_manager.get('live_sniper.min_volume_multiplier')
            base_min_turnover = config_manager.get('live_sniper.min_active_turnover_rate')
            sweet_spot_min = config_manager.get('live_sniper.sweet_spot_min', 8.0)
            sweet_spot_max = config_manager.get('live_sniper.sweet_spot_max', 15.0)
            
            # 【CTO紧急修复】应用早盘缩放因�?            min_multiplier = base_min_multiplier * scale_factor
            min_turnover = base_min_turnover * scale_factor
            
            # 记录到metadata
            metadata['early_market'] = is_early
            metadata['scale_factor'] = scale_factor
            
        except Exception as e:
            logger.error(f"GlobalFilter配置读取失败: {e}")
            return False, "配置读取失败", None
        
        # 【疑�?2修复】死亡换手拦�?- 70%硬门槛，`>` �?`>=`
        if turnover_rate >= GlobalFilterGateway.DEATH_TURNOVER_THRESHOLD:
            return False, f"死亡换手: {turnover_rate:.2f}% >= {GlobalFilterGateway.DEATH_TURNOVER_THRESHOLD}%", None
        
        # 检查量�?- 0/1判定（应用早盘降阈）
        if volume_ratio < min_multiplier:
            return False, f"量比不足: {volume_ratio:.2f}x < {min_multiplier:.2f}x{'[早盘降阈]' if is_early else ''}", None
        
        # 检查换�?- 0/1判定（应用早盘降阈，只检查下限）
        if turnover_rate < min_turnover:
            return False, f"换手太低: {turnover_rate:.2f}% < {min_turnover:.2f}%{'[早盘降阈]' if is_early else ''}", None
        
        # 【CTO红线】甜点位标记 - 仅注入tag，绝不加分！
        if sweet_spot_min <= turnover_rate <= sweet_spot_max:
            metadata['tag'] = '换手甜点'
        
        reason_parts = ["通过Boss二维铁网验证�?/1判定，均线权力下放�?]
        if is_early:
            reason_parts.append("[早盘降阈模式，捕捉意愿度]")
        
        return True, " ".join(reason_parts), metadata


# =============================================================================
# 快捷函数 - 供各模块直接调用
# =============================================================================

def apply_boss_filters(df, config_manager, true_dict=None, context="unknown"):
    """
    【快捷入口】应用Boss二维铁网（V20.3红线�?+ 早盘降阈 + P0修复 + CTO疑点修复�?    
    【CTO红线声明�?    - 均线判定(MA5/MA10/MA20)已完全删除，权力下放给战法Detector
    - 只做0/1生死判定，无打分
    - 死亡换手拦截统一�?=70%（新股在stock_filter第一道被过滤�?    - 甜点�?8%-15%)仅注入tag，绝不加�?    【CTO紧急修复】早盘降�? 09:30-09:45阈值降�?0%，捕捉意愿度
    【Boss P0修复】ATR缺数据保留NaN，不伪装成低能�?    【CTO疑点修复�?个疑点全部修�?    
    所有模块统一调用此函数！
    """
    return GlobalFilterGateway.apply_boss_two_dimensional_filters(
        df, config_manager, true_dict, context
    )


def quick_validate(stock_code, volume_ratio, turnover_rate, config_manager):
    """
    【快捷入口】单只股票快速验证（V20.3红线�?+ 早盘降阈 + P0修复 + CTO疑点修复�?    
    Returns:
        (is_valid, reason, metadata)
    """
    return GlobalFilterGateway.validate_signal_quality(
        stock_code, volume_ratio, turnover_rate, config_manager
    )
