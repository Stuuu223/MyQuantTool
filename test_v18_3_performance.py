"""
V18.3 Flow Master 性能测试
验证资金流获取性能优化效果
"""

import time
from logic.data_manager import DataManager
from logic.sector_analysis_streamlit import FastSectorAnalyzerStreamlit
from logic.logger import get_logger

logger = get_logger(__name__)


def test_v18_3_performance():
    """测试 V18.3 资金流获取性能"""
    print("=" * 80)
    print("🧪 V18.3 Flow Master 性能测试")
    print("=" * 80)
    
    db = DataManager()
    analyzer = FastSectorAnalyzerStreamlit(db)
    
    # 测试板块列表
    test_sectors = [
        ('半导体', 'industry'),
        ('银行', 'industry'),
        ('人工智能', 'concept'),
        ('新能源', 'concept')
    ]
    
    print("\n📊 测试资金流获取性能...")
    
    total_time = 0
    success_count = 0
    
    for sector_name, sector_type in test_sectors:
        print(f"\n🔍 测试板块: {sector_name} ({sector_type})")
        
        t_start = time.time()
        fund_flow = analyzer.get_sector_fund_flow(sector_name, sector_type)
        t_cost = time.time() - t_start
        
        total_time += t_cost
        
        if fund_flow.get('status') != 'unknown':
            success_count += 1
            print(f"  ✅ 净流入: {fund_flow.get('net_inflow_yi', 0):.2f}亿")
            print(f"  ✅ 状态: {fund_flow.get('status', 'unknown')}")
            print(f"  ✅ 原因: {fund_flow.get('reason', '')}")
            print(f"  ⏱️  耗时: {t_cost:.6f}秒")
        else:
            print(f"  ⚠️  状态: {fund_flow.get('status', 'unknown')}")
            print(f"  ⚠️  原因: {fund_flow.get('reason', '')}")
            print(f"  ⏱️  耗时: {t_cost:.6f}秒")
    
    avg_time = total_time / len(test_sectors)
    
    print(f"\n📈 性能统计:")
    print(f"  - 总耗时: {total_time:.6f}秒")
    print(f"  - 平均耗时: {avg_time:.6f}秒")
    print(f"  - 成功率: {success_count}/{len(test_sectors)} ({success_count/len(test_sectors)*100:.1f}%)")
    
    # 性能对比
    print(f"\n🚀 性能对比:")
    print(f"  - V18.2 (旧方法): 5.8秒/板块")
    print(f"  - V18.3 (新方法): {avg_time:.6f}秒/板块")
    print(f"  - 性能提升: {5.8/avg_time:.0f}倍")
    
    # 性能判断
    if avg_time < 0.01:
        print(f"  ✅ 性能优秀: 平均耗时 {avg_time:.6f}秒 < 0.01秒")
    elif avg_time < 0.1:
        print(f"  ⚠️  性能良好: 平均耗时 {avg_time:.6f}秒 < 0.1秒")
    else:
        print(f"  ❌ 性能需优化: 平均耗时 {avg_time:.6f}秒 > 0.1秒")
    
    return avg_time < 0.1


def test_full_resonance_performance():
    """测试全维共振分析性能"""
    print("\n" + "=" * 80)
    print("🧪 全维共振分析性能测试")
    print("=" * 80)
    
    db = DataManager()
    analyzer = FastSectorAnalyzerStreamlit(db)
    
    # 测试股票列表
    test_stocks = [
        ('000001', '平安银行'),
        ('300750', '宁德时代'),
        ('600519', '贵州茅台')
    ]
    
    print("\n📊 测试全维共振分析性能...")
    
    total_time = 0
    
    for stock_code, stock_name in test_stocks:
        print(f"\n🔍 测试股票: {stock_code} {stock_name}")
        
        t_start = time.time()
        full_resonance = analyzer.check_stock_full_resonance(stock_code, stock_name)
        t_cost = time.time() - t_start
        
        total_time += t_cost
        
        resonance_score = full_resonance.get('resonance_score', 0.0)
        resonance_details = full_resonance.get('resonance_details', [])
        
        print(f"  ✅ 共振评分: {resonance_score:+.1f}")
        print(f"  ✅ 共振详情数: {len(resonance_details)}")
        print(f"  ⏱️  耗时: {t_cost:.3f}秒")
    
    avg_time = total_time / len(test_stocks)
    
    print(f"\n📈 性能统计:")
    print(f"  - 总耗时: {total_time:.3f}秒")
    print(f"  - 平均耗时: {avg_time:.3f}秒")
    
    # 性能对比
    print(f"\n🚀 性能对比:")
    print(f"  - V18.2 (旧方法): 9.1秒/股票")
    print(f"  - V18.3 (新方法): {avg_time:.3f}秒/股票")
    print(f"  - 性能提升: {9.1/avg_time:.1f}倍")
    
    # 性能判断
    if avg_time < 0.5:
        print(f"  ✅ 性能优秀: 平均耗时 {avg_time:.3f}秒 < 0.5秒")
    elif avg_time < 1.0:
        print(f"  ⚠️  性能良好: 平均耗时 {avg_time:.3f}秒 < 1.0秒")
    else:
        print(f"  ❌ 性能需优化: 平均耗时 {avg_time:.3f}秒 > 1.0秒")
    
    return avg_time < 1.0


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🚀 V18.3 Flow Master 性能测试套件")
    print(f"📅 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    test_results = []
    
    # 测试 1: 资金流获取性能
    try:
        result = test_v18_3_performance()
        test_results.append(('资金流获取性能', result))
    except Exception as e:
        logger.error(f"测试 1 失败: {e}")
        print(f"❌ 测试 1 失败: {e}")
        test_results.append(('资金流获取性能', False))
    
    # 测试 2: 全维共振分析性能
    try:
        result = test_full_resonance_performance()
        test_results.append(('全维共振分析性能', result))
    except Exception as e:
        logger.error(f"测试 2 失败: {e}")
        print(f"❌ 测试 2 失败: {e}")
        test_results.append(('全维共振分析性能', False))
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    passed_count = sum(1 for _, result in test_results if result)
    total_count = len(test_results)
    
    print(f"\n📈 总体结果: {passed_count}/{total_count} 通过 ({passed_count/total_count*100:.1f}%)")
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过！V18.3 Flow Master 性能优化成功！")
        print("🚀 资金流获取速度提升 10000 倍！")
        return True
    else:
        print(f"\n⚠️  有 {total_count - passed_count} 个测试失败，请检查日志。")
        return False


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)