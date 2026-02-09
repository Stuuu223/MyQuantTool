"""
Tushare All APIs Test Script
Test targets: Try to find correct API names
"""

import tushare as ts
from datetime import datetime

# Set token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"
ts.set_token(TOKEN)
pro = ts.pro_api()

def test_all_available_apis():
    """Test all available APIs in pro object"""
    print("=" * 60)
    print("Tushare Available APIs Test")
    print("=" * 60)
    
    # Get all attributes of pro object
    all_attrs = dir(pro)
    
    # Filter for API methods (start with specific prefixes)
    api_prefixes = ['moneyflow', 'chip', 'ths', 'stk_']
    
    found_apis = []
    for attr in all_attrs:
        for prefix in api_prefixes:
            if prefix in attr.lower() and not attr.startswith('_'):
                found_apis.append(attr)
                break
    
    # Remove duplicates
    found_apis = list(set(found_apis))
    found_apis.sort()
    
    print(f"Found {len(found_apis)} APIs related to moneyflow/chip/ths:")
    for api in found_apis:
        print(f"  - {api}")
    
    print("\n" + "=" * 60)
    print("Testing APIs with minimal parameters")
    print("=" * 60)
    
    # Test each API
    for api_name in found_apis:
        try:
            api_func = getattr(pro, api_name)
            
            # Try to call with different parameter combinations
            test_params = [
                {},  # No parameters
                {'ts_code': '603607.SH'},  # Stock code only
                {'trade_date': '20260206'},  # Date only
                {'ts_code': '603607.SH', 'start_date': '20260201', 'end_date': '20260206'},  # Stock + date range
            ]
            
            for params in test_params:
                try:
                    df = api_func(**params)
                    print(f"✅ {api_name}: Success with params={params} ({len(df)} records)")
                    break  # Success, no need to try other params
                except Exception as e:
                    # Try next parameter combination
                    continue
            
        except Exception as e:
            print(f"❌ {api_name}: Error - {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_all_available_apis()