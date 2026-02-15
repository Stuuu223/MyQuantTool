# -*- coding: utf-8 -*-
"""
QMT Tick 数据可用性检查工具
功能：检查指定股票的Tick数据是否可以正常获取，用于诊断'Candidate pool 0'问题
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from logic.data.qmt_manager import get_qmt_manager

def check_tick_data():
    print("=" * 50)
    print("🔍 QMT Tick 数据检查工具")
    print("=" * 50)
    
    manager = get_qmt_manager()
    status = manager.get_status()
    
    print(f"QMT 状态: {'✅ 连接正常' if manager.is_available() else '❌ 未连接'}")
    if not manager.is_available():
        print("❌ 无法连接 QMT，请检查 QMT 客户端是否运行且配置正确")
        return

    # 测试股票列表 (包含主板、创业板、科创板)
    test_stocks = ['600519.SH', '000001.SZ', '300750.SZ', '688001.SH']
    print(f"\n📋 检查股票列表: {test_stocks}")
    
    try:
        tick_data = manager.get_full_tick(test_stocks)
        
        if not tick_data:
            print("❌ get_full_tick 返回为空 (None/Empty)")
            print("👉 可能原因: QMT 行情服务未连接或账号未登录")
            return

        success_count = 0
        for stock in test_stocks:
            if stock in tick_data:
                data = tick_data[stock]
                # 检查关键字段
                last_price = data.get('lastPrice')
                volume = data.get('volume')
                
                if last_price is not None and last_price > 0:
                    print(f"✅ {stock}: 现价={last_price}, 成交量={volume}")
                    success_count += 1
                else:
                    # 盘前或非交易时间可能为0，或者是停牌
                    print(f"⚠️  {stock}: 数据存在但现价可能无效 (lastPrice={last_price})")
                    # 只要有数据返回 key，就算连接成功
                    success_count += 1 
            else:
                print(f"❌ {stock}: 未获取到数据")
        
        print("-" * 50)
        if success_count == len(test_stocks):
            print("✅ Tick 数据获取功能正常")
        elif success_count > 0:
            print("⚠️  Tick 数据部分缺失，请检查订阅状态或市场状态")
        else:
            print("❌ Tick 数据完全不可用")
            print("👉 请检查: 1. QMT行情是否连接 2. 是否在交易时段 3. 股票代码是否正确")

    except Exception as e:
        print(f"❌ 发生异常: {e}")

if __name__ == "__main__":
    check_tick_data()
