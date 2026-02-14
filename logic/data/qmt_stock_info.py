#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMT 股票信息管理器
用于补充 tick 数据中缺失的股票名称、行业等信息

Author: iFlow CLI
Date: 2026-01-30
Version: V1.0
"""

import pandas as pd
from typing import Dict, Optional
from logic.utils.logger import get_logger
from logic.utils.code_converter import CodeConverter

logger = get_logger(__name__)


class QMTStockInfo:
    """QMT 股票信息管理器"""

    def __init__(self):
        self.xtdata = None
        self.code_converter = CodeConverter()
        self._stock_info_cache = {}  # {标准代码: {name, sector, ...}}

        try:
            from xtquant import xtdata
            self.xtdata = xtdata
            logger.info("✅ [QMTStockInfo] QMT 接口已加载")
        except ImportError:
            logger.warning("⚠️ [QMTStockInfo] QMT 接口不可用")

    def get_stock_name(self, code: str) -> str:
        """
        获取股票名称

        Args:
            code: 股票代码（任意格式）

        Returns:
            股票名称，获取失败返回空字符串
        """
        std_code = self.code_converter.to_standard(code)

        # 检查缓存
        if std_code in self._stock_info_cache:
            return self._stock_info_cache[std_code].get('name', '')

        # 从 QMT 获取
        if self.xtdata:
            try:
                qmt_code = self.code_converter.to_qmt(std_code)
                detail = self.xtdata.get_instrument_detail(qmt_code)

                if detail:
                    name = detail.get('InstrumentName', '')

                    # 缓存结果
                    self._stock_info_cache[std_code] = {
                        'name': name,
                        'code': std_code
                    }

                    return name
            except Exception as e:
                logger.debug(f"⚠️ [QMTStockInfo] 获取股票名称失败: {std_code}, {e}")

        return ''

    def batch_get_stock_names(self, codes: list) -> Dict[str, str]:
        """
        批量获取股票名称

        Args:
            codes: 股票代码列表

        Returns:
            {标准代码: 股票名称} 字典
        """
        result = {}

        if not self.xtdata:
            return result

        try:
            # 转换为 QMT 格式
            qmt_codes = [self.code_converter.to_qmt(c) for c in codes]

            # 批量查询
            for i, qmt_code in enumerate(qmt_codes):
                std_code = self.code_converter.to_standard(codes[i])

                # 先查缓存
                if std_code in self._stock_info_cache:
                    result[std_code] = self._stock_info_cache[std_code].get('name', '')
                    continue

                # 查询 QMT
                try:
                    detail = self.xtdata.get_instrument_detail(qmt_code)
                    if detail:
                        name = detail.get('InstrumentName', '')
                        result[std_code] = name

                        # 缓存
                        self._stock_info_cache[std_code] = {
                            'name': name,
                            'code': std_code
                        }
                except:
                    result[std_code] = ''

            logger.info(f"✅ [QMTStockInfo] 批量获取 {len(result)} 只股票名称")

        except Exception as e:
            logger.error(f"❌ [QMTStockInfo] 批量获取股票名称失败: {e}")

        return result

    def enrich_dataframe(self, df: pd.DataFrame, code_column: str = '代码') -> pd.DataFrame:
        """
        为 DataFrame 补充股票名称

        Args:
            df: 原始 DataFrame
            code_column: 代码列名

        Returns:
            补充了名称的 DataFrame
        """
        if df.empty or code_column not in df.columns:
            return df

        # 批量获取名称
        codes = df[code_column].tolist()
        name_dict = self.batch_get_stock_names(codes)

        # 补充到 DataFrame
        df['名称'] = df[code_column].map(lambda c: name_dict.get(self.code_converter.to_standard(c), ''))

        # 同时补充英文字段
        if 'name' in df.columns or 'code' in df.columns:
            df['name'] = df['名称']

        return df


# 全局单例
_qmt_stock_info = None

def get_qmt_stock_info() -> QMTStockInfo:
    """获取 QMT 股票信息管理器单例"""
    global _qmt_stock_info
    if _qmt_stock_info is None:
        _qmt_stock_info = QMTStockInfo()
    return _qmt_stock_info