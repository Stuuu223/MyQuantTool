#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTO数据飞轮：特征提取器 (Feature Extractor)
==========================================
职责：读取黄金样本清单，在历史快照中计算原始物理量，输出结构化数据

设计原则：
1. 零魔法数字 - 所有计算基于原始物理量
2. 严禁主观假设 - 不预设log10等公式
3. 数据驱动 - 让真实样本分布说话

Author: AI开发专家团队 (CTO架构指令)
Date: 2026-03-10
Version: V1.0.0
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xtquant import xtdata

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeatureExtractor:
    """
    特征提取器 - 从历史数据提取原始物理量
    
    输入：golden_samples.csv (stock_code, date, label)
    输出：features.csv (market_cap, raw_sustain, MFE, etc.)
    """
    
    def __init__(self):
        self.samples = None
        self.features = []
        
    def load_samples(self, filepath: str = 'data/validation/golden_samples.csv') -> pd.DataFrame:
        """加载黄金样本清单"""
        self.samples = pd.read_csv(filepath)
        logger.info(f"[加载样本] 共{len(self.samples)}个样本")
        logger.info(f"  - 真龙(label=1): {(self.samples['label']==1).sum()}个")
        logger.info(f"  - 骗炮(label=0): {(self.samples['label']==0).sum()}个")
        return self.samples
    
    def get_float_volume(self, stock_code: str) -> Optional[float]:
        """
        获取流通股本（股）
        
        使用get_instrument_detail获取FloatVolume字段
        注意：get_instrument_detail返回的FloatVolume单位已经是股！
        """
        try:
            # 使用get_instrument_detail获取流通股本
            detail = xtdata.get_instrument_detail(stock_code)
            if detail:
                float_volume = detail.get('FloatVolume', 0) or 0
                if float_volume > 0:
                    return float(float_volume)
            
            # 备用方法：从全量快照获取（盘后可能没有）
            snapshot = xtdata.get_full_tick([stock_code])
            if snapshot and stock_code in snapshot:
                tick = snapshot[stock_code]
                float_volume = tick.get('floatVolume', 0) or tick.get('FloatVolume', 0) or 0
                if float_volume > 0:
                    return float(float_volume)
                    
        except Exception as e:
            logger.warning(f"[获取流通股本失败] {stock_code}: {e}")
        return None
    
    def get_tick_data(self, stock_code: str, date: str) -> Optional[pd.DataFrame]:
        """
        获取指定日期的Tick数据
        
        Args:
            stock_code: 股票代码
            date: 日期 'YYYYMMDD'
            
        Returns:
            DataFrame with columns: time, lastPrice, volume, amount
        """
        try:
            tick_data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume', 'amount'],
                stock_list=[stock_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if tick_data and stock_code in tick_data:
                df = tick_data[stock_code]
                if df.empty:
                    logger.warning(f"[Tick数据为空] {stock_code} {date}")
                    return None
                return df
            else:
                logger.warning(f"[无Tick数据] {stock_code} {date}")
                return None
                
        except Exception as e:
            logger.error(f"[获取Tick数据失败] {stock_code} {date}: {e}")
            return None
    
    def get_daily_data(self, stock_code: str, end_date: str, days: int = 20) -> Optional[pd.DataFrame]:
        """
        获取历史日K数据
        
        Args:
            stock_code: 股票代码
            end_date: 结束日期 'YYYYMMDD'
            days: 需要的天数
            
        Returns:
            DataFrame with columns: open, high, low, close, volume, amount
        """
        try:
            # 计算开始日期（往前推days*2天确保足够）
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            start_dt = end_dt - timedelta(days=days*2)
            start_date = start_dt.strftime('%Y%m%d')
            
            daily_data = xtdata.get_local_data(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=[stock_code],
                period='1d',
                start_time=start_date,
                end_time=end_date
            )
            
            if daily_data and stock_code in daily_data:
                df = daily_data[stock_code]
                if len(df) < days:
                    logger.warning(f"[日K数据不足] {stock_code} 需要{days}天，实际{len(df)}天")
                return df.tail(days)
            else:
                logger.warning(f"[无日K数据] {stock_code} {end_date}")
                return None
                
        except Exception as e:
            logger.error(f"[获取日K数据失败] {stock_code} {end_date}: {e}")
            return None
    
    def calculate_flow_metrics(self, tick_df: pd.DataFrame, date: str) -> Dict:
        """
        计算资金流指标（时空切片法）
        
        核心原则：不估算，只用真实Tick数据
        
        Returns:
            Dict: flow_5min, flow_15min, flow_30min等
        """
        if tick_df is None or tick_df.empty:
            return {}
        
        try:
            # 转换时间戳
            if 'time' in tick_df.columns:
                if pd.api.types.is_numeric_dtype(tick_df['time']):
                    tick_df['datetime'] = pd.to_datetime(tick_df['time'], unit='ms') + pd.Timedelta(hours=8)
                    tick_df['time_str'] = tick_df['datetime'].dt.strftime('%H:%M:%S')
                else:
                    tick_df['time_str'] = tick_df['time'].astype(str)
            
            # 提取amount字段（QMT的amount是累计值）
            if 'amount' not in tick_df.columns:
                return {}
            
            # 获取最后一个tick的累计金额作为全天成交额
            total_amount = tick_df['amount'].iloc[-1] if len(tick_df) > 0 else 0
            
            # 时空切片1：09:30-09:35（5分钟）
            df_5min = tick_df[(tick_df['time_str'] >= '09:30:00') & (tick_df['time_str'] <= '09:35:00')]
            flow_5min = df_5min['amount'].iloc[-1] if len(df_5min) > 0 else 0
            
            # 时空切片2：09:30-09:45（15分钟）
            df_15min = tick_df[(tick_df['time_str'] >= '09:30:00') & (tick_df['time_str'] <= '09:45:00')]
            flow_15min = df_15min['amount'].iloc[-1] if len(df_15min) > 0 else 0
            
            # 时空切片3：09:30-10:00（30分钟）
            df_30min = tick_df[(tick_df['time_str'] >= '09:30:00') & (tick_df['time_str'] <= '10:00:00')]
            flow_30min = df_30min['amount'].iloc[-1] if len(df_30min) > 0 else 0
            
            return {
                'total_amount': total_amount,
                'flow_5min': flow_5min,
                'flow_15min': flow_15min,
                'flow_30min': flow_30min,
                'flow_5min_pct': flow_5min / total_amount * 100 if total_amount > 0 else 0,
                'flow_15min_pct': flow_15min / total_amount * 100 if total_amount > 0 else 0,
            }
            
        except Exception as e:
            logger.error(f"[计算资金流失败] {date}: {e}")
            return {}
    
    def calculate_price_metrics(self, tick_df: pd.DataFrame) -> Dict:
        """
        计算价格指标
        
        注意：QMT Tick数据在竞价阶段(09:15-09:25) lastPrice=0
        需要过滤掉这些数据
        
        Returns:
            Dict: high, low, open, close, prev_close, amplitude_pct
        """
        if tick_df is None or tick_df.empty:
            return {}
        
        try:
            if 'lastPrice' not in tick_df.columns:
                return {}
            
            # 【CTO修复】过滤掉lastPrice=0的竞价数据
            trade_df = tick_df[tick_df['lastPrice'] > 0].copy()
            if trade_df.empty:
                logger.warning("[价格数据缺失] 所有lastPrice=0")
                return {}
            
            prices = trade_df['lastPrice']
            
            # 开盘价（第一笔有价格的tick）
            open_price = prices.iloc[0] if len(prices) > 0 else 0
            
            # 最高价、最低价、收盘价
            high_price = prices.max()
            low_price = prices.min()
            close_price = prices.iloc[-1] if len(prices) > 0 else 0
            
            # 振幅
            amplitude_pct = ((high_price - low_price) / low_price * 100) if low_price > 0 else 0
            
            # 价格动能（日内K线推力）
            price_momentum = ((close_price - low_price) / (high_price - low_price)) if high_price != low_price else 0.5
            
            return {
                'open_price': open_price,
                'high_price': high_price,
                'low_price': low_price,
                'close_price': close_price,
                'amplitude_pct': amplitude_pct,
                'price_momentum': price_momentum,
            }
            
        except Exception as e:
            logger.error(f"[计算价格指标失败]: {e}")
            return {}
    
    def calculate_historical_baseline(self, stock_code: str, date: str, lookback_days: int = 5) -> Dict:
        """
        计算历史基线（用于计算sustain_ratio）
        
        核心指标：过去N天的日均成交额
        """
        daily_df = self.get_daily_data(stock_code, date, days=lookback_days+5)
        
        if daily_df is None or len(daily_df) < lookback_days:
            return {'avg_amount_5d': 0, 'avg_volume_5d': 0}
        
        try:
            # 排除当天（最后一条），取前N天
            historical = daily_df.iloc[:-1].tail(lookback_days)
            
            avg_amount_5d = historical['amount'].mean() if 'amount' in historical.columns else 0
            avg_volume_5d = historical['volume'].mean() if 'volume' in historical.columns else 0
            
            return {
                'avg_amount_5d': avg_amount_5d,
                'avg_volume_5d': avg_volume_5d,
            }
            
        except Exception as e:
            logger.error(f"[计算历史基线失败] {stock_code} {date}: {e}")
            return {'avg_amount_5d': 0, 'avg_volume_5d': 0}
    
    def extract_features_for_sample(self, stock_code: str, date: str, label: int) -> Optional[Dict]:
        """
        为单个样本提取所有特征
        
        Returns:
            Dict: 包含所有物理量的字典，或None（数据缺失时）
        """
        logger.info(f"[提取特征] {stock_code} {date} label={label}")
        
        # 1. 获取流通股本
        float_volume = self.get_float_volume(stock_code)
        if float_volume is None or float_volume <= 0:
            logger.warning(f"[跳过] {stock_code} 流通股本获取失败")
            return None
        
        # 2. 获取Tick数据
        tick_df = self.get_tick_data(stock_code, date)
        if tick_df is None:
            logger.warning(f"[跳过] {stock_code} {date} Tick数据缺失")
            return None
        
        # 3. 计算价格指标
        price_metrics = self.calculate_price_metrics(tick_df)
        if not price_metrics:
            logger.warning(f"[跳过] {stock_code} {date} 价格指标计算失败")
            return None
        
        # 4. 计算资金流指标
        flow_metrics = self.calculate_flow_metrics(tick_df, date)
        
        # 5. 计算历史基线
        historical = self.calculate_historical_baseline(stock_code, date)
        
        # 6. 计算衍生指标
        close_price = price_metrics.get('close_price', 0)
        
        # 流通市值（元）
        float_market_cap = float_volume * close_price
        
        # 量纲升维检查（A股最小流通市值不可能<2亿）
        if float_market_cap > 0 and float_market_cap < 200_000_000:
            float_market_cap = float_market_cap * 10000
            logger.debug(f"[量纲升维] {stock_code} 识别为万股单位")
        
        # 净流入（简化：用flow_15min作为流入代理）
        net_inflow = flow_metrics.get('flow_15min', 0)
        
        # 流入比（流入/流通市值）
        inflow_ratio = (net_inflow / float_market_cap * 100) if float_market_cap > 0 else 0
        
        # MFE做功效率（振幅%/流入比）
        amplitude_pct = price_metrics.get('amplitude_pct', 0)
        mfe = (amplitude_pct / inflow_ratio) if inflow_ratio > 0 else 0
        
        # 历史安全中位数（用avg_amount_5d作为代理）
        safe_median = historical.get('avg_amount_5d', 0)
        
        # raw_sustain（当前15分钟净流入 / 历史安全中位数）
        raw_sustain = (flow_metrics.get('flow_15min', 0) / safe_median) if safe_median > 0 else 0
        
        # 量比
        total_volume = tick_df['volume'].iloc[-1] if 'volume' in tick_df.columns and len(tick_df) > 0 else 0
        avg_volume_5d = historical.get('avg_volume_5d', 0)
        volume_ratio = (total_volume / avg_volume_5d) if avg_volume_5d > 0 else 0
        
        # 组装特征字典
        features = {
            'stock_code': stock_code,
            'date': date,
            'label': label,
            
            # 核心物理量（原始，无量纲化）
            'float_market_cap': float_market_cap,
            'float_market_cap_yi': float_market_cap / 100_000_000,  # 亿元单位
            'net_inflow': net_inflow,
            'inflow_ratio_pct': inflow_ratio,
            'mfe': mfe,
            'raw_sustain': raw_sustain,
            'volume_ratio': volume_ratio,
            
            # 价格指标
            'open_price': price_metrics.get('open_price', 0),
            'high_price': price_metrics.get('high_price', 0),
            'low_price': price_metrics.get('low_price', 0),
            'close_price': close_price,
            'amplitude_pct': amplitude_pct,
            'price_momentum': price_metrics.get('price_momentum', 0),
            
            # 资金流指标
            'total_amount': flow_metrics.get('total_amount', 0),
            'flow_5min': flow_metrics.get('flow_5min', 0),
            'flow_15min': flow_metrics.get('flow_15min', 0),
            'flow_30min': flow_metrics.get('flow_30min', 0),
            'flow_5min_pct': flow_metrics.get('flow_5min_pct', 0),
            'flow_15min_pct': flow_metrics.get('flow_15min_pct', 0),
            
            # 历史基线
            'avg_amount_5d': safe_median,
            'avg_volume_5d': avg_volume_5d,
        }
        
        return features
    
    def extract_all_features(self) -> pd.DataFrame:
        """提取所有样本的特征"""
        if self.samples is None:
            logger.error("[错误] 请先调用load_samples()加载样本")
            return pd.DataFrame()
        
        self.features = []
        success_count = 0
        fail_count = 0
        
        for _, row in self.samples.iterrows():
            stock_code = row['stock_code']
            date = str(row['date'])
            label = row['label']
            
            features = self.extract_features_for_sample(stock_code, date, label)
            
            if features:
                self.features.append(features)
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"[特征提取完成] 成功:{success_count} 失败:{fail_count}")
        
        return pd.DataFrame(self.features)
    
    def save_features(self, filepath: str = 'data/validation/features.csv'):
        """保存特征到CSV"""
        if not self.features:
            logger.error("[错误] 没有特征数据可保存")
            return
        
        df = pd.DataFrame(self.features)
        df.to_csv(filepath, index=False)
        logger.info(f"[保存完成] {filepath} ({len(df)}行)")
        
        return df


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("CTO数据飞轮：特征提取器启动")
    logger.info("=" * 60)
    
    # 初始化提取器
    extractor = FeatureExtractor()
    
    # 加载样本
    extractor.load_samples()
    
    # 提取特征
    df = extractor.extract_all_features()
    
    if df.empty:
        logger.error("[错误] 没有成功提取任何特征")
        return
    
    # 保存特征
    extractor.save_features()
    
    # 输出统计
    logger.info("\n" + "=" * 60)
    logger.info("特征统计摘要")
    logger.info("=" * 60)
    
    # 真龙vs骗炮对比
    true_dragons = df[df['label'] == 1]
    traps = df[df['label'] == 0]
    
    logger.info(f"\n真龙样本数: {len(true_dragons)}")
    logger.info(f"骗炮样本数: {len(traps)}")
    
    # 关键特征对比
    key_features = ['float_market_cap_yi', 'inflow_ratio_pct', 'mfe', 'raw_sustain', 'volume_ratio']
    
    for feat in key_features:
        if feat in df.columns:
            true_mean = true_dragons[feat].mean()
            trap_mean = traps[feat].mean()
            logger.info(f"\n{feat}:")
            logger.info(f"  真龙均值: {true_mean:.2f}")
            logger.info(f"  骗炮均值: {trap_mean:.2f}")
            logger.info(f"  差异: {true_mean - trap_mean:.2f}")


if __name__ == '__main__':
    main()
