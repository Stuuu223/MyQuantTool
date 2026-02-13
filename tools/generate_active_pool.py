#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短线活跃股生成脚本

基于已下载的 1分钟 K线数据，筛选出 500 只短线最活跃的股票

筛选条件：
- 日均换手率 > 3% (活跃)
- 近 60 天有涨停 (有妖气)
- 日均成交额 < 50亿 (剔除超级大象)
- 剔除停牌股票
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger

logger = get_logger("generate_active_pool")

# VIP Token
VIP_TOKEN = '6b1446e317ed67596f13d2e808291a01e0dd9839'


def start_token_service():
    """启动 xtdatacenter 行情服务 (Token 模式)"""
    try:
        from xtquant import xtdatacenter as xtdc
    except ImportError:
        logger.error("❌ 无法导入 xtquant，请检查环境")
        return None

    data_dir = PROJECT_ROOT / 'data' / 'qmt_data'
    data_dir.mkdir(parents=True, exist_ok=True)
    xtdc.set_data_home_dir(str(data_dir))
    xtdc.set_token(VIP_TOKEN)
    xtdc.init()
    listen_port = xtdc.listen(port=(58621, 58625))
    logger.info(f"🚀 行情服务已启动，监听端口: {listen_port}")
    return listen_port


def generate_active_pool():
    """
    基于已下载的 1分钟 K线数据，筛选出 500 只短线最活跃的股票
    """
    logger.info("=" * 80)
    logger.info("🔍 开始生成短线活跃股名单")
    logger.info("=" * 80)
    
    # 启动 Token 服务
    port = start_token_service()
    if not port:
        logger.error("❌ Token 服务启动失败")
        return []
    
    # 连接行情服务
    from xtquant import xtdata
    ip, port_num = port
    xtdata.connect(ip='127.0.0.1', port=port_num, remember_if_success=False)
    time.sleep(2)
    
    # 获取全市场股票
    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    logger.info(f"   全市场股票数: {len(all_stocks)}")
    
    # 计算时间范围（近 60 天）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=70)  # 多取 10 天确保有足够交易日
    start_time = start_date.strftime('%Y%m%d%H%M%S')
    
    logger.info(f"   时间范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    # 下载近 60 天日线数据
    logger.info("   📥 下载近 60 天日线数据用于筛选...")
    try:
        xtdata.download_history_data2(all_stocks, period='1d', start_time=start_time)
    except Exception as e:
        logger.error(f"❌ 日线数据下载失败: {e}")
        return []
    
    # 读取数据
    logger.info("   📊 计算指标...")
    data = xtdata.get_market_data_ex(
        field_list=['close', 'amount', 'turn'],  # turn 是换手率
        stock_list=all_stocks, 
        period='1d', 
        count=60
    )
    
    valid_stocks = []
    skipped_reasons = {
        '停牌': 0,
        '换手率低': 0,
        '无涨停': 0,
        '成交额过大': 0,
        '数据不足': 0
    }
    
    for code, df in data.items():
        if df.empty or len(df) < 20:
            skipped_reasons['数据不足'] += 1
            continue
        
        # 1. 剔除停牌 (最近一天成交额为0)
        last_amount = df['amount'].iloc[-1]
        if last_amount < 100000:  # 小于10万成交
            skipped_reasons['停牌'] += 1
            continue
        
        # 2. 计算日均换手率 (最近 20 天)
        if 'turn' not in df.columns or df['turn'].isna().all():
            skipped_reasons['数据不足'] += 1
            continue
        
        avg_turn = df['turn'].tail(20).mean()
        
        # 3. 计算是否有涨停 (High limit)
        # 简单判断：单日涨幅 > 9.5% (包括 10% 和 20%)
        closes = df['close']
        pct_chg = closes.pct_change()
        has_limit = (pct_chg > 0.095).any()
        
        # 4. 剔除大市值 (用成交额反推)
        avg_amount = df['amount'].tail(20).mean()
        
        # 筛选逻辑：
        # - 换手率 > 3% (活跃)
        # - 近 60 天有涨停 (有妖气)
        # - 日均成交额 < 50亿 (剔除超级大象)
        
        if avg_turn > 3.0 and has_limit and avg_amount < 50e8:
            valid_stocks.append({
                'code': code,
                'avg_turn': round(avg_turn, 2),
                'has_limit': has_limit,
                'avg_amount': round(avg_amount / 1e8, 2),  # 亿元
                'last_price': round(closes.iloc[-1], 2),
                'pct_change_1d': round(pct_chg.iloc[-1] * 100, 2) if len(pct_chg) > 1 else 0
            })
        else:
            # 记录跳过原因
            if avg_turn <= 3.0:
                skipped_reasons['换手率低'] += 1
            elif not has_limit:
                skipped_reasons['无涨停'] += 1
            elif avg_amount >= 50e8:
                skipped_reasons['成交额过大'] += 1
    
    # 排序：按换手率倒序 (越活跃越好)
    valid_stocks.sort(key=lambda x: x['avg_turn'], reverse=True)
    
    # 取 Top 500
    top_500 = valid_stocks[:500]
    
    logger.info("=" * 80)
    logger.info(f"✅ 筛选完成！入选 {len(top_500)} 只")
    logger.info("=" * 80)
    logger.info(f"跳过原因统计:")
    for reason, count in skipped_reasons.items():
        logger.info(f"   - {reason}: {count} 只")
    
    logger.info(f"\n榜喾示例 (Top 10):")
    for i, stock in enumerate(top_500[:10]):
        logger.info(f"   {i+1}. {stock['code']} | 换手率: {stock['avg_turn']}% | 涨停: {'是' if stock['has_limit'] else '否'} | 成交额: {stock['avg_amount']}亿")
    
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
    import time
    
    result = generate_active_pool()
    
    if result:
        logger.info("=" * 80)
        logger.info(f"🎉 成功生成 {len(result)} 只短线活跃股！")
        logger.info("=" * 80)
        logger.info("请查看以下文件:")
        logger.info("  - config/active_stocks.json (代码列表)")
        logger.info("  - config/active_stocks_detail.json (详细信息)")
    else:
        logger.error("❌ 生成失败")