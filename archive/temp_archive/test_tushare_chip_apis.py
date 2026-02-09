"""
Tushare Chip APIs Test Script
Test targets: Verify chip-related APIs
"""

import pandas as pd
import tushare as ts
from datetime import datetime

# Set token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"
ts.set_token(TOKEN)
pro = ts.pro_api()

def test_chip_apis():
    """Test various chip-related APIs"""
    print("=" * 60)
    print("Tushare Chip APIs Test")
    print("=" * 60)
    
    # Possible chip API names
    api_names = [
        ('stk_chip', {}),
        ('stk_chip_pc', {}),
        ('stk_chip_stat', {}),
        ('stk_chip_pe', {}),
        ('stk_chip_pb', {}),
        ('stk_chip_ps', {}),
        ('stk_chip_pt', {}),
    ]
    
    for api_name, params in api_names:
        try:
            # Try to get the API
            api_func = getattr(pro, api_name)
            
            # Try to call with parameters
            try:
                df = api_func(
                    ts_code='603607.SH',
                    start_date='20260201',
                    end_date='20260206',
                    **params
                )
                print(f"✅ {api_name}: Success ({len(df)} records)")
                print(f"   Fields: {list(df.columns)}")
            except Exception as e:
                print(f"❌ {api_name}: Call failed - {e}")
            
        except AttributeError:
            print(f"❌ {api_name}: API not found")
        except Exception as e:
            print(f"❌ {api_name}: Error - {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_chip_apis()