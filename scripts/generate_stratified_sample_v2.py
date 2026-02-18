#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V12标准样本池生成脚本 - 分层抽样版
========================================

生成原则：
1. 母体定义：有本地tick数据 ∩ auction_export交集 ∩ 流动性过滤
2. 分层维度：交易所 + 成交额三分位（实际参与配额分配）
3. 可复现性：固定随机种子(random_state=42)

配置驱动：
----------
所有参数从config/auction_sample_config.json读取，支持多profile：
- v12_standard: V12标准样本池（默认）
- v12_low_price_focus: 低价股关注
- v12_high_liquidity: 高流动性

母体筛选规则（V12标准）：
------------------------
- tick数据可用：本地QMT datadir存在该股票目录
- 竞价数据可用：存在于auction_export.csv
- 价格范围：3-100元（排除仙股和超高价股）
- 流动性：竞价成交额 ≥ 100万（排除僵尸股）

分层规则（配额分配维度）：
--------------------------
交易所分类：
  - SH: 沪主板（6开头）
  - SZ_MAIN: 深主板（00开头）
  - CYB: 创业板（30开头）
  - KCB: 科创板（68开头）
  - EXCLUDE: 北交所/新三板（排除）

成交额分层（三分位，核心分层维度）：
  - 低流动性: 0-33%
  - 中流动性: 33%-66%
  - 高流动性: 66%-100%

辅助标签（不参与配额分配，仅用于统计参考）：
--------------------------------------------
价格分层：
  - 低价: 3-10元
  - 中低价: 10-30元
  - 中高价: 30-60元
  - 高价: 60-100元

竞价涨跌幅分层：
  - 低开: 涨跌幅 < -1%
  - 平开: -1% ≤ 涨跌幅 ≤ 3%
  - 高开: 涨跌幅 > 3%

抽样方法：
----------
1. 按交易所比例分配样本名额（至少2只/交易所）
2. 在每个交易所内按成交额三分位分层抽样（核心逻辑）
3. 不足时从同交易所补充，超额时随机删减
4. 最终调整至目标总数（默认80只）

注：价格层和涨跌层仅作为辅助标签用于输出统计分布，不参与样本配额分配。
    四维度全分层会导致某些组合单元格样本过少，技术上不可行。
    分层是"尽力而为（best-effort）"，不保证每个bucket都非空。

输出文件：
----------
- scripts/samples/test_80_stocks_v12_standard.txt: V12标准样本池（推荐使用）

历史版本：
----------
- test_80_stocks.txt: V11顺序抽样（旧版，仅作对照）

Author: AI Project Director
Version: V12.1.0
Date: 2026-02-18
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Set, List, Dict, Any


def load_config_profile(config_path: str, profile_name: str) -> Dict[str, Any]:
    """
    从config文件加载指定profile的参数
    
    Args:
        config_path: config文件路径
        profile_name: profile名称（如'v12_standard'）
        
    Returns:
        参数字典
        
    Raises:
        FileNotFoundError: config文件不存在
        KeyError: profile不存在
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if 'profiles' not in config or profile_name not in config['profiles']:
        available = list(config.get('profiles', {}).keys())
        raise KeyError(f"Profile '{profile_name}' 不存在. 可用profiles: {available}")
    
    return config['profiles'][profile_name]


def get_available_tick_universe(data_dir: str = 'data/qmt_data/datadir') -> Set[str]:
    """
    获取本地有tick数据的股票宇宙
    
    Args:
        data_dir: QMT数据目录路径
        
    Returns:
        有tick数据的股票代码集合，格式如 '000001.SZ'
        
    Example:
        >>> tick_stocks = get_available_tick_universe()
        >>> print(f'有tick数据: {len(tick_stocks)}只')
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


def check_code_format_match(df_codes: pd.Series, tick_codes: Set[str]) -> bool:
    """
    检查auction数据代码格式与tick数据格式是否匹配
    
    Args:
        df_codes: auction数据中的股票代码列
        tick_codes: tick数据中的股票代码集合
        
    Returns:
        格式是否匹配
        
    Raises:
        ValueError: 格式不匹配时抛出异常
    """
    # 取样检查格式
    sample_df = df_codes.iloc[0] if len(df_codes) > 0 else ""
    sample_tick = list(tick_codes)[0] if tick_codes else ""
    
    df_has_suffix = '.' in str(sample_df)
    tick_has_suffix = '.' in str(sample_tick)
    
    if df_has_suffix != tick_has_suffix:
        raise ValueError(
            f"代码格式不匹配!\n"
            f"  auction数据格式: {'带后缀' if df_has_suffix else '纯代码'} (示例: {sample_df})\n"
            f"  tick数据格式: {'带后缀' if tick_has_suffix else '纯代码'} (示例: {sample_tick})\n"
            f"  请统一代码格式后再运行抽样。"
        )
    
    return True


