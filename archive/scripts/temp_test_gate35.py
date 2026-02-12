"""
Test Gate 3.5 with simulated data
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.full_market_scanner import FullMarketScanner

scanner = FullMarketScanner()

print("=" * 80)
print("Test Gate 3.5: 3-day price up but capital not following")
print("=" * 80)

# Test 1: ratio=0.8% + is_price_up_3d_capital_not_follow=True
print("\nTest 1: ratio=0.8% + is_price_up_3d_capital_not_follow=True")
result1 = scanner._calculate_decision_tag(
    ratio=0.8,
    risk_score=0.2,
    trap_signals=[],
    is_price_up_3d_capital_not_follow=True
)
print(f"  Result: {result1}")
print(f"  Expected: TRAP❌")
print(f"  Status: {'✅ PASS' if result1 == 'TRAP❌' else '❌ FAIL'}")

# Test 2: ratio=0.8% + is_price_up_3d_capital_not_follow=False
print("\nTest 2: ratio=0.8% + is_price_up_3d_capital_not_follow=False")
result2 = scanner._calculate_decision_tag(
    ratio=0.8,
    risk_score=0.2,
    trap_signals=[],
    is_price_up_3d_capital_not_follow=False
)
print(f"  Result: {result2}")
print(f"  Expected: BLOCK❌ (ratio > 0.5% and < 1%, falls through to default)")
print(f"  Status: {'✅ PASS' if result2 == 'BLOCK❌' else '❌ FAIL'}")

# Test 3: ratio=2.0% + is_price_up_3d_capital_not_follow=True
print("\nTest 3: ratio=2.0% + is_price_up_3d_capital_not_follow=True")
result3 = scanner._calculate_decision_tag(
    ratio=2.0,
    risk_score=0.2,
    trap_signals=[],
    is_price_up_3d_capital_not_follow=True
)
print(f"  Result: {result3}")
print(f"  Expected: FOCUS✅ (ratio in 1-3% and no trap signals)")
print(f"  Status: {'✅ PASS' if result3 == 'FOCUS✅' else '❌ FAIL'}")

# Test 4: ratio=0.3% + is_price_up_3d_capital_not_follow=True
print("\nTest 4: ratio=0.3% + is_price_up_3d_capital_not_follow=True")
result4 = scanner._calculate_decision_tag(
    ratio=0.3,
    risk_score=0.2,
    trap_signals=[],
    is_price_up_3d_capital_not_follow=True
)
print(f"  Result: {result4}")
print(f"  Expected: PASS❌ (ratio < 0.5% triggers gate 1)")
print(f"  Status: {'✅ PASS' if result4 == 'PASS❌' else '❌ FAIL'}")

# Test 5: ratio=4.0% + is_price_up_3d_capital_not_follow=True
print("\nTest 5: ratio=4.0% + is_price_up_3d_capital_not_follow=True")
result5 = scanner._calculate_decision_tag(
    ratio=4.0,
    risk_score=0.2,
    trap_signals=[],
    is_price_up_3d_capital_not_follow=True
)
print(f"  Result: {result5}")
print(f"  Expected: BLOCK❌ (ratio > 3% and not in 1-3% range)")
print(f"  Status: {'✅ PASS' if result5 == 'BLOCK❌' else '❌ FAIL'}")

# Test 6: ratio=0.3% + is_price_up_3d_capital_not_follow=False
print("\nTest 6: ratio=0.3% + is_price_up_3d_capital_not_follow=False")
result6 = scanner._calculate_decision_tag(
    ratio=0.3,
    risk_score=0.2,
    trap_signals=[],
    is_price_up_3d_capital_not_follow=False
)
print(f"  Result: {result6}")
print(f"  Expected: PASS❌ (ratio < 0.5% triggers gate 1)")
print(f"  Status: {'✅ PASS' if result6 == 'PASS❌' else '❌ FAIL'}")

# Test 7: ratio=0.8% + is_price_up_3d_capital_not_follow=True (should be blocked by gate 3.5)
print("\nTest 7: ratio=0.8% + is_price_up_3d_capital_not_follow=True")
result7 = scanner._calculate_decision_tag(
    ratio=0.8,
    risk_score=0.2,
    trap_signals=[],
    is_price_up_3d_capital_not_follow=True
)
print(f"  Result: {result7}")
print(f"  Expected: TRAP❌ (gate 3.5 triggers)")
print(f"  Status: {'✅ PASS' if result7 == 'TRAP❌' else '❌ FAIL'}")

# Test 8: ratio=1.2% + is_price_up_3d_capital_not_follow=True (should be FOCUS)
print("\nTest 8: ratio=1.2% + is_price_up_3d_capital_not_follow=True")
result8 = scanner._calculate_decision_tag(
    ratio=1.2,
    risk_score=0.2,
    trap_signals=[],
    is_price_up_3d_capital_not_follow=True
)
print(f"  Result: {result8}")
print(f"  Expected: FOCUS✅ (gate 3.5 doesn't trigger because ratio >= 1%)")
print(f"  Status: {'✅ PASS' if result8 == 'FOCUS✅' else '❌ FAIL'}")

print("\n" + "=" * 80)
print("Summary")
print("=" * 80)
all_tests_passed = all([
    result1 == 'TRAP❌',
    result2 == 'BLOCK❌',
    result3 == 'FOCUS✅',
    result4 == 'PASS❌',
    result5 == 'BLOCK❌',
    result6 == 'PASS❌',
    result7 == 'TRAP❌',
    result8 == 'FOCUS✅'
])
print(f"All tests passed: {all_tests_passed}")