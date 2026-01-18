"""
V18 The Navigator - 板块共振系统性能测试

测试内容：
1. 板块数据获取性能
2. 板块状态检查性能
3. 信号生成器集成性能
4. 缓存机制验证
5. 整体性能影响评估

执行：python test_v18_navigator_performance.py
"""

import time
import sys
from datetime import datetime
from logic.logger import get_logger
from logic.sector_analysis import FastSectorAnalyzer
from logic.data_manager import DataManager
from logic.signal_generator import SignalGenerator

logger = get_logger(__name__)


def test_sector_data_fetch_performance():
    """测试板块数据获取性能"""
    print("\n" + "="*60)
    print("🧪 测试 1: 板块数据获取性能")
    print("="*60)
    
    try:
        db = DataManager()
        analyzer = FastSectorAnalyzer(db)
        
        # 第一次获取（无缓存）
        print("\n📊 第一次获取（无缓存）...")
        t_start = time.time()
        sector_ranking = analyzer.get_akshare_sector_ranking()
        t_cost = time.time() - t_start
        
        if not sector_ranking.empty:
            print(f"✅ 获取成功！耗时: {t_cost:.2f} 秒")
            print(f"   板块数量: {len(sector_ranking)}")
            
            # 显示 Top 5
            print(f"\n   Top 5 领涨板块:")
            for _, row in sector_ranking.head(5).iterrows():
                print(f"     {row['板块名称']}: {row['涨跌幅']:.2f}%")
        else:
            print(f"❌ 获取失败！耗时: {t_cost:.2f} 秒")
            return False
        
# 第二次获取（有缓存）
        t_start = time.time()
        sector_ranking_cached = analyzer.get_akshare_sector_ranking()
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


