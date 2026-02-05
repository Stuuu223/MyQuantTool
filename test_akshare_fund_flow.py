"""
Test script to investigate AkShare 502 issue
Tests two interfaces:
1. AkShare stock_individual_fund_flow interface
2. EastMoney direct API (used by fund_flow_analyzer)
"""

import sys
import time
import akshare as ak
import requests
from datetime import datetime

def test_akshare_interface(stock_code="600519"):
    """Test AkShare interface"""
    print(f"\n{'='*60}")
    print(f"Test 1: AkShare stock_individual_fund_flow interface")
    print(f"{'='*60}")
    print(f"Stock code: {stock_code}")
    print(f"AkShare version: {ak.__version__}")
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        start_time = time.time()
        df = ak.stock_individual_fund_flow(stock=stock_code, market="sh")
        elapsed = time.time() - start_time

        print(f"✅ AkShare interface succeeded")
        print(f"   Time: {elapsed:.2f} seconds")
        print(f"   Data type: {type(df)}")
        print(f"   Data shape: {df.shape}")
        print(f"   First 5 rows:")
        print(df.head())
        return True, df
    except Exception as e:
        print(f"❌ AkShare interface failed")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {repr(e)}")
        return False, None


def test_eastmoney_api(stock_code="600519"):
    """Test EastMoney direct API (used by fund_flow_analyzer)"""
    print(f"\n{'='*60}")
    print(f"Test 2: EastMoney direct API (used by fund_flow_analyzer)")
    print(f"{'='*60}")
    print(f"Stock code: {stock_code}")
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Parse stock code to EastMoney format
    code = stock_code.replace('.SZ', '').replace('.SH', '')
    if code.startswith('6') or code.startswith('5'):
        secid = f"1.{code}"
    else:
        secid = f"0.{code}"

    base_url = "http://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
        "klt": "101",  # Daily
        "lmt": 5
    }

    try:
        start_time = time.time()
        response = requests.get(base_url, params=params, timeout=10)
        elapsed = time.time() - start_time

        print(f"   HTTP status code: {response.status_code}")
        print(f"   Time: {elapsed:.2f} seconds")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ EastMoney API succeeded")
            print(f"   Data structure: {list(data.keys())}")

            if 'data' in data and 'klines' in data['data']:
                klines = data['data']['klines']
                print(f"   Data count: {len(klines)}")
                if klines:
                    print(f"   First data row: {klines[0]}")
            return True, data
        else:
            print(f"❌ EastMoney API returned non-200 status code")
            print(f"   Response content: {response.text[:200]}")
            return False, None

    except requests.exceptions.HTTPError as e:
        print(f"❌ EastMoney API HTTP error")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {repr(e)}")
        if e.response is not None:
            print(f"   HTTP status code: {e.response.status_code}")
            print(f"   Response content: {e.response.text[:200]}")
        return False, None
    except Exception as e:
        print(f"❌ EastMoney API other error")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {repr(e)}")
        return False, None


def test_consecutive_requests(stock_code="600519", count=5):
    """Test consecutive requests (simulate hot pool batch calls)"""
    print(f"\n{'='*60}")
    print(f"Test 3: Consecutive requests (simulate hot pool batch calls)")
    print(f"{'='*60}")
    print(f"Stock code: {stock_code}")
    print(f"Request count: {count}")
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    base_url = "http://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
    code = stock_code.replace('.SZ', '').replace('.SH', '')
    secid = f"1.{code}" if code.startswith('6') or code.startswith('5') else f"0.{code}"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
        "klt": "101",
        "lmt": 5
    }

    success_count = 0
    fail_count = 0
    error_types = {}

    for i in range(count):
        print(f"\nRequest {i+1}/{count}...")
        try:
            start_time = time.time()
            response = requests.get(base_url, params=params, timeout=10)
            elapsed = time.time() - start_time

            if response.status_code == 200:
                print(f"   ✅ Success (time: {elapsed:.2f}s)")
                success_count += 1
            else:
                print(f"   ❌ Failed (status code: {response.status_code}, time: {elapsed:.2f}s)")
                fail_count += 1
                error_type = f"HTTP_{response.status_code}"
                error_types[error_type] = error_types.get(error_type, 0) + 1

            # No delay, direct consecutive requests (test rate limiting)
        except requests.exceptions.HTTPError as e:
            print(f"   ❌ HTTP error (status code: {e.response.status_code})")
            fail_count += 1
            error_type = f"HTTP_{e.response.status_code}"
            error_types[error_type] = error_types.get(error_type, 0) + 1
        except Exception as e:
            print(f"   ❌ Other error: {type(e).__name__}")
            fail_count += 1
            error_type = type(e).__name__
            error_types[error_type] = error_types.get(error_type, 0) + 1

    print(f"\n{'='*60}")
    print(f"Consecutive requests test results:")
    print(f"   Success: {success_count}/{count} ({success_count/count*100:.1f}%)")
    print(f"   Failed: {fail_count}/{count} ({fail_count/count*100:.1f}%)")
    print(f"   Error types: {error_types}")
    print(f"{'='*60}")

    return success_count, fail_count, error_types


def main():
    """Main function"""
    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
    else:
        stock_code = "600519"  # Kweichow Moutai

    print(f"\n{'#'*60}")
    print(f"# AkShare 502 Issue Investigation Script")
    print(f"{'#'*60}")
    print(f"Stock code: {stock_code}")
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"AkShare version: {ak.__version__}")
    print(f"{'#'*60}")

    # Test 1: AkShare interface
    akshare_success, akshare_data = test_akshare_interface(stock_code)

    # Test 2: EastMoney direct API
    eastmoney_success, eastmoney_data = test_eastmoney_api(stock_code)

    # Test 3: Consecutive requests (simulate hot pool batch calls)
    success, fail, error_types = test_consecutive_requests(stock_code, count=5)

    # Summary
    print(f"\n{'#'*60}")
    print(f"# Test Summary")
    print(f"{'#'*60}")
    print(f"AkShare interface: {'✅ Normal' if akshare_success else '❌ Failed'}")
    print(f"EastMoney API: {'✅ Normal' if eastmoney_success else '❌ Failed'}")
    print(f"Consecutive request success rate: {success/5*100:.1f}%")
    print(f"Consecutive request error types: {error_types}")
    print(f"{'#'*60}\n")


if __name__ == "__main__":
    main()