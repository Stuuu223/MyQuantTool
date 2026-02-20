#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据路径解析器
CTO指令：统一处理QMT数据路径，避免AI团队反复出错
"""

import json
from pathlib import Path
from typing import Tuple, Optional

# 加载配置
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "data_paths.json"

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)


def get_qmt_data_root() -> str:
    """获取QMT数据根目录"""
    return CONFIG['qmt_data_root']


def format_stock_code(raw_code: str) -> str:
    """
    格式化股票代码，添加.SZ或.SH后缀
    
    Args:
        raw_code: 原始代码，如 "002792", "603778"
    
    Returns:
        完整代码，如 "002792.SZ", "603778.SH"
    """
    if '.' in raw_code:
        return raw_code
    
    sz_prefixes = CONFIG['market_structure']['sz']['code_prefix']
    sh_prefixes = CONFIG['market_structure']['sh']['code_prefix']
    
    for prefix in sz_prefixes:
        if raw_code.startswith(prefix):
            return f"{raw_code}.SZ"
    
    for prefix in sh_prefixes:
        if raw_code.startswith(prefix):
            return f"{raw_code}.SH"
    
    # 默认深圳
    return f"{raw_code}.SZ"


def get_tick_file_path(stock_code: str) -> Tuple[str, str]:
    """
    获取tick文件的完整路径
    
    Args:
        stock_code: 原始代码或完整代码，如 "002792" 或 "002792.SZ"
    
    Returns:
        (完整文件路径, 市场标识)
    """
    # 提取纯数字代码
    pure_code = stock_code.split('.')[0]
    
    # 确定市场
    sz_prefixes = CONFIG['market_structure']['sz']['code_prefix']
    sh_prefixes = CONFIG['market_structure']['sh']['code_prefix']
    
    market = None
    for prefix in sz_prefixes:
        if pure_code.startswith(prefix):
            market = 'sz'
            break
    
    if not market:
        for prefix in sh_prefixes:
            if pure_code.startswith(prefix):
                market = 'sh'
                break
    
    if not market:
        market = 'sz'  # 默认深圳
    
    # 构建路径
    data_root = Path(CONFIG['qmt_data_root'])
    market_path = CONFIG['market_structure'][market]['path']
    file_name = pure_code  # 无扩展名
    
    full_path = data_root / market_path / file_name
    
    return str(full_path), market


def verify_data_exists(stock_code: str) -> bool:
    """
    验证某只票的tick数据是否存在
    
    Args:
        stock_code: 股票代码
    
    Returns:
        是否存在
    """
    file_path, _ = get_tick_file_path(stock_code)
    return Path(file_path).exists()


def get_all_available_stocks() -> Tuple[list, list]:
    """
    获取所有可用的股票代码
    
    Returns:
        (深圳股票列表, 上海股票列表)
    """
    data_root = Path(CONFIG['qmt_data_root'])
    
    sz_stocks = []
    sh_stocks = []
    
    # 深圳股票
    sz_path = data_root / 'sz' / '0'
    if sz_path.exists():
        sz_stocks = [f for f in sz_path.iterdir() if f.is_file() and f.name[0].isdigit()]
        sz_stocks = [f.name for f in sz_stocks]
    
    # 上海股票
    sh_path = data_root / 'sh' / '0'
    if sh_path.exists():
        sh_stocks = [f for f in sh_path.iterdir() if f.is_file() and f.name[0].isdigit()]
        sh_stocks = [f.name for f in sh_stocks]
    
    return sz_stocks, sh_stocks


if __name__ == "__main__":
    # 测试
    print("QMT数据路径解析器测试")
    print("="*60)
    
    print(f"\n数据根目录: {get_qmt_data_root()}")
    
    test_codes = ['002792', '603778', '300017', '301005']
    for code in test_codes:
        formatted = format_stock_code(code)
        path, market = get_tick_file_path(code)
        exists = verify_data_exists(code)
        
        print(f"\n代码: {code}")
        print(f"  格式化: {formatted}")
        print(f"  市场: {market}")
        print(f"  路径: {path}")
        print(f"  存在: {'✅' if exists else '❌'}")
    
    sz_list, sh_list = get_all_available_stocks()
    print(f"\n深圳股票数: {len(sz_list)}")
    print(f"上海股票数: {len(sh_list)}")