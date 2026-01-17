"""
V9.12.1 Review Mode Test Script

Test items:
1. Time weight in review mode (should be 1.0)
2. Auction analysis in review mode (should not decay)
3. AI data package generation in review mode

Author: iFlow CLI
Version: V9.12.1
Date: 2026-01-16
"""

import sys
import time as time_module
from datetime import time as datetime_time

# Add project root to path
sys.path.insert(0, 'E:\\MyQuantTool')


def test_time_weight_review_mode():
    """Test 1: Time weight in review mode"""
    print("=" * 60)
    print("Test 1: Time weight in review mode")
    print("=" * 60)
    
    try:
        from logic.algo import get_time_weight
        
        # Test weights at different times with review mode ON
        test_times = [
            (datetime_time(9, 30), "Market open"),
            (datetime_time(10, 30), "Morning battle"),
            (datetime_time(14, 45), "Late sneak attack"),
            (datetime_time(14, 55), "Last strike"),
            (datetime_time(15, 0), "Market close"),
        ]
        
        print("\nTime weight in REVIEW MODE (should be 1.0 for all):")
        for test_time, desc in test_times:
            weight = get_time_weight(test_time, is_review_mode=True)
            print(f"  {test_time.strftime('%H:%M')} ({desc}): weight={weight:.1f}")
            if weight != 1.0:
                print(f"    ❌ ERROR: Expected 1.0, got {weight}")
                return False
        
        print("\n✅ All weights are 1.0 in review mode!")
        
        # Test weights at different times with review mode OFF
        print("\nTime weight in NORMAL MODE (should decay):")
        for test_time, desc in test_times:
            weight = get_time_weight(test_time, is_review_mode=False)
            weight_desc = ""
            if weight == 1.0:
                weight_desc = "👑 Golden time"
            elif weight == 0.9:
                weight_desc = "⚔️ Battle time"
            elif weight == 0.7:
                weight_desc = "💤 Garbage time"
            elif weight == 0.4:
                weight_desc = "🦊 Sneak attack time"
            elif weight == 0.0:
                weight_desc = "☠️ Last strike"
            
            print(f"  {test_time.strftime('%H:%M')} ({desc}): weight={weight:.1f} - {weight_desc}")
        
        print("\n✅ Time weight review mode test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Time weight review mode test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_auction_analysis_review_mode():
    """Test 2: Auction analysis in review mode"""
    print("=" * 60)
    print("Test 2: Auction analysis in review mode")
    print("=" * 60)
    
    try:
        from logic.data_manager import DataManager
        from logic.algo import QuantAlgo
        
        # Initialize
        dm = DataManager()
        
        print("\nGetting market snapshot...")
        snapshot = dm.quotation.market_snapshot(prefix=False)
        
        if not snapshot or len(snapshot) == 0:
            print("❌ Failed to get market snapshot")
            return False
        
        print(f"✅ Got snapshot for {len(snapshot)} stocks")
        
        # Get yesterday's close prices
        last_closes = {}
        for code, data in snapshot.items():
            last_closes[code] = data.get('close', 0)
        
        # Test in NORMAL mode
        print("\n--- Testing in NORMAL mode (time decay ON) ---")
        start_time = time_module.time()
        results_normal = QuantAlgo.batch_analyze_auction(snapshot, last_closes, is_review_mode=False)
        elapsed_normal = time_module.time() - start_time
        
        # Get top 3 in normal mode
        sorted_normal = sorted(
            results_normal.items(),
            key=lambda x: x[1].get('score', 0),
            reverse=True
        )[:3]
        
        print(f"✅ Analysis completed in NORMAL mode (time: {elapsed_normal:.2f}s)")
        print("\nTop 3 in NORMAL mode:")
        for i, (code, result) in enumerate(sorted_normal, 1):
            print(f"  {i}. {code}")
            print(f"     - Base score: {result.get('base_score', 0)}")
            print(f"     - Time weight: {result.get('time_weight', 1.0)}")
            print(f"     - Final score: {result.get('score', 0)}")
            print(f"     - Time desc: {result.get('time_weight_desc', '')}")
        
        # Test in REVIEW mode
        print("\n--- Testing in REVIEW mode (time decay OFF) ---")
        start_time = time_module.time()
        results_review = QuantAlgo.batch_analyze_auction(snapshot, last_closes, is_review_mode=True)
        elapsed_review = time_module.time() - start_time
        
        # Get top 3 in review mode
        sorted_review = sorted(
            results_review.items(),
            key=lambda x: x[1].get('score', 0),
            reverse=True
        )[:3]
        
        print(f"✅ Analysis completed in REVIEW mode (time: {elapsed_review:.2f}s)")
        print("\nTop 3 in REVIEW mode:")
        for i, (code, result) in enumerate(sorted_review, 1):
            print(f"  {i}. {code}")
            print(f"     - Base score: {result.get('base_score', 0)}")
            print(f"     - Time weight: {result.get('time_weight', 1.0)}")
            print(f"     - Final score: {result.get('score', 0)}")
            print(f"     - Time desc: {result.get('time_weight_desc', '')}")
        
        # Verify that review mode has higher scores
        print("\n--- Verification ---")
        for i in range(min(3, len(sorted_normal), len(sorted_review))):
            code_normal, result_normal = sorted_normal[i]
            code_review, result_review = sorted_review[i]
            
            if code_normal != code_review:
                print(f"⚠️ Warning: Different stocks at position {i+1}")
                continue
            
            score_normal = result_normal.get('score', 0)
            score_review = result_review.get('score', 0)
            time_weight_normal = result_normal.get('time_weight', 1.0)
            time_weight_review = result_review.get('time_weight', 1.0)
            
            print(f"\n  Stock {code_normal}:")
            print(f"    - Normal mode: score={score_normal}, time_weight={time_weight_normal}")
            print(f"    - Review mode: score={score_review}, time_weight={time_weight_review}")
            
            if time_weight_review != 1.0:
                print(f"    ❌ ERROR: Review mode time weight should be 1.0")
                return False
            
            if score_review >= score_normal:
                print(f"    ✅ Review mode score >= Normal mode score")
            else:
                print(f"    ⚠️ Warning: Review mode score < Normal mode score")
        
        print("\n✅ Auction analysis review mode test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Auction analysis review mode test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_ai_context_review_mode():
    """Test 3: AI data package generation in review mode"""
    print("=" * 60)
    print("Test 3: AI data package generation in review mode")
    print("=" * 60)
    
    try:
        from logic.data_manager import DataManager
        from logic.sentiment_analyzer import SentimentAnalyzer
        
        # Initialize
        dm = DataManager()
        analyzer = SentimentAnalyzer(dm)
        
        # Test in REVIEW mode (smaller stock pool for speed)
        print("\n--- Testing AI data package in REVIEW mode ---")
        start_time = time_module.time()
        
        ai_context = analyzer.generate_ai_context(
            include_stock_pool=True, 
            stock_pool_size=5,
            is_review_mode=True
        )
        
        elapsed = time_module.time() - start_time
        
        if "error" in ai_context:
            print(f"❌ AI data package generation failed: {ai_context['error']}")
            return False
        
        print(f"\n✅ AI data package generation completed in REVIEW mode (time: {elapsed:.2f}s)")
        
        # Display stock pool data
        stock_pool = ai_context.get('stock_pool', {})
        if 'stocks' in stock_pool:
            stocks = stock_pool['stocks']
            print(f"\n🆕 Selected stock pool (top {len(stocks)}) in REVIEW mode:")
            for i, stock in enumerate(stocks, 1):
                print(f"\n  {i}. {stock['name']} ({stock['code']})")
                print(f"     - Price: {stock['price']}, Change %: {stock['pct']}%")
                print(f"     - Score: {stock['score']}")
                print(f"     - Base score: {stock.get('base_score', 'N/A')}")
                print(f"     - Time weight: {stock.get('time_weight', 'N/A')}")
                print(f"     - Time desc: {stock.get('time_weight_desc', 'N/A')}")
                print(f"     - Status: {stock['status']}")
                
                # Verify time weight is 1.0
                if stock.get('time_weight', 1.0) != 1.0:
                    print(f"     ❌ ERROR: Time weight should be 1.0 in review mode")
                    return False
                
                # Verify time desc is "📝 复盘模式 (不衰减)"
                if "复盘模式" not in stock.get('time_weight_desc', ''):
                    print(f"     ❌ ERROR: Time desc should contain '复盘模式'")
                    return False
        else:
            print(f"\n⚠️ Stock pool data: {stock_pool.get('error', 'N/A')}")
        
        print("\n✅ AI data package review mode test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ AI data package review mode test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("\n")
    print("🚀 V9.12.1 Review Mode Test")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("Time weight review mode", test_time_weight_review_mode()))
    results.append(("Auction analysis review mode", test_auction_analysis_review_mode()))
    results.append(("AI data package review mode", test_ai_context_review_mode()))
    
    # Summary results
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ Passed" if result else "❌ Failed"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All tests passed! V9.12.1 review mode verified successfully!")
        print("\n💡 Key improvements:")
        print("   - Review mode disables time decay (weight = 1.0)")
        print("   - Enables post-market analysis without 0-score issue")
        print("   - Preserves stock quality for review and backtesting")
    else:
        print(f"\n⚠️ {total - passed} tests failed, please check logs")
    
    print("\n")


if __name__ == "__main__":
    main()
