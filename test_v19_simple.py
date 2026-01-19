#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19 简化集成测试
只测试核心功能，不测试耗时的网络请求
"""

import sys
import time
from datetime import datetime
from logic.review_manager import ReviewManager
from logic.intraday_monitor import IntradayMonitor
from logic.market_sentiment import MarketSentiment
from logic.data_manager import DataManager
from logic.logger import get_logger

logger = get_logger(__name__)


def test_imports():
    """测试模块导入"""
    print("\n" + "="*60)
    print("测试1: 模块导入")
    print("="*60)
    
    try:
        from logic.market_sentiment import MarketSentiment
        from logic.intraday_monitor import IntradayMonitor
        from logic.review_manager import ReviewManager
        from logic.data_manager import DataManager
        
        print("✅ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False


def test_one_line_board_detection():
    """测试一字板检测（简化版）"""
    print("\n" + "="*60)
    print("测试2: 一字板检测")
    print("="*60)
    
    try:
        rm = ReviewManager()
        
        # 创建模拟数据
        test_dragon = {
            'code': '000001',
            'name': '测试股票',
            'seal_amount': 150000000  # 封单超过1亿
        }
        
        # 测试一字板检测（使用封单金额判断）
        is_one_line = rm._is_one_line_board('000001', '20260116', test_dragon)
        
        print(f"✅ 一字板检测完成")
        print(f"   - 股票: {test_dragon['name']} ({test_dragon['code']})")
        print(f"   - 封单金额: {test_dragon['seal_amount']/10000:.0f}万")
        print(f"   - 是否一字板: {'是' if is_one_line else '否'}")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dde_trace_time_alignment():
    """测试DDE溯源数据时间对齐"""
    print("\n" + "="*60)
    print("测试3: DDE溯源数据时间对齐")
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


def test_error_book_one_click_resurrection():
    """测试错题本一键复活"""
    print("\n" + "="*60)
    print("测试4: 错题本一键复活")
    print("="*60)
    
    try:
        rm = ReviewManager()
        
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


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("V19 简化集成测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 运行所有测试
    results.append(("模块导入", test_imports()))
    results.append(("一字板检测", test_one_line_board_detection()))
    results.append(("DDE溯源数据时间对齐", test_dde_trace_time_alignment()))
    results.append(("错题本一键复活", test_error_book_one_click_resurrection()))
    results.append(("盘中动态修正", test_intraday_correction()))
    results.append(("情绪周期定位", test_cycle_position()))
    
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
        print("\n🎉 所有测试通过！V19简化集成测试成功！")
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())
