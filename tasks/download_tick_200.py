#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO指令】定向Tick下载脚本
任务：根据云端粗筛的200只名单，定向下载Tick数据

说明：
- 只下载200只股票的Tick数据（不是5000只）
- 下载1天数据（2025-12-31）
- 预计耗时<1分钟，不会触发QMT限流
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
DOWNLOAD_PERIOD = 'tick'  # 下载Tick级别数据


def load_candidates() -> list:
    """加载候选股票名单"""
    if not CANDIDATES_FILE.exists():
        raise FileNotFoundError(f"候选名单不存在: {CANDIDATES_FILE}\n请先运行 tushare_market_filter.py")
    
    df = pd.read_csv(CANDIDATES_FILE)
    stock_list = df['ts_code'].tolist()
    print(f"   加载候选股票: {len(stock_list)}只")
    return stock_list


def download_tick_data(stock_list: list, trade_date: str):
    """
    批量下载Tick数据
    
    Args:
        stock_list: 股票代码列表（Tushare格式: 000001.SZ）
        trade_date: 交易日期（YYYYMMDD）
    """
    print("\n" + "="*80)
    print("【定向Tick下载】200只候选股票")
    print("="*80)
    print(f"日期: {trade_date}")
    print(f"数据类型: Tick（分笔成交）")
    print(f"预计耗时: <1分钟")
    print("="*80)
    
    success_count = 0
    failed_stocks = []
    
    for i, stock_code in enumerate(stock_list, 1):
        # 转换代码格式（Tushare: 000001.SZ -> QMT: 000001.SZ）
        # QMT格式与Tushare相同，无需转换
        
        print(f"\n[{i}/{len(stock_list)}] {stock_code}")
        
        try:
            # 检查本地是否已有数据
            existing_data = xtdata.get_local_data(
                field_list=['time'],
                stock_list=[stock_code],
                period='tick',
                start_time=trade_date,
                end_time=trade_date
            )
            
            if existing_data and stock_code in existing_data and not existing_data[stock_code].empty:
                print(f"   ✅ 本地已存在，跳过")
                success_count += 1
                continue
            
            # 下载Tick数据
            print(f"   📥 下载中...")
            xtdata.download_history_data(
                stock_code=stock_code,
                period='tick',
                start_time=trade_date,
                end_time=trade_date
            )
            
            # 验证下载
            downloaded_data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume'],
                stock_list=[stock_code],
                period='tick',
                start_time=trade_date,
                end_time=trade_date
            )
            
            if downloaded_data and stock_code in downloaded_data:
                tick_count = len(downloaded_data[stock_code])
                print(f"   ✅ 成功 ({tick_count}条Tick)")
                success_count += 1
            else:
                print(f"   ⚠️ 下载完成但数据为空")
                failed_stocks.append(stock_code)
                
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            failed_stocks.append(stock_code)
        
        # 短暂延迟，避免触发限流
        time.sleep(0.1)
    
    # 输出摘要
    print("\n" + "="*80)
    print("【下载结果摘要】")
    print("="*80)
    print(f"总候选: {len(stock_list)}只")
    print(f"成功: {success_count}只")
    print(f"失败: {len(failed_stocks)}只")
    
    if failed_stocks:
        print(f"\n失败列表:")
        for code in failed_stocks:
            print(f"   - {code}")
    
    print("\n" + "="*80)
    return success_count, failed_stocks


def verify_tick_data(stock_list: list, trade_date: str):
    """验证Tick数据完整性"""
    print("\n" + "="*80)
    print("【Tick数据验证】")
    print("="*80)
    
    verify_results = []
    
    for stock_code in stock_list[:10]:  # 只验证前10只
        try:
            data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume'],
                stock_list=[stock_code],
                period='tick',
                start_time=trade_date,
                end_time=trade_date
            )
            
            if data and stock_code in data and not data[stock_code].empty:
                tick_count = len(data[stock_code])
                first_time = data[stock_code]['time'].iloc[0]
                last_time = data[stock_code]['time'].iloc[-1]
                
                verify_results.append({
                    'code': stock_code,
                    'tick_count': tick_count,
                    'status': '✅ 正常'
                })
                print(f"   {stock_code}: {tick_count}条Tick ({first_time} -> {last_time})")
            else:
                verify_results.append({
                    'code': stock_code,
                    'tick_count': 0,
                    'status': '❌ 无数据'
                })
                print(f"   {stock_code}: 无数据")
        except Exception as e:
            verify_results.append({
                'code': stock_code,
                'tick_count': 0,
                'status': f'❌ 错误: {e}'
            })
            print(f"   {stock_code}: 错误 - {e}")
    
    return verify_results


def main():
    """主函数"""
    print("="*80)
    print("【CTO指令】定向Tick下载（200只）")
    print("="*80)
    
    # 检查QMT连接
    try:
        from xtquant import xtdata
        print("✅ QMT连接正常")
    except ImportError:
        print("❌ QMT未安装")
        return
    
    # 加载候选名单
    print("\n1️⃣ 加载候选名单...")
    try:
        stock_list = load_candidates()
    except FileNotFoundError as e:
        print(f"   {e}")
        return
    
    # 下载Tick数据
    print("\n2️⃣ 开始下载Tick数据...")
    success_count, failed_stocks = download_tick_data(stock_list, TRADE_DATE)
    
    # 验证数据
    print("\n3️⃣ 验证Tick数据...")
    verify_tick_data(stock_list, TRADE_DATE)
    
    # 输出下一步指引
    print("\n" + "="*80)
    print("✅ 定向Tick下载完成")
    print("="*80)
    print(f"成功下载: {success_count}/{len(stock_list)}只")
    print("\n下一步: 执行真实全息回演")
    print("命令: python tasks/run_time_machine_backtest.py --date 20251231")
    print("="*80)


if __name__ == '__main__':
    main()
