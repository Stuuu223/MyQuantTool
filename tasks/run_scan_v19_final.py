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

# 🔥 V19.16: 切换到 QMT 高速通道
from logic.realtime_data_provider import RealtimeDataProvider
from logic.midway_strategy_v19_final import MidwayStrategy
from logic.logger import get_logger

logger = get_logger(__name__)


def main():
    print("🚀 V19.16 QMT 最终扫描启动...")
    
    # 1. 初始化 QMT 数据源 (高速通道)
    print("📡 正在切换至 QMT 高速通道...")
    data_provider = RealtimeDataProvider()
    
    # 2. 初始化策略
    print("🎯 正在初始化半路战法...")
    midway = MidwayStrategy(data_provider)
    
    # 3. 定义扫描列表 (这里手动指定几个主板和创业板代码，确保覆盖)
    # 600000(浦发), 000001(平安), 300059(东方财富), 601127(赛力斯)
    test_stocks = ['600000', '000001', '300059', '601127', '300750']
    
    print(f"📊 正在获取 {len(test_stocks)} 只股票的毫秒级实时数据 (QMT)...")
    
    # 🔥 使用 QMT 高速接口
    realtime_data = data_provider.get_realtime_data(test_stocks)
    
    if not realtime_data:
        print("❌ 获取行情失败，请检查 QMT 连接")
        return
    
    print(f"✅ 获取成功，开始策略匹配...")
    
    results = []
    # 🔥 V19.16: 转换数据格式以适配战法接口
    # RealtimeDataProvider 返回 list，MidwayStrategy 期望 dict
    real_data_map = {stock['code']: stock for stock in realtime_data}
    
    for code in test_stocks:
        if code in real_data_map:
            data = real_data_map[code]
            # 这里的 data 是 RealtimeDataProvider 返回的字典格式
            is_hit, reason = midway.check_breakout(code, data)
            
            status = "🔴 命中" if is_hit else "⚫ 忽略"
            price = data['price']
            print(f"{status} | {code} | 现价:{price} | {reason}")
            
            if is_hit:
                results.append(code)
    
    print(f"\n🎉 扫描结束，共发现 {len(results)} 只标的")
    
    if results:
        print(f"📋 命中股票: {', '.join(results)}")
    else:
        print("⚠️ 未发现符合条件的股票，请检查：")
        print("   1. QMT 连接是否正常")
        print("   2. 数据订阅是否生效")
        print("   3. 股票是否在交易时间")
        print("   4. 现在可能是盘后时间（QMT无推流数据）")


if __name__ == "__main__":
    main()