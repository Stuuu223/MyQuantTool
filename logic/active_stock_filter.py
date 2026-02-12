#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.17 Active Stock Filter - 活跃股筛选器（QMT 核动力版）
专门用于筛选活跃股票，避免扫描"僵尸股"
按成交额或涨幅排序，优先扫描主力战场

🔥 V19.17 重大升级：
- 使用 QMT 获取全市场数据（毫秒级、稳定）
- 彻底消灭数据异构问题
- 保留所有现有过滤逻辑
- EasyQuotation 作为灾备方案

Author: iFlow CLI
Version: V19.17
"""

import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from logic.utils.logger import get_logger
from logic.utils.code_converter import CodeConverter

logger = get_logger(__name__)


class ActiveStockFilter:
    """
    V19.17 活跃股筛选器（Active Stock Filter - QMT Power）

    核心功能：
    1. 获取全市场实时行情（使用 QMT，毫秒级）
    2. 过滤停牌、无量、ST、退市股
    3. 按成交额或涨幅排序
    4. 返回前N只活跃股
    5. 支持振幅过滤、20cm标的筛选
    """

    def __init__(self):
        """初始化活跃股筛选器"""
        # 🚨 V19.17: 强制清理代理配置，防止连接池爆满
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            os.environ.pop(key, None)
        os.environ['NO_PROXY'] = '*'

        # 初始化 QMT 接口
        self.qmt_available = False
        self.xtdata = None
        self.code_converter = CodeConverter()

        try:
            from xtquant import xtdata
            self.xtdata = xtdata
            self.qmt_available = True
            logger.info("✅ [V19.17] QMT 数据接口已加载（活跃股筛选器）")
        except ImportError as e:
            logger.warning(f"⚠️ [V19.17] QMT 接口不可用: {e}")
            logger.warning(f"   将使用 EasyQuotation 作为灾备方案")

        # 🆕 添加股票信息管理器（用于补充股票名称）
        self.stock_info = None
        try:
            from logic.qmt_stock_info import get_qmt_stock_info
            self.stock_info = get_qmt_stock_info()
            logger.info("✅ [V19.17] 股票信息管理器已初始化")
        except Exception as e:
            logger.warning(f"⚠️ [V19.17] 股票信息管理器初始化失败: {e}")

    def _get_qmt_market_data(self) -> Optional[pd.DataFrame]:
        """
        🔥 V19.17: 使用 QMT 获取全市场数据

        Returns:
            DataFrame: 全市场股票数据
        """
        if not self.qmt_available:
            return None

        try:
            logger.info("📡 [V19.17] 使用 QMT 获取全市场数据...")

            # 🔥 使用 QMT 获取全市场股票列表
            stock_list = self.xtdata.get_stock_list_in_sector('沪深A股')

            if not stock_list:
                logger.warning("⚠️ [V19.17] QMT 未获取到股票列表")
                return None

            logger.info(f"📊 [V19.17] QMT 返回 {len(stock_list)} 只股票")

            # 转换为标准格式（去掉 .SH/.SZ 后缀）
            standard_codes = [self.code_converter.to_standard(code) for code in stock_list]

            # 🔥 批量获取全市场数据（使用 get_full_tick）
            # QMT 代码格式转换回去
            qmt_codes = [self.code_converter.to_qmt(code) for code in standard_codes]

            logger.info(f"⚡ [V19.17] 批量获取 {len(qmt_codes)} 只股票的实时数据...")

            # 获取全市场 tick 数据
            market_data = self.xtdata.get_full_tick(qmt_codes)

            if not market_data:
                logger.warning("⚠️ [V19.17] QMT 未获取到市场数据")
                return None

            logger.info(f"✅ [V19.17] QMT 成功获取 {len(market_data)} 只股票数据")

            # 🔥 V20.2: 尝试从 EasyQuotation 获取换手率数据（作为补充）
            turnover_rates = {}
            try:
                logger.info("⚡ [V20.2] 尝试从 EasyQuotation 获取换手率数据...")
                import easyquotation as eq
                eq_source = eq.use('tencent')
                
                # 批量获取股票列表
                std_codes = [self.code_converter.to_standard(code) for code in market_data.keys()]
                eq_data = eq_source.stocks(std_codes)
                
                if eq_data:
                    for std_code, eq_stock in eq_data.items():
                        if eq_stock and 'turnover' in eq_stock:
                            # EasyQuotation 的 turnover 是百分比，直接使用
                            turnover_rates[std_code] = eq_stock['turnover']
                
                logger.info(f"✅ [V20.2] 成功获取 {len(turnover_rates)} 只股票的换手率")
            except Exception as e:
                logger.warning(f"⚠️ [V20.2] 获取换手率失败: {e}")

            # 转换为 DataFrame
            stock_list = []
            for qmt_code, data in market_data.items():
                if not data:
                    continue

                # 转换为标准格式
                std_code = self.code_converter.to_standard(qmt_code)

                # 🔥 V19.17: 构造中文字段数据（与现有系统兼容）
                last_price = data.get('lastPrice', 0)
                last_close = data.get('lastClose', 0)
                open_price = data.get('open', 0)
                high_price = data.get('high', 0)
                low_price = data.get('low', 0)

                # 手动计算涨跌幅（QMT 不提供 pctChg 字段）
                pct_change = 0
                if last_close > 0:
                    pct_change = ((last_price - last_close) / last_close)

                # 🔥 修正：使用昨收价计算振幅（标准公式）
                amplitude = 0
                if last_close > 0:
                    amplitude = ((high_price - low_price) / last_close) * 100

                # 🔥 V20.2: 优先使用 EasyQuotation 的换手率，否则使用 0
                turnover_rate = turnover_rates.get(std_code, 0)

                stock = {
                    '代码': std_code,
                    '名称': '',  # 稍后批量补充
                    '最新价': last_price,
                    '昨收': last_close,
                    '今开': open_price,
                    '最高': high_price,
                    '最低': low_price,
                    '成交量': data.get('volume', 0) / 100,  # 股数 → 手数
                    '成交额': data.get('amount', 0) / 10000,  # 元 → 万元
                    '涨跌幅': pct_change * 100,  # 🔥 直接转为百分比（如 5.0 表示 5%）
                    '换手率': turnover_rate,  # 🔥 V20.2: 使用 EasyQuotation 的换手率
                    '振幅': amplitude,  # 🔥 修正后的振幅
                    # 🔥 V19.17: 添加英文字段兼容
                    'code': std_code,
                    'name': '',
                    'price': last_price,
                    'close': last_close,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'volume': data.get('volume', 0) / 100,
                    'amount': data.get('amount', 0) / 10000,
                    'change_pct': pct_change * 100,  # 🔥 英文字段也转为百分比
                    'turnover': turnover_rate,  # 🔥 V20.2: 使用 EasyQuotation 的换手率
                    'now': last_price,
                    'percent': pct_change * 100,  # 🔥 EasyQuotation 风格也转为百分比
                }

                stock_list.append(stock)

            df = pd.DataFrame(stock_list)

            # 🔥 批量补充股票名称
            if self.stock_info:
                df = self.stock_info.enrich_dataframe(df, code_column='代码')

            logger.info(f"✅ [V19.17] QMT 数据转换完成，共 {len(df)} 只股票（已补充名称）")

            return df

        except Exception as e:
            logger.error(f"❌ [V19.17] QMT 获取市场数据失败: {e}")
            return None

    def _get_easyquotation_market_data(self) -> Optional[pd.DataFrame]:
        """
        🆕 V19.17: 灾备方案 - 使用 EasyQuotation 获取全市场数据

        Returns:
            DataFrame: 全市场股票数据
        """
        try:
            logger.warning("🚑 [V19.17] QMT 失败，切换到 EasyQuotation 灾备方案...")

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

            logger.info(f"📊 [V19.17] 使用 EasyQuotation 获取 {len(stock_codes)} 只股票的行情...")

            # 批量获取（分批处理，每次200只）
            all_stocks = []
            batch_size = 200

            for i in range(0, len(stock_codes), batch_size):
                batch = stock_codes[i:i + batch_size]
                try:
                    data = quotation.stocks(batch)

                    for code, info in data.items():
                        # 转换为统一格式
                        stock_code = code.replace('sh', '').replace('sz', '')
                        stock_name = info.get('name', '')

                        # 计算涨幅
                        price = float(info.get('now', 0))
                        close = float(info.get('close', 0))
                        if close == 0:
                            continue

                        change_pct = ((price - close) / close) * 100

                        # 计算振幅
                        open_price = float(info.get('open', 0))
                        high = float(info.get('high', 0))
                        low = float(info.get('low', 0))

                        amplitude = 0
                        if open_price > 0:
                            amplitude = ((high - low) / open_price) * 100

                        stock = {
                            '代码': stock_code,
                            '名称': stock_name,
                            '最新价': price,
                            '昨收': close,
                            '今开': open_price,
                            '最高': high,
                            '最低': low,
                            '成交量': int(info.get('volume', 0)) if info.get('volume') else 0,
                            '成交额': 0,  # easyquotation 没有成交额数据
                            '涨跌幅': change_pct,
                            '换手率': 0,  # easyquotation 没有换手率数据
                            '振幅': amplitude,
                            # 英文字段
                            'code': stock_code,
                            'name': stock_name,
                            'price': price,
                            'close': close,
                            'open': open_price,
                            'high': high,
                            'low': low,
                            'volume': int(info.get('volume', 0)) if info.get('volume') else 0,
                            'amount': 0,
                            'change_pct': change_pct,
                            'turnover': 0,
                            'now': price,
                            'percent': change_pct,
                        }
                        all_stocks.append(stock)

                    logger.info(f"✅ [V19.17] 批次 {i//batch_size + 1} 完成，获取 {len(data)} 只股票")

                except Exception as batch_e:
                    logger.error(f"❌ [V19.17] 批次 {i//batch_size + 1} 获取失败: {batch_e}")
                    continue

            if not all_stocks:
                return None

            df = pd.DataFrame(all_stocks)
            logger.info(f"✅ [V19.17] EasyQuotation 数据获取完成，共 {len(df)} 只股票")

            return df

        except Exception as e:
            logger.error(f"❌ [V19.17] EasyQuotation 获取市场数据失败: {e}")
            return None

    def get_active_stocks(
        self,
        limit: int = 200,
        sort_by: str = 'amount',
        min_change_pct: Optional[float] = None,
        max_change_pct: Optional[float] = None,
        exclude_st: bool = True,
        exclude_delisting: bool = True,
        min_volume: int = 0,
        skip_top: int = 10,  # 🔥 V20.0: 从30降到10
        min_amplitude: float = 1.0,  # 🔥 V20.0: 从3.0降到1.0
        only_20cm: bool = False
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
        logger.info(f"🔍 [V19.17] 正在筛选活跃股票池 (limit={limit}, sort_by={sort_by})...")

        try:
            # 🔥 V19.17: 优先使用 QMT 获取全市场数据
            df_active = self._get_qmt_market_data()

            # 如果 QMT 失败，降级到 EasyQuotation
            if df_active is None or df_active.empty:
                logger.warning("⚠️ [V19.17] QMT 数据不可用，切换到 EasyQuotation...")
                df_active = self._get_easyquotation_market_data()

            if df_active is None or df_active.empty:
                logger.error("❌ [V19.17] 所有数据源均失败")
                return []

            logger.info(f"✅ [V19.17] 获取到 {len(df_active)} 只股票的行情数据")

            # ========================================================
            # 以下是现有的过滤逻辑（保持不变）
            # ========================================================

            # 3. 数据清洗与排序
            # 确保成交额是数值类型
            if '成交额' in df_active.columns:
                df_active['成交额'] = pd.to_numeric(df_active['成交额'], errors='coerce')
                df_active = df_active.sort_values(by='成交额', ascending=False)

            # 过滤掉 ST 和 退市
            if exclude_st or exclude_delisting:
                df_active = df_active[~df_active['名称'].str.contains('ST|退', na=False)]

            # 20cm标的筛选
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

            # 振幅过滤
            if min_amplitude > 0 and '振幅' in df_active.columns:
                df_active['振幅'] = pd.to_numeric(df_active['振幅'], errors='coerce')
                df_active = df_active[df_active['振幅'] >= min_amplitude]

            # 跳过前N只大家伙
            skip_count = min(skip_top, len(df_active))
            df_active = df_active.iloc[skip_count:]

            # 取前 limit 个
            df_active = df_active.head(limit)

            # 转换为字典列表
            active_list = df_active.to_dict('records')

            logger.info(f"✅ [V19.17] 筛选出 {len(active_list)} 只活跃股 (Top {limit}, 跳过前{skip_count}只)")
            return active_list

        except Exception as e:
            logger.error(f"❌ [V19.17] 活跃股筛选失败: {e}")
            # 最后的灾备：返回核心资产列表
            logger.warning("🚑 启动最后的灾备列表 (核心资产)")
            return [
                {'code': '600519', 'name': '贵州茅台', 'price': 0, 'close': 0, 'change_pct': 0, 'amount': 0,
                 '代码': '600519', '名称': '贵州茅台', '最新价': 0, '昨收': 0, '涨跌幅': 0, '成交额': 0},
                {'code': '300750', 'name': '宁德时代', 'price': 0, 'close': 0, 'change_pct': 0, 'amount': 0,
                 '代码': '300750', '名称': '宁德时代', '最新价': 0, '昨收': 0, '涨跌幅': 0, '成交额': 0},
                {'code': '601127', 'name': '小康股份', 'price': 0, 'close': 0, 'change_pct': 0, 'amount': 0,
                 '代码': '601127', '名称': '小康股份', '最新价': 0, '昨收': 0, '涨跌幅': 0, '成交额': 0},
                {'code': '000001', 'name': '平安银行', 'price': 0, 'close': 0, 'change_pct': 0, 'amount': 0,
                 '代码': '000001', '名称': '平安银行', '最新价': 0, '昨收': 0, '涨跌幅': 0, '成交额': 0},
                {'code': '300059', 'name': '东方财富', 'price': 0, 'close': 0, 'change_pct': 0, 'amount': 0,
                 '代码': '300059', '名称': '东方财富', '最新价': 0, '昨收': 0, '涨跌幅': 0, '成交额': 0},
            ]


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
    skip_top: int = 10,  # 🔥 V20.0: 从30降到10
    min_amplitude: float = 1.0,  # 🔥 V20.0: 从3.0降到1.0
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