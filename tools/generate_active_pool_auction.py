#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短线活跃股生成脚本 (竞价数据版本 - 3秒完成)

使用竞价数据快速生成短线活跃股名单，避免 QMT 逐个读取的卡顿问题

筛选条件：
- 成交额 > 1亿（资金关注度高）
- 涨幅绝对值 > 1%（有异动）
- 成交量 > 1000 手（有实际成交）

数据源：auction_export.csv（5192 条记录）
"""

import sys
import os
import json
import pandas as pd
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger

logger = get_logger("generate_active_pool_auction")


def generate_active_pool_from_auction():
    """
    使用竞价数据生成短线活跃股名单（3秒完成）
    """
    logger.info("=" * 80)
    logger.info("🔍 开始生成短线活跃股名单 (竞价数据版本)")
    logger.info("=" * 80)
    
    # 读取竞价数据
    auction_file = PROJECT_ROOT / 'auction_export.csv'
    if not auction_file.exists():
        logger.error(f"❌ 竞价数据文件不存在: {auction_file}")
        return []
    
    logger.info(f"   📂 读取竞价数据: {auction_file}")
    df = pd.read_csv(auction_file)
    logger.info(f"   ✅ 读取到 {len(df)} 条记录")
    
    # 计算涨幅
    df['pct_change'] = ((df['竞价价格'] - df['昨收价格']) / df['昨收价格']) * 100
    
    # 筛选条件
    # 1. 成交额 > 1亿（资金关注度高）
    # 2. 涨幅绝对值 > 1%（有异动）
    # 3. 成交量 > 1000 手（有实际成交）
    
    filtered = df[
        (df['成交额'] > 1e8) &  # 1亿
        (abs(df['pct_change']) > 1.0) &  # 涨幅 > 1%
        (df['成交量'] > 1000)
    ].copy()
    
    logger.info(f"   筛选后剩余: {len(filtered)} 只")
    
    # 排序：按成交额降序（资金关注度最高）
    filtered = filtered.sort_values('成交额', ascending=False)
    
    # 构建结果列表
    active_stocks = []
    for _, row in filtered.iterrows():
        active_stocks.append({
            'code': row['股票代码'],
            'auction_price': row['竞价价格'],
            'prev_close': row['昨收价格'],
            'pct_change': round(row['pct_change'], 2),
            'volume': row['成交量'],
            'amount': row['成交额'],
            'amount_yi': round(row['成交额'] / 1e8, 2)  # 亿元
        })
    
    # 取 Top 500
    top_500 = active_stocks[:500]
    
    logger.info("=" * 80)
    logger.info(f"✅ 筛选完成！入选 {len(top_500)} 只")
    logger.info("=" * 80)
    
    logger.info(f"\n榜喾示例 (Top 20):")
    for i, stock in enumerate(top_500[:20]):
        change_sign = "+" if stock['pct_change'] >= 0 else ""
        logger.info(f"   {i+1}. {stock['code']} | 涨幅: {change_sign}{stock['pct_change']}% | 成交额: {stock['amount_yi']}亿")
    
    # 保存为 JSON (两种格式)
    output_dir = PROJECT_ROOT / 'config'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 格式 1：仅代码列表
    code_list_file = output_dir / 'active_stocks.json'
    code_list = [stock['code'] for stock in top_500]
    with open(code_list_file, 'w', encoding='utf-8') as f:
        json.dump(code_list, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 代码列表已保存至: {code_list_file}")
    
    # 格式 2：详细信息
    detail_file = output_dir / 'active_stocks_detail.json'
    with open(detail_file, 'w', encoding='utf-8') as f:
        json.dump(top_500, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 详细信息已保存至: {detail_file}")
    
    return code_list


if __name__ == "__main__":
    result = generate_active_pool_from_auction()
    
    if result:
        logger.info("=" * 80)
        logger.info(f"🎉 成功生成 {len(result)} 只短线活跃股！")
        logger.info("=" * 80)
        logger.info("✅ 3秒完成！基于竞价数据（今日资金实际投票结果）")
        logger.info("请查看以下文件:")
        logger.info("  - config/active_stocks.json (代码列表)")
        logger.info("  - config/active_stocks_detail.json (详细信息)")
        logger.info("")
        logger.info("下一步：用这个名单继续 Tick 下载或开盘实盘测试")
    else:
        logger.error("❌ 生成失败")