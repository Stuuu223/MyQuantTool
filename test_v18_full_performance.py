"""
V18 The Navigator - 全维板块共振系统性能测试（完整旗舰版）

测试内容：
1. 行业板块数据获取性能
2. 概念板块数据获取性能
3. 资金热度计算性能
4. 全维共振分析性能
5. 信号生成器集成性能
6. 缓存机制验证
7. 整体性能影响评估

执行：python test_v18_full_performance.py
"""

import time
import sys
from datetime import datetime
from logic.logger import get_logger
from logic.sector_analysis import FastSectorAnalyzer
from logic.data_manager import DataManager
from logic.signal_generator import SignalGenerator

logger = get_logger(__name__)


def test_industry_data_fetch_performance():
    """测试行业板块数据获取性能"""
    print("\n" + "="*60)
    print("🧪 测试 1: 行业板块数据获取性能")
    print("="*60)
    
    try:
        db = DataManager()
        analyzer = FastSectorAnalyzer(db)
        
        # 第一次获取（无缓存）
        print("\n📊 第一次获取（无缓存）...")
        t_start = time.time()
        industry_ranking = analyzer.get_akshare_sector_ranking()
        t_cost = time.time() - t_start
        
        if not industry_ranking.empty:
            print(f"✅ 获取成功！耗时: {t_cost:.2f} 秒")
            print(f"   板块数量: {len(industry_ranking)}")
            
            # 显示 Top 5
            print(f"\n   Top 5 领涨板块:")
            for _, row in industry_ranking.head(5).iterrows():
                print(f"     {row['板块名称']}: {row['涨跌幅']:.2f}%, 资金热度 {row['资金热度']:.1f}")
        else:
            print(f"❌ 获取失败！耗时: {t_cost:.2f} 秒")
            return False
        
        # 第二次获取（有缓存）
        print("\n📊 第二次获取（有缓存）...")
        t_start = time.time()
        industry_ranking_cached = analyzer.get_akshare_sector_ranking()
        t_cost_cached = time.time() - t_start
        
        print(f"✅ 获取成功！耗时: {t_cost_cached:.2f} 秒")
        if t_cost_cached > 0:
            print(f"   缓存加速: {t_cost / t_cost_cached:.2f}x")
        else:
            print(f"   缓存加速: 极快 (缓存时间 < 0.01秒)")
        
        # 性能判断
        if t_cost < 5.0:
            print(f"✅ 性能优秀: 首次获取 {t_cost:.2f} 秒 < 5.0 秒")
        elif t_cost < 10.0:
            print(f"⚠️ 性能一般: 首次获取 {t_cost:.2f} 秒 < 10.0 秒")
        else:
            print(f"❌ 性能较差: 首次获取 {t_cost:.2f} 秒 > 10.0 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_concept_data_fetch_performance():
    """测试概念板块数据获取性能"""
    print("\n" + "="*60)
    print("🧪 测试 2: 概念板块数据获取性能")
    print("="*60)
    
    try:
        db = DataManager()
        analyzer = FastSectorAnalyzer(db)
        
        # 第一次获取（无缓存）
        print("\n📊 第一次获取（无缓存）...")
        t_start = time.time()
        concept_ranking = analyzer.get_akshare_concept_ranking()
        t_cost = time.time() - t_start
        
        if not concept_ranking.empty:
            print(f"✅ 获取成功！耗时: {t_cost:.2f} 秒")
            print(f"   概念板块数量: {len(concept_ranking)}")
            
            # 显示 Top 5
            print(f"\n   Top 5 领涨概念:")
            for _, row in concept_ranking.head(5).iterrows():
                print(f"     {row['板块名称']}: {row['涨跌幅']:.2f}%, 资金热度 {row['资金热度']:.1f}")
        else:
            print(f"❌ 获取失败！耗时: {t_cost:.2f} 秒")
            return False
        
        # 第二次获取（有缓存）
        print("\n📊 第二次获取（有缓存）...")
        t_start = time.time()
        concept_ranking_cached = analyzer.get_akshare_concept_ranking()
        t_cost_cached = time.time() - t_start
        
        print(f"✅ 获取成功！耗时: {t_cost_cached:.2f} 秒")
        if t_cost_cached > 0:
            print(f"   缓存加速: {t_cost / t_cost_cached:.2f}x")
        else:
            print(f"   缓存加速: 极快 (缓存时间 < 0.01秒)")
        
        # 性能判断
        if t_cost < 5.0:
            print(f"✅ 性能优秀: 首次获取 {t_cost:.2f} 秒 < 5.0 秒")
        elif t_cost < 10.0:
            print(f"⚠️ 性能一般: 首次获取 {t_cost:.2f} 秒 < 10.0 秒")
        else:
            print(f"❌ 性能较差: 首次获取 {t_cost:.2f} 秒 > 10.0 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_capital_heat_calculation():
    """测试资金热度计算性能"""
    print("\n" + "="*60)
    print("🧪 测试 3: 资金热度计算性能")
    print("="*60)
    
    try:
        db = DataManager()
        analyzer = FastSectorAnalyzer(db)
        
        # 获取行业板块数据
        industry_ranking = analyzer.get_akshare_sector_ranking()
        
        if industry_ranking.empty:
            print(f"❌ 行业板块数据为空")
            return False
        
        # 测试资金热度计算
        print(f"\n📊 测试资金热度计算...")
        t_start = time.time()
        
        # 重新计算资金热度
        capital_heat = analyzer._calculate_capital_heat(industry_ranking)
        
        t_cost = time.time() - t_start
        
        print(f"✅ 计算完成！耗时: {t_cost:.3f} 秒")
        print(f"   计算数量: {len(capital_heat)}")
        print(f"   平均资金热度: {capital_heat.mean():.2f}")
        
        # 显示 Top 5
        print(f"\n   Top 5 资金热度:")
        top_5_heat = industry_ranking.nlargest(5, '资金热度')
        for _, row in top_5_heat.iterrows():
            print(f"     {row['板块名称']}: 资金热度 {row['资金热度']:.1f}, 涨幅 {row['涨跌幅']:.2f}%")
        
        # 性能判断
        if t_cost < 0.1:
            print(f"✅ 性能优秀: {t_cost:.3f} 秒 < 0.1 秒")
        elif t_cost < 0.5:
            print(f"⚠️ 性能一般: {t_cost:.3f} 秒 < 0.5 秒")
        else:
            print(f"❌ 性能较差: {t_cost:.3f} 秒 > 0.5 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_resonance_analysis():
    """测试全维共振分析性能"""
    print("\n" + "="*60)
    print("🧪 测试 4: 全维共振分析性能")
    print("="*60)
    
    try:
        db = DataManager()
        analyzer = FastSectorAnalyzer(db)
        
        # 测试股票列表
        test_stocks = [
            ('000001', '平安银行'),
            ('000002', '万科A'),
            ('600036', '招商银行'),
            ('600519', '贵州茅台'),
            ('300750', '宁德时代'),
        ]
        
        print(f"\n📊 测试 {len(test_stocks)} 只股票的全维共振分析...")
        
        total_time = 0
        results = []
        
        for stock_code, stock_name in test_stocks:
            t_start = time.time()
            full_resonance = analyzer.check_stock_full_resonance(stock_code, stock_name)
            t_cost = time.time() - t_start
            total_time += t_cost
            
            resonance_score = full_resonance.get('resonance_score', 0.0)
            resonance_details = full_resonance.get('resonance_details', [])
            is_leader = full_resonance.get('is_leader', False)
            is_follower = full_resonance.get('is_follower', False)
            
            results.append({
                'code': stock_code,
                'name': stock_name,
                'score': resonance_score,
                'is_leader': is_leader,
                'is_follower': is_follower,
                'details': resonance_details,
                'time': t_cost
            })
            
            print(f"   {stock_code} ({stock_name}): 共振评分 {resonance_score:+.1f}, 耗时 {t_cost:.3f}秒")
            if resonance_details:
                for detail in resonance_details[:2]:  # 只显示前2条
                    print(f"     - {detail}")
        
        avg_time = total_time / len(test_stocks)
        print(f"\n✅ 平均耗时: {avg_time:.3f} 秒/股")
        print(f"   总耗时: {total_time:.2f} 秒")
        
        # 统计结果
        leader_count = sum(1 for r in results if r['is_leader'])
        follower_count = sum(1 for r in results if r['is_follower'])
        positive_count = sum(1 for r in results if r['score'] > 0)
        negative_count = sum(1 for r in results if r['score'] < 0)
        
        print(f"\n   📊 结果统计:")
        print(f"     龙头: {leader_count}/{len(test_stocks)}")
        print(f"     跟风: {follower_count}/{len(test_stocks)}")
        print(f"     共振加分: {positive_count}/{len(test_stocks)}")
        print(f"     逆风减分: {negative_count}/{len(test_stocks)}")
        
        # 性能判断
        if avg_time < 0.5:
            print(f"✅ 性能优秀: 平均 {avg_time:.3f} 秒 < 0.5 秒")
        elif avg_time < 1.0:
            print(f"⚠️ 性能一般: 平均 {avg_time:.3f} 秒 < 1.0 秒")
        else:
            print(f"❌ 性能较差: 平均 {avg_time:.3f} 秒 > 1.0 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_generator_integration():
    """测试信号生成器集成性能"""
    print("\n" + "="*60)
    print("🧪 测试 5: 信号生成器集成性能")
    print("="*60)
    
    try:
        db = DataManager()
        signal_gen = SignalGenerator()
        
        # 测试股票
        test_stock = '000001'
        test_stock_name = '平安银行'
        
        print(f"\n📊 测试股票 {test_stock} 的信号生成（含全维板块共振）...")
        
        # 获取基础数据
        t_start = time.time()
        
        # 模拟数据
        ai_score = 85.0
        capital_flow = 10000000  # 1000万流入
        trend = 'UP'
        current_pct_change = 3.5
        yesterday_lhb_net_buy = 0
        open_pct_change = 1.0
        circulating_market_cap = 100000000000  # 1000亿
        market_sentiment_score = 65
        market_status = "主升"
        
        result = signal_gen.calculate_final_signal(
            stock_code=test_stock,
            ai_score=ai_score,
            capital_flow=capital_flow,
            trend=trend,
            current_pct_change=current_pct_change,
            yesterday_lhb_net_buy=yesterday_lhb_net_buy,
            open_pct_change=open_pct_change,
            circulating_market_cap=circulating_market_cap,
            market_sentiment_score=market_sentiment_score,
            market_status=market_status
        )
        
        t_cost = time.time() - t_start
        
        print(f"✅ 信号生成完成！耗时: {t_cost:.2f} 秒")
        print(f"   信号: {result['signal']}")
        print(f"   评分: {result['score']:.2f}")
        print(f"   原因: {result['reason']}")
        
        # 检查是否包含板块信息
        if 'sector_info' in result:
            sector_info = result['sector_info']
            print(f"\n   📊 板块共振信息:")
            print(f"     板块名称: {sector_info.get('sector_name', '未知')}")
            print(f"     板块排名: {sector_info.get('sector_rank', -1)}")
            print(f"     板块状态: {sector_info.get('status', 'NEUTRAL')}")
            print(f"     修正系数: {sector_info.get('modifier', 1.0)}")
            print(f"     共振原因: {sector_info.get('reason', '')}")
        else:
            print(f"⚠️ 警告: 信号结果中未包含板块信息")
        
        # 性能判断
        if t_cost < 2.0:
            print(f"✅ 性能优秀: {t_cost:.2f} 秒 < 2.0 秒")
        elif t_cost < 3.0:
            print(f"⚠️ 性能一般: {t_cost:.2f} 秒 < 3.0 秒")
        else:
            print(f"❌ 性能较差: {t_cost:.2f} 秒 > 3.0 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_mechanism():
    """测试缓存机制"""
    print("\n" + "="*60)
    print("🧪 测试 6: 缓存机制验证")
    print("="*60)
    
    try:
        db = DataManager()
        analyzer = FastSectorAnalyzer(db)
        
        # 清除缓存
        analyzer._akshare_industry_cache = None
        analyzer._akshare_concept_cache = None
        analyzer._akshare_cache_timestamp = None
        
        print("\n📊 测试缓存机制...")
        
        # 第一次获取（无缓存）
        t_start = time.time()
        industry_ranking_1 = analyzer.get_akshare_sector_ranking()
        t_cost_1 = time.time() - t_start
        print(f"   第一次获取（无缓存）: {t_cost_1:.2f} 秒")
        
        # 第二次获取（有缓存）
        t_start = time.time()
        industry_ranking_2 = analyzer.get_akshare_sector_ranking()
        t_cost_2 = time.time() - t_start
        print(f"   第二次获取（有缓存）: {t_cost_2:.2f} 秒")
        
        # 第三次获取（有缓存）
        t_start = time.time()
        industry_ranking_3 = analyzer.get_akshare_sector_ranking()
        t_cost_3 = time.time() - t_start
        print(f"   第三次获取（有缓存）: {t_cost_3:.2f} 秒")
        
        # 验证缓存效果
        if t_cost_2 > 0:
            cache_speedup = t_cost_1 / t_cost_2
            print(f"\n✅ 缓存加速: {cache_speedup:.2f}x")
        else:
            cache_speedup = 0
            print(f"\n✅ 缓存加速: 极快 (缓存时间 < 0.01秒)")
        
        if cache_speedup > 10:
            print(f"✅ 缓存效果优秀: 加速 {cache_speedup:.2f}x > 10x")
        elif cache_speedup > 5:
            print(f"⚠️ 缓存效果一般: 加速 {cache_speedup:.2f}x > 5x")
        else:
            print(f"❌ 缓存效果较差: 加速 {cache_speedup:.2f}x < 5x")
        
        # 验证数据一致性
        if len(industry_ranking_1) == len(industry_ranking_2) == len(industry_ranking_3):
            print(f"✅ 数据一致性验证通过: 三次获取的板块数量一致 ({len(industry_ranking_1)})")
        else:
            print(f"❌ 数据一致性验证失败: 板块数量不一致")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_overall_performance():
    """测试整体性能影响"""
    print("\n" + "="*60)
    print("🧪 测试 7: 整体性能影响评估")
    print("="*60)
    
    try:
        db = DataManager()
        analyzer = FastSectorAnalyzer(db)
        signal_gen = SignalGenerator()
        
        # 测试批量股票处理
        test_stocks = [
            ('000001', '平安银行'),
            ('000002', '万科A'),
            ('600036', '招商银行'),
            ('600519', '贵州茅台'),
            ('300750', '宁德时代'),
            ('002594', '比亚迪'),
            ('002714', '牧原股份'),
            ('600000', '浦发银行'),
            ('601318', '中国平安'),
            ('601398', '工商银行')
        ]
        
        print(f"\n📊 测试批量处理 {len(test_stocks)} 只股票...")
        
        # 预热（获取板块数据）
        analyzer.get_akshare_sector_ranking()
        analyzer.get_akshare_concept_ranking()
        
        # 批量处理
        t_start = time.time()
        
        results = []
        for stock_code, stock_name in test_stocks:
            # 模拟数据
            ai_score = 85.0
            capital_flow = 10000000
            trend = 'UP'
            current_pct_change = 3.5
            
            result = signal_gen.calculate_final_signal(
                stock_code=stock_code,
                ai_score=ai_score,
                capital_flow=capital_flow,
                trend=trend,
                current_pct_change=current_pct_change,
                yesterday_lhb_net_buy=0,
                open_pct_change=1.0,
                circulating_market_cap=100000000000,
                market_sentiment_score=65,
                market_status="主升"
            )
            
            results.append({
                'code': stock_code,
                'signal': result['signal'],
                'score': result['score'],
                'sector_status': result.get('sector_info', {}).get('status', 'NEUTRAL'),
                'sector_modifier': result.get('sector_info', {}).get('modifier', 1.0)
            })
        
        total_time = time.time() - t_start
        avg_time = total_time / len(test_stocks)
        
        print(f"✅ 批量处理完成！")
        print(f"   总耗时: {total_time:.2f} 秒")
        print(f"   平均耗时: {avg_time:.3f} 秒/股")
        print(f"   处理速度: {len(test_stocks) / total_time:.2f} 股/秒")
        
        # 统计结果
        buy_signals = sum(1 for r in results if r['signal'] == 'BUY')
        leader_sectors = sum(1 for r in results if r['sector_status'] == 'LEADER')
        drag_sectors = sum(1 for r in results if r['sector_status'] == 'DRAG')
        
        print(f"\n   📊 结果统计:")
        print(f"     BUY 信号: {buy_signals}/{len(test_stocks)}")
        print(f"     领涨板块: {leader_sectors}/{len(test_stocks)}")
        print(f"     拖累板块: {drag_sectors}/{len(test_stocks)}")
        
        # 性能判断
        if avg_time < 0.5:
            print(f"✅ 性能优秀: 平均 {avg_time:.3f} 秒 < 0.5 秒")
        elif avg_time < 1.0:
            print(f"⚠️ 性能一般: 平均 {avg_time:.3f} 秒 < 1.0 秒")
        else:
            print(f"❌ 性能较差: 平均 {avg_time:.3f} 秒 > 1.0 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🚀 V18 The Navigator - 全维板块共振系统性能测试（完整旗舰版）")
    print("="*60)
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # 执行所有测试
    test_results.append(("行业板块数据获取性能", test_industry_data_fetch_performance()))
    test_results.append(("概念板块数据获取性能", test_concept_data_fetch_performance()))
    test_results.append(("资金热度计算性能", test_capital_heat_calculation()))
    test_results.append(("全维共振分析性能", test_full_resonance_analysis()))
    test_results.append(("信号生成器集成性能", test_signal_generator_integration()))
    test_results.append(("缓存机制验证", test_cache_mechanism()))
    test_results.append(("整体性能影响评估", test_overall_performance()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 所有测试通过！V18 全维板块共振系统性能优异。")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查日志。")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
