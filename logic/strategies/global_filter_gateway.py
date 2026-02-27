#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GlobalFilterGateway - 全局过滤网关

【架构大一统核心组件】
解决"踢一脚动一脚"问题：实盘和回放必须走同一套过滤逻辑！

【设计原则】
1. DRY原则 - 所有过滤逻辑集中于此，禁止分散在各个方法中
2. SSOT原则 - 所有阈值从Config读取，零硬编码
3. 统一入口 - 无论是盘中实盘、盘后回放、历史回测，都必须调用此网关
<<<<<<< HEAD

【Boss三维铁网】
1. 趋势网: MA5 >= MA10 且 Close >= MA20 (过滤布朗运动)
2. 量能网: volume_ratio >= min_volume_multiplier (如1.5倍，动态放量)
3. 换手网: min_turnover <= turnover <= max_turnover (5%~60%，大哥起步线+死亡熔断)

Author: 架构大一统工程
Date: 2026-02-26
Version: 1.0.0
=======
4. 【CTO终极红线】0/1判定，无打分！均线判定权力下放给战法Detector！

【Boss二维铁网 - V20.2红线版】
1. 量能网: volume_ratio >= min_volume_multiplier (如1.5倍，动态放量) - 0/1判定
2. 换手网: min_turnover <= turnover <= max_turnover (5%~60%，大哥起步线+死亡熔断) - 0/1判定
3. 【删除】趋势网(MA5/MA10/MA20) - 完全删除，权力下放给战法Detector
4. 【新增】死亡换手拦截: turnover > 70%直接拦截
5. 【新增】甜点位标记: 8% <= turnover <= 15%注入{'tag': '换手甜点'}，绝不加分

