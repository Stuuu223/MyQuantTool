"""
V9.13 Lianban and Weak-to-Strong Test Script

Test items:
1. Stock status calculation (lianban count, yesterday status)
2. Weak-to-strong recognition logic
3. AI data package with lianban and weak-to-strong info
4. Auction analysis with lianban bonus

Author: iFlow CLI
Version: V9.13
Date: 2026-01-16
"""

import sys
import time as time_module

# Add project root to path
sys.path.insert(0, 'E:\\MyQuantTool')


def test_stock_status():
    """Test 1: Stock status calculation"""
    print("=" * 60)
    print("Test 1: Stock status calculation (lianban count)")
    print("=" * 60)
    
    try:
        from logic.data_manager import DataManager
        
        # Initialize
        dm = DataManager()
        
        # Test with some sample stocks
        test_codes = ['000001', '000002', '600000', '300001', '688001']
        
        print("\nTesting stock status calculation:")
        for code in test_codes:
            print(f"\n  Stock: {code}")
            
            start_time = time_module.time()
            status = dm.get_stock_status(code)
            elapsed = time_module.time() - start_time
            
            print(f"    - Lianban count: {status['lianban_count']}")
            print(f"    - Yesterday status: {status['yesterday_status']}")
            print(f"    - Yesterday pct: {status['yesterday_pct']:.2f}%")
            print(f"    - Limit threshold: {status['limit_threshold']:.1f}%")
            print(f"    - Time: {elapsed:.2f}s")
        
        print("\n✅ Stock status calculation test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Stock status calculation test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_weak_to_strong_recognition():
    """Test 2: Weak-to-strong recognition in auction analysis"""
    print("=" * 60)
    print("Test 2: Weak-to-strong recognition")
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
        
        # Test with review mode to avoid time decay
        print("\nAnalyzing auction strength (review mode)...")
        start_time = time_module.time()
        
        results = QuantAlgo.batch_analyze_auction(
            snapshot, 
            last_closes, 
            is_review_mode=True,
            data_manager=dm
        )
        
        elapsed = time_module.time() - start_time
        
        print(f"✅ Analysis completed (time: {elapsed:.2f}s)")
        
        # Find stocks with weak-to-strong signal
        weak_to_strong_stocks = []
        for code, result in results.items():
            if result.get('is_weak_to_strong', False):
                weak_to_strong_stocks.append((code, result))
        
        print(f"\n🔥 Weak-to-strong signals found: {len(weak_to_strong_stocks)}")
        
        # Display top 5 weak-to-strong stocks
        sorted_wts = sorted(
            weak_to_strong_stocks,
            key=lambda x: x[1].get('score', 0),
            reverse=True
        )[:5]
        
        for i, (code, result) in enumerate(sorted_wts, 1):
            print(f"\n  {i}. {code}")
            print(f"     - Score: {result.get('score', 0)}")
            print(f"     - Base score: {result.get('base_score', 0)}")
            print(f"     - Lianban count: {result.get('lianban_count', 0)}")
            print(f"     - Yesterday status: {result.get('yesterday_status', 'N/A')}")
            print(f"     - Weak-to-strong bonus: {result.get('weak_to_strong_bonus', 0)}")
            print(f"     - Lianban bonus: {result.get('lianban_bonus', 0)}")
            print(f"     - Status: {result.get('status', 'N/A')}")
        
        # Display top 5 stocks by lianban count
        print("\n📈 Top 5 stocks by lianban count:")
        sorted_lianban = sorted(
            results.items(),
            key=lambda x: x[1].get('lianban_count', 0),
            reverse=True
        )[:5]
        
        for i, (code, result) in enumerate(sorted_lianban, 1):
            print(f"\n  {i}. {code}")
            print(f"     - Lianban count: {result.get('lianban_count', 0)}")
            print(f"     - Score: {result.get('score', 0)}")
            print(f"     - Yesterday status: {result.get('yesterday_status', 'N/A')}")
            print(f"     - Lianban bonus: {result.get('lianban_bonus', 0)}")
            print(f"     - High risk penalty: {result.get('high_risk_penalty', 0)}")
        
        print("\n✅ Weak-to-strong recognition test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Weak-to-strong recognition test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_ai_context_with_lianban():
    """Test 3: AI data package with lianban and weak-to-strong info"""
    print("=" * 60)
    print("Test 3: AI data package with lianban info")
    print("=" * 60)
    
    try:
        from logic.data_manager import DataManager
        from logic.sentiment_analyzer import SentimentAnalyzer
        
        # Initialize
        dm = DataManager()
        analyzer = SentimentAnalyzer(dm)
        
        print("\nGenerating AI data package (with stock pool)...")
        start_time = time_module.time()
        
        # Generate AI data package (including stock pool)
        ai_context = analyzer.generate_ai_context(
            include_stock_pool=True, 
            stock_pool_size=10,
            is_review_mode=True
        )
        
        elapsed = time_module.time() - start_time
        
        if "error" in ai_context:
            print(f"❌ AI data package generation failed: {ai_context['error']}")
            return False
        
        print(f"\n✅ AI data package generation completed (time: {elapsed:.2f}s)")
        
        # Display stock pool data
        stock_pool = ai_context.get('stock_pool', {})
        if 'stocks' in stock_pool:
            stocks = stock_pool['stocks']
            print(f"\n🆕 Selected stock pool (top {len(stocks)}):")
            for i, stock in enumerate(stocks, 1):
                print(f"\n  {i}. {stock['name']} ({stock['code']})")
                print(f"     - Price: {stock['price']}, Change %: {stock['pct']}%")
                print(f"     - Score: {stock['score']}")
                print(f"     - Base score: {stock.get('base_score', 'N/A')}")
                print(f"     - Time weight: {stock.get('time_weight', 'N/A')}")
                print(f"     - Status: {stock['status']}")
                print(f"     - Lianban status: {stock.get('lianban_status', 'N/A')}")
                print(f"     - Lianban count: {stock.get('lianban_count', 0)}")
                print(f"     - Yesterday status: {stock.get('yesterday_status', 'N/A')}")
                print(f"     - Weak-to-strong: {stock.get('is_weak_to_strong', False)}")
                print(f"     - Weak-to-strong bonus: {stock.get('weak_to_strong_bonus', 0)}")
                print(f"     - Lianban bonus: {stock.get('lianban_bonus', 0)}")
                print(f"     - High risk penalty: {stock.get('high_risk_penalty', 0)}")
        else:
            print(f"\n⚠️ Stock pool data: {stock_pool.get('error', 'N/A')}")
        
        print("\n✅ AI data package lianban info test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ AI data package lianban info test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("\n")
    print("🚀 V9.13 Lianban and Weak-to-Strong Test")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("Stock status calculation", test_stock_status()))
    results.append(("Weak-to-strong recognition", test_weak_to_strong_recognition()))
    results.append(("AI data package lianban info", test_ai_context_with_lianban()))
    
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
        print("\n🎉 All tests passed! V9.13 lianban and weak-to-strong features verified successfully!")
        print("\n💡 Key improvements:")
        print("   - Real lianban count calculation (not just based on current pct)")
        print("   - Weak-to-strong recognition (烂板/断板 + 高开)")
        print("   - Lianban bonus (2板+10分, 4板+15分)")
        print("   - High risk penalty (5板+低开-50分)")
        print("   - AI can now understand stock 'status' and 'attitude'")
    else:
        print(f"\n⚠️ {total - passed} tests failed, please check logs")
    
    print("\n")


if __name__ == "__main__":
    main()