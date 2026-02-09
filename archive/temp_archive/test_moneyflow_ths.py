"""
Test Tushare moneyflow_ths API
Test target: Verify if the account has 5000+ points to access THS moneyflow
"""

import pandas as pd
import tushare as ts
from datetime import datetime

# Set token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"
ts.set_token(TOKEN)
pro = ts.pro_api()

def test_moneyflow_ths():
    """Test moneyflow_ths API"""
    print("=" * 60)
    print("Test: Tushare moneyflow_ths API")
    print("=" * 60)
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test stock: 603607.SH")
    print(f"Test date: 2026-02-01 to 2026-02-06")
    print()
    
    try:
        # Call moneyflow_ths with correct API name
        df = pro.moneyflow_ths(
            ts_code='603607.SH',
            start_date='20260201',
            end_date='20260206'
        )
        
        print(f"✅ Success: {len(df)} records")
        print(f"Fields: {list(df.columns)}")
        print(f"\nData:")
        print(df)
        
        print("\n" + "=" * 60)
        print("Conclusion")
        print("=" * 60)
        print("✅ Your account has 5000+ points!")
        print("✅ moneyflow_ths API is available")
        print("✅ You can use THS moneyflow as a data source")
        
        return df
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed: {e}")
        
        print("\n" + "=" * 60)
        print("Conclusion")
        print("=" * 60)
        
        if "权限" in error_msg or "permission" in error_msg.lower():
            print("❌ Your account does NOT have 5000+ points")
            print("❌ moneyflow_ths API requires 5000+ points")
            print("✅ You can still use moneyflow (standard) API")
        elif "接口名" in error_msg or "interface" in error_msg.lower():
            print("❌ API name might be wrong")
            print("❌ Please check Tushare documentation")
        else:
            print("❌ Unknown error")
            print(f"Error details: {error_msg}")
        
        return None

if __name__ == "__main__":
    test_moneyflow_ths()
