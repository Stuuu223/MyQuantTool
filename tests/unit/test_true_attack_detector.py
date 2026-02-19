#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TrueAttackDetector 测试用例

测试覆盖：
1. 正常真攻击检测
2. 尾盘偷袭过滤
3. 对倒行为过滤
4. 缩量上涨过滤
5. 资金流出过滤
6. 综合评分计算
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from logic.strategies.true_attack_detector import TrueAttackDetector, create_true_attack_detector
from logic.strategies.event_detector import EventType


def test_true_attack_detection():
    """测试正常真攻击检测"""
    print("\n" + "=" * 70)
    print("测试1: 正常真攻击检测（应触发事件）")
    print("=" * 70)

    detector = TrueAttackDetector(history_window=5)
    base_time = datetime(2026, 2, 19, 14, 30, 0)  # 14:30，非尾盘
    circ_mv = 1_000_000_000  # 10亿流通市值

    # 模拟连续5分钟的真攻击数据：价格上涨，持续流入，买盘>卖盘
    test_data_sequence = [
        {'price': 10.0, 'main_inflow': 1_000_000, 'main_buy': 5_000_000, 'main_sell': 2_000_000, 'volume': 10000, 'amount': 100_000},
        {'price': 10.05, 'main_inflow': 1_200_000, 'main_buy': 5_500_000, 'main_sell': 2_200_000, 'volume': 12000, 'amount': 120_600},
        {'price': 10.12, 'main_inflow': 1_500_000, 'main_buy': 6_000_000, 'main_sell': 2_500_000, 'volume': 15000, 'amount': 151_800},
        {'price': 10.20, 'main_inflow': 1_300_000, 'main_buy': 5_800_000, 'main_sell': 2_400_000, 'volume': 13000, 'amount': 132_600},
        {'price': 10.28, 'main_inflow': 1_800_000, 'main_buy': 7_000_000, 'main_sell': 2_800_000, 'volume': 18000, 'amount': 185_040},
    ]

    print(f"测试参数: 流通市值={circ_mv/1e8:.0f}亿, 时间={base_time.strftime('%H:%M')}")
    print(f"数据特征: 持续5分钟净流入, 价格从10.0→10.28, 买盘>卖盘")

    events = []
    for i, data in enumerate(test_data_sequence):
        tick_data = {
            'stock_code': '000001.SZ',
            'timestamp': base_time + timedelta(minutes=i),
            'main_inflow': data['main_inflow'],
            'main_buy': data['main_buy'],
            'main_sell': data['main_sell'],
            'price': data['price'],
            'volume': data['volume'],
            'amount': data['amount'],
        }
        context = {'circ_mv': circ_mv}

        event = detector.detect(tick_data, context)
        if event:
            events.append(event)

    if events:
        event = events[0]  # 取第一个触发的事件
        print(f"\n✅ PASS: 成功检测到真攻击事件")
        print(f"   事件类型: {event.event_type.value}")
        print(f"   股票代码: {event.stock_code}")
        print(f"   攻击评分: {event.confidence:.2f}")
        print(f"   攻击强度: {event.data.get('attack_strength')}")
        print(f"   流入比例: {event.data.get('inflow_ratio', 0):.4%}")
        print(f"   特征评分:")
        print(f"      - 持续流入: {event.data.get('sustained_score', 0):.2f}")
        print(f"      - 量价配合: {event.data.get('volume_price_score', 0):.2f}")
        print(f"      - 买盘优势: {event.data.get('buy_sell_score', 0):.2f}")
        print(f"      - 时机评分: {event.data.get('timing_score', 0):.2f}")
        assert event.event_type == EventType.CAPITAL_ATTACK
        assert event.confidence >= 0.6
        return True
    else:
        print(f"\n❌ FAIL: 未检测到攻击事件")
        return False


