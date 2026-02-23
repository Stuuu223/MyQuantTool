# -*- coding: utf-8 -*-
"""
价格工具模块 - Phase 7核心能力封装

提供统一、可信的价格数据获取和计算能力。
所有价格数据唯一可信源：QMT本地日线

设计原则：
- 禁止估算/兜底值
- 禁止返回None代替错误
- 禁止使用外部API（Tushare等）
- 单一可信数据源：QMT本地日线

Author: iFlow CLI
Date: 2026-02-23
Version: 1.0.0
"""

from typing import Optional
from datetime import datetime, timedelta
import pandas as pd

from logic.utils.logger import get_logger

logger = get_logger(__name__)


class DataMissingError(Exception):
    """数据缺失错误 - 禁止估算时必须抛出"""
    pass


class PriceCalculationError(Exception):
    """价格计算错误"""
    pass


def _get_xtdata_module():
    """
    延迟导入xtdata模块，避免启动时连接问题
    
    Returns:
        xtdata模块
    
    Raises:
        ImportError: xtdata模块不可用
    """
    try:
        from xtquant import xtdata
        return xtdata
    except ImportError as e:
        logger.error("xtdata模块导入失败，请确保在QMT虚拟环境中运行")
        raise ImportError(f"xtdata模块不可用: {e}")


def _normalize_stock_code(stock_code: str) -> str:
    """
    标准化股票代码格式
    
    Args:
        stock_code: 原始股票代码，如'300986.SZ'或'300986'
    
    Returns:
        str: 标准化后的代码，如'300986.SZ'
    
    Raises:
        ValueError: 代码格式无效
    """
    if not stock_code or not isinstance(stock_code, str):
        raise ValueError(f"股票代码不能为空，类型: {type(stock_code)}")
    
    # 如果已经包含后缀，直接返回
    if '.' in stock_code:
        return stock_code.upper()
    
    # 根据代码规则添加后缀
    code = stock_code.strip()
    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"股票代码格式错误: {stock_code}，应为6位数字")
    
    # 根据代码前缀判断交易所
    if code.startswith('6'):
        return f"{code}.SH"
    elif code.startswith(('0', '3')):
        return f"{code}.SZ"
    elif code.startswith('8') or code.startswith('4'):
        return f"{code}.BJ"
    else:
        raise ValueError(f"无法识别的股票代码: {stock_code}")


def _get_previous_trade_date(date: str) -> str:
    """
    获取指定日期的前一个交易日
    
    Args:
        date: 日期，格式'YYYYMMDD'
    
    Returns:
        str: 前一交易日，格式'YYYYMMDD'
    
    Raises:
        ValueError: 日期格式无效
    """
    try:
        dt = datetime.strptime(date, "%Y%m%d")
    except ValueError:
        raise ValueError(f"日期格式错误: {date}，应为YYYYMMDD格式")
    
    # 向前查找前一个交易日（跳过周末）
    prev_date = dt - timedelta(days=1)
    while prev_date.weekday() >= 5:  # 5=周六, 6=周日
        prev_date -= timedelta(days=1)
    
    return prev_date.strftime("%Y%m%d")


def get_pre_close(stock_code: str, date: str) -> float:
    """
    获取昨收价 - 唯一可信数据源：QMT本地日线
    
    从QMT本地日线数据中获取指定日期的前一日收盘价。
    禁止：使用Tushare、禁止用开盘价估算
    
    Args:
        stock_code: 股票代码，如'300986.SZ'或'300986'
        date: 日期，格式'YYYYMMDD'
    
    Returns:
        float: 昨收价
    
    Raises:
        DataMissingError: 数据缺失时抛出，禁止估算
        ValueError: 参数格式无效
        ImportError: xtdata模块不可用
    
    Example:
        >>> pre_close = get_pre_close('300986.SZ', '20251231')
        >>> print(pre_close)
        25.68
    """
    # 1. 参数验证
    if not stock_code or not isinstance(stock_code, str):
        raise ValueError(f"股票代码无效: {stock_code}")
    
    if not date or not isinstance(date, str):
        raise ValueError(f"日期无效: {date}")
    
    # 标准化代码
    try:
        normalized_code = _normalize_stock_code(stock_code)
    except ValueError as e:
        raise ValueError(f"股票代码格式错误: {e}")
    
    # 2. 计算前一交易日
    try:
        prev_date = _get_previous_trade_date(date)
    except ValueError as e:
        raise ValueError(f"日期计算错误: {e}")
    
    # 3. 获取xtdata模块
    xtdata = _get_xtdata_module()
    
    # 4. 查询QMT本地日线数据
    try:
        # 下载数据（如果本地没有）
        xtdata.download_history_data(
            stock_code=normalized_code,
            period='1d',
            start_time=prev_date,
            end_time=prev_date
        )
        
        # 获取本地数据
        data = xtdata.get_local_data(
            field_list=['close'],
            stock_code_list=[normalized_code],
            period='1d',
            start_time=prev_date,
            end_time=prev_date
        )
        
    except Exception as e:
        logger.error(f"获取日线数据失败 [{normalized_code}@{prev_date}]: {e}")
        raise DataMissingError(
            f"无法获取 {normalized_code} 在 {prev_date} 的日线数据: {e}"
        )
    
    # 5. 解析数据
    if data is None or normalized_code not in data:
        raise DataMissingError(
            f"QMT本地数据缺失: {normalized_code} 在 {prev_date} 无数据"
        )
    
    close_series = data[normalized_code]
    if close_series is None or len(close_series) == 0:
        raise DataMissingError(
            f"QMT本地数据为空: {normalized_code} 在 {prev_date} 收盘价缺失"
        )
    
    # 获取收盘价
    try:
        pre_close = float(close_series.iloc[-1])
    except (IndexError, TypeError, ValueError) as e:
        raise DataMissingError(
            f"收盘价数据解析失败 [{normalized_code}@{prev_date}]: {e}"
        )
    
    # 6. 数据有效性验证
    if pre_close <= 0:
        raise DataMissingError(
            f"收盘价无效 [{normalized_code}@{prev_date}]: {pre_close}"
        )
    
    logger.debug(f"获取昨收价成功 [{normalized_code}]: {pre_close}")
    return pre_close