def generate_stratified_sample(
    config_profile: str = "v12_standard",
    config_path: str = "config/auction_sample_config.json",
    auction_file: str = "data/auction/auction_export.csv",
    output_dir: str = "scripts/samples"
) -> List[str]:
    """
    生成分层抽样的股票样本池（配置驱动）
    
    实际分层逻辑（2维）：
    - 第1维：交易所（用于比例配额分配）
    - 第2维：成交额三分位（用于分层抽样）
    
    辅助标签（仅统计，不参与配额）：价格层、涨跌层
    
    Args:
        config_profile: config profile名称（默认'v12_standard'）
        config_path: config文件路径
        auction_file: 竞价数据CSV文件路径
        output_dir: 输出目录
        
    Returns:
        抽样得到的股票代码列表
        
    Raises:
        ValueError: 母体数量不足或代码格式不匹配
    """
    # 1. 加载配置（禁止硬编码参数）
    params = load_config_profile(config_path, config_profile)
    
    price_min = params["price_min"]
    price_max = params["price_max"]
    min_amount = params["min_auction_amount"]
    target_count = params["target_count"]
    random_seed = params["random_seed"]
    exchange_min_quota = params.get("exchange_min_quota", 2)
    liquidity_buckets = params.get("liquidity_buckets", 3)
    
    print(f'[INFO] 使用配置: {config_profile}')
    print(f'[INFO] 参数: 价格{price_min}-{price_max}元, 成交额≥{min_amount/1e6:.0f}万, 目标{target_count}只')
    
    # 2. 获取有tick数据的股票
    tick_stocks = get_available_tick_universe()
    print(f'[INFO] 本地tick数据股票: {len(tick_stocks)}只')
    
    if len(tick_stocks) == 0:
        raise ValueError("未找到任何tick数据，请检查data/qmt_data/datadir目录")
    
    # 3. 读取auction数据
    df = pd.read_csv(auction_file)
    
    # 4. 检查代码格式匹配（CTO要求）
    check_code_format_match(df['股票代码'], tick_stocks)
    
    # 5. 取交集
    df = df[df['股票代码'].isin(tick_stocks)]
    print(f'[INFO] auction_export与tick交集: {len(df)}只')
    
    # 6. 母体过滤
    df = df[(df['竞价价格'] >= price_min) & (df['竞价价格'] <= price_max)]
    df = df[df['成交额'] >= min_amount]
    print(f'[INFO] 过滤后母体({price_min}-{price_max}元, ≥{min_amount/1e6:.0f}万成交): {len(df)}只')
    
    # 检查母体数量是否充足（CTO要求：告警机制）
    if len(df) < target_count * 2:
        import warnings
        warnings.warn(
            f"[WARNING] 母体数量({len(df)})不足目标({target_count})的2倍，"
            f"分层质量可能下降。建议检查过滤条件或扩大数据源。",
            UserWarning
        )
    
    # 7. 添加分层标签
    def classify_exchange(code: str) -> str:
        """交易所分类（配额分配维度1）"""
        if code.startswith('6'):
            return 'SH'
        elif code.startswith('00'):
            return 'SZ_MAIN'
        elif code.startswith('30'):
            return 'CYB'
        elif code.startswith('68'):
            return 'KCB'
        else:
            return 'EXCLUDE'
    
    df['交易所'] = df['股票代码'].apply(classify_exchange)
    df = df[df['交易所'] != 'EXCLUDE']
    
    # 成交额分层（配额分配维度2 - 核心分层维度）
    df['成交额层'] = pd.qcut(
        df['成交额'], 
        q=liquidity_buckets, 
        labels=['低流动性', '中流动性', '高流动性']
    )
    
    # 辅助标签：价格层（仅用于统计，不参与配额分配）
    df['价格层'] = pd.cut(
        df['竞价价格'], 
        bins=[0, 10, 30, 60, 100], 
        labels=['低价', '中低价', '中高价', '高价']
    )
    
    # 辅助标签：竞价涨跌幅分层（仅用于统计，不参与配额分配）
    df['涨跌幅'] = (df['竞价价格'] / df['昨收价格'] - 1) * 100
    df['涨跌层'] = pd.cut(
        df['涨跌幅'], 
        bins=[-np.inf, -1, 3, np.inf], 
        labels=['低开', '平开', '高开']
    )
    
    # 8. 打印分层统计
    print(f'\n[分层统计]')
    print(f'交易所分布:\n{df["交易所"].value_counts()}')
    print(f'\n成交额层分布（核心分层维度）:\n{df["成交额层"].value_counts()}')
    print(f'\n价格层分布（辅助统计）:\n{df["价格层"].value_counts()}')
    print(f'\n涨跌层分布（辅助统计）:\n{df["涨跌层"].value_counts()}')
    
    # 9. 分层抽样（核心逻辑：交易所配额 + 成交额层抽样）
    total_stocks = len(df)
    sampled = []
    
    for exchange in ['SH', 'SZ_MAIN', 'CYB', 'KCB']:
        exchange_df = df[df['交易所'] == exchange]
        if len(exchange_df) == 0:
            continue
        
        # 按交易所比例分配名额（至少exchange_min_quota只）
        exchange_target = max(exchange_min_quota, int(target_count * len(exchange_df) / total_stocks))
        
        if len(exchange_df) > exchange_target:
            # 核心逻辑：按成交额层分层抽样（每个层至少1只）
            base_quota = max(1, exchange_target // liquidity_buckets)
            exchange_sample = exchange_df.groupby('成交额层', group_keys=False).apply(
                lambda x: x.sample(min(len(x), base_quota), random_state=random_seed),
                include_groups=False
            )
            # 补充不足
            if len(exchange_sample) < exchange_target:
                remaining = exchange_target - len(exchange_sample)
                excluded = exchange_df.index.difference(exchange_sample.index)
                if len(excluded) > 0:
                    additional = exchange_df.loc[excluded].sample(
                        min(remaining, len(excluded)), random_state=random_seed
                    )
                    exchange_sample = pd.concat([exchange_sample, additional])
            # 删减超额
            if len(exchange_sample) > exchange_target:
                exchange_sample = exchange_sample.sample(exchange_target, random_state=random_seed)
        else:
            exchange_sample = exchange_df
        
        sampled.append(exchange_sample)
        print(f'[INFO] {exchange}: 母体{len(exchange_df)}只 → 抽样{len(exchange_sample)}只')
    
    # 10. 合并并调整总数
    final_sample = pd.concat(sampled)
    
    if len(final_sample) > target_count:
        final_sample = final_sample.sample(target_count, random_state=random_seed)
    elif len(final_sample) < target_count:
        excluded = df.index.difference(final_sample.index)
        additional = df.loc[excluded].sample(
            min(target_count - len(final_sample), len(excluded)), 
            random_state=random_seed
        )
        final_sample = pd.concat([final_sample, additional])
    
    # 11. 输出结果
    print(f'\n[最终结果]')
    print(f'样本总数: {len(final_sample)}只')
    print(f'交易所分布:\n{final_sample["交易所"].value_counts()}')
    print(f'\n价格统计: 均价¥{final_sample["竞价价格"].mean():.2f}, '
          f'范围[¥{final_sample["竞价价格"].min():.2f}, ¥{final_sample["竞价价格"].max():.2f}]')
    print(f'成交额统计: 平均{final_sample["成交额"].mean()/1e6:.2f}百万')
    
    # 12. 保存（添加元数据注释，便于追溯）
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_file = Path(output_dir) / f'test_{target_count}_stocks_{config_profile}.txt'
    sample_codes = final_sample['股票代码'].tolist()
    
    from datetime import datetime
    with open(output_file, 'w') as f:
        # 写入元数据注释（CTO要求）
        f.write(f'# profile={config_profile}\n')
        f.write(f'# generated_at={datetime.now().isoformat()}\n')
        f.write(f'# version=V12.1.0\n')
        f.write(f'# count={len(sample_codes)}\n')
        f.write(f'# price_range={price_min}-{price_max}\n')
        f.write(f'# min_amount={min_amount}\n')
        f.write('#\n')
        # 写入股票代码
        for code in sample_codes:
            f.write(code + '\n')
    
    print(f'\n[INFO] 样本池已保存: {output_file}')
    print(f'[INFO] 元数据: profile={config_profile}, count={len(sample_codes)}')
    
    return sample_codes


if __name__ == '__main__':
    # V12标准样本池生成（配置驱动）
    codes = generate_stratified_sample(
        config_profile='v12_standard',
        config_path='config/auction_sample_config.json',
        auction_file='data/auction/auction_export.csv',
        output_dir='scripts/samples'
    )
    
    print(f'\n前20只样本: {codes[:20]}')