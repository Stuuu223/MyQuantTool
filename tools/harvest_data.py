#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据收割机 - 批量下载并保存历史数据

用途：只要能联网，运行这个脚本，它就把你要的股票（比如自选股或ETF）的历史数据全拉下来，存成csv，以后断网也能回测！

Author: iFlow CLI
Version: V19.11.6
"""

import sys
import os
# 确保能找到根目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import time
from logic.data_source_manager import get_data_source_manager
from logic.logger import get_logger

logger = get_logger(__name__)


def harvest_history_data(stock_list=None):
    """
    收割机主程序：批量下载历史数据并覆盖保存
    
    Args:
        stock_list: 股票代码列表，如果为None则使用默认列表
    """
    if not stock_list:
        # 默认收割列表：如果你有配置文件，这里可以改去读 config
        stock_list = ['600000', '000001', '300059', '601127', '300750']
    
    ds = get_data_source_manager()
    save_dir = "data/history_kline"
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"🚜 [数据收割机] 启动！目标收割: {len(stock_list)} 只")
    
    success_count = 0
    fail_count = 0
    
    for i, code in enumerate(stock_list, 1):
        try:
            # 1. 获取数据 (复用我们修复好的带降级的接口)
            df = ds.get_history_kline(code)
            
            if df is not None and not df.empty:
                # 2. 保存 (覆盖式，保证最新)
                file_path = os.path.join(save_dir, f"{code}.csv")
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                print(f"[{i}/{len(stock_list)}] ✅ {code} 收割完成 -> {file_path}")
                success_count += 1
            else:
                print(f"[{i}/{len(stock_list)}] ❌ {code} 颗粒无收 (数据为空)")
                fail_count += 1
            
        except Exception as e:
            print(f"[{i}/{len(stock_list)}] 💥 {code} 收割报错: {e}")
            fail_count += 1
        
        # 3. 礼貌爬虫，防止封IP
        time.sleep(0.5)
    
    print(f"\n🎉 收割结束！成功 {success_count} 只，失败 {fail_count} 只")
    print(f"📁 数据保存在: {os.path.abspath(save_dir)}")


if __name__ == "__main__":
    # 你可以在这里传入你的全市场列表
    harvest_history_data()