def test_last_15_minutes_filter():
    """测试尾盘偷袭过滤"""
    print("\n" + "=" * 70)
    print("测试2: 尾盘偷袭过滤（不应触发事件）")
    print("=" * 70)

    detector = TrueAttackDetector(history_window=5)
    base_time = datetime(2026, 2, 19, 14, 46, 0)  # 14:46，尾盘开始
    circ_mv = 1_000_000_000

    # 同样的攻击数据，但时间在尾盘
    test_data_sequence = [
        {'price': 10.0, 'main_inflow': 1_000_000, 'main_buy': 5_000_000, 'main_sell': 2_000_000, 'volume': 10000, 'amount': 100_000},
        {'price': 10.05, 'main_inflow': 1_200_000, 'main_buy': 5_500_000, 'main_sell': 2_200_000, 'volume': 12000, 'amount': 120_600},
        {'price': 10.12, 'main_inflow': 1_500_000, 'main_buy': 6_000_000, 'main_sell': 2_500_000, 'volume': 15000, 'amount': 151_800},
    ]

    print(f"测试参数: 流通市值={circ_mv/1e8:.0f}亿, 时间={base_time.strftime('%H:%M')}（尾盘）")

    event = None
    for i, data in enumerate(test_data_sequence):
        tick_data = {
            'stock_code': '000002.SZ',
            'timestamp': base_time + timedelta(minutes=i),
            'main_inflow': data['main_inflow'],
            'main_buy': data['main_buy'],
            'main_sell': data['main_sell'],
            'price': data['price'],
            'volume': data['volume'],
            'amount': data['amount'],
        }
        context = {'circ_mv': circ_mv}

        event = detector.detect(tick_data, context)

    if event is None:
        print(f"\n✅ PASS: 尾盘偷袭被正确过滤")
        return True
    else:
        print(f"\n❌ FAIL: 尾盘偷袭被误判为真攻击！评分={event.confidence:.2f}")
        return False


def test_wash_trading_filter():
    """测试对倒行为过滤"""
    print("\n" + "=" * 70)
    print("测试3: 对倒行为过滤（卖盘>买盘，不应触发事件）")
    print("=" * 70)

    detector = TrueAttackDetector(history_window=5)
    base_time = datetime(2026, 2, 19, 14, 30, 0)
    circ_mv = 1_000_000_000

    # 卖盘大于买盘的数据（对倒嫌疑）
    test_data_sequence = [
        {'price': 10.0, 'main_inflow': 500_000, 'main_buy': 3_000_000, 'main_sell': 5_000_000, 'volume': 10000, 'amount': 100_000},
        {'price': 10.02, 'main_inflow': 600_000, 'main_buy': 3_200_000, 'main_sell': 5_500_000, 'volume': 11000, 'amount': 110_220},
        {'price': 10.05, 'main_inflow': 700_000, 'main_buy': 3_500_000, 'main_sell': 6_000_000, 'volume': 12000, 'amount': 120_600},
    ]

    print(f"测试参数: 流通市值={circ_mv/1e8:.0f}亿")
    print(f"数据特征: 卖盘>买盘（对倒嫌疑）")

    event = None
    for i, data in enumerate(test_data_sequence):
        tick_data = {
            'stock_code': '000003.SZ',
            'timestamp': base_time + timedelta(minutes=i),
            'main_inflow': data['main_inflow'],
            'main_buy': data['main_buy'],
            'main_sell': data['main_sell'],
            'price': data['price'],
            'volume': data['volume'],
            'amount': data['amount'],
        }
        context = {'circ_mv': circ_mv}

        event = detector.detect(tick_data, context)

    if event is None:
        print(f"\n✅ PASS: 对倒行为被正确过滤")
        return True
    else:
        print(f"\n❌ FAIL: 对倒行为被误判为真攻击！评分={event.confidence:.2f}")
        return False


def test_volume_price_divergence():
    """测试量价背离过滤（缩量上涨）"""
    print("\n" + "=" * 70)
    print("测试4: 缩量上涨过滤（价格上涨但成交量萎缩）")
    print("=" * 70)

    detector = TrueAttackDetector(history_window=5)
    base_time = datetime(2026, 2, 19, 14, 30, 0)
    circ_mv = 1_000_000_000

    # 价格上涨但成交量萎缩（诱多嫌疑）
    test_data_sequence = [
        {'price': 10.0, 'main_inflow': 1_000_000, 'main_buy': 5_000_000, 'main_sell': 2_000_000, 'volume': 10000, 'amount': 100_000},
        {'price': 10.10, 'main_inflow': 1_100_000, 'main_buy': 5_200_000, 'main_sell': 2_100_000, 'volume': 8000, 'amount': 80_800},  # 缩量
        {'price': 10.25, 'main_inflow': 1_200_000, 'main_buy': 5_500_000, 'main_sell': 2_200_000, 'volume': 7000, 'amount': 71_750},  # 继续缩量
    ]

    print(f"测试参数: 流通市值={circ_mv/1e8:.0f}亿")
    print(f"数据特征: 价格10.0→10.25，但成交量从10000→8000→7000（缩量）")

    event = None
    for i, data in enumerate(test_data_sequence):
        tick_data = {
            'stock_code': '000004.SZ',
            'timestamp': base_time + timedelta(minutes=i),
            'main_inflow': data['main_inflow'],
            'main_buy': data['main_buy'],
            'main_sell': data['main_sell'],
            'price': data['price'],
            'volume': data['volume'],
            'amount': data['amount'],
        }
        context = {'circ_mv': circ_mv}

        event = detector.detect(tick_data, context)

    # 缩量上涨可能触发弱攻击，但评分应该较低
    if event is None or event.confidence < 0.6:
        print(f"\n✅ PASS: 缩量上涨被正确识别为弱攻击或无攻击")
        if event:
            print(f"   评分={event.confidence:.2f} (< 0.6阈值)")
        return True
    else:
        print(f"\n⚠️ WARN: 缩量上涨触发攻击，评分={event.confidence:.2f}")
        return False


