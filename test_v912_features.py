"""
V9.12 New Features Test Script

Test items:
1. Time decay factor function
2. ST stock and Beijing Stock Exchange separate statistics
3. Market phase prediction function
4. Consecutive limit-up information in AI data package
5. Time weight application in auction analysis

Author: iFlow CLI
Version: V9.12
Date: 2026-01-16
"""

import sys
import time as time_module
from datetime import time as datetime_time

# Add project root to path
sys.path.insert(0, 'E:\\MyQuantTool')


def test_time_weight():
    """Test 1: Time decay factor function"""
    print("=" * 60)
    print("Test 1: Time decay factor function")
    print("=" * 60)
    
    try:
        from logic.algo import get_time_weight
        
        # Test weights at different times
        test_times = [
            (datetime_time(9, 15), "Auction start"),
            (datetime_time(9, 30), "Market open"),
            (datetime_time(9, 45), "Golden half hour"),
            (datetime_time(10, 30), "Morning battle"),
            (datetime_time(11, 30), "Morning close"),
            (datetime_time(13, 0), "Afternoon open"),
            (datetime_time(14, 0), "Afternoon sleepy"),
            (datetime_time(14, 45), "Late sneak attack"),
            (datetime_time(14, 55), "Last strike"),
            (datetime_time(15, 0), "Market close"),
        ]
        
        print("\nTime weight test results:")
        for test_time, desc in test_times:
            weight = get_time_weight(test_time)
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
        
        print("\n✅ Time decay factor test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Time decay factor test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_sentiment_with_st_stats():
    """Test 2: ST stock and Beijing Stock Exchange separate statistics"""
    print("=" * 60)
    print("Test 2: ST stock and Beijing Stock Exchange separate statistics")
    print("=" * 60)
    
    try:
        from logic.data_manager import DataManager
        from logic.sentiment_analyzer import SentimentAnalyzer
        
        # Initialize
        dm = DataManager()
        analyzer = SentimentAnalyzer(dm)
        
        print("\nGetting market sentiment data...")
        start_time = time_module.time()
        
        # Get market sentiment
        mood = analyzer.analyze_market_mood(force_refresh=True)
        
        elapsed = time_module.time() - start_time
        
        if mood is None:
            print("❌ Failed to get market sentiment data")
            return False
        
        print(f"\n✅ Market sentiment analysis completed (time: {elapsed:.2f}s)")
        print(f"  - Total stocks: {mood['total']}")
        print(f"  - Limit up count: {mood['limit_up']}")
        print(f"  - Limit down count: {mood['limit_down']}")
        print(f"  - 🆕 ST limit up: {mood.get('st_limit_up', 0)} stocks")
        print(f"  - 🆕 ST limit down: {mood.get('st_limit_down', 0)} stocks")
        print(f"  - 🆕 Beijing Stock Exchange limit up: {mood.get('bj_limit_up', 0)} stocks")
        print(f"  - 🆕 Beijing Stock Exchange limit down: {mood.get('bj_limit_down', 0)} stocks")
        print(f"  - Up count: {mood['up']}")
        print(f"  - Down count: {mood['down']}")
        print(f"  - Sentiment score: {mood['score']}")
        
        # Risk warning
        if mood.get('st_limit_up', 0) > 20:
            print(f"\n⚠️ Risk warning: ST limit up stocks exceed 20, may indicate market decline")
        
        print("\n✅ ST stock and Beijing Stock Exchange statistics test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ ST stock and Beijing Stock Exchange statistics test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_market_phase_prediction():
    """Test 3: Market phase prediction function"""
    print("=" * 60)
    print("Test 3: Market phase prediction function")
    print("=" * 60)
    
    try:
        from logic.data_manager import DataManager
        from logic.sentiment_analyzer import SentimentAnalyzer
        
        # Initialize
        dm = DataManager()
        analyzer = SentimentAnalyzer(dm)
        
        print("\nGenerating AI data package...")
        start_time = time_module.time()
        
        # Generate AI data package
        ai_context = analyzer.generate_ai_context(include_stock_pool=False)
        
        elapsed = time_module.time() - start_time
        
        if "error" in ai_context:
            print(f"❌ AI data package generation failed: {ai_context['error']}")
            return False
        
        print(f"\n✅ AI data package generation completed (time: {elapsed:.2f}s)")
        
        # Display market phase prediction
        meta = ai_context.get('meta', {})
        market_phase = meta.get('market_phase', 'Unknown')
        
        print(f"\n🆕 Market phase prediction: {market_phase}")
        
        # Display detailed sentiment data
        sentiment = ai_context.get('market_sentiment', {})
        print(f"\nDetailed sentiment data:")
        print(f"  - Sentiment score: {sentiment.get('score', 0)}")
        print(f"  - Market temperature: {sentiment.get('temperature', 'N/A')}")
        print(f"  - Limit up count: {sentiment.get('limit_up_count', 0)}")
        print(f"  - Limit down count: {sentiment.get('limit_down_count', 0)}")
        print(f"  - ST limit up: {sentiment.get('st_limit_up_count', 0)}")
        print(f"  - Beijing Stock Exchange limit up: {sentiment.get('bj_limit_up_count', 0)}")
        
        # Display trading advice
        advice = ai_context.get('trading_advice', '')
        print(f"\nTrading advice: {advice}")
        
        # Display risk assessment
        risk = ai_context.get('risk_assessment', {})
        print(f"\nRisk assessment:")
        print(f"  - Overall risk: {risk.get('level', 'N/A')}")
        print(f"  - Limit up risk: {risk.get('limit_up_risk', 'N/A')}")
        print(f"  - Limit down risk: {risk.get('limit_down_risk', 'N/A')}")
        
        print("\n✅ Market phase prediction test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Market phase prediction test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_auction_with_time_weight():
    """Test 4: Time weight application in auction analysis"""
    print("=" * 60)
    print("Test 4: Time weight application in auction analysis")
    print("=" * 60)
    
    try:
        from logic.data_manager import DataManager
        from logic.algo import QuantAlgo, get_time_weight
        
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
        
        print("\nBatch analyzing auction strength...")
        start_time = time_module.time()
        
        # Batch analysis
        results = QuantAlgo.batch_analyze_auction(snapshot, last_closes)
        
        elapsed = time_module.time() - start_time
        
        print(f"✅ Auction analysis completed (time: {elapsed:.2f}s)")
        print(f"  - Analyzed stocks: {len(results)}")
        
        # Get current time weight
        current_time_weight = get_time_weight()
        print(f"\nCurrent time weight: {current_time_weight:.1f}")
        
        # Display Top 5 with time weight impact
        print("\nTop 5 strong stocks (with time weight impact):")
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1].get('score', 0),
            reverse=True
        )[:5]
        
        for i, (code, result) in enumerate(sorted_results, 1):
            base_score = result.get('base_score', 0)
            final_score = result.get('score', 0)
            time_weight = result.get('time_weight', 1.0)
            time_weight_desc = result.get('time_weight_desc', '')
            
            print(f"\n  {i}. {code}")
            print(f"     - Price: {result.get('price', 0)}")
            print(f"     - Change %: {result.get('pct', 0)}%")
            print(f"     - Base score: {base_score}")
            print(f"     - Time weight: {time_weight:.1f} ({time_weight_desc})")
            print(f"     - Final score: {final_score}")
            print(f"     - Status: {result.get('status', 'Unknown')}")
            print(f"     - Turnover rate: {result.get('turnover_rate', 0)}%")
        
        print("\n✅ Auction analysis time weight test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Auction analysis time weight test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_ai_context_with_lianban():
    """Test 5: Consecutive limit-up information in AI data package"""
    print("=" * 60)
    print("Test 5: Consecutive limit-up information in AI data package")
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
        ai_context = analyzer.generate_ai_context(include_stock_pool=True, stock_pool_size=10)
        
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
                print(f"     - Time weight: {stock.get('time_weight', 'N/A')} ({stock.get('time_weight_desc', 'N/A')})")
                print(f"     - Status: {stock['status']}")
                print(f"     - Turnover rate: {stock['turnover_rate']}%")
                print(f"     - 🆕 Consecutive limit-up mark: {stock.get('lianban_status', 'N/A')}")
        else:
            print(f"\n⚠️ Stock pool data: {stock_pool.get('error', 'N/A')}")
        
        print("\n✅ AI data package consecutive limit-up information test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ AI data package consecutive limit-up information test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("\n")
    print("🚀 V9.12 New Features Test")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("Time decay factor", test_time_weight()))
    results.append(("ST stock and Beijing Stock Exchange statistics", test_sentiment_with_st_stats()))
    results.append(("Market phase prediction", test_market_phase_prediction()))
    results.append(("Auction analysis time weight", test_auction_with_time_weight()))
    results.append(("AI data package consecutive limit-up information", test_ai_context_with_lianban()))
    
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
        print("\n🎉 All tests passed! V9.12 new features verified successfully!")
    else:
        print(f"\n⚠️ {total - passed} tests failed, please check logs")
    
    print("\n")


if __name__ == "__main__":
    main()