Author: 架构大一统工程 + CTO红线改造
Date: 2026-02-27
Version: 2.0.0
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class GlobalFilterGateway:
    """
    全局过滤网关 - 统一所有选股过滤逻辑
    
    【使用场景】
    - 盘中实盘: _catch_up_mid_day() 必须调用
    - 盘后回放: replay_today_signals() 必须调用  
    - 历史回测: backtest_engine 必须调用
<<<<<<< HEAD
    """
    
    @staticmethod
    def apply_boss_three_dimensional_filters(
=======
    
    【CTO红线声明】
    此网关只做0/1生死判定，不做任何打分！均线判定已完全删除！
    """
    
    # ========== CTO红线常量：死亡换手阈值 ==========
    DEATH_TURNOVER_THRESHOLD = 70.0  # 死亡换手线70%
    SWEET_SPOT_MIN = 8.0  # 甜点位下限8%
    SWEET_SPOT_MAX = 15.0  # 甜点位上限15%
    
    @staticmethod
    def apply_boss_two_dimensional_filters(
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
        df: pd.DataFrame,
        config_manager=None,
        true_dict=None,
        context: str = "unknown"
    ) -> Tuple[pd.DataFrame, Dict]:
        """
<<<<<<< HEAD
        【Boss三维铁网】应用统一过滤逻辑
=======
        【Boss二维铁网 - V20.2红线版】应用统一过滤逻辑
        
        【CTO红线改造说明】
        - 完全删除MA5/MA10/MA20均线判定（权力下放给战法Detector）
        - 只做0/1生死判定，无打分机制
        - 新增死亡换手拦截(>70%)
        - 新增甜点位标记(8%-15%)，仅注入tag，绝不加分
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
        
        Args:
            df: 输入DataFrame，必须包含以下列:
                - stock_code: 股票代码
                - volume_ratio: 量比倍数
                - turnover_rate: 换手率(%)
<<<<<<< HEAD
                - ma5, ma10, ma20: 均线数据（可选，如有则检查趋势）
                - price, prev_close: 价格和昨收（可选）
            config_manager: 配置管理器
            true_dict: TrueDictionary实例（用于获取均线数据）
=======
                - 【删除】ma5, ma10, ma20: 不再检查
            config_manager: 配置管理器
            true_dict: TrueDictionary实例（用于获取均线数据）【已废弃】
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
            context: 调用上下文（用于日志区分："realtime"/"replay"/"backtest"）
            
        Returns:
            Tuple[filtered_df, stats_dict]: 
<<<<<<< HEAD
                - filtered_df: 过滤后的DataFrame
=======
                - filtered_df: 过滤后的DataFrame（新增'tag'列标记甜点位）
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
                - stats_dict: 过滤统计信息
        """
        if df.empty:
            logger.warning(f"[{context}] 输入数据为空，跳过过滤")
<<<<<<< HEAD
            return df, {"input": 0, "output": 0, "filters_applied": []}
        
        original_count = len(df)
        stats = {"input": original_count, "filters_applied": []}
=======
            return df, {"input": 0, "output": 0, "filters_applied": [], "death_turnover_blocked": 0}
        
        original_count = len(df)
        stats = {"input": original_count, "filters_applied": [], "death_turnover_blocked": 0}
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
        
        # 【从Config读取所有阈值 - SSOT原则】
        try:
            min_volume_multiplier = config_manager.get('live_sniper.min_volume_multiplier')
            min_turnover = config_manager.get('live_sniper.min_active_turnover_rate')  # 5%
            max_turnover = config_manager.get('live_sniper.turnover_rate_max')  # 60%
            
            # 验证读取成功
            if None in [min_volume_multiplier, min_turnover, max_turnover]:
                raise ValueError("核心配置缺失")
                
        except Exception as e:
            logger.error(f"[{context}] 配置读取失败: {e}")
            raise RuntimeError("系统拒绝启动：缺少核心过滤配置")
        
<<<<<<< HEAD
        logger.info(f"[{context}] Boss三维铁网启动 | 输入: {original_count}只 | "
                   f"量比>={min_volume_multiplier}x | 换手{min_turnover}%~{max_turnover}%")
        
        # ========== 第一维：量能网 ==========
        # 量比 >= 配置倍数（如1.5倍）
=======
        logger.info(f"[{context}] Boss二维铁网启动(V20.2红线版) | 输入: {original_count}只 | "
                   f"量比>={min_volume_multiplier}x | 换手{min_turnover}%~{max_turnover}% | "
                   f"【均线判定已删除，权力下放】")
        
        # ========== 预处理：换手率单位自适应 ==========
        if 'turnover_rate' in df.columns:
            # 【Bug修复】换手率单位自适应：如果是小数(0.05)则转为百分比(5.0)
            if df['turnover_rate'].max() <= 1.0:
                logger.info(f"  🔧 检测到换手率数据为小数形式，自动转换为百分比")
                df['turnover_rate'] = df['turnover_rate'] * 100.0
        
        # ========== 【CTO红线】死亡换手拦截 ==========
        # turnover_rate > 70%直接拦截，永不进入候选池
        if 'turnover_rate' in df.columns:
            death_mask = df['turnover_rate'] > GlobalFilterGateway.DEATH_TURNOVER_THRESHOLD
            death_count = death_mask.sum()
            if death_count > 0:
                death_stocks = df[death_mask]['stock_code'].tolist() if 'stock_code' in df.columns else []
                logger.warning(f"  ☠️ 死亡换手拦截: {death_count}只被拦截 (换手>{GlobalFilterGateway.DEATH_TURNOVER_THRESHOLD}%)"
                              f" - {death_stocks[:5]}{'...' if death_count > 5 else ''}")
                stats["death_turnover_blocked"] = int(death_count)
                # 从df中删除死亡换手股票
                df = df[~death_mask].copy()
        
        # ========== 第一维：量能网（0/1判定，无打分） ==========
        # 量比 >= 配置倍数（如1.5倍）- 纯生死判定
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
        if 'volume_ratio' in df.columns:
            volume_before = len(df)
            mask_volume = df['volume_ratio'] >= min_volume_multiplier
            df = df[mask_volume].copy()
            volume_after = len(df)
            volume_rejected = volume_before - volume_after
            stats["filters_applied"].append(f"volume_ratio>={min_volume_multiplier}x")
<<<<<<< HEAD
            logger.info(f"  🔹 量能网: {volume_after}/{volume_before}只通过 (量比>={min_volume_multiplier}x)")
            # 【物理探针】打印被淘汰的阈值边界信息
            if volume_rejected > 0 and 'volume_ratio' in df.columns:
=======
            logger.info(f"  🔹 量能网: {volume_after}/{volume_before}只通过 (量比>={min_volume_multiplier}x)【0/1判定】")
            # 【物理探针】打印被淘汰的阈值边界信息
            if volume_rejected > 0:
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
                min_ratio = df['volume_ratio'].min() if len(df) > 0 else 0
                max_ratio = df['volume_ratio'].max() if len(df) > 0 else 0
                logger.info(f"     📊 通过者量比范围: {min_ratio:.2f}x ~ {max_ratio:.2f}x")
                logger.info(f"     🚫 淘汰: {volume_rejected}只因量比<{min_volume_multiplier}x")
        
<<<<<<< HEAD
        # ========== 第二维：换手网 ==========
        # 5% <= 换手率 <= 60%
        if 'turnover_rate' in df.columns:
            # 【Bug修复】换手率单位自适应：如果是小数(0.05)则转为百分比(5.0)
            if df['turnover_rate'].max() <= 1.0:
                logger.info(f"  🔧 检测到换手率数据为小数形式，自动转换为百分比")
                df['turnover_rate'] = df['turnover_rate'] * 100.0
            
            mask_turnover = (df['turnover_rate'] >= min_turnover) & (df['turnover_rate'] <= max_turnover)
            df = df[mask_turnover].copy()
            stats["filters_applied"].append(f"turnover_{min_turnover}~{max_turnover}%")
            logger.info(f"  🔹 换手网: {len(df)}只通过 (换手{min_turnover}%~{max_turnover}%)")
        
        # ========== 第三维：趋势网（如有数据） ==========
        # MA5 >= MA10 且 Close >= MA20
        if all(col in df.columns for col in ['ma5', 'ma10', 'ma20']):
            mask_trend = (df['ma5'] >= df['ma10']) & (df['price'] >= df['ma20'])
            df = df[mask_trend].copy()
            stats["filters_applied"].append("ma5>=ma10&price>=ma20")
            logger.info(f"  🔹 趋势网: {len(df)}只通过 (MA多头排列)")
        else:
            logger.debug(f"[{context}] 跳过趋势网检查（缺少均线数据）")
        
        stats["output"] = len(df)
        stats["filter_rate"] = f"{len(df)/original_count*100:.1f}%"
        
        logger.info(f"[{context}] Boss三维铁网完成 | 输出: {len(df)}只 | 通过率: {stats['filter_rate']}")
        
        return df, stats
=======
        # ========== 第二维：换手网（0/1判定，无打分） ==========
        # 5% <= 换手率 <= 60% - 纯生死判定
        if 'turnover_rate' in df.columns:
            mask_turnover = (df['turnover_rate'] >= min_turnover) & (df['turnover_rate'] <= max_turnover)
            turnover_before = len(df)
            df = df[mask_turnover].copy()
            turnover_after = len(df)
            stats["filters_applied"].append(f"turnover_{min_turnover}~{max_turnover}%")
            logger.info(f"  🔹 换手网: {turnover_after}/{turnover_before}只通过 (换手{min_turnover}%~{max_turnover}%)【0/1判定】")
        
        # ========== 【CTO红线】甜点位标记（仅注入tag，绝不加分！） ==========
        # 换手8%-15%标记为甜点位，但不做任何打分，仅作为信息标记
        if 'turnover_rate' in df.columns and len(df) > 0:
            sweet_mask = (df['turnover_rate'] >= GlobalFilterGateway.SWEET_SPOT_MIN) & \
                         (df['turnover_rate'] <= GlobalFilterGateway.SWEET_SPOT_MAX)
            sweet_count = sweet_mask.sum()
            
            # 初始化tag列为空字符串
            df['tag'] = ''
            # 对甜点位股票注入tag（仅标记，绝不加分！）
            df.loc[sweet_mask, 'tag'] = '换手甜点'
            
            if sweet_count > 0:
                logger.info(f"  🍰 甜点位标记: {sweet_count}只被标记为'换手甜点' (换手{GlobalFilterGateway.SWEET_SPOT_MIN}%~{GlobalFilterGateway.SWEET_SPOT_MAX}%)"
                           f"【仅注入tag，绝不加分！】")
        
        # ========== 【CTO红线】趋势网已完全删除 ==========
        # MA5/MA10/MA20判定已删除，权力下放给战法Detector！
        # 不再进行任何均线相关的过滤或打分
        logger.info(f"  ✅ 趋势网: 【已删除】均线判定权力下放给战法Detector")
        
        stats["output"] = len(df)
        stats["filter_rate"] = f"{len(df)/original_count*100:.1f}%" if original_count > 0 else "0%"
        
        logger.info(f"[{context}] Boss二维铁网完成 | 输出: {len(df)}只 | 通过率: {stats['filter_rate']} | "
                   f"死亡换手拦截: {stats['death_turnover_blocked']}只")
        
        return df, stats

>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
    
    @staticmethod
    def validate_signal_quality(
        stock_code: str,
        volume_ratio: float,
        turnover_rate: float,
        config_manager=None
<<<<<<< HEAD
    ) -> Tuple[bool, str]:
        """
        【信号质量验证】单只股票快速验证
        
        用于Tick级信号触发前的快速检查
        
        Returns:
            (is_valid, reason): 是否有效，原因说明
        """
=======
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        【信号质量验证】单只股票快速验证 - V20.2红线版
        
        用于Tick级信号触发前的快速检查
        【CTO红线】只做0/1判定，无打分！
        
        Returns:
            (is_valid, reason, metadata): 
                - is_valid: True/False (0/1判定)
                - reason: 原因说明
                - metadata: 元数据字典，包含'tag'等标记（如'换手甜点'）
        """
        metadata = {}
        
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
        try:
            min_multiplier = config_manager.get('live_sniper.min_volume_multiplier')
            min_turnover = config_manager.get('live_sniper.min_active_turnover_rate')
            max_turnover = config_manager.get('live_sniper.turnover_rate_max')
        except:
<<<<<<< HEAD
            return False, "配置读取失败"
        
        # 检查量比
        if volume_ratio < min_multiplier:
            return False, f"量比不足: {volume_ratio:.2f}x < {min_multiplier}x"
        
        # 检查换手
        if turnover_rate < min_turnover:
            return False, f"换手太低: {turnover_rate:.2f}% < {min_turnover}%"
        if turnover_rate > max_turnover:
            return False, f"死亡换手: {turnover_rate:.2f}% > {max_turnover}%"
        
        return True, "通过Boss三维铁网验证"
=======
            return False, "配置读取失败", None
        
        # 【CTO红线】死亡换手拦截 - 70%硬门槛
        if turnover_rate > GlobalFilterGateway.DEATH_TURNOVER_THRESHOLD:
            return False, f"死亡换手: {turnover_rate:.2f}% > {GlobalFilterGateway.DEATH_TURNOVER_THRESHOLD}%", None
        
        # 检查量比 - 0/1判定
        if volume_ratio < min_multiplier:
            return False, f"量比不足: {volume_ratio:.2f}x < {min_multiplier}x", None
        
        # 检查换手 - 0/1判定
        if turnover_rate < min_turnover:
            return False, f"换手太低: {turnover_rate:.2f}% < {min_turnover}%", None
        if turnover_rate > max_turnover:
            return False, f"换手超标: {turnover_rate:.2f}% > {max_turnover}%", None
        
        # 【CTO红线】甜点位标记 - 仅注入tag，绝不加分！
        if GlobalFilterGateway.SWEET_SPOT_MIN <= turnover_rate <= GlobalFilterGateway.SWEET_SPOT_MAX:
            metadata['tag'] = '换手甜点'
        
        return True, "通过Boss二维铁网验证【0/1判定，均线权力下放】", metadata
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)