def calc_true_change(current_price: float, pre_close: float) -> float:
    """
    计算真实涨幅 - 唯一公式：(今价-昨收)/昨收
    
    使用昨收价作为基准计算涨跌幅，禁止：使用开盘价作为基准
    
    Args:
        current_price: 当前价格
        pre_close: 昨收价
    
    Returns:
        float: 涨幅百分比（如5.5表示上涨5.5%）
    
    Raises:
        PriceCalculationError: 计算失败
        ValueError: 参数无效
    
    Example:
        >>> change = calc_true_change(27.0, 25.68)
        >>> print(change)
        5.14
    """
    # 1. 参数验证
    if current_price is None:
        raise ValueError("当前价格不能为空")
    
    if pre_close is None:
        raise ValueError("昨收价不能为空")
    
    if not isinstance(current_price, (int, float)):
        raise ValueError(f"当前价格必须是数字: {type(current_price)}")
    
    if not isinstance(pre_close, (int, float)):
        raise ValueError(f"昨收价必须是数字: {type(pre_close)}")
    
    # 2. 价格有效性检查
    if current_price <= 0:
        raise ValueError(f"当前价格必须大于0: {current_price}")
    
    if pre_close <= 0:
        raise ValueError(f"昨收价必须大于0: {pre_close}")
    
    # 3. 计算涨幅
    try:
        change = (current_price - pre_close) / pre_close * 100
    except ZeroDivisionError:
        raise PriceCalculationError("昨收价为0，无法计算涨幅")
    
    # 4. 结果验证（检查是否溢出）
    if not isinstance(change, (int, float)):
        raise PriceCalculationError(f"计算结果异常: {change}")
    
    # 限制范围（A股涨跌幅限制为±20%，科创板±20%，ST±5%）
    if change > 1000 or change < -1000:
        logger.warning(f"涨幅异常 [{current_price}/{pre_close}]: {change:.2f}%")
    
    return round(change, 2)


def batch_get_pre_close(stock_codes: list, date: str) -> dict:
    """
    批量获取昨收价
    
    Args:
        stock_codes: 股票代码列表
        date: 日期，格式'YYYYMMDD'
    
    Returns:
        dict: {stock_code: pre_close}，失败的股票代码不会包含在结果中
    
    Example:
        >>> results = batch_get_pre_close(['300986.SZ', '000001.SZ'], '20251231')
        >>> print(results)
        {'300986.SZ': 25.68, '000001.SZ': 10.5}
    """
    results = {}
    errors = []
    
    for code in stock_codes:
        try:
            pre_close = get_pre_close(code, date)
            normalized = _normalize_stock_code(code)
            results[normalized] = pre_close
        except Exception as e:
            errors.append(f"{code}: {e}")
            logger.warning(f"批量获取昨收价失败 [{code}]: {e}")
    
    if errors:
        logger.warning(f"批量获取完成: {len(results)}/{len(stock_codes)} 成功，失败列表: {errors}")
    
    return results


def validate_price_data(current_price: float, pre_close: float, 
                        max_change_pct: float = 20.0) -> bool:
    """
    验证价格数据合理性
    
    Args:
        current_price: 当前价格
        pre_close: 昨收价
        max_change_pct: 最大允许涨跌幅（默认20%）
    
    Returns:
        bool: 数据是否合理
    
    Raises:
        ValueError: 数据异常
    """
    if current_price <= 0 or pre_close <= 0:
        raise ValueError(f"价格必须大于0: current={current_price}, pre_close={pre_close}")
    
    change_pct = abs((current_price - pre_close) / pre_close * 100)
    
    if change_pct > max_change_pct * 1.1:  # 允许10%的容差
        raise ValueError(
            f"价格变动异常: 当前{current_price}, 昨收{pre_close}, 变动{change_pct:.2f}%"
        )
    
    return True
