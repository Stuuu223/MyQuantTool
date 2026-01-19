"""
V18.2 Money Flow Simple Test
简单的功能验证测试
"""

import time
from logic.data_manager import DataManager
from logic.sector_analysis_streamlit import FastSectorAnalyzerStreamlit
from logic.logger import get_logger

logger = get_logger(__name__)


def main():
    print("=" * 80)
    print("🧪 V18.2 Money Flow Simple Test")
    print("=" * 80)
    
    db = DataManager()
    analyzer = FastSectorAnalyzerStreamlit(db)
    
    # 测试 1: 获取板块资金流
    print("\n📊 测试 1: 获取板块资金流")
    print("-" * 80)
    
    t_start = time.time()
    fund_flow = analyzer.get_sector_fund_flow('半导体', 'industry')
    t_cost = time.time() - t_start
    
    print(f"板块: 半导体")
    print(f"净流入: {fund_flow.get('net_inflow_yi', 0):.2f}亿")
    print(f"状态: {fund_flow.get('status', 'unknown')}")
    print(f"原因: {fund_flow.get('reason', '')}")
    print(f"耗时: {t_cost:.3f}秒")
    
    # 测试 2: 全维共振分析
    print("\n📊 测试 2: 全维共振分析（含资金流）")
    print("-" * 80)
    
    t_start = time.time()
    full_resonance = analyzer.check_stock_full_resonance('000001', '平安银行')
    t_cost = time.time() - t_start
    
    resonance_score = full_resonance.get('resonance_score', 0.0)
    resonance_details = full_resonance.get('resonance_details', [])
    industry_info = full_resonance.get('industry_info', {})
    
    print(f"股票: 000001 平安银行")
    print(f"共振评分: {resonance_score:+.1f}")
    print(f"共振详情数: {len(resonance_details)}")
    print(f"耗时: {t_cost:.3f}秒")
    
    # 检查资金流信息
    if 'fund_flow' in industry_info:
        fund_flow = industry_info['fund_flow']
        print(f"\n💰 资金流信息:")
        print(f"  净流入: {fund_flow.get('net_inflow_yi', 0):.2f}亿")
        print(f"  状态: {fund_flow.get('status', 'unknown')}")
        print(f"  原因: {fund_flow.get('reason', '')}")
    else:
        print(f"\n⚠️  未获取到资金流信息")
    
    # 显示共振详情
    print(f"\n📋 共振详情:")
    for detail in resonance_details:
        print(f"  - {detail}")
    
    # 测试 3: Unknown 状态处理
    print("\n📊 测试 3: Unknown 状态处理")
    print("-" * 80)
    
    sector_info = analyzer.get_stock_sector_info('N000001')
    sector_status = sector_info.get('status', 'unknown')
    
    print(f"股票: N000001 (模拟新股)")
    print(f"板块状态: {sector_status}")
    
    if sector_status == 'unknown':
        print("✅ Unknown 状态标记正常")
    elif sector_status == 'new':
        print("✅ 新股标记正常")
    
    print("\n" + "=" * 80)
    print("✅ 简单测试完成")
    print("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()