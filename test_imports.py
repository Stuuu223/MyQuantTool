"""Smoke test for core modules"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 60)
print("Smoke Test")
print("=" * 60)

test_modules = [
    ('logic.strategies.midway_strategy', 'Midway Strategy'),
    ('logic.strategies.leader_event_detector', 'Leader Event'),
    ('logic.strategies.event_detector', 'Event Detector'),
    ('logic.data.qmt_manager', 'QMT Manager'),
    ('logic.data.fund_flow_analyzer', 'Fund Flow'),
    ('logic.data.realtime_data_provider', 'Realtime Provider'),
    ('logic.analyzers.stock_analyzer', 'Stock Analyzer'),
    ('logic.analyzers.technical_analyzer', 'Technical Analyzer'),
    ('logic.strategies.strategy_factory', 'Strategy Factory'),
    ('logic.strategies.wind_filter', 'Wind Filter'),
    ('logic.strategies.dynamic_threshold', 'Dynamic Threshold'),
    ('logic.strategies.auction_strength_validator', 'Auction Validator'),
    ('logic.strategies.backtest_engine', 'Backtest Engine'),
]

passed = 0
failed = 0
errors = []

for module_path, description in test_modules:
    try:
        __import__(module_path)
        print(f"OK {description}: {module_path}")
        passed += 1
    except Exception as e:
        print(f"FAIL {description}: {module_path}")
        print(f"   Error: {type(e).__name__}: {e}")
        failed += 1
        errors.append((module_path, description, str(e)))

print("\n" + "=" * 60)
print(f"Result: {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    print("\nFailed details:")
    for module_path, description, error in errors:
        print(f"  - {description} ({module_path})")
        print(f"    Error: {error}")
    sys.exit(1)
else:
    print("\nAll imports successful!")
    sys.exit(0)