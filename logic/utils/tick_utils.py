#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tick数据工具函数集

提供与QMT tick数据相关的通用工具函数，供回测、实盘、数据管理模块使用。

Author: AI Project Director
Version: V1.0
Date: 2026-02-18
"""

from pathlib import Path
from typing import Set, List, Optional


def get_available_tick_universe(data_dir: str = 'data/qmt_data/datadir') -> Set[str]:
    """
    获取本地有tick数据的股票宇宙
    
    扫描QMT数据目录，返回所有存在tick数据的股票代码集合。
    用于确保抽样或回测的股票确实有本地数据可用。
    
    Args:
        data_dir: QMT数据目录路径，默认 'data/qmt_data/datadir'
        
    Returns:
        有tick数据的股票代码集合，格式如 '000001.SZ', '600000.SH'
        
    Example:
        >>> from logic.utils.tick_utils import get_available_tick_universe
        >>> tick_stocks = get_available_tick_universe()
        >>> print(f'本地有tick数据: {len(tick_stocks)}只')
        >>> 
        >>> # 检查某只股票是否有tick数据
        >>> if '000001.SZ' in tick_stocks:
        ...     print('平安银行有tick数据')
        
    Note:
        - 只检查目录是否存在，不验证目录内数据完整性
        - 不包含日期维度，需另行检查具体日期的数据可用性
    """
    data_path = Path(data_dir)
    tick_stocks = set()
    
    for exchange in ['SZ', 'SH']:
        tick_dir = data_path / exchange / '0'
        if tick_dir.exists():
            for stock_dir in tick_dir.iterdir():
                if stock_dir.is_dir():
                    code = stock_dir.name
                    suffix = 'SZ' if exchange == 'SZ' else 'SH'
                    tick_stocks.add(f'{code}.{suffix}')
    
    return tick_stocks


def filter_tick_available(
    stock_list: List[str], 
    data_dir: str = 'data/qmt_data/datadir'
) -> List[str]:
    """
    从股票列表中过滤出有tick数据的股票
    
    Args:
        stock_list: 股票代码列表
        data_dir: QMT数据目录路径
        
    Returns:
        有tick数据的股票子列表
        
    Example:
        >>> stocks = ['000001.SZ', '000002.SZ', '999999.XY']
        >>> available = filter_tick_available(stocks)
        >>> print(f'{len(available)}/{len(stocks)} 只有tick数据')
    """
    tick_universe = get_available_tick_universe(data_dir)
    return [s for s in stock_list if s in tick_universe]


def check_tick_coverage(
    stock_list: List[str],
    data_dir: str = 'data/qmt_data/datadir'
) -> dict:
    """
    检查股票列表的tick数据覆盖情况
    
    Args:
        stock_list: 股票代码列表
        data_dir: QMT数据目录路径
        
    Returns:
        覆盖情况报告字典，包含：
        - total: 总股票数
        - has_tick: 有tick数据数
        - missing: 无tick数据的股票列表
        - coverage_pct: 覆盖率百分比
        
    Example:
        >>> report = check_tick_coverage(['000001.SZ', '999999.XY'])
        >>> print(f"覆盖率: {report['coverage_pct']:.1f}%")
    """
    tick_universe = get_available_tick_universe(data_dir)
    
    has_tick = []
    missing = []
    
    for stock in stock_list:
        if stock in tick_universe:
            has_tick.append(stock)
        else:
            missing.append(stock)
    
    total = len(stock_list)
    
    return {
        'total': total,
        'has_tick': len(has_tick),
        'missing': missing,
        'coverage_pct': (len(has_tick) / total * 100) if total > 0 else 0
    }


def get_stock_exchange(stock_code: str) -> Optional[str]:
    """
    根据股票代码判断交易所
    
    Args:
        stock_code: 股票代码，如 '000001.SZ'
        
    Returns:
        交易所名称: 'SH' | 'SZ_MAIN' | 'CYB' | 'KCB' | None
        
    Example:
        >>> get_stock_exchange('000001.SZ')
        'SZ_MAIN'
        >>> get_stock_exchange('600000.SH')
        'SH'
    """
    if '.' in stock_code:
        code = stock_code.split('.')[0]
    else:
        code = stock_code
    
    if code.startswith('6'):
        return 'SH'
    elif code.startswith('00'):
        return 'SZ_MAIN'
    elif code.startswith('30'):
        return 'CYB'
    elif code.startswith('68'):
        return 'KCB'
    else:
        return None


if __name__ == '__main__':
    # 测试
    print('测试 get_available_tick_universe():')
    universe = get_available_tick_universe()
    print(f'  本地tick数据股票: {len(universe)}只')
    print(f'  前10只: {list(universe)[:10]}')
    
    print('\n测试 check_tick_coverage():')
    test_stocks = ['000001.SZ', '000002.SZ', '600000.SH', '999999.XY']
    report = check_tick_coverage(test_stocks)
    print(f"  总数: {report['total']}")
    print(f"  有tick: {report['has_tick']}")
    print(f"  缺失: {report['missing']}")
    print(f"  覆盖率: {report['coverage_pct']:.1f}%")
