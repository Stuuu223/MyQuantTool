"""
Test script for fund_flow_analyzer after migration to AkShare
"""

import sys
sys.path.insert(0, '.')

from logic.fund_flow_analyzer import FundFlowAnalyzer, format_fund_flow_analysis

def test_single_stock(stock_code="600519"):
    """Test single stock fund flow analysis"""
    print(f"\n{'='*60}")
    print(f"Test: Single Stock Fund Flow Analysis")
    print(f"{'='*60}")
    print(f"Stock code: {stock_code}")

    analyzer = FundFlowAnalyzer(enable_cache=True)

    # Test get_fund_flow
    print(f"\n1. Test get_fund_flow:")
    data = analyzer.get_fund_flow(stock_code, days=5)

    if "error" in data:
        print(f"   ❌ Failed: {data['error']}")
        return False
    else:
        print(f"   ✅ Success")
        print(f"   Records count: {len(data['records'])}")
        print(f"   Latest date: {data['latest']['date']}")
        print(f"   Latest data: {data['latest']}")

    # Test analyze_fund_flow
    print(f"\n2. Test analyze_fund_flow:")
    result = analyzer.analyze_fund_flow(stock_code)

    if "error" in result:
        print(f"   ❌ Failed: {result['error']}")
        return False
    else:
        print(f"   ✅ Success")
        print(f"   Decision: {result['decision']}")
        print(f"   Risk level: {result['risk_level']}")
        print(f"   Reason: {result['reason']}")
        print(f"   Data source: {result['data_source']}")

    # Test format_analysis
    print(f"\n3. Test format_analysis:")
    report = analyzer.format_analysis(result)
    print(report)

    return True

def test_multiple_stocks(stock_codes=["600519", "000001", "300997"]):
    """Test multiple stocks fund flow analysis"""
    print(f"\n{'='*60}")
    print(f"Test: Multiple Stocks Fund Flow Analysis")
    print(f"{'='*60}")
    print(f"Stock codes: {stock_codes}")

    analyzer = FundFlowAnalyzer(enable_cache=True)

    success_count = 0
    fail_count = 0

    for stock_code in stock_codes:
        print(f"\n--- Testing {stock_code} ---")
        result = analyzer.analyze_fund_flow(stock_code)

        if "error" in result:
            print(f"   ❌ Failed: {result['error']}")
            fail_count += 1
        else:
            print(f"   ✅ Success")
            print(f"   Decision: {result['decision']}, Risk: {result['risk_level']}")
            print(f"   Institution: {result['fund_flow']['institution_net']/10000:.2f}万")
            print(f"   Retail: {result['fund_flow']['retail_net']/10000:.2f}万")
            success_count += 1

    print(f"\n{'='*60}")
    print(f"Multiple stocks test results:")
    print(f"   Success: {success_count}/{len(stock_codes)}")
    print(f"   Failed: {fail_count}/{len(stock_codes)}")
    print(f"{'='*60}")

    return success_count == len(stock_codes)

def main():
    """Main function"""
    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
    else:
        stock_code = "600519"  # Kweichow Moutai

    print(f"\n{'#'*60}")
    print(f"# Fund Flow Analyzer Test Script (AkShare Migration)")
    print(f"{'#'*60}")

    # Test 1: Single stock
    test_single_stock(stock_code)

    # Test 2: Multiple stocks
    test_multiple_stocks(["600519", "000001", "300997"])

    print(f"\n{'#'*60}")
    print(f"# Test Completed")
    print(f"{'#'*60}\n")

if __name__ == "__main__":
    main()