#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充下载缺失的Tick数据
针对62只Tick数据缺失的股票进行补充下载
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

import pandas as pd
from datetime import datetime
from pathlib import Path
from xtquant import xtdata
import time

# 配置
CANDIDATES_FILE = Path('E:/MyQuantTool/data/scan_results/20251231_candidates_73.csv')
TRADE_DATE = '20251231'


def check_tick_data(stock_code: str) -> bool:
    """检查是否已有Tick数据"""
    try:
        tick = xtdata.get_local_data(
            field_list=['time'],
            stock_list=[stock_code],
            period='tick',
            start_time=TRADE_DATE,
            end_time=TRADE_DATE
        )
        return tick is not None and stock_code in tick and len(tick[stock_code]) > 100
    except:
        return False


def supplement_tick_download():
    """补充下载Tick数据"""
    print("="*80)
    print("【补充下载Tick数据】")
    print("="*80)
    print(f"目标日期: {TRADE_DATE}")
    print("="*80)
    
    # 加载候选名单
    df = pd.read_csv(CANDIDATES_FILE)
    stock_list = df['ts_code'].tolist()
    print(f"候选股票总数: {len(stock_list)}只")
    
    # 检查哪些缺少Tick数据
    missing_stocks = []
    print("\n1️⃣ 检查Tick数据完整性...")
    for i, stock in enumerate(stock_list, 1):
        has_tick = check_tick_data(stock)
        status = "✅" if has_tick else "❌"
        if not has_tick:
            missing_stocks.append(stock)
        if i <= 10 or not has_tick:  # 只显示前10只和缺失的
            print(f"   {status} [{i}/{len(stock_list)}] {stock}")
    
    print(f"\n   缺失Tick数据: {len(missing_stocks)}只")
    
    if not missing_stocks:
        print("\n✅ 所有股票Tick数据已完整，无需补充下载")
        return
    
    # 补充下载
    print("\n2️⃣ 开始补充下载Tick数据...")
    print(f"   预计耗时: {len(missing_stocks) * 8}秒 ({len(missing_stocks)/60:.1f}分钟)")
    print("="*80)
    
    success_count = 0
    failed_stocks = []
    
    for i, stock_code in enumerate(missing_stocks, 1):
        try:
            print(f"\n[{i}/{len(missing_stocks)}] {stock_code}")
            
            # 下载Tick数据
            print(f"   📥 下载中...")
            xtdata.download_history_data(
                stock_code=stock_code,
                period='tick',
                start_time=TRADE_DATE,
                end_time=TRADE_DATE
            )
            
            # 验证下载
            has_data = check_tick_data(stock_code)
            if has_data:
                # 获取实际条数
                tick = xtdata.get_local_data(
                    field_list=['time'],
                    stock_list=[stock_code],
                    period='tick',
                    start_time=TRADE_DATE,
                    end_time=TRADE_DATE
                )
                tick_count = len(tick[stock_code]) if tick and stock_code in tick else 0
                print(f"   ✅ 成功 ({tick_count}条)")
                success_count += 1
            else:
                print(f"   ⚠️ 数据为空或不足")
                failed_stocks.append(stock_code)
                
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            failed_stocks.append(stock_code)
        
        # 延迟避免限流
        time.sleep(0.5)
    
    # 输出汇总
    print("\n" + "="*80)
    print("【补充下载结果】")
    print("="*80)
    print(f"需补充下载: {len(missing_stocks)}只")
    print(f"成功: {success_count}只")
    print(f"失败: {len(failed_stocks)}只")
    
    if failed_stocks:
        print(f"\n失败列表:")
        for code in failed_stocks:
            print(f"   - {code}")
    
    # 最终验证
    print("\n3️⃣ 最终验证...")
    final_complete = 0
    for stock in stock_list:
        if check_tick_data(stock):
            final_complete += 1
    
    print(f"\n   最终完整率: {final_complete}/{len(stock_list)} ({final_complete/len(stock_list)*100:.1f}%)")
    print("="*80)
    print("✅ 补充下载完成")
    print("="*80)


if __name__ == '__main__':
    supplement_tick_download()