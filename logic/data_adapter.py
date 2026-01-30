#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据适配层 - 统一不同数据源的字段格式
让战法无缝切换 QMT / AkShare / EasyQuotation

Author: iFlow CLI
Date: 2026-01-30
Version: V1.0
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from logic.logger import get_logger
from logic.active_stock_filter import get_active_stock_filter

logger = get_logger(__name__)


class DataAdapter:
    """
    数据适配层

    功能:
    1. 统一字段名（中英文双重映射）
    2. 统一单位（涨跌幅% vs 小数，成交额元 vs 万元）
    3. 自动补充缺失字段（量比、换手率等）
    """

    # 字段映射表（旧字段名 -> 新字段名）
    FIELD_MAPPING = {
        # QMT/新格式 -> 战法常用格式
        '最新价': 'price',
        '昨收': 'close',
        '今开': 'open',
        '最高': 'high',
        '最低': 'low',
        '成交量': 'volume',
        '成交额': 'amount',
        '涨跌幅': 'change_pct',
        '换手率': 'turnover',
        '振幅': 'amplitude',
        '代码': 'code',
        '名称': 'name',

        # 反向映射
        'price': '最新价',
        'close': '昨收',
        'open': '今开',
        'high': '最高',
        'low': '最低',
        'volume': '成交量',
        'amount': '成交额',
        'change_pct': '涨跌幅',
        'turnover': '换手率',
        'amplitude': '振幅',
        'code': '代码',
        'name': '名称',
    }

    @staticmethod
    def normalize_dataframe(df: pd.DataFrame, source: str = 'qmt') -> pd.DataFrame:
        """
        标准化 DataFrame 字段

        Args:
            df: 原始 DataFrame
            source: 数据源类型 (qmt/akshare/easyquotation)

        Returns:
            标准化后的 DataFrame（同时包含中英文字段）
        """
        if df.empty:
            return df

        df = df.copy()

        # 1. 确保同时存在中英文字段
        for cn_field, en_field in DataAdapter.FIELD_MAPPING.items():
            if cn_field in df.columns and en_field not in df.columns:
                df[en_field] = df[cn_field]
            elif en_field in df.columns and cn_field not in df.columns:
                df[cn_field] = df[en_field]

        # 2. 统一涨跌幅单位（确保是百分比，不是小数）
        if '涨跌幅' in df.columns:
            # 🔥 改进判断：使用中位数而非最大值，更准确
            sample_val = df['涨跌幅'].abs().quantile(0.5)  # 使用中位数
            if sample_val < 1:  # 说明是小数形式
                df['涨跌幅'] = df['涨跌幅'] * 100
                df['change_pct'] = df['涨跌幅']
                logger.debug(f"✅ [DataAdapter] 涨跌幅已从小数转换为百分比格式")

        # 3. 统一成交额单位（确保是万元）
        # QMT 已经是万元，无需转换

        # 4. 补充常用派生字段
        if '最新价' in df.columns and '昨收' in df.columns:
            # 涨跌额
            df['涨跌额'] = df['最新价'] - df['昨收']
            df['change'] = df['涨跌额']

            # 涨跌幅（如果没有）
            if '涨跌幅' not in df.columns:
                df['涨跌幅'] = ((df['最新价'] - df['昨收']) / df['昨收']) * 100
                df['change_pct'] = df['涨跌幅']

        # 5. 补充其他常用字段的别名
        if 'price' in df.columns:
            df['now'] = df['price']  # EasyQuotation 风格
            df['最新'] = df['price']

        if 'change_pct' in df.columns:
            df['percent'] = df['change_pct']  # EasyQuotation 风格

        logger.debug(f"✅ [DataAdapter] 标准化完成，字段: {df.columns.tolist()}")

        return df

    @staticmethod
    def get_active_stocks_unified(
        limit: int = 200,
        min_change_pct: Optional[float] = None,
        max_change_pct: Optional[float] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        获取活跃股票（统一接口）

        返回的数据已标准化，可直接用于所有战法

        Args:
            limit: 返回数量
            min_change_pct: 最小涨幅（百分比，如 5.0 表示 5%）
            max_change_pct: 最大涨幅
            **kwargs: 其他参数透传给 ActiveStockFilter

        Returns:
            标准化的股票列表
        """
        filter_obj = get_active_stock_filter()

        # 获取原始数据
        stocks = filter_obj.get_active_stocks(
            limit=limit,
            min_change_pct=min_change_pct,
            max_change_pct=max_change_pct,
            **kwargs
        )

        if not stocks:
            return []

        # 转为 DataFrame 进行标准化
        df = pd.DataFrame(stocks)
        df = DataAdapter.normalize_dataframe(df, source='qmt')

        # 转回字典列表
        return df.to_dict('records')

    @staticmethod
    def get_stock_pool_for_strategy(
        strategy_name: str,
        **filters
    ) -> pd.DataFrame:
        """
        为特定战法获取股票池

        Args:
            strategy_name: 战法名称 (longtou/dixi/banlu/weipan)
            **filters: 过滤条件

        Returns:
            标准化的 DataFrame
        """
        # 根据战法类型设置默认过滤条件
        strategy_defaults = {
            'longtou': {  # 龙头战法
                'min_amplitude': 2.0,  # 🔥 降低振幅门槛
                'min_change_pct': 0.0,  # 🔥 降低涨幅门槛
                'only_20cm': False,
                'limit': 100
            },
            'dixi': {  # 低吸战法
                'min_change_pct': -10.0,  # 🔥 扩大跌幅范围
                'max_change_pct': 3.0,  # 🔥 扩大涨幅范围
                'min_amplitude': 2.0,  # 🔥 降低振幅门槛
                'limit': 100
            },
            'banlu': {  # 半路战法
                'min_change_pct': 0.0,  # 🔥 降低涨幅门槛
                'max_change_pct': 15.0,  # 🔥 扩大涨幅范围
                'min_amplitude': 2.0,  # 🔥 降低振幅门槛
                'only_20cm': False,  # 🔥 包含主板股票
                'limit': 50
            },
            'weipan': {  # 尾盘战法
                'min_amplitude': 2.0,  # 🔥 降低振幅门槛
                'limit': 100
            }
        }

        # 合并默认参数和用户参数
        params = strategy_defaults.get(strategy_name, {})
        params.update(filters)

        logger.info(f"🎯 [DataAdapter] 为战法 '{strategy_name}' 获取股票池，参数: {params}")

        # 获取标准化数据
        stocks = DataAdapter.get_active_stocks_unified(**params)

        if not stocks:
            logger.warning(f"⚠️ [DataAdapter] 战法 '{strategy_name}' 未获取到股票")
            return pd.DataFrame()

        df = pd.DataFrame(stocks)
        logger.info(f"✅ [DataAdapter] 战法 '{strategy_name}' 获取到 {len(df)} 只股票")

        return df


# 便捷函数
def get_stocks_for_longtou(**kwargs) -> pd.DataFrame:
    """龙头战法专用接口"""
    return DataAdapter.get_stock_pool_for_strategy('longtou', **kwargs)

def get_stocks_for_dixi(**kwargs) -> pd.DataFrame:
    """低吸战法专用接口"""
    return DataAdapter.get_stock_pool_for_strategy('dixi', **kwargs)

def get_stocks_for_banlu(**kwargs) -> pd.DataFrame:
    """半路战法专用接口"""
    return DataAdapter.get_stock_pool_for_strategy('banlu', **kwargs)

def get_stocks_for_weipan(**kwargs) -> pd.DataFrame:
    """尾盘战法专用接口"""
    return DataAdapter.get_stock_pool_for_strategy('weipan', **kwargs)