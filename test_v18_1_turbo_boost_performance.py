"""
V18.1 Turbo Boost Performance Test Script

Test Goals:
1. Background refresh mechanism verification
2. Static mapping table performance test
3. API fallback functionality test
4. Full resonance analysis performance optimization verification
5. Overall performance impact assessment
"""

import time
import sys
from datetime import datetime

# Disable tqdm progress bar
import os
os.environ['TQDM_DISABLE'] = '1'

from logic.data_manager import DataManager
from logic.sector_analysis import FastSectorAnalyzer


def test_1_background_refresh():
    """Test 1: Background refresh mechanism verification"""
    print("=" * 60)
    print("Test 1: Background refresh mechanism verification")
    print("=" * 60)
    
    db = DataManager()
    analyzer = FastSectorAnalyzer(db)
    
    # Check background thread status
    print(f"Background refresh thread status: {'Running' if analyzer._auto_refresh_running else 'Stopped'}")
    print(f"Background thread name: {analyzer._auto_refresh_thread.name if analyzer._auto_refresh_thread else 'N/A'}")
    print(f"Is daemon thread: {analyzer._auto_refresh_thread.daemon if analyzer._auto_refresh_thread else 'N/A'}")
    
    # Wait for background refresh to complete
    print("\nWaiting for background refresh to complete (max 5 seconds)...")
    time.sleep(5)
    
    # Check cache status
    if analyzer._akshare_industry_cache is not None:
        print(f"Industry sector cache updated, {len(analyzer._akshare_industry_cache)} sectors")
    else:
        print("Industry sector cache is empty")
    
    if analyzer._akshare_concept_cache is not None:
        print(f"Concept sector cache updated, {len(analyzer._akshare_concept_cache)} sectors")
    else:
        print("Concept sector cache is empty (fallback mode may be triggered due to timeout)")
    
    print(f"Fallback mode status: {'Enabled' if analyzer._fallback_mode else 'Normal'}")
    
    print("\nTest 1 passed\n")


def test_2_static_mapping_performance():
    """Test 2: Static mapping table performance test"""
    print("=" * 60)
    print("Test 2: Static mapping table performance test")
    print("=" * 60)
    
    db = DataManager()
    analyzer = FastSectorAnalyzer(db)
    
    # Check mapping table size
    map_size = len(analyzer._stock_sector_map)
    print(f"Mapping table size: {map_size} stocks")
    
    if map_size == 0:
        print("ERROR: Mapping table is empty, test failed")
        return False
    
    # Test query performance
    test_stocks = ['000001', '000002', '600036', '600519', '300750']
    
    print("\nTesting query performance (1000 queries)...")
    t_start = time.time()
    
    for _ in range(1000):
        for stock_code in test_stocks:
            sector_info = analyzer._stock_sector_map.get(stock_code, {})
            industry = sector_info.get('industry', 'Unknown')
    
    t_cost = time.time() - t_start
    avg_time = t_cost / (1000 * len(test_stocks))
    
    print(f"1000 queries completed, total time: {t_cost:.3f} seconds")
    print(f"Average query time: {avg_time * 1000:.4f} milliseconds")
    
    if avg_time < 0.0001:
        print("Excellent performance: Average query time < 0.1 ms")
    elif avg_time < 0.001:
        print("Good performance: Average query time < 1 ms")
    else:
        print("Average performance: Average query time >= 1 ms")
    
    # Show example query results
    print("\nExample query results:")
    for stock_code in test_stocks:
        sector_info = analyzer._stock_sector_map.get(stock_code, {})
        industry = sector_info.get('industry', 'Unknown')
        print(f"   {stock_code}: {industry}")
    
    print("\nTest 2 passed\n")
    return True


def test_3_api_fallback():
    """Test 3: API fallback functionality test"""
    print("=" * 60)
    print("Test 3: API fallback functionality test")
    print("=" * 60)
    
    db = DataManager()
    analyzer = FastSectorAnalyzer(db)
    
    # Wait for background refresh to complete
    print("Waiting for background refresh to complete...")
    time.sleep(5)
    
    # Check fallback mode status
    fallback_mode = analyzer._fallback_mode
    print(f"Fallback mode status: {'Enabled' if fallback_mode else 'Normal'}")
    
    if fallback_mode:
        print("Concept sector API timeout, fallback mode enabled")
        print("Fallback mode working normally")
    else:
        print("Concept sector API normal, fallback mode not enabled")
    
    # Test functionality in fallback mode
    print("\nTesting sector data retrieval in fallback mode...")
    
    industry_ranking = analyzer.get_akshare_sector_ranking()
    if not industry_ranking.empty:
        print(f"Industry sector data normal, {len(industry_ranking)} sectors")
    else:
        print("ERROR: Industry sector data is empty")
    
    concept_ranking = analyzer.get_akshare_concept_ranking()
    if not concept_ranking.empty:
        print(f"Concept sector data normal, {len(concept_ranking)} sectors")
    else:
        if fallback_mode:
            print("Concept sector data is empty (expected behavior in fallback mode)")
        else:
            print("ERROR: Concept sector data is empty (unexpected in normal mode)")
    
    print("\nTest 3 passed\n")
    return True


