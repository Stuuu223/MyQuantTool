"""
测试三层数据融合分析工具
"""

from tools.stock_analyzer import UnifiedStockAnalyzer

def test_basic_call():
    """基本调用测试"""
    print("="*80)
    print("测试1: 基本调用（自动模式）")
    print("="*80)
    
    analyzer = UnifiedStockAnalyzer()
    result = analyzer.analyze(
        stock_code='300997',
        mode='auto',  # 自动判断场景
        position=0.0,  # 当前无持仓
        entry_price=None,  # 无建仓价
        output_format='both'  # 同时输出JSON和TXT
    )
    
    print(f"\n调用结果: {'成功' if result['success'] else '失败'}")
    if result['success']:
        print(f"分析模式: {result.get('mode')}")
        print(f"交易阶段: {result.get('phase')}")
    
    return result

def test_with_position():
    """带持仓调用测试"""
    print("\n" + "="*80)
    print("测试2: 带持仓调用")
    print("="*80)
    
    analyzer = UnifiedStockAnalyzer()
    result = analyzer.analyze(
        stock_code='300997',
        mode='auto',
        position=0.3,  # 30%持仓
        entry_price=24.5,  # 建仓价24.5元
        output_format='both'
    )
    
    print(f"\n调用结果: {'成功' if result['success'] else '失败'}")
    if result['success']:
        print(f"当前持仓: {result.get('position_info', {}).get('current_position'):.0%}")
    
    return result

def test_manual_mode():
    """手动指定模式调用测试"""
    print("\n" + "="*80)
    print("测试3: 手动指定历史分析模式")
    print("="*80)
    
    analyzer = UnifiedStockAnalyzer()
    result = analyzer.analyze(
        stock_code='300997',
        mode='realtime',  # 使用实时分析
        output_format='both'
    )
    
    print(f"\n调用结果: {'成功' if result['success'] else '失败'}")
    
    return result

if __name__ == '__main__':
    # 运行测试
    test_basic_call()
    test_with_position()
    test_manual_mode()
    
    print("\n" + "="*80)
    print("所有测试完成！")
    print("="*80)
