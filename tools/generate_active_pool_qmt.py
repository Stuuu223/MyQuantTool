#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短线活跃股生成脚本 (QMT 数据版本)

使用已下载的 1分钟 K线数据，筛选出 500 只短线最活跃的股票

筛选条件：
- 日均换手率 > 3% (活跃)
- 近 60 天有涨停 (有妖气)
- 日均成交额 < 50亿 (剔除超级大象)
- 剔除停牌股票

数据源：已下载的 1分钟 K线数据（19.28 GB，5190 只股票）
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import time

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger

logger = get_logger("generate_active_pool_qmt")

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
    listen_port = xtdc.listen(port=(58623, 58625))
    logger.info(f"🚀 行情服务已启动，监听端口: {listen_port}")
    return listen_port


def generate_active_pool():
    """
    使用 QMT 1分钟 K线数据生成短线活跃股名单
    """
    logger.info("=" * 80)
    logger.info("🔍 开始生成短线活跃股名单 (QMT 数据版本)")
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
    
    # 获取全市场股票列表（基于已下载数据）
    data_dir = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir'
    
    stock_list = []
    for market in ['SH', 'SZ']:
        kline_dir = data_dir / market / '60'
        if kline_dir.exists():
            files = list(kline_dir.glob('*.DAT'))
            for f in files:
                code = f"{f.stem}.{market}"
                stock_list.append(code)
    
    logger.info(f"   发现已下载数据的股票: {len(stock_list)} 只")
    
    # 读取 1分钟 K线数据并合成日线
    valid_stocks = []
    skipped_reasons = {
        '数据不足': 0,
        '换手率低': 0,
        '无涨停': 0,
        '成交额过大': 0,
        '其他': 0
    }
    
    logger.info(f"   开始处理 {len(stock_list)} 只股票...")
    
    for idx, code in enumerate(stock_list):
        try:
            # 读取近 60 天的 1分钟 K线数据
            data = xtdata.get_local_data(
                stock_list=[code],
                period='1m',
                count=60 * 390  # 60 天 * 390 分钟/天
            )
            
            if code not in data or data[code].empty:
                skipped_reasons['数据不足'] += 1
                continue
            
            df = data[code]
            
            if len(df) < 390:  # 少于 1 天的数据
                skipped_reasons['数据不足'] += 1
                continue
            
            # 合成日线数据
            df.index = pd.to_datetime(df.index, unit='s')
            df = df.resample('D').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'amount': 'sum'
            }).dropna()
            
            if len(df) < 20:
                skipped_reasons['数据不足'] += 1
                continue
            
            # 计算涨跌幅
            df['pct_change'] = df['close'].pct_change() * 100
            
            # 计算换手率（用成交额估算）
            # 假设平均成交价 = 成交额 / 成交量
            # 换手率 = 成交量 / 流通股本
            # 由于没有流通股本数据，我们用成交额 / 均价来估算活跃度
            df['turnover_est'] = (df['amount'] / df['close']) / 100000000  # 亿元
            
            # 1. 日均换手率估算 (最近 20 天)
            avg_turnover = df['turnover_est'].tail(20).mean()
            
            # 2. 检查是否有涨停
            # 简单判断：涨幅 >= 9.5%
            has_limit = (df['pct_change'] >= 9.5).any()
            
            # 3. 日均成交额
            avg_amount = df['amount'].tail(20).mean()
            
            # 筛选逻辑：
            # - 换手率估算 > 1 亿（活跃）
            # - 近 60 天有涨停 (有妖气)
            # - 日均成交额 < 50亿 (剔除超级大象)
            
            if avg_turnover > 1.0 and has_limit and avg_amount < 50e8:
                valid_stocks.append({
                    'code': code,
                    'avg_turnover': round(avg_turnover, 2),
                    'has_limit': has_limit,
                    'avg_amount': round(avg_amount / 1e8, 2),  # 亿元
                    'last_price': round(df['close'].iloc[-1], 2),
                    'pct_change': round(df['pct_change'].iloc[-1], 2) if len(df['pct_change']) > 1 else 0
                })
            else:
                if avg_turnover <= 1.0:
                    skipped_reasons['换手率低'] += 1
                elif not has_limit:
                    skipped_reasons['无涨停'] += 1
                elif avg_amount >= 50e8:
                    skipped_reasons['成交额过大'] += 1
        
        except Exception as e:
            logger.debug(f"   跳过 {code}: {e}")
            skipped_reasons['其他'] += 1
            continue
        
        # 显示进度
        if (idx + 1) % 500 == 0:
            logger.info(f"   进度: {idx + 1}/{len(stock_list)}, 已筛选: {len(valid_stocks)} 只")
    
    # 排序：按换手率倒序
    valid_stocks.sort(key=lambda x: x['avg_turnover'], reverse=True)
    
    # 取 Top 500
    top_500 = valid_stocks[:500]
    
    logger.info("=" * 80)
    logger.info(f"✅ 筛选完成！入选 {len(top_500)} 只")
    logger.info("=" * 80)
    logger.info(f"跳过原因统计:")
    for reason, count in skipped_reasons.items():
        logger.info(f"   - {reason}: {count} 只")
    
    logger.info(f"\n榜喾示例 (Top 20):")
    for i, stock in enumerate(top_500[:20]):
        logger.info(f"   {i+1}. {stock['code']} | 换手率: {stock['avg_turnover']}亿 | 涨停: {'是' if stock['has_limit'] else '否'} | 成交额: {stock['avg_amount']}亿 | 涨幅: {stock['pct_change']}%")
    
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
