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
                        '代码': row['代码'],
                        '名称': row['名称'],
                        '最新价': float(row.get('最新价', 0)) if pd.notna(row.get('最新价')) else 0.0,
                        '昨收': float(row.get('昨收', 0)) if pd.notna(row.get('昨收')) else 0.0,
                        '最高': float(row.get('最高', 0)) if pd.notna(row.get('最高')) else 0.0,
                        '最低': float(row.get('最低', 0)) if pd.notna(row.get('最低')) else 0.0,
                        '今开': float(row.get('今开', 0)) if pd.notna(row.get('今开')) else 0.0,
                        '成交量': int(row.get('成交量', 0)) if pd.notna(row.get('成交量')) else 0,
                        '成交额': float(row.get('成交额', 0)) if pd.notna(row.get('成交额')) else 0.0,
                        '涨跌幅': float(row.get('涨跌幅', 0)) if pd.notna(row.get('涨跌幅')) else 0.0,
                        '换手率': float(row.get('换手率', 0)) if pd.notna(row.get('换手率')) else 0.0,
                        '振幅': float(row.get('振幅', 0)) if '振幅' in row else 0.0,
                        # 🔥 V19.17: 添加英文字段兼容（EasyQuotation 格式）
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
                        'now': float(row.get('最新价', 0)) if pd.notna(row.get('最新价')) else 0.0,  # EasyQuotation 兼容
                        'percent': float(row.get('涨跌幅', 0)) if pd.notna(row.get('涨跌幅')) else 0.0,  # EasyQuotation 兼容
                    }
                    active_list.append(stock)

                logger.info(f"✅ 筛选出 {len(active_list)} 只活跃股 (Top {limit}, 跳过前{skip_count}只)")
                return active_list

        except Exception as e:
            logger.error(f"❌ 活跃股筛选失败: {e}")
            # 🆕 V19.14: 灾备方案：使用 easyquotation 获取全市场行情
            logger.warning("🚑 AkShare 失败，切换到 easyquotation 获取全市场行情...")
            try:
                import easyquotation as eq
                quotation = eq.use('sina')

                # 从配置文件中获取股票代码列表
                from pathlib import Path
                import json
                config_path = Path(__file__).parent.parent / 'easyquotation' / 'stock_codes.conf'

                stock_codes = []
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        # 尝试解析为 JSON 格式
                        try:
                            data = json.loads(content)
                            if isinstance(data, dict) and 'stock' in data:
                                stock_codes = data['stock']
                            elif isinstance(data, list):
                                stock_codes = data
                        except json.JSONDecodeError:
                            # 如果不是 JSON，按行解析
                            stock_codes = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]

                    # 转换为 easyquotation 格式（sh 前缀）
                    stock_codes = [f"sh{code}" if code.startswith('6') else f"sz{code}" for code in stock_codes]

                if not stock_codes:
                    # 如果配置文件不存在或为空，使用核心资产
                    stock_codes = ['sh600519', 'sz300750', 'sh601127', 'sz000001', 'sz300059', 'sh600036', 'sz002594']

                logger.info(f"📊 使用 easyquotation 获取 {len(stock_codes)} 只股票的行情...")

                # 批量获取（分批处理，每次200只）
                active_list = []
                batch_size = 200

                for i in range(0, len(stock_codes), batch_size):
                    batch = stock_codes[i:i + batch_size]
                    try:
                        data = quotation.stocks(batch)

                        for code, info in data.items():
                            # 转换为统一格式
                            stock_code = code.replace('sh', '').replace('sz', '')
                            stock_name = info.get('name', '')

                            # 过滤 ST 和 退市股
                            if exclude_st or exclude_delisting:
                                if 'ST' in stock_name or '退' in stock_name:
                                    continue

                            # 计算涨幅
                            price = float(info.get('now', 0))
                            close = float(info.get('close', 0))
                            if close == 0:
                                continue

                            change_pct = ((price - close) / close) * 100

                            # 过滤涨幅范围
                            if min_change_pct is not None and change_pct < min_change_pct:
                                continue
                            if max_change_pct is not None and change_pct > max_change_pct:
                                continue

                            # 🆕 V19.14: 计算振幅（使用今开、最高、最低）
                            open_price = float(info.get('open', 0))
                            high = float(info.get('high', 0))
                            low = float(info.get('low', 0))

                            amplitude = 0
                            if open_price > 0:
                                amplitude = ((high - low) / open_price) * 100

                            # 过滤振幅
                            if min_amplitude > 0 and amplitude < min_amplitude:
                                continue

                            # 🆕 V19.14: 过滤 20cm 标的
                            if only_20cm and not stock_code.startswith(('300', '688')):
                                continue

                            stock = {
                                'code': stock_code,
                                'name': stock_name,
                                'price': price,
                                'close': close,
                                'high': high,
                                'low': low,
                                'open': open_price,
                                'volume': int(info.get('volume', 0)) if info.get('volume') else 0,
                                'amount': 0,  # easyquotation 没有成交额数据
                                'change_pct': change_pct,
                                'turnover': 0,  # easyquotation 没有换手率数据
                                'amplitude': amplitude
                            }
                            active_list.append(stock)

                        logger.info(f"✅ 批次 {i//batch_size + 1} 完成，获取 {len(data)} 只股票")

                    except Exception as batch_e:
                        logger.error(f"❌ 批次 {i//batch_size + 1} 获取失败: {batch_e}")
                        continue

                logger.info(f"✅ [灾备方案] 使用 easyquotation 成功获取 {len(active_list)} 只活跃股")

                # 按成交量排序
                if sort_by == 'amount' or sort_by == 'volume':
                    active_list.sort(key=lambda x: x['volume'], reverse=True)
                elif sort_by == 'change_pct':
                    active_list.sort(key=lambda x: x['change_pct'], reverse=True)

                # 取前 limit 个
                active_list = active_list[:limit]

                logger.info(f"✅ [灾备方案] 筛选出 {len(active_list)} 只活跃股 (Top {limit})")

                return active_list

            except Exception as backup_e:
                logger.error(f"❌ [灾备方案] easyquotation 也失败了: {backup_e}")
                # 最后的灾备：返回核心资产列表
                logger.warning("🚑 启动最后的灾备列表 (核心资产)")
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