"""Check QMT environment connection status"""
import sys
import io
sys.path.insert(0, '.')

# Force UTF-8 encoding for output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from xtquant import xtdata
import pandas as pd

print("=" * 70)
print("QMT Environment Check")
print("=" * 70)

# Test 1: Check stock list retrieval
print("\n1. Check stock list retrieval...")
try:
    stock_list = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"[OK] Successfully retrieved stock list: {len(stock_list)} stocks")
except Exception as e:
    print(f"[FAIL] Failed to get stock list: {e}")
    print("[WARN] Possible reason: QMT not logged in or no market data permission")
    sys.exit(1)

# Test 2: Check historical K-line data
print("\n2. Check historical K-line data...")
test_code = '600519.SH'
try:
    hist_data = xtdata.get_market_data(
        stock_list=[test_code],
        period='1d',
        count=5
    )

    if hist_data and 'volume' in hist_data:
        volume_df = hist_data['volume']
        print(f"[OK] Successfully retrieved historical K-line data")
        print(f"   DataFrame shape: {volume_df.shape}")
        print(f"   Columns: {list(volume_df.columns)}")
        print(f"   Index: {list(volume_df.index)}")

        if test_code in volume_df.columns:
            volumes = volume_df[test_code]
            print(f"   Volume data: {volumes.tolist()}")
        else:
            print(f"[WARN] {test_code} not in columns")
    else:
        print(f"[FAIL] Historical K-line data is empty")
        print("[WARN] Possible reason: No historical data permission")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] Failed to get historical K-line: {e}")
    sys.exit(1)

# Test 3: Check real-time quotes
print("\n3. Check real-time quotes...")
try:
    tick_data = xtdata.get_full_tick([test_code])
    if tick_data and test_code in tick_data:
        data = tick_data[test_code]
        print(f"[OK] Successfully retrieved real-time quotes")
        print(f"   lastPrice: {data.get('lastPrice', 'N/A')}")
        print(f"   lastClose: {data.get('lastClose', 'N/A')}")
        print(f"   volume: {data.get('volume', 'N/A')}")
    else:
        print(f"[WARN] Real-time quotes empty (may be outside trading hours)")
except Exception as e:
    print(f"[FAIL] Failed to get real-time quotes: {e}")

print("\n" + "=" * 70)
print("Check completed")
print("=" * 70)
print("\nIf all tests passed, QMT environment is ready")
print("Execute: python tasks/collect_auction_snapshot.py --date 2026-02-12")