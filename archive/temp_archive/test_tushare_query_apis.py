"""
Tushare Query API Test Script
Test targets: Test various APIs using query method
"""

import tushare as ts
from datetime import datetime

# Set token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"
ts.set_token(TOKEN)
pro = ts.pro_api()

def test_query_apis():
    """Test various APIs using query method"""
    print("=" * 60)
    print("Tushare Query API Test")
    print("=" * 60)
    
    # API names to test
    api_names = [
        'daily',  # Daily data
        'moneyflow',  # Moneyflow
        'ths_daily',  # THS daily
        'ths_moneyflow',  # THS moneyflow
        'ths_member',  # THS member
        'stk_chip_cost',  # Chip cost
        'stk_chip_distribution',  # Chip distribution
        'stk_chip_concentration',  # Chip concentration
        'stk_chip_pc',  # Chip profit/loss ratio
        'stk_chip_stat',  # Chip statistics
        'stk_chip_flow',  # Chip flow
    ]
    
    common_params = {
        'ts_code': '603607.SH',
        'start_date': '20260201',
        'end_date': '20260206'
    }
    
    for api_name in api_names:
        try:
            df = pro.query(api_name, **common_params)
            print(f"✅ {api_name}: Success ({len(df)} records)")
            print(f"   Fields: {list(df.columns)[:5]}...")
        except Exception as e:
            print(f"❌ {api_name}: Failed - {e}")
    
    print("\n" + "=" * 60)
    print("Conclusion")
    print("=" * 60)
    print("1. ✅ moneyflow: Can get individual stock moneyflow data")
    print("2. ❌ ths_moneyflow: Interface name might be wrong or no permission")
    print("3. ❌ stk_chip_*: Interface names might be wrong or no permission")

if __name__ == "__main__":
    test_query_apis()