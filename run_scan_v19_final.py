#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.10 最终扫描脚本

功能：
- 使用三级火箭架构（DataSourceManager）
- 使用纯净版半路战法（MidwayStrategy）
- 验证全市场扫描功能

Author: iFlow CLI
Version: V19.10 Final
"""

import sys
import os
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- ⚡ 暴力清除所有代理设置，强制直连 ---
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ['NO_PROXY'] = '*'  # 告诉 Python 任何地址都不走代理
print("🛡️ 已强制清除所有系统代理配置，准备使用本机/热点IP直连...")

from logic.data_source_manager import DataSourceManager
from logic.midway_strategy_v19_final import MidwayStrategy
from logic.logger import get_logger

logger = get_logger(__name__)


def main():
    print("🚀 V19.10 最终扫描启动...")
    
    # 1. 初始化数据源 (三级火箭)
    print("📡 正在初始化数据源（三级火箭架构）...")
    ds_mgr = DataSourceManager()
    
    # 2. 初始化策略
    print("🎯 正在初始化半路战法...")
    midway = MidwayStrategy(ds_mgr)
    
    # 3. 定义扫描列表 (这里手动指定几个主板和创业板代码，确保覆盖)
    # 600000(浦发), 000001(平安), 300059(东方财富), 601127(赛力斯)
    test_stocks = ['600000', '000001', '300059', '601127', '300750']
    
    print(f"📊 正在获取 {len(test_stocks)} 只股票的实时数据 (极速层)...")
    
    # 使用极速接口 (EasyQuotation)
    real_data_map = ds_mgr.get_realtime_price_fast(test_stocks)
    
    if not real_data_map:
        print("❌ 获取行情失败，请检查网络或 EasyQuotation 配置")
        return
    
    print(f"✅ 获取成功，开始策略匹配...")
    
    results = []
    for code in test_stocks:
        if code in real_data_map:
            data = real_data_map[code]
            # 这里的 data 是 DataSourceManager 返回的字典格式
            is_hit, reason = midway.check_breakout(code, data)
            
            status = "🔴 命中" if is_hit else "⚫ 忽略"
            # 兼容两种数据格式：easyquotation原始格式和DataSourceManager转换格式
            price = data.get('now') or data.get('price')
            print(f"{status} | {code} | 现价:{price} | {reason}")
            
            if is_hit:
                results.append(code)
    
    print(f"\n🎉 扫描结束，共发现 {len(results)} 只标的")
    
    if results:
        print(f"📋 命中股票: {', '.join(results)}")
    else:
        print("⚠️ 未发现符合条件的股票，请检查：")
        print("   1. 网络连接是否正常")
        print("   2. 数据源是否可用")
        print("   3. 股票是否在交易时间")


if __name__ == "__main__":
    main()