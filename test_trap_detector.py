"""
Test script for TrapDetector.detect() method
"""

import sys
sys.path.insert(0, '.')

from logic.trap_detector import TrapDetector

def test_detect_method():
    """Test TrapDetector.detect() method"""
    print(f"\n{'='*60}")
    print(f"Test: TrapDetector.detect() Method")
    print(f"{'='*60}")

    detector = TrapDetector()

    # Test with a stock code
    stock_code = "600519"  # Kweichow Moutai

    print(f"\nTesting stock: {stock_code}")

    try:
        result = detector.detect(stock_code, days=30)

        print(f"\n✅ detect() method succeeded")
        print(f"   - Signals count: {len(result.get('signals', []))}")
        print(f"   - Trap count: {result.get('trap_count', 0)}")
        print(f"   - Highest severity: {result.get('highest_severity', 0):.2f}")
        print(f"   - Highest risk level: {result.get('highest_risk_level', 'N/A')}")
        print(f"   - Total outflow: {result.get('total_outflow', 0):.2f}万元")
        print(f"   - Comprehensive risk score: {result.get('comprehensive_risk_score', 0):.2f}")
        print(f"   - Risk assessment: {result.get('risk_assessment', 'N/A')}")
        print(f"   - Scan time: {result.get('scan_time', 'N/A')}")

        # Print signals
        signals = result.get('signals', [])
        if signals:
            print(f"\n   Signals:")
            for i, signal in enumerate(signals[:5], 1):  # Show first 5 signals
                print(f"     {i}. Type: {signal.get('type', 'N/A')}, Severity: {signal.get('severity', 0):.2f}")
                print(f"        Date: {signal.get('date', 'N/A')}")
                print(f"        Description: {signal.get('description', 'N/A')}")

        return True

    except Exception as e:
        print(f"\n❌ detect() method failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_stocks():
    """Test detect() method with multiple stocks"""
    print(f"\n{'='*60}")
    print(f"Test: Multiple Stocks")
    print(f"{'='*60}")

    detector = TrapDetector()
    stock_codes = ["600519", "000001", "300997"]

    success_count = 0
    fail_count = 0

    for stock_code in stock_codes:
        print(f"\n--- Testing {stock_code} ---")
        try:
            result = detector.detect(stock_code, days=30)

            if result.get('trap_count', 0) >= 0:
                print(f"   ✅ Success")
                print(f"   - Risk score: {result.get('comprehensive_risk_score', 0):.2f}")
                print(f"   - Risk assessment: {result.get('risk_assessment', 'N/A')}")
                success_count += 1
            else:
                print(f"   ❌ Failed: Invalid result")
                fail_count += 1

        except Exception as e:
            print(f"   ❌ Failed: {e}")
            fail_count += 1

    print(f"\n{'='*60}")
    print(f"Multiple stocks test results:")
    print(f"   Success: {success_count}/{len(stock_codes)}")
    print(f"   Failed: {fail_count}/{len(stock_codes)}")
    print(f"{'='*60}")

    return success_count == len(stock_codes)

def main():
    """Main function"""
    print(f"\n{'#'*60}")
    print(f"# TrapDetector Test Script")
    print(f"{'#'*60}")

    # Test 1: Single stock
    test_detect_method()

    # Test 2: Multiple stocks
    test_multiple_stocks()

    print(f"\n{'#'*60}")
    print(f"# Test Completed")
    print(f"{'#'*60}\n")

if __name__ == "__main__":
    main()