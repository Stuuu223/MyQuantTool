#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.13 Active Stock Filter - 活跃股筛选器
专门用于筛选活跃股票，避免扫描"僵尸股"
按成交额或涨幅排序，优先扫描主力战场

Author: iFlow CLI
Version: V19.13
"""

import pandas as pd
import akshare as ak
import os
from typing import List, Dict, Any, Optional
from logic.logger import get_logger

logger = get_logger(__name__)


class ActiveStockFilter:
    """
    V19.13 活跃股筛选器（Active Stock Filter）

    核心功能：
    1. 获取全市场实时行情（使用 AkShare，更稳定）
    2. 过滤停牌、无量、ST、退市股
    3. 按成交额或涨幅排序
    4. 返回前N只活跃股
    """

    def __init__(self):
        """初始化活跃股筛选器"""
        # 🚨 V19.13: 强制清理代理配置，防止连接池爆满
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            os.environ.pop(key, None)
        os.environ['NO_PROXY'] = '*'

    def get_active_stocks(
        self,
        limit: int = 200,
        sort_by: str = 'amount',
        min_change_pct: Optional[float] = None,
        max_change_pct: Optional[float] = None,
        exclude_st: bool = True,
        exclude_delisting: bool = True,
        min_volume: int = 0,
        skip_top: int = 30,
        min_amplitude: float = 3.0,
        only_20cm: bool = False  # 🆕 V19.13: 是否只扫描20cm标的
    ) -> List[Dict[str, Any]]:
        """
        获取活跃股票列表

        Args:
            limit: 返回股票数量
            sort_by: 排序方式，'amount'（成交额）或 'change_pct'（涨幅）
            min_change_pct: 最小涨幅（可选）
            max_change_pct: 最大涨幅（可选）
            exclude_st: 是否排除ST股
            exclude_delisting: 是否排除退市股
            min_volume: 最小成交量（手）
            skip_top: 跳过前N只大家伙（默认30，跳过茅台、中信证券等权重股）
            min_amplitude: 最小振幅（百分比，默认3%，过滤织布机行情）
            only_20cm: 是否只扫描20cm标的（300/688）

        Returns:
            list: 活跃股票列表
        """
        logger.info(f"🔍 正在筛选活跃股票池 (limit={limit}, sort_by={sort_by})...")

        try:
            # 1. 强制直连，防止代理干扰 AkShare
            os.environ['NO_PROXY'] = '*'

            # 2. 获取实时行情榜单 (东方财富源)
            df_active = ak.stock_zh_a_spot_em()

            if df_active is not None and not df_active.empty:
                logger.info(f"✅ 获取到 {len(df_active)} 只股票的行情数据")

                # 3. 数据清洗与排序
                # 确保成交额是数值类型
                if '成交额' in df_active.columns:
                    df_active['成交额'] = pd.to_numeric(df_active['成交额'], errors='coerce')
                    df_active = df_active.sort_values(by='成交额', ascending=False)

                # 过滤掉 ST 和 退市
                if exclude_st or exclude_delisting:
                    df_active = df_active[~df_active['名称'].str.contains('ST|退', na=False)]

                # 🆕 V19.13: 20cm标的筛选
                if only_20cm:
                    df_active = df_active[df_active['代码'].str.startswith(('300', '688'))]
                    logger.info(f"🎯 只扫描20cm标的，筛选后: {len(df_active)} 只")

                # 过滤掉北交所 (可选)
                # df_active = df_active[~df_active['代码'].str.startswith(('8', '4', '9'))]

                # 过滤涨幅范围
                if min_change_pct is not None or max_change_pct is not None:
                    if '涨跌幅' in df_active.columns:
                        df_active['涨跌幅'] = pd.to_numeric(df_active['涨跌幅'], errors='coerce')
                        if min_change_pct is not None:
                            df_active = df_active[df_active['涨跌幅'] >= min_change_pct]
                        if max_change_pct is not None:
                            df_active = df_active[df_active['涨跌幅'] <= max_change_pct]

                # 🆕 V19.13: 振幅过滤
                if min_amplitude > 0 and '最高' in df_active.columns and '最低' in df_active.columns:
                    df_active['最高'] = pd.to_numeric(df_active['最高'], errors='coerce')
                    df_active['最低'] = pd.to_numeric(df_active['最低'], errors='coerce')
                    df_active['今开'] = pd.to_numeric(df_active['今开'], errors='coerce')
                    df_active = df_active[df_active['今开'] > 0]
                    df_active['振幅'] = (df_active['最高'] - df_active['最低']) / df_active['今开'] * 100
                    df_active = df_active[df_active['振幅'] >= min_amplitude]

                # 🆕 V19.13: 跳过前N只大家伙
                skip_count = min(skip_top, len(df_active))
                df_active = df_active.iloc[skip_count:]

                # 取前 limit 个
                df_active = df_active.head(limit)

                # 转换为字典列表
                active_list = []
                for _, row in df_active.iterrows():
                    stock = {
                        'code': row['代码'],
                        'name': row['名称'],
                        'price': float(row.get('最新价', 0)) if pd.notna(row.get('最新价')) else 0.0,
                        'close': float(row.get('昨收', 0)) if pd.notna(row.get('昨收')) else 0.0,
                        'high': float(row.get('最高', 0)) if pd.notna(row.get('最高')) else 0.0,
                        'low': float(row.get('最低', 0)) if pd.notna(row.get('最低')) else 0.0,
                        'open': float(row.get('今开', 0)) if pd.notna(row.get('今开')) else 0.0,
                        'volume': int(row.get('成交量', 0)) if pd.notna(row.get('成交量')) else 0,
                        'amount': float(row.get('成交额', 0)) if pd.notna(row.get('成交额')) else 0.0,
                        'change_pct': float(row.get('涨跌幅', 0)) if pd.notna(row.get('涨跌幅')) else 0.0,
                        'turnover': float(row.get('换手率', 0)) if pd.notna(row.get('换手率')) else 0.0,
                        'amplitude': float(row.get('振幅', 0)) if '振幅' in row else 0.0
                    }
                    active_list.append(stock)

                logger.info(f"✅ 筛选出 {len(active_list)} 只活跃股 (Top {limit}, 跳过前{skip_count}只)")
                return active_list

        except Exception as e:
            logger.error(f"❌ 活跃股筛选失败: {e}")
            # 灾备：如果 AKShare 挂了，返回核心资产列表，保证有东西可扫
            logger.warning("🚑 启动灾备列表 (核心资产)")
            return [
                {'code': '600519', 'name': '贵州茅台', 'price': 0, 'close': 0, 'change_pct': 0, 'amount': 0},
                {'code': '300750', 'name': '宁德时代', 'price': 0, 'close': 0, 'change_pct': 0, 'amount': 0},
                {'code': '601127', 'name': '小康股份', 'price': 0, 'close': 0, 'change_pct': 0, 'amount': 0},
                {'code': '000001', 'name': '平安银行', 'price': 0, 'close': 0, 'change_pct': 0, 'amount': 0},
                {'code': '300059', 'name': '东方财富', 'price': 0, 'close': 0, 'change_pct': 0, 'amount': 0},
                {'code': '600036', 'name': '招商银行', 'price': 0, 'close': 0, 'change_pct': 0, 'amount': 0},
                {'code': '002594', 'name': '比亚迪', 'price': 0, 'close': 0, 'change_pct': 0, 'amount': 0}
            ]

        return []


# 便捷函数
_asf_instance = None

def get_active_stock_filter() -> ActiveStockFilter:
    """获取活跃股筛选器单例"""
    global _asf_instance
    if _asf_instance is None:
        _asf_instance = ActiveStockFilter()
    return _asf_instance


def get_active_stocks(
    limit: int = 200,
    sort_by: str = 'amount',
    min_change_pct: Optional[float] = None,
    max_change_pct: Optional[float] = None,
    exclude_st: bool = True,
    exclude_delisting: bool = True,
    min_volume: int = 0,
    skip_top: int = 30,
    min_amplitude: float = 3.0,
    only_20cm: bool = False
) -> List[Dict[str, Any]]:
    """
    便捷函数：获取活跃股票列表

    Args:
        limit: 返回股票数量
        sort_by: 排序方式，'amount'（成交额）或 'change_pct'（涨幅）
        min_change_pct: 最小涨幅（可选）
        max_change_pct: 最大涨幅（可选）
        exclude_st: 是否排除ST股
        exclude_delisting: 是否排除退市股
        min_volume: 最小成交量（手）
        skip_top: 跳过前N只大家伙（默认30）
        min_amplitude: 最小振幅（百分比，默认3%）
        only_20cm: 是否只扫描20cm标的

    Returns:
        list: 活跃股票列表
    """
    filter_obj = get_active_stock_filter()
    return filter_obj.get_active_stocks(
        limit=limit,
        sort_by=sort_by,
        min_change_pct=min_change_pct,
        max_change_pct=max_change_pct,
        exclude_st=exclude_st,
        exclude_delisting=exclude_delisting,
        min_volume=min_volume,
        skip_top=skip_top,
        min_amplitude=min_amplitude,
        only_20cm=only_20cm
    )