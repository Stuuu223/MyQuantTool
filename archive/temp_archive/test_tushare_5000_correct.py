"""
Tushare 5000 Points Features Test Script
Test targets: Verify industry moneyflow and chip cost APIs
"""

import pandas as pd
import tushare as ts
from datetime import datetime

# Set token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"
ts.set_token(TOKEN)
pro = ts.pro_api()

def test_ths_moneyflow():
    """Test THS moneyflow API"""
    print("=" * 60)
    print("Test 1: THS Moneyflow API (ths_moneyflow)")
    print("=" * 60)
    
    try:
        # Get THS moneyflow data
        df = pro.ths_moneyflow(
            ts_code='603607.SH',
            start_date='20260201',
            end_date='20260206'
        )
        
        print(f"Success: {len(df)} records")
        print(f"Fields: {list(df.columns)}")
        print(f"\nData:")
        print(df)
        
        return df
        
    except Exception as e:
        print(f"Failed: {e}")
        return None

def test_moneyflow():
    """Test individual stock moneyflow API"""
    print("\n" + "=" * 60)
    print("Test 2: Individual Stock Moneyflow API (moneyflow)")
    print("=" * 60)
    
    try:
        # Get individual stock moneyflow data
        df = pro.moneyflow(
            ts_code='603607.SH',
            start_date='20260201',
            end_date='20260206'
        )
        
        print(f"Success: {len(df)} records")
        print(f"Fields: {list(df.columns)}")
        print(f"\nData:")
        print(df)
        
        return df
        
    except Exception as e:
        print(f"Failed: {e}")
        return None

def test_stk_chip_cost():
    """Test daily chip cost API"""
    print("\n" + "=" * 60)
    print("Test 3: Daily Chip Cost API (stk_chip_cost)")
    print("=" * 60)
    
    try:
        # Get chip cost data
        df = pro.stk_chip_cost(
            ts_code='603607.SH',
            start_date='20260201',
            end_date='20260206'
        )
        
        print(f"Success: {len(df)} records")
        print(f"Fields: {list(df.columns)}")
        print(f"\nData:")
        print(df)
        
        return df
        
    except Exception as e:
        print(f"Failed: {e}")
        return None

def test_stk_chip_distribution():
    """Test chip distribution API"""
    print("\n" + "=" * 60)
    print("Test 4: Chip Distribution API (stk_chip_distribution)")
    print("=" * 60)
    
    try:
        # Get chip distribution data
        df = pro.stk_chip_distribution(
            ts_code='603607.SH',
            start_date='20260201',
            end_date='20260206'
        )
        
        print(f"Success: {len(df)} records")
        print(f"Fields: {list(df.columns)}")
        print(f"\nData:")
        print(df)
        
        return df
        
    except Exception as e:
        print(f"Failed: {e}")
        return None

def test_stk_chip_concentration():
    """Test chip concentration API"""
    print("\n" + "=" * 60)
    print("Test 5: Chip Concentration API (stk_chip_concentration)")
    print("=" * 60)
    
    try:
        # Get chip concentration data
        df = pro.stk_chip_concentration(
            ts_code='603607.SH',
            start_date='20260201',
            end_date='20260206'
        )
        
        print(f"Success: {len(df)} records")
        print(f"Fields: {list(df.columns)}")
        print(f"\nData:")
        print(df)
        
        return df
        
    except Exception as e:
        print(f"Failed: {e}")
        return None

def main():
    print("Tushare 5000 Points Features Test")
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test stock: 603607.SH")
    print(f"Test date: 2026-02-01 to 2026-02-06")
    print()
    
    # Run tests
    test_ths_moneyflow()
    test_moneyflow()
    test_stk_chip_cost()
    test_stk_chip_distribution()
    test_stk_chip_concentration()
    
    print("\n" + "=" * 60)
    print("Test Completed")
    print("=" * 60)

if __name__ == "__main__":
    main()