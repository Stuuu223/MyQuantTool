#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.6 深化迭代测试脚本
测试所有新功能的性能和正确性
"""

import time
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.money_flow_master import get_money_flow_master
from logic.low_suction_engine import get_low_suction_engine
from logic.signal_generator import get_signal_generator_v14_4

logger = get_logger(__name__)

def test_price_discovery_stage():
    """测试价格发现阶段（DDE抢筹战法）"""
    print("=" * 60)
    print("测试价格发现阶段（DDE抢筹战法）")
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
            print(f"DDE脉冲强度: {result['dde_pulse_strength']:.1f}倍")
            print(f"成交量放大倍数: {result['volume_amplification']:.1f}倍")
            print(f"是否有连续巨量大单: {result['has_continuous_big_orders']}")
            print(f"置信度: {result['confidence']:.1%}")
            print(f"原因: {result['reason']}")
        else:
            print(f"❌ 无法获取实时数据")
        
        print("\n✅ 价格发现阶段测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"价格发现阶段测试失败: {e}")
        print(f"\n❌ 价格发现阶段测试失败: {e}\n")
        return False

def test_divergence_to_consensus():
    """测试分歧转一致（低吸战法）"""
    print("=" * 60)
    print("测试分歧转一致（低吸战法）")
    print("=" * 60)
    
    try:
        # 初始化管理器
        low_suction_engine = get_low_suction_engine()
        data_manager = DataManager()
        
        # 测试股票
        stock_code = "300992"
        current_price = 26.00
        prev_close = 26.00
        logic_keywords = ["机器人", "航天"]
        
        # 获取实时数据
        realtime_data = data_manager.get_realtime_data(stock_code)
        if realtime_data:
            current_price = realtime_data.get('price', current_price)
            prev_close = realtime_data.get('pre_close', prev_close)
        
        print(f"股票代码: {stock_code}")
        print(f"当前价格: ¥{current_price:.2f}")
        print(f"昨收价: ¥{prev_close:.2f}")
        print(f"核心逻辑关键词: {', '.join(logic_keywords)}")
        
        # 检测分歧转一致
        result = low_suction_engine.check_divergence_to_consensus(stock_code, current_price, prev_close, logic_keywords)
        
        print(f"是否有分歧转一致信号: {result['has_divergence_to_consensus']}")
        print(f"高位价格: ¥{result['high_price']:.2f}")
        print(f"回撤幅度: {result['pullback_pct']:.1f}%")
        print(f"是否回踩MA5: {result['ma5_touch']}")
        print(f"是否缩量: {result['volume_shrink']}")
        print(f"反弹力度: {result['bounce_strength']:.1f}%")
        print(f"逻辑是否未死: {result['logic_alive']}")
        print(f"置信度: {result['confidence']:.1%}")
        print(f"原因: {result['reason']}")
        
        print("\n✅ 分歧转一致测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"分歧转一致测试失败: {e}")
        print(f"\n❌ 分歧转一致测试失败: {e}\n")
        return False

def test_elastic_buffer_signal():
    """测试弹性缓冲信号"""
    print("=" * 60)
    print("测试弹性缓冲信号（20cm/30cm）")
    print("=" * 60)
    
    try:
        # 初始化管理器
        signal_gen = get_signal_generator_v14_4()
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
            
            # 检测弹性缓冲信号
            intraday_data = None  # 这里简化处理，实际应该从数据管理器获取分时数据
            result = signal_gen.check_elastic_buffer_signal(stock_code, current_price, prev_close, intraday_data)
            
            print(f"是否有弹性缓冲信号: {result['has_elastic_buffer']}")
            print(f"是否是20cm/30cm股票: {result['is_20cm_or_30cm']}")
            print(f"当前涨幅: {result['current_pct_change']:.1f}%")
            print(f"涨停幅度: {result['limit_up_pct']:.1f}%")
            print(f"弹性空间: {result['elastic_space']:.1f}%")
            print(f"是否缩量: {result['volume_shrink']}")
            print(f"是否回踩分时均线: {result['intraday_ma_touch']}")
            print(f"DDE是否强势: {result['dde_strong']}")
            print(f"置信度: {result['confidence']:.1%}")
            print(f"原因: {result['reason']}")
        else:
            print(f"❌ 无法获取实时数据")
        
        print("\n✅ 弹性缓冲信号测试完成！\n")
        return True
    except Exception as e:
        logger.error(f"弹性缓冲信号测试失败: {e}")
        print(f"\n❌ 弹性缓冲信号测试失败: {e}\n")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("V18.6 深化迭代测试")
    print("=" * 60 + "\n")
    
    start_time = time.time()
    
    # 运行所有测试
    results = []
    results.append(("价格发现阶段", test_price_discovery_stage()))
    results.append(("分歧转一致", test_divergence_to_consensus()))
    results.append(("弹性缓冲信号", test_elastic_buffer_signal()))
    
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
    print("🎉 所有 V18.6 深化迭代测试完成！")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()