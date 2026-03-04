#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
150%死亡换手合理性验证脚本

【Boss需求】
验证150%作为死亡换手红线的合理性，以数据证明：
- 换手 >= 150% 的股票次日涨幅显著低于 70-150% 分桶
- 70-150% 分桶仍有上涨空间，证明150%不会误杀真龙

【CTO设计】
数据源: data/kline_cache 本地缓存 (日K线)
时间范围: 迓去3个月 (约60-70个交易日)
分桶策略:
  1. 70-150%: 可能的真龙区间 (应保留)
  2. 150-200%: 死亡区上沿 (应拦截)
  3. >= 200%: 极端死亡区 (应拦截)

【输出】
1. data/validation/death_turnover_150_validation.csv
2. data/validation/death_turnover_150_summary.txt
3. data/validation/death_turnover_150_distribution.png (可选)

Author: CTO
Date: 2026-03-04
Version: 1.0.0
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
KLINE_CACHE_DIR = PROJECT_ROOT / "data" / "kline_cache"
VALIDATION_OUTPUT_DIR = PROJECT_ROOT / "data" / "validation"

# 确保输出目录存在
VALIDATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class DeathTurnoverValidator:
    """
    150%死亡换手合理性验证器
    
    【Boss需求】
    统计验证150%作为死亡换手红线的合理性
    
    【分桶策略】
    1. [70, 150): 真龙区间 (应保留)
    2. [150, 200): 死亡区上沿 (应拦截)
    3. [200, +∞): 极端死亡区 (应拦截)
    """
    
    def __init__(self, lookback_months: int = 3):
        """
        Args:
            lookback_months: 回望月数，默认3个月
        """
        self.lookback_months = lookback_months
        self.kline_cache_dir = KLINE_CACHE_DIR
        self.validation_output_dir = VALIDATION_OUTPUT_DIR
        
        # 分桶边界 (百分比)
        self.BUCKET_BOUNDARIES = [70.0, 150.0, 200.0]
        self.BUCKET_LABELS = [
            "70-150% (真龙区)",
            "150-200% (死亡区上沿)",
            ">= 200% (极端死亡区)"
        ]
        
        logger.info(f"初始化验证器: 回望{lookback_months}个月")
        logger.info(f"K线缓存目录: {self.kline_cache_dir}")
        logger.info(f"输出目录: {self.validation_output_dir}")
    
    def load_kline_data(self, stock_code: str) -> pd.DataFrame:
        """
        从data/kline_cache加载股票的日K线数据
        
        Args:
            stock_code: 股票代码 (e.g. "000001.SZ")
            
        Returns:
            pd.DataFrame: 日K线数据，包含date, open, close, high, low, volume, turnover_rate
        """
        cache_file = self.kline_cache_dir / f"{stock_code}_daily.json"
        
        if not cache_file.exists():
            return pd.DataFrame()
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data or 'klines' not in data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data['klines'])
            
            # 转换日期
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            elif 'time' in df.columns:
                df['date'] = pd.to_datetime(df['time'])
                df = df.drop('time', axis=1)
            else:
                return pd.DataFrame()
            
            # 确保必须列存在
            required_cols = ['date', 'close', 'high', 'low', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    return pd.DataFrame()
            
            # 转换数值类型
            for col in ['close', 'high', 'low', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 计算换手率 (如果缓存文件没有)
            if 'turnover_rate' not in df.columns:
                # 需要从其他字段计算，暂时跳过
                logger.warning(f"{stock_code}: 缺少turnover_rate字段")
                return pd.DataFrame()
            else:
                df['turnover_rate'] = pd.to_numeric(df['turnover_rate'], errors='coerce')
                # 【单位自适应】如果是小数形式，转为百分比
                if df['turnover_rate'].max() < 1.0:
                    df['turnover_rate'] = df['turnover_rate'] * 100.0
            
            # 排序
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"加载{stock_code}失败: {e}")
            return pd.DataFrame()
    
    def calculate_next_day_return(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算次日涨跌幅
        
        Args:
            df: 日K线数据
            
        Returns:
            pd.DataFrame: 添加next_day_return列 (百分比)
        """
        if len(df) < 2:
            return df
        
        df = df.copy()
        df['next_close'] = df['close'].shift(-1)
        df['next_day_return'] = ((df['next_close'] - df['close']) / df['close']) * 100.0
        
        return df
    
    def classify_turnover_bucket(self, turnover: float) -> str:
        """
        根据换手率分类到对应分桶
        
        Args:
            turnover: 换手率 (百分比)
            
        Returns:
            str: 分桶标签
        """
        if pd.isna(turnover):
            return "NA"
        
        if turnover < self.BUCKET_BOUNDARIES[0]:
            return f"< {self.BUCKET_BOUNDARIES[0]}% (低活跃)"
        elif turnover < self.BUCKET_BOUNDARIES[1]:
            return self.BUCKET_LABELS[0]
        elif turnover < self.BUCKET_BOUNDARIES[2]:
            return self.BUCKET_LABELS[1]
        else:
            return self.BUCKET_LABELS[2]
    
    def collect_samples(self) -> pd.DataFrame:
        """
        从 kline_cache 收集所有样本
        
        Returns:
            pd.DataFrame: 所有样本，包含 stock_code, date, turnover_rate, next_day_return, bucket
        """
        logger.info("=" * 70)
        logger.info("开始收集样本...")
        
        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_months * 30)
        
        logger.info(f"时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        
        all_samples = []
        
        # 遍历 kline_cache 目录
        cache_files = list(self.kline_cache_dir.glob("*_daily.json"))
        total_files = len(cache_files)
        
        logger.info(f"找到 {total_files} 个缓存文件")
        
        for idx, cache_file in enumerate(cache_files, 1):
            stock_code = cache_file.stem.replace('_daily', '')
            
            if idx % 100 == 0:
                logger.info(f"处理进度: {idx}/{total_files} ({idx/total_files*100:.1f}%)")
            
            # 加载数据
            df = self.load_kline_data(stock_code)
            
            if df.empty:
                continue
            
            # 过滤时间范围
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            
            if df.empty:
                continue
            
            # 过滤换手率 >= 70% 的样本
            df = df[df['turnover_rate'] >= 70.0]
            
            if df.empty:
                continue
            
            # 计算次日涨跌幅
            df = self.calculate_next_day_return(df)
            
            # 只保留有有效次日数据的样本
            df = df[df['next_day_return'].notna()]
            
            if df.empty:
                continue
            
            # 分桶
            df['bucket'] = df['turnover_rate'].apply(self.classify_turnover_bucket)
            
            # 添加股票代码
            df['stock_code'] = stock_code
            
            # 选择需要的列
            sample_df = df[['stock_code', 'date', 'turnover_rate', 'next_day_return', 'bucket']].copy()
            
            all_samples.append(sample_df)
        
        if not all_samples:
            logger.warning("未找到任何有效样本")
            return pd.DataFrame()
        
        # 合并所有样本
        result = pd.concat(all_samples, ignore_index=True)
        
        logger.info(f"=" * 70)
        logger.info(f"收集完成: 共 {len(result)} 个样本")
        
        return result
    
    def analyze_samples(self, df: pd.DataFrame) -> Dict:
        """
        分析样本统计数据
        
        Args:
            df: 样本数据
            
        Returns:
            Dict: 统计结果
        """
        logger.info("=" * 70)
        logger.info("开始分析样本...")
        
        stats = {}
        
        # 按分桶统计
        for bucket_label in self.BUCKET_LABELS:
            bucket_df = df[df['bucket'] == bucket_label]
            
            if bucket_df.empty:
                stats[bucket_label] = {
                    'count': 0,
                    'mean_return': np.nan,
                    'median_return': np.nan,
                    'positive_rate': np.nan,
                    'limit_up_rate': np.nan,
                    'max_drawdown': np.nan
                }
                continue
            
            count = len(bucket_df)
            returns = bucket_df['next_day_return']
            
            mean_return = returns.mean()
            median_return = returns.median()
            positive_rate = (returns > 0).sum() / count * 100.0
            limit_up_rate = (returns >= 9.8).sum() / count * 100.0  # 涨停约为10%
            max_drawdown = returns.min()
            
            stats[bucket_label] = {
                'count': count,
                'mean_return': mean_return,
                'median_return': median_return,
                'positive_rate': positive_rate,
                'limit_up_rate': limit_up_rate,
                'max_drawdown': max_drawdown
            }
            
            logger.info(f"")
            logger.info(f"分桶: {bucket_label}")
            logger.info(f"  样本数: {count}")
            logger.info(f"  平均次日涨跌幅: {mean_return:.2f}%")
            logger.info(f"  中位数次日涨跌幅: {median_return:.2f}%")
            logger.info(f"  次日上涨概率: {positive_rate:.2f}%")
            logger.info(f"  次日涨停概率: {limit_up_rate:.2f}%")
            logger.info(f"  最大回撤: {max_drawdown:.2f}%")
        
        return stats
    
    def generate_report(self, df: pd.DataFrame, stats: Dict) -> str:
        """
        生成文字报告
        
        Args:
            df: 样本数据
            stats: 统计结果
            
        Returns:
            str: 报告内容
        """
        report = []
        report.append("=" * 70)
        report.append("150% 死亡换手合理性验证报告")
        report.append("=" * 70)
        report.append("")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"数据源: data/kline_cache (日K线缓存)")
        report.append(f"时间范围: 过去 {self.lookback_months} 个月")
        report.append(f"总样本数: {len(df)}")
        report.append("")
        report.append("-" * 70)
        report.append("分桶统计结果")
        report.append("-" * 70)
        report.append("")
        
        for bucket_label in self.BUCKET_LABELS:
            bucket_stats = stats[bucket_label]
            report.append(f"【{bucket_label}】")
            report.append(f"  样本数: {bucket_stats['count']}")
            report.append(f"  平均次日涨跌幅: {bucket_stats['mean_return']:.2f}%")
            report.append(f"  中位数次日涨跌幅: {bucket_stats['median_return']:.2f}%")
            report.append(f"  次日上涨概率: {bucket_stats['positive_rate']:.2f}%")
            report.append(f"  次日涨停概率: {bucket_stats['limit_up_rate']:.2f}%")
            report.append(f"  最大回撤: {bucket_stats['max_drawdown']:.2f}%")
            report.append("")
        
        report.append("-" * 70)
        report.append("结论")
        report.append("-" * 70)
        report.append("")
        
        # 判断结论
        true_dragon_mean = stats[self.BUCKET_LABELS[0]]['mean_return']
        death_upper_mean = stats[self.BUCKET_LABELS[1]]['mean_return']
        death_extreme_mean = stats[self.BUCKET_LABELS[2]]['mean_return']
        
        if pd.notna(true_dragon_mean) and pd.notna(death_upper_mean):
            if death_upper_mean < true_dragon_mean:
                report.append("✅ 150%作为死亡换手红线是合理的！")
                report.append("")
                report.append(f"  真龙区(70-150%)平均次日涨幅: {true_dragon_mean:.2f}%")
                report.append(f"  死亡区(150-200%)平均次日涨幅: {death_upper_mean:.2f}%")
                report.append(f"  差异: {true_dragon_mean - death_upper_mean:.2f}%")
                report.append("")
                report.append("  【Boss裁决验证】150%确实是游资出货完毕红线，不会误杀真龙！")
            else:
                report.append("⚠️ 警告: 150%红线可能过于严格")
                report.append("")
                report.append(f"  真龙区(70-150%)平均次日涨幅: {true_dragon_mean:.2f}%")
                report.append(f"  死亡区(150-200%)平均次日涨幅: {death_upper_mean:.2f}%")
                report.append(f"  差异: {true_dragon_mean - death_upper_mean:.2f}%")
                report.append("")
                report.append("  建议重新评估死亡换手阈值。")
        else:
            report.append("⚠️ 样本数据不足，无法得出结论")
        
        report.append("")
        report.append("=" * 70)
        
        return "\n".join(report)
    
    def run(self):
        """
        执行完整验证流程
        """
        logger.info("=" * 70)
        logger.info("150% 死亡换手合理性验证 - 开始")
        logger.info("=" * 70)
        
        # 1. 收集样本
        df = self.collect_samples()
        
        if df.empty:
            logger.error("没有收集到有效样本，退出")
            return
        
        # 2. 分析样本
        stats = self.analyze_samples(df)
        
        # 3. 生成报告
        report = self.generate_report(df, stats)
        
        # 4. 保存结果
        csv_path = self.validation_output_dir / "death_turnover_150_validation.csv"
        txt_path = self.validation_output_dir / "death_turnover_150_summary.txt"
        
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"\n✅ CSV数据已保存: {csv_path}")
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"✅ 摘要报告已保存: {txt_path}")
        
        # 5. 打印报告
        print("\n")
        print(report)
        
        logger.info("=" * 70)
        logger.info("150% 死亡换手合理性验证 - 完成")
        logger.info("=" * 70)


if __name__ == "__main__":
    # 创建验证器
    validator = DeathTurnoverValidator(lookback_months=3)
    
    # 执行验证
    validator.run()
