"""
V9.0 游资掠食者系统测试脚本

测试内容：
1. 生死红线检测（退市风险、*ST）
2. 身份与涨幅错配检测
3. 资金结构恶化检测
4. 半路板战法逻辑
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.predator_system import PredatorSystem


def test_kill_switch():
    """测试生死红线检测功能"""
    print("=" * 60)
    print("测试 1: 生死红线检测")
    print("=" * 60)
    
    predator = PredatorSystem()
    
    # 测试用例1：正常股票
    stock_data = {
        'symbol': '301526',
        'name': '国际复材',
        'remark': ''
    }
    result = predator.check_kill_switch(stock_data)
    print(f"测试用例1（正常股票）:")
    print(f"  输入: {stock_data}")
    print(f"  触发: {result['triggered']}")
    print(f"  结果: {'✅ 通过' if not result['triggered'] else '❌ 失败'}")
    print()
    
    # 测试用例2：退市风险股票
    stock_data = {
        'symbol': '301526',
        'name': '国际复材',
        'remark': '存在退市风险'
    }
    result = predator.check_kill_switch(stock_data)
    print(f"测试用例2（退市风险股票）:")
    print(f"  输入: {stock_data}")
    print(f"  触发: {result['triggered']}")
    print(f"  关键词: {result['keywords']}")
    print(f"  理由: {result['reason']}")
    print(f"  结果: {'✅ 通过' if result['triggered'] else '❌ 失败'}")
    print()
    
    # 测试用例3：ST股票
    stock_data = {
        'symbol': 'ST123',
        'name': 'ST某某',
        'remark': ''
    }
    result = predator.check_kill_switch(stock_data)
    print(f"测试用例3（ST股票）:")
    print(f"  输入: {stock_data}")
    print(f"  触发: {result['triggered']}")
    print(f"  关键词: {result['keywords']}")
    print(f"  理由: {result['reason']}")
    print(f"  结果: {'✅ 通过' if result['triggered'] else '❌ 失败'}")
    print()


def test_identity_mismatch():
    """测试身份与涨幅错配检测功能"""
    print("=" * 60)
    print("测试 2: 身份与涨幅错配检测")
    print("=" * 60)
    
    predator = PredatorSystem()
    
    # 测试用例1：创业板股票涨幅10%（错配）
    stock_data = {
        'symbol': '301526',
        'name': '国际复材',
        'remark': ''
    }
    realtime_data = {
        'change_percent': 10.34,
        'volume_ratio': 1,
        'turnover_rate': 0
    }
    result = predator.check_identity_mismatch(stock_data, realtime_data)
    print(f"测试用例1（创业板股票涨幅10%）:")
    print(f"  输入: 股票代码 {stock_data['symbol']}, 涨幅 {realtime_data['change_percent']}%")
    print(f"  触发: {result['triggered']}")
    print(f"  理由: {result['reason']}")
    print(f"  警告: {result['warning']}")
    print(f"  结果: {'✅ 通过' if result['triggered'] else '❌ 失败'}")
    print()
    
    # 测试用例2：创业板股票涨幅19.8%（正常）
    stock_data = {
        'symbol': '301526',
        'name': '国际复材',
        'remark': ''
    }
    realtime_data = {
        'change_percent': 19.8,
        'volume_ratio': 1,
        'turnover_rate': 0
    }
    result = predator.check_identity_mismatch(stock_data, realtime_data)
    print(f"测试用例2（创业板股票涨幅19.8%）:")
    print(f"  输入: 股票代码 {stock_data['symbol']}, 涨幅 {realtime_data['change_percent']}%")
    print(f"  触发: {result['triggered']}")
    print(f"  结果: {'✅ 通过' if not result['triggered'] else '❌ 失败'}")
    print()
    
    # 测试用例3：主板股票涨幅10%（正常）
    stock_data = {
        'symbol': '600000',
        'name': '浦发银行',
        'remark': ''
    }
    realtime_data = {
        'change_percent': 10.0,
        'volume_ratio': 1,
        'turnover_rate': 0
    }
    result = predator.check_identity_mismatch(stock_data, realtime_data)
    print(f"测试用例3（主板股票涨幅10%）:")
    print(f"  输入: 股票代码 {stock_data['symbol']}, 涨幅 {realtime_data['change_percent']}%")
    print(f"  触发: {result['triggered']}")
    print(f"  结果: {'✅ 通过' if not result['triggered'] else '❌ 失败'}")
    print()


def test_fund_structure():
    """测试资金结构恶化检测功能"""
    print("=" * 60)
    print("测试 3: 资金结构恶化检测")
    print("=" * 60)
    
    predator = PredatorSystem()
    
    # 测试用例1：资金结构恶化
    fund_flow = {
        'main_net_outflow': 180000000,  # 主力净流出1.8亿
        'financing_buy': 50000000  # 融资买入5000万
    }
    result = predator.check_fund_structure(fund_flow)
    print(f"测试用例1（资金结构恶化）:")
    print(f"  输入: 主力净流出 {fund_flow['main_net_outflow']/10000:.0f}万, 融资买入 {fund_flow['financing_buy']/10000:.0f}万")
    print(f"  触发: {result['triggered']}")
    print(f"  理由: {result['reason']}")
    print(f"  警告: {result['warning']}")
    print(f"  结果: {'✅ 通过' if result['triggered'] else '❌ 失败'}")
    print()
    
    # 测试用例2：资金结构正常
    fund_flow = {
        'main_net_outflow': 5000000,  # 主力净流出500万
        'financing_buy': 10000000  # 融资买入1000万
    }
    result = predator.check_fund_structure(fund_flow)
    print(f"测试用例2（资金结构正常）:")
    print(f"  输入: 主力净流出 {fund_flow['main_net_outflow']/10000:.0f}万, 融资买入 {fund_flow['financing_buy']/10000:.0f}万")
    print(f"  触发: {result['triggered']}")
    print(f"  结果: {'✅ 通过' if not result['triggered'] else '❌ 失败'}")
    print()


def test_halfway_strategy():
    """测试半路板战法功能"""
    print("=" * 60)
    print("测试 4: 半路板战法")
    print("=" * 60)
    
    predator = PredatorSystem()
    
    # 测试用例1：创业板股票涨幅13%（符合半路板）
    stock_data = {
        'symbol': '301526',
        'name': '国际复材',
        'remark': ''
    }
    realtime_data = {
        'change_percent': 13.5,
        'volume_ratio': 3.5,
        'turnover_rate': 10.0
    }
    result = predator.analyze_halfway_strategy(stock_data, realtime_data)
    print(f"测试用例1（创业板股票涨幅13.5%）:")
    print(f"  输入: 股票代码 {stock_data['symbol']}, 涨幅 {realtime_data['change_percent']}%, 量比 {realtime_data['volume_ratio']}, 换手率 {realtime_data['turnover_rate']}%")
    print(f"  触发: {result['triggered']}")
    print(f"  评分: {result['score']}")
    print(f"  角色: {result['role']}")
    print(f"  信号: {result['signal']}")
    print(f"  置信度: {result['confidence']}")
    print(f"  建议仓位: {result['suggested_position']*100}%")
    print(f"  理由: {result['reason']}")
    print(f"  结果: {'✅ 通过' if result['triggered'] else '❌ 失败'}")
    print()
    
    # 测试用例2：创业板股票涨幅10%（不符合半路板）
    stock_data = {
        'symbol': '301526',
        'name': '国际复材',
        'remark': ''
    }
    realtime_data = {
        'change_percent': 10.0,
        'volume_ratio': 3.5,
        'turnover_rate': 10.0
    }
    result = predator.analyze_halfway_strategy(stock_data, realtime_data)
    print(f"测试用例2（创业板股票涨幅10%）:")
    print(f"  输入: 股票代码 {stock_data['symbol']}, 涨幅 {realtime_data['change_percent']}%")
    print(f"  触发: {result['triggered']}")
    print(f"  理由: {result['reason']}")
    print(f"  结果: {'✅ 通过' if not result['triggered'] else '❌ 失败'}")
    print()
    
    # 测试用例3：主板股票涨幅6%（符合半路板）
    stock_data = {
        'symbol': '600000',
        'name': '浦发银行',
        'remark': ''
    }
    realtime_data = {
        'change_percent': 6.5,
        'volume_ratio': 2.5,
        'turnover_rate': 8.0
    }
    result = predator.analyze_halfway_strategy(stock_data, realtime_data)
    print(f"测试用例3（主板股票涨幅6.5%）:")
    print(f"  输入: 股票代码 {stock_data['symbol']}, 涨幅 {realtime_data['change_percent']}%, 量比 {realtime_data['volume_ratio']}, 换手率 {realtime_data['turnover_rate']}%")
    print(f"  触发: {result['triggered']}")
    print(f"  评分: {result['score']}")
    print(f"  角色: {result['role']}")
    print(f"  信号: {result['signal']}")
    print(f"  置信度: {result['confidence']}")
    print(f"  建议仓位: {result['suggested_position']*100}%")
    print(f"  理由: {result['reason']}")
    print(f"  结果: {'✅ 通过' if result['triggered'] else '❌ 失败'}")
    print()


def test_analyze_stock():
    """测试完整股票分析功能"""
    print("=" * 60)
    print("测试 5: 完整股票分析")
    print("=" * 60)
    
    predator = PredatorSystem()
    
    # 测试用例：国际复材（触发生死红线）
    stock_data = {
        'symbol': '301526',
        'name': '国际复材',
        'remark': '存在退市风险'
    }
    realtime_data = {
        'change_percent': 10.34,
        'volume_ratio': 1,
        'turnover_rate': 0
    }
    fund_flow = {
        'main_net_outflow': 180000000,
        'financing_buy': 50000000
    }
    
    result = predator.analyze_stock(stock_data, realtime_data, fund_flow)
    print(f"测试用例（国际复材）:")
    print(f"  股票: {stock_data['name']} ({stock_data['symbol']})")
    print(f"  涨幅: {realtime_data['change_percent']}%")
    print(f"  评分: {result['score']}")
    print(f"  角色: {result['role']}")
    print(f"  信号: {result['signal']}")
    print(f"  置信度: {result['confidence']}")
    print(f"  理由: {result['reason']}")
    print(f"  警告: {result['warning']}")
    print(f"  建议仓位: {result['suggested_position']*100}%")
    print(f"  检查结果:")
    for check_name, check_result in result['checks'].items():
        print(f"    {check_name}: {'触发' if check_result.get('triggered', False) else '未触发'}")
    print(f"  结果: {'✅ 通过' if result['signal'] == 'SELL' else '❌ 失败'}")
    print()


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("V9.0 游资掠食者系统测试")
    print("=" * 60 + "\n")
    
    # 运行所有测试
    test_kill_switch()
    test_identity_mismatch()
    test_fund_structure()
    test_halfway_strategy()
    test_analyze_stock()
    
    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()