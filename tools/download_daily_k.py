#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
粮仓补给工具 - 下载全市场1年日K数据

用法:
    python tools/download_daily_k.py

Author: AI总监 (CTO粮仓计划)
Date: 2026-02-25
"""

import time
from datetime import datetime, timedelta

def download_all_daily_k():
    """下载全市场1年日K数据"""
    from xtquant import xtdata
    
    print("=" * 60)
    print("🌾 粮仓补给工具 - 下载全市场1年日K数据")
    print("=" * 60)
    
    # 获取全市场股票列表
    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"📊 目标股票数: {len(all_stocks)} 只")
    
    # 计算日期范围
    today_str = datetime.now().strftime('%Y%m%d')
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
    print(f"📅 日期范围: {one_year_ago} ~ {today_str}")
    
    # 分批下载
    BATCH_SIZE = 500
    total_batches = (len(all_stocks) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"📦 分批数量: {total_batches} 批")
    
    start_time = time.time()
    success_count = 0
    failed_count = 0
    
    for i in range(0, len(all_stocks), BATCH_SIZE):
        batch = all_stocks[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        
        try:
            xtdata.download_history_data2(
                stock_list=batch,
                period='1d',
                start_time=one_year_ago,
                end_time=today_str
            )
            success_count += len(batch)
            elapsed = time.time() - start_time
            print(f"✅ 批次 {batch_num}/{total_batches}: {len(batch)} 只 (累计 {success_count}/{len(all_stocks)}, 耗时 {elapsed:.1f}s)")
        except Exception as e:
            failed_count += len(batch)
            print(f"❌ 批次 {batch_num}/{total_batches}: 失败 - {e}")
    
    total_elapsed = time.time() - start_time
    
    print("=" * 60)
    print(f"✅ 粮仓补给完成!")
    print(f"   成功: {success_count} 只")
    print(f"   失败: {failed_count} 只")
    print(f"   总耗时: {total_elapsed:.1f}s")
    print("=" * 60)
    
    # 验证下载结果
    print("\n📋 验证下载结果...")
    sample = all_stocks[::20]  # 每20只取一只
    has_data = 0
    
    for stock in sample:
        data = xtdata.get_local_data(
            field_list=['time'],
            stock_list=[stock],
            period='1d',
            start_time=one_year_ago,
            end_time=today_str
        )
        if data and stock in data and data[stock] is not None and len(data[stock]) > 100:
            has_data += 1
    
    print(f"📊 抽样验证: {has_data}/{len(sample)} 只有数据 ({has_data/len(sample)*100:.1f}%)")
    
    return {
        'success': success_count,
        'failed': failed_count,
        'elapsed': total_elapsed,
        'sample_rate': has_data / len(sample)
    }


if __name__ == "__main__":
    result = download_all_daily_k()
    print(f"\n✅ 下载结果: {result}")
