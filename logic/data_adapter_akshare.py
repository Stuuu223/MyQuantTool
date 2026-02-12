#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🏴‍☠️ [海盗适配器]：免费抓取东方财富实时资金流数据 (DDE)
用于为 V18.6 系统提供核心弹药，绕过 Tushare 积分限制。

功能：
- 获取单只股票的实时主力资金流向
- 计算乖离率 (Bias Rate)
- 从全市场资金流排名中快速提取目标股票数据
"""

import akshare as ak
import pandas as pd
from datetime import datetime
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class MoneyFlowAdapter:
    """
    🏴‍☠️ [海盗适配器]：免费抓取东方财富实时资金流数据 (DDE)
    用于为 V18.6 系统提供核心弹药，绕过 Tushare 积分限制。
    """

    # 缓存机制：避免频繁请求东方财富接口
    _rank_cache = None
    _rank_cache_time = None
    _cache_ttl = 10  # 缓存有效期（秒）

    @staticmethod
    def get_realtime_dde(stock_code):
        """
        获取单只股票的实时主力资金流向

        Args:
            stock_code: 股票代码（如 "600519" 或 "600519.SH"）

        Returns:
            dict: {
                'dde_net_amount': 主力净流入金额 (元),
                'scramble_degree': 主力净流入占比 (%),
                'super_big_order': 超大单净流入 (元),
                'big_order': 大单净流入 (元),
                'timestamp': 数据时间戳
            }
        """
        try:
            # 适配代码格式 (Akshare 需要 "600000" 这种，不需要后缀)
            clean_code = stock_code.split('.')[0]

            # 调用东方财富个股资金流接口
            # 注意：这个接口返回的是历史数据列表，我们需要取当天的最新一条
            # 某些接口在盘中会实时更新当日数据

            # 备用方案：直接抓取"个股资金流排名"接口，然后过滤出该股
            # 这样速度更快，不用一只只请求历史
            return MoneyFlowAdapter._fetch_from_rank_api(clean_code)

        except Exception as e:
            logger.error(f"DDE 数据抓取失败 {stock_code}: {e}")
            return None

    @staticmethod
    def _fetch_from_rank_api(target_code):
        """
        从全市场资金流排名中"捞"出目标股票（速度极快）

        Args:
            target_code: 目标股票代码（如 "600000"）

        Returns:
            dict: DDE 数据
        """
        try:
            current_time = datetime.now()

            # 检查缓存
            if (MoneyFlowAdapter._rank_cache is not None and
                MoneyFlowAdapter._rank_cache_time is not None):
                time_diff = (current_time - MoneyFlowAdapter._rank_cache_time).total_seconds()
                if time_diff < MoneyFlowAdapter._cache_ttl:
                    # 使用缓存
                    df = MoneyFlowAdapter._rank_cache
                else:
                    # 缓存过期，重新获取
                    df = MoneyFlowAdapter._fetch_rank_data()
            else:
                # 没有缓存，重新获取
                df = MoneyFlowAdapter._fetch_rank_data()

            if df is None or df.empty:
                return {
                    'dde_net_amount': 0,
                    'scramble_degree': 0,
                    'super_big_order': 0,
                    'big_order': 0,
                    'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')
                }

            # 过滤出目标股票
            row = df[df['代码'] == target_code]

            if row.empty:
                return {
                    'dde_net_amount': 0,
                    'scramble_degree': 0,
                    'super_big_order': 0,
                    'big_order': 0,
                    'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')
                }

            # 解析数据
            # 东方财富接口返回列名可能变动，需根据实际情况调整
            row_data = row.iloc[0]

            # 尝试不同的列名（兼容不同版本的接口）
            # 注意：实际的列名是 '今日主力净流入-净额'，不是 '今日主力净流入'
            main_net_flow = MoneyFlowAdapter._safe_get_float(row_data, ['今日主力净流入-净额', '今日主力净流入', '主力净流入-净额', '主力净流入'])
            main_net_pct = MoneyFlowAdapter._safe_get_float(row_data, ['今日主力净流入-净占比', '今日主力净流入占比', '主力净流入-净占比', '主力净流入占比'])
            super_big_order = MoneyFlowAdapter._safe_get_float(row_data, ['今日超大单净流入-净额', '今日超大单净流入', '超大单净流入-净额', '超大单净流入'])
            big_order = MoneyFlowAdapter._safe_get_float(row_data, ['今日大单净流入-净额', '今日大单净流入', '大单净流入-净额', '大单净流入'])

            return {
                'dde_net_amount': main_net_flow,
                'scramble_degree': main_net_pct,  # 抢筹度 = 净占比
                'super_big_order': super_big_order,
                'big_order': big_order,
                'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            logger.warning(f"Akshare 接口波动: {e}")
            return {
                'dde_net_amount': 0,
                'scramble_degree': 0,
                'super_big_order': 0,
                'big_order': 0,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    @staticmethod
    def _fetch_rank_data():
        """
        获取东方财富实时资金流榜单 (即时)
        🚀 V19.1 优化：添加超时和重试机制 + 🔥 V19.2 强制绕过代理

        Returns:
            pd.DataFrame: 资金流排名数据
        """
        import time
        import os  # 引入 os 模块

        max_retries = 3  # 最大重试次数
        retry_delay = 2  # 重试延迟（秒）

        # 1. 临时移除环境变量中的代理设置（这是解决 ProxyError 的关键）
        # 这一步是为了防止 requests 自动读取系统的 HTTP_PROXY
        original_http = os.environ.get('HTTP_PROXY')
        original_https = os.environ.get('HTTPS_PROXY')
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)

        try:
            for attempt in range(max_retries):
                try:
                    # 获取东方财富实时资金流榜单 (今日)
                    # 注意：ak.stock_individual_fund_flow_rank() 不支持 timeout 参数
                    df = ak.stock_individual_fund_flow_rank(indicator="今日")

                    # 更新缓存
                    MoneyFlowAdapter._rank_cache = df
                    MoneyFlowAdapter._rank_cache_time = datetime.now()

                    return df

                except Exception as e:
                    error_type = type(e).__name__
                    error_msg = str(e)

                    # 如果是连接错误，尝试重试
                    if attempt < max_retries - 1 and ('Connection' in error_msg or 'Timeout' in error_msg or '10054' in error_msg or 'Proxy' in error_msg):
                        logger.warning(f"获取资金流榜单失败（第{attempt + 1}次尝试）: {error_type}: {error_msg}")
                        logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        # 最后一次尝试失败或非连接错误，直接返回
                        logger.error(f"获取资金流榜单失败（已重试{max_retries}次）: {error_type}: {error_msg}")
                        return None
        finally:
            # 2. 无论成功失败，必须恢复环境变量，以免影响其他需要代理的组件（如 GitHub 推送）
            if original_http:
                os.environ['HTTP_PROXY'] = original_http
            if original_https:
                os.environ['HTTPS_PROXY'] = original_https

    @staticmethod
    def _safe_get_float(row_data, possible_keys):
        """
        安全地从行数据中获取浮点数（兼容不同列名和中文单位）

        Args:
            row_data: 行数据
            possible_keys: 可能的列名列表

        Returns:
            float: 浮点数，如果找不到则返回 0
        """
        for key in possible_keys:
            if key in row_data:
                try:
                    value = row_data[key]
                    if pd.isna(value):
                        return 0.0

                    # 处理字符串类型（可能包含中文单位）
                    if isinstance(value, str):
                        value = value.strip()
                        # 处理中文单位
                        if '亿' in value:
                            return float(value.replace('亿', '')) * 100000000
                        elif '万' in value:
                            return float(value.replace('万', '')) * 10000
                        else:
                            return float(value)

                    # 处理数值类型
                    return float(value)
                except (ValueError, TypeError, AttributeError):
                    continue
        return 0.0

    @staticmethod
    def calculate_ma_bias(stock_code, current_price):
        """
        ⚡ [V19.2 紧急熔断] 强制返回 0，禁止盘中请求历史数据。
        这是导致系统卡死和 IP 被封的罪魁祸首。
        
        原因：
        - 盘中对每只股票都请求历史K线数据（ak.stock_zh_a_hist）
        - 5472只股票 = 5472次网络请求
        - 东方财富防火墙判定为DDoS攻击，强制断开连接（ConnectionResetError 10054）
        - 程序傻傻重试，导致主线程彻底卡死
        
        解决方案：
        - 盘中直接返回0，不请求网络
        - 使用盘前预计算缓存（PreMarketCache）计算MA5
        - 公式：Realtime_MA5 = (Pre_Market_MA4 * 4 + Current_Price) / 5
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            
        Returns:
            float: 乖离率 (%) - 盘中强制返回0
        """
        # ⚡ V19.2 紧急熔断：盘中直接返回0，禁止网络请求
        return 0.0
    @staticmethod
    def batch_get_dde(stock_codes):
        """
        批量获取多只股票的 DDE 数据（使用缓存优化）

        Args:
            stock_codes: 股票代码列表

        Returns:
            dict: {stock_code: dde_data}
        """
        try:
            # 先获取全市场排名数据（只请求一次）
            df = MoneyFlowAdapter._fetch_rank_data()

            if df is None or df.empty:
                return {}

            result = {}

            # 批量过滤
            for stock_code in stock_codes:
                clean_code = stock_code.split('.')[0]
                row = df[df['代码'] == clean_code]

                if not row.empty:
                    row_data = row.iloc[0]

                    main_net_flow = MoneyFlowAdapter._safe_get_float(row_data, ['今日主力净流入', '主力净流入', '主力净流入-净额'])
                    main_net_pct = MoneyFlowAdapter._safe_get_float(row_data, ['今日主力净流入占比', '主力净流入占比', '主力净流入-净占比'])
                    super_big_order = MoneyFlowAdapter._safe_get_float(row_data, ['今日超大单净流入', '超大单净流入', '超大单净流入-净额'])
                    big_order = MoneyFlowAdapter._safe_get_float(row_data, ['今日大单净流入', '大单净流入', '大单净流入-净额'])

                    result[stock_code] = {
                        'dde_net_amount': main_net_flow,
                        'scramble_degree': main_net_pct,
                        'super_big_order': super_big_order,
                        'big_order': big_order,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                else:
                    # 没有找到数据，返回默认值
                    result[stock_code] = {
                        'dde_net_amount': 0,
                        'scramble_degree': 0,
                        'super_big_order': 0,
                        'big_order': 0,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

            return result

        except Exception as e:
            logger.error(f"批量获取 DDE 数据失败: {e}")
            return {}

    @staticmethod
    def clear_cache():
        """清除缓存"""
        MoneyFlowAdapter._rank_cache = None
        MoneyFlowAdapter._rank_cache_time = None
        logger.info("DDE 数据缓存已清除")