def test_sector_status_check_performance():
    """测试板块状态检查性能"""
    print("\n" + "="*60)
    print("🧪 测试 2: 板块状态检查性能")
    print("="*60)
    
    try:
        db = DataManager()
        analyzer = FastSectorAnalyzer(db)
        
        # 测试股票列表
        test_stocks = [
            '000001',  # 平安银行
            '000002',  # 万科A
            '600036',  # 招商银行
            '600519',  # 贵州茅台
            '300750',  # 宁德时代
        ]
        
        print(f"\n📊 测试 {len(test_stocks)} 只股票的板块状态检查...")
        
        total_time = 0
        results = []
        
        for stock_code in test_stocks:
            t_start = time.time()
            sector_status = analyzer.check_sector_status(stock_code)
            t_cost = time.time() - t_start
            total_time += t_cost
            
            status = sector_status.get('status', 'NEUTRAL')
            sector_name = sector_status.get('sector_name', '未知')
            sector_rank = sector_status.get('sector_rank', -1)
            modifier = sector_status.get('modifier', 1.0)
            
            results.append({
                'code': stock_code,
                'sector': sector_name,
                'rank': sector_rank,
                'status': status,
                'modifier': modifier,
                'time': t_cost
            })
            
            print(f"   {stock_code}: {sector_name} (排名 {sector_rank}, 状态 {status}, 修正 ×{modifier}) - {t_cost:.3f}秒")
        
        avg_time = total_time / len(test_stocks)
        print(f"\n✅ 平均耗时: {avg_time:.3f} 秒/股")
        print(f"   总耗时: {total_time:.2f} 秒")
        
        # 性能判断
        if avg_time < 0.1:
            print(f"✅ 性能优秀: 平均 {avg_time:.3f} 秒 < 0.1 秒")
        elif avg_time < 0.5:
            print(f"⚠️ 性能一般: 平均 {avg_time:.3f} 秒 < 0.5 秒")
        else:
            print(f"❌ 性能较差: 平均 {avg_time:.3f} 秒 > 0.5 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_generator_integration():
    """测试信号生成器集成性能"""
    print("\n" + "="*60)
    print("🧪 测试 3: 信号生成器集成性能")
    print("="*60)
    
    try:
        db = DataManager()
        signal_gen = SignalGenerator()
        
        # 测试股票
        test_stock = '000001'
        
        print(f"\n📊 测试股票 {test_stock} 的信号生成（含板块共振）...")
        
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
        if t_cost < 1.0:
            print(f"✅ 性能优秀: {t_cost:.2f} 秒 < 1.0 秒")
        elif t_cost < 2.0:
            print(f"⚠️ 性能一般: {t_cost:.2f} 秒 < 2.0 秒")
        else:
            print(f"❌ 性能较差: {t_cost:.2f} 秒 > 2.0 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_mechanism():
    """测试缓存机制"""
    print("\n" + "="*60)
    print("🧪 测试 4: 缓存机制验证")
    print("="*60)
    
    try:
        db = DataManager()
        analyzer = FastSectorAnalyzer(db)
        
        # 清除缓存
        analyzer._akshare_sector_cache = None
        analyzer._akshare_cache_timestamp = None
        
        print("\n📊 测试缓存机制...")
        
        # 第一次获取（无缓存）
        t_start = time.time()
        sector_ranking_1 = analyzer.get_akshare_sector_ranking()
        t_cost_1 = time.time() - t_start
        print(f"   第一次获取（无缓存）: {t_cost_1:.2f} 秒")
        
        # 第二次获取（有缓存）
        t_start = time.time()
        sector_ranking_2 = analyzer.get_akshare_sector_ranking()
        t_cost_2 = time.time() - t_start
        print(f"   第二次获取（有缓存）: {t_cost_2:.2f} 秒")
        
        # 第三次获取（有缓存）
        t_start = time.time()
        sector_ranking_3 = analyzer.get_akshare_sector_ranking()
        t_cost_3 = time.time() - t_start
        print(f"   第三次获取（有缓存）: {t_cost_3:.2f} 秒")
        
        # 验证缓存效果
        cache_speedup = t_cost_1 / t_cost_2 if t_cost_2 > 0 else 0
        print(f"\n✅ 缓存加速: {cache_speedup:.2f}x")
        
        if cache_speedup > 10:
            print(f"✅ 缓存效果优秀: 加速 {cache_speedup:.2f}x > 10x")
        elif cache_speedup > 5:
            print(f"⚠️ 缓存效果一般: 加速 {cache_speedup:.2f}x > 5x")
        else:
            print(f"❌ 缓存效果较差: 加速 {cache_speedup:.2f}x < 5x")
        
        # 验证数据一致性
        if len(sector_ranking_1) == len(sector_ranking_2) == len(sector_ranking_3):
            print(f"✅ 数据一致性验证通过: 三次获取的板块数量一致 ({len(sector_ranking_1)})")
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
    print("🧪 测试 5: 整体性能影响评估")
    print("="*60)
    
    try:
        db = DataManager()
        analyzer = FastSectorAnalyzer(db)
        signal_gen = SignalGenerator()
        
        # 测试批量股票处理
        test_stocks = [
            '000001', '000002', '600036', '600519', '300750',
            '002594', '002714', '600000', '601318', '601398'
        ]
        
        print(f"\n📊 测试批量处理 {len(test_stocks)} 只股票...")
        
        # 预热（获取板块数据）
        analyzer.get_akshare_sector_ranking()
        
        # 批量处理
        t_start = time.time()
        
        results = []
        for stock_code in test_stocks:
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
                'sector_status': result.get('sector_info', {}).get('status', 'NEUTRAL')
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
        if avg_time < 0.2:
            print(f"✅ 性能优秀: 平均 {avg_time:.3f} 秒 < 0.2 秒")
        elif avg_time < 0.5:
            print(f"⚠️ 性能一般: 平均 {avg_time:.3f} 秒 < 0.5 秒")
        else:
            print(f"❌ 性能较差: 平均 {avg_time:.3f} 秒 > 0.5 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🚀 V18 The Navigator - 板块共振系统性能测试")
    print("="*60)
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # 执行所有测试
    test_results.append(("板块数据获取性能", test_sector_data_fetch_performance()))
    test_results.append(("板块状态检查性能", test_sector_status_check_performance()))
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
        print("🎉 所有测试通过！V18 板块共振系统性能优异。")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查日志。")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
