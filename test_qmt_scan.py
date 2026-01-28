# -*- coding: utf-8 -*-
"""
QMT 核动力扫描测试
验证批量数据获取和单位转换是否正确
"""
import sys
import os

# 确保能找到项目路径
sys.path.append(os.getcwd())

from logic.realtime_data_provider import RealtimeDataProvider

def test_scan():
    print(">>> 🚀 启动 QMT 核动力扫描测试...")
    
    # 1. 初始化 QMT 数据源
    provider = RealtimeDataProvider()
    
    # 2. 准备测试股票池
    test_codes = ['000426', '601899', '000001', '300059', '601127', '300750']
    
    print(f">>> 正在批量获取 {len(test_codes)} 只股票的毫秒级数据...")
    
    # 3. 批量获取
    realtime_data = provider.get_realtime_data(test_codes)
    
    if not realtime_data:
        print(">>> ❌ 未获取到数据，请检查 QMT 连接或订阅")
        return
    
    print(f">>> 成功获取 {len(realtime_data)} 条数据，开始校验单位...")
    print("-" * 70)
    print(f"{'代码':<10} {'现价':<10} {'涨幅%':<10} {'成交量(手)':<15} {'成交额(万)':<15} {'数据源':<10}")
    print("-" * 70)
    
    for stock in realtime_data:
        code = stock['code']
        price = stock['price']
        change_pct = stock['change_pct'] * 100
        volume = stock['volume']
        amount = stock['amount']
        source = stock['source']
        
        print(f"{code:<10} {price:<10.2f} {change_pct:<10.2f} {volume:<15.0f} {amount:<15.0f} {source:<10}")
    
    print("-" * 70)
    print(">>> ✅ 测试完成。")
    print(">>>    如果成交量是'万手'级别，成交额是'亿元/万元'级别，说明单位修复成功。")
    print(">>>    如果数据源显示'QMT'，说明正在使用 QMT 高速通道。")

if __name__ == "__main__":
    test_scan()