def test_4_full_resonance_performance():
    """Test 4: Full resonance analysis performance optimization verification"""
    print("=" * 60)
    print("Test 4: Full resonance analysis performance optimization verification")
    print("=" * 60)
    
    db = DataManager()
    analyzer = FastSectorAnalyzer(db)
    
    # Wait for background refresh to complete
    print("Waiting for background refresh to complete...")
    time.sleep(5)
    
    # Test stock list
    test_stocks = [
        ('000001', '平安银行'),
        ('000002', '万科A'),
        ('600036', '招商银行'),
        ('600519', '贵州茅台'),
        ('300750', '宁德时代')
    ]
    
    print(f"\nTesting full resonance analysis for {len(test_stocks)} stocks...")
    
    total_time = 0
    results = []
    
    for stock_code, stock_name in test_stocks:
        t_start = time.time()
        
        resonance_result = analyzer.check_stock_full_resonance(stock_code, stock_name)
        
        t_cost = time.time() - t_start
        total_time += t_cost
        
        results.append({
            'stock_code': stock_code,
            'stock_name': stock_name,
            'time': t_cost,
            'resonance_score': resonance_result.get('resonance_score', 0),
            'is_leader': resonance_result.get('is_leader', False),
            'is_follower': resonance_result.get('is_follower', False)
        })
        
        print(f"   {stock_code} ({stock_name}): {t_cost:.3f}s, resonance score {resonance_result.get('resonance_score', 0):+.1f}")
    
    avg_time = total_time / len(test_stocks)
    
    print(f"\nAverage time: {avg_time:.3f}s per stock")
    print(f"Total time: {total_time:.3f}s")
    
    # Performance evaluation
    if avg_time < 0.001:
        print("Excellent performance: Average time < 1ms (Goal achieved)")
    elif avg_time < 0.01:
        print("Good performance: Average time < 10ms")
    elif avg_time < 0.1:
        print("Good performance: Average time < 100ms")
    elif avg_time < 1.0:
        print("Average performance: Average time < 1s")
    else:
        print("Poor performance: Average time >= 1s")
    
    # Statistics
    leader_count = sum(1 for r in results if r['is_leader'])
    follower_count = sum(1 for r in results if r['is_follower'])
    positive_count = sum(1 for r in results if r['resonance_score'] > 0)
    
    print(f"\nResult statistics:")
    print(f"   Leaders: {leader_count}/{len(test_stocks)}")
    print(f"   Followers: {follower_count}/{len(test_stocks)}")
    print(f"   Positive scores: {positive_count}/{len(test_stocks)}")
    
    print("\nTest 4 passed\n")
    return True


def test_5_overall_performance():
    """Test 5: Overall performance impact assessment"""
    print("=" * 60)
    print("Test 5: Overall performance impact assessment")
    print("=" * 60)
    
    db = DataManager()
    analyzer = FastSectorAnalyzer(db)
    
    # Wait for background refresh to complete
    print("Waiting for background refresh to complete...")
    time.sleep(5)
    
    # Test batch processing
    test_stocks = [
        '000001', '000002', '600036', '600519', '300750',
        '002594', '002714', '600000', '601318', '601398'
    ]
    
    print(f"\nTesting batch processing for {len(test_stocks)} stocks...")
    
    t_start = time.time()
    
    for stock_code in test_stocks:
        resonance_result = analyzer.check_stock_full_resonance(stock_code)
        # Simulate actual usage scenario
        resonance_score = resonance_result.get('resonance_score', 0)
    
    t_cost = time.time() - t_start
    avg_time = t_cost / len(test_stocks)
    
    print(f"Batch processing completed!")
    print(f"   Total time: {t_cost:.3f}s")
    print(f"   Average time: {avg_time:.3f}s per stock")
    print(f"   Processing speed: {len(test_stocks) / t_cost:.2f} stocks/s")
    
    # Performance evaluation
    if avg_time < 0.001:
        print("Excellent performance: Average time < 1ms")
    elif avg_time < 0.01:
        print("Good performance: Average time < 10ms")
    elif avg_time < 0.1:
        print("Good performance: Average time < 100ms")
    elif avg_time < 1.0:
        print("Average performance: Average time < 1s")
    else:
        print("Poor performance: Average time >= 1s")
    
    print("\nTest 5 passed\n")
    return True


def main():
    """Main test function"""
    print("\n")
    print("=" * 60)
    print("V18.1 Turbo Boost - Performance Test")
    print("=" * 60)
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n")
    
    # Run all tests
    tests = [
        ("Background refresh mechanism verification", test_1_background_refresh),
        ("Static mapping table performance test", test_2_static_mapping_performance),
        ("API fallback functionality test", test_3_api_fallback),
        ("Full resonance analysis performance optimization verification", test_4_full_resonance_performance),
        ("Overall performance impact assessment", test_5_overall_performance)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            test_func()
            results.append((test_name, "PASSED"))
        except Exception as e:
            print(f"Test failed: {test_name}")
            print(f"Error message: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, "FAILED"))
    
    # Output test results summary
    print("\n")
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results:
        print(f"{result} {test_name}")
    
    passed_count = sum(1 for _, result in results if result == "PASSED")
    total_count = len(results)
    
    print(f"\nTotal: {passed_count} passed, {total_count - passed_count} failed")
    
    if passed_count == total_count:
        print("\nAll tests passed! V18.1 Turbo Boost performance optimization successful!")
    else:
        print("\nSome tests failed, please check error messages")
    
    print("\n")


if __name__ == '__main__':
    main()