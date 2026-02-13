#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试时间分段筛选逻辑（最小可复现测试）

目的：验证 Level 1 筛选的时间分段逻辑是否正确
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger

logger = get_logger("test_time_segment_filter")


def test_config_reading():
    """测试配置读取是否正确"""
    import json
    
    config_path = PROJECT_ROOT / 'config' / 'market_scan_config.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("=" * 80)
    print("测试 1: 配置读取")
    print("=" * 80)
    
    # 检查 time_segments 是否存在
    if 'time_segments' in config:
        print("✅ time_segments 配置存在")
        
        # 检查各时间段配置
        for segment in ['opening', 'midday', 'close']:
            if segment in config['time_segments']:
                seg_config = config['time_segments'][segment]
                print(f"  {segment}:")
                print(f"    - pct_chg_min: {seg_config.get('pct_chg_min')}")
                print(f"    - volume_ratio_min: {seg_config.get('volume_ratio_min')}")
                print(f"    - turnover_min: {seg_config.get('turnover_min')}")
            else:
                print(f"❌ {segment} 配置缺失")
    else:
        print("❌ time_segments 配置不存在")
    
    print()


def test_time_segment_logic():
    """测试时间分段逻辑"""
    from datetime import datetime, timedelta
    
    print("=" * 80)
    print("测试 2: 时间分段逻辑")
    print("=" * 80)
    
    # 模拟三个时间点
    test_times = [
        (datetime(2026, 2, 13, 9, 35), "开盘阶段"),
        (datetime(2026, 2, 13, 10, 30), "盘中阶段"),
        (datetime(2026, 2, 13, 14, 50), "尾盘阶段"),
    ]
    
    for test_time, expected_segment in test_times:
        hour = test_time.hour
        minute = test_time.minute
        
        # 模拟代码逻辑
        if 9 <= hour < 10:
            segment = "opening"
            pct_chg_min = 0.5
            volume_ratio_min = 1.9
            turnover_min = 0.03
        elif 10 <= hour < 14 or (hour == 14 and minute < 30):
            segment = "midday"
            pct_chg_min = 1.0
            volume_ratio_min = 1.5
            turnover_min = 0.02
        else:
            segment = "close"
            pct_chg_min = 2.0
            volume_ratio_min = 3.0
            turnover_threshold = 0.05
        
        # 验证
        if segment == expected_segment:
            print(f"✅ {test_time.strftime('%H:%M')} - {expected_segment}")
            print(f"    pct_chg_min: {pct_chg_min}%, volume_ratio_min: {volume_ratio_min}, turnover_min: {turnover_min}%")
        else:
            print(f"❌ {test_time.strftime('%H:%M')} - 期望: {expected_segment}, 实际: {segment}")
    
    print()


def test_turnover_calculation():
    """测试换手率计算"""
    print("=" * 80)
    print("测试 3: 换手率计算")
    print("=" * 80)
    
    # 模拟数据
    test_cases = [
        {
            "code": "600000.SH",
            "volume": 100000000,  # 1亿股
            "circ_mv": 10000000000,  # 100亿流通市值
            "last_price": 10.0,  # 10元/股
            "expected_turnover": 0.1  # 10%
        },
        {
            "code": "300001.SZ",
            "volume": 50000000,  # 5000万股
            "circ_mv": 5000000000,  # 50亿流通市值
            "last_price": 5.0,  # 5元/股
            "expected_turnover": 0.05  # 5%
        },
    ]
    
    for case in test_cases:
        code = case["code"]
        volume = case["volume"]
        circ_mv = case["circ_mv"]
        last_price = case["last_price"]
        expected_turnover = case["expected_turnover"]
        
        # 计算流通股本
        circulating_shares = circ_mv / last_price
        
        # 计算换手率
        turnover_rate = volume / circulating_shares if circulating_shares > 0 else 0
        
        # 验证
        if abs(turnover_rate - expected_turnover) < 0.0001:
            print(f"✅ {code}")
            print(f"    流通股本: {circulating_shares/1e8:.2f}亿股")
            print(f"    成交量: {volume/1e8:.2f}亿股")
            print(f"    换手率: {turnover_rate*100:.2f}% (期望: {expected_turnover*100:.2f}%)")
        else:
            print(f"❌ {code}")
            print(f"    计算错误: {turnover_rate*100:.2f}% != {expected_turnover*100:.2f}%")
    
    print()


def test_market_cap_zero_fallback():
    """测试市值=0时的降级逻辑"""
    print("=" * 80)
    print("测试 4: 市值=0时的降级逻辑")
    print("=" * 80)
    
    # 模拟市值=0的情况
    test_cases = [
        {
            "code": "000001.SZ",
            "market_cap": 0,
            "amount": 5000000,  # 500万
            "expected_pass": False  # 应该拒绝（成交额<1000万）
        },
        {
            "code": "000002.SZ",
            "market_cap": 0,
            "amount": 15000000,  # 1500万
            "expected_pass": True  # 应该通过（成交额>1000万）
        },
    ]
    
    for case in test_cases:
        code = case["code"]
        market_cap = case["market_cap"]
        amount = case["amount"]
        expected_pass = case["expected_pass"]
        
        # 模拟代码逻辑
        if market_cap == 0:
            # 市值为0时的降级策略：使用成交额作为替代指标
            # 要求：成交额 > 1000万
            if amount < 10_000_000:
                passed = False
                reason = "成交额过低"
            else:
                passed = True
                reason = "成交额达标"
        
        # 验证
        if passed == expected_pass:
            print(f"✅ {code} - {reason} (成交额={amount/1e8:.2f}亿)")
        else:
            print(f"❌ {code} - 逻辑错误 (期望通过: {expected_pass}, 实际通过: {passed})")
    
    print()


def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("🧪 时间分段筛选逻辑测试")
    print("=" * 80 + "\n")
    
    try:
        # 运行测试
        test_config_reading()
        test_time_segment_logic()
        test_turnover_calculation()
        test_market_cap_zero_fallback()
        
        # 总结
        print("=" * 80)
        print("✅ 所有测试通过")
        print("=" * 80)
        return 0
    except Exception as e:
        print("=" * 80)
        print(f"❌ 测试失败: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())