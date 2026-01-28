# -*- coding: utf-8 -*-
"""
QMT 历史复盘测试
验证时间点快照获取和性能
"""
import sys
import os
import time

# 确保能找到项目路径
sys.path.append(os.getcwd())

from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.midway_strategy_v19_final import MidwayStrategy
from logic.logger import get_logger

logger = get_logger(__name__)


def test_time_snapshot():
    """测试时间点快照获取"""
    print(">>> 🚀 启动 QMT 历史复盘测试...")
    
    # 1. 初始化 QMT 历史数据提供者
    # 测试日期：昨天
    # 测试时间点：14:56:00（尾盘冲刺）
    print(">>> 📅 初始化 QMT 历史数据提供者...")
    provider = QMTHistoricalProvider(
        date='20260127',  # 使用最近的交易日
        time_point='145600',  # 14:56:00
        period='1m'
    )
    
    if not provider.qmt_available:
        print(">>> ❌ QMT 接口不可用，请检查 QMT 环境配置")
        return
    
    # 2. 准备测试股票
    test_codes = ['000426', '601899', '000001', '300059', '601127']
    
    print(f">>> 📊 测试股票: {', '.join(test_codes)}")
    print(f">>> 📅 复盘日期: 20260127")
    print(f">>> ⏰ 复盘时间: 14:56:00")
    
    # 3. 下载历史数据
    print(">>> 📥 正在下载历史数据...")
    start_time = time.time()
    download_success = provider.download_history_data(test_codes, period='1m')
    download_time = time.time() - start_time
    
    if download_success:
        print(f">>> ✅ 历史数据下载成功，耗时: {download_time:.2f}秒")
    else:
        print(">>> ⚠️ 历史数据下载失败（可能数据已存在）")
    
    # 4. 获取时间点快照
    print(">>> 🔍 正在获取时间点快照...")
    start_time = time.time()
    snapshot_data = provider.get_realtime_data(test_codes)
    snapshot_time = time.time() - start_time
    
    if not snapshot_data:
        print(">>> ❌ 未获取到快照数据")
        return
    
    print(f">>> ✅ 成功获取 {len(snapshot_data)} 条快照，耗时: {snapshot_time:.2f}秒")
    print("-" * 80)
    print(f"{'代码':<10} {'现价':<10} {'涨幅%':<10} {'成交量(手)':<15} {'成交额(万)':<15} {'时间点':<15}")
    print("-" * 80)
    
    for stock in snapshot_data:
        code = stock['code']
        price = stock['price']
        change_pct = stock['change_pct'] * 100
        volume = stock['volume']
        amount = stock['amount']
        replay_time = stock.get('replay_time', 'N/A')
        source = stock['source']
        
        print(f"{code:<10} {price:<10.2f} {change_pct:<10.2f} {volume:<15.0f} {amount:<15.0f} {replay_time:<15}")
    
    print("-" * 80)
    print(f">>> 数据源: {source}")
    
    # 5. 测试半路战法复盘
    print(">>> 🎯 正在测试半路战法复盘...")
    midway = MidwayStrategy(provider)
    
    hit_count = 0
    print("-" * 80)
    print(f"{'代码':<10} {'现价':<10} {'涨幅%':<10} {'战法信号':<20}")
    print("-" * 80)
    
    for stock in snapshot_data:
        code = stock['code']
        try:
            is_hit, reason = midway.check_breakout(code, stock)
            status = "✅ 命中" if is_hit else "⚫ 忽略"
            print(f"{code:<10} {stock['price']:<10.2f} {stock['change_pct']*100:<10.2f} {status:<20}")
            
            if is_hit:
                hit_count += 1
                print(f"        原因: {reason}")
        except Exception as e:
            print(f"{code:<10} {'ERROR':<10} {'ERROR':<10} {'分析失败':<20}")
            logger.error(f"半路战法分析 {code} 失败: {e}")
    
    print("-" * 80)
    print(f">>> 🎉 测试完成！")
    print(f">>>    命中数量: {hit_count}/{len(snapshot_data)}")
    print(f">>>    数据下载耗时: {download_time:.2f}秒")
    print(f">>>    快照获取耗时: {snapshot_time:.2f}秒")
    print(f">>>    总耗时: {download_time + snapshot_time:.2f}秒")
    print(">>>    如果数据源显示'QMT_History'，说明正在使用 QMT 历史数据通道。")


def test_multiple_timepoints():
    """测试多个时间点快照"""
    print("\n>>> 🔄 测试多个时间点快照...")
    
    timepoints = [
        ('093000', '9:30:00 开盘'),
        ('103000', '10:30:00 早盘'),
        ('143000', '14:30:00 尾盘'),
        ('145600', '14:56:00 尾盘冲刺'),
        ('150000', '15:00:00 收盘'),
    ]
    
    test_code = '000426'
    
    print(f">>> 📊 测试股票: {test_code}")
    print(f">>> 📅 复盘日期: 20260127")
    print("-" * 80)
    
    for timepoint, desc in timepoints:
        print(f">>> ⏰ 测试时间点: {desc} ({timepoint})")
        
        provider = QMTHistoricalProvider(
            date='20260127',
            time_point=timepoint,
            period='1m'
        )
        
        if not provider.qmt_available:
            print(">>> ❌ QMT 接口不可用")
            continue
        
        snapshot = provider.get_snapshot_at_time(test_code, timepoint)
        
        if snapshot:
            print(f"    ✅ 成功获取快照: 现价={snapshot['price']:.2f}, 涨幅={snapshot['change_pct']*100:.2f}%")
        else:
            print(f"    ❌ 未获取到快照")


if __name__ == "__main__":
    print("=" * 80)
    print("QMT 历史复盘测试 - V19.17")
    print("=" * 80)
    
    # 测试1：时间点快照
    test_time_snapshot()
    
    # 测试2：多个时间点
    # test_multiple_timepoints()
    
    print("\n" + "=" * 80)
    print("所有测试完成！")
    print("=" * 80)
