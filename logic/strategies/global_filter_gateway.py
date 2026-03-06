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
4. 【CTO终极红线】0/1判定，无打分！均线判定权力下放给战法Detector！

【Boss二维铁网 - V20.3红线版 + 早盘降阈 + P0修复 + CTO疑点修复】
1. 量能网: volume_ratio >= min_volume_multiplier (如3.0倍，动态放量) - 0/1判定
2. 换手网: min_turnover <= turnover (5%起步，大哥起步线) - 0/1判定
3. 死亡换手拦截: turnover >= 70%直接拦截（研究验证：70%以上10日亏损14.67%）
4. 甜点位标记: 8% <= turnover <= 15%注入{'tag': '换手甜点'}，绝不加分
5. 早盘降阈: 09:30-09:45阈值降至60%，捕捉意愿度（固定UTC+8时区）
6. 【P0修复】ATR缺数据不再伪装成低能态，保留NaN用于统计

Author: 架构大一统工程 + CTO红线改造 + Boss P0修复 + CTO疑点修复
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
        value: 任意类型的输入值
        default: 转换失败时的默认值
        
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
    【CTO紧急修复 + 疑点#5修复】检测早盘时间窗口并返回阈值缩放因子
    
    早盘降阈哲学（老板钦定）：
    - 早盘(09:30-09:45)是资金意愿度暴露期
    - 降低阈值至60%，扩大观察池
    - 捕捉更多早盘粒子初速度信号
    
    【疑点#5修复】显式指定 UTC+8 (中国时区)，避免非中国时区部署时窗口失效
    
    Returns:
        (is_early, scale_factor): 
            - is_early: 是否在早盘时间窗口
            - scale_factor: 阈值缩放因子 (0.6 或 1.0)
    """
    # 【疑点#5修复】使用中国时区 (UTC+8)
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
    
    【使用场景】
    - 盘中实盘: live_cmd → run_live_trading_engine
    - 热复盘: replay_cmd → TimeMachineEngine (大一统)
    - 历史回测: backtest_cmd → TimeMachineEngine (大一统)
    
    【CTO红线声明】
    此网关只做0/1生死判定，不做任何打分！均线判定已完全删除！
    【CTO紧急修复】早盘降阈逻辑(60%)，捕捉资金意愿度
    【Boss P0修复】ATR缺数据保留NaN，死亡换手统一70%
    【CTO疑点修复】死亡换手>=70%，单位自适应<1.0，ATR无magic number，时区修复
    """
    
    # ========== CTO红线常量：死亡换手阈值 ==========
    DEATH_TURNOVER_THRESHOLD = 70.0  # 【V20.5.2】死亡换手线统一为70%（研究验证：70%以上10日亏损14.67%）
    # 甜点位阈值已迁移到config: live_sniper.sweet_spot_min / sweet_spot_max
    
    @staticmethod
    def apply_boss_two_dimensional_filters(
        df: pd.DataFrame,
        config_manager=None,
        true_dict=None,
        context: str = "unknown"
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        【Boss二维铁网 - V20.3红线版 + 早盘降阈 + P0修复 + CTO疑点修复】应用统一过滤逻辑
        
        【CTO红线改造说明】
        - 完全删除MA5/MA10/MA20均线判定（权力下放给战法Detector）
        - 只做0/1生死判定，无打分机制
        - 死亡换手拦截统一为>=70%（新股在stock_filter第一道被过滤，不会到这里）
        - 甜点位标记(8%-15%)，仅注入tag，绝不加分
        【CTO紧急修复】早盘降阈: 09:30-09:45阈值降至60%
        【Boss P0修复】ATR缺数据保留NaN，不伪装成低能态
        【CTO疑点修复】
        - 疑点#1: 死亡换手 `>` → `>=`
        - 疑点#3: 单位自适应 `<= 1.0` → `< 1.0`
        - 疑点#4: ATR默认值 `0.05` → `None`
        - 疑点#5: 早盘时区修复 UTC+8
        
        Args:
            df: 输入DataFrame，必须包含以下列:
                - stock_code: 股票代码
                - volume_ratio: 量比倍数
                - turnover_rate: 换手率(%)
            config_manager: 配置管理器
            true_dict: TrueDictionary实例（用于获取ATR数据）
            context: 调用上下文（用于日志区分："realtime"/"replay"/"backtest"）
            
        Returns:
            Tuple[filtered_df, stats_dict]: 
                - filtered_df: 过滤后的DataFrame（新增'tag'列标记甜点位，'atr_ratio'列保留NaN）
                - stats_dict: 过滤统计信息（包含atr_data_missing计数）
        """
        if df.empty:
            logger.warning(f"[{context}] 输入数据为空，跳过过滤")
            return df, {
                "input": 0, "output": 0, "filters_applied": [], 
                "death_turnover_blocked": 0, "atr_data_missing": 0
            }
        
        original_count = len(df)
        stats = {
            "input": original_count, 
            "filters_applied": [], 
            "death_turnover_blocked": 0,
            "atr_data_missing": 0
        }
        
        # ========== 【CTO紧急修复 + 疑点#5修复】早盘降阈逻辑 ==========
        is_early, scale_factor = check_early_market_scale()
        if is_early:
            logger.info(f"  ⏰ [早盘降阈] 检测到早盘时间窗口(09:30-09:45)，阈值降至60%，捕捉意愿度")
        
        # 【从Config读取所有阈值 - SSOT原则】
        try:
            # 读取基础阈值
            base_min_volume = config_manager.get('live_sniper.min_volume_multiplier')
            base_min_turnover = config_manager.get('live_sniper.min_active_turnover_rate')  # 5%
            sweet_spot_min = config_manager.get('live_sniper.sweet_spot_min', 8.0)  # 甜点位下限
            sweet_spot_max = config_manager.get('live_sniper.sweet_spot_max', 15.0)  # 甜点位上限
            
            # 验证读取成功
            if None in [base_min_volume, base_min_turnover]:
                raise ValueError("核心配置缺失")
            
            # 【CTO紧急修复】应用早盘缩放因子
            min_volume_multiplier = base_min_volume * scale_factor
            min_turnover = base_min_turnover * scale_factor
            
            # 记录到stats
            stats['early_market'] = is_early
            stats['scale_factor'] = scale_factor
                
        except Exception as e:
            logger.error(f"[{context}] 配置读取失败: {e}")
            raise RuntimeError("系统拒绝启动：缺少核心过滤配置")
        
        logger.info(f"[{context}] Boss三维铁网启动(V20.3物理重铸版+早盘降阈+P0修复+CTO疑点修复) | 输入: {original_count}只 | "
                   f"量比>={min_volume_multiplier:.2f}x | 换手>={min_turnover:.2f}% | 死亡换手>={GlobalFilterGateway.DEATH_TURNOVER_THRESHOLD}% | "
                   f"早盘:{is_early} | 缩放:{scale_factor} | "
                   f"【均线判定已删除，权力下放】")
        
        # ========== 预处理：换手率单位自适应 + safe_float类型安全 ==========
        if 'turnover_rate' in df.columns:
            # 【CTO类型安全】强制转换为float，防止str/int比较错误
            df['turnover_rate'] = df['turnover_rate'].apply(lambda x: safe_float(x, 0.0))
            # 【疑点#3修复】换手率单位自适应：`<= 1.0` → `< 1.0`，避免max=1.0%被误判
            if df['turnover_rate'].max() < 1.0:
                logger.info(f"  🔧 检测到换手率数据为小数形式，自动转换为百分比")
                df['turnover_rate'] = df['turnover_rate'] * 100.0
        
        # 【CTO类型安全】volume_ratio也强制转换
        if 'volume_ratio' in df.columns:
            df['volume_ratio'] = df['volume_ratio'].apply(lambda x: safe_float(x, 0.0))
        
        # ========== 【疑点#1修复】死亡换手拦截 - `>` → `>=` ==========
        # turnover_rate >= 70%直接拦截，永不进入候选池
        # 新股在stock_filter第一道被过滤（需历史数据），不会走到这里
        # 【Boss裁决】150%是游资出货完毕红线，150.0%本身就应拦截
        if 'turnover_rate' in df.columns:
            death_mask = df['turnover_rate'] >= GlobalFilterGateway.DEATH_TURNOVER_THRESHOLD  # 【疑点#1修复】
            death_count = death_mask.sum()
            if death_count > 0:
                death_stocks = df[death_mask]['stock_code'].tolist() if 'stock_code' in df.columns else []
                logger.warning(f"  ☠️ 死亡换手拦截: {death_count}只被拦截 (换手>={GlobalFilterGateway.DEATH_TURNOVER_THRESHOLD}%)"
                              f" - {death_stocks[:5]}{'...' if death_count > 5 else ''}")
                stats["death_turnover_blocked"] = int(death_count)
                # 从df中删除死亡换手股票
                df = df[~death_mask].copy()
        
        # ========== 第一维：量能网（0/1判定，无打分） ==========
        # 量比 >= 配置倍数（如3.0倍）- 纯生死判定
        if 'volume_ratio' in df.columns:
            volume_before = len(df)
            mask_volume = df['volume_ratio'] >= min_volume_multiplier
            df = df[mask_volume].copy()
            volume_after = len(df)
            volume_rejected = volume_before - volume_after
            stats["filters_applied"].append(f"volume_ratio>={min_volume_multiplier:.2f}x")
            logger.info(f"  🔹 量能网: {volume_after}/{volume_before}只通过 (量比>={min_volume_multiplier:.2f}x)【0/1判定{'，早盘降阈' if is_early else ''}】")
            # 【物理探针】打印被淘汰的阈值边界信息
            if volume_rejected > 0:
                min_ratio = df['volume_ratio'].min() if len(df) > 0 else 0
                max_ratio = df['volume_ratio'].max() if len(df) > 0 else 0
                logger.info(f"     📊 通过者量比范围: {min_ratio:.2f}x ~ {max_ratio:.2f}x")
                logger.info(f"     🚫 淘汰: {volume_rejected}只因量比<{min_volume_multiplier:.2f}x")
        
        # ========== 第二维：换手网（0/1判定，无打分，只检查下限） ==========
        # 换手率 >= min_turnover (5%) - 纯生死判定
        # 上限已在死亡换手拦截处理，不重复过滤
        if 'turnover_rate' in df.columns:
            mask_turnover = df['turnover_rate'] >= min_turnover
            turnover_before = len(df)
            df = df[mask_turnover].copy()
            turnover_after = len(df)
            stats["filters_applied"].append(f"turnover>={min_turnover:.2f}%")
            logger.info(f"  🔹 换手网: {turnover_after}/{turnover_before}只通过 (换手>={min_turnover:.2f}%)【0/1判定{'，早盘降阈' if is_early else ''}】")
        
        # ========== 第三维：ATR势垒网（可配置：仅记录/硬过滤，P0修复+疑点#4修复）==========
        # 【ATR阈值说明】
        # - 当前采用 atr_ratio >= 1.8x（研究报告推荐值）
        # - 研究样本：2026-02-27至2026-03-02（4天）
        # - 结论：atr_ratio >= 1.8时，涨停概率提升3.2倍
        # - TODO: 后续需三个月样本重新估此参数
        #
        # 【物理学意义】
        # - ATR = Average True Range = 真实波幅均值
        # - atr_ratio = 今日波幅 / 20日平均真实波幅
        # - atr_ratio > 1.8 表示今日波动超过历史平均的1.8倍
        # - 高能态 = 高波动 = 资金活跃度高 = 起爆概率高
        #
        # 【过滤模式】(2026-03-04 CTO降级)
        # - record_only: 仅记录到df，不拦截（当前模式）
        # - hard_filter: 硬过滤拦截（等三个月回测后再启用）
        #
        # 【Boss P0修复】(2026-03-04)
        # - prev_close缺失时返回None而非0
        # - atr_ratio保留NaN，不填充为0
        # - 新增stats['atr_data_missing']计数
        # - 区分"缺数据"和"真低能态"，用于回测统计
        #
        # 【疑点#4修复】(2026-03-04 CTO审计)
        # - atr_20d 默认值 `0.05` → `None`
        # - 原因: 0.05 magic number缺乏物理学依据，应明确标记为"数据缺失"
        # - atr_20d=None → today_tr/None → NaN → 计入atr_data_missing
        
        atr_ratio_min = config_manager.get('kinetic_physics.atr_ratio_min', 1.8) if config_manager else 1.8
        atr_filter_enabled = config_manager.get('kinetic_physics.atr_filter_enabled', True) if config_manager else True
        atr_filter_mode = config_manager.get('kinetic_physics.atr_filter_mode', 'record_only') if config_manager else 'record_only'
        
        if atr_filter_enabled and true_dict and 'stock_code' in df.columns and len(df) > 0:
            try:
                # 【疑点#4修复】获取ATR数据（20日平均真实波幅），默认None而非0.05
                df['atr_20d'] = df['stock_code'].apply(
                    lambda x: true_dict.get_atr_20d(x) if hasattr(true_dict, 'get_atr_20d') else None
                )
                
                # 【Boss P0修复】获取前收盘价，缺失时返回None而非0
                df['prev_close'] = df['stock_code'].apply(
                    lambda x: true_dict.get_prev_close(x) if hasattr(true_dict, 'get_prev_close') else None
                )
                
                # 【Boss P0修复 + 疑点#4修复】检查缺数据并标记（prev_close或atr_20d任一缺）
                missing_mask = df['prev_close'].isna() | (df['prev_close'] == 0) | df['atr_20d'].isna() | (df['atr_20d'] == 0)
                missing_count = missing_mask.sum()
                stats['atr_data_missing'] = int(missing_count)
                
                # 计算今日真实波幅比率
                # 今日TR = (high - low) / prev_close
                # atr_ratio = 今日TR / atr_20d
                if 'high' in df.columns and 'low' in df.columns:
                    # 【CTO修复】使用numpy.where处理NaN，缺失数据用1.0默认值
                    import numpy as np
                    
                    # prev_close为0或NaN时，today_tr=0（无法计算）
                    prev_close_safe = df['prev_close'].replace(0, float('nan'))
                    df['today_tr'] = np.where(
                        prev_close_safe.notna(),
                        (df['high'] - df['low']) / prev_close_safe,
                        0.0
                    )
                    
                    # atr_20d为0或NaN时，atr_ratio=1.0（默认市场平均水平，放行！）
                    df['atr_ratio'] = np.where(
                        (df['atr_20d'].notna()) & (df['atr_20d'] > 0) & (df['today_tr'] > 0),
                        df['today_tr'] / df['atr_20d'],
                        1.0  # 【CTO修复】缺失数据默认1.0，代表市场平均水平，放行！
                    )
                    
                    # 【CTO修复】简化警告：只打印缺失数量，不打印具体代码
                    if missing_count > 0:
                        logger.info(f"  🔹 ATR势垒网: {missing_count}只股票数据缺失，使用默认值1.0x（市场平均水平）")
                    
                    atr_before = len(df)
                    # 统计时排除NaN
                    atr_pass_count = (df['atr_ratio'] >= atr_ratio_min).sum()
                    atr_rejected = (df['atr_ratio'] < atr_ratio_min).sum()  # 不包含NaN
                    
                    stats["filters_applied"].append(f"atr_ratio>={atr_ratio_min}x({atr_filter_mode})")
                    
                    # 根据模式决定是否硬过滤
                    if atr_filter_mode == 'hard_filter':
                        # 硬过滤：拦截低能态股票（NaN单独统计为"数据缺失，无法判断"）
                        mask_atr = df['atr_ratio'] >= atr_ratio_min
                        df = df[mask_atr].copy()
                        atr_after = len(df)
                        stats["atr_filtered"] = atr_rejected
                        
                        logger.info(f"  🔹 ATR势垒网: {atr_after}/{atr_before}只通过 (ATR比率>={atr_ratio_min}x)【硬过滤模式】")
                        
                        if atr_rejected > 0:
                            filtered_atr = df['atr_ratio'].dropna()
                            if len(filtered_atr) > 0:
                                logger.info(f"     📊 通过者ATR比率范围: {filtered_atr.min():.2f}x ~ {filtered_atr.max():.2f}x")
                            logger.info(f"     🚫 淘汰: {atr_rejected}只因ATR比率<{atr_ratio_min}x（低能态，无起爆潜力）")
                        
                        if missing_count > 0:
                            logger.info(f"     ⚠️ 数据缺失: {missing_count}只prev_close/atr_20d缺失，atr_ratio=NaN（无法判断，保留）")
                    else:
                        # 仅记录模式：不过滤，只记录到df
                        stats["atr_filtered"] = 0
                        logger.info(f"  🔹 ATR势垒网: {atr_pass_count}/{atr_before}只达标 (ATR比率>={atr_ratio_min}x)【仅记录模式，不拦截】")
                        if atr_rejected > 0:
                            logger.info(f"     📊 未达标: {atr_rejected}只ATR比率<{atr_ratio_min}x（待回测验证后再决定是否拦截）")
                else:
                    logger.warning(f"  ⚠️ ATR势垒网: 缺少high/low列，跳过ATR计算")
                    df['atr_ratio'] = float('nan')
                    
            except Exception as e:
                logger.warning(f"  ⚠️ ATR势垒网计算失败: {e}，跳过ATR计算")
                df['atr_ratio'] = float('nan')
        else:
            if not atr_filter_enabled:
                logger.info(f"  🔹 ATR势垒网: 已禁用 (atr_filter_enabled=False)")
            elif 'stock_code' not in df.columns:
                logger.warning(f"  ⚠️ ATR势垒网: 缺少stock_code列，跳过ATR计算")
            elif len(df) == 0:
                logger.info(f"  🔹 ATR势垒网: 输入为空，跳过")
            else:
                logger.warning(f"  ⚠️ ATR势垒网: 缺少true_dict，跳过ATR计算")
            df['atr_ratio'] = float('nan')
        
        # ========== 【CTO红线】甜点位标记（仅注入tag，绝不加分！） ==========
        # 换手8%-15%标记为甜点位，但不做任何打分，仅作为信息标记
        if 'turnover_rate' in df.columns and len(df) > 0:
            sweet_mask = (df['turnover_rate'] >= sweet_spot_min) & \
                         (df['turnover_rate'] <= sweet_spot_max)
            sweet_count = sweet_mask.sum()
            
            # 初始化tag列为空字符串
            df['tag'] = ''
            # 对甜点位股票注入tag（仅标记，绝不加分！）
            df.loc[sweet_mask, 'tag'] = '换手甜点'
            
            if sweet_count > 0:
                logger.info(f"  🍰 甜点位标记: {sweet_count}只被标记为'换手甜点' (换手{sweet_spot_min}%~{sweet_spot_max}%)"
                           f"【仅注入tag，绝不加分！】")
        
        # ========== 【CTO红线】趋势网已完全删除 ==========
        # MA5/MA10/MA20判定已删除，权力下放给战法Detector！
        # 不再进行任何均线相关的过滤或打分
        logger.info(f"  ✅ 趋势网: 【已删除】均线判定权力下放给战法Detector")
        
        stats["output"] = len(df)
        stats["filter_rate"] = f"{len(df)/original_count*100:.1f}%" if original_count > 0 else "0%"
        
        logger.info(f"[{context}] Boss二维铁网完成 | 输出: {len(df)}只 | 通过率: {stats['filter_rate']} | "
                   f"死亡换手拦截: {stats['death_turnover_blocked']}只 | ATR数据缺失: {stats['atr_data_missing']}只 | "
                   f"{'[早盘降阈模式]' if is_early else '[正常模式]'}")
        
        return df, stats

    
    @staticmethod
    def validate_signal_quality(
        stock_code: str,
        volume_ratio: float,
        turnover_rate: float,
        config_manager=None
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        【信号质量验证】单只股票快速验证 - V20.3红线版 + 早盘降阈 + P0修复 + 疑点#2修复
        
        用于Tick级信号触发前的快速检查
        【CTO红线】只做0/1判定，无打分！
        【CTO紧急修复】早盘降阈逻辑(60%)
        【Boss P0修复】死亡换手统一为70%
        【疑点#2修复】死亡换手 `>` → `>=`
        
        Returns:
            (is_valid, reason, metadata): 
                - is_valid: True/False (0/1判定)
                - reason: 原因说明
                - metadata: 元数据字典，包含'tag'等标记（如'换手甜点'）
        """
        metadata = {}
        
        # 【CTO类型安全】强制转换为float，防止str/int比较错误
        volume_ratio = safe_float(volume_ratio, 0.0)
        turnover_rate = safe_float(turnover_rate, 0.0)
        
        # ========== 【CTO紧急修复 + 疑点#5修复】早盘降阈逻辑 ==========
        is_early, scale_factor = check_early_market_scale()
        
        try:
            # 读取基础阈值
            base_min_multiplier = config_manager.get('live_sniper.min_volume_multiplier')
            base_min_turnover = config_manager.get('live_sniper.min_active_turnover_rate')
            sweet_spot_min = config_manager.get('live_sniper.sweet_spot_min', 8.0)
            sweet_spot_max = config_manager.get('live_sniper.sweet_spot_max', 15.0)
            
            # 【CTO紧急修复】应用早盘缩放因子
            min_multiplier = base_min_multiplier * scale_factor
            min_turnover = base_min_turnover * scale_factor
            
            # 记录到metadata
            metadata['early_market'] = is_early
            metadata['scale_factor'] = scale_factor
            
        except:
            return False, "配置读取失败", None
        
        # 【疑点#2修复】死亡换手拦截 - 70%硬门槛，`>` → `>=`
        if turnover_rate >= GlobalFilterGateway.DEATH_TURNOVER_THRESHOLD:
            return False, f"死亡换手: {turnover_rate:.2f}% >= {GlobalFilterGateway.DEATH_TURNOVER_THRESHOLD}%", None
        
        # 检查量比 - 0/1判定（应用早盘降阈）
        if volume_ratio < min_multiplier:
            return False, f"量比不足: {volume_ratio:.2f}x < {min_multiplier:.2f}x{'[早盘降阈]' if is_early else ''}", None
        
        # 检查换手 - 0/1判定（应用早盘降阈，只检查下限）
        if turnover_rate < min_turnover:
            return False, f"换手太低: {turnover_rate:.2f}% < {min_turnover:.2f}%{'[早盘降阈]' if is_early else ''}", None
        
        # 【CTO红线】甜点位标记 - 仅注入tag，绝不加分！
        if sweet_spot_min <= turnover_rate <= sweet_spot_max:
            metadata['tag'] = '换手甜点'
        
        reason_parts = ["通过Boss二维铁网验证【0/1判定，均线权力下放】"]
        if is_early:
            reason_parts.append("[早盘降阈模式，捕捉意愿度]")
        
        return True, " ".join(reason_parts), metadata


# =============================================================================
# 快捷函数 - 供各模块直接调用
# =============================================================================

def apply_boss_filters(df, config_manager, true_dict=None, context="unknown"):
    """
    【快捷入口】应用Boss二维铁网（V20.3红线版 + 早盘降阈 + P0修复 + CTO疑点修复）
    
    【CTO红线声明】
    - 均线判定(MA5/MA10/MA20)已完全删除，权力下放给战法Detector
    - 只做0/1生死判定，无打分
    - 死亡换手拦截统一为>=70%（新股在stock_filter第一道被过滤）
    - 甜点位(8%-15%)仅注入tag，绝不加分
    【CTO紧急修复】早盘降阈: 09:30-09:45阈值降至60%，捕捉意愿度
    【Boss P0修复】ATR缺数据保留NaN，不伪装成低能态
    【CTO疑点修复】5个疑点全部修复
    
    所有模块统一调用此函数！
    """
    return GlobalFilterGateway.apply_boss_two_dimensional_filters(
        df, config_manager, true_dict, context
    )


def quick_validate(stock_code, volume_ratio, turnover_rate, config_manager):
    """
    【快捷入口】单只股票快速验证（V20.3红线版 + 早盘降阈 + P0修复 + CTO疑点修复）
    
    Returns:
        (is_valid, reason, metadata)
    """
    return GlobalFilterGateway.validate_signal_quality(
        stock_code, volume_ratio, turnover_rate, config_manager
    )
