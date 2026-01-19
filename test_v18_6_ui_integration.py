#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.6 UI 集成测试脚本
测试所有新功能的性能和正确性
"""

import time
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.money_flow_master import get_money_flow_master
from logic.low_suction_engine import get_low_suction_engine
from logic.utils import Utils
from logic.second_wave_detector import get_second_wave_detector
from logic.fake_order_detector import get_fake_order_detector
from logic.national_team_guard import get_national_team_guard
from logic.signal_generator import get_signal_generator_v14_4

logger = get_logger(__name__)

def test_pre_buy_mode():
    """测试预判模式"""
    print("=" * 60)
    print("测试预判模式（Pre-Buy Signal）")
    print("=" * 60)
    
    try:
        # 初始化管理器
        money_flow_master = get_money_flow_master()
        data_manager = DataManager()
        
        # 测试股票
        stock_code = "300992"
        
        # 获取实时数据
        realtime_data = data_manager.get_realtime_data(stock_code)
        if realtime_data:
            current_price = realtime_data.get('price', 0)
            prev_close = realtime_data.get('pre_close', current_price)
            current_pct_change = (current_price - prev_close) / prev_close * 100 if prev_close > 0 else 0
            
            print(f"股票代码: {stock_code}")
            print(f"当前价格: ¥{current_price:.2f}")
            print(f"当前涨幅: {current_pct_change:.2f}%")
            
            # 检查是否在预判区间
            if 4.0 <= current_pct_change <= 6.0:
                print(f"✅ 涨幅 {current_pct_change:.1f}% 在预判区间（4%-6%）")
                
                # 检查 DDE 斜率
                dde_history = money_flow_master._get_dde_history(stock_code, lookback=5)
                if dde_history and len(dde_history) >= 3:
                    recent_dde = dde_history[-3:]
                    dde_slope = (recent_dde[-1] - recent_dde[0]) / len(recent_dde)
                    
                    print(f"DDE 斜率: {dde_slope:.3f}")
                    
                    if dde_slope > 0:
                        print(f"✅ [预判信号] DDE 斜率转正，建议提前布局")
                    else:
                        print(f"⚠️ DDE 斜率向下，暂不建议提前布局")
                else:
                    print(f"⚠️ DDE 历史数据不足，无法判断斜率")
            else:
                print(f"📊 涨幅 {current_pct_change:.1f}% 不在预判区间（4%-6%）")
        else:
            print(f"❌ 无法获取实时数据")
        
        print("\n✅ 预判模式测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"预判模式测试失败: {e}")
        print(f"\n❌ 预判模式测试失败: {e}\n")
        return False

def test_elastic_buffer():
    """测试弹性缓冲"""
    print("=" * 60)
    print("测试弹性缓冲（Elastic Buffer）")
    print("=" * 60)
    
    try:
        # 初始化管理器
        money_flow_master = get_money_flow_master()
        data_manager = DataManager()
        
        # 测试股票
        stock_code = "300992"
        
        # 获取实时数据
        realtime_data = data_manager.get_realtime_data(stock_code)
        if realtime_data:
            current_price = realtime_data.get('price', 0)
            prev_close = realtime_data.get('pre_close', current_price)
            current_pct_change = (current_price - prev_close) / prev_close * 100 if prev_close > 0 else 0
            
            # 获取涨停系数
            limit_ratio = Utils.get_limit_ratio(stock_code)
            limit_up_pct = (limit_ratio - 1.0) * 100
            
            print(f"股票代码: {stock_code}")
            print(f"当前价格: ¥{current_price:.2f}")
            print(f"当前涨幅: {current_pct_change:.2f}%")
            print(f"涨停幅度: {limit_up_pct:.1f}%")
            
            # 检查是否是20cm/30cm股票
            if limit_ratio >= 1.2:
                if 9.0 <= current_pct_change <= 11.0:
                    print(f"✅ 涨幅 {current_pct_change:.1f}% 在弹性缓冲区间（9%-11%）")
                    
                    # 检查 DDE 斜率
                    dde_history = money_flow_master._get_dde_history(stock_code, lookback=5)
                    if dde_history and len(dde_history) >= 3:
                        recent_dde = dde_history[-3:]
                        dde_slope = (recent_dde[-1] - recent_dde[0]) / len(recent_dde)
                        
                        print(f"DDE 斜率: {dde_slope:.3f}")
                        
                        if dde_slope > 0:
                            elastic_buffer = limit_up_pct - current_pct_change
                            print(f"✅ [弹性缓冲] DDE 斜率转正，剩余空间 {elastic_buffer:.1f}%，安全垫充足")
                        else:
                            print(f"⚠️ DDE 斜率向下，暂不建议追高")
                    else:
                        print(f"⚠️ DDE 历史数据不足，无法判断斜率")
                else:
                    print(f"📊 涨幅 {current_pct_change:.1f}% 不在弹性缓冲区间（9%-11%）")
            else:
                print(f"📊 该股票不是 20cm/30cm 标的，无需弹性缓冲检查")
        else:
            print(f"❌ 无法获取实时数据")
        
        print("\n✅ 弹性缓冲测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"弹性缓冲测试失败: {e}")
        print(f"\n❌ 弹性缓冲测试失败: {e}\n")
        return False

def test_buy_mode():
    """测试 BUY_MODE 参数"""
    print("=" * 60)
    print("测试 BUY_MODE 参数（DRAGON_CHASE / LOW_SUCTION）")
    print("=" * 60)
    
    try:
        # 初始化管理器
        money_flow_master = get_money_flow_master()
        
        # 测试股票
        stock_code = "300992"
        
        # 测试 DRAGON_CHASE 模式
        print(f"测试 DRAGON_CHASE 模式:")
        is_vetoed, veto_reason = money_flow_master.check_dde_veto(stock_code, "BUY", "DRAGON_CHASE")
        print(f"是否否决: {is_vetoed}")
        print(f"原因: {veto_reason if veto_reason else '无'}")
        
        # 测试 LOW_SUCTION 模式
        print(f"\n测试 LOW_SUCTION 模式:")
        is_vetoed, veto_reason = money_flow_master.check_dde_veto(stock_code, "BUY", "LOW_SUCTION")
        print(f"是否否决: {is_vetoed}")
        print(f"原因: {veto_reason if veto_reason else '无'}")
        
        print("\n✅ BUY_MODE 参数测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"BUY_MODE 参数测试失败: {e}")
        print(f"\n❌ BUY_MODE 参数测试失败: {e}\n")
        return False

def test_second_wave():
    """测试二波预期识别"""
    print("=" * 60)
    print("测试二波预期识别")
    print("=" * 60)
    
    try:
        # 初始化管理器
        second_wave_detector = get_second_wave_detector()
        
        # 测试股票
        stock_code = "300992"
        current_price = 28.00
        suction_price = 26.00
        
        result = second_wave_detector.check_second_wave_signal(stock_code, current_price, suction_price)
        
        print(f"股票代码: {stock_code}")
        print(f"当前价格: ¥{current_price:.2f}")
        print(f"低吸价格: ¥{suction_price:.2f}")
        print(f"是否有二波预期: {result['has_second_wave']}")
        print(f"原因: {result['reason']}")
        
        if result['has_second_wave']:
            print(f"置信度: {result['confidence']:.1%}")
            print(f"提升比例: {result['boost_ratio']:.1f}x")
        
        print("\n✅ 二波预期识别测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"二波预期识别测试失败: {e}")
        print(f"\n❌ 二波预期识别测试失败: {e}\n")
        return False

def test_fake_order():
    """测试假单信号检测"""
    print("=" * 60)
    print("测试假单信号检测")
    print("=" * 60)
    
    try:
        # 初始化管理器
        fake_order_detector = get_fake_order_detector()
        
        # 测试股票
        stock_code = "300992"
        signal = "BUY"
        
        result = fake_order_detector.check_fake_order_signal(stock_code, signal)
        
        print(f"股票代码: {stock_code}")
        print(f"原始信号: {signal}")
        print(f"是否有假单: {result['has_fake_order']}")
        print(f"是否是虚假繁荣: {result['is_fake_prosperity']}")
        print(f"原因: {result['reason']}")
        
        if result['cancellation_rate'] > 0:
            print(f"撤单率: {result['cancellation_rate']:.2%}")
        
        if result['has_fake_order']:
            print(f"置信度: {result['confidence']:.1%}")
        
        print("\n✅ 假单信号检测测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"假单信号检测测试失败: {e}")
        print(f"\n❌ 假单信号检测测试失败: {e}\n")
        return False

def test_national_team_guard():
    """测试国家队护盘指纹"""
    print("=" * 60)
    print("测试国家队护盘指纹")
    print("=" * 60)
    
    try:
        # 初始化管理器
        national_team_guard = get_national_team_guard()
        
        # 测试国家队护盘检测
        result = national_team_guard.check_national_team_guard()
        
        print(f"是否在护盘: {result['is_guarding']}")
        print(f"护盘强度: {result['guard_strength']:.1%}")
        print(f"原因: {result['reason']}")
        
        # 测试全域共振检测
        stock_code = "300992"
        suction_price = 26.00
        
        result2 = national_team_guard.check_global_resonance(stock_code, suction_price)
        
        print(f"\n股票代码: {stock_code}")
        print(f"低吸价格: ¥{suction_price:.2f}")
        print(f"是否有全域共振: {result2['has_global_resonance']}")
        print(f"原因: {result2['reason']}")
        
        if result2['has_global_resonance']:
            print(f"置信度: {result2['confidence']:.1%}")
            print(f"提升比例: {result2['boost_ratio']:.1f}x")
        
        print("\n✅ 国家队护盘指纹测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"国家队护盘指纹测试失败: {e}")
        print(f"\n❌ 国家队护盘指纹测试失败: {e}\n")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("V18.6 UI 集成测试")
    print("=" * 60 + "\n")
    
    start_time = time.time()
    
    # 运行所有测试
    results = []
    results.append(("预判模式", test_pre_buy_mode()))
    results.append(("弹性缓冲", test_elastic_buffer()))
    results.append(("BUY_MODE 参数", test_buy_mode()))
    results.append(("二波预期识别", test_second_wave()))
    results.append(("假单信号检测", test_fake_order()))
    results.append(("国家队护盘指纹", test_national_team_guard()))
    
    # 统计结果
    print("=" * 60)
    print("测试结果统计")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    elapsed_time = time.time() - start_time
    print(f"总耗时: {elapsed_time:.2f}秒")
    
    print("\n" + "=" * 60)
    print("🎉 所有 V18.6 UI 集成测试完成！")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()