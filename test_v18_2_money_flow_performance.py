"""
V18.2 Money Flow Performance Test
板块资金流向过滤器性能测试

测试目标：
1. 测试 get_sector_fund_flow 方法的性能
2. 测试 check_stock_full_resonance 中资金流集成的性能
3. 验证资金流数据的准确性
4. 测试量价背离检测逻辑
"""

import time
import sys
from datetime import datetime
from logic.data_manager import DataManager
from logic.sector_analysis_streamlit import FastSectorAnalyzerStreamlit
from logic.logger import get_logger

logger = get_logger(__name__)


def test_sector_fund_flow_performance():
    """测试板块资金流向获取性能"""
    print("=" * 80)
    print("🧪 V18.2 Money Flow Performance Test - Sector Fund Flow")
    print("=" * 80)
    
    db = DataManager()
    analyzer = FastSectorAnalyzerStreamlit(db)
    
    # 测试板块列表
    test_sectors = [
        ('低空经济', 'concept'),
        ('人工智能', 'concept'),
        ('半导体', 'industry'),
        ('银行', 'industry')
    ]
    
    print("\n📊 测试板块资金流向获取性能...")
    
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
            print(f"  ⏱️  耗时: {t_cost:.3f}秒")
        else:
            print(f"  ⚠️  状态: {fund_flow.get('status', 'unknown')}")
            print(f"  ⚠️  原因: {fund_flow.get('reason', '')}")
            print(f"  ⏱️  耗时: {t_cost:.3f}秒")
    
    avg_time = total_time / len(test_sectors)
    
    print(f"\n📈 性能统计:")
    print(f"  - 总耗时: {total_time:.3f}秒")
    print(f"  - 平均耗时: {avg_time:.3f}秒")
    print(f"  - 成功率: {success_count}/{len(test_sectors)} ({success_count/len(test_sectors)*100:.1f}%)")
    
    # 性能判断
    if avg_time < 0.5:
        print(f"  ✅ 性能优秀: 平均耗时 {avg_time:.3f}秒 < 0.5秒")
    elif avg_time < 1.0:
        print(f"  ⚠️  性能良好: 平均耗时 {avg_time:.3f}秒 < 1.0秒")
    else:
        print(f"  ❌ 性能需优化: 平均耗时 {avg_time:.3f}秒 > 1.0秒")
    
    return avg_time < 1.0


def test_full_resonance_with_money_flow():
    """测试全维共振分析（含资金流）性能"""
    print("\n" + "=" * 80)
    print("🧪 V18.2 Money Flow Performance Test - Full Resonance with Money Flow")
    print("=" * 80)
    
    db = DataManager()
    analyzer = FastSectorAnalyzerStreamlit(db)
    
    # 测试股票列表
    test_stocks = [
        ('000001', '平安银行'),
        ('300750', '宁德时代'),
        ('002594', '比亚迪'),
        ('600519', '贵州茅台')
    ]
    
    print("\n📊 测试全维共振分析（含资金流）性能...")
    
    total_time = 0
    money_flow_count = 0
    
    for stock_code, stock_name in test_stocks:
        print(f"\n🔍 测试股票: {stock_code} {stock_name}")
        
        t_start = time.time()
        full_resonance = analyzer.check_stock_full_resonance(stock_code, stock_name)
        t_cost = time.time() - t_start
        
        total_time += t_cost
        
        resonance_score = full_resonance.get('resonance_score', 0.0)
        resonance_details = full_resonance.get('resonance_details', [])
        industry_info = full_resonance.get('industry_info', {})
        
        print(f"  ✅ 共振评分: {resonance_score:+.1f}")
        print(f"  ✅ 共振详情数: {len(resonance_details)}")
        
        # 检查是否包含资金流信息
        has_money_flow = 'fund_flow' in industry_info
        if has_money_flow:
            money_flow_count += 1
            fund_flow = industry_info['fund_flow']
            print(f"  💰 资金流: {fund_flow.get('net_inflow_yi', 0):.2f}亿 ({fund_flow.get('status', 'unknown')})")
        
        print(f"  ⏱️  耗时: {t_cost:.3f}秒")
        
        # 显示共振详情
        if resonance_details:
            print(f"  📋 共振详情:")
            for detail in resonance_details[:3]:  # 只显示前3条
                print(f"     - {detail}")
    
    avg_time = total_time / len(test_stocks)
    
    print(f"\n📈 性能统计:")
    print(f"  - 总耗时: {total_time:.3f}秒")
    print(f"  - 平均耗时: {avg_time:.3f}秒")
    print(f"  - 资金流覆盖率: {money_flow_count}/{len(test_stocks)} ({money_flow_count/len(test_stocks)*100:.1f}%)")
    
    # 性能判断
    if avg_time < 0.3:
        print(f"  ✅ 性能优秀: 平均耗时 {avg_time:.3f}秒 < 0.3秒")
    elif avg_time < 0.5:
        print(f"  ⚠️  性能良好: 平均耗时 {avg_time:.3f}秒 < 0.5秒")
    else:
        print(f"  ❌ 性能需优化: 平均耗时 {avg_time:.3f}秒 > 0.5秒")
    
    return avg_time < 0.5


