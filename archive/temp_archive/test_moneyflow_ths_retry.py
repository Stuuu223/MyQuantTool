"""
Retry Test for Tushare moneyflow_ths API
Test after waiting for rate limit to reset
"""

import sys
sys.path.append('E:/MyQuantTool')

import tushare as ts
from datetime import datetime
import time

# Set token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"
ts.set_token(TOKEN)
pro = ts.pro_api()

def test_with_retry():
    """Test moneyflow_ths with retry"""
    print("=" * 60)
    print("Retry Test: Tushare moneyflow_ths API")
    print("=" * 60)
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test stock: 603607.SH")
    print(f"Test date: 2025-08-12")
    print()
    
    max_retries = 3
    retry_delay = 10  # seconds
    
    for attempt in range(1, max_retries + 1):
        print(f"Attempt {attempt}/{max_retries}...")
        
        try:
            df = pro.moneyflow_ths(
                ts_code='603607.SH',
                start_date='20250812',
                end_date='20250812'
            )
            
            print(f"✅ SUCCESS: {len(df)} records")
            print(f"Fields: {list(df.columns)}")
            print(f"\nData:")
            print(df)
            
            print("\n" + "=" * 60)
            print("Conclusion: API is ACCESSIBLE")
            print("=" * 60)
            print("✅ Rate limit has been reset")
            print("✅ Your token has 5000+ points")
            print("✅ The API can be used for offline research")
            
            return df
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ FAILED: {e}")
            
            if "每分钟" in error_msg or "每小时" in error_msg or "分钟" in error_msg or "小时" in error_msg:
                print(f"Reason: Rate limited")
                if attempt < max_retries:
                    print(f"Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                else:
                    print("\n" + "=" * 60)
                    print("Conclusion: API is RATE LIMITED")
                    print("=" * 60)
                    print("❌ Rate limit is still active")
                    print("❌ Need to wait longer or reduce frequency")
                    print("✅ Continue using eastmoney + standard moneyflow")
            elif "权限" in error_msg and ("分钟" not in error_msg and "小时" not in error_msg):
                print(f"Reason: No permission")
                print("\n" + "=" * 60)
                print("Conclusion: API is NOT PERMITTED")
                print("=" * 60)
                print("❌ Your token does not have 5000+ points")
                print("✅ Continue using eastmoney + standard moneyflow")
                return None
            else:
                print(f"Reason: Unknown error - {error_msg}")
                return None
    
    return None

if __name__ == "__main__":
    test_with_retry()