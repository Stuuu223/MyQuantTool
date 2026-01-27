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
# 添加项目根目录到路径，防止报错
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import time
from logic.data_source_manager import get_data_source_manager
from logic.logger import get_logger

logger = get_logger(__name__)


def harvest_history(stock_list):
    """
    数据收割机：批量下载并保存历史数据
    
    Args:
        stock_list: 股票代码列表，例如 ['600519', '300750', '601127']
    """
    ds = get_data_source_manager()
    save_dir = "data/history_kline"
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"🚜 开始收割 {len(stock_list)} 只股票的历史数据...")
    
    success_count = 0
    fail_count = 0
    
    for i, code in enumerate(stock_list, 1):
        print(f"[{i}/{len(stock_list)}] 正在下载: {code} ...", end="", flush=True)
        
        # 调用我们修复好的带降级的接口
        df = ds.get_history_kline(code)
        
        if df is not None and not df.empty:
            # 保存文件
            file_path = os.path.join(save_dir, f"{code}.csv")
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f" ✅ 存入 {file_path}")
            success_count += 1
        else:
            print(" ❌ 失败")
            fail_count += 1
        
        # 稍微歇一下，别把刚才好不容易通的IP又搞封了
        time.sleep(1)
    
    print(f"\n🎉 收割完成！成功保存 {success_count}/{len(stock_list)} 只股票数据，失败 {fail_count} 只。")
    print(f"📁 数据保存在: {os.path.abspath(save_dir)}")


if __name__ == "__main__":
    # 在这里填入你想保存的股票代码
    my_watchlist = ['600519', '300750', '601127', '000001', '300059']
    
    # 或者去读你的配置文件
    # import json
    # with open('config/monitor_list.json', 'r', encoding='utf-8') as f:
    #     my_watchlist = json.load(f)
    
    harvest_history(my_watchlist)