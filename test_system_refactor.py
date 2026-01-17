#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V10 系统瘦身验证测试
验证 utils.py 和 config_system.py 的功能
"""

import sys
from datetime import datetime

def test_utils():
    """测试1：验证 Utils 工具类"""
    print("=" * 60)
    print("测试1：Utils 工具类验证")
    print("=" * 60)
    
    try:
        from logic.utils import Utils
        
        # 测试 safe_float
        print("🔍 测试 safe_float:")
        assert Utils.safe_float(None) == 0.0
        assert Utils.safe_float('') == 0.0
        assert Utils.safe_float('10.5') == 10.5
        assert Utils.safe_float('abc', 100) == 100.0
        print("  ✅ safe_float 正常")
        
        # 测试 calculate_amount
        print("🔍 测试 calculate_amount:")
        amount = Utils.calculate_amount(100, 10.5)  # 100手 * 100股 * 10.5元
        assert amount == 105000.0
        print(f"  ✅ calculate_amount: 100手 * 10.5元 = {amount}元")
        
        # 测试 get_beijing_time
        print("🔍 测试 get_beijing_time:")
        bj_time = Utils.get_beijing_time()
        print(f"  ✅ 北京时间: {bj_time}")
        
        # 测试 format_number
        print("🔍 测试 format_number:")
        assert Utils.format_number(10000) == "1.00万"
        assert Utils.format_number(100000000) == "1.00亿"
        print(f"  ✅ format_number: 10000 = {Utils.format_number(10000)}")
        print(f"  ✅ format_number: 1亿 = {Utils.format_number(100000000)}")
        
        # 测试 clean_stock_code
        print("🔍 测试 clean_stock_code:")
        assert Utils.clean_stock_code('sh600519') == '600519'
        assert Utils.clean_stock_code('sz000001') == '000001'
        assert Utils.clean_stock_code('600519') == '600519'
        print("  ✅ clean_stock_code 正常")
        
        # 测试 is_limit_up
        print("🔍 测试 is_limit_up:")
        assert Utils.is_limit_up(0.10, '600519') == True
        assert Utils.is_limit_up(0.20, '300001') == True
        assert Utils.is_limit_up(0.05, 'st600001') == True
        assert Utils.is_limit_up(0.08, '600519') == False
        print("  ✅ is_limit_up 正常")
        
        # 测试 is_limit_down
        print("🔍 测试 is_limit_down:")
        assert Utils.is_limit_down(-0.10, '600519') == True
        assert Utils.is_limit_down(-0.20, '300001') == True
        assert Utils.is_limit_down(-0.05, 'st600001') == True
        assert Utils.is_limit_down(-0.08, '600519') == False
        print("  ✅ is_limit_down 正常")
        
        # 测试 safe_divide
        print("🔍 测试 safe_divide:")
        assert Utils.safe_divide(10, 2) == 5.0
        assert Utils.safe_divide(10, 0) == 0.0
        assert Utils.safe_divide(None, 2) == 0.0
        print("  ✅ safe_divide 正常")
        
        print("\n🎉 Utils 工具类验证通过！")
        return True
    
    except Exception as e:
        print(f"\n❌ Utils 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """测试2：验证 Config 配置"""
    print("\n" + "=" * 60)
    print("测试2：Config 配置验证")
    print("=" * 60)
    
    try:
        import config_system as config
        
        # 测试市场情绪阈值
        print("🔍 测试市场情绪阈值:")
        print(f"  THRESHOLD_MARKET_HEAT_HIGH = {config.THRESHOLD_MARKET_HEAT_HIGH}")
        print(f"  THRESHOLD_MARKET_HEAT_LOW = {config.THRESHOLD_MARKET_HEAT_LOW}")
        print(f"  THRESHOLD_MALIGNANT_RATE = {config.THRESHOLD_MALIGNANT_RATE}")
        print("  ✅ 市场情绪阈值正常")
        
        # 测试风险扫描阈值
        print("🔍 测试风险扫描阈值:")
        print(f"  THRESHOLD_OPEN_KILL_GAP = {config.THRESHOLD_OPEN_KILL_GAP}")
        print(f"  THRESHOLD_FAKE_BOARD_RATIO = {config.THRESHOLD_FAKE_BOARD_RATIO}")
        print(f"  THRESHOLD_LATE_SNEAK_TIME = {config.THRESHOLD_LATE_SNEAK_TIME}")
        print("  ✅ 风险扫描阈值正常")
        
        # 测试技术分析阈值
        print("🔍 测试技术分析阈值:")
        print(f"  THRESHOLD_BIAS_HIGH = {config.THRESHOLD_BIAS_HIGH}")
        print(f"  THRESHOLD_BIAS_LOW = {config.THRESHOLD_BIAS_LOW}")
        print(f"  THRESHOLD_MA_PERIOD = {config.THRESHOLD_MA_PERIOD}")
        print("  ✅ 技术分析阈值正常")
        
        # 测试系统设置
        print("🔍 测试系统设置:")
        print(f"  MAX_SCAN_WORKERS = {config.MAX_SCAN_WORKERS}")
        print(f"  API_TIMEOUT = {config.API_TIMEOUT}")
        print(f"  MAX_SCAN_STOCKS = {config.MAX_SCAN_STOCKS}")
        print("  ✅ 系统设置正常")
        
        # 测试涨停阈值函数
        print("🔍 测试涨停阈值函数:")
        assert config.get_limit_up_threshold('600519') == config.LIMIT_UP_MAIN
        assert config.get_limit_up_threshold('300001') == config.LIMIT_UP_GEM
        assert config.get_limit_up_threshold('st600001') == config.LIMIT_UP_ST
        print("  ✅ get_limit_up_threshold 正常")
        
        # 测试跌停阈值函数
        print("🔍 测试跌停阈值函数:")
        assert config.get_limit_down_threshold('600519') == config.LIMIT_DOWN_MAIN
        assert config.get_limit_down_threshold('300001') == config.LIMIT_DOWN_GEM
        assert config.get_limit_down_threshold('st600001') == config.LIMIT_DOWN_ST
        print("  ✅ get_limit_down_threshold 正常")
        
        # 测试交易时间判断
        print("🔍 测试交易时间判断:")
        assert config.is_trading_time(570) == True   # 9:30
        assert config.is_trading_time(690) == False  # 11:30
        assert config.is_trading_time(780) == True   # 13:00
        assert config.is_trading_time(900) == False  # 15:00
        print("  ✅ is_trading_time 正常")
        
        # 测试时间权重
        print("🔍 测试时间权重:")
        assert config.get_time_weight(570) == 1.0   # 9:30-10:30
        assert config.get_time_weight(630) == 0.9   # 10:30-11:30
        assert config.get_time_weight(840) == 0.7   # 14:00-14:40
        assert config.get_time_weight(880) == 0.0   # 14:40-15:00
        print("  ✅ get_time_weight 正常")
        
        print("\n🎉 Config 配置验证通过！")
        return True
    
    except Exception as e:
        print(f"\n❌ Config 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """测试3：集成测试"""
    print("\n" + "=" * 60)
    print("测试3：集成测试")
    print("=" * 60)
    
    try:
        from logic.utils import Utils
        import config_system as config
        
        # 测试：使用 Utils 和 Config 计算封单金额
        print("🔍 测试：计算封单金额（使用 Utils）")
        volume_lots = 100
        price = 10.5
        amount = Utils.calculate_amount(volume_lots, price)
        formatted_amount = Utils.format_number(amount)
        print(f"  {volume_lots}手 * ¥{price} = ¥{amount} ({formatted_amount})")
        assert amount == 105000.0
        print("  ✅ 封单金额计算正常")
        
        # 测试：使用 Config 判断涨停
        print("🔍 测试：判断涨停（使用 Config）")
        change_pct = 0.10
        code = '600519'
        is_limit = config.get_limit_up_threshold(code) <= change_pct
        print(f"  {code} 涨幅 {Utils.format_percentage(change_pct)}, 涨停阈值 {config.get_limit_up_threshold(code)}, 是否涨停: {is_limit}")
        assert is_limit == True
        print("  ✅ 涨停判断正常")
        
        # 测试：使用 Config 判断交易时间
        print("🔍 测试：判断交易时间（使用 Config）")
        now = Utils.get_beijing_time()
        current_time_minutes = now.hour * 60 + now.minute
        is_trading = config.is_trading_time(current_time_minutes)
        time_weight = config.get_time_weight(current_time_minutes)
        print(f"  当前时间: {now.strftime('%H:%M')}")
        print(f"  是否交易: {is_trading}")
        print(f"  时间权重: {time_weight}")
        print("  ✅ 交易时间判断正常")
        
        print("\n🎉 集成测试通过！")
        return True
    
    except Exception as e:
        print(f"\n❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("V10 系统瘦身验证测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 执行所有测试
    results = {
        'Utils 工具类': test_utils(),
        'Config 配置': test_config(),
        '集成测试': test_integration()
    }
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {test_name}")
    
    # 最终结论
    print("\n" + "=" * 60)
    if all(results.values()):
        print("🎉 所有测试通过！")
        print("✅ Utils 工具类功能正常")
        print("✅ Config 配置管理正常")
        print("✅ 集成测试通过")
        print()
        print("系统瘦身成功！")
        print("下一步：在现有代码中应用 Utils 和 Config")
        return 0
    else:
        print("⚠️ 部分测试失败")
        print("请检查失败的测试项并修复")
        return 1

if __name__ == '__main__':
    sys.exit(main())