# =============================================================================
# 快捷函数 - 供各模块直接调用
# =============================================================================

def apply_boss_filters(df, config_manager, true_dict=None, context="unknown"):
    """
<<<<<<< HEAD
    【快捷入口】应用Boss三维铁网
    
    所有模块统一调用此函数！
    """
    return GlobalFilterGateway.apply_boss_three_dimensional_filters(
=======
    【快捷入口】应用Boss二维铁网（V20.2红线版）
    
    【CTO红线声明】
    - 均线判定(MA5/MA10/MA20)已完全删除，权力下放给战法Detector
    - 只做0/1生死判定，无打分
    - 新增死亡换手拦截(>70%)
    - 甜点位(8%-15%)仅注入tag，绝不加分
    
    所有模块统一调用此函数！
    """
    return GlobalFilterGateway.apply_boss_two_dimensional_filters(
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
        df, config_manager, true_dict, context
    )


def quick_validate(stock_code, volume_ratio, turnover_rate, config_manager):
    """
<<<<<<< HEAD
    【快捷入口】单只股票快速验证
=======
    【快捷入口】单只股票快速验证（V20.2红线版）
    
    Returns:
        (is_valid, reason, metadata)
>>>>>>> 4ebbab7 (V20纯血架构重构：动能势能双轨Ratio化+战法分流+VWAP宽容)
    """
    return GlobalFilterGateway.validate_signal_quality(
        stock_code, volume_ratio, turnover_rate, config_manager
    )