def test_divergence_detection():
    """测试量价背离检测逻辑"""
    print("\n" + "=" * 80)
    print("🧪 V18.2 Money Flow Performance Test - Divergence Detection")
    print("=" * 80)
    
    db = DataManager()
    analyzer = FastSectorAnalyzerStreamlit(db)
    
    # 获取行业板块排名
    industry_ranking = analyzer.get_akshare_sector_ranking()
    
    if industry_ranking.empty:
        print("⚠️  无法获取行业板块数据")
        return False
    
    # 测试 Top 5 板块的资金流
    print("\n📊 测试 Top 5 板块的量价背离检测...")
    
    divergence_count = 0
    strong_inflow_count = 0
    
    for idx, row in industry_ranking.head(5).iterrows():
        sector_name = row['板块名称']
        rank = int(row['rank'])
        pct_chg = float(row['涨跌幅'])
        
        print(f"\n🔍 板块: {sector_name} (Rank {rank}, 涨幅 {pct_chg:.2f}%)")
        
        # 获取资金流
        fund_flow = analyzer.get_sector_fund_flow(sector_name, 'industry')
        net_inflow_yi = fund_flow.get('net_inflow_yi', 0)
        fund_status = fund_flow.get('status', 'unknown')
        
        print(f"  💰 净流入: {net_inflow_yi:.2f}亿 ({fund_status})")
        
        # 检测量价背离
        if fund_status == 'outflow' and rank <= 5:
            divergence_count += 1
            print(f"  ⚠️  [量价背离] 板块涨幅 Top 5 但资金流出!")
        elif fund_status == 'strong_inflow':
            strong_inflow_count += 1
            print(f"  ✅ [资金抱团] 板块净流入超10亿!")
    
    print(f"\n📈 检测结果:")
    print(f"  - 量价背离数量: {divergence_count}/5")
    print(f"  - 资金抱团数量: {strong_inflow_count}/5")
    
    return True


def test_unknown_status_handling():
    """测试 Unknown 状态处理"""
    print("\n" + "=" * 80)
    print("🧪 V18.2 Money Flow Performance Test - Unknown Status Handling")
    print("=" * 80)
    
    db = DataManager()
    analyzer = FastSectorAnalyzerStreamlit(db)
    
    # 测试新股（N开头）
    test_stocks = [
        ('N000001', '测试新股'),  # 模拟新股
        ('000001', '平安银行')  # 真实股票
    ]
    
    print("\n📊 测试 Unknown 状态处理...")
    
    for stock_code, stock_name in test_stocks:
        print(f"\n🔍 测试股票: {stock_code} {stock_name}")
        
        # 获取板块信息
        sector_info = analyzer.get_stock_sector_info(stock_code)
        sector_status = sector_info.get('status', 'unknown')
        
        print(f"  ✅ 板块状态: {sector_status}")
        
        if sector_status == 'unknown':
            print(f"  ⚠️  未知板块标记正常")
        elif sector_status == 'new':
            print(f"  🆕 新股标记正常")
        elif sector_status == 'known':
            print(f"  ✅ 已知板块标记正常")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("🚀 V18.2 Money Flow Performance Test Suite")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    test_results = []
    
    # 测试 1: 板块资金流向获取性能
    try:
        result = test_sector_fund_flow_performance()
        test_results.append(('板块资金流向获取性能', result))
    except Exception as e:
        logger.error(f"测试 1 失败: {e}")
        print(f"❌ 测试 1 失败: {e}")
        test_results.append(('板块资金流向获取性能', False))
    
    # 测试 2: 全维共振分析（含资金流）性能
    try:
        result = test_full_resonance_with_money_flow()
        test_results.append(('全维共振分析性能', result))
    except Exception as e:
        logger.error(f"测试 2 失败: {e}")
        print(f"❌ 测试 2 失败: {e}")
        test_results.append(('全维共振分析性能', False))
    
    # 测试 3: 量价背离检测
    try:
        result = test_divergence_detection()
        test_results.append(('量价背离检测', result))
    except Exception as e:
        logger.error(f"测试 3 失败: {e}")
        print(f"❌ 测试 3 失败: {e}")
        test_results.append(('量价背离检测', False))
    
    # 测试 4: Unknown 状态处理
    try:
        result = test_unknown_status_handling()
        test_results.append(('Unknown 状态处理', result))
    except Exception as e:
        logger.error(f"测试 4 失败: {e}")
        print(f"❌ 测试 4 失败: {e}")
        test_results.append(('Unknown 状态处理', False))
    
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
        print("\n🎉 所有测试通过！V18.2 Money Flow 功能正常。")
        return True
    else:
        print(f"\n⚠️  有 {total_count - passed_count} 个测试失败，请检查日志。")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)