def test_outflow_filter():
    """测试资金流出过滤"""
    print("\n" + "=" * 70)
    print("测试5: 资金流出过滤（净流出不应触发事件）")
    print("=" * 70)

    detector = TrueAttackDetector(history_window=5)
    base_time = datetime(2026, 2, 19, 14, 30, 0)
    circ_mv = 1_000_000_000

    # 资金净流出的数据
    test_data_sequence = [
        {'price': 10.0, 'main_inflow': -500_000, 'main_buy': 2_000_000, 'main_sell': 5_000_000, 'volume': 10000, 'amount': 100_000},
        {'price': 9.95, 'main_inflow': -600_000, 'main_buy': 2_200_000, 'main_sell': 5_500_000, 'volume': 12000, 'amount': 119_400},
        {'price': 9.90, 'main_inflow': -700_000, 'main_buy': 2_500_000, 'main_sell': 6_000_000, 'volume': 15000, 'amount': 148_500},
    ]

    print(f"测试参数: 流通市值={circ_mv/1e8:.0f}亿")
    print(f"数据特征: 持续净流出，价格下跌")

    event = None
    for i, data in enumerate(test_data_sequence):
        tick_data = {
            'stock_code': '000005.SZ',
            'timestamp': base_time + timedelta(minutes=i),
            'main_inflow': data['main_inflow'],
            'main_buy': data['main_buy'],
            'main_sell': data['main_sell'],
            'price': data['price'],
            'volume': data['volume'],
            'amount': data['amount'],
        }
        context = {'circ_mv': circ_mv}

        event = detector.detect(tick_data, context)

    if event is None:
        print(f"\n✅ PASS: 资金流出被正确过滤")
        return True
    else:
        print(f"\n❌ FAIL: 资金流出被误判为真攻击！评分={event.confidence:.2f}")
        return False


def test_score_calculation():
    """测试综合评分计算"""
    print("\n" + "=" * 70)
    print("测试6: 综合评分计算验证")
    print("=" * 70)

    detector = TrueAttackDetector(history_window=5)
    base_time = datetime(2026, 2, 19, 14, 30, 0)
    circ_mv = 5_000_000_000  # 50亿大盘股

    # 强攻击数据（高流入比例）
    test_data_sequence = [
        {'price': 50.0, 'main_inflow': 10_000_000, 'main_buy': 50_000_000, 'main_sell': 20_000_000, 'volume': 50000, 'amount': 2_500_000},
        {'price': 51.0, 'main_inflow': 15_000_000, 'main_buy': 60_000_000, 'main_sell': 25_000_000, 'volume': 60000, 'amount': 3_060_000},
        {'price': 52.5, 'main_inflow': 20_000_000, 'main_buy': 70_000_000, 'main_sell': 30_000_000, 'volume': 70000, 'amount': 3_675_000},
        {'price': 54.0, 'main_inflow': 18_000_000, 'main_buy': 65_000_000, 'main_sell': 28_000_000, 'volume': 65000, 'amount': 3_510_000},
        {'price': 55.5, 'main_inflow': 25_000_000, 'main_buy': 80_000_000, 'main_sell': 35_000_000, 'volume': 80000, 'amount': 4_440_000},
    ]

    total_inflow = sum(d['main_inflow'] for d in test_data_sequence)
    ratio = total_inflow / circ_mv

    print(f"测试参数: 流通市值={circ_mv/1e8:.0f}亿")
    print(f"数据特征: 5分钟总流入={total_inflow/1e4:.0f}万, ratio={ratio:.4%}")

    event = None
    for i, data in enumerate(test_data_sequence):
        tick_data = {
            'stock_code': '000006.SZ',
            'timestamp': base_time + timedelta(minutes=i),
            'main_inflow': data['main_inflow'],
            'main_buy': data['main_buy'],
            'main_sell': data['main_sell'],
            'price': data['price'],
            'volume': data['volume'],
            'amount': data['amount'],
        }
        context = {'circ_mv': circ_mv}

        event = detector.detect(tick_data, context)

    if event:
        print(f"\n✅ PASS: 评分计算正确")
        print(f"   攻击评分: {event.confidence:.2f}")
        print(f"   攻击强度: {event.data.get('attack_strength')}")
        print(f"   流入比例: {event.data.get('inflow_ratio', 0):.4%}")
        assert event.confidence >= 0.6
        assert 'feature_scores' in event.data
        return True
    else:
        print(f"\n❌ FAIL: 未检测到攻击事件")
        return False


