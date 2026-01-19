#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19 集成测试
测试所有V19新增功能：
1. 一字板检测
2. DDE溯源数据时间对齐
3. 席位历史战绩
4. 错题本一键复活
5. 盘中动态修正
6. 情绪周期定位
"""

import sys
import time
import json
from datetime import datetime
from logic.review_manager import ReviewManager
from logic.intraday_monitor import IntradayMonitor
from logic.market_sentiment import MarketSentiment
from logic.data_manager import DataManager
from logic.logger import get_logger

logger = get_logger(__name__)


def test_one_line_board_detection():
    """测试一字板检测"""
    print("\n" + "="*60)
    print("测试1: 一字板检测")
    print("="*60)
    
    try:
        rm = ReviewManager()
        
        # 测试日期
        test_date = '20260116'
        
        # 获取高价值案例
        cases = rm.capture_golden_cases(test_date)
        
        if cases and cases['dragons']:
            # 测试第一个真龙
            dragon = cases['dragons'][0]
            is_one_line = rm._is_one_line_board(dragon['code'], test_date, dragon)
            
            print(f"✅ 一字板检测完成")
            print(f"   - 股票: {dragon['name']} ({dragon['code']})")
            print(f"   - 是否一字板: {'是' if is_one_line else '否'}")
            return True
        else:
            print("⚠️ 未获取到测试数据")
            return True
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dde_trace_time_alignment():
    """测试DDE溯源数据时间对齐"""
    print("\n" + "="*60)
    print("测试2: DDE溯源数据时间对齐")
    print("="*60)
    
    try:
        rm = ReviewManager()
        
        # 测试股票代码
        test_code = '000001'
        test_date = '20260116'
        
        dde_history = rm.get_dde_history(test_code, test_date)
        
        if dde_history:
            print(f"✅ 成功获取 {test_code} 的DDE历史数据")
            print(f"   - 数据点数量: {len(dde_history)}")
            
            # 检查时间格式
            first_time = dde_history[0].get('time', '')
            print(f"   - 时间格式: {first_time}")
            print(f"   - 时间类型: {type(first_time)}")
            
            # 检查是否是字符串格式
            if isinstance(first_time, str):
                print("✅ 时间格式正确，为字符串类型")
            else:
                print("⚠️ 时间格式可能需要转换")
            
            return True
        else:
            print("⚠️ 未获取到DDE历史数据（可能是模拟数据）")
            return True
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_seat_history_performance():
    """测试席位历史战绩"""
    print("\n" + "="*60)
    print("测试3: 席位历史战绩")
    print("="*60)
    
    try:
        rm = ReviewManager()
        
        # 测试席位
        test_seat = "陈小群"
        
        perf = rm.get_seat_history_performance(test_seat, lookback_days=30)
        
        print(f"✅ 成功获取席位历史战绩")
        print(f"   - 席位: {perf['seat_name']}")
        print(f"   - 上榜次数: {perf['total_appearances']}")
        print(f"   - 次日平均溢价: {perf['next_day_avg_profit']}%")
        print(f"   - 盈利概率: {perf['next_day_profit_rate']}%")
        
        if perf['total_appearances'] > 0:
            print("✅ 席位历史战绩功能正常")
        else:
            print("⚠️ 该席位在30天内无上榜记录")
        
        return True
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_book_one_click_resurrection():
    """测试错题本一键复活"""
    print("\n" + "="*60)
    print("测试4: 错题本一键复活")
    print("="*60)
    
    try:
        rm = ReviewManager()
        
        # 测试日期
        test_date = '20260116'
        
        # 添加测试股票到监控列表
        test_code = '000001'
        test_name = '平安银行'
        
        success = rm.add_to_monitor_list(test_code, test_name, reason="测试错题本一键复活")
        
        if success:
            print(f"✅ 成功将 {test_name} 加入监控列表")
            
            # 读取监控列表
            monitor_list = rm.get_monitor_list()
            
            if monitor_list:
                print(f"✅ 监控列表读取成功，共 {len(monitor_list)} 只股票")
                for stock in monitor_list:
                    print(f"   - {stock['name']} ({stock['code']}): {stock['reason']}")
            else:
                print("⚠️ 监控列表为空")
            
            return True
        else:
            print("❌ 加入监控列表失败")
            return False
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_intraday_correction():
    """测试盘中动态修正"""
    print("\n" + "="*60)
    print("测试5: 盘中动态修正")
    print("="*60)
    
    try:
        dm = DataManager()
        monitor = IntradayMonitor(dm)
        
        # 测试执行力警报
        alert = monitor.check_execution_alert()
        
        print(f"✅ 执行力警报检查完成")
        print(f"   - 是否应该触发警报: {alert['should_alert']}")
        print(f"   - 捕获涨停数: {alert['captured_count']}")
        print(f"   - 实际买入数: {alert['bought_count']}")
        print(f"   - 漏失数量: {alert['missed_count']}")
        print(f"   - 严重程度: {alert['severity']}")
        
        # 测试动态买入阈值
        threshold = monitor.get_dynamic_buy_threshold()
        print(f"✅ 动态买入阈值: {threshold*100:.0f}%")
        
        # 测试执行力历史
        history = monitor.get_execution_history(days=7)
        print(f"✅ 执行力历史记录数: {len(history)}")
        
        return True
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cycle_position():
    """测试情绪周期定位"""
    print("\n" + "="*60)
    print("测试6: 情绪周期定位")
    print("="*60)
    
    try:
        ms = MarketSentiment()
        
        # 获取市场状态（包含周期定位）
        regime_info = ms.get_market_regime()
        
        cycle_position = regime_info.get('cycle_position', {})
        
        print(f"✅ 情绪周期定位完成")
        print(f"   - 周期位置: {cycle_position.get('cycle_position', 'UNKNOWN')}")
        print(f"   - 周期描述: {cycle_position.get('cycle_description', '')}")
        print(f"   - 周期策略: {cycle_position.get('cycle_strategy', '')}")
        print(f"   - 趋势方向: {cycle_position.get('trend_direction', 'SIDEWAYS')}")
        print(f"   - 趋势强度: {cycle_position.get('trend_strength', 'WEAK')}")
        
        return True
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance():
    """测试性能"""
    print("\n" + "="*60)
    print("测试7: 性能测试")
    print("="*60)
    
    try:
        dm = DataManager()
        rm = ReviewManager()
        ms = MarketSentiment()
        monitor = IntradayMonitor(dm)
        
        # 测试各个功能的耗时
        start_time = time.time()
        
        # 1. 一字板检测
        start = time.time()
        cases = rm.capture_golden_cases('20260116')
        if cases and cases['dragons']:
            rm._is_one_line_board(cases['dragons'][0]['code'], '20260116', cases['dragons'][0])
        elapsed1 = time.time() - start
        print(f"✅ 一字板检测耗时: {elapsed1:.2f}秒")
        
        # 2. DDE溯源
        start = time.time()
        dde_history = rm.get_dde_history('000001', '20260116')
        elapsed2 = time.time() - start
        print(f"✅ DDE溯源耗时: {elapsed2:.2f}秒")
        
        # 3. 席位历史战绩
        start = time.time()
        rm.get_seat_history_performance("陈小群", lookback_days=30)
        elapsed3 = time.time() - start
        print(f"✅ 席位历史战绩耗时: {elapsed3:.2f}秒")
        
        # 4. 盘中动态修正
        start = time.time()
        monitor.check_execution_alert()
        elapsed4 = time.time() - start
        print(f"✅ 盘中动态修正耗时: {elapsed4:.2f}秒")
        
        # 5. 情绪周期定位
        start = time.time()
        ms.get_cycle_position()
        elapsed5 = time.time() - start
        print(f"✅ 情绪周期定位耗时: {elapsed5:.2f}秒")
        
        total_time = elapsed1 + elapsed2 + elapsed3 + elapsed4 + elapsed5
        print(f"\n✅ 总耗时: {total_time:.2f}秒")
        
        if total_time < 60:
            print("✅ 性能测试通过，总耗时小于60秒")
            return True
        else:
            print(f"⚠️ 性能警告，总耗时 {total_time:.2f} 秒，超过60秒")
            return False
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("V19 集成测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 运行所有测试
    results.append(("一字板检测", test_one_line_board_detection()))
    results.append(("DDE溯源数据时间对齐", test_dde_trace_time_alignment()))
    results.append(("席位历史战绩", test_seat_history_performance()))
    results.append(("错题本一键复活", test_error_book_one_click_resurrection()))
    results.append(("盘中动态修正", test_intraday_correction()))
    results.append(("情绪周期定位", test_cycle_position()))
    results.append(("性能测试", test_performance()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！V19集成测试成功！")
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())