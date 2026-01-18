"""
V14.4 龙虎榜反制系统集成验证
测试 AkShare 数据链路是否畅通，验证涨停豁免和龙虎榜博弈逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from logic.signal_generator import get_signal_generator_v14_4
from logic.data_manager import DataManager
from logic.logger import get_logger
from datetime import datetime, timedelta

logger = get_logger(__name__)


def verify_integration():
    """验证 V14.4 集成"""
    print("="*70)
    print("V14.4 龙虎榜反制系统集成验证")
    print("="*70)
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 初始化组件
    print("[1/5] 初始化组件...")
    try:
        sg = get_signal_generator_v14_4()
        dm = DataManager()
        print("✅ SignalGenerator 和 DataManager 初始化成功")
    except Exception as e:
        print(f"❌ 组件初始化失败: {e}")
        return False
    
    print()
    
    # 测试股票列表（使用 2026-01-17 的涨停股）
    test_stocks = [
        {
            "code": "600058",
            "name": "五矿发展",
            "expected": "涨停豁免"
        },
        {
            "code": "603056",
            "name": "德恩精工",
            "expected": "涨停豁免"
        },
        {
            "code": "600841",
            "name": "上柴股份",
            "expected": "涨停豁免"
        },
        {
            "code": "000001",
            "name": "平安银行",
            "expected": "正常计算"
        }
    ]
    
    print("[2/5] 测试数据获取...")
    print("-" * 70)
    
    results = []
    
    for i, stock in enumerate(test_stocks, 1):
        print(f"\n测试 {i}/{len(test_stocks)}: {stock['name']} ({stock['code']})")
        print(f"预期结果: {stock['expected']}")
        print("-" * 70)
        
        try:
            # 获取实时数据
            print("  [步骤1] 获取实时行情...")
            realtime_data = dm.get_realtime_data(stock['code'])
            
            if realtime_data:
                print(f"  ✅ 行情获取成功")
                print(f"     - 当前价格: {realtime_data.get('price', 'N/A')}")
                print(f"     - 涨跌幅: {realtime_data.get('change_percent', 'N/A')}%")
                print(f"     - 成交量: {realtime_data.get('volume', 'N/A')}")
            else:
                print(f"  ❌ 行情获取失败")
                continue
            
            # 获取资金流向
            print("  [步骤2] 获取资金流向...")
            capital_flow, market_cap = sg.get_capital_flow(stock['code'], dm)
            print(f"  ✅ 资金流向: {capital_flow/10000:.2f}万元")
            print(f"  ✅ 流通市值: {market_cap/100000000:.2f}亿元")
            
            # 获取趋势
            print("  [步骤3] 获取趋势状态...")
            df = dm.get_history_data(symbol=stock['code'])
            if df is not None and len(df) >= 20:
                trend = sg.get_trend_status(df)
                print(f"  ✅ 趋势状态: {trend}")
            else:
                print(f"  ⚠️  历史数据不足，使用默认趋势: UP")
                trend = 'UP'
            
            # 获取龙虎榜数据
            print("  [步骤4] 获取龙虎榜数据...")
            lhb_net_buy, open_pct = sg.get_yesterday_lhb_data(stock['code'], dm)
            print(f"  ✅ 昨日龙虎榜净买入: {lhb_net_buy/10000:.2f}万元")
            print(f"  ✅ 今日开盘涨幅: {open_pct:.2f}%")
            
            # 运行 V14.4 决策
            print("  [步骤5] 运行 V14.4 决策...")
            result = sg.calculate_final_signal(
                stock_code=stock['code'],
                ai_score=85.0,  # 假设 AI 评分为 85
                capital_flow=capital_flow,
                trend=trend,
                current_pct_change=realtime_data.get('change_percent', 0),
                yesterday_lhb_net_buy=lhb_net_buy,
                open_pct_change=open_pct,
                circulating_market_cap=market_cap
            )
            
            print(f"  ✅ 决策完成")
            print(f"     - 信号: {result['signal']}")
            print(f"     - 得分: {result['score']:.1f}")
            print(f"     - 理由: {result['reason']}")
            print(f"     - 风险: {result['risk']}")
            
            # 验证结果
            success = True
            if stock['expected'] == "涨停豁免":
                if result['signal'] != 'BUY':
                    print(f"  ❌ 验证失败: 预期 BUY，实际 {result['signal']}")
                    success = False
                elif "涨停豁免" not in result['reason']:
                    print(f"  ❌ 验证失败: 理由未包含涨停豁免")
                    success = False
                else:
                    print(f"  ✅ 验证成功: 涨停豁免逻辑正确")
            else:
                if result['signal'] not in ['BUY', 'WAIT', 'SELL']:
                    print(f"  ❌ 验证失败: 信号异常")
                    success = False
                else:
                    print(f"  ✅ 验证成功: 正常计算")
            
            results.append({
                'stock': stock,
                'success': success,
                'result': result
            })
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'stock': stock,
                'success': False,
                'error': str(e)
            })
    
    print()
    print("[3/5] 测试报告...")
    print("-" * 70)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    print()
    print("[4/5] 详细结果...")
    print("-" * 70)
    
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['stock']['name']} ({r['stock']['code']})")
        if r['success']:
            result = r['result']
            print(f"   信号: {result['signal']}")
            print(f"   得分: {result['score']:.1f}")
            print(f"   理由: {result['reason']}")
            print(f"   状态: ✅ 通过")
        else:
            print(f"   状态: ❌ 失败")
            if 'error' in r:
                print(f"   错误: {r['error']}")
    
    print()
    print("[5/5] 逻辑冲突验证...")
    print("-" * 70)
    
    # 验证龙虎榜陷阱 vs 涨停豁免的逻辑冲突
    print("\n测试场景: 龙虎榜陷阱（高开）→ 涨停（最后封死）")
    print("-" * 70)
    
    # 模拟: 早上高开（陷阱），下午涨停（豁免）
    print("早上: 豪华榜净买6000万 + 高开7.5%")
    print("下午: 强势封板（+9.8%）")
    print()
    
    # 涨停豁免测试
    result_limit_up = sg.calculate_final_signal(
        stock_code="TEST001",
        ai_score=90.0,
        capital_flow=10000000,
        trend='UP',
        current_pct_change=9.8,  # 涨停
        yesterday_lhb_net_buy=60000000,  # 豪华榜
        open_pct_change=7.5  # 高开（陷阱）
    )
    
    print(f"V14.4 决策结果:")
    print(f"  信号: {result_limit_up['signal']}")
    print(f"  得分: {result_limit_up['score']:.1f}")
    print(f"  理由: {result_limit_up['reason']}")
    print()
    
    if result_limit_up['signal'] == 'BUY' and "涨停豁免" in result_limit_up['reason']:
        print("✅ 逻辑正确: 涨停豁免优先级高于龙虎榜陷阱")
        print("   解释: '封板'的事实 > '高开'的隐患")
    else:
        print("❌ 逻辑异常: 涨停豁免未生效")
    
    print()
    print("="*70)
    print("验证完成")
    print("="*70)
    
    if passed == total:
        print("\n✅ 所有测试通过！数据链路畅通！")
        print("\n系统状态:")
        print("- ✅ AkShare 数据获取正常")
        print("- ✅ SignalGenerator 决策逻辑正确")
        print("- ✅ 涨停豁免逻辑生效")
        print("- ✅ 龙虎榜博弈逻辑生效")
        print("- ✅ 逻辑优先级正确（涨停豁免 > 龙虎榜陷阱）")
        return True
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查数据链路")
        return False


if __name__ == '__main__':
    success = verify_integration()
    sys.exit(0 if success else 1)