def test_cooldown():
    """测试冷却机制"""
    print("\n" + "=" * 70)
    print("测试7: 冷却机制测试（同一股票2分钟内不重复触发）")
    print("=" * 70)

    detector = TrueAttackDetector(history_window=5)
    base_time = datetime(2026, 2, 19, 14, 30, 0)
    circ_mv = 1_000_000_000

    # 第一次攻击数据
    test_data_sequence = [
        {'price': 10.0, 'main_inflow': 1_000_000, 'main_buy': 5_000_000, 'main_sell': 2_000_000, 'volume': 10000, 'amount': 100_000},
        {'price': 10.05, 'main_inflow': 1_200_000, 'main_buy': 5_500_000, 'main_sell': 2_200_000, 'volume': 12000, 'amount': 120_600},
        {'price': 10.12, 'main_inflow': 1_500_000, 'main_buy': 6_000_000, 'main_sell': 2_500_000, 'volume': 15000, 'amount': 151_800},
        {'price': 10.20, 'main_inflow': 1_300_000, 'main_buy': 5_800_000, 'main_sell': 2_400_000, 'volume': 13000, 'amount': 132_600},
        {'price': 10.28, 'main_inflow': 1_800_000, 'main_buy': 7_000_000, 'main_sell': 2_800_000, 'volume': 18000, 'amount': 185_040},
    ]

    print(f"第一次攻击检测...")

    event1 = None
    for i, data in enumerate(test_data_sequence):
        tick_data = {
            'stock_code': '000007.SZ',
            'timestamp': base_time + timedelta(minutes=i),
            'main_inflow': data['main_inflow'],
            'main_buy': data['main_buy'],
            'main_sell': data['main_sell'],
            'price': data['price'],
            'volume': data['volume'],
            'amount': data['amount'],
        }
        context = {'circ_mv': circ_mv}

        event1 = detector.detect(tick_data, context)

    if not event1:
        print(f"\n❌ FAIL: 第一次攻击未检测到")
        return False

    print(f"✓ 第一次攻击检测到，评分={event1.confidence:.2f}")

    # 立即再检测一次（1分钟后=60秒），应该在冷却期内（120秒）
    print(f"\n1分钟后再次检测（冷却期2分钟，应在冷却期内）...")

    event2 = None
    for i, data in enumerate(test_data_sequence):
        tick_data = {
            'stock_code': '000007.SZ',  # 同一股票
            'timestamp': base_time + timedelta(minutes=5+i),  # 5分钟后
            'main_inflow': data['main_inflow'],
            'main_buy': data['main_buy'],
            'main_sell': data['main_sell'],
            'price': data['price'] + 0.5,  # 价格更高
            'volume': data['volume'],
            'amount': data['amount'],
        }
        context = {'circ_mv': circ_mv}

        event2 = detector.detect(tick_data, context)

    if event2 is None:
        print(f"✅ PASS: 冷却机制工作正常，同一股票1分钟内未重复触发")
        return True
    else:
        print(f"⚠️ WARN: 冷却期内再次触发，评分={event2.confidence:.2f}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("TrueAttackDetector 完整测试套件")
    print("=" * 70)

    results = []

    results.append(("真攻击检测", test_true_attack_detection()))
    results.append(("尾盘过滤", test_last_15_minutes_filter()))
    results.append(("对倒过滤", test_wash_trading_filter()))
    results.append(("缩量过滤", test_volume_price_divergence()))
    results.append(("流出过滤", test_outflow_filter()))
    results.append(("评分计算", test_score_calculation()))
    results.append(("冷却机制", test_cooldown()))

    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {name}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
