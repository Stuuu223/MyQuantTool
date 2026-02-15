"""Smoke test for core modules - V15 Updated"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 60)
print("V15 Smoke Test - Core Modules")
print("=" * 60)

test_modules = [
    ('logic.strategies.event_detector', 'Event Detector'),
    ('logic.data_providers.qmt_manager', 'QMT Manager'),
    ('logic.data_providers.fund_flow_analyzer', 'Fund Flow'),
    ('logic.data_providers.realtime_data_provider', 'Realtime Provider'),
    ('logic.analyzers.stock_analyzer', 'Stock Analyzer'),
    ('logic.analyzers.technical_analyzer', 'Technical Analyzer'),
    ('logic.strategies.wind_filter', 'Wind Filter'),
    ('logic.strategies.dynamic_threshold', 'Dynamic Threshold'),
    ('logic.strategies.auction_strength_validator', 'Auction Validator'),
    ('logic.strategies.backtest_engine', 'Backtest Engine'),
    ('logic.strategies.triple_funnel_scanner', 'Triple Funnel Scanner'),
    ('logic.strategies.full_market_scanner', 'Full Market Scanner'),
    ('logic.core.rate_limiter', 'Rate Limiter'),
    ('logic.core.failsafe', 'Fail-Safe'),
    ('logic.analyzers.trap_detector', 'Trap Detector'),
    ('logic.data_providers.level1_provider', 'Level-1 Provider'),
    ('logic.data_providers.level2_provider', 'Level-2 Provider'),
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

print("
" + "=" * 60)
print(f"Result: {passed} passed, {failed} failed")

if failed > 0:
    print("
Failed details:")
    for module_path, description, error in errors:
        print(f"  - {description} ({module_path})")
        print(f"    Error: {error}")
    sys.exit(1)
else:
    print("
All imports successful!")
    sys.exit(0)
