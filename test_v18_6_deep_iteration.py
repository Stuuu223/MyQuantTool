"""
V18.6 深化迭代测试脚本
测试所有 V18.6 新功能：
1. BUY_MODE 参数（DRAGON_CHASE / LOW_SUCTION）
2. 价格缓冲区
3. 高精度校准
4. 二波预期识别
5. 托单套路监控
6. 国家队护盘指纹
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

from logic.money_flow_master import get_money_flow_master
from logic.low_suction_engine import get_low_suction_engine
from logic.utils import Utils
from logic.second_wave_detector import get_second_wave_detector
from logic.fake_order_detector import get_fake_order_detector
from logic.national_team_guard import get_national_team_guard

def test_buy_mode():
    """测试 BUY_MODE 参数"""
    print("=" * 60)
    print("测试 BUY_MODE 参数（DRAGON_CHASE / LOW_SUCTION）")
    print("=" * 60)
    
    mfm = get_money_flow_master()
    
    # 测试用例1：DRAGON_CHASE 模式，DDE 为负应该被否决
    print("\n测试用例1：DRAGON_CHASE 模式，DDE 为负")
    is_vetoed, veto_reason = mfm.check_dde_veto('300992', 'BUY', 'DRAGON_CHASE')
    print(f"是否否决: {is_vetoed}")
    print(f"原因: {veto_reason}")
    
    # 测试用例2：LOW_SUCTION 模式，DDE 为负但斜率转正不应该被否决
    print("\n测试用例2：LOW_SUCTION 模式，DDE 为负但斜率转正")
    is_vetoed, veto_reason = mfm.check_dde_veto('300992', 'BUY', 'LOW_SUCTION')
    print(f"是否否决: {is_vetoed}")
    print(f"原因: {veto_reason}")
    
    print("\n" + "=" * 60)
    print("✅ BUY_MODE 参数测试完成！")
    print("=" * 60)

def test_price_buffer():
    """测试价格缓冲区"""
    print("\n" + "=" * 60)
    print("测试价格缓冲区")
    print("=" * 60)
    
    lse = get_low_suction_engine()
    
    # 测试价格缓冲区阈值
    print(f"\n分时均线价格缓冲区：")
    print(f"下限: {lse.INTRADAY_MA_TOUCH_THRESHOLD_MIN:.3f} ({lse.INTRADAY_MA_TOUCH_THRESHOLD_MIN*100:.1f}%)")
    print(f"上限: {lse.INTRADAY_MA_TOUCH_THRESHOLD_MAX:.3f} ({lse.INTRADAY_MA_TOUCH_THRESHOLD_MAX*100:.1f}%)")
    print(f"缓冲区宽度: {(lse.INTRADAY_MA_TOUCH_THRESHOLD_MAX - lse.INTRADAY_MA_TOUCH_THRESHOLD_MIN)*100:.1f}%")
    
    print("\n" + "=" * 60)
    print("✅ 价格缓冲区测试完成！")
    print("=" * 60)

def test_high_precision():
    """测试高精度校准"""
    print("\n" + "=" * 60)
    print("测试高精度校准")
    print("=" * 60)
    
    # 测试不同股票代码的涨停系数
    test_cases = [
        ('300992', '创业板'),
        ('688001', '科创板'),
        ('000001', '主板'),
        ('600000', '主板'),
        ('830799', '北交所'),
        ('ST0001', 'ST股')
    ]
    
    print("\n涨停系数测试：")
    for code, desc in test_cases:
        ratio = Utils.get_limit_ratio(code)
        print(f"{code} ({desc}): {ratio:.3f} ({(ratio-1)*100:.1f}%)")
    
    print("\n" + "=" * 60)
    print("✅ 高精度校准测试完成！")
    print("=" * 60)

def test_second_wave():
    """测试二波预期识别"""
    print("\n" + "=" * 60)
    print("测试二波预期识别")
    print("=" * 60)
    
    swd = get_second_wave_detector()
    
    # 测试用例：检查泰福泵业的二波预期
    print("\n测试用例：泰福泵业 (300992)")
    second_wave = swd.check_second_wave_signal('300992', 28.00, 26.00)
    print(f"是否有二波预期: {second_wave['has_second_wave']}")
    print(f"原因: {second_wave['reason']}")
    
    print("\n" + "=" * 60)
    print("✅ 二波预期识别测试完成！")
    print("=" * 60)

def test_fake_order():
    """测试托单套路监控"""
    print("\n" + "=" * 60)
    print("测试托单套路监控")
    print("=" * 60)
    
    fod = get_fake_order_detector()
    
    # 测试用例：检查泰福泵业的假单信号
    print("\n测试用例：泰福泵业 (300992)")
    fake_order = fod.check_fake_order_signal('300992', 'BUY')
    print(f"是否有假单: {fake_order['has_fake_order']}")
    print(f"是否是虚假繁荣: {fake_order['is_fake_prosperity']}")
    print(f"原因: {fake_order['reason']}")
    
    print("\n" + "=" * 60)
    print("✅ 托单套路监控测试完成！")
    print("=" * 60)

def test_national_team_guard():
    """测试国家队护盘指纹"""
    print("\n" + "=" * 60)
    print("测试国家队护盘指纹")
    print("=" * 60)
    
    ntg = get_national_team_guard()
    
    # 测试用例：检查国家队护盘信号
    print("\n测试用例：检查国家队护盘信号")
    national_team_guard = ntg.check_national_team_guard()
    print(f"是否在护盘: {national_team_guard['is_guarding']}")
    print(f"护盘强度: {national_team_guard['guard_strength']:.2f}")
    print(f"原因: {national_team_guard['reason']}")
    
    # 测试用例：检查全域共振信号
    print("\n测试用例：泰福泵业 (300992) 全域共振")
    global_resonance = ntg.check_global_resonance('300992', 26.00)
    print(f"是否有全域共振: {global_resonance['has_global_resonance']}")
    print(f"原因: {global_resonance['reason']}")
    
    print("\n" + "=" * 60)
    print("✅ 国家队护盘指纹测试完成！")
    print("=" * 60)

if __name__ == '__main__':
    test_buy_mode()
    test_price_buffer()
    test_high_precision()
    test_second_wave()
    test_fake_order()
    test_national_team_guard()
    
    print("\n" + "=" * 60)
    print("🎉 所有 V18.6 深化迭代测试完成！")
    print("=" * 60)