#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.6.1 进阶战法测试脚本
测试所有新功能的性能和正确性
"""

import time
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.money_flow_master import get_money_flow_master
from logic.signal_generator import get_signal_generator_v14_4
from logic.fake_order_detector import get_fake_order_detector

logger = get_logger(__name__)

def test_problem_a_dde_fake_fall():
    """测试问题A：低吸模式下的'DDE假摔'误杀"""
    print("=" * 60)
    print("测试问题A：低吸模式下的'DDE假摔'误杀")
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
        
        print("\n✅ 问题A测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"问题A测试失败: {e}")
        print(f"\n❌ 问题A测试失败: {e}\n")
        return False

def test_problem_b_volume_trap():
    """测试问题B：价格发现区的'量能陷阱'"""
    print("=" * 60)
    print("测试问题B：价格发现区的'量能陷阱'")
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
            
            print(f"股票代码: {stock_code}")
            print(f"当前价格: ¥{current_price:.2f}")
            print(f"昨收价: ¥{prev_close:.2f}")
            
            # 检测价格发现阶段
            result = money_flow_master.check_price_discovery_stage(stock_code, current_price, prev_close)
            
            print(f"是否在价格发现阶段: {result['in_price_discovery']}")
            print(f"价格区间: {result['price_range']}")
            print(f"流动性是否OK: {result.get('liquidity_ok', False)}")
            if 'turnover_rate' in result:
                print(f"换手率: {result['turnover_rate']:.1f}%")
            if 'turnover_amount' in result:
                print(f"成交额: {result['turnover_amount']/100000000:.2f}亿")
            print(f"原因: {result['reason']}")
        else:
            print(f"❌ 无法获取实时数据")
        
        print("\n✅ 问题B测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"问题B测试失败: {e}")
        print(f"\n❌ 问题B测试失败: {e}\n")
        return False

def test_optimization1_dynamic_stop_loss():
    """测试优化1：20cm战法的'动态止损'"""
    print("=" * 60)
    print("测试优化1：20cm战法的'动态止损'")
    print("=" * 60)
    
    try:
        # 初始化管理器
        signal_gen = get_signal_generator_v14_4()
        
        # 测试股票
        stock_code = "300992"
        current_price = 28.00
        entry_price = 26.00
        dde_avg_price = 26.50
        
        print(f"股票代码: {stock_code}")
        print(f"当前价格: ¥{current_price:.2f}")
        print(f"入场价格: ¥{entry_price:.2f}")
        print(f"DDE均价线: ¥{dde_avg_price:.2f}")
        
        # 检测动态止损
        result = signal_gen.check_dynamic_stop_loss(stock_code, current_price, entry_price, dde_avg_price)
        
        print(f"是否应该止损: {result['should_stop_loss']}")
        if result['should_stop_loss']:
            print(f"止损类型: {result['stop_loss_type']}")
            print(f"止损价格: ¥{result['stop_loss_price']:.2f}")
        print(f"当前亏损: {result['current_loss_pct']:.1f}%")
        print(f"距离DDE均价线: {result['distance_to_dde_avg']:.1f}%")
        print(f"原因: {result['reason']}")
        
        print("\n✅ 优化1测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"优化1测试失败: {e}")
        print(f"\n❌ 优化1测试失败: {e}\n")
        return False

def test_optimization2_institutional_cost_line():
    """测试优化2：UI的'资金透视'增强"""
    print("=" * 60)
    print("测试优化2：UI的'资金透视'增强")
    print("=" * 60)
    
    try:
        # 初始化管理器
        signal_gen = get_signal_generator_v14_4()
        
        # 测试股票
        stock_code = "300992"
        
        print(f"股票代码: {stock_code}")
        
        # 计算主力成本线
        institutional_cost_line = signal_gen.calculate_institutional_cost_line(stock_code)
        
        if institutional_cost_line > 0:
            print(f"主力成本线: ¥{institutional_cost_line:.2f}")
            
            # 获取当前价格
            data_manager = signal_gen.get_data_manager()
            realtime_data = data_manager.get_realtime_data(stock_code)
            if realtime_data:
                current_price = realtime_data.get('price', 0)
                distance = (current_price - institutional_cost_line) / institutional_cost_line * 100 if institutional_cost_line > 0 else 0
                
                print(f"当前价格: ¥{current_price:.2f}")
                print(f"距离成本线: {distance:.1f}%")
                
                if abs(distance) <= 2:
                    print(f"✅ [黄金低吸点] 当前价格接近主力成本线")
                elif distance > 10:
                    print(f"⚠️ [追高风险] 当前价格高于主力成本线{distance:.1f}%")
                else:
                    print(f"📊 [观察中] 当前价格距离主力成本线{distance:.1f}%")
        else:
            print(f"⚠️ 无法计算主力成本线")
        
        print("\n✅ 优化2测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"优化2测试失败: {e}")
        print(f"\n❌ 优化2测试失败: {e}\n")
        return False

def test_deepening1_trap_pulse():
    """测试深化1：主力'画图'识别"""
    print("=" * 60)
    print("测试深化1：主力'画图'识别")
    print("=" * 60)
    
    try:
        # 初始化管理器
        fake_order_detector = get_fake_order_detector()
        
        # 测试股票
        stock_code = "300992"
        current_pct_change = 4.0
        
        print(f"股票代码: {stock_code}")
        print(f"当前涨幅: {current_pct_change:.1f}%")
        
        # 检测诱多陷阱
        result = fake_order_detector.check_trap_pulse(stock_code, current_pct_change)
        
        print(f"是否是诱多陷阱: {result['is_trap_pulse']}")
        print(f"买一/买二挂单巨大: {result['bid1_bid2_huge']}")
        print(f"买一/买二迅速撤单: {result['bid1_bid2_cancel_fast']}")
        print(f"撤单率: {result['cancellation_rate']:.2%}")
        print(f"置信度: {result['confidence']:.1%}")
        print(f"原因: {result['reason']}")
        
        print("\n✅ 深化1测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"深化1测试失败: {e}")
        print(f"\n❌ 深化1测试失败: {e}\n")
        return False

def test_deepening2_take_profit():
    """测试深化2：卖出逻辑的艺术"""
    print("=" * 60)
    print("测试深化2：卖出逻辑的艺术")
    print("=" * 60)
    
    try:
        # 初始化管理器
        signal_gen = get_signal_generator_v14_4()
        
        # 测试股票
        stock_code = "300992"
        current_price = 30.00
        entry_price = 26.00
        current_pct_change = 15.0
        is_limit_up = False
        
        print(f"股票代码: {stock_code}")
        print(f"当前价格: ¥{current_price:.2f}")
        print(f"入场价格: ¥{entry_price:.2f}")
        print(f"当前涨幅: {current_pct_change:.1f}%")
        print(f"是否涨停: {is_limit_up}")
        
        # 检查止盈信号
        result = signal_gen.check_take_profit_signal(stock_code, current_price, entry_price, current_pct_change, is_limit_up)
        
        print(f"是否应该止盈: {result['should_take_profit']}")
        if result['should_take_profit']:
            print(f"止盈类型: {result['take_profit_type']}")
        print(f"当前盈利: {result['current_profit_pct']:.1f}%")
        if result['seal_volume_ratio'] > 0:
            print(f"封单量/成交量: {result['seal_volume_ratio']:.2%}")
        print(f"DDE背离: {result['dde_divergence']}")
        print(f"原因: {result['reason']}")
        
        print("\n✅ 深化2测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"深化2测试失败: {e}")
        print(f"\n❌ 深化2测试失败: {e}\n")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("V18.6.1 进阶战法测试")
    print("=" * 60 + "\n")
    
    start_time = time.time()
    
    # 运行所有测试
    results = []
    results.append(("问题A：DDE假摔误杀", test_problem_a_dde_fake_fall()))
    results.append(("问题B：量能陷阱", test_problem_b_volume_trap()))
    results.append(("优化1：动态止损", test_optimization1_dynamic_stop_loss()))
    results.append(("优化2：主力成本线", test_optimization2_institutional_cost_line()))
    results.append(("深化1：诱多陷阱识别", test_deepening1_trap_pulse()))
    results.append(("深化2：自动止盈", test_deepening2_take_profit()))
    
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
    print("🎉 所有 V18.6.1 进阶战法测试完成！")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()